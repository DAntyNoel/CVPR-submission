# Base-Error Mining Task

Created: 2026-05-27

## 1. 目标

本任务用于解决当前 COCO object-existence 接近 ceiling 的问题：普通
COCO held-out 上 Base Instruct 已达到约 95.9% accuracy，Hard COCO 上也有约
94.4% accuracy，导致 Answer-DPO 与 Evidence-Hint DPO 的差距很难被稳定观察。

Base-error mining 的目标是构造一个小规模、锁定的诊断评测集：

> 先在一个较大的 held-out 候选池上运行 Base Instruct，只保留 Base 明确答错且标签可靠的样本，再用同一个 locked set 评测 Base Instruct、Answer-DPO 和 Evidence-Hint DPO。

这个评测集只作为 diagnostic set，用来观察两种 DPO 是否能修复 Base 的典型错误；它不能替代普通 held-out / Hard COCO / GQA simple 主表，也不能被写成无偏总体 benchmark。

## 2. 实验边界

- 不新增第四个方法组，仍只比较 Base Instruct、Answer-DPO、Evidence-Hint DPO。
- 不用于训练、调参或筛选 adapter，只用于最终诊断评测。
- 不在当前交互环境直接运行 7B VLM 推理；所有完整 Base mining 推理和三组复评都必须通过 Slurm。
- 候选池构造、打分、JSONL 过滤、summary 统计可以作为轻量 CPU 步骤本地运行。
- locked set 一旦确定，不再根据 Answer-DPO 或 Evidence-Hint DPO 结果修改。

## 3. 推荐产物

建议新增或生成以下文件：

```text
data/eval/base_error_mining_candidates.jsonl
data/eval/base_error_mining_candidates.summary.json
data/eval/base_error_mining_image_ids.txt
data/eval/base_error_mining_image_ids.summary.json
results/eval/generations/base_error_mining_candidates/mixed/base.jsonl
results/eval/generations/base_error_mining_candidates/mixed/base.metrics.json
data/eval/base_error_mined_object_existence.jsonl
data/eval/base_error_mined_object_existence.summary.json
data/audit/base_error_mined_audit.csv
results/eval/generations/base_error_mined_object_existence/mixed/base.jsonl
results/eval/generations/base_error_mined_object_existence/mixed/answer_dpo.jsonl
results/eval/generations/base_error_mined_object_existence/mixed/evidence_hint_dpo.jsonl
tasks/base-error-mining/RESULTS.md
tasks/base-error-mining/results_summary.json
```

如果后续把 GQA simple 也纳入 mining，可另存为：

```text
data/eval/base_error_mined_gqa_simple.jsonl
```

第一版优先做 COCO object-existence，因为它直接回应 COCO ceiling effect。

## 4. 候选池设计

候选池应比最终 locked set 大，建议先做 5k 到 20k 条候选问题，最后锁定
500 到 1,000 条诊断样本。候选池来源按优先级：

1. COCO held-out image ids 中未用于训练的图片。
2. 当前 Hard COCO 的 same-coarse-group absent-object 逻辑。
3. 额外加入更容易出错但仍可审计的负例类型，例如 fine-grained confusable objects、常共现物体、较小可见面积正例。
4. 可选：GQA simple candidate 中的未训练图片，用于属性和左右关系 mining。

候选池需要保留以下字段：

```text
id
source
image
image_id
question
target
target_object 或 target_text
task_type
candidate_strategy
positive_object
negative_object
```

COCO object-existence 的第一版建议保持 yes/no 大致平衡，并记录每个类别、每种候选策略的数量，避免最后只剩少数高频类别。

## 5. Mining 流程

### Step 1: 构造候选池

写一个轻量 CPU 脚本生成候选集，建议命名为：

```text
scripts/eval/prepare_base_error_mining_candidates.py
```

关键检查：

- train/eval image overlap 必须为 0。
- 图片路径必须存在。
- 同一 image/question/target_object 不重复。
- COCO 负例默认继续排除低置信类别；如需保留，必须进入人工 audit。
- 输出 summary，包含候选数量、yes/no 比例、类别分布、策略分布、图片数、重叠检查。

