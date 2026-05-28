# V1 收尾与可复用资产清单

更新日期：2026-05-27

## 0. 用途

V1 的结论已经归档到 `v1/`。本文件只回答一个问题：哪些内容值得从旧项目里拿出来，作为下一版 claim-level evidence preference 项目的起点。

核心判断：

> 旧项目的 template evidence hint 不适合作为主方法继续加码，但它留下了很有价值的数据、训练、评测和诊断基础。下一版应复用基础设施，替换研究问题。

## 1. 直接复用的资产

### 1.1 数据流水线

可继续复用：

```text
scripts/data/
  common.py
  01_build_coco_object_pairs.py
  02_build_gqa_simple_pairs.py
  03_merge_and_split_pairs.py
  04_export_dpo_formats.py
  05_make_audit_sheet.py
  06_check_data_leakage.py
  07_clean_and_balance_pairs.py
  09_prepare_eval_image_ids.py
  10_download_gqa_vg_images.py
```

值得保留的设计：

- `canonical_pairs_main.jsonl` 先对齐语义，再导出不同训练格式。
- 所有训练组共享同一批图像、问题、chosen/rejected 语义，减少方法外变量。
- `image_id` 级 train/eval overlap 检查必须保留。
- 审计表按 source/task type 分层抽样，适合扩展到 claim/evidence 审计。

下一版需要新增的只是 claim-evidence 字段，而不是推翻整个数据流水线。

### 1.2 评测流水线

可继续复用：

```text
scripts/eval/
  run_vlm_inference.py
  score_object_eval.py
  prepare_coco_heldout_eval.py
  prepare_coco_hard_eval.py
  prepare_gqa_simple_heldout_eval.py
  prepare_official_external_benchmarks.py
  submit_external_benchmark_evals.sh
```

当前已经准备好的 eval 资产：

```text
data/eval/coco_heldout_object_existence.jsonl
data/eval/gqa_simple_heldout.jsonl
data/eval/coco_hard_object_existence.jsonl
data/eval/base_error_mined_object_existence.jsonl
data/eval/pope_coco_random.jsonl
data/eval/pope_coco_popular.jsonl
data/eval/pope_coco_adversarial.jsonl
data/eval/amber_discriminative.jsonl
```

下一版仍应保留 Acc、BAcc、F1、FPR、FNR、yes rate、other rate。V1 证明了只看 Acc 会掩盖重要的 FPR/FNR trade-off。

### 1.3 训练与 Slurm 基础设施

可继续复用：

```text
LLaMA-Factory/
experiments/llamafactory_configs/
experiments/slurm/
experiments/README.md
experiments/training_summary.md
```

经验结论：

- Qwen2.5-VL-7B + LoRA-DPO + ZeRO-2 是当前最稳妥的 7B 路线。
- Evidence-Hint 的 ZeRO-3 在 RTX4090 上过慢，后续优先 ZeRO-2。
- 训练和完整评测都应通过 Slurm；交互环境只做轻量数据检查、dry-run 和文档整理。

### 1.4 论文与写作资产

可继续复用：

```text
paper/
  main.tex
  main_full.tex
  appendix.tex
  preamble.tex
  cvpr.sty
  references.bib
  Makefile
```

值得保留的写作经验：

- 主实验不要超过三组。
- 正文控制在 6 页以内。
- 负结果也可以成立，但叙事必须是 controlled diagnostic study。
- 表格必须同时报告 FPR/FNR，不能只放 accuracy。

## 2. 可以作为负面证据继续引用的结论

这些不是下一版主方法，但很适合放到动机或预实验里：

| V1 发现 | 对 V2 的启发 |
| --- | --- |
| Response-side template hint 没有稳定超过 Answer-DPO。 | 需要更强的 claim-evidence 绑定，而不是继续改模板语气。 |
| 10k scale-up 没有翻转趋势。 | 问题不是单纯数据量不够。 |
| Input-Side Evidence 是 Phase-2 最稳变体但仍偏弱。 | evidence placement 有影响，但 template cue 强度不足。 |
| Balanced Hard Input-Side 提升 recovery 但提高 FPR。 | hard data 有用，但需要显式控制 false-positive evidence。 |
| Base-error-mined set 上 evidence hint recovery 弱。 | 新方法必须测试是否真的修复 base model 已犯的错误。 |

## 3. 不建议继续投入的旧方向

不建议作为下一阶段主线：

- 继续跑 response-side Evidence-Hint 的比例搜索，例如 10%、15%、20%、50%。
- 只改 `Evidence hint:` 的文本格式，例如 check-step、chosen-only、evidence-only。
- 再做同类 10k/20k scale-up。
- 把 Balanced Hard Input-Side 直接包装成强主方法。
- 只在 COCO/GQA yes/no 上展示小数点级提升。

这些方向可以留作 appendix 或 internal ablation，但不应成为新项目核心。

## 4. 下一版必须补上的能力

V2 应该把 evidence 从“回答风格”推进到“可验证对象”：

- 每个视觉断言都有 claim type：object、attribute、relation。
- 每个 claim 绑定 evidence：object label、box、attribute value、relation edge。
- 负样本不仅答案错，还包括 answer correct but evidence wrong。
- 评测不仅问 answer correctness，也测 evidence correctness。
- 数据质量先审计，再训练；高质量小数据优先于低质量大数据。

这就是新方向 `idea-evidence-grounded-preference-vlm/` 的出发点。
