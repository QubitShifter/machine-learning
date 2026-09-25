# Adaptive Problem Selection

MAT-PAL uses a transparent rule-based adaptive selection layer. Learners can
still choose fixed problems and manual difficulty. Adaptive practice recommends
the next runnable activity.

Phase 18 keeps that policy deterministic and explainable. It adds a bounded
recent-history window and a derived feature layer so difficulty can use more
than the single latest session.

## Architecture

Raw progress, derived features, and recommendation policy are separate:

1. `src/core/student_model/progress_store.py` persists mastery, counts,
   last-session fields, and a bounded `recent_sessions` list.
2. `src/core/adaptive/features.py` derives `AdaptivePerformanceFeatures`.
3. `RuleBasedAdaptivePolicy` ranks topics and chooses a supported difficulty.
4. The API and dashboard consume the resulting `AdaptiveRecommendation`.

The policy does not parse arbitrary progress dictionaries. Feature calculation
is not duplicated in API routes, the dashboard, the frontend, or tutor engines.

## Mastery Source

Mastery still uses the existing student model and progress store:

- `StudentModel.update_mastery_after_question(...)`
- `src/core/student_model/progress_store.py`
- `math/ode/data/student_progress.json`

Phase 18 does not change mastery-update mathematics.

Progress is stored by mastery key under `skills`. Each record keeps:

- `mastery`, on a `0.0` to `1.0` scale
- `questions_completed`
- `first_attempt_streak`
- last-session fields: total attempts, incorrect attempts, hints,
  first-attempt success, completion
- `recent_sessions`, a bounded list of recent completed-session summaries

## Mastery Keys

The shared API maps runnable activity to a mastery key in one place:

- Primary School word problems -> `grade4_reverse_reasoning`
- Primary School arithmetic -> `grade4_arithmetic`
- Primary School unknown numbers -> `grade4_unknown_number`
- Primary School number patterns -> `grade4_number_patterns`
- First-order linear ODEs -> `linear_first_order_ode`
- Separable ODEs -> `separable_equations`

If a future topic has no explicit mapping, the first registration skill is used,
then the topic id as a fallback.

## Recent History

Completed sessions append a minimal history entry:

- `completed`
- `total_attempts`
- `incorrect_attempts`
- `hints_used`
- `first_attempt_success`
- `steps_completed`
- `total_steps`

`RECENT_HISTORY_LIMIT = 5`. Older entries are dropped. Incomplete sessions are
not appended.

## Backward Compatibility

Phase 16/17 progress files do not contain `recent_sessions`. They still load.

Missing history defaults to an empty list. Mastery, question counts, and streaks
are preserved. If `recent_sessions` is empty but last-session fields show that
at least one session happened, the feature builder derives exactly one
synthetic observation from those `last_*` fields. It does not invent a longer
history.

Legacy recent-session entries may omit `steps_completed` and `total_steps`.
Those records still load. The feature builder does not invent historical step
counts. Sessions without a positive `steps_completed` are omitted from the
attempts-per-step average. If no recent session has step counts,
`recent_average_attempts_per_step` is `0.0` and does not by itself satisfy
the weak-attempts criterion.

## Derived Features

`build_adaptive_features(...)` is the authoritative calculator. Rates use the
recent session count as the denominator and return `0.0` when that count is
zero.

- `recent_completion_rate`: completed sessions / recent session count
- `recent_first_attempt_success_rate`: first-attempt successes / count
- `recent_hint_rate`: sessions with hints / count
- `recent_incorrect_rate`: sessions with incorrect attempts / count
- `recent_average_attempts_per_step`: mean of
  `total_attempts / max(steps_completed, 1)` over sessions that recorded a
  positive `steps_completed`. Raw per-session `total_attempts` is not used
  because a clean multi-step tutor session naturally has many submissions.

`has_enough_recent_history` is true when
`recent_session_count >= MIN_RECENT_SESSIONS_FOR_TREND` (`2`).

`recent_trend` is display-oriented and is not a mastery label:

- `strong`
- `stable`
- `needs_support`
- `insufficient_history`

