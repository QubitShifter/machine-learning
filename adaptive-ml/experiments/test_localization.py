import sympy as sp
from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.tutor_registry import (
    KINEMATICS_FIXED_PROBLEM_ID,
    LINEAR_ODE_FIXED_PROBLEM_ID,
    SEPARABLE_ODE_FIXED_PROBLEM_ID,
)
from src.core.i18n.concept import (
    CANONICAL_NO,
    CANONICAL_YES,
    normalize_concept_answer,
)
from src.core.i18n.locale import normalize_locale
from src.core.i18n.ode import ot
from src.core.i18n.question import qt
from src.core.tutor_engine.adapters.linear_ode_adapter import (
    LinearODETutorAdapter,
)
from src.core.tutor_engine.contracts import StudentSubmission
from src.core.tutor_engine.linear_first_order_engine import (
    LinearFirstOrderEngine,
)
from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)
from src.core.physics.kinematics.generator import (
    generate_kinematics_problem,
)
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
    get_student_record,
    load_progress,
)


client = TestClient(app)
PRIMARY_SCHOOL_PROBLEM_ID = "grade4_reverse_reasoning_001"


def start_session(problem_id, language=None, student_id="local_student"):
    payload = {
        "problem_id": problem_id,
        "student_id": student_id,
    }
    if language is not None:
        payload["language"] = language

    response = client.post("/sessions/start", json=payload)
    assert response.status_code == 200
    return response.json()


def generate_problem(topic, language="en", seed=11, difficulty=1):
    mapping = {
        "kinematics": {
            "subject": "physics",
            "domain": "classical_mechanics",
            "topic": "kinematics",
        },
        "first_order_linear": {
            "subject": "mathematics",
            "domain": "ode",
            "topic": "first_order_linear",
        },
        "separable_equations": {
            "subject": "mathematics",
            "domain": "ode",
            "topic": "separable_equations",
        },
    }
    payload = {
        **mapping[topic],
        "difficulty": difficulty,
        "seed": seed,
        "language": language,
    }
    response = client.post("/problems/generate", json=payload)
    assert response.status_code == 200
    return response.json()


def assert_unsupported_language_falls_back_to_english():
    assert normalize_locale("de") == "en"
    assert normalize_locale("") == "en"
    assert normalize_locale(None) == "en"

    session = start_session(
        KINEMATICS_FIXED_PROBLEM_ID,
        language="de",
    )
    english = start_session(KINEMATICS_FIXED_PROBLEM_ID)

    assert session["problem_title"] == english["problem_title"]
    assert session["problem_statement"] == english["problem_statement"]
    assert "accelerates" in session["problem_statement"]


def assert_english_session_starts_in_english():
    session = start_session(KINEMATICS_FIXED_PROBLEM_ID)
    assert "Car accelerating" in session["problem_title"]
    assert "starts from rest" in session["problem_statement"]
    assert "Identify the initial velocity" in session["feedback"]


def assert_bulgarian_session_starts_in_bulgarian():
    session = start_session(
        KINEMATICS_FIXED_PROBLEM_ID,
        language="bg",
    )
    assert "Автомобил, ускоряващ от покой" in session["problem_title"]
    assert "тръгва от покой" in session["problem_statement"]
    assert "Определете началната скорост" in session["feedback"]
    assert "m/s^2" in session["problem_statement"]


def assert_same_math_across_languages():
    english = start_session(KINEMATICS_FIXED_PROBLEM_ID)
    bulgarian = start_session(
        KINEMATICS_FIXED_PROBLEM_ID,
        language="bg",
    )
    assert english["total_steps"] == bulgarian["total_steps"]
    assert english["expected_input_type"] == (
        bulgarian["expected_input_type"]
    )

    english_wrong = client.post(
        f"/sessions/{english['session_id']}/answer",
        json={"answer": "1 m/s", "input_type": "units"},
    )
    bulgarian_wrong = client.post(
        f"/sessions/{bulgarian['session_id']}/answer",
        json={"answer": "1 m/s", "input_type": "units"},
    )
    assert english_wrong.status_code == 200
    assert bulgarian_wrong.status_code == 200
    assert english_wrong.json()["status"] == "incorrect"
    assert bulgarian_wrong.json()["status"] == "incorrect"


def assert_fixed_kinematics_bulgarian_prompt():
    session = start_session(
        KINEMATICS_FIXED_PROBLEM_ID,
        language="bg",
    )
    assert "Определете началната скорост" in session["feedback"]


