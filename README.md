# CVPR Submission Toy Project

这是一个面向 CVPR 示例投稿的小型实验仓库，目标是在受控、轻量的设定下验证：

> 在 VLM 回答级 DPO 中加入模板化的轻量视觉证据提示，是否能比普通 Answer-DPO 更稳定地减少简单对象幻觉。

当前项目聚焦一个小规模 **mixed COCO/GQA** 设定：COCO object-existence 加 GQA simple attribute / left-right relation。主实验仍控制为三组：Base Instruct、Answer-DPO、Evidence-Hint DPO。第一版论文不扩展到复杂推理、计数、多 backbone 或多 seed 对比。

## 当前状态

- 研究计划与论文大纲已整理在 `idea-lightweighted-grounded-preference-vlm/`。
- 二期方法改进想法已整理在 `idea-imporve-evidence/`，聚焦 evidence placement、
  evidence-only preference、chosen-only evidence、counterfactual pairs 和 check-step evidence。
- Phase-2 第一轮方法变体已完成：Evidence-Only DPO、Input-Side Evidence DPO
  和 Chosen-Only Evidence DPO；三组均复用 5k mixed COCO/GQA split、
  Qwen2.5-VL-7B、LoRA-DPO 和 ZeRO-2，只改变 preference 格式。训练 jobs
  64302-64304 与 COCO/GQA/Hard COCO/Base-error-mined after-ok 评测 jobs
  64305-64316 均为 exit 0，统一写入 `OUTPUT_VARIANT=phase2`。Input-Side
  Evidence 是三组里最稳的变体：COCO/GQA/Hard COCO Acc 为
  0.961/0.768/0.947，base-error recovery 为 0.044，但仍未改写主线
  “Evidence-Hint 不稳定超过 Answer-DPO” 的诊断结论。
- 已在 `tasks/answer-evidence-mix-dpo/` 新增 Answer-Evidence Mix DPO 任务实现：
  默认用 70% plain Answer-DPO + 30% Evidence-Hint DPO 构造 5k mixed rescue run，
  目标是在保留 Answer-DPO Acc/F1 的同时继承一部分 Evidence-Hint 的 FPR 下降。
- 已在 `tasks/balanced-hard-evidence-dpo/` 新增 Balanced Hard Evidence-DPO
  任务实现：默认构造 5k balanced hard evidence preference 数据，其中
  object-existence 部分严格 yes/no 平衡，并混入 Hard COCO、Base-error-mined、
  canonical COCO pairs 与 GQA anchors，目标是降低 FPR 的同时避免 FNR 上升。
- COCO Base 分数过高与 Hard COCO ceiling-effect 诊断任务已单独整理在
  `tasks/coco-hard-ceiling-diagnosis/`。
- Base-error mining 诊断评测任务已单独整理在
  `tasks/base-error-mining/`，Base-conditioned locked diagnostic set 与三组复评均已完成。
- CVPR LaTeX 稿件已更新在 `paper/`：`main.tex` 当前已从 assumed-positive 草稿改为
  使用真实结果的 controlled diagnostic study，并已纳入 10k mixed scale-up 诊断结论。
- 5k mixed preference pairs 已生成：3,500 COCO object-existence + 1,500 GQA simple attribute/relation。
- 10k mixed scale-up 诊断有独立 Slurm 链路：6,000 COCO + 4,000 GQA，不覆盖 5k
  主线数据、adapter 或评测结果，用于检查数据规模是否改变 Evidence-Hint 趋势。
  2026-05-27 链路已完成：data 64369、Evidence-Hint ZeRO-2 train 64371、
  Answer-DPO ZeRO-2 train 64397、eval jobs 64375-64377 和 64398-64400
  均为 exit 0。Answer-DPO ZeRO-3 job 64370 因 RTX4090 上过慢已取消并被
  64397（`A100,L40S,ADA6000`）替代。10k 结果未改变 Evidence-Hint 趋势：
  COCO/GQA/Hard COCO Acc 为 Answer 0.965/0.769/0.948，Evidence-Hint
  0.961/0.766/0.944；Evidence-Hint 仍降低 FPR，但 Acc/F1 未超过 Answer。
  旧尝试 64272-64282
  已取消，因为同时排除 base-error-mining 图像会让本地 COCO 子集不足 6k；64283-64291
  已取消并改为 10k 专用 Phase-2 sidecar 文件，避免覆盖并行方法改进产物；64293-64301
  已取消并改用并发 GQA/VG 下载，避免单线程下载拖慢 10k 数据准备；64321-64329
  已取消并把 GQA/VG 下载目标从 5,000 收到 4,300，保留 4,200 成功阈值。
