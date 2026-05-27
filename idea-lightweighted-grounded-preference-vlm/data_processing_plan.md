# 数据处理范式与执行计划

更新日期：2026-05-26

## 0. 总体原则

这版项目只需要证明一个小结论：**Evidence-Hint DPO 是否比普通 Answer-DPO 更能减少简单对象/属性幻觉**。因此数据处理必须服务于“低成本、可复现、少变量”：

- 不做人手画框，不做人手写解释。
- 不引入 GPT/闭源 VLM 生成训练答案，避免额外噪声和成本。
- 不使用评测集图片构造训练样本，尽量避免数据泄漏。
- 所有 chosen/rejected 都由已有标注和模板生成。
- Answer-DPO 与 Evidence-Hint DPO 使用完全相同的图片、问题、chosen/rejected 语义，只差 evidence hint 格式。

最终产物只需要两份训练 JSONL：

```text
data/processed/answer_dpo_train.jsonl
data/processed/evidence_hint_dpo_train.jsonl
```

以及一份人工抽查表：

```text
data/audit/audit_200.csv
```

## 1. 数据来源

### 1.1 首选训练来源

| 来源 | 使用部分 | 目的 | 备注 |
| --- | --- | --- | --- |
| COCO train2017 | `instances_train2017.json` | 构造对象存在问题 | 用 train split，避免和 POPE/COCO-val 评测重叠 |
| GQA train balanced | questions + scene graphs | 构造简单属性/关系问题 | 只取低噪声 question types |

### 1.2 评测来源

| 来源 | 用途 |
| --- | --- |
| POPE | 主 object hallucination 评测 |
| AMBER object/attribute subset | 对象/属性幻觉评测 |
| GQA val/dev simple subset | 简单 VQA 准确率 |
| Hard COCO held-out | 常共现/同粗类难负例，专测 absent-object false positive |

关键约束：训练样本优先来自 COCO train2017 和 GQA train；评测使用 POPE/AMBER/GQA val 或 dev。自建 COCO/Hard COCO 评测必须来自 held-out/unused image ids。脚本中保留 `image_id` 去重检查，发现 train/eval image overlap 就剔除训练样本。

## 2. 目标规模

先做稳定版 5k，再做扩展版 10k：

| 版本 | COCO 对象存在 | GQA 属性/关系 | 总量 |
| --- | ---: | ---: | ---: |
| smoke | 1,500 | 500 | 2,000 |
| main | 3,500 | 1,500 | 5,000 |
| expanded | 6,000 | 4,000 | 10,000 |

推荐执行顺序：先生成 smoke 版，跑通训练和评测；如果 2k 数据格式没问题，直接生成 main 版作为论文主结果。expanded 版现在作为条件触发的 10k scale-up：只有当 5k 主结果、Hard COCO、evidence-style prompt 和 POPE/AMBER 小子集仍不足以支撑清晰结论时，才重训 10k Answer-DPO 与 10k Evidence-Hint DPO。

## 3. 统一样本格式

先生成一个中间格式 `canonical_pairs.jsonl`，再导出两种训练格式。这样 Answer-DPO 和 Evidence-Hint DPO 的语义完全对齐。

```json
{
  "id": "coco_obj_000001",
  "source": "coco",
  "image": "data/images/coco/train2017/000000123456.jpg",
  "image_id": "coco_train2017_000000123456",
  "task_type": "object_existence",
  "question": "Is there a dog in the image?",
  "chosen_answer": "Yes, there is a dog in the image.",
  "rejected_answer": "Yes, there is a cat in the image.",
  "evidence_hint_chosen": "Evidence hint: annotated visible object: dog.",
  "evidence_hint_rejected": "Evidence hint: unsupported object: cat is not annotated as visible.",
  "label": {
    "positive_object": "dog",
    "negative_object": "cat"
  }
}
```

导出的 Answer-DPO：

```json
{
  "id": "coco_obj_000001",
  "image": "data/images/coco/train2017/000000123456.jpg",
  "prompt": "<image>\nQuestion: Is there a dog in the image?\nAnswer:",
  "chosen": "Yes, there is a dog in the image.",
  "rejected": "Yes, there is a cat in the image."
}
```

导出的 Evidence-Hint DPO：

```json
{
  "id": "coco_obj_000001",
  "image": "data/images/coco/train2017/000000123456.jpg",
  "prompt": "<image>\nQuestion: Is there a dog in the image?\nAnswer:",
  "chosen": "Yes, there is a dog in the image.\nEvidence hint: annotated visible object: dog.",
  "rejected": "Yes, there is a cat in the image.\nEvidence hint: unsupported object: cat is not annotated as visible."
}
```

