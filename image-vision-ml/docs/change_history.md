# Development Change History

Permanent chronological record of significant Image Vision ML changes, including UI, backend, scientific calculations, APIs, data processing, configuration, and bug fixes.

Individual records live under [`changes/`](changes/). Feature documentation lives in the [`feature registry`](feature_registry.md). Bug records live in [`bug_fix_history.md`](bug_fix_history.md).

This log is **not** a Git changelog replacement. Uncommitted work is recorded as `git_reference: uncommitted`. Historical phases without a recoverable UTC event time use `timestamp: unknown` and `retrospective: true`; `documented_at` is the actual clock time the retrospective was written.

## Workflow

```text
IMPLEMENTED → TESTED → VERIFIED
```

Also supported: `PENDING_VERIFICATION`, `RETROSPECTIVE`.

Rules:

1. Record every significant implementation change.
2. Use actual runtime UTC timestamps (`YYYY-MM-DDTHH:MM:SSZ`).
3. Preserve historical entries. Never reuse IDs. Never rewrite earlier records.
4. When a change is revised, append a new change or a later verification note.
5. Link feature IDs and bug IDs.
6. Distinguish implemented, tested, and verified.
7. Record intentionally unchanged scientific behaviour when relevant.
8. Do not invent timestamps for historical work.

```bash
python -m scripts.change_log list
python -m scripts.change_log validate
python -m scripts.change_log refresh
```

## Records

<!-- CHANGE_TABLE_START -->
| Change ID | Timestamp | Phase | Type | Status | Description | Git | Details |
|---|---|---|---|---|---|---|---|
| `CHG-0001` | 2026-10-22T13:53:13Z | 3.5 UI Refinement | enhancement | verified | Satellite Explorer split workspace with independently scrolling scientific inspector | `uncommitted` | [CHG-0001](changes/CHG-0001.md) |
| `CHG-0002` | 2026-10-22T13:53:14Z | 3.5 UI Refinement | documentation | verified | Permanent development change-history log and Markdown validator | `uncommitted` | [CHG-0002](changes/CHG-0002.md) |
| `CHG-0003` | unknown | 3.3 coverage and readiness | feature | retrospective | Retrospective of Phase 3.3 coverage, calibration, and modeling-readiness work | `uncommitted` | [CHG-0003](changes/CHG-0003.md) |
| `CHG-0004` | unknown | 3.4 soil and agricultural analytics | feature | retrospective | Retrospective of Phase 3.4 ERA5-Land soil-moisture foundation and Soil Analysis UI | `uncommitted` | [CHG-0004](changes/CHG-0004.md) |
| `CHG-0005` | unknown | 3.5 Scientific Satellite Explorer | feature | retrospective | Retrospective of Phase 3.5 histograms, SCL overlay, pixel inspector, and multi-AOI preparation | `uncommitted` | [CHG-0005](changes/CHG-0005.md) |
| `CHG-0006` | 2026-10-22T16:14:22Z | Soil Analysis UI Enhancement | feature | verified | Year-over-year historical soil-moisture comparison on Soil Analysis | `uncommitted` | [CHG-0006](changes/CHG-0006.md) |
| `CHG-0007` | 2026-10-22T16:35:43Z | Soil Analysis UX Refinement | enhancement | verified | Soil Analysis contextual workspaces for historical comparison and detailed analysis | `uncommitted` | [CHG-0007](changes/CHG-0007.md) |
<!-- CHANGE_TABLE_END -->
