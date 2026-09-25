from dataclasses import replace

from src.core.i18n.logical_reasoning import lrt
from src.core.i18n.question import question_fallback_message
from src.core.question_engine.contracts import (
    QuestionRoute,
    TutorQuestionContext,
    TutorQuestionRequest,
)
from src.core.question_engine.context import sanitize_tutor_metadata
from src.core.question_engine.engine import GeneralTutorQuestionEngine
from src.core.question_engine.guided_questions import (
    GuidedQuestionError,
    list_suggested_questions,
    resolve_guided_question,
)
from src.core.question_engine.providers import (
    FakeTutorModelProvider,
    NullTutorModelProvider,
)
from src.core.tutor_engine.concept_guidance.logical_reasoning_guidance import (
    build_logical_guidance_context,
    match_logical_answer_format_intent,
    match_logical_method_intent,
    match_logical_reasoning_explanation,
    match_logical_terminology_intent,
)
from src.core.tutor_engine.contracts import StudentSubmission
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    generate_distribution_puzzle,
    generate_logic_detective,
    generate_number_detective,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.compile import (
    compile_logical_reasoning_puzzle,
    discloses_protected,
    integer_tokens,
    protected_answers_from,
)


def _live(step_number):
    return type("Live", (), {"current_step": step_number})()


def _context(problem, extra=None, step=None):
    step = step or problem.solution_steps[0]
    metadata = {
        "family": problem.known.get("family"),
        "milestone": (step.metadata or {}).get("milestone"),
        "purpose": (step.metadata or {}).get("purpose"),
        "params": dict((step.metadata or {}).get("params") or {}),
        "logic_params": dict((step.metadata or {}).get("params") or {}),
        "clue_kinds": list(problem.known.get("clue_kinds") or ()),
        "visible_numbers": list(problem.known.get("visible_numbers") or ()),
        "public_clues": list(problem.known.get("public_clues") or ()),
    }
    if extra:
        metadata.update(extra)
    return TutorQuestionContext(
        language=problem.language,
        subject="mathematics",
        domain="primary_school",
        topic="logical_reasoning",
        problem_id=problem.problem_id,
        problem_title=problem.title,
        problem_statement=problem.problem_text,
        current_step=step.step_number,
        total_steps=problem.get_number_of_steps(),
        current_prompt=step.prompt,
        expected_input_type="number",
        tutor_metadata=metadata,
    )


def _compile_family(family, difficulty=1, seed=5, language="en"):
    generators = {
        "number_detective": generate_number_detective,
        "distribution_puzzles": generate_distribution_puzzle,
        "logic_detective": generate_logic_detective,
    }
    puzzle = generators[family](difficulty=difficulty, seed=seed)
    return puzzle, compile_logical_reasoning_puzzle(puzzle, language)


def assert_progressive_hints(family):
    puzzle, problem = _compile_family(family, seed=8)
    engine = PrimarySchoolTutorEngine(problem)
    step = problem.solution_steps[0]
    visible = set(problem.known.get("visible_numbers") or ())
    protected = protected_answers_from(problem, 1)
    first = engine.request_hint()
    assert first.metadata["hint_level"] == 1
    assert first.hint_available is True
    assert not discloses_protected(first.feedback, protected, visible)
    second = engine.request_hint()
    assert second.metadata["hint_level"] == 2
    assert first.feedback != second.feedback
    assert not discloses_protected(second.feedback, protected, visible)
    third = engine.request_hint()
    assert third.metadata["hint_level"] == 3
    assert third.metadata["hint_exhausted"] is True
    assert third.hint_available is False
    assert not discloses_protected(third.feedback, protected, visible)
    fourth = engine.request_hint()
    assert fourth.hint_available is False
    assert fourth.metadata["hint_counted"] is False
    assert engine.session.get_hints_for_current_step() == 3
    print(f"{family} hints:")
    print("  L1:", first.feedback)
    print("  L2:", second.feedback)
    print("  L3:", third.feedback)
    empty = engine.submit(StudentSubmission(""))
    assert empty.status == "incorrect"
    assert empty.metadata["error_type"] == "empty_answer"
    assert empty.metadata.get("guidance_mode") == "independent"
    assert engine.session.get_math_errors_for_current_step() == 0
    assert engine.session.get_hints_for_current_step() == 3
    wrong = engine.submit(StudentSubmission("0"))
    assert wrong.status == "incorrect"
    assert engine.session.get_hints_for_current_step() == 3
    if (problem.solution_steps[0].expected_answer != 0):
        assert wrong.metadata.get("guidance_mode") == "independent"
        assert engine.session.get_math_errors_for_current_step() == 1
    live = _live(1)
    allowed = {
        item.question_id
        for item in list_suggested_questions(
            topic="logical_reasoning",
            problem=problem,
            live_response=live,
            language="en",
            completed=False,
        )
    }
    before = engine.session.get_hints_for_current_step()
    resolve_guided_question(
        next(iter(allowed)),
        allowed_ids=allowed,
        topic="logical_reasoning",
        problem=problem,
        live_response=live,
        context=_context(problem),
        language="en",
    )
    assert engine.session.get_hints_for_current_step() == before
    engine.submit(StudentSubmission(str(step.expected_answer)))
    if problem.get_number_of_steps() > 1:
        nxt = engine.request_hint()
        assert nxt.metadata["hint_level"] == 1
        assert engine.session.get_hints_for_current_step() == 1


