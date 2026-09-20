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
        guided_questions.py
            catalog, selection, ID validation, local handlers
        guided_elaboration.py
            optional verified-strategy selection for one
            allow-listed Guided Question ID

## Guided Questions

Primary-school students can click a small set of suggested
questions instead of typing. The feature reuses the existing
`POST /sessions/{id}/question` path. It does not add a second
question engine, discovery endpoint, or explanation panel.

### Request and discovery

`QuestionRequest` accepts the existing free-form field and an
optional stable identifier:

    {"question": "What is a factor?"}
    {"question_id": "unknown.factor.definition"}

If both are present, `question_id` determines routing. The
displayed and history text is the server-derived localized
label, not the client-supplied string.

`SessionResponse` includes an additive list:

    suggested_questions: [
      {
        "question_id": "unknown.factor.definition",
        "label": "What is a factor?",
        "category": "definition"
      }
    ]

Suggestions are computed from the live engine step, the
server-side problem, and the session language. They are not
derived from the most recent concept feedback. The list is
refreshed on session start, GET, answers, hints, guided
questions, free-form questions, and completion.

IDs are language-neutral. Labels and explanations follow the
session language (`en` / `bg`).

### Validation

Treat `question_id` as untrusted. Resolve it only against the
currently offered suggestions for this session, problem, step,
and family. Unknown, stale, wrong-family, unsupported, and
complete-solution IDs return HTTP 400.

Invalid guided requests do not call Ollama or web retrieval,
do not append history, and do not change step, attempts, hints,
mastery, or completion.

### Supported families

- Unknown Numbers (`unknown_numbers`): addition, subtraction,
  and multiplication forms. Definitions, identify-known, and
  inverse-method questions reuse Phase 24 handlers.
- Generated story problems (`story_problems`): known facts,
  asked quantity, current-step approach, and relation-specific
  phrases such as more-than, fewer-than, twice-as-many, or
  doubled — only when that relation is in the template.
  Explanations are built from the server-side situation model
  (`template_id`, quantity roles, visible `statement_ids`,
  current-step purpose, and the current relation). They name
  the actual given numbers and the asked quantity. They do
  not say “look at the numbers.”
- Arithmetic (`arithmetic`): parentheses meaning, first
  operation, and left-to-right evaluation when the generated
  shape supports it.
- Number Patterns (`number_patterns`): sequence rule,
  operation-chain follow, and reverse-chain undo when the
  generated variant supports it.

Unsupported contexts return `[]`:

- static Hazelnuts reverse-reasoning (`word_problems`)
- first-order linear and separable ODEs
- kinematics / physics

### Disclosure

Every catalog entry has an explicit disclosure level:

- `definition` — visible vocabulary or phrase meaning
- `understand_step` — what the current step is asking
- `explain_method` — verified symbolic transformation without
  evaluating hidden answers

Complete-solution IDs are never suggested. Method answers may
show `x = 35 ÷ 7` but must not evaluate `x`. Handlers that
cannot guarantee this are omitted from discovery.

Do not scan explanation text for digits. Build explanations
from approved templates and visible operands. Use internal
answer keys only for validation.

Story Guided Questions distinguish provenance:

- A. Given facts already written in the statement
  (`statement_ids` / `statement_params`). These may appear
  in “what is given?”, identify-known steps, and vocabulary
  “in this problem” clauses.
- B. A current-step answer that is itself a quoted given
  number. Identify-known guidance may mention it.
- C/D/E. Computed intermediates, future intermediates, and
  the unfinished final answer. Ordinary guided explanations
  must not display those values.

Internal-only context (`slots`, `quantities`, `relations`,
`ask`, `hidden`, current relation id) stays on the server.
It is stripped from model prompts and must not appear in
the public session response. Discovery still returns only
`question_id`, `label`, and `category`.

Examples:

