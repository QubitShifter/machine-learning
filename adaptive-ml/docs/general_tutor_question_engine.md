# General Tutor Question Engine

Phase 23 adds an open-ended Ask-a-question path that is separate
from deterministic grading.

Learners can ask broader questions than the hardcoded Linear ODE
concept matcher. Known concept questions still use the local fast
path. Everything else can use a model provider, with optional web
retrieval when the question actually needs external sources.

## Purpose

Keep this split:

    Submit answer  →  SymPy / units / step checkers  →  progress
    Ask a question →  Question Engine  →  explanation + sources

The question engine never decides whether a math answer is correct.
It does not complete steps, change mastery, or increment attempts.

## Architecture

    Student question
          ↓
    POST /sessions/{id}/question
          ↓
    TutorQuestionContext from the live session
          ↓
    local concept guidance (strong match only)
          ↓
    alternative-method intent on a first-order linear ODE:
        Case A — verified transformation → local explanation
        Case B — no verified transformation → local uncertainty
          ↓
    Case C — general open-ended question:
          routing → MODEL_ONLY or MODEL_WITH_WEB
          optional web search
          model explanation in the session language
          structured sources

Package:

    src/core/question_engine/
        contracts.py     TutorQuestionContext, sources, routes
        engine.py        GeneralTutorQuestionEngine
        local_guidance.py
        routing.py
        alternative_methods.py
        grounding.py
        providers.py     Null / Fake / optional HTTP providers
        sources.py       ranking, snippet bounds
        context.py       model prompt + public context
        config.py        build_question_engine_from_env()

## Local / model / web routing

Deterministic. No opaque confidence score.

- Strong local concept match → `LOCAL_ONLY`
- Supported Unknown Numbers method questions → `LOCAL_ONLY`
  (parameterized inverse-operation explanation from verified
  equation facts; a complete evaluation of `x` only when the
  learner asks for the full answer or the exercise is already
  complete). Unrelated questions stay on the model path.
- Supported Unknown Numbers definition questions
  (“what is a factor?”, “какво е множител?”) → `LOCAL_ONLY`
  before method matching. Unsupported terms stay on the model
  path.
- Alternative-method intent on a supported first-order linear
  ODE **and** a verified transformation → `LOCAL_ONLY`
  (Case A; no model, no web)
- Alternative-method intent on a supported first-order linear
  ODE **without** a verified transformation → `LOCAL_ONLY`
  (Case B; localized uncertainty; no model, no web)
- Question asks to search / find sources / latest / recent /
  current applications / who introduced / външен източник /
  намери / ... → `MODEL_WITH_WEB`
- Otherwise → `MODEL_ONLY` (Case C)

Known Linear ODE explanations (integrating factor, divide by μ,
product derivative, C, P(x)/Q(x)) stay local. A narrow
alternative-method handler covers questions such as “can this be
solved another way?” and “can I use separation of variables?”.
That handler is checked before the Linear ODE concept matcher so
a specific-method question is not absorbed by an unrelated
substring match.

Failure to verify a transformation is **not** proof that no
other method exists. That case must not be sent to the model to
decide existence or uniqueness.

General open-ended questions (applications in physics, “what is
erfi?”, Navier–Stokes nonlinearity, and similar) are **not**
captured by the alternative-method fallback. They keep the
existing local / model / web routing.

Stage-generic fallback text is **not** treated as a strong
match.

## Provider abstractions

    TutorModelProvider.answer(question, context, sources, prompt)
    WebSearchProvider.search(query, max_results=5)

Defaults:

- `NullTutorModelProvider` — unavailable, no network
- `NullWebSearchProvider` — empty results, no network

Tests use:

- `FakeTutorModelProvider`
- `FakeWebSearchProvider`

Optional live providers, only when configured:

- OpenAI-compatible chat completions
- generic HTTP search endpoint

The engine does not import a vendor SDK.

## Session language

The stored tutor session language is authoritative.

A Bulgarian session answers in Bulgarian even if the learner typed
English. An English session answers in English even if the learner
typed Bulgarian.