### Step 2: Base 推理

候选池准备好后，通过 Slurm 跑 Base Instruct：

```bash
MODEL_KEY=base \
EVAL_JSONL=data/eval/base_error_mining_candidates.jsonl \
OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

不要在当前 shell 直接启动 7B 模型推理。

### Step 3: 自动打分并筛 Base 错误

使用现有 scorer 先得到 Base predictions：

```bash
python scripts/eval/score_object_eval.py \
  --input results/eval/generations/base_error_mining_candidates/mixed/base.jsonl
```

再写一个轻量过滤脚本，建议命名为：

```text
scripts/eval/mine_base_errors.py
```

筛选规则：

- 保留 `prediction != target` 的样本。
- 优先保留可解析为 yes/no 的错误；`other` 或 refusal 单独统计，除非人工确认其确实是错误。
- 按 false positive / false negative 分层采样，默认各取一半。
- 按 object category 和 candidate_strategy 限制单类上限，避免 mined set 被少数对象主导。
- 输出 locked set 前固定随机种子。

### Step 4: 人工审计

自动 mined set 需要做小规模人工审计，建议 100 到 200 条：

```text
data/audit/base_error_mined_audit.csv
```

审计项：

- 图像是否能打开。
- 问题是否语义清楚。
- target label 是否可信。
- Base 是否确实答错。
- 是否存在 COCO 漏标、小物体不可见、遮挡过强、问题歧义等情况。

若审计发现系统性噪声，优先修改候选池过滤规则后重新 mining；不要只删除会影响方法比较的个别样本。

### Step 5: 锁定诊断集

锁定后输出：

```text
data/eval/base_error_mined_object_existence.jsonl
data/eval/base_error_mined_object_existence.summary.json
```

summary 至少记录：

- 候选池路径和 Base generation 路径。
- mining 日期、随机种子、筛选规则。
- selected rows、unique images、yes/no 数量。
- Base false positive / false negative 数量。
- 类别分布和策略分布。
- train/eval image overlap。
- audit 通过率。

### Step 6: 三组复评

在 locked set 上复评三组：

```bash
MODEL_KEY=base EVAL_JSONL=data/eval/base_error_mined_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/base_error_mined_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo EVAL_JSONL=data/eval/base_error_mined_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

Base 的候选池输出可以用于 mining 依据，但 locked set 上仍建议保留一份同路径复评输出，方便三组 metrics 的目录结构一致。

## 6. 主要指标

这个集合是按 Base 错误筛出来的，因此不能把 Base accuracy 当作普通泛化能力指标解释。重点看：

| 指标 | 用途 |
| --- | --- |
| Recovery Accuracy | DPO 在 Base 错误样本上修复了多少 |
| False Positive Recovery | 对 Base 误报不存在对象的修复率 |
| False Negative Recovery | 对 Base 漏检存在对象的修复率 |
| Evidence-Hint vs Answer-DPO Delta | 核心比较，判断 evidence hint 是否比普通 Answer-DPO 更会修复错误 |
| Refusal / Other Rate | 排除靠拒答或格式漂移获得收益 |
| Category Breakdown | 检查收益是否只来自少数类别 |
| Strategy Breakdown | 区分 same-coarse、confusable、small-object 等错误来源 |

论文中应明确说明：该诊断集是 Base-conditioned evaluation，因此它衡量的是错误修复能力，不是无偏 accuracy。

## 7. 判读规则

| 结果模式 | 解释与写法 |
| --- | --- |
| Evidence-Hint DPO 明显高于 Answer-DPO，且 refusal 不升高 | 可作为 evidence hint 改善 Base 典型错误的强诊断证据。 |
| 两个 DPO 都高于 Base，但彼此接近 | 说明偏好训练能修复部分 Base 错误，但 evidence hint 的额外作用有限。 |
| Evidence-Hint 只降低 FP、但提高 FN | 写成对象幻觉减少与召回损失之间的 trade-off。 |
| 三组都接近或 DPO 更差 | 说明 mined 错误可能是标注噪声、视觉不可见或训练未覆盖的困难类型。 |
| 效果只集中在少数类别 | 不写总体强结论，改写为类别特定诊断发现。 |