def assert_distribution_hints_all_steps():
    for difficulty in (1, 2, 3):
        for seed in (1, 5, 8, 12):
            for language in ("en", "bg"):
                puzzle, problem = _compile_family(
                    "distribution_puzzles",
                    difficulty=difficulty,
                    seed=seed,
                    language=language,
                )
                engine = PrimarySchoolTutorEngine(problem)
                visible = set(problem.known.get("visible_numbers") or ())
                for step in problem.solution_steps:
                    protected = protected_answers_from(
                        problem,
                        step.step_number,
                    )
                    hidden = set(protected) - visible
                    hints = []
                    for _ in range(3):
                        result = engine.request_hint()
                        hints.append(result.feedback)
                        assert not discloses_protected(
                            result.feedback,
                            protected,
                            visible,
                        )
                        leaked = set(
                            integer_tokens(result.feedback)
                        ) & hidden
                        assert not leaked, (
                            step.step_number,
                            leaked,
                            result.feedback,
                        )
                    fourth = engine.request_hint()
                    assert fourth.metadata["hint_exhausted"] is True
                    assert fourth.metadata["hint_counted"] is False
                    assert engine.session.get_hints_for_current_step() == 3
                    bodies = [
                        text.replace(
                            "This is the last hint for this step.",
                            "",
                        ).replace(
                            "Това е последният подсказ за тази стъпка.",
                            "",
                        ).strip()
                        for text in hints
                    ]
                    assert len(set(bodies)) == 3, (
                        difficulty,
                        seed,
                        language,
                        step.step_number,
                        bodies,
                    )
                    assert "= ?" in hints[2] or "=?" in hints[2].replace(" ", ""), (
                        difficulty,
                        seed,
                        language,
                        step.step_number,
                        (step.metadata or {}).get("milestone"),
                        hints[2],
                    )
                    if language == "bg":
                        assert "the " not in hints[2].lower()
                    wrong = engine.submit(StudentSubmission("0"))
                    assert wrong.status == "incorrect"
                    assert engine.session.get_hints_for_current_step() == 3
                    engine.submit(
                        StudentSubmission(str(step.expected_answer))
                    )


def assert_guided_questions():
    _, number = _compile_family("number_detective")
    _, dist = _compile_family("distribution_puzzles")
    _, logic = _compile_family("logic_detective")
    live = _live(1)
    number_ids = [
        item.question_id
        for item in list_suggested_questions(
            topic="logical_reasoning",
            problem=number,
            live_response=live,
            language="en",
            completed=False,
        )
    ]
    dist_ids = [
        item.question_id
        for item in list_suggested_questions(
            topic="logical_reasoning",
            problem=dist,
            live_response=live,
            language="en",
            completed=False,
        )
    ]
    logic_ids = [
        item.question_id
        for item in list_suggested_questions(
            topic="logical_reasoning",
            problem=logic,
            live_response=live,
            language="en",
            completed=False,
        )
    ]
    assert "logic.known" in number_ids
    assert "logic.eliminate" in number_ids
    assert "logic.eliminate" not in dist_ids
    assert "logic.first_clue" in dist_ids
    assert "logic.check" in logic_ids
    label, answer = resolve_guided_question(
        "logic.known",
        allowed_ids=set(number_ids),
        topic="logical_reasoning",
        problem=number,
        live_response=live,
        context=_context(number),
        language="en",
    )
    assert "What information is given?" == label
    assert "clues" in answer.lower()
    protected = protected_answers_from(number, 1)
    visible = set(number.known.get("visible_numbers") or ())
    assert not discloses_protected(answer, protected, visible)
    try:
        resolve_guided_question(
            "logic.eliminate",
            allowed_ids=set(dist_ids),
            topic="logical_reasoning",
            problem=dist,
            live_response=live,
            context=_context(dist),
            language="en",
        )
        raise AssertionError("stale eliminate id should be rejected")
    except GuidedQuestionError:
        pass
    try:
        resolve_guided_question(
            "story.phrase.doubled",
            allowed_ids=set(number_ids),
            topic="logical_reasoning",
            problem=number,
            live_response=live,
            context=_context(number),
            language="en",
        )
        raise AssertionError("unknown id should be rejected")
    except GuidedQuestionError:
        pass
    bg_label, bg_answer = resolve_guided_question(
        "logic.unknown",
        allowed_ids=set(number_ids),
        topic="logical_reasoning",
        problem=number,
        live_response=live,
        context=_context(number),
        language="bg",
    )
    assert "намерим" in bg_label.lower() or "Какво" in bg_label
    assert bg_answer


def assert_free_form_safety():
    puzzle, problem = _compile_family("logic_detective", difficulty=3)
    context = _context(problem)
    engine = GeneralTutorQuestionEngine(
        model_provider=FakeTutorModelProvider(
            text="The blue object is in box 3."
        ),
    )
    english = engine.answer(
        TutorQuestionRequest(question="How do I solve this step?"),
        context,
    )
    assert english.answer_source == "local"
    assert "box 3" not in english.answer.lower()
    bulgarian = engine.answer(
        TutorQuestionRequest(question="Как да намеря отговора на тази стъпка?"),
        context,
    )
    assert bulgarian.answer_source == "local"
    clue = engine.answer(
        TutorQuestionRequest(question="Which clue should I use?"),
        context,
    )
    assert clue.answer_source == "local"
    eliminate = engine.answer(
        TutorQuestionRequest(question="How do I eliminate the wrong options?"),
        context,
    )
    assert eliminate.answer_source == "local"
    bg_clue = engine.answer(
        TutorQuestionRequest(question="Коя улика да използвам?"),
        context,
    )
    assert bg_clue.answer_source == "local"
    bg_elim = engine.answer(
        TutorQuestionRequest(question="Как да изключа грешните възможности?"),
        context,
    )
    assert bg_elim.answer_source == "local"
    fallback = match_logical_reasoning_explanation(
        "How do I solve this step?",
        TutorQuestionContext(
            language="en",
            subject="mathematics",
            domain="primary_school",
            topic="logical_reasoning",
            problem_id="x",
            problem_title="x",
            problem_statement="x",
            current_step=1,
            total_steps=1,
            current_prompt="x",
            expected_input_type="number",
            tutor_metadata={},
        ),
    )
    assert fallback is not None
    general = engine.answer(
        TutorQuestionRequest(question="Where is logic used in real life?"),
        context,
    )
    assert general.answer_source == "model"
    protected = protected_answers_from(problem, 1)
    visible = set(problem.known.get("visible_numbers") or ())
    for result in (english, bulgarian, clue, eliminate, bg_clue, bg_elim):
        assert not discloses_protected(result.answer, protected, visible)
    assert match_logical_method_intent("How do I solve this step?")
    assert match_logical_reasoning_explanation(
        "How do I solve this step?",
        TutorQuestionContext(
            language="en",
            subject="mathematics",
            domain="ode",
            topic="first_order_linear",
            problem_id="ode",
            problem_title="ODE",
            problem_statement="Solve y",
            current_step=1,
            total_steps=4,
            current_prompt="x",
            expected_input_type="math",
            tutor_metadata={},
        ),
    ) is None


