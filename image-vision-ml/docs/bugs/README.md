# Bug records

Permanent per-issue records for Image Vision ML. IDs are sequential and never reused.

- Central table: [`../bug_fix_history.md`](../bug_fix_history.md)
- Feature index: [`../feature_registry.md`](../feature_registry.md)
- Change history: [`../change_history.md`](../change_history.md)

Workflow: `OPEN → INVESTIGATING → FIXED → VERIFIED`, plus `DEFERRED`, `NOT_A_BUG`, and `REOPENED`.

A code change is not verified until tests have been run and a later verification timestamp is recorded.

```bash
python -m scripts.bug_log list
python -m scripts.bug_log validate
```

Do not delete records after a fix. Not every rejected satellite scene is a software bug.
