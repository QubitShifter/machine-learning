# Change records

Permanent per-change records for Image Vision ML. IDs are sequential (`CHG-NNNN`) and never reused.

- Central table: [`../change_history.md`](../change_history.md)
- Feature index: [`../feature_registry.md`](../feature_registry.md)
- Bug history: [`../bug_fix_history.md`](../bug_fix_history.md)

```bash
python -m scripts.change_log list
python -m scripts.change_log validate
```

Do not rewrite earlier records. Retrospective entries must set `retrospective: true` and must not invent timestamps or Git commits.
