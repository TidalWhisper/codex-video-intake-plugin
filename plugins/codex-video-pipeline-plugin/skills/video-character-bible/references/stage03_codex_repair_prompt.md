Repair the Stage 03 character bible JSON.

Rules:
- Fix only the fields required by failed checks and the repair packet.
- Preserve already-correct character identity, role logic, and continuity anchors.
- Do not rewrite the approved story or invent new lead characters.
- Return the full corrected JSON object, not a diff.
- Keep `performance_profile` complete for every character.
- Keep `reference_image_handoff` coherent with `reference_image_required` and the provided repair facts.