- mixed audit 与泄漏检查已完成，审计摘要见 `data/audit/`，当前 train/eval image overlap 为 0。
- GQA simple held-out eval 已生成：`data/eval/gqa_simple_heldout.jsonl`，共 1,000 条，color 与 left/right relation 各 500 条。
- Hard COCO held-out eval 已生成：`data/eval/coco_hard_object_existence.jsonl`，共 1,000 条，yes/no 各 500 条，500 张 held-out 图像，train/eval image overlap 为 0。
- mixed Answer-DPO job 64200 已完成并写出 mixed adapter；mixed Evidence-Hint DPO 改用
  已完成的 ZeRO-2 job 64252 作为默认结果，原 ZeRO-3 job 64201 已取消。
- 由于 64201 的 ZeRO-3 run 在 RTX4090 上显存占用偏低，独立 ZeRO-2 run 64252 已完成，
  输出到 `outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo_zero2/`：训练 runtime
  950.96s、train loss 0.1347，adapter dry-run 已通过；`evidence_hint_dpo` 默认评测
  registry 已切到该 adapter。
- 5k COCO-only adapter 的三组 held-out object-existence 验证已完成：Base Acc 0.959、Answer-DPO Acc 0.961、Evidence-Hint DPO Acc 0.960。
- 统一评测脚本已支持输出变体目录和 evidence-style prompt；Base、mixed Answer-DPO 和
  mixed Evidence-Hint DPO 的 COCO/GQA normal prompt、Hard COCO 和 evidence-style prompt
  评测均已完成，summary 见 `experiments/eval_summary.md`。
- 官方 POPE/AMBER 外部评测链路已补齐：`prepare_official_external_benchmarks.py`
  可 sparse-clone 官方标注/query 并生成 POPE random/popular/adversarial 与 AMBER
  discriminative eval JSONL；`prepare_external_eval_images.slurm` 可补齐 POPE/AMBER
  图片 roots，三组外部评测已完成，summary 见 `experiments/eval_summary.md`。
- Hard COCO 的 Base 与 mixed Answer-DPO 评测 jobs 64233/64234 已完成：Base Acc 0.944，
  mixed Answer-DPO Acc 0.950；原 `afterok:64201` 依赖评测 jobs 64235-64239 和 64263
  已取消。ZeRO-2 Evidence-Hint 的 normal-prompt 评测 jobs 64255-64257 已完成：COCO Acc
  0.961、GQA Acc 0.766、Hard COCO Acc 0.946；evidence-style jobs 64258/64259 也已完成：
  COCO Acc 0.955、GQA Acc 0.767。
- Base-error mining 诊断已完成：候选池 10,000 条，Base Acc 0.9472；locked set 527 条
  Base 错误。Answer-DPO recovery 为 0.063，Evidence-Hint DPO ZeRO-2 recovery 为 0.030。
- 当前真实结论采用 Plan B：模板化 evidence hint 在 COCO/Hard COCO/GQA 上只带来很小的
  false-positive 下降，整体 Acc/F1 未稳定超过 Answer-DPO；10k mixed scale-up 已确认
  该趋势没有翻转。后续不再提交重复评测或新的规模实验，除非明确需要。

## 目录结构

