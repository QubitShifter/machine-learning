# Linear Algebra Extension Points

Phase 12 prepares MAT-PAL for future Linear Algebra tutors without adding a
fake runnable tutor or catalog-visible problem.

## Shared Contracts

The shared backend contract uses `ExpectedInputType` for
`StudentSubmission.input_type` and `TutorResponse.expected_input_type`.
The FastAPI schemas and frontend `InputType` union already include:

- `vector`
- `matrix`

These input types travel through the existing generic session API:

```text
POST /sessions/start
POST /sessions/{session_id}/answer
POST /sessions/{session_id}/hint
```

No Linear Algebra specific route is needed.

## Vector Input Flow

Future vector stages can return:

```python
TutorResponse(
    ...,
    expected_input_type="vector",
)
```

The frontend flow is:

```text
AnswerInput
-> VectorAnswerInput
-> StudentSubmission(answer=..., input_type="vector")
-> LinearAlgebraTutorAdapter.submit(...)
```

`VectorAnswerInput` is currently a placeholder. A future implementation can
capture ordered entries such as `[1, 2, 3]` and submit a stable serialized
answer string plus optional metadata, for example dimension or orientation.

## Matrix Input Flow

Future matrix stages can return:

```python
TutorResponse(
    ...,
    expected_input_type="matrix",
)
```

The frontend flow is:

```text
AnswerInput
-> MatrixAnswerInput
-> StudentSubmission(answer=..., input_type="matrix")
-> LinearAlgebraTutorAdapter.submit(...)
```

`MatrixAnswerInput` is currently a placeholder. A future implementation can
capture rows and columns and submit a stable serialized answer string plus
optional metadata, for example shape, row labels, or column labels.

## Future Adapter Registration

A future `LinearAlgebraTutorAdapter` should implement the same engine protocol
used by the existing registry:

```python
class LinearAlgebraTutorAdapter:
    def get_current_response(self) -> TutorResponse: ...
    def submit(self, submission: StudentSubmission) -> TutorResponse: ...
    def request_hint(self) -> TutorResponse: ...
```

It can then be registered with `TutorRegistry`:

```python
registry.register(
    TutorRegistration(
        problem_id="linear_algebra_real_problem_id",
        title="Real Linear Algebra Activity",
        problem_statement="...",
        subject="mathematics",
        domain="linear_algebra",
        topic="...",
        topic_name="...",
        problem_type="linear_algebra",
        total_steps=...,
        expected_input_type="matrix",
        create_engine=lambda: LinearAlgebraTutorAdapter(...),
        catalog_visible=True,
    )
)
```

Only real runnable Linear Algebra tutors should be catalog-visible. Until then,
the Linear Algebra catalog hierarchy remains empty.
