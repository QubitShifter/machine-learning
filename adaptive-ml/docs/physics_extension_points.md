# Physics Extension Points

Phase 13 prepares MAT-PAL for future Physics tutors without adding a fake
runnable tutor or catalog-visible Physics activity.

## Shared Units Contract

Physics tutors can use the existing shared input type:

```python
TutorResponse(
    ...,
    expected_input_type="units",
)
```

The existing generic session API remains unchanged:

```text
POST /sessions/start
POST /sessions/{session_id}/answer
POST /sessions/{session_id}/hint
```

No Physics-specific route is needed.

## Units Input Flow

The intended frontend-to-backend flow is:

```text
TutorResponse.expected_input_type = "units"
-> AnswerInput
-> UnitsAnswerInput
-> StudentSubmission(answer=..., input_type="units")
-> PhysicsTutorAdapter.submit(...)
```

`UnitsAnswerInput` currently captures a numerical value and a unit string, then
submits one stable answer string such as:

```json
{
  "answer": "9.81 m/s^2",
  "input_type": "units"
}
```

This preserves the current shared `StudentSubmission.answer` contract. Future
adapters may also use `StudentSubmission.metadata` for structured details when
needed.

## Future Value/Unit Representation

A future parser can normalize unit-bearing answers into a structure like:

```json
{
  "kind": "scalar_with_unit",
  "value": "9.81",
  "unit": "m/s^2",
  "raw": "9.81 m/s^2"
}
```

This representation can cover examples such as:

- `9.81 m/s^2`
- `15 N`
- `3.2 kg`
- `20 m/s`
- `5 J`
- `12 V`

Future vector quantities with units can extend the same idea:

```json
{
  "kind": "vector_with_unit",
  "components": ["3", "4"],
  "unit": "m/s",
  "raw": "<3, 4> m/s"
}
```

The current phase does not implement unit conversion, dimensional analysis, or
equivalence checking. Those belong in future Physics adapter/checker logic.

## Future Physics Topics

Future Physics tutors can use the existing catalog hierarchy and registry for
domains such as:

- classical mechanics
- electricity and magnetism
- waves
- thermodynamics
- optics
- modern physics

Each topic should become catalog-visible only when backed by a real runnable
tutor implementation.

Phase 21 adds runnable 1D Kinematics
(`physics / classical_mechanics / kinematics`)
through the existing catalog, registry, generic session
API, units input, MathContent rendering, adaptive
progress, and student profiles. See
`docs/kinematics_tutor.md`.

Still deferred:

- 2D motion
- projectile motion
- Newton's laws
- force diagrams
- energy
- momentum
- rotational mechanics

Deferred to Phase 22 — Internationalization & Bulgarian
Language Support

## Future Adapter Registration

A future `PhysicsTutorAdapter` should implement the same engine protocol used by
Primary School and ODE tutors:

```python
class PhysicsTutorAdapter:
    def get_current_response(self) -> TutorResponse: ...
    def submit(self, submission: StudentSubmission) -> TutorResponse: ...
    def request_hint(self) -> TutorResponse: ...
```

It can register through `TutorRegistry`:

```python
registry.register(
    TutorRegistration(
        problem_id="physics_real_problem_id",
        title="Real Physics Activity",
        problem_statement="...",
        subject="physics",
        domain="classical_mechanics",
        topic="...",
        topic_name="...",
        problem_type="physics",
        total_steps=...,
        expected_input_type="units",
        create_engine=lambda: PhysicsTutorAdapter(...),
        catalog_visible=True,
    )
)
```

The FastAPI routes and frontend remain domain-neutral because rendering and
input dispatch depend on `expected_input_type`, not subject, domain, or topic.
