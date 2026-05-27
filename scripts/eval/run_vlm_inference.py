#!/usr/bin/env python3
"""Run unified Qwen2.5-VL inference for base and LoRA DPO variants."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from common import ensure_parent, load_jsonl, repo_path, write_json


MODEL_REGISTRY = {
    "base": {
        "method": "Base Instruct",
        "adapter_name_or_path": None,
    },
    "answer_dpo": {
        "method": "Answer-DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_mixed_answer_dpo",
    },
    "evidence_hint_dpo": {
        "method": "Evidence-Hint DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo_zero2",
    },
    "answer_evidence_mix_dpo": {
        "method": "Answer-Evidence Mix DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_answer_evidence_mix_dpo_zero2",
    },
    "phase2_evidence_only_dpo": {
        "method": "Phase-2 Evidence-Only DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_phase2_evidence_only_dpo_zero2",
    },
    "phase2_input_side_evidence_dpo": {
        "method": "Phase-2 Input-Side Evidence DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_phase2_input_side_evidence_dpo_zero2",
    },
    "phase2_chosen_only_evidence_dpo": {
        "method": "Phase-2 Chosen-Only Evidence DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_phase2_chosen_only_evidence_dpo_zero2",
    },
    "input_side_main_balanced_hard_dpo": {
        "method": "Balanced Hard Input-Side Evidence DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_input_side_main_balanced_hard_dpo_zero2",
    },
    "cepo_answer_dpo": {
        "method": "CEPO Answer-DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2",
    },
    "cepo_latent_dpo": {
        "method": "CEPO-Latent DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_cepo_latent_dpo_zero2",
    },
    "cepo_dual_dpo": {
        "method": "CEPO-Dual DPO",
        "adapter_name_or_path": "outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-key", choices=sorted(MODEL_REGISTRY), required=True)
    parser.add_argument("--eval", required=True, help="Normalized eval JSONL.")
    parser.add_argument("--output", default=None, help="Raw generation JSONL.")
    parser.add_argument("--metadata-output", default=None)
    parser.add_argument(
        "--model-name-or-path",
        default="models/Qwen2.5-VL-7B-Instruct",
        help="Base Qwen2.5-VL model path.",
    )
    parser.add_argument(
        "--adapter-name-or-path",
        default=None,
        help="Override adapter path. Use 'none' only for the base model.",
    )
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--image-min-pixels", type=int, default=None)
    parser.add_argument("--image-max-pixels", type=int, default=None)
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--torch-dtype", default="bfloat16", choices=("auto", "float16", "bfloat16", "float32"))
    parser.add_argument(
        "--instruction-suffix",
        default="Answer with a short yes/no sentence only.",
        help="Suffix appended to every evaluation question.",
    )
    parser.add_argument(
        "--allow-missing-images",
        action="store_true",
        help="Do not fail during setup if image paths are missing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files, adapter wiring, and output paths without loading the model.",
    )
    args = parser.parse_args()

    eval_path = repo_path(args.eval)
    model_path = repo_path(args.model_name_or_path)
    if not eval_path.exists():
        print(f"Missing eval JSONL: {eval_path}", file=sys.stderr)
        return 2
    if not model_path.exists():
        print(f"Missing base model path: {model_path}", file=sys.stderr)
        return 2

    adapter_path = resolve_adapter_path(args.model_key, args.adapter_name_or_path)
    adapter_status = validate_adapter(args.model_key, adapter_path)
    if adapter_status["status"] == "error":
        print(adapter_status["message"], file=sys.stderr)
        return 2

    records = load_jsonl(eval_path)
    if args.max_samples is not None:
        records = records[: args.max_samples]
    missing_images = [
        str(repo_path(record["image"]))
        for record in records
        if record.get("image") and not repo_path(record["image"]).exists()
    ]
    if missing_images and not args.allow_missing_images:
        print(
            f"Missing {len(missing_images)} eval images; first missing image: {missing_images[0]}",
            file=sys.stderr,
        )
        return 2

    output_path = repo_path(args.output or default_output_path(args.model_key, eval_path))
    metadata_path = repo_path(args.metadata_output or output_path.with_suffix(".metadata.json"))
    metadata = build_metadata(args, eval_path, output_path, model_path, adapter_path, adapter_status, len(records))

    if args.dry_run:
        ensure_parent(output_path)
        write_json(metadata_path, metadata)
        print(f"Dry run OK for {args.model_key}: {len(records)} eval rows.")
        print(f"Adapter status: {adapter_status['status']}")
        print(f"Raw generations will be written to {output_path}")
        print(f"Metadata written to {metadata_path}")
        return 0

    model, processor = load_model_and_processor(args, model_path, adapter_path)
    ensure_parent(output_path)
    with output_path.open("w", encoding="utf-8") as f:
        for idx, record in enumerate(records, start=1):
            generation = generate_one(model, processor, record, args)
            out = dict(record)
            out["model_key"] = args.model_key
            out["method"] = MODEL_REGISTRY[args.model_key]["method"]
            out["prompt"] = build_prompt(record["question"], args.instruction_suffix)
            out["generation"] = generation
            out["generation_index"] = idx
            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    metadata["finished_at"] = now_iso()
    write_json(metadata_path, metadata)
    print(f"Wrote raw generations to {output_path}")
    print(f"Wrote metadata to {metadata_path}")
    return 0


def resolve_adapter_path(model_key: str, override: str | None) -> str | None:
    if override == "none":
        return None
    if override:
        return override
    return MODEL_REGISTRY[model_key]["adapter_name_or_path"]


def validate_adapter(model_key: str, adapter_path: str | None) -> dict[str, str]:
    if model_key == "base":
        if adapter_path:
            return {"status": "error", "message": "Base model must not receive a LoRA adapter."}
        return {"status": "not_applicable", "message": "Base model uses no adapter."}
    if not adapter_path:
        return {
            "status": "error",
            "message": f"{model_key} requires adapter_name_or_path; refusing to run base-only evaluation.",
        }
    full_path = repo_path(adapter_path)
    required = ("adapter_config.json", "adapter_model.safetensors")
    missing = [name for name in required if not (full_path / name).exists()]
    if missing:
        return {
            "status": "error",
            "message": f"{model_key} adapter is incomplete at {full_path}; missing {missing}.",
        }
    return {"status": "ready", "message": f"Adapter ready at {full_path}."}


def load_model_and_processor(args: argparse.Namespace, model_path: Any, adapter_path: str | None) -> tuple[Any, Any]:
    import torch
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    dtype = {
        "auto": "auto",
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }[args.torch_dtype]
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        str(model_path),
        torch_dtype=dtype,
        device_map=args.device_map,
        trust_remote_code=True,
    )
    if adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, str(repo_path(adapter_path)), is_trainable=False)
        if not getattr(model, "peft_config", None):
            raise RuntimeError("LoRA adapter did not attach; refusing to continue.")
    processor = AutoProcessor.from_pretrained(str(model_path), trust_remote_code=True)
    model.eval()
    return model, processor


def generate_one(model: Any, processor: Any, record: dict[str, Any], args: argparse.Namespace) -> str:
    import torch
    from qwen_vl_utils import process_vision_info

    image_path = str(repo_path(record["image"]))
    image_content: dict[str, Any] = {"type": "image", "image": image_path}
    if args.image_min_pixels is not None:
        image_content["min_pixels"] = args.image_min_pixels
    if args.image_max_pixels is not None:
        image_content["max_pixels"] = args.image_max_pixels
    messages = [
        {
            "role": "user",
            "content": [
                image_content,
                {"type": "text", "text": build_prompt(record["question"], args.instruction_suffix)},
            ],
        }
    ]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to(model.device)
    generation_kwargs = {
        "max_new_tokens": args.max_new_tokens,
        "do_sample": args.temperature > 0,
        "temperature": args.temperature if args.temperature > 0 else None,
        "top_p": args.top_p,
    }
    generation_kwargs = {key: value for key, value in generation_kwargs.items() if value is not None}
    with torch.inference_mode():
        generated_ids = model.generate(**inputs, **generation_kwargs)
    trimmed = [
        output_ids[len(input_ids) :]
        for input_ids, output_ids in zip(inputs.input_ids, generated_ids, strict=True)
    ]
    return processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()


def build_prompt(question: str, suffix: str) -> str:
    question = str(question).strip()
    suffix = str(suffix or "").strip()
    return f"{question}\n{suffix}" if suffix else question


def default_output_path(model_key: str, eval_path: Any) -> str:
    eval_name = repo_path(eval_path).stem
    return f"results/eval/generations/{eval_name}/{model_key}.jsonl"


def build_metadata(
    args: argparse.Namespace,
    eval_path: Any,
    output_path: Any,
    model_path: Any,
    adapter_path: str | None,
    adapter_status: dict[str, str],
    num_records: int,
) -> dict[str, Any]:
    return {
        "created_at": now_iso(),
        "model_key": args.model_key,
        "method": MODEL_REGISTRY[args.model_key]["method"],
        "model_name_or_path": str(model_path),
        "adapter_name_or_path": str(repo_path(adapter_path)) if adapter_path else None,
        "adapter_status": adapter_status,
        "eval_file": str(eval_path),
        "output_file": str(output_path),
        "num_records": num_records,
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "image_min_pixels": args.image_min_pixels,
        "image_max_pixels": args.image_max_pixels,
        "instruction_suffix": args.instruction_suffix,
        "dry_run": args.dry_run,
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
