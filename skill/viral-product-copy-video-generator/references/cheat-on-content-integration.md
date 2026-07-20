# Cheat-On-Content Integration

Use this reference when the user asks the promotion Skill to review generated drafts with `cheat-on-content`.

## Default Behavior

- Use the built-in scorecard first.
- If `cheat-on-content` is installed, use it as a second-pass qualitative reviewer.
- Prefer lightweight scoring/review language unless the user explicitly asks to start a real prediction cycle.
- Do not write immutable prediction logs by default.

## Safe Review Flow

1. Generate platform content into the selected output directory.
2. Read the generated bridge pack at `reports/promotion-manager/cheat-review/<product>-cheat-review-pack.json`.
3. Pick the exact per-platform Markdown draft from `reports/promotion-manager/cheat-review/drafts/`.
4. Ask `cheat-on-content` for qualitative scoring only, or use `cheat-score` if the user's project has already been initialized for that system.
5. Copy actionable rewrite suggestions back into the promotion review report.
6. Keep the publish pack approval gate unchanged.

## Prediction Cycle Boundary

Only start a `cheat-predict` style cycle when the user explicitly asks for prediction logging. A prediction cycle creates immutable logs and has stricter blind-prediction rules. Do not silently create those files from a normal product-promotion request.

## Fallback

If `cheat-on-content` is unavailable, blocked, or not initialized in the user's current content project, continue with the built-in scorecard. The promotion pipeline must not fail just because the optional review Skill is unavailable.
