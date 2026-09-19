import re

from src.core.i18n.primary_school import PRIMARY_SCHOOL_TEXT, pst
from src.core.question_engine.context import sanitize_tutor_metadata
from src.core.question_engine.contracts import QuestionRoute
from src.core.question_engine import (
    FakeTutorModelProvider,
    FakeWebSearchProvider,
    GeneralTutorQuestionEngine,
    TutorQuestionContext,
    TutorQuestionRequest,
)
from src.core.question_engine.local_guidance import match_local_concept
from src.core.tutor_engine.concept_guidance.unknown_number_guidance import (
    build_unknown_number_explanation,
    extract_unknown_number_facts,
    match_unknown_number_explanation,
    match_vocabulary_term,
)
from src.core.tutor_engine.contracts import StudentSubmission
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation import (
    generate_unknown_number_problem,
)


CYRILLIC = re.compile(r"[А-Яа-яЁё]")
ENGLISH_MATH_TERMS = (
    "addend",
    "subtrahend",
    "minuend",
    "factor",
    "subtract",
    "divide",
    "both sides",
    "inverse",
    "combined with",
)
BG_FORBIDDEN = (
    "съчетано",
    "разпрострим",
    "се отнеме",
)


def make_unknown_context(
    *,
    equation="x + 7 = 12",
    form="x+a=b",
    language="en",
    exercise_completed=False,
    extra_metadata=None,
    problem_statement=None,
) -> TutorQuestionContext:
    statement = problem_statement or (
        "Find the integer x that makes this true: "
        f"{equation}"
        if language != "bg"
        else (
            "Намерете цялото число x, за което е вярно: "
            f"{equation}"
        )
    )
    metadata = {
        "form": form,
        "equation": equation,
        "exercise_completed": exercise_completed,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return TutorQuestionContext(
        language=language,
        subject="mathematics",
        domain="primary_school",
        topic="unknown_numbers",
        problem_id="grade4_unknown_number_test",
        problem_title="Find the unknown number",
        problem_statement=statement,
        current_step=2,
        total_steps=2,
        current_prompt=f"What is x in {equation}?",
        expected_input_type="number",
        tutor_metadata=metadata,
    )


def _assert_no_evaluated_unknown(text: str, x: int) -> None:
    assert not re.search(
        rf"(?:so |следователно )?x\s*=\s*{x}(?!\d)",
        text.lower(),
    )
    assert "check:" not in text.lower()
    assert "проверка:" not in text.lower()


def _assert_language_clean(text: str, language: str) -> None:
    lowered = text.lower()
    for phrase in BG_FORBIDDEN:
        assert phrase not in lowered, text
    if language == "en":
        assert CYRILLIC.search(text) is None, text
        return
    for term in ENGLISH_MATH_TERMS:
        assert term not in lowered, text


def assert_addition_explanation_uses_parameters():
    context = make_unknown_context()
    facts = extract_unknown_number_facts(context)
    assert facts is not None
    assert facts["a"] == 7
    assert facts["b"] == 12
    assert facts["x"] == 5
    assert facts["equation"] == "x + 7 = 12"
    assert facts["left_undo"] == "x + 7 - 7"
    assert facts["right_undo"] == "12 - 7"
    assert facts["x"] + facts["a"] == facts["b"]

    method = match_unknown_number_explanation(
        "How do I find x?",
        context,
    )
    assert method is not None
    assert "unknown addend" in method
    assert "Subtraction is the inverse of addition." in method
    assert "Subtract 7 from both sides:" in method
    assert "    x + 7 - 7 = 12 - 7" in method
    assert "    x = 12 - 7" in method
    _assert_no_evaluated_unknown(method, 5)
    _assert_language_clean(method, "en")

    complete = match_unknown_number_explanation(
        "Show the complete solution",
        context,
    )
    assert complete is not None
    assert method in complete
    assert "So x = 5." in complete
    assert "Check: 5 + 7 = 12." in complete
    _assert_language_clean(complete, "en")

    bulgarian = match_unknown_number_explanation(
        "Как да намеря x?",
        make_unknown_context(language="bg"),
    )
    assert bulgarian is not None
    assert "неизвестното събираемо" in bulgarian
    assert "Извадете 7 от двете страни:" in bulgarian
    assert "    x + 7 - 7 = 12 - 7" in bulgarian
    assert "    x = 12 - 7" in bulgarian
    _assert_no_evaluated_unknown(bulgarian, 5)
    _assert_language_clean(bulgarian, "bg")


def assert_subtraction_and_multiplication_explanations():
    sub_context = make_unknown_context(
        equation="x - 7 = 5",
        form="x-a=b",
    )
    sub_facts = extract_unknown_number_facts(sub_context)
    assert sub_facts["x"] == 12
    assert sub_facts["x"] - 7 == 5
    sub_method = build_unknown_number_explanation(
        sub_facts,
        "en",
        complete=False,
    )
    assert "unknown minuend" in sub_method
    assert "Addition is the inverse of subtraction." in sub_method
    assert "Add 7 to both sides:" in sub_method
    assert "    x - 7 + 7 = 5 + 7" in sub_method
    assert "    x = 5 + 7" in sub_method
    _assert_no_evaluated_unknown(sub_method, 12)

    sub_complete = build_unknown_number_explanation(
        sub_facts,
        "bg",
        complete=True,
    )
    assert "неизвестното умаляемо" in sub_complete
    assert "Прибавете 7 към двете страни:" in sub_complete
    assert "Следователно x = 12." in sub_complete
    assert "Проверка: 12 - 7 = 5." in sub_complete
    _assert_language_clean(sub_complete, "bg")

    mul_context = make_unknown_context(
        equation="11 × x = 132",
        form="a*x=b",
    )
    mul_facts = extract_unknown_number_facts(mul_context)
    assert mul_facts["a"] == 11
    assert mul_facts["b"] == 132
    assert mul_facts["x"] == 12
    assert 11 * 12 == 132
    mul_method = match_unknown_number_explanation(
        "Explain the inverse operation",
        mul_context,
    )
    assert mul_method is not None
    assert "unknown factor" in mul_method
    assert "Division is the inverse of multiplication." in (
        mul_method
    )
    assert "Divide both sides by the known factor 11:" in (
        mul_method
    )
    assert "    (11 × x) ÷ 11 = 132 ÷ 11" in mul_method
    assert "    x = 132 ÷ 11" in mul_method
    _assert_no_evaluated_unknown(mul_method, 12)

    mul_complete = match_unknown_number_explanation(
        "What is x?",
        mul_context,
    )
    assert "So x = 12." in mul_complete
    assert "Check: 11 × 12 = 132." in mul_complete
    bg_mul = build_unknown_number_explanation(
        mul_facts,
        "bg",
        complete=True,
    )
    assert "неизвестният множител" in bg_mul
    assert "Разделете двете страни на известния множител 11:" in (
        bg_mul
    )
    assert "Следователно x = 12." in bg_mul
    assert "Проверка: 11 × 12 = 132." in bg_mul
    _assert_language_clean(bg_mul, "bg")


def assert_generic_subtraction_template_is_not_used():
    mul = match_unknown_number_explanation(
        "How do I solve this?",
        make_unknown_context(
            equation="11 × x = 132",
            form="a*x=b",
        ),
    )
    assert mul is not None
    assert "Subtract" not in mul
    assert "Извадете" not in mul
    assert "÷" in mul


def assert_complete_after_exercise_completion():
    completed = match_unknown_number_explanation(
        "How do I solve this?",
        make_unknown_context(exercise_completed=True),
    )
    assert completed is not None
    assert "So x = 5." in completed
    assert "Check: 5 + 7 = 12." in completed
    method = match_unknown_number_explanation(
        "How do I solve this?",
        make_unknown_context(exercise_completed=False),
    )
    assert method is not None
    assert "So x = 5." not in method
    unrelated = match_unknown_number_explanation(
        "Where are equations used in real life?",
        make_unknown_context(exercise_completed=True),
    )
    assert unrelated is None


def assert_vocabulary_definitions_are_local():
    mul = make_unknown_context(
        equation="7 × x = 35",
        form="a*x=b",
        language="bg",
    )
    facts = extract_unknown_number_facts(mul)
    assert facts["x"] == 5
    factor = match_unknown_number_explanation(
        "Какво е множител?",
        mul,
    )
    assert factor is not None
    assert match_vocabulary_term("Какво е множител?") == (
        "factor"
    )
    assert "множители" in factor
    assert "произведение" in factor
    assert "7 × x = 35" in factor
    assert "числото 7 е известният множител" in factor
    assert "x е неизвестният множител" in factor
    assert "35 е произведението" in factor
    assert "Помисли кое число трябва да умножим по 7" in (
        factor
    )
    assert "Разделете" not in factor
    assert "x = 35 ÷ 7" not in factor
    _assert_no_evaluated_unknown(factor, 5)
    _assert_language_clean(factor, "bg")

    meaning = match_unknown_number_explanation(
        "Какво означава множител?",
        mul,
    )
    assert meaning is not None
    assert "множители" in meaning

    product = match_unknown_number_explanation(
        "Какво е произведение?",
        mul,
    )
    assert product is not None
    assert "Произведението е резултатът" in product
    assert "35 е произведението" in product
    _assert_no_evaluated_unknown(product, 5)

    add = make_unknown_context(
        equation="x + 7 = 12",
        form="x+a=b",
        language="bg",
    )
    addend = match_unknown_number_explanation(
        "Какво е събираемо?",
        add,
    )
    assert addend is not None
    assert "събираеми" in addend
    assert "известното събираемо" in addend
    assert "Разделете" not in addend
    _assert_no_evaluated_unknown(addend, 5)

    english_addend = match_unknown_number_explanation(
        "What is an addend?",
        make_unknown_context(),
    )
    assert english_addend is not None
    assert "addends" in english_addend
    assert "known addend" in english_addend
    _assert_language_clean(english_addend, "en")

    sub = make_unknown_context(
        equation="x - 7 = 5",
        form="x-a=b",
        language="bg",
    )
    subtrahend = match_unknown_number_explanation(
        "Какво е умалител?",
        sub,
    )
    assert subtrahend is not None
    assert "умалител" in subtrahend
    assert "известният умалител" in subtrahend
    _assert_no_evaluated_unknown(subtrahend, 12)

    english_sub = match_unknown_number_explanation(
        "What is a subtrahend?",
        make_unknown_context(
            equation="x - 7 = 5",
            form="x-a=b",
        ),
    )
    assert "subtrahend" in english_sub
    assert "minuend" in english_sub

    english_factor = match_unknown_number_explanation(
        "What is a factor in multiplication?",
        make_unknown_context(
            equation="7 × x = 35",
            form="a*x=b",
        ),
    )
    assert english_factor is not None
    assert "known factor" in english_factor
    assert "product" in english_factor
    assert "Divide both sides" not in english_factor
    _assert_no_evaluated_unknown(english_factor, 5)

    meaning_en = match_unknown_number_explanation(
        "What does factor mean?",
        make_unknown_context(
            equation="7 × x = 35",
            form="a*x=b",
        ),
    )
    assert meaning_en is not None
    assert "factors" in meaning_en
    english_product = match_unknown_number_explanation(
        "What is a product?",
        make_unknown_context(
            equation="7 × x = 35",
            form="a*x=b",
        ),
    )
    assert english_product is not None
    assert "The product is the result" in english_product
    assert "35 is the product" in english_product
    _assert_no_evaluated_unknown(english_product, 5)


def assert_definition_intent_precedes_method():
    context = make_unknown_context(
        equation="7 × x = 35",
        form="a*x=b",
        language="bg",
    )
    definition = match_unknown_number_explanation(
        "Обясни какво е множител",
        context,
    )
    assert definition is not None
    assert "известният множител" in definition
    assert "x = 35 ÷ 7" not in definition
    method = match_unknown_number_explanation(
        "Как да реша уравнението?",
        context,
    )
    assert method is not None
    assert "x = 35 ÷ 7" in method
    assert "Следователно x = 5." not in method
    english_method = match_unknown_number_explanation(
        "How do I solve this?",
        make_unknown_context(
            equation="7 × x = 35",
            form="a*x=b",
        ),
    )
    assert "x = 35 ÷ 7" in english_method
    assert "So x = 5." not in english_method


def assert_unsupported_terms_are_not_locally_defined():
    context = make_unknown_context(
        equation="7 × x = 35",
        form="a*x=b",
        language="bg",
    )
    assert match_vocabulary_term("Какво е дроб?") is None
    assert match_unknown_number_explanation(
        "Какво е дроб?",
        context,
    ) is None
    assert match_unknown_number_explanation(
        "Where are equations used in real life?",
        context,
    ) is None


def assert_ordinary_hints_do_not_reveal_x():
    problem = generate_unknown_number_problem(
        difficulty=3,
        seed=8,
        language="en",
    )
    x = problem.known["x"]
    engine = PrimarySchoolTutorEngine(problem=problem)
    first = engine.request_hint()
    assert first.status == "hint"
    assert str(x) not in first.feedback
    assert f"x = {x}" not in first.feedback
    engine.submit(
        StudentSubmission(
            answer=str(problem.solution_steps[0].expected_answer),
            input_type="number",
        )
    )
    second = engine.request_hint()
    assert str(x) not in second.feedback
    assert "So x =" not in second.feedback
    assert problem.known["equation"] not in second.feedback or (
        str(x) not in second.feedback
    )


def assert_generated_prompts_use_operation_terms():
    seen = set()
    for difficulty in (1, 2, 3):
        for seed in range(30):
            english = generate_unknown_number_problem(
                difficulty=difficulty,
                seed=seed,
                language="en",
            )
            bulgarian = generate_unknown_number_problem(
                difficulty=difficulty,
                seed=seed,
                language="bg",
            )
            form = english.known["form"]
            seen.add(form)
            prompt_en = english.solution_steps[0].prompt
            prompt_bg = bulgarian.solution_steps[0].prompt
            hint_en = english.solution_steps[1].hint or ""
            hint_bg = bulgarian.solution_steps[1].hint or ""
            assert "combined with" not in prompt_en.lower()
            assert "съчетано" not in prompt_bg.lower()
            assert set(
                english.solution_steps[0].metadata["params"]
            ) == {"equation"}
            assert set(
                english.solution_steps[1].metadata["params"]
            ) == {"equation"}
            x = english.known["x"]
            assert str(x) not in hint_en
            assert str(x) not in hint_bg
            if form == "x+a=b":
                assert "known addend" in prompt_en
                assert "събираемо" in prompt_bg
            elif form == "x-a=b":
                assert "known subtrahend" in prompt_en
                assert "умалител" in prompt_bg
            else:
                assert "known factor" in prompt_en
                assert "множител" in prompt_bg
    assert seen == {"x+a=b", "x-a=b", "a*x=b"}
    for language, table in PRIMARY_SCHOOL_TEXT.items():
        for key, text in table.items():
            if not key.startswith("gen.unknown."):
                continue
            _assert_language_clean(text, language)
            assert "съчетано" not in text
            assert "combined with" not in text.lower()


def assert_general_unknown_questions_use_model():
    model = FakeTutorModelProvider()
    engine = GeneralTutorQuestionEngine(
        model_provider=model,
        web_search_provider=FakeWebSearchProvider(),
    )
    context = make_unknown_context()
    result = engine.answer(
        TutorQuestionRequest(
            question="Where are equations used in real life?",
        ),
        context,
    )
    assert result.answer_source == "model"
    assert result.route == QuestionRoute.MODEL_ONLY
    assert len(model.calls) == 1
    public_meta = model.calls[0]["context"]["tutor_metadata"]
    assert "x" not in public_meta
    assert "expected_answer" not in public_meta
    assert "final_answer" not in public_meta
    assert "step_specs" not in public_meta
    sanitized = sanitize_tutor_metadata(
        {
            "form": "x+a=b",
            "equation": "x + 7 = 12",
            "x": 5,
            "expected_answer": 5,
            "final_answer": 5,
            "step_specs": [{"expected_answer": 5}],
        }
    )
    assert sanitized["equation"] == "x + 7 = 12"
    assert "x" not in sanitized
    assert "expected_answer" not in sanitized
    assert "final_answer" not in sanitized
    assert "step_specs" not in sanitized

    local = engine.answer(
        TutorQuestionRequest(question="How do I solve this?"),
        context,
    )
    assert local.answer_source == "local"
    assert local.route == QuestionRoute.LOCAL_ONLY
    assert "x = 12 - 7" in local.answer
    assert "So x = 5." not in local.answer
    assert len(model.calls) == 1


def assert_ode_routing_is_unchanged():
    model = FakeTutorModelProvider()
    engine = GeneralTutorQuestionEngine(
        model_provider=model,
        web_search_provider=FakeWebSearchProvider(),
    )
    ode = TutorQuestionContext(
        language="bg",
        subject="mathematics",
        domain="ode",
        topic="first_order_linear",
        problem_id="linear_first_order_fixed",
        problem_title="First-Order Linear ODE",
        problem_statement="Solve dy/dx + (-2)*y = 2",
        current_step=3,
        total_steps=8,
        current_prompt="Find the integrating factor mu(x).",
        expected_input_type="math",
        tutor_metadata={
            "stage": "find_integrating_factor",
            "p_expression": "-2",
            "q_expression": "2",
        },
    )
    result = engine.answer(
        TutorQuestionRequest(
            question="Може ли да се реши по друг начин?",
        ),
        ode,
    )
    assert result.answer_source == "local"
    assert "разделяне на променливите" in result.answer
    assert match_unknown_number_explanation(
        "How do I find x?",
        ode,
    ) is None
    assert match_local_concept(
        "How do I find x?",
        make_unknown_context(),
    ) is not None


def assert_pst_templates_are_parameterized():
    add = pst(
        "en",
        "gen.unknown.method.add",
        equation="x + 7 = 12",
        a=7,
        b=12,
        left_undo="x + 7 - 7",
        right_undo="12 - 7",
    )
    assert "{a}" not in add
    assert "{b}" not in add
    assert "x = 12 - 7" in add


def main():
    assert_addition_explanation_uses_parameters()
    assert_subtraction_and_multiplication_explanations()
    assert_generic_subtraction_template_is_not_used()
    assert_complete_after_exercise_completion()
    assert_vocabulary_definitions_are_local()
    assert_definition_intent_precedes_method()
    assert_unsupported_terms_are_not_locally_defined()
    assert_ordinary_hints_do_not_reveal_x()
    assert_generated_prompts_use_operation_terms()
    assert_general_unknown_questions_use_model()
    assert_ode_routing_is_unchanged()
    assert_pst_templates_are_parameterized()
    print("unknown_number_guidance tests passed")


if __name__ == "__main__":
    main()