BROWSER_FORMAT_QUESTION = (
    "Should I enter the answer for two boxes separated by comma?"
)

ENGLISH_FORMAT_QUESTIONS = (
    BROWSER_FORMAT_QUESTION,
    "Should I enter both answers separated by a comma?",
    "Should I enter the answers for two boxes?",
    "Do I need to enter two numbers?",
    "Should I enter one number?",
    "Can I enter both numbers together?",
)

BULGARIAN_FORMAT_QUESTIONS = (
    "Трябва ли да въведа двата отговора, разделени със запетая?",
    "Трябва ли да въведа две числа?",
    "Трябва ли да въведа едно число?",
    "Мога ли да въведа двата отговора заедно?",
)

UNRELATED_QUESTIONS = (
    "Where is logic used in real life?",
    "What is a prime number?",
    "How many items are in the first box?",
    "What number should I find?",
    "Should I enter the number?",
    "What is the answer?",
)


def _failing_model():
    return FakeTutorModelProvider(
        error=AssertionError("model must not be called"),
    )


def _hidden_answers(problem):
    hidden = []
    visible = set(problem.known.get("visible_numbers") or ())
    for step in problem.solution_steps:
        value = step.expected_answer
        if isinstance(value, int) and value not in visible:
            hidden.append(value)
    return tuple(hidden)


def _assert_format_result(result, *, language="en", boxes=False):
    assert result.answer_source == "local"
    assert result.route == QuestionRoute.LOCAL_ONLY
    answer = result.answer
    lowered = answer.lower()
    fallback = question_fallback_message(language)
    assert answer != fallback
    assert "can't provide a reliable extended answer" not in lowered
    assert "надежден разширен отговор" not in lowered
    if language == "en":
        assert "one number" in lowered
        assert "current step" in lowered
        if boxes:
            assert "box" in lowered
        else:
            assert "box quantities" not in lowered
    else:
        assert "едно число" in lowered
        assert "стъпка" in lowered
        latin = [
            character
            for character in answer
            if "a" <= character.lower() <= "z"
        ]
        assert not latin, answer


def _assert_no_solution(answer, problem):
    protected = protected_answers_from(problem, 1)
    visible = set(problem.known.get("visible_numbers") or ())
    assert not discloses_protected(answer, protected, visible)
    lowered = f" {answer.lower()} "
    for value in _hidden_answers(problem):
        assert f" {value} " not in lowered
        assert f" {value}." not in lowered
        assert f" {value}," not in lowered