```text
idea-lightweighted-grounded-preference-vlm/
  plan.md                         # 项目目标、方法与实验设计
  paper_outline_and_tasks.md       # 论文大纲与后续任务清单
  data_processing_plan.md          # 数据构造方案
  midterm_report.md                # 第一份中期进展报告
  midterm_report_2.md              # 第二份中期进展报告，含 10k/外部评测/Phase-2 收口

idea-imporve-evidence/
  phase2_method_ideas.md           # 二期 evidence 方法改进方案

tasks/
  coco-hard-ceiling-diagnosis/      # COCO/Hard COCO ceiling-effect 诊断任务
  base-error-mining/                # Base 错误样本挖掘诊断评测任务
  answer-evidence-mix-dpo/          # 70/30 Answer/Evidence mixed-format DPO rescue run
  balanced-hard-evidence-dpo/       # Balanced hard evidence preference rescue run

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
  main.tex                         # CVPR 2026 诊断型完整草稿，含真实 mixed 主结果
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

输出文件为 `paper/build/main_full.pdf`。2026-05-27 已重新验证诊断稿：普通
`make pdf` 生成 5 页 `paper/build/main.pdf`，`make full` 生成 7 页带附录
`paper/build/main_full.pdf`；仅剩官方 `lineno.sty` UTF-8 warning，无表格溢出告警。

## 数据流水线

详细命令见 `scripts/data/README.md`。核心产物是：

```text
data/processed/canonical_pairs.jsonl
data/processed/answer_dpo_train.jsonl
data/processed/evidence_hint_dpo_train.jsonl
data/processed/answer_evidence_mix_dpo_train.jsonl
data/audit/audit_200.csv
data/processed/check_report_main.json
data/eval/gqa_simple_heldout.jsonl
data/eval/coco_hard_object_existence.jsonl
```

如果需要重新生成数据，优先使用已有 Slurm 脚本或轻量 CPU 脚本；大文件建议软链接，不要直接复制进仓库。

Answer-Evidence Mix DPO 复用 `canonical_pairs_main.jsonl`，默认导出 70% plain
Answer-DPO 与 30% Evidence-Hint DPO 的混合格式：

```text
data/processed/answer_evidence_mix_dpo_train.jsonl
experiments/llamafactory_data/cvpr_answer_evidence_mix_dpo.json
```

Balanced Hard Evidence-DPO 默认在任务目录内生成派生产物，避免污染主线 5k/10k
数据注册表：

```text
tasks/balanced-hard-evidence-dpo/generated/balanced_hard_evidence_dpo_train.jsonl
tasks/balanced-hard-evidence-dpo/llamafactory_data/cvpr_balanced_hard_evidence_dpo.json
```

Phase-2 方法变体复用 `canonical_pairs_main.jsonl` 并额外导出：

```text
data/processed/phase2_evidence_only_dpo_train.jsonl
data/processed/phase2_input_side_evidence_dpo_train.jsonl
data/processed/phase2_chosen_only_evidence_dpo_train.jsonl
experiments/llamafactory_data/cvpr_phase2_evidence_only_dpo.json
experiments/llamafactory_data/cvpr_phase2_input_side_evidence_dpo.json
experiments/llamafactory_data/cvpr_phase2_chosen_only_evidence_dpo.json
```

10k mixed scale-up 的数据准备会写到独立文件，并可能通过 CPU Slurm 下载额外 GQA/VG 图像：

```bash
sbatch scripts/data/prepare_mixed_10k_scaleup.slurm
```

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

mixed Evidence-Hint DPO 默认使用 ZeRO-2。默认脚本为：

```bash
sbatch experiments/slurm/train_evidence_hint_dpo.slurm
```

mixed 主实验 adapter 默认位于：

```text
outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/
outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo_zero2/
```

显式 ZeRO-2 wrapper 仍保留为兼容入口：

```bash
sbatch experiments/slurm/train_evidence_hint_dpo_zero2.slurm
```

旧 COCO-only preliminary adapter 位于：

```text
outputs/llamafactory/qwen25vl7b_answer_dpo/
outputs/llamafactory/qwen25vl7b_evidence_hint_dpo/
```

10k mixed scale-up 通过依赖链一次性提交数据、两组 DPO 训练和 COCO/GQA/Hard COCO
normal-prompt 评测：

```bash
bash experiments/slurm/submit_mixed10k_scaleup.sh
```

10k adapter 与评测变体分别写入：

```text
outputs/llamafactory/qwen25vl7b_mixed10k_answer_dpo/
outputs/llamafactory/qwen25vl7b_mixed10k_evidence_hint_dpo_zero2/
results/eval/generations/<eval_name>/mixed10k/<model_key>.jsonl
```

2026-05-27 status: the 10k chain completed. Answer-DPO 10k was switched from
the slow ZeRO-3 job 64370 to ZeRO-2 job 64397 on `A100,L40S,ADA6000`;
Evidence-Hint used ZeRO-2 job 64371. Answer-DPO evals were jobs 64398-64400,
and Evidence-Hint evals were jobs 64375-64377. The scale-up did not flip the
trend: Evidence-Hint still trades lower false-positive rate for no Acc/F1 gain
over Answer-DPO.

Phase-2 第一轮三组方法变体通过独立 Slurm 训练脚本提交，不在交互环境直接运行：

```bash
bash experiments/slurm/submit_phase2_method_variants.sh
```

该提交脚本会为每个训练任务挂载 after-ok 评测：COCO held-out、GQA simple、Hard COCO
和 Base-error-mined diagnostic；结果写入 `OUTPUT_VARIANT=phase2`。

对应 adapter 输出为：

```text
outputs/llamafactory/qwen25vl7b_phase2_evidence_only_dpo_zero2/
outputs/llamafactory/qwen25vl7b_phase2_input_side_evidence_dpo_zero2/
outputs/llamafactory/qwen25vl7b_phase2_chosen_only_evidence_dpo_zero2/
```

2026-05-27 status: Phase-2 第一轮已完成。训练 jobs 64302-64304 均为
`COMPLETED`，评测 jobs 64305-64316 均为 `COMPLETED`。结果显示
Input-Side Evidence DPO 最接近主线 Answer-DPO，但三组都没有带来足以替换
主实验结论的稳定提升：

```text
COCO held-out Acc: Evidence-Only 0.959, Input-Side 0.961, Chosen-Only 0.961
GQA simple Acc:    Evidence-Only 0.765, Input-Side 0.768, Chosen-Only 0.765
Hard COCO Acc:     Evidence-Only 0.942, Input-Side 0.947, Chosen-Only 0.946
Base-error recovery: Evidence-Only 0.015, Input-Side 0.044, Chosen-Only 0.032
```

Answer-Evidence Mix DPO 是一个独立 rescue run，不进入当前三组主实验表。它使用
ZeRO-2 配置，训练和四个 after-ok 评测通过：

```bash
bash experiments/slurm/submit_answer_evidence_mix_dpo.sh
```

对应 adapter 与评测输出为：

```text
outputs/llamafactory/qwen25vl7b_answer_evidence_mix_dpo_zero2/
results/eval/generations/<eval_name>/answer_evidence_mix/answer_evidence_mix_dpo.jsonl
```

Balanced Hard Evidence-DPO 是另一个独立 rescue run，用于直接解决 FPR/FNR
trade-off。它先生成任务内 LLaMA-Factory 数据，再用 ZeRO-2 训练：

```bash
sbatch tasks/balanced-hard-evidence-dpo/train_balanced_hard_evidence_dpo.slurm
```

对应 adapter 与任务内 registry 为：

```text
outputs/llamafactory/qwen25vl7b_balanced_hard_evidence_dpo_zero2/
tasks/balanced-hard-evidence-dpo/llamafactory_data/dataset_info.json
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

