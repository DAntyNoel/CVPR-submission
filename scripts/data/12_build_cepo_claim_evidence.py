#!/usr/bin/env python3
"""Build CEPO claim-evidence preference data and DPO exports."""

from __future__ import annotations

import argparse
import copy
import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import (
    article_phrase,
    be_verb,
    clean_name,
    ensure_parent,
    load_image_id_set,
    load_json,
    load_jsonl,
    repo_path,
    repo_relative,
    summarize_records,
    weighted_choice,
    write_json,
    write_jsonl,
)


COLORS = [
    "black",
    "blue",
    "brown",
    "gray",
    "green",
    "orange",
    "pink",
    "purple",
    "red",
    "white",
    "yellow",
]

COLOR_ALIASES = {"grey": "gray", "silver": "gray"}

MATERIALS = [
    "brick",
    "ceramic",
    "cloth",
    "fabric",
    "glass",
    "leather",
    "metal",
    "paper",
    "plastic",
    "rubber",
    "stone",
    "wooden",
]

CONFUSABLE_ATTRS = {
    ("gray", "white"),
    ("gray", "black"),
    ("white", "gray"),
    ("white", "yellow"),
    ("brown", "orange"),
    ("orange", "brown"),
}

RELATION_FLIPS = {"left": "right", "right": "left"}