def assert_answer_format_questions():
    _, distribution = _compile_family("distribution_puzzles", seed=5)
    _, number = _compile_family("number_detective", seed=5)
    dist_context = _context(distribution)
    number_context = _context(number)
    engine = GeneralTutorQuestionEngine(
        model_provider=_failing_model(),
    )
    null_engine = GeneralTutorQuestionEngine(
        model_provider=NullTutorModelProvider(),
    )

    browser = engine.answer(
        TutorQuestionRequest(question=BROWSER_FORMAT_QUESTION),
        dist_context,
    )
    _assert_format_result(browser, boxes=True)
    _assert_no_solution(browser.answer, distribution)
    assert match_logical_answer_format_intent(BROWSER_FORMAT_QUESTION)
    assert match_logical_reasoning_explanation(
        BROWSER_FORMAT_QUESTION,
        dist_context,
    ) == browser.answer

    for question in ENGLISH_FORMAT_QUESTIONS:
        result = engine.answer(
            TutorQuestionRequest(question=question),
            dist_context,
        )
        _assert_format_result(result, boxes=True)
        _assert_no_solution(result.answer, distribution)

    bg_context = replace(dist_context, language="bg")
    bg_engine = GeneralTutorQuestionEngine(
        model_provider=_failing_model(),
    )
    for question in BULGARIAN_FORMAT_QUESTIONS:
        assert match_logical_answer_format_intent(question)
        result = bg_engine.answer(
            TutorQuestionRequest(question=question),
            bg_context,
        )
        _assert_format_result(result, language="bg", boxes=True)
        _assert_no_solution(result.answer, distribution)

    unavailable = null_engine.answer(
        TutorQuestionRequest(question=BROWSER_FORMAT_QUESTION),
        dist_context,
    )
    _assert_format_result(unavailable, boxes=True)
    assert unavailable.metadata.get("model_unavailable") is not True
    assert engine.model_provider.calls == []
    assert bg_engine.model_provider.calls == []

    generic = engine.answer(
        TutorQuestionRequest(question="Should I enter one number?"),
        number_context,
    )
    _assert_format_result(generic, boxes=False)
    _assert_no_solution(generic.answer, number)

    for question in UNRELATED_QUESTIONS:
        assert not match_logical_answer_format_intent(question)
    general = GeneralTutorQuestionEngine(
        model_provider=FakeTutorModelProvider(text="MODEL_GENERAL"),
    ).answer(
        TutorQuestionRequest(question="Where is logic used in real life?"),
        dist_context,
    )
    assert general.answer_source == "model"
    number_only = GeneralTutorQuestionEngine(
        model_provider=FakeTutorModelProvider(text="MODEL_NUMBER"),
    ).answer(
        TutorQuestionRequest(question="What is a prime number?"),
        dist_context,
    )
    assert number_only.answer_source == "model"

    other_type = match_logical_reasoning_explanation(
        BROWSER_FORMAT_QUESTION,
        TutorQuestionContext(
            language="en",
            subject="mathematics",
            domain="primary_school",
            topic="logical_reasoning",
            problem_id="x",
            problem_title="x",
            problem_statement="x",
            current_step=1,
            total_steps=1,
            current_prompt="x",
            expected_input_type="math",
            tutor_metadata={"family": "distribution_puzzles"},
        ),
    )
    assert other_type is None

    example = None
    for seed in range(1, 80):
        _, candidate = _compile_family(
            "distribution_puzzles",
            difficulty=1,
            seed=seed,
        )
        answers = [
            step.expected_answer
            for step in candidate.solution_steps
        ]
        if {16, 13, 8}.issubset(set(answers)):
            example = candidate
            break
    if example is None:
        example = distribution
    example_result = engine.answer(
        TutorQuestionRequest(question=BROWSER_FORMAT_QUESTION),
        _context(example),
    )
    _assert_format_result(example_result, boxes=True)
    _assert_no_solution(example_result.answer, example)
    lowered = example_result.answer.lower()
    for forbidden in (16, 13, 8):
        assert str(forbidden) not in lowered


BROWSER_TERMINOLOGY_QUESTION = (
    "What does 'scaled box' mean in this problem? "
    "Explain it without giving me the answer."
)
ENGLISH_TERMINOLOGY_QUESTIONS = (
    BROWSER_TERMINOLOGY_QUESTION,
    "What does scaled box mean?",
    "What is the scaled box?",
    "What does scaled mean in this problem?",
    "Which box is being multiplied?",
)
BULGARIAN_TERMINOLOGY_QUESTIONS = (
    "Какво означава умножената кутия?",
    "Коя кутия е умножена?",
    "Какво означава кутията с умножение?",
)


def _times_clue(problem):
    for clue in problem.known.get("public_clues") or ():
        if clue.get("kind") == "times_as_many":
            return clue
    return None


def _box_name(box, language):
    return lrt(language, f"gen.logic.box.{box}")


def _factor_word(factor, language):
    word = lrt(language, f"gen.logic.factor_word.{factor}")
    if word == f"gen.logic.factor_word.{factor}":
        return str(factor)
    return word


def _assert_no_hidden_answers(text, problem, step_number):
    visible = set(problem.known.get("visible_numbers") or ())
    hidden = set(protected_answers_from(problem, step_number)) - visible
    leaked = set(integer_tokens(text)) & hidden
    assert not leaked, (leaked, text)
    lowered = text.lower()
    fallback = question_fallback_message(problem.language)
    assert text != fallback
    assert "can't provide a reliable extended answer" not in lowered
    assert "надежден разширен отговор" not in lowered


def _assert_identifies_scaled_box(text, problem, language):
    times = _times_clue(problem)
    assert times is not None
    left_name = _box_name(times["left"], language)
    right_name = _box_name(times["right"], language)
    factor = times["factor"]
    word = _factor_word(factor, language)
    assert left_name in text, (left_name, text)
    assert right_name in text, (right_name, text)
    assert word in text or str(factor) in text, (word, factor, text)
    assert right_name != left_name


def assert_distribution_step_wording():
    for seed in (1, 5, 8, 12):
        for language in ("en", "bg"):
            _, problem = _compile_family(
                "distribution_puzzles",
                difficulty=3,
                seed=seed,
                language=language,
            )
            times = _times_clue(problem)
            assert times is not None
            left_name = _box_name(times["left"], language)
            right_name = _box_name(times["right"], language)
            word = _factor_word(times["factor"], language)
            extra_step = problem.solution_steps[0]
            assert extra_step.metadata["milestone"] == "extra_from_scaled"
            prompt = extra_step.prompt
            assert "scaled box" not in prompt.lower()
            assert "кутията с умножение" not in prompt
            assert left_name in prompt
            assert right_name in prompt
            assert word in prompt or str(times["factor"]) in prompt
            if language == "en":
                assert "times as many" in prompt
            _assert_no_hidden_answers(prompt, problem, extra_step.step_number)
            total_step = problem.solution_steps[1]
            assert total_step.metadata["milestone"] == "extra_total"
            assert "combined extra amount" not in total_step.prompt.lower()
            assert left_name in total_step.prompt or _box_name(
                next(
                    clue["left"]
                    for clue in problem.known["public_clues"]
                    if clue.get("kind") == "more_than"
                ),
                language,
            ) in total_step.prompt