官方 POPE/AMBER 外部 benchmark 可用轻量脚本准备标注与统一 eval JSONL：

```bash
python scripts/eval/prepare_official_external_benchmarks.py
```

输出文件为：

```text
data/eval/pope_coco_random.jsonl
data/eval/pope_coco_popular.jsonl
data/eval/pope_coco_adversarial.jsonl
data/eval/amber_discriminative.jsonl
```

该脚本只下载官方 metadata，不拉取图片。POPE 评测需要 COCO val2014 图片位于
`data/raw/coco/val2014`；AMBER 评测需要官方图片位于 `data/raw/amber/images`。
图片根目录通过 CPU Slurm 准备；AMBER 会优先尝试官方 Google Drive 包，集群无法访问
Google 时自动从 `visual-preference/AMBER` 的 HF parquet 镜像导出同名图片：

```bash
sbatch scripts/data/prepare_external_eval_images.slurm
```

确认图片就绪后，可提交三组固定模型的外部评测：

```bash
DRY_RUN=1 scripts/eval/submit_external_benchmark_evals.sh
scripts/eval/submit_external_benchmark_evals.sh
```

AMBER 含少量高分辨率图片；完整 AMBER 推理建议通过 Slurm 环境变量限制 Qwen
视觉输入分辨率，例如 `IMAGE_MAX_PIXELS=1003520`。

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