def assert_kinematics_bulgarian_hint():
    session = start_session(
        KINEMATICS_FIXED_PROBLEM_ID,
        language="bg",
    )
    hinted = client.post(
        f"/sessions/{session['session_id']}/hint"
    )
    assert hinted.status_code == 200
    assert "Покой означава" in hinted.json()["feedback"]


def assert_kinematics_bulgarian_incorrect_feedback():
    session = start_session(
        KINEMATICS_FIXED_PROBLEM_ID,
        language="bg",
    )
    response = client.post(
        f"/sessions/{session['session_id']}/answer",
        json={"answer": "3", "input_type": "units"},
    )
    assert response.status_code == 200
    feedback = response.json()["feedback"]
    assert "Добавете SI единицата" in feedback


def assert_ode_bulgarian_prompt():
    session = start_session(
        LINEAR_ODE_FIXED_PROBLEM_ID,
        language="bg",
    )
    assert "Линейно диференциално уравнение" in (
        session["problem_title"]
    )
    assert "Решете" in session["problem_statement"]
    assert "y' + P(x)y = Q(x)" in session["feedback"]
    assert (
        "Даденото уравнение от този вид ли е?"
        in session["feedback"]
    )
    assert (
        "Даденото уравнение вече ли е в този вид?"
        not in session["feedback"]
    )


def assert_separable_bulgarian_prompt():
    session = start_session(
        SEPARABLE_ODE_FIXED_PROBLEM_ID,
        language="bg",
    )
    assert "разделящи се променливи" in session["problem_title"]
    assert "Решете" in session["problem_statement"]
    assert "dy/dx = 2*x*y" in session["problem_statement"]
    assert "разделете променливите" in session["feedback"]


def assert_primary_school_bulgarian_prompt():
    session = start_session(
        PRIMARY_SCHOOL_PROBLEM_ID,
        language="bg",
    )
    assert "катерица" in session["problem_statement"]
    assert "хралупи" in session["problem_statement"]
    assert "Колко лешника са останали" in session["feedback"]


def assert_generated_kinematics_same_seed_quantities():
    english = generate_kinematics_problem(
        difficulty=2,
        seed=11,
        language="en",
    )
    bulgarian = generate_kinematics_problem(
        difficulty=2,
        seed=11,
        language="bg",
    )
    assert english.quantities == bulgarian.quantities
    assert english.unknown == bulgarian.unknown
    assert english.difficulty == bulgarian.difficulty
    assert [step.kind for step in english.steps] == [
        step.kind for step in bulgarian.steps
    ]
    assert [step.quantity for step in english.steps] == [
        step.quantity for step in bulgarian.steps
    ]
    assert english.statement != bulgarian.statement
    assert "Find" in english.statement or "find" in english.statement.lower()
    assert "Намерете" in bulgarian.statement
    assert "m/s" in english.statement
    assert "m/s" in bulgarian.statement


def assert_generated_kinematics_api_same_seed():
    english = generate_problem("kinematics", "en", seed=21, difficulty=2)
    bulgarian = generate_problem("kinematics", "bg", seed=21, difficulty=2)
    assert english["problem_id"] != bulgarian["problem_id"]
    assert english["total_steps"] == bulgarian["total_steps"]
    assert english["problem_text"] != bulgarian["problem_text"]
    assert "Намерете" in bulgarian["problem_text"]
    assert "m/s" in english["problem_text"]
    assert "m/s" in bulgarian["problem_text"]


def assert_progress_data_unchanged_by_language():
    payload = client.get("/progress").json()
    topics = {
        topic["topic"]: topic
        for topic in payload["topics"]
    }
    assert "kinematics" in topics
    kinematics = topics["kinematics"]
    assert kinematics["topic"] == "kinematics"
    assert kinematics["topic_name"] == "Kinematics"
    assert kinematics["subject"] == "physics"
    assert kinematics["domain"] == "classical_mechanics"
    assert "recent_trend" in kinematics


def assert_student_isolation_unchanged_by_language():
    start_session(
        KINEMATICS_FIXED_PROBLEM_ID,
        language="bg",
        student_id="profile_a",
    )
    start_session(
        LINEAR_ODE_FIXED_PROBLEM_ID,
        language="en",
        student_id="profile_b",
    )
    progress = load_progress(DEFAULT_PROGRESS_PATH)
    student_a = get_student_record(progress, "profile_a")
    student_b = get_student_record(progress, "profile_b")
    assert student_a is not student_b
    response_a = client.get(
        "/progress",
        params={"student_id": "profile_a"},
    ).json()
    response_b = client.get(
        "/progress",
        params={"student_id": "profile_b"},
    ).json()
    assert response_a["student_id"] == "profile_a"
    assert response_b["student_id"] == "profile_b"