DEFAULT_EVAL_IMAGE_ID_FILES = [
    "data/eval/coco_heldout_object_existence.jsonl",
    "data/eval/coco_hard_object_existence.jsonl",
    "data/eval/base_error_mined_object_existence.jsonl",
    "data/eval/gqa_simple_heldout.jsonl",
    "data/eval/pope_coco_random.jsonl",
    "data/eval/pope_coco_popular.jsonl",
    "data/eval/pope_coco_adversarial.jsonl",
    "data/eval/amber_discriminative.jsonl",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coco-canonical", default="data/processed/canonical_coco_main.jsonl")
    parser.add_argument("--coco-instances", default="data/raw/coco/annotations/instances_train2017.json")
    parser.add_argument("--gqa-scene-graphs", default="data/raw/gqa/train_sceneGraphs.json")
    parser.add_argument("--gqa-image-root", default="data/raw/gqa/images")
    parser.add_argument("--output-dir", default="data/processed/cepo")
    parser.add_argument("--coco-object-count", type=int, default=2000)
    parser.add_argument("--gqa-attribute-count", type=int, default=1500)
    parser.add_argument("--gqa-relation-count", type=int, default=1500)
    parser.add_argument("--wrong-evidence-count", type=int, default=1000)
    parser.add_argument("--audit-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-pairs-per-gqa-image", type=int, default=2)
    parser.add_argument("--eval-image-ids", nargs="*", default=DEFAULT_EVAL_IMAGE_ID_FILES)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    output_dir = repo_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    eval_ids = load_image_id_set(args.eval_image_ids)
    coco_records = build_coco_records(args, eval_ids, rng)
    gqa_attr_records, gqa_rel_records = build_gqa_records(args, eval_ids, rng)
    base_records = coco_records + gqa_attr_records + gqa_rel_records
    wrong_records = build_wrong_evidence_records(base_records, args.wrong_evidence_count, rng)

    records = base_records + wrong_records
    rng.shuffle(records)

    canonical_path = output_dir / "claim_evidence_canonical.jsonl"
    answer_path = output_dir / "answer_dpo_train.jsonl"
    cepo_path = output_dir / "cepo_latent_dpo_train.jsonl"
    audit_path = output_dir / "claim_evidence_audit_200.csv"
    summary_path = output_dir / "claim_evidence_summary.json"
    leakage_path = output_dir / "leakage_report.json"

    write_jsonl(canonical_path, records)
    write_jsonl(answer_path, [export_answer_dpo(record) for record in records])
    write_jsonl(cepo_path, [export_cepo_latent_dpo(record) for record in records])
    write_audit_csv(audit_path, records, args.audit_size, rng)

    leakage = leakage_report(records, eval_ids, args.eval_image_ids)
    summary = build_summary(records, leakage)
    write_json(summary_path, summary)
    write_json(leakage_path, leakage)

    print(f"Wrote {len(records)} CEPO canonical records to {canonical_path}")
    print(f"Wrote Answer-DPO export to {answer_path}")
    print(f"Wrote CEPO-Latent export to {cepo_path}")
    print(f"Wrote audit sheet to {audit_path}")
    print(f"Wrote summary to {summary_path}")
    print(f"Wrote leakage report to {leakage_path}")
    return 0 if not leakage["overlap_count"] else 1


def build_coco_records(args: argparse.Namespace, eval_ids: set[str], rng: random.Random) -> list[dict[str, Any]]:
    canonical = load_jsonl(args.coco_canonical)
    instances = load_json(args.coco_instances)
    box_index = build_coco_box_index(instances)
    rng.shuffle(canonical)

    selected: list[dict[str, Any]] = []
    for row in canonical:
        image_id = str(row.get("image_id") or "")
        if image_id in eval_ids:
            continue
        label = row.get("label") or {}
        pos = clean_name(label.get("positive_object"))
        neg = clean_name(label.get("negative_object"))
        if not pos or not neg:
            continue
        boxes = box_index.get(image_id) or {}
        pos_box = boxes.get(pos)
        if not pos_box:
            continue
        record = make_coco_record(row, pos, neg, pos_box, boxes)
        selected.append(record)
        if len(selected) >= args.coco_object_count:
            break

    if len(selected) < args.coco_object_count:
        raise RuntimeError(f"Only built {len(selected)} COCO object records; requested {args.coco_object_count}.")
    return assign_ids(selected, "cepo_coco_obj")


def build_coco_box_index(instances: dict[str, Any]) -> dict[str, dict[str, list[float]]]:
    categories = {int(cat["id"]): clean_name(cat["name"]) for cat in instances.get("categories", [])}
    images = {int(img["id"]): img for img in instances.get("images", [])}
    best: dict[str, dict[str, tuple[float, list[float]]]] = defaultdict(dict)
    for ann in instances.get("annotations", []):
        if int(ann.get("iscrowd", 0)) == 1:
            continue
        image = images.get(int(ann.get("image_id", -1)))
        label = categories.get(int(ann.get("category_id", -1)))
        if not image or not label:
            continue
        width = float(image.get("width") or 0)
        height = float(image.get("height") or 0)
        if width <= 0 or height <= 0:
            continue
        box = normalize_xywh_box(ann.get("bbox"), width, height)
        if not box:
            continue
        area = float(ann.get("area") or 0.0)
        image_id = f"coco_train2017_{Path(image.get('file_name') or '').stem}"
        old = best[image_id].get(label)
        if old is None or area > old[0]:
            best[image_id][label] = (area, box)
    return {image_id: {label: pair[1] for label, pair in labels.items()} for image_id, labels in best.items()}


def make_coco_record(
    row: dict[str, Any],
    pos: str,
    neg: str,
    pos_box: list[float],
    boxes: dict[str, list[float]],
) -> dict[str, Any]:
    evidence_pool = [{"label": label, "box": box} for label, box in sorted(boxes.items()) if label != pos]
    return {
        "id": row["id"],
        "source": "coco",
        "image": row["image"],
        "image_id": row["image_id"],
        "task_type": "object_existence",
        "base_task_type": "object_existence",
        "question": row["question"],
        "chosen_answer": row["chosen_answer"],
        "rejected_answer": row["rejected_answer"],
        "answer_dpo_rejected_answer": row["rejected_answer"],
        "chosen_claims": [
            claim(
                span=f"{pos} visible",
                claim_type="object",
                support="supported",
                evidence=[{"role": "target", "label": pos, "box": pos_box}],
            )
        ],
        "rejected_claims": [
            claim(
                span=f"{neg} visible",
                claim_type="object",
                support="contradicted",
                evidence=[{"role": "target", "label": neg, "box": None}],
            )
        ],
        "negative_type": "answer_wrong",
        "label": {
            "positive_object": pos,
            "negative_object": neg,
            "visible_objects": sorted(boxes),
        },
        "evidence_pool": evidence_pool,
    }


def build_gqa_records(
    args: argparse.Namespace,
    eval_ids: set[str],
    rng: random.Random,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scene_graphs = load_json(args.gqa_scene_graphs)
    image_root = repo_path(args.gqa_image_root)
    attr_candidates: list[dict[str, Any]] = []
    rel_candidates: list[dict[str, Any]] = []

    for raw_image_id, graph in scene_graphs.items():
        image_id = f"gqa_train_{raw_image_id}"
        if image_id in eval_ids or str(raw_image_id) in eval_ids:
            continue
        image_path = find_gqa_image(image_root, str(raw_image_id))
        if not image_path:
            continue
        width = float(graph.get("width") or 0)
        height = float(graph.get("height") or 0)
        if width <= 0 or height <= 0:
            continue

        objects = normalize_gqa_objects(graph.get("objects") or {}, width, height)
        object_pool = [
            {"label": obj["name"], "box": obj["box"]}
            for obj in objects.values()
            if obj.get("name") and obj.get("box")
        ]

        for object_id, obj in objects.items():
            for attr_type, attr_value in iter_simple_attributes(obj.get("attributes", [])):
                attr_candidates.append(
                    {
                        "image": image_path,
                        "image_id": image_id,
                        "object_id": object_id,
                        "object": obj["name"],
                        "box": obj["box"],
                        "attribute_type": attr_type,
                        "attribute": attr_value,
                        "object_pool": object_pool,
                    }
                )
            for relation in obj.get("relations", []):
                rel = normalize_relation(relation.get("name"))
                if rel not in RELATION_FLIPS:
                    continue
                target_id = str(relation.get("object") or "")
                target = objects.get(target_id)
                if not target or not relation_matches_box(rel, obj["box"], target["box"]):
                    continue
                rel_candidates.append(
                    {
                        "image": image_path,
                        "image_id": image_id,
                        "subject_id": object_id,
                        "subject": obj["name"],
                        "subject_box": obj["box"],
                        "object_id": target_id,
                        "object": target["name"],
                        "object_box": target["box"],
                        "relation": rel,
                    }
                )

    rng.shuffle(attr_candidates)
    rng.shuffle(rel_candidates)
    per_image_counts: dict[str, int] = defaultdict(int)
    attr_records = take_gqa_candidates(
        attr_candidates,
        args.gqa_attribute_count,
        per_image_counts,
        args.max_pairs_per_gqa_image,
        make_gqa_attribute_record,
        rng,
    )
    rel_records = take_gqa_candidates(
        rel_candidates,
        args.gqa_relation_count,
        per_image_counts,
        args.max_pairs_per_gqa_image,
        make_gqa_relation_record,
        rng,
    )
    if len(attr_records) < args.gqa_attribute_count:
        raise RuntimeError(f"Only built {len(attr_records)} GQA attribute records; requested {args.gqa_attribute_count}.")
    if len(rel_records) < args.gqa_relation_count:
        raise RuntimeError(f"Only built {len(rel_records)} GQA relation records; requested {args.gqa_relation_count}.")
    return assign_ids(attr_records, "cepo_gqa_attr"), assign_ids(rel_records, "cepo_gqa_rel")


def find_gqa_image(image_root: Path, image_id: str) -> str | None:
    for suffix in (".jpg", ".jpeg", ".png"):
        path = image_root / f"{image_id}{suffix}"
        if path.exists():
            return repo_relative(path)
    return None


def normalize_gqa_objects(objects: dict[str, Any], width: float, height: float) -> dict[str, dict[str, Any]]:
    out = {}
    for object_id, obj in objects.items():
        name = clean_name(obj.get("name"))
        box = normalize_xywh_box([obj.get("x"), obj.get("y"), obj.get("w"), obj.get("h")], width, height)
        if not name or not box:
            continue
        out[str(object_id)] = {
            "name": name,
            "box": box,
            "attributes": obj.get("attributes") or [],
            "relations": obj.get("relations") or [],
        }
    return out


def iter_simple_attributes(attributes: list[Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_attr in attributes:
        attr = COLOR_ALIASES.get(clean_name(raw_attr), clean_name(raw_attr))
        if attr in COLORS:
            key = ("color", attr)
        elif attr in MATERIALS:
            key = ("material", attr)
        else:
            continue
        if key not in seen:
            out.append(key)
            seen.add(key)
    return out


def normalize_relation(name: Any) -> str | None:
    rel = clean_name(name)
    if rel in {"left", "left of", "to the left of"} or "left of" in rel:
        return "left"
    if rel in {"right", "right of", "to the right of"} or "right of" in rel:
        return "right"
    return None


def relation_matches_box(relation: str, subject_box: list[float], object_box: list[float]) -> bool:
    subject_center = (subject_box[0] + subject_box[2]) / 2
    object_center = (object_box[0] + object_box[2]) / 2
    margin = 0.02
    if relation == "left":
        return subject_center + margin < object_center
    if relation == "right":
        return subject_center > object_center + margin
    return False


def take_gqa_candidates(
    candidates: list[dict[str, Any]],
    desired: int,
    per_image_counts: dict[str, int],
    max_pairs_per_image: int,
    factory: Any,
    rng: random.Random,
) -> list[dict[str, Any]]:
    records = []
    seen = set()
    for candidate in candidates:
        if len(records) >= desired:
            break
        image_id = candidate["image_id"]
        if per_image_counts[image_id] >= max_pairs_per_image:
            continue
        key = tuple((k, str(v)) for k, v in sorted(candidate.items()) if k != "object_pool")
        if key in seen:
            continue
        record = factory(candidate, rng)
        if not record:
            continue
        records.append(record)
        seen.add(key)
        per_image_counts[image_id] += 1
    return records


def make_gqa_attribute_record(candidate: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    attr_type = candidate["attribute_type"]
    pos_attr = candidate["attribute"]
    vocab = COLORS if attr_type == "color" else MATERIALS
    neg_attr = choose_negative_attribute(pos_attr, vocab, rng)
    obj = candidate["object"]
    verb = be_verb(obj)
    task_type = f"attribute_{attr_type}"
    question = f"What color is the {obj}?" if attr_type == "color" else f"What material is the {obj}?"
    evidence = [{"role": "target", "label": obj, "box": candidate["box"]}]
    evidence_pool = [item for item in candidate["object_pool"] if item["label"] != obj]
    return {
        "id": "",
        "source": "gqa",
        "image": candidate["image"],
        "image_id": candidate["image_id"],
        "task_type": task_type,
        "base_task_type": task_type,
        "question": question,
        "chosen_answer": f"The {obj} {verb} {pos_attr}.",
        "rejected_answer": f"The {obj} {verb} {neg_attr}.",
        "answer_dpo_rejected_answer": f"The {obj} {verb} {neg_attr}.",
        "chosen_claims": [
            claim(
                span=f"{obj} is {pos_attr}",
                claim_type="attribute",
                support="supported",
                evidence=copy.deepcopy(evidence),
                attribute=pos_attr,
            )
        ],
        "rejected_claims": [
            claim(
                span=f"{obj} is {neg_attr}",
                claim_type="attribute",
                support="contradicted",
                evidence=copy.deepcopy(evidence),
                attribute=neg_attr,
            )
        ],
        "negative_type": "attribute_mismatch",
        "label": {
            "object": obj,
            "attribute_type": attr_type,
            "positive_attribute": pos_attr,
            "negative_attribute": neg_attr,
        },
        "evidence_pool": evidence_pool,
    }


def make_gqa_relation_record(candidate: dict[str, Any], rng: random.Random) -> dict[str, Any] | None:
    relation = candidate["relation"]
    negative_relation = RELATION_FLIPS.get(relation)
    if not negative_relation:
        return None
    subject = candidate["subject"]
    obj = candidate["object"]
    relation_phrase = relation_answer_phrase(relation, obj)
    negative_phrase = relation_answer_phrase(negative_relation, obj)
    evidence = [
        {"role": "subject", "label": subject, "box": candidate["subject_box"]},
        {"role": "object", "label": obj, "box": candidate["object_box"]},
    ]
    return {
        "id": "",
        "source": "gqa",
        "image": candidate["image"],
        "image_id": candidate["image_id"],
        "task_type": "relation_spatial",
        "base_task_type": "relation_spatial",
        "question": f"Is the {subject} {relation_phrase}?",
        "chosen_answer": f"Yes, the {subject} is {relation_phrase}.",
        "rejected_answer": f"No, the {subject} is {negative_phrase}.",
        "answer_dpo_rejected_answer": f"No, the {subject} is {negative_phrase}.",
        "chosen_claims": [
            claim(
                span=f"{subject} {relation}_of {obj}",
                claim_type="relation",
                support="supported",
                evidence=copy.deepcopy(evidence),
                relation=f"{relation}_of",
            )
        ],
        "rejected_claims": [
            claim(
                span=f"{subject} {negative_relation}_of {obj}",
                claim_type="relation",
                support="contradicted",
                evidence=copy.deepcopy(evidence),
                relation=f"{negative_relation}_of",
            )
        ],
        "negative_type": "relation_reversal",
        "label": {
            "subject": subject,
            "object": obj,
            "relation": relation,
            "negative_relation": negative_relation,
        },
    }


def choose_negative_attribute(pos_attr: str, vocab: list[str], rng: random.Random) -> str:
    candidates = [attr for attr in vocab if attr != pos_attr]
    weights = []
    for attr in candidates:
        weight = 1.0
        if (pos_attr, attr) in CONFUSABLE_ATTRS:
            weight *= 0.35
        weights.append(weight)
    return weighted_choice(candidates, weights, rng)


def relation_answer_phrase(relation: str, obj: str) -> str:
    return f"to the {relation} of the {obj}"


def build_wrong_evidence_records(
    source_records: list[dict[str, Any]],
    desired: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    candidates = list(source_records)
    rng.shuffle(candidates)
    out: list[dict[str, Any]] = []
    for source in candidates:
        record = make_wrong_evidence_record(source, rng)
        if record is None:
            continue
        out.append(record)
        if len(out) >= desired:
            break
    if len(out) < desired:
        raise RuntimeError(f"Only built {len(out)} wrong-evidence records; requested {desired}.")
    return assign_ids(out, "cepo_wrong_ev")


def make_wrong_evidence_record(source: dict[str, Any], rng: random.Random) -> dict[str, Any] | None:
    chosen_claim = copy.deepcopy(source["chosen_claims"][0])
    rejected_claim = copy.deepcopy(chosen_claim)
    rejected_claim["support"] = "wrong_evidence"
    rejected_claim["wrong_evidence_source"] = source["id"]

    claim_type = chosen_claim["type"]
    if claim_type in {"object", "attribute"}:
        pool = source.get("evidence_pool") or []
        if not pool:
            return None
        wrong = rng.choice(pool)
        rejected_claim["evidence"] = [{"role": "target", "label": wrong["label"], "box": wrong["box"]}]
    elif claim_type == "relation":
        evidence = chosen_claim.get("evidence") or []
        if len(evidence) < 2:
            return None
        subject = copy.deepcopy(evidence[0])
        obj = copy.deepcopy(evidence[1])
        subject["role"], obj["role"] = "object", "subject"
        rejected_claim["evidence"] = [obj, subject]
    else:
        return None

    return {
        "id": "",
        "source": source["source"],
        "image": source["image"],
        "image_id": source["image_id"],
        "task_type": "wrong_evidence",
        "base_task_type": source["task_type"],
        "question": source["question"],
        "chosen_answer": source["chosen_answer"],
        "rejected_answer": source["chosen_answer"],
        "answer_dpo_rejected_answer": source["answer_dpo_rejected_answer"],
        "chosen_claims": [chosen_claim],
        "rejected_claims": [rejected_claim],
        "negative_type": "evidence_wrong",
        "label": {
            **(source.get("label") or {}),
            "source_record_id": source["id"],
            "source_task_type": source["task_type"],
        },
    }


def claim(
    span: str,
    claim_type: str,
    support: str,
    evidence: list[dict[str, Any]],
    attribute: str | None = None,
    relation: str | None = None,
) -> dict[str, Any]:
    return {
        "span": span,
        "type": claim_type,
        "support": support,
        "evidence": evidence,
        "attribute": attribute,
        "relation": relation,
    }


def normalize_xywh_box(raw_box: Any, width: float, height: float) -> list[float] | None:
    if not isinstance(raw_box, (list, tuple)) or len(raw_box) < 4:
        return None
    try:
        x, y, w, h = [float(v) for v in raw_box[:4]]
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    x1 = max(0.0, min(1.0, x / width))
    y1 = max(0.0, min(1.0, y / height))
    x2 = max(0.0, min(1.0, (x + w) / width))
    y2 = max(0.0, min(1.0, (y + h) / height))
    if x2 <= x1 or y2 <= y1:
        return None
    return [round(v, 4) for v in (x1, y1, x2, y2)]


def assign_ids(records: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    for idx, record in enumerate(records, start=1):
        record["id"] = f"{prefix}_{idx:06d}"
    return records


def export_answer_dpo(record: dict[str, Any]) -> dict[str, Any]:
    rejected = record.get("answer_dpo_rejected_answer") or record.get("rejected_answer")
    return {
        "id": record["id"],
        "image": record["image"],
        "prompt": prompt(record),
        "chosen": record["chosen_answer"],
        "rejected": rejected,
        "source": record.get("source"),
        "task_type": record.get("task_type"),
        "negative_type": record.get("negative_type"),
    }


def export_cepo_latent_dpo(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "image": record["image"],
        "prompt": prompt(record),
        "chosen": format_claim_response(record["chosen_answer"], record["chosen_claims"]),
        "rejected": format_claim_response(record["rejected_answer"], record["rejected_claims"]),
        "source": record.get("source"),
        "task_type": record.get("task_type"),
        "negative_type": record.get("negative_type"),
    }


def prompt(record: dict[str, Any]) -> str:
    return "\n".join(["<image>", f"Question: {record['question']}", "Answer:"])


def format_claim_response(answer: str, claims: list[dict[str, Any]]) -> str:
    lines = [f"Answer: {answer}", "Claims:"]
    for one in claims:
        lines.extend(
            [
                f"- type: {one['type']}",
                f"  claim: {one['span']}",
                f"  evidence: {compact_evidence(one)}",
                f"  support: {one['support']}",
            ]
        )
    return "\n".join(lines)


def compact_evidence(one: dict[str, Any]) -> str:
    evidence = one.get("evidence") or []
    if one.get("type") == "relation":
        subject = next((item["label"] for item in evidence if item.get("role") == "subject"), "unknown")
        obj = next((item["label"] for item in evidence if item.get("role") == "object"), "unknown")
        relation = one.get("relation") or "unknown"
        return f"subject={subject}; object={obj}; relation={relation}"
    label = evidence[0].get("label") if evidence else "none"
    if one.get("type") == "attribute":
        return f"{label}; attribute={one.get('attribute')}"
    return str(label)


def write_audit_csv(path: str | Path, records: list[dict[str, Any]], sample_size: int, rng: random.Random) -> None:
    sample = rng.sample(records, min(sample_size, len(records)))
    headers = [
        "id",
        "source",
        "task_type",
        "base_task_type",
        "negative_type",
        "image",
        "question",
        "chosen_answer",
        "rejected_answer",
        "chosen_claim",
        "rejected_claim",
        "chosen_evidence",
        "rejected_evidence",
        "chosen_support",
        "rejected_support",
        "chosen_answer_correct",
        "rejected_answer_wrong",
        "chosen_evidence_correct",
        "rejected_error_correct",
        "note",
    ]
    ensure_parent(path)
    with repo_path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for record in sample:
            chosen = record["chosen_claims"][0]
            rejected = record["rejected_claims"][0]
            writer.writerow(
                {
                    "id": record["id"],
                    "source": record["source"],
                    "task_type": record["task_type"],
                    "base_task_type": record.get("base_task_type", ""),
                    "negative_type": record["negative_type"],
                    "image": record["image"],
                    "question": record["question"],
                    "chosen_answer": record["chosen_answer"],
                    "rejected_answer": record["rejected_answer"],
                    "chosen_claim": chosen["span"],
                    "rejected_claim": rejected["span"],
                    "chosen_evidence": compact_evidence(chosen),
                    "rejected_evidence": compact_evidence(rejected),
                    "chosen_support": chosen["support"],
                    "rejected_support": rejected["support"],
                    "chosen_answer_correct": "",
                    "rejected_answer_wrong": "",
                    "chosen_evidence_correct": "",
                    "rejected_error_correct": "",
                    "note": "",
                }
            )


def leakage_report(records: list[dict[str, Any]], eval_ids: set[str], eval_paths: list[str]) -> dict[str, Any]:
    train_ids = {str(record.get("image_id")) for record in records if record.get("image_id")}
    overlap = sorted(train_ids & eval_ids)
    return {
        "train_image_ids": len(train_ids),
        "eval_image_ids": len(eval_ids),
        "overlap_count": len(overlap),
        "overlap_first20": overlap[:20],
        "eval_image_id_files": eval_paths,
    }


def build_summary(records: list[dict[str, Any]], leakage: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_records(records)
    summary.update(
        {
            "task_type_counts": dict(sorted(Counter(record["task_type"] for record in records).items())),
            "base_task_type_counts": dict(sorted(Counter(record.get("base_task_type", "") for record in records).items())),
            "negative_type_counts": dict(sorted(Counter(record["negative_type"] for record in records).items())),
            "source_counts": dict(sorted(Counter(record["source"] for record in records).items())),
            "same_answer_rows": sum(1 for record in records if record["chosen_answer"] == record["rejected_answer"]),
            "answer_dpo_identical_rows": sum(
                1
                for record in records
                if record["chosen_answer"] == (record.get("answer_dpo_rejected_answer") or record.get("rejected_answer"))
            ),
            "claims_with_missing_box": sum(
                1
                for record in records
                for key in ("chosen_claims", "rejected_claims")
                for one in record[key]
                for ev in one.get("evidence") or []
                if ev.get("box") is None
            ),
            "leakage": leakage,
        }
    )
    return summary


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