2026-05-27 mixed/evidence-style/base-error-mined 评测当前状态：

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
64201  CANCELLED  replaced by ZeRO-2 job 64252
64235  CANCELLED  old afterok:64201 COCO held-out
64236  CANCELLED  old afterok:64201 GQA simple
64237  CANCELLED  old afterok:64201 Hard COCO
64238  CANCELLED  old afterok:64201 GQA evidence-style
64239  CANCELLED  old afterok:64201 COCO evidence-style
64255  COMPLETED  mixed Evidence-Hint DPO  COCO held-out, mixed_zero2
64256  COMPLETED  mixed Evidence-Hint DPO  GQA simple, mixed_zero2
64257  COMPLETED  mixed Evidence-Hint DPO  Hard COCO, mixed_zero2
64258  COMPLETED  mixed Evidence-Hint DPO  COCO held-out, evidence_prompt_zero2
64259  COMPLETED  mixed Evidence-Hint DPO  GQA simple, evidence_prompt_zero2
64263  CANCELLED  old afterok:64201 base-error-mined eval
64251  COMPLETED  Base Instruct      base-error mining candidates, mixed
64262  COMPLETED  Base Instruct      base-error-mined locked set, mixed
64264  COMPLETED  mixed Answer-DPO   base-error-mined locked set, mixed
64267  COMPLETED  mixed Evidence-Hint DPO  base-error-mined locked set, mixed
```

当前可用的 mixed 指标：

```text
COCO held-out: Base Acc 0.959, mixed Answer-DPO Acc 0.961, ZeRO-2 Evidence-Hint Acc 0.961
GQA simple:    Base Acc 0.764, mixed Answer-DPO Acc 0.768, ZeRO-2 Evidence-Hint Acc 0.766
Hard COCO:     Base Acc 0.944, mixed Answer-DPO Acc 0.950, ZeRO-2 Evidence-Hint Acc 0.946
Evidence prompt: COCO ZeRO-2 Evidence-Hint Acc 0.955, GQA ZeRO-2 Evidence-Hint Acc 0.767
Base-error mined recovery: Answer-DPO 0.063, ZeRO-2 Evidence-Hint 0.030
```

10k mixed scale-up diagnostic:

```text
COCO held-out: Answer-DPO Acc 0.965/FPR 0.018, Evidence-Hint Acc 0.961/FPR 0.016
GQA simple:    Answer-DPO Acc 0.769/FPR 0.164, Evidence-Hint Acc 0.766/FPR 0.146
Hard COCO:     Answer-DPO Acc 0.948/FPR 0.048, Evidence-Hint Acc 0.944/FPR 0.038
Conclusion: 10k scale-up preserves the 5k pattern; Evidence-Hint lowers false positives but does not improve Acc/F1 over Answer-DPO.
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

正文采用 CVPR 2026 格式。页数按 6/7/8 页弹性控制：优先压到 6 页，7 页可接受，8 页作为正文硬上限。参考文献加可选附录部分总量不超过 10 页，附录非必须。本轮写作任务已把 `paper/main.tex` 从结果占位稿改为使用真实结果的诊断型审稿稿。

模板文件已从 `cvpr-org/author-kit` main commit
`217fe7698116978ab2d972e2369a3d1567152f34` 直接替换：`paper/cvpr.sty`、
`paper/ieeenat_fullname.bst`、`paper/preamble.tex` 和 `paper/rebuttal.tex`
均来自官方文件；`paper/main.tex` 保留本文正文，但文档头部结构按官方
`main.tex` 对齐。用于替换的临时 author-kit clone 已删除，仓库不再保留该模板子仓库。
由于当前用 Tectonic/XeTeX 编译，官方样式中的 PSNFSS Times/Helvetica 粗体在默认
TU 编码下不会自动解析，因此 `paper/local_xetex_fonts.tex` 强制使用 T1 编码，让
`T1/ptm` 和 `T1/phv` 官方 Times/Helvetica 字体族正确加载，避免论文标题和章节标题
退化成非粗体。

正文只支撑一个小而明确的诊断结论：

- 方法：不改模型结构、不改 DPO loss，只改 preference response 格式。
- 数据：5k mixed COCO/GQA preference pairs 为主实验，10k mixed scale-up 作为规模诊断；
  覆盖对象存在、简单颜色/材质属性和左右空间关系。
- 实验：Base Instruct、Answer-DPO、Evidence-Hint DPO 三组。
- 指标：COCO held-out、Hard COCO、GQA simple 的 Acc/BAcc/F1/FPR/FNR、yes/no bias、refusal/other rate、生成长度与 evidence-cue rate；10k scale-up、base-error-mined recovery 作为诊断补充；POPE/AMBER 外部 benchmark 已补入主实验汇总。
- 限制：不声称解决计数、多步关系、开放式描述或复杂 grounding。
- 结论：Evidence-Hint DPO 在 COCO/Hard COCO/GQA 上只表现出小幅 false-positive 下降；
  5k 主实验、10k scale-up 与 base-error recovery 都未显示其稳定超过 Answer-DPO，
  因此论文写成 controlled diagnostic study，而不是强正向方法论文。

论文大纲和任务清单见 `idea-lightweighted-grounded-preference-vlm/paper_outline_and_tasks.md`。
