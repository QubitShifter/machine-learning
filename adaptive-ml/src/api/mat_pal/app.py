from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from src.api.mat_pal import session_store
from src.api.mat_pal.schemas import (
    AnswerRequest,
    SessionResponse,
    StartSessionRequest,
)


app = FastAPI(
    title="MAT-PAL API",
    version="0.1.0",
    docs_url="/swagger",
)


@app.get(
    "/fastapi",
    include_in_schema=False,
)
def fastapi_docs() -> RedirectResponse:
    return RedirectResponse(
        url="/swagger"
    )


@app.post(
    "/sessions/start",
    response_model=SessionResponse,
)
def start_session(
    request: StartSessionRequest,
) -> SessionResponse:
    try:
        return session_store.start_session(
            problem_id=request.problem_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@app.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
)
def get_session(
    session_id: str,
) -> SessionResponse:
    response = session_store.get_session(
        session_id
    )

    if response is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    return response


@app.post(
    "/sessions/{session_id}/answer",
    response_model=SessionResponse,
)
def submit_answer(
    session_id: str,
    request: AnswerRequest,
) -> SessionResponse:
    response = session_store.submit_answer(
        session_id=session_id,
        answer_request=request,
    )

    if response is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    return response


@app.post(
    "/sessions/{session_id}/hint",
    response_model=SessionResponse,
)
def request_hint(
    session_id: str,
) -> SessionResponse:
    response = session_store.request_hint(
        session_id=session_id
    )

    if response is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    return response