def assert_bulgarian_v_preposition_before_second_box():
    puzzle = generate_distribution_puzzle(difficulty=3, seed=52)
    english = compile_logical_reasoning_puzzle(puzzle, "en")
    bulgarian = compile_logical_reasoning_puzzle(puzzle, "bg")
    assert "28 items" in english.problem_text
    assert "3 times" in english.problem_text
    assert "2 more items" in english.problem_text
    extra_en = english.solution_steps[0]
    extra_bg = bulgarian.solution_steps[0]
    assert extra_en.metadata["milestone"] == "extra_from_scaled"
    assert extra_en.prompt == (
        "How much extra does the first box contain because "
        "it has three times as many items as the second box?"
    )
    assert "in the second box" not in extra_en.prompt
    assert "във" not in extra_en.prompt
    assert extra_bg.prompt == (
        "Във втората кутия има 2 допълнителни предмета. "
        "Колко допълнителни предмета се получават в "
        "първата кутия, когато умножим този брой по 3?"
    )
    assert "отколкото в втората" not in extra_bg.prompt
    assert "отколкото в втората" not in bulgarian.problem_text
    assert "пъти повече предмети, отколкото във втората кутия" in (
        bulgarian.problem_text
    )
    assert "пъти толкова" not in bulgarian.problem_text
    assert "Във втората кутия" in extra_bg.prompt
    assert "отколкото във втората кутия" in bulgarian.problem_text
    second_box = next(
        step
        for step in bulgarian.solution_steps
        if (step.metadata or {}).get("params", {}).get("box") == "box_b"
    )
    assert "има в втората" not in second_box.prompt
    assert "има във втората" in second_box.prompt
    failing = _failing_model()
    engine = GeneralTutorQuestionEngine(model_provider=failing)
    en_result = engine.answer(
        TutorQuestionRequest(
            question=BROWSER_TERMINOLOGY_QUESTION,
        ),
        _context(english),
    )
    bg_result = engine.answer(
        TutorQuestionRequest(question="Какво означава умножената кутия?"),
        _context(bulgarian),
    )
    assert en_result.answer_source == "local"
    assert bg_result.answer_source == "local"
    assert failing.calls == []
    assert en_result.answer == (
        "The scaled box is the first box. It contains "
        "three times as many items as the second box. "
        "The multiplier also applies to the extra amount. "
        "Use that relationship to work out the extra "
        "without finding the final quantities yet."
    )
    assert "във" not in en_result.answer
    assert "отколкото в втората" not in bg_result.answer
    assert "отколкото във втората кутия" in bg_result.answer
    assert bg_result.answer == (
        "Умножената кутия е първата кутия. В нея има "
        "три пъти повече предмети, отколкото във "
        "втората кутия. Същият множител важи и за "
        "излишъка. Използвайте тази връзка, за да "
        "намерите излишъка, без още да търсите крайните "
        "количества."
    )


def assert_distribution_terminology():
    failing = _failing_model()
    null_engine = GeneralTutorQuestionEngine(
        model_provider=NullTutorModelProvider(),
    )
    failing_engine = GeneralTutorQuestionEngine(
        model_provider=failing,
    )
    for seed in (1, 5, 8, 12):
        _, english = _compile_family(
            "distribution_puzzles",
            difficulty=3,
            seed=seed,
            language="en",
        )
        context = _context(english)
        tutor = PrimarySchoolTutorEngine(english)
        before_step = tutor.session.get_current_step().step_number
        before_hints = tutor.session.get_hints_for_current_step()
        result = failing_engine.answer(
            TutorQuestionRequest(question=BROWSER_TERMINOLOGY_QUESTION),
            context,
        )
        assert result.answer_source == "local"
        assert result.route == QuestionRoute.LOCAL_ONLY
        assert failing.calls == []
        _assert_identifies_scaled_box(result.answer, english, "en")
        _assert_no_hidden_answers(result.answer, english, 1)
        assert "final" in result.answer.lower() or "without" in result.answer.lower()
        null_result = null_engine.answer(
            TutorQuestionRequest(question=BROWSER_TERMINOLOGY_QUESTION),
            context,
        )
        assert null_result.answer_source == "local"
        for question in ENGLISH_TERMINOLOGY_QUESTIONS:
            asked = failing_engine.answer(
                TutorQuestionRequest(question=question),
                context,
            )
            assert asked.answer_source == "local", question
            _assert_identifies_scaled_box(asked.answer, english, "en")
            _assert_no_hidden_answers(asked.answer, english, 1)
        _, bulgarian = _compile_family(
            "distribution_puzzles",
            difficulty=3,
            seed=seed,
            language="bg",
        )
        bg_context = _context(bulgarian)
        for question in BULGARIAN_TERMINOLOGY_QUESTIONS:
            asked = failing_engine.answer(
                TutorQuestionRequest(question=question),
                bg_context,
            )
            assert asked.answer_source == "local", question
            _assert_identifies_scaled_box(asked.answer, bulgarian, "bg")
            _assert_no_hidden_answers(asked.answer, bulgarian, 1)
            assert "the " not in asked.answer
        assert tutor.session.get_current_step().step_number == before_step
        assert tutor.session.get_hints_for_current_step() == before_hints
        wrong = tutor.submit(StudentSubmission("0"))
        assert wrong.status == "incorrect"
        assert tutor.session.get_hints_for_current_step() == before_hints