- Reverse bottles: given facts mention the taken, added,
  and final numbers, not the recovered start. “What are we
  trying to find?” names the starting number. Later reverse
  steps name the inverse of the current relation without
  evaluating it.
- Comparison: “more than” / “fewer than” / “twice as many”
  appear only when that relation is in the template, and
  the text names Leo/Nina (or boys/girls) from this story.
- Several operations: “in all” or “times as many” is tied
  to the actual groups in the current template.

Known story-guidance limitations:

- Language switching still clears the live session.
- Phrase examples use independent sample numbers, never
  hidden computed values from the current story.
- Hazelnuts, ODE, and physics still return `[]`.

### Session state

Guided questions use the existing non-grading question path.
They never call `engine.submit()`. Question history may grow by
one bounded entry (last 3). Hint counters, attempts, mastery,
and the current step stay unchanged. Clicking a suggestion must
not clear a partially typed numeric answer.

### Hybrid AI Tutor (safe MVP)

An optional **Explain differently** / **Обясни по друг начин**
action can follow one allow-listed Guided Question after the
deterministic explanation is already on screen:

    story.phrase.doubled

MAT-PAL remains authoritative for mathematical facts,
transformations, answer keys, grading, disclosure, and
progress. Llama does not solve or grade the exercise. It may
only choose among reviewed teaching strategies. The backend
then renders original EN/BG templates and verified blocks.

This MVP does **not** display arbitrary model-generated
explanations, `connective_before` / `connective_after` prose,
or free-form mathematics. Valid JSON is not proof that the
mathematics is correct. Unexpected model output fails closed
to the local explanation.

#### Request

Reuse `POST /sessions/{id}/question` with optional
`explanation_mode`:

    {"question_id": "story.phrase.doubled"}
    {"question_id": "story.phrase.doubled", "explanation_mode": "local"}
    {"question_id": "story.phrase.doubled", "explanation_mode": "elaborate"}

Omitting `explanation_mode` preserves the existing Guided
Question path. The identifier is still validated against the
live allowed set. An `elaborate` request for an ID that is
not allow-listed for hybrid selection does not call the model.
Free-form `{ "question": "..." }` routing is unchanged for
general questions. On generated story problems, a narrow
method-intent list is answered locally from the situation
model instead of unrestricted Ollama. Client-supplied
explanation or mathematical context is ignored.

`Explain differently` does not append a second question-history
entry and does not consume an extra history slot. Failed
elaboration leaves history unchanged.

#### Strategy selection

The model must return a JSON object and nothing else:

    {
      "schema": "matpal.guided_strategy.v1",
      "strategy": "analogy",
      "example_id": null
    }

Allowed strategies for this MVP:

- `simpler_words`
- `analogy`
- `concrete_example` with `example_id` from the approved list
  (`double.apples.3x2` for doubling)

Validation requires the exact schema identifier, a known
strategy, an approved example ID when required, no unexpected
keys, no extra text, and a bounded payload. Provider-level
JSON schema is not required. MAT-PAL constructs the visible
text from reviewed templates.

To add another verified strategy later: extend the allow-listed
question IDs, strategy IDs, optional example IDs, and EN/BG
templates in `guided_elaboration.py` / `story_guidance.py`.
Do not introduce a second question engine.

#### Restricted provider context

The hybrid path uses a dedicated prompt, not the unrestricted
free-form model prompt. The model receives only:

- language
- grade-appropriate level (grade 4)
- stable question ID
- supported strategy IDs
- allowed example IDs
- a short selection-task description

It does **not** receive student name or ID, session ID,
mastery, progress, the full problem, hidden quantities, the
final answer, the current expected answer, solution steps,
question history, or credentials. Entire
`PrimarySchoolProblem` / `TutorQuestionContext` objects are
not sent. Hidden intermediate, current-expected, and final
answers must never appear in system messages, user messages,
JSON context, forbidden-answer lists, or validation metadata
visible to the model.