推理评测时不使用 evidence hint prompt，只问普通问题。

## 4. COCO 对象存在样本

### 4.1 选择图片

从 COCO train2017 中抽图，过滤规则：

- 至少包含 2 个已标注对象类别。
- 保留面积大于图片面积 1% 的对象，避免极小物体导致 chosen 本身不稳定。
- 跳过 `iscrowd=1` 的实例。
- 每张图片最多生成 2 条问题，避免同一图片过度重复。

### 4.2 正负对象

正对象：

- 从该图 COCO 标注类别中采样。
- 优先采样面积较大的对象。
- 同一类别重复多个实例也只当作一个 visible object。

负对象：

- 从不在该图标注中的 COCO 类别采样。
- 避免选过于容易被标注漏掉的小物体类别，例如 `fork`、`knife`、`remote` 可以降低采样权重。
- 优先从同一粗类或相近类中采样，让负例不是太弱，例如 `dog/cat`、`bus/truck`、`cup/bottle`。

### 4.2.1 Hard COCO held-out 负例

普通 COCO held-out 已经可能接近 ceiling，因此新增一个只用于评测的 Hard COCO variant。构造原则：

- 只使用 held-out/unused image ids，不进入训练 canonical pairs。
- yes/no 仍保持平衡；正例沿用可见对象，负例优先选择常共现或同粗类但未标注为可见的对象。
- 负例可以从同一图片的正对象出发做相近类别采样，例如 `dog/cat`、`bus/truck`、`cup/bottle`、`chair/couch`，并继续过滤低置信漏标类别。
- 每张图片控制问题数量，避免同图重复过多。
- 输出建议为 `data/eval/coco_hard_object_existence.jsonl` 和对应 `.summary.json`，评测结果写入独立 output variant，避免覆盖普通 COCO held-out。

Hard COCO 只作为评测压力测试，不用于训练或调参；如果它和普通 COCO 结论冲突，论文应优先解释普通 held-out 的 ceiling effect。

### 4.3 问题模板

对象存在只用 yes/no 模板，减少答案风格变量：

```text
Is there a {pos_obj} in the image?
Can you see a {pos_obj} in this image?
Does the image contain a {pos_obj}?
```

chosen/rejected：

```text
Chosen: Yes, there is a {pos_obj} in the image.
Rejected: Yes, there is a {neg_obj} in the image.
```

注意：rejected 故意回答另一个不存在对象，而不是简单回答 “No”，这样更像 hallucination 错误。

### 4.4 Evidence hint 模板

```text
Chosen hint: Evidence hint: annotated visible object: {pos_obj}.
Rejected hint: Evidence hint: unsupported object: {neg_obj} is not annotated as visible.
```

不加入 box 坐标。这样方法仍然是“轻量证据提示”，不是完整 grounding。

## 5. GQA 简单属性/关系样本

### 5.1 选择 question types

只保留容易模板化、低噪声的问题：

- `query color`：What color is the object?
- `query material`：What is the object made of?
- `verify attribute`：Is the object red/wooden/open?
- `choose attribute`：Is the object red or blue?
- 简单空间关系：left/right/above/below，仅在 scene graph 关系明确时使用。

先不使用复杂计数、比较、逻辑组合、多跳推理。它们容易让 15 天项目掉进数据清洗深坑。

### 5.2 属性样本模板

从 GQA scene graph 取 object 与 attribute：

```text
Question: What color is the bus?
Chosen: The bus is yellow.
Rejected: The bus is red.
Chosen hint: Evidence hint: annotated attribute of bus: yellow.
Rejected hint: Evidence hint: mismatched attribute for bus: red.
```

负属性采样规则：

- color 只从颜色词表里采样。
- material 只从材质词表里采样。
- rejected 属性不能等于 chosen 属性。
- 避免选择视觉上过近且标注容易混淆的颜色组合，例如 `gray/silver`、`white/beige` 可以降低采样权重。

### 5.3 关系样本模板

关系样本只保留方向明确的空间关系：

```text
Question: What is to the left of the table?
Chosen: The chair is to the left of the table.
Rejected: The chair is to the right of the table.
Chosen hint: Evidence hint: annotated relation: chair left of table.
Rejected hint: Evidence hint: contradicted relation: chair right of table.
```

关系样本最多占 GQA 部分的 30%。如果人工抽查发现噪声高，就全部降级为属性样本。

## 6. 数据导出与目录结构

建议目录：