A high mastery score can still have `needs_support` recent performance, and a
low mastery score can still have a `strong` recent trend.

## Difficulty Policy

`RuleBasedAdaptivePolicy` still maps mastery to a base difficulty:

- `mastery < 0.40` -> difficulty `1`
- `0.40 <= mastery < 0.75` -> difficulty `2`
- `mastery >= 0.75` -> difficulty `3`

That numeric base is snapped to the nearest actual supported level. If two
supported levels are equally near, the lower one is chosen.

Movement then uses supported-level index, not numeric `+1`/`-1` with min/max
clamping. For `supported = (1, 3)`, a strong move from `1` becomes `3`. For
`supported = (2, 4, 7)`, movement is `2 -> 4 -> 7`.

## Recent Performance Adjustment

When at least two recent sessions exist, aggregate rates decide the adjustment:

Strong, all of:

- first-attempt success rate `>= 0.75`
- hint rate `<= 0.25`
- incorrect rate `<= 0.25`

Then move up one supported level.

Weak, any of:

- hint rate `>= 0.50`
- incorrect rate `>= 0.50`
- average attempts per completed step `>= 2.0`

Then move down one supported level.

If both strong and weak would apply, or neither applies, keep the base
difficulty.

If there are fewer than two recent sessions, aggregate trend adjustment is not
used. Phase 16 last-session fallback still applies so existing short histories
do not change abruptly:

- Strong last session: first-attempt streak `>= 2`, last session was a
  first-attempt success, and no hints were used
- Weak last session: at least two recent incorrect submissions or at least two
  hints

Static-only topics return `recommended_difficulty = null` and do not mention
difficulty adjustments.

## Topic Selection

The policy considers only runnable catalog topics. Ranking remains primarily
mastery-driven and deterministic:

1. Lower mastery
2. Fewer completed questions
3. Weaker recent performance, used only as a later deterministic tie-breaker:
   lower first-attempt success rate, then higher hint rate, then higher
   incorrect rate
4. Lexicographic topic id

Phase 18 does not change the primary ranking criteria. Recent-performance
signals are added only after mastery and questions completed, and before
topic id.

No random selection is used.

For ODE topics, recommendations can be fulfilled by Phase 15 generation. For a
static-only topic such as the current Primary School word problem, the
recommendation points at the fixed runnable problem instead of pretending
generation exists.

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

The summary is recorded once per completed session. It updates mastery through
the existing student model and appends one bounded history entry.

## API And Frontend Flow

`POST /adaptive/recommendation` returns a generic recommendation with:

- subject/domain/topic
- difficulty
- mastery and mastery key
- generation availability
- optional static problem id
- concise reason
- JSON-safe metadata for derived features, base difficulty, adjustment, and
  supported difficulties

The frontend `Practice Next` action calls the recommendation endpoint. If the
recommended topic supports generation, it calls the existing
`POST /problems/generate` endpoint and starts the returned problem through
`POST /sessions/start`. If the topic is static-only, it starts the recommended
problem id directly.

## Current Limitations

Phase 18 is still heuristic and deterministic. It is:

- not probabilistic
- not Bayesian
- not learned from data
- not personalized by a trained model
- not estimating item discrimination
- not estimating latent ability independently of mastery
- not modeling forgetting curves
- not modeling prerequisite graphs

Primary School `topics.json` now records explicit prerequisite metadata.
A generic runtime curriculum loader can read it. Adaptive recommendation
still does not consume prerequisite metadata. The field is sequencing
metadata, not an access lock. The live edges are Arithmetic to Unknown
Numbers and Arithmetic to Story Problems.

Those limits are intentional. The feature layer is meant to be reused later by
BKT, IRT, DKT, RL, or other models.

Other current limits:

- No authentication or multi-user account model; this uses the existing local
  single-user progress file.
- ODE hint counts are tracked at the shared API layer, not inside the adapter
  sessions.
- No timing analytics.

Future ML policies can implement the same recommendation shape as
`RuleBasedAdaptivePolicy` and can be compared against this deterministic
baseline.