def assert_distribution_guided_questions_are_contextual():
    _, number = _compile_family("number_detective")
    _, logic = _compile_family("logic_detective")
    live = _live(1)
    number_known = resolve_guided_question(
        "logic.known",
        allowed_ids={"logic.known", "logic.unknown", "logic.first_clue", "logic.eliminate"},
        topic="logical_reasoning",
        problem=number,
        live_response=live,
        context=_context(number),
        language="en",
    )[1]
    assert "written clues" in number_known.lower()
    logic_known = resolve_guided_question(
        "logic.known",
        allowed_ids={"logic.known", "logic.unknown", "logic.eliminate", "logic.check"},
        topic="logical_reasoning",
        problem=logic,
        live_response=live,
        context=_context(logic),
        language="en",
    )[1]
    assert "written clues" in logic_known.lower()
    for seed in (1, 5):
        for language in ("en", "bg"):
            _, problem = _compile_family(
                "distribution_puzzles",
                difficulty=3,
                seed=seed,
                language=language,
            )
            ids = {
                "logic.known",
                "logic.unknown",
                "logic.first_clue",
                "logic.check",
            }
            answers = []
            for question_id in (
                "logic.known",
                "logic.unknown",
                "logic.first_clue",
                "logic.check",
            ):
                _, answer = resolve_guided_question(
                    question_id,
                    allowed_ids=ids,
                    topic="logical_reasoning",
                    problem=problem,
                    live_response=live,
                    context=_context(problem),
                    language=language,
                )
                answers.append(answer)
                _assert_no_hidden_answers(answer, problem, 1)
            assert len(set(answers)) == 4, answers
            known, unknown, first, check = answers
            times = _times_clue(problem)
            left_name = _box_name(times["left"], language)
            assert left_name in known or str(times["factor"]) in known
            assert problem.solution_steps[0].prompt in unknown or left_name in unknown
            assert left_name in first or str(times["factor"]) in first
            assert "scaled box" not in check.lower()
            generic = "the given facts are the written clues"
            assert generic not in known.lower()


def assert_guidance_context_does_not_leak():
    _, problem = _compile_family("distribution_puzzles", difficulty=2)
    ctx = build_logical_guidance_context(problem, _live(1), "en")
    sanitized = sanitize_tutor_metadata(
        {
            "family": ctx.family,
            "milestone": ctx.milestone,
            "expected_answer": problem.solution_steps[0].expected_answer,
            "blueprint": "secret",
            "intended": 9,
        }
    )
    assert "expected_answer" not in sanitized
    assert "blueprint" not in sanitized
    assert "intended" not in sanitized


BROWSER_EXTRA_METHOD_QUESTION = (
    "Как точно да намерим излишъкът в първата кутия?"
)
BULGARIAN_EXTRA_METHOD_QUESTIONS = (
    BROWSER_EXTRA_METHOD_QUESTION,
    "Как да намеря излишъка?",
    "Как да изчисля излишъка в първата кутия?",
    "Как се намира този излишък?",
    "Как да реша текущата стъпка?",
)
ENGLISH_EXTRA_METHOD_QUESTIONS = (
    "How do I find the extra amount?",
    "How do I calculate the extra in the first box?",
    "How do I solve this step?",
)
UNRELATED_EXTRA_QUESTIONS = (
    "How many items are in the first box?",
    "What number should I find?",
    "What is the extra?",
    "Какъв е излишъкът?",
    "Колко предмета има в първата кутия?",
)


def _more_clue(problem):
    for clue in problem.known.get("public_clues") or ():
        if clue.get("kind") == "more_than":
            return clue
    return None


def _assert_extra_method_answer(answer, problem, language):
    times = _times_clue(problem)
    more = _more_clue(problem)
    assert times is not None
    assert more is not None
    factor = times["factor"]
    extra = more["extra"]
    product = factor * extra
    left_name = _box_name(times["left"], language)
    right_name = _box_name(times["right"], language)
    extra_left_name = _box_name(more["left"], language)
    extra_right_name = _box_name(more["right"], language)
    extra_left_name_cap = extra_left_name[:1].upper() + extra_left_name[1:]
    word = _factor_word(factor, language)
    left_name_cap = left_name[:1].upper() + left_name[1:]
    lowered = answer.lower()
    fallback = question_fallback_message(language)
    assert answer != fallback
    assert "can't provide a reliable extended answer" not in lowered
    assert "надежден разширен отговор" not in lowered
    assert extra_left_name in answer, answer
    assert extra_right_name in answer, answer
    assert left_name in answer or left_name_cap in answer, answer
    assert right_name in answer, answer
    assert word in answer or str(factor) in answer
    assert str(factor) in answer
    assert str(extra) in answer
    assert "×" in answer
    assert "= ?" in answer
    more_index = answer.lower().find(extra_left_name.lower())
    right_index = answer.lower().find(extra_right_name.lower(), more_index)
    assert more_index != -1
    assert right_index != -1
    reversed_more = (
        f"{extra_right_name} has {extra} more"
        if language == "en"
        else f"{extra_right_name} има {extra} предмета повече"
    )
    assert reversed_more not in answer
    if language == "en":
        assert f"{extra_left_name_cap} has {extra} more items than {extra_right_name}" in answer
        assert "multiplied" in lowered
        assert f"Write {factor} × {extra} = ?" in answer
    else:
        assert f"има {extra} предмета повече" in answer
        assert extra_left_name in answer.split("отколкото")[0]
        assert extra_right_name in answer.split("отколкото")[1]
        assert "умножава" in lowered
        assert f"Запишете {factor} × {extra} = ?" in answer
    tokens = set(integer_tokens(answer))
    assert product not in tokens
    current = problem.solution_steps[0]
    assert current.metadata["milestone"] == "extra_from_scaled"
    assert current.expected_answer == product
    _assert_no_hidden_answers(answer, problem, current.step_number)
    for step in problem.solution_steps:
        value = step.expected_answer
        if isinstance(value, int) and value not in {factor, extra}:
            assert value not in tokens, (value, answer)