## 8. 与论文主线的关系

Base-error mined set 的推荐定位：

- 如果 GQA simple 和普通 held-out 已能支持主结论，它放 appendix 或 diagnostic analysis。
- 如果 COCO/Hard COCO ceiling 太强，它可以作为正文短小诊断表，解释为什么普通 COCO 差距小。
- 不应替代主表，因为它由 Base 错误条件化构造。
- 不应用于选择训练 checkpoint、prompt 或 mining 阈值。

推荐论文表述：

```text
Because COCO object-existence is near-saturated for the base model, we further
construct a locked diagnostic set from base-model errors on a larger held-out
candidate pool. This set is not used as an unbiased benchmark; instead, it
measures whether preference-tuned variants recover typical base failures under
the same three-group comparison.
```

## 9. 最小任务清单

- [x] 写 `prepare_base_error_mining_candidates.py`，生成 COCO object-existence 候选池。
- [x] 跑候选池 summary 与 train/eval image overlap 检查。
- [x] 通过 Slurm 跑 Base 候选池推理。
- [x] 写 `mine_base_errors.py`，从 Base generation 中筛出 locked set。
- [ ] 人工审计 100 到 200 条 mined 样本。
- [x] 锁定 `base_error_mined_object_existence.jsonl` 和 summary。
- [x] 通过 Slurm 跑三组 locked-set 复评。
- [x] 汇总 recovery、FPR/FNR recovery、refusal/other、类别和策略 breakdown。
- [ ] 决定放正文 diagnostic table 还是 appendix。

## 10. 当前状态

- 已新增 `scripts/eval/prepare_base_error_mining_candidates.py`、
  `scripts/eval/mine_base_errors.py` 与
  `scripts/eval/summarize_base_error_mining_results.py`。
- 已生成 `data/eval/base_error_mining_image_ids.txt`：2,580 张 COCO
  pool 中未用于训练的图像，train/eval image overlap 为 0。
- 已生成 `data/eval/base_error_mining_candidates.jsonl`：10,000 条 COCO
  object-existence candidate rows，yes/no 各 5,000，`heldout_pool_absent_object`
  与 `same_coarse_group_absent_object` 各 5,000。
- Base candidate mining job `64251` 已完成：candidate accuracy 0.9472，
  528 个可解析 Base 错误，refusal/other 均为 0。
- 已生成 `data/eval/base_error_mined_object_existence.jsonl`：527 条
  Base-conditioned diagnostic rows，404 false negatives，123 false positives，
  474 unique images，train/eval image overlap 为 0。
- 已生成 `data/audit/base_error_mined_audit.csv`：150 条人工审计样本。当前
  audit pass rate 仍为 `null`，因此结果应标注为 pre-audit diagnostic。
- locked-set 复评已完成 Base job `64262`、Answer-DPO job `64264` 与
  Evidence-Hint DPO ZeRO-2 job `64267`。旧 mixed Evidence-Hint ZeRO-3
  adapter job `64201` 已被取消；其依赖 eval job `64263` 因此没有产出。
- 当前 Evidence-Hint row 使用 completed ZeRO-2 adapter
  `outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo_zero2/`，输出到
  canonical `mixed/evidence_hint_dpo.jsonl`。早先的 job `64266` 也产生了一份
  同内容的 `mixed_zero2` 变体，保留作追踪用途。
- 当前结果已写入 `tasks/base-error-mining/RESULTS.md` 与
  `tasks/base-error-mining/results_summary.json`。结论是 Answer-DPO recovery
  0.063，Evidence-Hint DPO ZeRO-2 recovery 0.030；Evidence-Hint 在这个
  pre-audit mined set 上未优于 Answer-DPO。
