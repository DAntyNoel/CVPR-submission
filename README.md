# CVPR Submission Toy Project

这是一个面向 CVPR 示例投稿的小型实验仓库，目标是在受控、轻量的设定下验证：

> 在 VLM 回答级 DPO 中加入模板化的轻量视觉证据提示，是否能比普通 Answer-DPO 更稳定地减少简单对象幻觉。

当前项目聚焦一个小规模 **mixed COCO/GQA** 设定：COCO object-existence 加 GQA simple attribute / left-right relation。主实验仍控制为三组：Base Instruct、Answer-DPO、Evidence-Hint DPO。第一版论文不扩展到复杂推理、计数、多 backbone 或多 seed 对比。

## 当前状态

- 研究计划与论文大纲已整理在 `idea-lightweighted-grounded-preference-vlm/`。
- CVPR LaTeX 稿件已更新在 `paper/`：`main.tex` 当前是一版按“mixed Evidence-Hint DPO
  正常完成并取得小幅正向结果”假设写成的完整 review-ready 草稿，已移除正文占位标记。
- 5k mixed preference pairs 已生成：3,500 COCO object-existence + 1,500 GQA simple attribute/relation。
- mixed audit 与泄漏检查已完成，审计摘要见 `data/audit/`，当前 train/eval image overlap 为 0。
- GQA simple held-out eval 已生成：`data/eval/gqa_simple_heldout.jsonl`，共 1,000 条，color 与 left/right relation 各 500 条。
- Hard COCO held-out eval 已生成：`data/eval/coco_hard_object_existence.jsonl`，共 1,000 条，yes/no 各 500 条，500 张 held-out 图像，train/eval image overlap 为 0。
- mixed Answer-DPO job 64200 已完成并写出 mixed adapter；真实 mixed Evidence-Hint DPO job 64201
  在现有实验记录中仍等待最终核验。论文正文中的 Evidence-Hint 主结果用于本轮“实验一切正常”写作与评审模拟，真实投稿前需用最终评测日志替换核对。
- 5k COCO-only adapter 的三组 held-out object-existence 验证已完成：Base Acc 0.959、Answer-DPO Acc 0.961、Evidence-Hint DPO Acc 0.960。
- 统一评测脚本已支持输出变体目录和 evidence-style prompt；Base 与 mixed Answer-DPO 的 COCO/GQA normal prompt 及 evidence-style prompt 评测均已完成，partial summary 见 `experiments/eval_summary.md`。Evidence-Hint DPO 评测等待 64201 完成后再提交。
- 等待 64201 时，Hard COCO 的 Base 与 mixed Answer-DPO 评测 jobs 64233/64234 已完成：Base Acc 0.944，mixed Answer-DPO Acc 0.950；mixed Evidence-Hint DPO 的 Hard COCO、COCO/GQA normal prompt 与 evidence-style prompt 评测仍等待最终 adapter。

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
  eval_summary.md                  # 已完成评测的摘要

paper/
  main.tex                         # CVPR 2026 完整草稿，含 assumed-normal 主结果
  main_full.tex                    # 独立完整稿入口，编译时包含 appendix
  preamble.tex                     # 与 cvpr-org/author-kit 对齐的 preamble helper
  local_xetex_fonts.tex            # Tectonic/XeTeX T1 编码修正，恢复 Times/Helvetica 粗体
  rebuttal.tex                     # cvpr-org/author-kit 官方 author-response 模板
  cvpr.sty                         # CVPR 2026 官方样式
  ieeenat_fullname.bst             # CVPR 2026 官方引用样式
  references.bib                   # 初稿引用
  appendix.tex                     # full-paper build 使用的补充材料
  Makefile                         # Tectonic 论文编译入口
  rebuttal/                        # 两位模拟 reviewer 的评审结果

data/
  processed/                       # canonical pairs 与 DPO 训练 JSONL
  audit/                           # 数据抽查结果
  eval/                            # held-out object-existence 评测集

