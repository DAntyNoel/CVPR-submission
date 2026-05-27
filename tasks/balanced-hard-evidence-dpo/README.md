# Balanced Hard Evidence-DPO Task

Created: 2026-05-27

## 1. 目标

当前 Evidence-Hint DPO 的主要问题不是完全无效，而是收益表现为
FPR/FNR trade-off：模型更保守，false-positive rate 略降，但 recall 侧受损，
因此 Acc/F1 没有稳定超过 Answer-DPO。

本任务用于实现一个更有针对性的 rescue experiment：

> 用 balanced hard object-existence pairs 和少量 GQA anchor 构造
> Balanced Hard Evidence-DPO，让 evidence 信号同时覆盖 yes/no 两侧，避免模型
> 只学会少说 yes。

它仍保持小规模、单 backbone、单 seed、ZeRO-2、LoRA-DPO，不新增大规模实验。

## 2. 方法设计

第三组方法从 naive Evidence-Hint DPO 升级为：

```text
Balanced Hard Evidence-DPO
```

数据配方默认 5,000 条：

| Slice | Rows | Purpose |
| --- | ---: | --- |
| Hard COCO paired rows | 1,000 | same-coarse absent-object hard negatives，天然 yes/no 平衡 |
| Base-error paired rows | 1,000 | 从 Base-error-mined set 合成 yes/no 配对，针对 Base 常见错误 |
| COCO canonical paired rows | 2,000 | 从 5k 主训练 COCO 部分合成 present/absent 配对，稳定对象存在能力 |
| GQA anchor rows | 1,000 | 保留简单属性/关系能力，避免只优化 COCO yes/no |

object-existence rows 的 chosen/rejected 都带简短 evidence：

```text
Chosen yes: Yes, there is a bicycle in the image.
Evidence: a bicycle is visually supported in the image.

Rejected no: No, there is no bicycle in the image.
Evidence: a bicycle is not visually supported in the image.
```

对于 absent-object 问题则反过来：

```text
Chosen no: No, there is no dog in the image.
Evidence: a dog is not visually supported in the image.

Rejected yes: Yes, there is a dog in the image.
Evidence: a dog is visually supported in the image.
```

这样 evidence 既不会只惩罚 false positive，也会保护 present-object recall。

## 3. 生成训练数据

轻量 CPU 步骤，可在登录节点运行：

```bash
python tasks/balanced-hard-evidence-dpo/build_balanced_hard_evidence_dpo.py
```

默认输出：

```text
tasks/balanced-hard-evidence-dpo/generated/balanced_hard_evidence_dpo_train.jsonl
tasks/balanced-hard-evidence-dpo/generated/balanced_hard_evidence_dpo_summary.json
tasks/balanced-hard-evidence-dpo/llamafactory_data/cvpr_balanced_hard_evidence_dpo.json
tasks/balanced-hard-evidence-dpo/llamafactory_data/dataset_info.json
```

这些都是派生产物，已由本任务目录下的 `.gitignore` 忽略。

## 4. 训练

完整训练必须走 Slurm，不要在当前交互环境直接启动 7B 训练：

```bash
sbatch tasks/balanced-hard-evidence-dpo/train_balanced_hard_evidence_dpo.slurm
```

该脚本会先重新生成 Balanced Hard Evidence-DPO 数据，再用 ZeRO-2 训练：

```text
tasks/balanced-hard-evidence-dpo/qwen25vl_balanced_hard_evidence_dpo.yaml
```

adapter 输出：

```text
outputs/llamafactory/qwen25vl7b_balanced_hard_evidence_dpo_zero2/
```

## 5. 评测

训练完成后，优先复用现有统一评测脚本，并用 `ADAPTER_NAME_OR_PATH` 指向新 adapter：

```bash
MODEL_KEY=evidence_hint_dpo \
ADAPTER_NAME_OR_PATH=outputs/llamafactory/qwen25vl7b_balanced_hard_evidence_dpo_zero2 \
EVAL_JSONL=data/eval/coco_hard_object_existence.jsonl \
OUTPUT_VARIANT=balanced_hard \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo \
ADAPTER_NAME_OR_PATH=outputs/llamafactory/qwen25vl7b_balanced_hard_evidence_dpo_zero2 \
EVAL_JSONL=data/eval/gqa_simple_heldout.jsonl \
OUTPUT_VARIANT=balanced_hard \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo \
ADAPTER_NAME_OR_PATH=outputs/llamafactory/qwen25vl7b_balanced_hard_evidence_dpo_zero2 \
EVAL_JSONL=data/eval/base_error_mined_object_existence.jsonl \
OUTPUT_VARIANT=balanced_hard \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

如需跑 COCO held-out，也使用同样方式指定 `data/eval/coco_heldout_object_existence.jsonl`。

## 6. 成功标准

本任务只有在同时满足以下趋势时，才适合替换论文中的 naive Evidence-Hint DPO：

- Hard COCO FPR 低于或不高于 Answer-DPO。
- Hard COCO Acc/F1 不低于 Answer-DPO 超过 0.2-0.3 pt。
- GQA simple 不明显退化。
- Base-error-mined recovery 明显高于 naive Evidence-Hint DPO，最好接近或超过 Answer-DPO。
- refusal/other rate 仍为 0 或接近 0。

如果只降低 FPR 但继续牺牲 FNR，则说明 balanced hard evidence 仍没有解决核心问题，
论文应保留诊断型叙事。

## 7. 论文定位

若成功，论文主线可以从：

```text
naive evidence hints are insufficient
```

升级为：

```text
naive evidence hints are insufficient, but balanced hard evidence preferences
can reduce unsupported visual claims without the same recall penalty.
```

若失败，本任务仍然是有价值的 ablation：它表明问题不只是 easy-data ceiling 或
evidence placement，而是模板 evidence 本身的监督强度不足。
