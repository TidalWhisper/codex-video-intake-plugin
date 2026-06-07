Repair the Stage 05 semantic contract JSON.

Rules:
- Return one full replacement JSON object that matches the Stage 05 semantic contract schema exactly.
- Keep all unchanged good fields stable unless a failed validation item requires updating them.
- Do not push semantics back into Python. If a field is currently missing and Python would otherwise need to infer it, you must fill it explicitly in the repaired contract.
- Keep the official Stage 05 mainline intact:
  - Stage05-A bootstrap
  - Stage05-B `reference_guided_storyboard`
- Do not remove canonical reference-image paths or replace them with invented filenames.
- Prefer the smallest valid fix:
  - keep semantic prompt/review/repair decisions explicit
  - avoid re-expanding optional workflow metadata unless the repair actually needs a shot-level override
  - `review_card` may be omitted if the rest of the contract already gives Python enough information to render it mechanically