outputs/
  llamafactory/                    # LoRA adapter 输出，mixed 与 COCO-only preliminary 分目录保存

results/
  eval/                            # 评测生成结果与元信息
```

## 环境约定

默认 shell 环境来自 `~/.zshrc`，Python 环境使用 conda，包管理优先使用 `uv`。

不要在当前交互环境里直接启动重任务，例如大规模数据搬运、7B 模型推理、GPU 训练或完整评测。这类任务应通过 Slurm 提交到对应资源。

## 论文编译

当前机器已配置用户级 LaTeX 编译环境：

```bash
conda activate cvpr-latex
cd paper
make pdf
```

如需在另一台机器重建该环境：

```bash
conda create -n cvpr-latex -c conda-forge tectonic=0.16.9
```

默认编译器为 Tectonic 0.16.9，输出文件为 `paper/build/main.pdf`。第一次编译会在 `~/.cache/Tectonic/` 缓存 TeX 资源；后续编译可直接复用。由于当前账号没有免密 sudo，未安装系统级 TeX Live，仓库默认不依赖 `apt install` 或系统 `latexmk`。

如需独立编译带附录的完整稿：

```bash
conda activate cvpr-latex
cd paper
make full
```

输出文件为 `paper/build/main_full.pdf`。2026-05-27 已验证：普通 `make pdf`
生成 4 页 `paper/build/main.pdf`，`make full` 生成 5 页带附录
`paper/build/main_full.pdf`。

## 数据流水线

详细命令见 `scripts/data/README.md`。核心产物是：

```text
data/processed/canonical_pairs.jsonl
data/processed/answer_dpo_train.jsonl
data/processed/evidence_hint_dpo_train.jsonl
data/audit/audit_200.csv
data/processed/check_report_main.json
data/eval/gqa_simple_heldout.jsonl
data/eval/coco_hard_object_existence.jsonl
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

mixed 主实验 adapter 默认位于：

```text
outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/
outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo/
```

旧 COCO-only preliminary adapter 位于：

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

GQA simple held-out eval 已准备好；如需重建：

```bash
python scripts/eval/prepare_gqa_simple_heldout_eval.py \
  --candidates data/processed/canonical_gqa_candidates.jsonl \
  --train data/processed/canonical_pairs_main.jsonl \
  --output data/eval/gqa_simple_heldout.jsonl \
  --max-rows 1000 \
  --seed 42
```

Hard COCO held-out eval 已准备好；如需重建：

```bash
python scripts/eval/prepare_coco_hard_eval.py \
  --heldout-image-ids data/eval/heldout_object_existence_image_ids.txt \
  --output data/eval/coco_hard_object_existence.jsonl \
  --max-pairs 500 \
  --seed 42
```

mixed adapter 训练完成后，可以做轻量 dry-run，检查 adapter 路径是否正确：

```bash
python scripts/eval/run_vlm_inference.py \
  --model-key answer_dpo \
  --eval data/eval/coco_heldout_object_existence.jsonl \
  --output results/eval/generations/coco_heldout_object_existence/mixed/answer_dpo.jsonl \
  --dry-run
```

完整推理应通过 Slurm 提交：

```bash
MODEL_KEY=base EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

可通过 `OUTPUT_VARIANT` 避免覆盖已有结果，例如 mixed 主结果写入：

```text
results/eval/generations/<eval_name>/mixed/<model_key>.jsonl
```

evidence-style prompt 评测可复用同一 Slurm 脚本：

```bash
MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/gqa_simple_heldout.jsonl \
OUTPUT_VARIANT=evidence_prompt \
INSTRUCTION_SUFFIX="Answer yes or no, then briefly mention the visual evidence." \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

如需固定使用已完成的 5k COCO-only adapter，而不是当前 registry 默认的 mixed
adapter，可通过 `ADAPTER_NAME_OR_PATH` 覆盖：