def assert_distribution_extra_method_guidance():
    failing = _failing_model()
    engine = GeneralTutorQuestionEngine(model_provider=failing)
    null_engine = GeneralTutorQuestionEngine(
        model_provider=NullTutorModelProvider(),
    )
    for question in BULGARIAN_EXTRA_METHOD_QUESTIONS:
        assert match_logical_method_intent(question), question
        assert not match_logical_terminology_intent(question)
        assert not match_logical_answer_format_intent(question)
    for question in ENGLISH_EXTRA_METHOD_QUESTIONS:
        assert match_logical_method_intent(question), question
        assert not match_logical_terminology_intent(question)
    for question in UNRELATED_EXTRA_QUESTIONS:
        assert not match_logical_method_intent(question), question
        assert not match_logical_terminology_intent(question)

    _, reproduced = _compile_family(
        "distribution_puzzles",
        difficulty=3,
        seed=58,
        language="bg",
    )
    assert "37" in reproduced.problem_text
    times = _times_clue(reproduced)
    more = _more_clue(reproduced)
    assert times["factor"] == 2
    assert more["extra"] == 3
    context = _context(reproduced)
    browser = engine.answer(
        TutorQuestionRequest(question=BROWSER_EXTRA_METHOD_QUESTION),
        context,
    )
    assert browser.answer_source == "local"
    assert browser.route == QuestionRoute.LOCAL_ONLY
    assert failing.calls == []
    _assert_extra_method_answer(browser.answer, reproduced, "bg")
    unavailable = null_engine.answer(
        TutorQuestionRequest(question=BROWSER_EXTRA_METHOD_QUESTION),
        context,
    )
    assert unavailable.answer_source == "local"
    assert unavailable.answer == browser.answer

    seen_factors = set()
    seen_extras = set()
    for seed in (1, 5, 8, 12, 52, 58):
        _, english = _compile_family(
            "distribution_puzzles",
            difficulty=3,
            seed=seed,
            language="en",
        )
        extra_step = english.solution_steps[0]
        assert extra_step.metadata["milestone"] == "extra_from_scaled"
        en_context = _context(english)
        tutor = PrimarySchoolTutorEngine(english)
        before_step = tutor.session.get_current_step().step_number
        before_hints = tutor.session.get_hints_for_current_step()
        times = _times_clue(english)
        more = _more_clue(english)
        seen_factors.add(times["factor"])
        seen_extras.add(more["extra"])
        for question in ENGLISH_EXTRA_METHOD_QUESTIONS:
            result = engine.answer(
                TutorQuestionRequest(question=question),
                en_context,
            )
            assert result.answer_source == "local", question
            assert result.route == QuestionRoute.LOCAL_ONLY
            _assert_extra_method_answer(result.answer, english, "en")
        _, bulgarian = _compile_family(
            "distribution_puzzles",
            difficulty=3,
            seed=seed,
            language="bg",
        )
        bg_context = _context(bulgarian)
        for question in BULGARIAN_EXTRA_METHOD_QUESTIONS:
            result = engine.answer(
                TutorQuestionRequest(question=question),
                bg_context,
            )
            assert result.answer_source == "local", question
            _assert_extra_method_answer(result.answer, bulgarian, "bg")
            assert "the " not in result.answer
        assert tutor.session.get_current_step().step_number == before_step
        assert tutor.session.get_hints_for_current_step() == before_hints
        wrong = tutor.submit(StudentSubmission("0"))
        assert wrong.status == "incorrect"
        assert tutor.session.get_current_step().step_number == before_step
        assert tutor.session.get_hints_for_current_step() == before_hints
        general = GeneralTutorQuestionEngine(
            model_provider=FakeTutorModelProvider(text="MODEL_GENERAL"),
        ).answer(
            TutorQuestionRequest(question="Where is logic used in real life?"),
            en_context,
        )
        assert general.answer_source == "model"
        for question in UNRELATED_EXTRA_QUESTIONS[:3]:
            asked = GeneralTutorQuestionEngine(
                model_provider=FakeTutorModelProvider(text="MODEL_UNRELATED"),
            ).answer(
                TutorQuestionRequest(question=question),
                en_context,
            )
            assert asked.answer_source == "model", question
    assert len(seen_factors) > 1
    assert len(seen_extras) > 1
    assert failing.calls == []

    format_result = engine.answer(
        TutorQuestionRequest(question=BROWSER_FORMAT_QUESTION),
        _context(reproduced),
    )
    assert format_result.answer_source == "local"
    term_result = engine.answer(
        TutorQuestionRequest(question=BROWSER_TERMINOLOGY_QUESTION),
        _context(
            _compile_family(
                "distribution_puzzles",
                difficulty=3,
                seed=58,
                language="en",
            )[1]
        ),
    )
    assert term_result.answer_source == "local"
    assert failing.calls == []