```text
data/
  raw/
    coco/
      annotations/instances_train2017.json
      train2017/
    gqa/
      train_balanced_questions.json
      train_sceneGraphs.json
  processed/
    canonical_pairs_smoke.jsonl
    canonical_pairs_main.jsonl
    canonical_pairs_expanded.jsonl
    answer_dpo_train.jsonl
    evidence_hint_dpo_train.jsonl
  eval/
    gqa_simple_eval.jsonl
  audit/
    audit_200.csv
    audit_summary.md
```

脚本建议：

```text
scripts/data/01_build_coco_object_pairs.py
scripts/data/02_build_gqa_simple_pairs.py
scripts/data/03_merge_and_split_pairs.py
scripts/data/04_export_dpo_formats.py
scripts/data/05_make_audit_sheet.py
scripts/data/06_check_data_leakage.py
```

## 7. 质检规则

### 7.1 自动质检

生成后必须跑以下检查：

- `id` 唯一。
- 图片路径存在。
- chosen/rejected 不完全相同。
- chosen/rejected 都不超过 40 tokens，避免风格差异过大。
- Evidence-Hint DPO 中 chosen 和 rejected 都含有 `Evidence hint:`。
- Answer-DPO 中不含 `Evidence hint:`。
- 训练 image_id 与评测 image_id 无交集。
- task type 比例接近目标：object 约 70%，attribute/relation 约 30%。
- rejected object/attribute 不在对应正标注中。

### 7.2 人工抽查

抽查 200 条，表格字段：

```text
id, source, image, question, chosen, rejected, chosen_hint, rejected_hint,
chosen_correct, rejected_wrong, hint_correct, note
```

合格标准：

- `chosen_correct >= 85%`
- `rejected_wrong >= 90%`
- `hint_correct >= 90%`

如果不达标：

- COCO chosen 错：提高面积阈值，从 1% 改到 2%。
- COCO rejected 错：降低容易漏标类别的负采样概率。
- GQA 属性错：只保留 color，暂时去掉 material/relation。
- hint 错：检查模板映射和类别名标准化。

## 8. 随机性与可复现

固定三个 seed：

```text
seed_data = 42
seed_train_1 = 42
seed_train_2 = 3407
```

主论文可以只报告 seed 42；如果时间允许，在附录或正文一句话补 seed 3407 的趋势一致性。数据生成脚本每次输出：

```text
data/processed/stats_main.json
```

内容包括：

- 样本总量。
- 每类 task 数量。
- 每个对象/属性的频次 top 20。
- 平均 prompt/chosen/rejected token 长度。
- 训练/评测 image overlap 数量。

## 9. 15 天执行版排期

| 时间 | 数据处理目标 | 产物 |
| --- | --- | --- |
| Day 1 上午 | 下载/整理 COCO 与 GQA annotation，确定图片路径 | `data/raw/` 可读 |
| Day 1 下午 | 写 COCO object pair 生成脚本 | `canonical_coco_smoke.jsonl` |
| Day 2 上午 | 写 GQA simple pair 生成脚本 | `canonical_gqa_smoke.jsonl` |
| Day 2 下午 | 合并 smoke 2k，导出两种 DPO 格式 | smoke 版两份 train JSONL |
| Day 3 上午 | 生成 200 条 audit CSV，人工抽查 | `audit_200.csv` |
| Day 3 下午 | 根据抽查修过滤规则，生成 main 5k | main 版两份 train JSONL |
| Day 4 | 训练 Answer-DPO 与 Evidence-Hint DPO | 两个 checkpoint |
| Day 5 | 跑 COCO/GQA/Hard COCO/evidence-style prompt | 初版结果表 |
| Day 6 | 补 POPE，AMBER 视数据准备情况加入 | 外部评测表 |
| Day 7 | 如果结果不稳，检查数据分布和 bad cases | `audit_summary.md` |
| Day 8 | 条件触发 10k scale-up | expanded 数据与两组 DPO train JSONL |

Day 8 以后不再大改数据范式；除条件触发的 10k scale-up 外，只做小修、评测、写作和 case study。

## 10. 最小失败保护

如果 GQA 数据处理耗时超预期，直接放弃 GQA 训练数据，只用 COCO object existence 生成 5k pairs。论文结论相应收窄为：

> Evidence hints help reduce simple object hallucination under lightweight DPO tuning.

保留 GQA simple subset 只作为评测，或者完全移除 GQA 指标。这样项目仍然能在 15 天内完成。

如果 7B 训练脚本不稳定，使用 Qwen2.5-VL-3B 跑完整三组实验。正文写作中说明这是 simulated submission / limited-time study，重点放在数据处理范式和趋势观察，而不是 SOTA。