```bash
MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
ADAPTER_NAME_OR_PATH=outputs/llamafactory/qwen25vl7b_answer_dpo \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
ADAPTER_NAME_OR_PATH=outputs/llamafactory/qwen25vl7b_evidence_hint_dpo \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

2026-05-27 已按该 COCO-only 设置启动主实验验证：

```text
64205  Base Instruct
64206  Answer-DPO        outputs/llamafactory/qwen25vl7b_answer_dpo
64207  Evidence-Hint DPO outputs/llamafactory/qwen25vl7b_evidence_hint_dpo
```

2026-05-27 等待 mixed Evidence-Hint DPO 64201 时，已提交可先跑的 mixed/evidence-style
评测；Hard COCO 前两组也已提交。当前状态：

```text
64213  COMPLETED  Base Instruct      GQA simple, mixed output variant
64214  COMPLETED  mixed Answer-DPO   COCO held-out, mixed output variant
64215  COMPLETED  mixed Answer-DPO   GQA simple, mixed output variant
64216  COMPLETED  Base Instruct      GQA simple, evidence_prompt output variant
64217  COMPLETED  Base Instruct      COCO held-out, evidence_prompt output variant
64218  COMPLETED  mixed Answer-DPO   GQA simple, evidence_prompt output variant
64219  COMPLETED  mixed Answer-DPO   COCO held-out, evidence_prompt output variant
64233  COMPLETED  Base Instruct      Hard COCO, mixed output variant
64234  COMPLETED  mixed Answer-DPO   Hard COCO, mixed output variant
```

当前可用的 mixed partial 指标：

```text
COCO held-out: Base Acc 0.959, mixed Answer-DPO Acc 0.961
GQA simple:    Base Acc 0.764, mixed Answer-DPO Acc 0.768
Hard COCO:     Base Acc 0.944, mixed Answer-DPO Acc 0.950
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

正文采用 CVPR 2026 格式。页数按 6/7/8 页弹性控制：优先压到 6 页，7 页可接受，8 页作为正文硬上限。参考文献加可选附录部分总量不超过 10 页，附录非必须。本轮写作任务已把 `paper/main.tex` 从结果占位稿改为完整审稿稿，并在 `paper/build/main.pdf` 生成对应 PDF。

模板文件已从 `cvpr-org/author-kit` main commit
`217fe7698116978ab2d972e2369a3d1567152f34` 直接替换：`paper/cvpr.sty`、
`paper/ieeenat_fullname.bst`、`paper/preamble.tex` 和 `paper/rebuttal.tex`
均来自官方文件；`paper/main.tex` 保留本文正文，但文档头部结构按官方
`main.tex` 对齐。用于替换的临时 author-kit clone 已删除，仓库不再保留该模板子仓库。
由于当前用 Tectonic/XeTeX 编译，官方样式中的 PSNFSS Times/Helvetica 粗体在默认
TU 编码下不会自动解析，因此 `paper/local_xetex_fonts.tex` 强制使用 T1 编码，让
`T1/ptm` 和 `T1/phv` 官方 Times/Helvetica 字体族正确加载，避免论文标题和章节标题
退化成非粗体。

正文只支撑一个小而明确的结论：

- 方法：不改模型结构、不改 DPO loss，只改 preference response 格式。
- 数据：5k mixed COCO/GQA preference pairs，覆盖对象存在、简单颜色/材质属性和左右空间关系。
- 实验：Base Instruct、Answer-DPO、Evidence-Hint DPO 三组。
- 指标：COCO held-out、Hard COCO、GQA simple、yes bias、refusal rate；POPE/AMBER 视官方数据可用性补充。
- 限制：不声称解决计数、多步关系、开放式描述或复杂 grounding。

注意：当前论文表格中的 Evidence-Hint DPO 行是按用户指定的“实验正常完成”前提写入的正向结果，用于完善论文叙事和模拟评审；真实提交前应以 `experiments/eval_summary.md` 和最终 Slurm 输出为准逐项复核。

论文大纲和任务清单见 `idea-lightweighted-grounded-preference-vlm/paper_outline_and_tasks.md`。