Ask-a-question does not take a client `language` field.

## Current tutor context

The model receives:

- subject, domain, topic
- problem title and statement
- current step / prompt / expected input type
- sanitized tutor metadata (P, Q, stage, …)

It does not receive:

- student display name
- student_id
- session UUID
- mastery / progress history
- internal closed-form solution checks

## Linear ODE alternative-method evidence

For `first_order_linear` problems, `grounding.py` reads existing
`p_expression` and `q_expression` metadata. It does not call the
Linear ODE tutor engine or `engine.submit()`.

Classification and verification are distinct:

1. SymPy `classify_ode` may list `separable`. That flag is stored
   as `classified_separable` and is **not** shown to the model.
2. A transformation is constructed only when `Q - P*y` factors as
   `f(x)*g(y)`.
3. The rearrangement `y' = f(x)*g(y)` is checked algebraically.
4. The separated form is kept only when it reconstructs that
   product on the domain where `g(y) != 0`.
5. If `g(y)` is divided out, the restriction `g(y) != 0` is
   recorded. Constant roots of `g` are substituted into the
   original ODE (`P*c - Q` simplifies to `0`). Only verified
   equilibria are listed; unverified candidates are omitted.
6. An optional internal `dsolve` expression is residual-checked
   with `linear_ode_residual`. A nonzero residual is not marked
   verified.

Learner-visible `VerifiedTransformation` fields, when established:

- original / rearranged / separated equations
- optional integration of both sides (`F(y) = G(x) + C`)
- intermediate restrictions
- recovered constant/equilibrium solutions

Those objects stay internal. They are **not** serialized into the
learner answer as `method = separable` or `verified = True`.

### Case A — verified alternative available

When the learner asks about an alternative method **and** a
verified separable transformation exists, MAT-PAL builds a
localized EN/BG explanation from those expressions:

- intro naming separation of variables
- original equation
- rearrangement
- separation
- restriction and verified equilibrium, when present
- a prompt to integrate both sides, without the closed-form `y`

This path is `answer_source=local`. It does not call the model or
web search.

### Case B — alternative not verified

When alternative-method intent is detected on a supported
first-order linear ODE, but no suitable verified transformation
is available, MAT-PAL returns a deterministic localized
uncertainty explanation:

- the integrating-factor method applies to this linear equation
  under the usual first-order linear assumptions
- no alternative transformation has been verified for the
  current problem
- that is **not** a proof that another method is impossible
- the learner may continue with the integrating-factor method

This path is also `answer_source=local`. It does not call the
model or web. It does not claim uniqueness. It does not
fabricate a separated equation.

These two statements are not equivalent:

    No alternative method has been verified.
    No alternative method exists.

A specific-method question such as “can I use separation of
variables?” is distinguished from “is there another way?”. If
separation has not been verified, the reply says applicability
has not been established. It does not say that separation
definitely works, and it does not say that separation is
impossible.

### Case C — general open-ended question

Questions that are not alternative-method requests keep the
existing local / model / web routing. Examples: applications of
linear ODEs in physics, “what is erfi?”, why Navier–Stokes is
nonlinear. These must not be captured by the Case B fallback.

If a general question still reaches the model, the prompt
receives human-readable mathematics, not raw dicts or dataclass
reprs. Absence of evidence in that prompt is stated as “no
alternative transformation has been verified”, not as a proof
that no other method exists.

Internal-only data, stripped from the model prompt and provider
context:

- `internal_solution_checks` (closed-form candidate + residual)
- `classified_separable`
- raw `verified_method_evidence` dictionaries
- implementation notes such as `alternative_method_notes`

The model is told to explain verified transformations, not invent
missing algebra, not invent method names, not claim uniqueness,
and not reveal a complete explicit solution for `y` unless the
learner asked for a fully worked solution.

If the product factorization cannot be verified, no separated
equation is invented. The integrating-factor method remains the
established general method for this class. Other methods may
exist for particular equations, but they are not asserted as
either available or impossible.

