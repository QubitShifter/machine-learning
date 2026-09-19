# Primary-School Mathematics Engine

Phase 24 adds the first reusable Grade 4 exercise families to the
existing MAT-PAL tutor loop. It does not add a second tutor engine,
session API, mastery system, or grading framework.

New items reuse `PrimarySchoolTutorEngine`, `PrimarySchoolProblem`,
`SolutionStep`, `TutorRegistry`, `ProblemGeneratorRegistry`, the
generated-problem store, adaptive services, and EN/BG localization.

## Supported Families

| Family | Catalog topic | Mastery key | Problem types |
| --- | --- | --- | --- |
| Arithmetic expressions | `arithmetic` | `grade4_arithmetic` | `arithmetic` |
| Unknown-number equations | `unknown_numbers` | `grade4_unknown_number` | `unknown_number` |
| Number sequences and operation chains | `number_patterns` | `grade4_number_patterns` | `number_pattern`, `operation_chain` |

The static reverse-reasoning word problem
`grade4_reverse_reasoning_001` remains on `word_problems` with mastery
key `grade4_reverse_reasoning`. Completing a generated family does not
update that key.

The mathematical family is independent of the answer format. New items
use a single numeric field with exact integer grading. Legacy reverse
reasoning keeps text input and the previous numeric checker.

## Supported Operations

Arithmetic expressions use a stored expression tree, never `eval()`:

- addition
- subtraction
- multiplication
- parentheses derived from tree precedence

Division is not generated in this phase. If a later increment adds
division, it must be exact nonzero integer division and still evaluate
through the tree.

Unknown-number forms:

- `x + a = b`
- `x - a = b`
- `a × x = b`

The unknown is a unique integer. Zero coefficients are rejected.
Generated items are checked by substituting `x` back into the equation.

Number patterns:

- arithmetic sequences with a nonzero common difference
- forward chains such as `start → +n → ×m → ?`
- reverse chains such as `? → +n → ×m → result`

Sequence items ask for the common difference, then the next term.
Chain items ask for each intermediate, then the missing start or
result. Reverse chains are checked by undoing the operations and
recovering the original start.

## Difficulty Rules

Difficulties `1`, `2`, and `3` are supported for every family.

Arithmetic:

1. two-term addition or subtraction, operands `1–12`, result `≤ 24`
2. order of operations `a + b × c` or `a × b + c`, values `≤ 80`
3. parentheses `(a ± b) × c`, values `≤ 144`

Unknown numbers:

1. `x + a = b`, `x` in `1–15`
2. addition or subtraction forms, `x` in `1–30`
3. also `a × x = b` with exact integer `x` in `2–12`

Sequences and chains:

1. arithmetic sequence only
2. forward operation chain only
3. either a longer sequence or a reverse chain

All leaves, intermediates, and results stay inside those bounds.
Negative intermediates are rejected.

## Deterministic Verification

Generators use `random.Random(seed)` through the existing problem
generation contract. A fixed seed reproduces the same mathematics.
Problem IDs still use a UUID suffix, matching ODE and kinematics.

Each candidate is verified before it is returned:

- arithmetic: tree evaluation equals the displayed expression value
- unknown numbers: substitution and inverse solution agree
- sequences: common difference rebuilds every term
- chains: forward values and reverse recovery both match

Invalid candidates are discarded. If no valid item appears within 24
attempts, generation raises `PrimarySchoolGenerationError`, which the
API maps to HTTP 400. Ollama, web retrieval, and other LLMs are never
used to invent or check the answer key.

## Answer Input Rules

New exercises use `input_type="number"` and
`answer_format="integer"`.

Accepted:

- surrounding whitespace
- optional `+` or `-`
- ordinary integers such as `7` or `12`
- exact decimal forms such as `7.0` or `7,0` when the fractional part
  is all zeros

Rejected without rounding:

- empty input
- nonnumeric text
- `NaN`, `Inf`, and scientific notation
- fractional values such as `7.1`
- strings longer than 24 characters

`AnswerRequest.answer` is unchanged. Legacy reverse reasoning still
uses the previous float comparison path.

## Generator Registration

Register a family in `build_default_problem_generator_registry()`:

1. Implement a generator that returns `PrimarySchoolProblem`.
2. Store language-neutral `prompt_key`, `hint_key`, and params on each
   step.
3. Localize with `localize_generated_primary_school`.
4. Register subject `mathematics`, domain `primary_school`, and the
   catalog topic id.
5. Map that topic in `TOPIC_MASTERY_KEYS`.
6. Add EN/BG strings under stable `gen.*` keys.

The catalog merges generator-only topics into the primary-school
domain even when no static problem exists. Adaptive recommendations
can then point at the topic and a generation difficulty.

Generator-only families are first-class catalog topics. They keep
empty `problem_ids` until the learner generates an item. The learning
path uses `generation_available` and `supported_difficulties` from the
catalog, not a hardcoded topic list. Static reverse reasoning remains
on `word_problems`.

## Adaptive Mastery Mapping

Completion uses `mastery_key_for_registration()`:

- arithmetic completion updates `grade4_arithmetic`
- unknown-number completion updates `grade4_unknown_number`
- sequence or chain completion updates `grade4_number_patterns`

Ask-a-question never grades or advances the exercise, so it does not
update mastery.

## Adding a Future Family

Do not create a new tutor engine. Add another generator, topic id,
mastery key, and localized templates. Keep using
`PrimarySchoolTutorEngine` and a supported `AnswerFormat`. New answer
widgets are a separate frontend increment.

## Curriculum Metadata Unused at Runtime

`math/primary-school/curriculum/*.json` is documentation. Runtime
routing uses the tutor registry, generator registry, and
`TOPIC_MASTERY_KEYS`. Unused in this phase:

- topics `fractions` and `geometry`
- skills `grade4_arithmetic_division`, `grade4_fraction_half`,
  `grade4_fraction_whole_from_half`,
  `grade4_number_pattern_recursive_digits`,
  `grade4_number_pattern_constraints`

## Known Limitations

- No multiple-choice, multi-field, written, or diagram interfaces.
- Arithmetic has no division.
- Sequence common differences are positive.
- Sequences and chains share one family mastery key.
- Ordinary step hints are one verified conceptual sentence and do
  not evaluate `x`. A method question in Ask-a-question shows the
  inverse operation and the next verified transformation, still
  without `x = …`. A definition question such as “Какво е
  множител?” is matched before method intent and explains the
  term without solving for `x`. A complete worked solution is
  returned only when the learner explicitly asks for the full
  answer, or after the exercise is already complete. The hint
  endpoint has no separate full-solution mode.
- Generated catalog rows have no static problem id until generation.

## Deferred Exercise Families

Later increments can add fractions, geometry, mixed word problems,
division, multi-field answers, and visual models without replacing
this engine.
