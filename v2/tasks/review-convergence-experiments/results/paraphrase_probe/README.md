# Paraphrased CEPO-Probe Results

This directory stores the template-robustness check requested after the
2026-05-30 review. The probe reuses the locked CEPO supported and
wrong-evidence rows, images, and labels, but rewrites the prompt and candidate
evidence wording.

Purpose:

- test whether CEPO-Dual-2k still improves wrong-evidence rejection when the
  probe is not phrased exactly like the training/evaluation template;
- avoid new label noise by preserving the original target fields;
- keep the check inference-only through Slurm.

Canonical commands:

```bash
python scripts/eval/prepare_cepo_paraphrase_probe.py
bash experiments/slurm/submit_cepo_paraphrase_probe_eval.sh
python scripts/eval/summarize_cepo_paraphrase_probe_results.py
```

Expected generated eval files:

```text
data/eval/cepo_evidence_probe_paraphrase.jsonl
data/eval/cepo_wrong_evidence_probe_paraphrase.jsonl
data/eval/cepo_paraphrase_probe.summary.json
```

Required rows in `metrics.csv`:

- Base Instruct;
- CEPO Answer-DPO;
- CEPO-Dual-2k.

Heavy inference must be submitted through Slurm.

Completed run:

- Slurm jobs 64741--64746 completed with exit code 0.
- Base / CEPO Answer-DPO / CEPO-Dual-2k supported accuracy:
  86.0 / 90.0 / 90.0.
- Base / CEPO Answer-DPO / CEPO-Dual-2k wrong-evidence rejection:
  65.8 / 61.8 / 73.2.
- CEPO-Dual-2k keeps a +11.5 point wrong-evidence rejection advantage over
  CEPO Answer-DPO under row-preserving paraphrased wording, with 0.0 parse
  failures.