This is a narrow first-order linear check, not a general symbolic
solver or singular-solution algorithm. Equations such as
`y' + x y = x**2` or `y' + 2 y = 2x + 1` have no verified
alternative transformation here even though they remain
first-order linear.

A particular solution of `y' + 2 y = 2x + 1` can be found by
inspection (`y_p = x`), and `y = x + u` reduces the ODE to a
homogeneous equation. MAT-PAL does not currently verify that
reduction. Adding a particular-solution / substitution engine is
out of scope for this question-engine path; the correct
immediate behavior is qualified uncertainty, not an unsupported
impossibility claim.

## Question history

Each session keeps the last 3 question/answer pairs.

History is discarded with the session. It is not written to
progress or mastery. Follow-up questions can use that bounded
context.

## Web-query privacy

Search queries are built only from:

    topic + domain + subject + learner question

Never send student_id, profile name, session UUID, or mastery.

## Source model

    TutorSource: title, url, domain, optional snippet

The API/frontend expose title, url, and domain. Snippets are not
required in the UI. At most 3 useful results are returned from up
to 5 search hits. Snippets are clipped.

Preferred domains (`.edu`, OpenStax, LibreTexts, arXiv, …) are
ranked first. This is a small preference list, not a giant
allowlist.

## Source safety

Retrieved text is untrusted reference material.

The model prompt states that retrieved content is not instructions
and must be ignored if it tries to change tutor rules. Web pages
cannot grade answers or mutate session state.

## No grading via model

`POST /sessions/{id}/question` never calls `engine.submit()`.

`POST /sessions/{id}/answer` remains the only grading path.

## State immutability

Asking a question does not change:

- current step
- completed flag
- answer/incorrect counts
- hints used
- mastery

Only the bounded question history and the displayed feedback
change.

## Failure / offline fallback

No API keys required. The app starts with null providers.

- Known local concept: still answered
- Unknown question without a model: localized fallback
- Web failure with a working model: model answer plus a short
  notice that external sources were unavailable
- Model failure: localized fallback, no fabricated answer

## Environment configuration

    MATPAL_MODEL_PROVIDER=none|openai_compatible
    MATPAL_MODEL_API_KEY=
    MATPAL_MODEL_BASE_URL=https://api.openai.com/v1
    MATPAL_MODEL_NAME=gpt-4.1-mini
    MATPAL_MODEL_TIMEOUT_SECONDS=20

    MATPAL_WEB_SEARCH_PROVIDER=none|http
    MATPAL_WEB_SEARCH_URL=
    MATPAL_WEB_SEARCH_API_KEY=

Secrets are never printed or returned in API errors.

## Frontend

When `sources` is non-empty, Feedback shows Sources / Източници
with `target="_blank"` `rel="noopener noreferrer"` links.

When `metadata.used_web` is true, a small badge is shown:

- EN: Answer supported by external sources
- BG: Отговор с помощта на външни източници

Local answers do not show an empty Sources section.

While a question request is in flight:

- EN: Finding an explanation...
- BG: Подготвям обяснение...

Ask-a-question still closes after submit so the MathLive answer
editor is restored (Phase 22).

Conceptual / general-question responses use the Explanation /
Обяснение status pill and the model answer. They do not repeat
that label as a second heading. Ordinary graded feedback still
uses the Feedback heading. Previous graded responses stay under
Last answer / Последен отговор.

## Test strategy

    PYTHONPATH=. python3 experiments/test_question_engine.py

Covers routing, language, context, privacy, sources, prompt
injection labeling, history, fallbacks, session immutability,
Linear ODE alternative-method grounding, deterministic
alternative-method explanations (verified and unverified),
general-question routing, and leakage of internal
verification metadata. Providers are fakes. Tests do not
use the network or API keys.

## Adding another provider

Implement `TutorModelProvider` or `WebSearchProvider`, then wire it
in `build_question_engine_from_env()`. Do not call vendor SDKs from
`engine.py`.