def assert_bulgarian_distribution_wording():
    reproduced_seed = 5
    factor2_seed = 58
    puzzle = generate_distribution_puzzle(
        difficulty=3,
        seed=reproduced_seed,
    )
    english = compile_logical_reasoning_puzzle(puzzle, "en")
    bulgarian = compile_logical_reasoning_puzzle(puzzle, "bg")
    assert english.problem_text == (
        "Three boxes contain 26 items in all. The first "
        "box contains 3 times as many items as the second "
        "box. The second box contains 4 more items than "
        "the third box. Find how many items are in each box."
    )
    assert english.solution_steps[0].prompt == (
        "How much extra does the first box contain because "
        "it has three times as many items as the second box?"
    )
    assert bulgarian.problem_text == (
        "В три кутии има общо 26 предмета. В първата кутия "
        "има 3 пъти повече предмети, отколкото във втората "
        "кутия. Във втората кутия има с 4 предмета повече, "
        "отколкото в третата кутия. Намерете колко предмета "
        "има във всяка кутия."
    )
    assert "пъти толкова" not in bulgarian.problem_text
    assert "отколкото в втората" not in bulgarian.problem_text
    extra_bg = bulgarian.solution_steps[0]
    extra_en = english.solution_steps[0]
    assert extra_bg.metadata["milestone"] == "extra_from_scaled"
    assert extra_bg.prompt == (
        "Във втората кутия има 4 допълнителни предмета. "
        "Колко допълнителни предмета се получават в "
        "първата кутия, когато умножим този брой по 3?"
    )
    assert extra_bg.expected_answer == extra_en.expected_answer == 12
    assert extra_en.expected_answer == 3 * 4
    assert [step.expected_answer for step in english.solution_steps] == [
        step.expected_answer for step in bulgarian.solution_steps
    ]
    assert len(english.solution_steps) == len(bulgarian.solution_steps) == 7
    assert [
        (step.metadata or {}).get("milestone")
        for step in english.solution_steps
    ] == [
        (step.metadata or {}).get("milestone")
        for step in bulgarian.solution_steps
    ]
    assert "Колко предмета има в първата кутия?" not in extra_bg.prompt
    _assert_no_hidden_answers(extra_bg.prompt, bulgarian, 1)
    _assert_no_hidden_answers(bulgarian.problem_text, bulgarian, 1)
    assert 12 not in integer_tokens(extra_bg.prompt)
    assert 12 not in integer_tokens(bulgarian.problem_text)

    other = compile_logical_reasoning_puzzle(
        generate_distribution_puzzle(difficulty=3, seed=factor2_seed),
        "bg",
    )
    other_en = compile_logical_reasoning_puzzle(
        generate_distribution_puzzle(difficulty=3, seed=factor2_seed),
        "en",
    )
    times = _times_clue(other)
    more = _more_clue(other)
    left_name = _box_name(times["left"], "bg")
    extra_left_name = _box_name(more["left"], "bg")
    extra_right_name = _box_name(more["right"], "bg")
    factor = times["factor"]
    extra = more["extra"]
    assert factor == 2
    assert extra == 3
    assert f"{factor} пъти повече предмети, отколкото" in other.problem_text
    prompt = other.solution_steps[0].prompt
    assert extra_left_name in prompt
    assert left_name in prompt
    assert str(extra) in prompt
    assert str(factor) in prompt
    assert "допълнителни предмета" in prompt
    assert extra_right_name not in prompt or extra_right_name in other.problem_text
    product = factor * extra
    assert product not in integer_tokens(prompt)
    assert other.solution_steps[0].expected_answer == product
    assert [
        step.expected_answer for step in other.solution_steps
    ] == [step.expected_answer for step in other_en.solution_steps]
    assert other_en.problem_text.startswith("Three boxes contain")
    assert "times as many" in other_en.problem_text

    live = _live(1)
    dist_items = list_suggested_questions(
        topic="logical_reasoning",
        problem=bulgarian,
        live_response=live,
        language="bg",
        completed=False,
    )
    dist_labels = {item.question_id: item.label for item in dist_items}
    assert dist_labels["logic.first_clue"] == "Кое условие да използвам първо?"
    assert "улика" not in dist_labels["logic.first_clue"]
    en_items = list_suggested_questions(
        topic="logical_reasoning",
        problem=english,
        live_response=live,
        language="en",
        completed=False,
    )
    en_labels = {item.question_id: item.label for item in en_items}
    assert en_labels["logic.first_clue"] == "Which clue should I use first?"
    first_label, first_answer = resolve_guided_question(
        "logic.first_clue",
        allowed_ids=set(dist_labels),
        topic="logical_reasoning",
        problem=bulgarian,
        live_response=live,
        context=_context(bulgarian),
        language="bg",
    )
    assert first_label == "Кое условие да използвам първо?"
    assert "улика" not in first_answer
    assert "пъти повече предмети, отколкото" in first_answer
    _assert_no_hidden_answers(first_answer, bulgarian, 1)

    _, number = _compile_family("number_detective", language="bg")
    number_items = list_suggested_questions(
        topic="logical_reasoning",
        problem=number,
        live_response=live,
        language="bg",
        completed=False,
    )
    number_labels = {item.question_id: item.label for item in number_items}
    assert number_labels["logic.first_clue"] == "Коя улика да използвам първо?"

    _, logic = _compile_family("logic_detective", language="bg")
    logic_items = list_suggested_questions(
        topic="logical_reasoning",
        problem=logic,
        live_response=live,
        language="bg",
        completed=False,
    )
    logic_labels = {item.question_id: item.label for item in logic_items}
    assert "logic.first_clue" not in logic_labels
    joined = " ".join(logic_labels.values())
    assert "улика" in joined or "невъзможн" in joined
    _, logic_answer = resolve_guided_question(
        "logic.eliminate",
        allowed_ids=set(logic_labels),
        topic="logical_reasoning",
        problem=logic,
        live_response=live,
        context=_context(logic),
        language="bg",
    )
    assert "улика" in logic_answer


def main():
    for family in (
        "number_detective",
        "distribution_puzzles",
        "logic_detective",
    ):
        assert_progressive_hints(family)
    assert_distribution_hints_all_steps()
    assert_guided_questions()
    assert_free_form_safety()
    assert_answer_format_questions()
    assert_distribution_step_wording()
    assert_bulgarian_v_preposition_before_second_box()
    assert_distribution_terminology()
    assert_distribution_guided_questions_are_contextual()
    assert_guidance_context_does_not_leak()
    assert_distribution_extra_method_guidance()
    assert_bulgarian_distribution_wording()
    print("logical_reasoning_guidance tests passed")


if __name__ == "__main__":
    main()
