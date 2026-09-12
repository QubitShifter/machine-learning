# Adaptive Problem Selection

Phase 16 adds a transparent rule-based adaptive selection layer. It is
additive: learners can still manually choose fixed problems and manual
difficulty, while adaptive practice recommends the next runnable activity.

## Mastery Source

Mastery uses the existing student model and progress store:

- `StudentModel.update_mastery_after_question(...)`
- `src/core/student_model/progress_store.py`
- `math/ode/data/student_progress.json`

Progress is stored by mastery key under `skills`. Each record keeps:

- `mastery`, on a `0.0` to `1.0` scale
- `questions_completed`
- `first_attempt_streak`
- recent session fields: total attempts, incorrect attempts, hints, first-attempt success, completion

## Mastery Keys

The shared API maps runnable activity to a mastery key in one place:

- Primary School word problems -> `grade4_reverse_reasoning`
- First-order linear ODEs -> `linear_first_order_ode`
- Separable ODEs -> `separable_equations`

If a future topic has no explicit mapping, the first registration skill is used,
then the topic id as a fallback.

## Difficulty Policy

`RuleBasedAdaptivePolicy` centralizes the thresholds:

- `mastery < 0.40` -> difficulty `1`
- `0.40 <= mastery < 0.75` -> difficulty `2`
- `mastery >= 0.75` -> difficulty `3`

The selected difficulty is clamped to the generator's supported difficulties,
so future topics can expose a different range.

## Recent Performance

Recent performance adjusts the base difficulty by at most one level:

- Strong performance: `first_attempt_streak >= 2`, the last session was a
  first-attempt success, and no hints were used -> increase by one level.
- Weak performance: at least two recent incorrect submissions or at least two
  hints -> decrease by one level.

The result never goes below the minimum supported difficulty or above the
maximum supported difficulty.

## Topic Selection

The policy considers only runnable catalog topics. It recommends the topic with
the lowest mastery. Ties are deterministic:

1. Lower mastery
2. Fewer completed questions
3. Lexicographic topic id

For ODE topics, recommendations can be fulfilled by Phase 15 generation. For a
static-only topic such as the current Primary School word problem, the
recommendation points at the fixed runnable problem instead of pretending
generation exists. Recommended difficulty is `null` for static topics.

## Session Summary

The shared session store creates `SessionPerformanceSummary` on completion:

- problem, subject, domain, topic, difficulty
- mastery key
- completion status
- total answer submissions
- incorrect submissions
- hint requests
- first-attempt success
- completed step count and total steps

The summary is recorded once per session and is the input to mastery updates.

## API And Frontend Flow

`POST /adaptive/recommendation` returns a generic recommendation with:

- subject/domain/topic
- difficulty
- mastery and mastery key
- generation availability
- optional static problem id
- concise reason

The frontend `Practice Next` action calls the recommendation endpoint. If the
recommended topic supports generation, it calls the existing
`POST /problems/generate` endpoint and starts the returned problem through
`POST /sessions/start`. If the topic is static-only, it starts the recommended
problem id directly.

## Current Limitations

- No authentication or multi-user account model; this uses the existing local
  single-user progress file.
- ODE hint counts are tracked at the shared API layer, not inside the adapter
  sessions.
- No timing analytics.
- No ML policy is implemented yet.

Future ML policies can implement the same recommendation shape as
`RuleBasedAdaptivePolicy` and can be compared against this deterministic
baseline.
