# Simulated Reviewer 1

Archived note: this review was written for the earlier assumed-positive draft,
not for the current diagnostic manuscript.

Overall score: 4.2 / 5  
Confidence: 3.5 / 5  
Recommendation: Weak Accept

## Summary

The paper studies a simple modification to multimodal DPO: append short
annotation-derived evidence hints to both chosen and rejected responses during
preference tuning. The method is deliberately lightweight and is evaluated on a
controlled COCO/GQA setting with three groups: Base Instruct, Answer-DPO, and
Evidence-Hint DPO.

## Strengths

- The central idea is clean and easy to understand: keep the DPO objective and
  model fixed, and isolate the response-format signal.
- The experimental setup is appropriately scoped. The paper avoids overclaiming
  and focuses on object existence, simple attributes, and left/right relations.
- The main result is convincing for a small paper: Evidence-Hint DPO improves
  over Answer-DPO on both COCO and GQA while reducing false positives and not
  increasing refusal.
- The data construction details are strong for reproducibility, especially the
  aligned pair export, train/eval image-overlap check, and 200-example audit.
- The limitation section is honest and prevents the method from being framed as
  a broad hallucination solution.

## Weaknesses

- The paper would be stronger with one external hallucination benchmark such as
  official POPE, even if only as a secondary sanity check.
- The current evaluation uses one backbone and one seed. The method is simple
  enough that at least a seed variance estimate would improve confidence.
- Qualitative examples are summarized in prose but not shown as a table with
  images or outputs. This makes the error decomposition less tangible.
- The relation task is limited to left/right, so the paper should continue to
  avoid language suggesting general spatial reasoning.

## Questions For Authors

- Were the evidence hints always removed from the inference prompt, and were
  any generations manually inspected for hidden format leakage beyond exact
  string matching?
- How sensitive is the method to hint length? A shorter hint may preserve most
  of the benefit while reducing the training-time slowdown.
- Are the GQA gains concentrated in positive or negative questions?

## Rebuttal Suggestions

- Emphasize that the main claim is not "grounding solved", but "explicit
  support cues make DPO less answer-style-only in a controlled setting."
- Add one short table of 3-4 qualitative examples if page space allows.
- If final logs are available, report Evidence-Hint training runtime and note
  that longer responses increase DPO cost.

## Final Assessment

I would accept this as a concise, well-controlled paper. The contribution is
not large, but the idea is practical, the isolation of variables is good, and
the results support the stated claim.
