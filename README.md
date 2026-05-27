# CVPR Submission Toy Project

这是一个面向 CVPR 示例投稿的小型实验仓库，目标是在受控、轻量的设定下验证：

> 在 VLM 回答级 DPO 中加入模板化的轻量视觉证据提示，是否能比普通 Answer-DPO 更稳定地减少简单对象幻觉。

当前项目聚焦 **COCO object-existence** 场景，主实验控制为三组：Base Instruct、Answer-DPO、Evidence-Hint DPO。第一版论文不扩展到复杂属性、关系、计数或多 backbone 对比。

## 当前状态

- 研究计划与论文大纲已整理在 `idea-lightweighted-grounded-preference-vlm/`。
- 5k COCO-only preference pairs 已生成，并导出为 Answer-DPO 与 Evidence-Hint DPO 两种格式。
- 数据抽查与泄漏检查已完成，审计摘要见 `data/audit/`。
- Qwen2.5-VL-7B-Instruct 的 Answer-DPO 与 Evidence-Hint DPO LoRA 训练已完成，摘要见 `experiments/training_summary.md`。
- 统一评测脚本已准备好，下一步主要是跑 Base / Answer-DPO / Evidence-Hint DPO 的 object hallucination 评测并整理表格。

## 目录结构

```text
idea-lightweighted-grounded-preference-vlm/
  plan.md                         # 项目目标、方法与实验设计
  paper_outline_and_tasks.md       # 论文大纲与后续任务清单
  data_processing_plan.md          # 数据构造方案

scripts/data/
  README.md                        # 数据流水线说明
  00_*.py ... 10_*.py              # 数据下载、构造、导出、审计与泄漏检查脚本

scripts/eval/
  README.md                        # 评测流水线说明
  prepare_*.py                     # 评测集准备
  run_vlm_inference.py             # 统一推理入口
  score_object_eval.py             # object hallucination 指标计算

experiments/
  README.md                        # 训练与评测启动说明
  llamafactory_configs/            # LLaMA-Factory DPO 配置
  slurm/                           # 训练、下载、评测 Slurm 脚本
  training_summary.md              # 已完成训练的摘要

data/
  processed/                       # canonical pairs 与 DPO 训练 JSONL
  audit/                           # 数据抽查结果
  eval/                            # held-out object-existence 评测集

outputs/
  llamafactory/                    # LoRA adapter 输出

results/
  eval/                            # 评测生成结果与元信息
```

## 环境约定

默认 shell 环境来自 `~/.zshrc`，Python 环境使用 conda，包管理优先使用 `uv`。

不要在当前交互环境里直接启动重任务，例如大规模数据搬运、7B 模型推理、GPU 训练或完整评测。这类任务应通过 Slurm 提交到对应资源。

## 数据流水线

详细命令见 `scripts/data/README.md`。核心产物是：

```text
data/processed/canonical_pairs.jsonl
data/processed/answer_dpo_train.jsonl
data/processed/evidence_hint_dpo_train.jsonl
data/audit/audit_200.csv
data/processed/check_report_main.json
```

如果需要重新生成数据，优先使用已有 Slurm 脚本或轻量 CPU 脚本；大文件建议软链接，不要直接复制进仓库。

## 训练

训练基于仓库内的 `LLaMA-Factory` 和 `experiments/llamafactory_configs/` 配置。主比较包含：

```text
base              # 原始 Qwen2.5-VL-7B-Instruct，不训练
answer_dpo        # 普通回答级 DPO
evidence_hint_dpo # 带轻量 evidence hint 的 DPO
```

训练任务通过 Slurm 提交：

```bash
sbatch experiments/slurm/train_answer_dpo.slurm
sbatch experiments/slurm/train_evidence_hint_dpo.slurm
```

已完成训练的 adapter 默认位于：

```text
outputs/llamafactory/qwen25vl7b_answer_dpo/
outputs/llamafactory/qwen25vl7b_evidence_hint_dpo/
```

## 评测

评测入口见 `scripts/eval/README.md`。先准备 COCO held-out object-existence 评测集：

```bash
python scripts/eval/prepare_coco_heldout_eval.py \
  --heldout-image-ids data/eval/heldout_object_existence_image_ids.txt \
  --output data/eval/coco_heldout_object_existence.jsonl \
  --max-pairs 500 \
  --seed 42
```

推理前可以做轻量 dry-run，检查 adapter 路径是否正确：

```bash
python scripts/eval/run_vlm_inference.py \
  --model-key answer_dpo \
  --eval data/eval/coco_heldout_object_existence.jsonl \
  --dry-run
```

完整推理应通过 Slurm 提交：

```bash
MODEL_KEY=base EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

生成结果保存到：

```text
results/eval/generations/<eval_name>/<model_key>.jsonl
```

计算指标：

```bash
python scripts/eval/score_object_eval.py \
  --input results/eval/generations/coco_heldout_object_existence/base.jsonl
```

## 论文写作

正文建议控制在 6 页以内，只支撑一个小而明确的结论：

- 方法：不改模型结构、不改 DPO loss，只改 preference response 格式。
- 数据：5k COCO object-existence preference pairs。
- 实验：Base Instruct、Answer-DPO、Evidence-Hint DPO 三组。
- 指标：POPE 或 COCO held-out accuracy/F1、yes bias、refusal rate。
- 限制：不声称解决属性、关系、计数、开放式描述或复杂 grounding。

论文大纲和任务清单见 `idea-lightweighted-grounded-preference-vlm/paper_outline_and_tasks.md`。