The server may keep hidden values privately to verify
rendered text. Overlapping visible and hidden digits are not
treated as leaks by scanning every numeral.

#### Configuration

    MATPAL_GUIDED_AI_MODE=off|optional
    MATPAL_GUIDED_ELABORATION_TIMEOUT_SECONDS=15

Default mode is `off`: Guided Questions behave as before, no
model call occurs, and Explain differently is not shown.

`optional` shows the button only for allow-listed IDs when a
model provider is configured (`is_available()`). Clicking it
may call the existing OpenAI-compatible provider. There is no
second client. Do not hardcode the Ollama address; use
`MATPAL_MODEL_BASE_URL`.

The elaboration timeout is per-request on
`TutorModelProvider.answer(timeout_seconds=...)`. It does not
change `MATPAL_MODEL_TIMEOUT_SECONDS` used by free-form Ask a
question. CPU-only Ollama development often needs longer than
15 seconds, for example:

    MATPAL_GUIDED_ELABORATION_TIMEOUT_SECONDS=180

Do not raise the free-form timeout unless that path also
needs it.

#### Fallback and stale responses

The local explanation is the fallback for disabled or missing
providers, timeout, HTTP errors, empty or invalid JSON,
unknown strategies, unsupported example IDs, unexpected
fields, stale sessions, changed steps, and duplicate in-flight
elaboration. Raw provider errors are never shown to the child.
The existing explanation stays visible while the request runs.

Public metadata is additive and machine-readable:

- `elaboration_available`
- `elaboration_status` (`applied`, `off`, `unavailable`,
  `unsupported`, `failed`, `stale`, `duplicate`)
- `elaboration_strategy` / `elaboration_example_id` when applied
- `mathematical_source=deterministic_backend`
- `explanation_selected_by_model` (selection only; the model
  did not verify the mathematics)
- `guided_local_explanation` for restoring the original text

Before the provider call the server captures session ID,
problem ID, current step, and question ID. After the response
it re-reads the live session and discards the elaboration if
any of those changed or the question is no longer allowed.
The in-flight guard only rejects duplicate elaboration
requests. It does not lock answer submission for the duration
of an Ollama call. FastAPI runs the synchronous urllib request
in a worker thread; other worker threads can still
`POST /answer`.

The frontend also ignores a response that no longer matches
the active session, problem, and step.

Elaboration never calls `engine.submit()`, never advances the
step, and never changes attempts, hints, completion, mastery,
adaptive difficulty, or progress.

### Language switching

Switching the UI language currently clears the active session.
Guided Questions does not restore the live step. That existing
limitation is unchanged.

### Adding a safe handler

1. Choose a stable, language-neutral `question_id`.
2. Add EN/BG label and explanation keys. Do not substring-
   translate and do not ask a model to invent the question.
3. Register the ID only for the exercise family, form, step,
   and relation that the handler can explain from verified
   server-side problem data.
4. Assign `definition`, `understand_step`, or `explain_method`.
   If the handler would reveal a current, future, or final
   numeric answer, omit it.
5. Resolve the label from the catalog. Store that label in
   question history.
6. Keep the handler local. A displayed guided ID must never
   fall through to Ollama or web retrieval.
7. Return only `question_id`, `label`, and `category` in
   discovery. Never serialize `x`, `expected_answer`, slots,
   quantities, relations, or the answer key.

## Local / model / web routing

Deterministic. No opaque confidence score.

- Guided `question_id` that is currently suggested →
  `LOCAL_ONLY` (catalog handler only; no model, no web)
- Story-problem free-form **method** intent on
  `story_problems` (“How do I solve this step?”,
  “Как да намеря отговора…”) → `LOCAL_ONLY` using
  `story_step_guidance`. The unrestricted model is not used
  to calculate steps or invent answer keys.
