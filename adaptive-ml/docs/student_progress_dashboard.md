# Student Progress Dashboard

Phase 17 exposes MAT-PAL's existing adaptive state through a read-only,
generic progress dashboard.

## Data Source

The dashboard reads the existing local progress store:

`math/ode/data/student_progress.json`

The backend loads it through `src/core/student_model/progress_store.py`.
Missing files and legacy records are handled by the existing defaulting logic.

## API Shape

`GET /progress` returns:

- `student_id`
- `topics`
- `recommendation`
- response metadata

Each topic contains:

- subject, domain, topic id, and topic name
- mastery key
- mastery and display-only mastery label
- questions completed
- first-attempt streak
- last attempts, incorrect attempts, hints, first-attempt success, completion
- generation availability and supported difficulties
- recommended difficulty for generatable topics
- static problem id for static-only runnable topics
- recent session count, first-attempt rate, hint rate, incorrect rate,
  average attempts per completed step, and display-only recent trend

Recent trend values are `strong`, `stable`, `needs_support`, and
`insufficient_history`. They come from the shared adaptive feature builder and
are not a mastery-completion label.

Optional filters:

- `subject`
- `domain`

## Topic Grouping

The service enumerates runnable tutor registrations from the shared tutor
registry and groups cards by:

`subject/domain/topic`

This prevents duplicate cards when multiple problems belong to one topic.
Only runnable registered topics appear; catalog placeholders are not shown.

## Mastery Display

Mastery remains a `0.0` to `1.0` model value. The frontend shows the numeric
value, a rounded percentage for the bar, and a display-only label:

- `< 0.40` -> `Building`
- `0.40` to `< 0.75` -> `Developing`
- `>= 0.75` -> `Strong`

These labels are display-only and do not affect adaptive policy behavior.

The dashboard may also show a display-only recent-performance trend from the
same backend feature builder used by the recommendation policy. Mastery level
and recent trend are different concepts.

## Recommendation Integration

The progress service reuses `RuleBasedAdaptivePolicy` for recommended
difficulty. It also includes the current adaptive recommendation returned by
the same policy/service used by `POST /adaptive/recommendation`.

The frontend does not recompute recommendations.

## Practice Recommended

The dashboard's `Practice Recommended Topic` action reuses the existing
adaptive practice flow:

1. Use the included recommendation.
2. If `generation_available` is true, call `POST /problems/generate`.
3. Start the returned problem through `POST /sessions/start`.
4. If the recommendation points to a static problem id, start it directly.

No ODE-specific frontend branching is required.

## Static Topics

Static-only runnable topics, such as the current Primary School problem, still
appear. They show `generation_available = false`, no recommended generated
difficulty, and a `problem_id` for direct practice.

## Limitations

- Local single-user progress only.
- No authentication or accounts.
- No database.
- No historical charts or time-series analytics.
- No ML policy, BKT, DKT, IRT, or RL.
- Browser verification is still required for the final dashboard UX.
