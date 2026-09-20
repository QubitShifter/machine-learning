# Generated Primary-School Word Problems

Phase 25 adds generated Grade 4 story problems on the existing
MAT-PAL tutor loop. It does not add a second engine, session API,
or grading framework.

Catalog topic: `story_problems`
Generator: `grade4_word_problems`
Mastery key: `grade4_word_problems`

The static Hazelnuts item stays on `word_problems` with mastery
`grade4_reverse_reasoning`. Completing a generated story does not
update that key.

## Supported Families

| Family id | Reasoning |
| --- | --- |
| `several_operations` | Compute intermediates, then a final total or product |
| `comparison` | More than, fewer than, or twice as many |
| `reverse` | A final result is given; recover the starting quantity |

Each generated item uses one reviewed template from a closed set.
Templates are original and parameterized. They are not workbook
copies and they do not reuse the three-hollows hazelnut story.

## Situation Model

A language-neutral `StoryTemplate` stores:

- `template_id`, `family`, `difficulty`
- sampled integer slots
- named quantities
- an ordered list of relations (a small DAG / chain)
- the quantity the story asks for
- which quantities are hidden versus shown in the wording

Relations are only:

- `add`
- `sub`
- `mul`
- `double` (exactly ×2)

General division stories are not generated. Exact `÷2` appears only
when a reverse item undoes doubling.

## Exact Verification

Before an item is returned, `verify_word_problem` checks:

- parameter bounds and positive integers
- relation evaluation matches stored quantities
- statement numbers match the visible quantities
- reverse recovery restores the hidden start
- doubling is ×2, never remainder + 2×remainder
- comparison direction matches “more than” / “fewer than”
- calculation-step count equals the declared difficulty
- the last tutoring step is the asked-for quantity
- ordinary hint parameters do not include that final unknown

Invalid candidates retry up to 24 times, then fail closed.
Seeds reproduce the mathematics. Problem IDs still use a UUID
suffix. No model writes or grades the answer key.

## Reviewed Templates

Wording is bound to a specific mathematical meaning. These are
not interchangeable:

| English / Bulgarian phrasing | Meaning |
| --- | --- |
| twice as many / два пъти толкова | ×2 |
| N more than / с N повече | +N, named quantity is larger |
| N fewer than / с N по-малко | −N, named quantity is smaller |
| the number of remaining bottles was doubled / броят на останалите бутилки бил удвоен | remainder × 2 |
| two more / с 2 повече | +2, not doubling |

Forbidden because it is ambiguous:

- “twice as many as remained were put in”
- adding twice the remaining quantity (that would be ×3)

Canonical reverse example:

- 6 bottles were taken out
- the remaining number was doubled
- 18 bottles afterward
- start = 15

Forward: `(15 − 6) × 2 = 18`
Backward: `18 ÷ 2 = 9`, `9 + 6 = 15`

## Difficulty

Difficulty is the number of mathematical relationships, not the
size of the numbers.

1. one relationship and a short solution
2. two dependent relationships
3. three relationships, or mixed comparison / reverse structure

An identify-known step may precede the calculations. Tests treat
`relation_count` and tutoring-step count as different numbers.
Grade 4 bounds stay small (results ≤ 40 / 80 / 200).

## Localization

Template ids and relations are language-neutral. EN/BG strings live
under `gen.story.*` and are rendered with `pst()`. Stories are not
translated by substring replacement.

Catalog keys:

- `catalog.topic.story_problems`
- `catalog.problem.grade4_word_problems_generated`

The generated title and preview follow the UI language. The problem
id and numerical parameters stay the same.

## Adaptive Mastery

`story_problems → grade4_word_problems`
`word_problems → grade4_reverse_reasoning` (unchanged)

## Adding a Future Template

1. Add a `StoryTemplate` with an explicit wording-to-relation
   meaning, required phrases, and forbidden phrases.
2. Add EN/BG statement, prompt, and hint keys for every step
   quantity.
3. Sample only visible and hidden slots; derived values come from
   relations.
4. Extend the semantic tests. Arithmetic verification alone does
   not prove that the wording matches the model.

Do not attach a generator to `word_problems`.

## Free-form mathematical safety

Method questions such as “How do I solve this step?” and
“Как да намеря отговора на тази стъпка?” do not go to the
unrestricted model when the live item is a generated
`story_problems` exercise.

The question engine matches a small reviewed intent list, then
reuses `story_step_guidance` on the authoritative situation
model. The explanation names the current step’s relation and
the required inverse or forward operation. It may show an
unevaluated setup such as `26 - 8 = ?` when both numbers are
already disclosed (given in the statement, or recovered by a
**completed** earlier step).

It must not:

- evaluate the current unanswered step (`26 - 8 = 18`)
- reveal future intermediates or the final start
- say that an intermediate (for example 9) is the starting
  quantity
- send hidden values or forbidden-answer lists to Ollama

A method request without enough live context still stays local
and returns a safe clarification. General questions that are
not about solving this exercise can still use the model.

## Progressive hints

Generated story problems keep the existing `POST /sessions/{id}/hint`
endpoint. Repeated clicks on the same step advance three
levels derived from the situation model:

1. Understand the relevant story relationship.
2. Name the appropriate operation (often the inverse).
3. Show a verified unevaluated expression for this step.

A further click keeps the last hint on screen and states that
all hints for the step have been shown. `hint_available`
becomes false so the UI can disable **More help**. A correct
answer moves to the next step and hint levels start again.
An incorrect answer does not advance the step and does not
auto-reveal the next hint. Language switching still clears the
live session, so hint progression resets with the new session.

**Hint counting:** only newly revealed hints increment
the per-step engine counter and `StoredSession.hint_requests`.
A fourth request after the last story hint is answered safely
and does not increment counters. Legacy single-hint exercises
still count every click. Guided Questions and free-form
questions do not increment hint counters. Mastery formulas
are unchanged: any revealed hint in the session still means
the completion was not first-attempt-without-hints. The
adaptive `last_hints_used >= 2` threshold is reached by the
three revealed story levels themselves, so skipping exhausted
repeats does not change the formula.

Incorrect story feedback adds a short next action (“check the
last action and undo it”) without diagnosing a specific
wrong number.

## Disclosure

Provenance stays structured:

- A. Given statement facts may appear.
- B. A completed step’s result may appear in a later hint or
  method explanation.
- C/D/E. Current expected, future intermediates, and the
  unfinished final answer must not.

Do not scan digits as a leak test. Overlapping visible and
hidden numbers are judged by field provenance.

## Known Limitations

- No general division, fractions, geometry, diagrams, or
  multiple-choice
- No free-text “name the operation” step
- Wrong-operation diagnostics are deferred unless a later phase
  can prove a unique alternate using the same visible numbers
- Ordinary vocabulary help explains a closed phrase list and does
  not print the final unknown
- A, B, and C share one catalog topic and one mastery key
- Progressive three-level hints are story problems only.
  Hazelnuts, Unknown Numbers, arithmetic, patterns, ODE, and
  physics keep their previous single-hint text.
- Method capture is a narrow phrase list, not a general
  classifier. Unrecognised solution requests on a story still
  fail closed locally rather than inventing mathematics.
- No misconception diagnosis from a wrong numeric answer.