- Guided `explanation_mode=elaborate` on an allow-listed ID
  with `MATPAL_GUIDED_AI_MODE=optional` → model **selects**
  a verified strategy; MAT-PAL **renders** the explanation.
  Unsupported IDs and every parse failure stay local.
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

    TutorModelProvider.answer(question, context, sources, prompt, timeout_seconds=None)
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

    MATPAL_GUIDED_AI_MODE=off|optional
    MATPAL_GUIDED_ELABORATION_TIMEOUT_SECONDS=15

    MATPAL_WEB_SEARCH_PROVIDER=none|http
    MATPAL_WEB_SEARCH_URL=
    MATPAL_WEB_SEARCH_API_KEY=

Secrets are never printed or returned in API errors.

## Frontend

`TutorCard` shows GuidedQuestions above Hint / Ask a question
when `suggested_questions` is non-empty. Buttons submit
`question_id` through the existing `submitQuestion` API. The
existing FeedbackPanel explanation view is reused. Hint and
free-form Ask a question remain. An empty suggestion list
renders no panel.

When a supported Guided Question explanation is on screen and
hybrid mode is `optional` with a configured provider, Feedback
shows a secondary **Explain differently** /
**Обясни по друг начин** control in the existing explanation
block. It does not add a second panel or heading. While that
request runs, the local explanation, numeric answer field,
Hint, and Ask a question stay available. Failed elaboration
keeps the original text.

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

## Free-form story method safety

On generated `story_problems`, a small reviewed phrase list
(“How do I solve this step?”, “Как да намеря отговора на тази
стъпка?”, “What action should I use?”) is answered locally
from `story_step_guidance`. That path reuses the same
situation model as Guided Questions and progressive hints.
It names the current step’s relation and the required
operation. It may show an unevaluated setup such as
`26 - 8 = ?` when those numbers are already disclosed.

It does not evaluate the unanswered step, reveal future
intermediates, or call the unrestricted model to calculate.
A method request with incomplete live context still stays
`LOCAL_ONLY` and returns a safe clarification. The web cue
`намери` still requests retrieval; `намеря` in a method
question does not. Phase 23 ODE Case A/B/C routing is
unchanged.

Guided Questions and free-form questions do not increment
hint counters, advance the step, or change mastery.
Progressive story hints use the existing Hint endpoint.
Only newly revealed hints increment `hint_requests` and the
per-step engine counter. Exhausted repeats stay local, do
not increment, and do not reveal answers. Mastery formulas
are unchanged.

Conceptual / general-question responses use the Explanation /
Обяснение status pill and the model answer. They do not repeat
that label as a second heading. Ordinary graded feedback still
uses the Feedback heading. Previous graded responses stay under
Last answer / Последен отговор.

## Test strategy

    PYTHONPATH=. python3 experiments/test_question_engine.py
    PYTHONPATH=. python3 experiments/test_guided_questions.py
    PYTHONPATH=. python3 experiments/test_guided_elaboration.py
    PYTHONPATH=. python3 experiments/test_story_math_safety.py

Covers routing, language, context, privacy, sources, prompt
injection labeling, history, fallbacks, session immutability,
Linear ODE alternative-method grounding, deterministic
alternative-method explanations (verified and unverified),
general-question routing, and leakage of internal
verification metadata. Guided-question tests cover discovery
for Unknown Numbers, story families, arithmetic/patterns,
invalid/stale/wrong-family IDs, no provider calls, disclosure,
and session immutability. Hybrid elaboration tests cover mode
`off` / `optional`, strategy rendering, hostile model output,
restricted provider context, stale and duplicate requests, and
unchanged free-form / Guided Question routing. Story math-safety
tests cover the bottle reverse-reasoning fixture, method-intent
local routing, progressive hint levels, hint counters, incorrect
nudges, and EN/BG text. Providers are fakes. Tests do not use
the network or API keys.

## Adding another provider

Implement `TutorModelProvider` or `WebSearchProvider`, then wire it
in `build_question_engine_from_env()`. Do not call vendor SDKs from
`engine.py`.