def submit_linear_answer(session_id, answer):
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={"answer": answer, "input_type": "text"},
    )
    assert response.status_code == 200
    return response.json()


def assert_concept_answer_normalization():
    assert (
        normalize_concept_answer("yes", "en")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("Y", "en")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer(" no ", "en")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("n", "en")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("да", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("ДА", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer(" Да ", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("не", "bg")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("НЕ", "bg")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("banana", "bg")
        is None
    )
    assert (
        normalize_concept_answer("да", "en")
        is None
    )
    assert (
        normalize_concept_answer("true", "en")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("да, съвпадат", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("да съвпадат", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("съвпадат", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("равни са", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("ДА, СЪВПАДАТ!", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("  да съвпадат  ", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("те съвпадат", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("еднакви са", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("да, равни са", "bg")
        == CANONICAL_YES
    )
    assert (
        normalize_concept_answer("не съвпадат", "bg")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("не, не съвпадат", "bg")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("Не, не съвпадат.", "bg")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("различни са", "bg")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("не са равни", "bg")
        == CANONICAL_NO
    )
    assert (
        normalize_concept_answer("не знам", "bg")
        is None
    )
    assert (
        normalize_concept_answer("интегриращ фактор", "bg")
        is None
    )
    assert (
        normalize_concept_answer("they match", "en")
        is None
    )


def assert_bulgarian_linear_yes_aliases_are_accepted():
    x = sp.symbols("x")
    engine = LinearFirstOrderEngine(
        p_expression=2 * x,
        q_expression=x,
        language="bg",
    )

    for answer in ("да", "ДА", " Да "):
        result = engine.evaluate(
            stage=LinearODEStage.IDENTIFY_STANDARD_FORM,
            student_answer=answer,
        )
        assert result["correct"] is True, answer

    english = LinearFirstOrderEngine(
        p_expression=2 * x,
        q_expression=x,
        language="en",
    )
    english_yes = english.evaluate(
        stage=LinearODEStage.IDENTIFY_STANDARD_FORM,
        student_answer="yes",
    )
    assert english_yes["correct"] is True
    assert "already written" in english_yes["feedback"]
    assert "Next, identify" in english_yes["suggestion"]

    rejected = engine.evaluate(
        stage=LinearODEStage.IDENTIFY_STANDARD_FORM,
        student_answer="banana",
    )
    assert rejected["correct"] is False


def assert_bulgarian_linear_api_concept_answers():
    expected_feedback = (
        "Правилно. Уравнението вече е записано в "
        "стандартния вид на линейно диференциално "
        "уравнение от първи ред."
    )
    expected_suggestion = (
        "След това определете P(x) и Q(x)."
    )

    for answer in ("да", "ДА", " Да "):
        session = start_session(
            LINEAR_ODE_FIXED_PROBLEM_ID,
            language="bg",
        )
        payload = submit_linear_answer(
            session["session_id"],
            answer,
        )
        assert payload["status"] == "correct", answer
        assert payload["current_step"] == 2, answer
        assert payload["feedback"] == expected_feedback
        assert payload["suggestion"] == expected_suggestion
        assert "The equation is already" not in (
            payload["feedback"]
        )
        assert "Next, identify" not in (
            payload.get("suggestion") or ""
        )

    session = start_session(
        LINEAR_ODE_FIXED_PROBLEM_ID,
        language="bg",
    )
    unrelated = submit_linear_answer(
        session["session_id"],
        "banana",
    )
    assert unrelated["status"] == "incorrect"

    english = start_session(LINEAR_ODE_FIXED_PROBLEM_ID)
    english_yes = submit_linear_answer(
        english["session_id"],
        "yes",
    )
    assert english_yes["status"] == "correct"
    assert "The equation is already" in (
        english_yes["feedback"]
    )
    assert "Next, identify" in english_yes["suggestion"]


def assert_bulgarian_adapter_yes_advances():
    adapter = LinearODETutorAdapter(
        p_expression=2 * sp.symbols("x"),
        q_expression=sp.symbols("x"),
        language="bg",
    )
    prompt = adapter.get_current_response()
    assert (
        "Даденото уравнение от този вид ли е?"
        in prompt.feedback
    )

    response = adapter.submit(
        StudentSubmission(
            answer="да",
            input_type="text",
        )
    )
    assert response.status == "correct"
    assert response.current_step == 2
    assert "Правилно. Уравнението вече е записано" in (
        response.feedback
    )
    assert response.suggestion == (
        "След това определете P(x) и Q(x)."
    )
    assert "The equation is already" not in response.feedback
    assert "Next, identify" not in (
        response.suggestion or ""
    )


def assert_missing_language_defaults_to_english():
    detail = client.get(
        f"/problems/{KINEMATICS_FIXED_PROBLEM_ID}"
    ).json()
    assert detail["language"] == "en"
    assert "starts from rest" in detail["problem_text"]

    localized = client.get(
        f"/problems/{KINEMATICS_FIXED_PROBLEM_ID}",
        params={"language": "bg"},
    ).json()
    assert localized["language"] == "bg"
    assert "тръгва от покой" in localized["problem_text"]
    assert localized["problem_id"] == KINEMATICS_FIXED_PROBLEM_ID


def assert_bulgarian_integrating_factor_wording():
    prompt = ot(
        "bg",
        "linear.stage.mu",
        P="2*x",
        integrated_p="x**2",
    )
    assert "Намерете интегриращия фактор mu(x)." in prompt
    assert "Намерете mu(x)." not in prompt
    assert "Find mu(x)." not in prompt

    english = ot(
        "en",
        "linear.stage.mu",
        P="2*x",
        integrated_p="x**2",
    )
    assert "Find mu(x)." in english
    assert "Намерете интегриращия фактор" not in english

    session = start_session(
        LINEAR_ODE_FIXED_PROBLEM_ID,
        language="bg",
    )
    submit_linear_answer(session["session_id"], "да")
    identified = submit_linear_answer(
        session["session_id"],
        "P = 2*x, Q = x",
    )
    next_prompt = identified["metadata"]["next_prompt"]
    assert "Намерете интегриращия фактор" in next_prompt
    assert "Намерете mu(x)." not in next_prompt


def assert_bulgarian_linear_concept_guidance():
    x = sp.symbols("x")
    english = LinearFirstOrderEngine(
        p_expression=2 * x,
        q_expression=x,
        language="en",
    ).evaluate(
        stage=LinearODEStage.FIND_INTEGRATING_FACTOR,
        student_answer="Why do we use an integrating factor?",
    )
    assert english.get("kind") == "concept"
    assert "The integrating factor" in english["feedback"]
    assert "We start with" in english["feedback"]

    bulgarian = LinearFirstOrderEngine(
        p_expression=2 * x,
        q_expression=x,
        language="bg",
    )
    for question in (
        "Защо ни е нужен интегриращ фактор?",
        "Защо използваме интегриращ фактор?",
    ):
        result = bulgarian.evaluate(
            stage=LinearODEStage.FIND_INTEGRATING_FACTOR,
            student_answer=question,
        )
        feedback = result["feedback"]
        assert result.get("kind") == "concept", question
        assert "Интегриращият фактор" in feedback, question
        assert "mu' = P(x)*mu" in feedback, question
        assert "The integrating factor" not in feedback
        assert "We start with" not in feedback
        assert "By the product rule" not in feedback

    divide = bulgarian.evaluate(
        stage=LinearODEStage.FIND_INTEGRATING_FACTOR,
        student_answer=(
            "И двете страни на уравнението ли да се разделят "
            "на интегриращия фактор?"
        ),
    )
    assert divide.get("kind") == "concept"
    assert "разделяме двете страни" in divide["feedback"]
    assert "mu(x)" in divide["feedback"]
    assert "Задайте концептуален въпрос" not in divide["feedback"]
    assert "Интегриращият фактор се избира" not in divide["feedback"]
    assert "The integrating factor" not in divide["feedback"]

    session = start_session(
        LINEAR_ODE_FIXED_PROBLEM_ID,
        language="bg",
    )
    submit_linear_answer(session["session_id"], "да")
    submit_linear_answer(
        session["session_id"],
        "P = 2*x, Q = x",
    )
    payload = submit_linear_answer(
        session["session_id"],
        "Защо ни е нужен интегриращ фактор?",
    )
    assert payload["status"] == "concept"
    assert "Интегриращият фактор" in payload["feedback"]
    assert "The integrating factor" not in payload["feedback"]


def assert_alternative_method_strings_are_localized():
    assert qt("bg", "question.alternative.intro").startswith(
        "Да. Това уравнение може да се реши и чрез "
        "разделяне на променливите."
    )
    assert "separation of variables" in qt(
        "en",
        "question.alternative.intro",
    )
    assert qt("bg", "question.alternative.rearrange") == (
        "Пренареждаме уравнението:"
    )
    assert qt("en", "question.alternative.rearrange") == (
        "Rearrange the equation:"
    )
    assert qt("bg", "question.alternative.separate") == (
        "Разделяме променливите:"
    )
    assert qt("bg", "question.alternative.restriction_lead") == (
        "При делението приемаме, че"
    )
    assert qt("en", "question.alternative.restriction_lead") == (
        "When dividing we assume that"
    )
    assert qt("bg", "question.alternative.equilibrium_lead") == (
        "Отделно проверяваме, че постоянната функция"
    )
    assert qt("en", "question.alternative.equilibrium_lead") == (
        "Separately we check that the constant function"
    )
    assert qt("bg", "question.alternative.equilibrium_tail") == (
        "също е решение на първоначалното уравнение."
    )
    assert "разделяне" not in qt(
        "en",
        "question.alternative.intro",
    )
    assert qt(
        "bg",
        "question.alternative.unverified.if_applies",
    ) == (
        "Методът с интегриращ фактор е приложим за това "
        "линейно уравнение."
    )
    assert qt(
        "en",
        "question.alternative.unverified.if_applies",
    ) == (
        "The integrating-factor method applies to this "
        "linear equation."
    )
    assert qt(
        "bg",
        "question.alternative.unverified.no_verified",
    ) == (
        "На този етап нямам проверено алтернативно "
        "преобразуване за конкретната задача."
    )
    assert qt(
        "en",
        "question.alternative.unverified.no_verified",
    ) == (
        "I do not currently have a verified alternative "
        "transformation for this particular problem."
    )
    assert qt(
        "bg",
        "question.alternative.unverified.separation",
    ) == (
        "Не съм установил, че разделянето на "
        "променливите е приложимо за това уравнение."
    )
    assert qt(
        "en",
        "question.alternative.unverified.separation",
    ) == (
        "I have not established that separation of "
        "variables applies to this equation."
    )
    assert qt(
        "bg",
        "question.alternative.unverified.not_impossible",
    ) == (
        "Това не означава, че друг метод е невъзможен."
    )
    assert qt(
        "en",
        "question.alternative.unverified.not_impossible",
    ) == (
        "That does not mean another method is impossible."
    )
    assert qt(
        "bg",
        "question.alternative.unverified.continue",
    ) == (
        "Можем да продължим с метода с интегриращ фактор "
        "или да разгледаме допълнително приложимостта на "
        "друг подход."
    )
    assert qt(
        "en",
        "question.alternative.unverified.continue",
    ) == (
        "We can continue with the integrating-factor "
        "method or examine another approach more closely."
    )
    assert "Transformacao" not in qt(
        "bg",
        "question.alternative.unverified.no_verified",
    )
    assert "разделяне" not in qt(
        "en",
        "question.alternative.unverified.no_verified",
    )
    assert "единственият" not in qt(
        "bg",
        "question.alternative.unverified.no_verified",
    )
    assert "only possible" not in qt(
        "en",
        "question.alternative.unverified.if_applies",
    )


def main():
    assert_unsupported_language_falls_back_to_english()
    assert_english_session_starts_in_english()
    assert_bulgarian_session_starts_in_bulgarian()
    assert_same_math_across_languages()
    assert_fixed_kinematics_bulgarian_prompt()
    assert_kinematics_bulgarian_hint()
    assert_kinematics_bulgarian_incorrect_feedback()
    assert_ode_bulgarian_prompt()
    assert_concept_answer_normalization()
    assert_bulgarian_linear_yes_aliases_are_accepted()
    assert_bulgarian_linear_api_concept_answers()
    assert_bulgarian_adapter_yes_advances()
    assert_separable_bulgarian_prompt()
    assert_primary_school_bulgarian_prompt()
    assert_generated_kinematics_same_seed_quantities()
    assert_generated_kinematics_api_same_seed()
    assert_progress_data_unchanged_by_language()
    assert_student_isolation_unchanged_by_language()
    assert_missing_language_defaults_to_english()
    assert_bulgarian_integrating_factor_wording()
    assert_bulgarian_linear_concept_guidance()
    assert_alternative_method_strings_are_localized()
    print("localization tests passed")


if __name__ == "__main__":
    main()
