from src.core.i18n.text import tr
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
    SolutionStep,
)


PRIMARY_SCHOOL_TEXT = {
    "en": {
        "complete": "Excellent. You solved the problem.",
        "continue": "Good. Let's continue.",
        "no_hint": "No additional hint is available.",
        "empty_answer": "Please enter an answer.",
        "not_numeric": "I could not understand that as a number.",
        "invalid_expected": (
            "The tutor could not validate this step."
        ),
        "correct": "Correct.",
        "incorrect": "That is not the correct answer yet.",
    },
    "bg": {
        "complete": "Отлично. Решихте задачата.",
        "continue": "Добре. Да продължим.",
        "no_hint": "Няма допълнителна подсказка.",
        "empty_answer": "Моля, въведете отговор.",
        "not_numeric": "Не разпознах това като число.",
        "invalid_expected": (
            "Учебният помощник не можа да провери "
            "тази стъпка."
        ),
        "correct": "Правилно.",
        "incorrect": "Това все още не е верният отговор.",
    },
}

PRIMARY_SCHOOL_PROBLEMS_BG = {
    "grade4_reverse_reasoning_001": {
        "title": "Лешници в три хралупи",
        "problem_text": (
            "Катерица събрала лешници и решила да ги "
            "скрие в три хралупи. В първата хралупа "
            "сложила половината лешници и още 2 лешника. "
            "Във втората хралупа сложила половината от "
            "останалите лешници и още 4 лешника. В "
            "третата хралупа сложила половината от "
            "останалите лешници и още 5 лешника. След "
            "това останали 7 лешника. Колко лешника е "
            "събрала катерицата в началото?"
        ),
        "steps": {
            1: {
                "prompt": (
                    "Колко лешника са останали, след като "
                    "катерицата напълнила трите хралупи?"
                ),
                "hint": (
                    "Погледнете последното изречение на "
                    "задачата."
                ),
            },
            2: {
                "prompt": (
                    "Преди катерицата да добави още 5 "
                    "лешника в третата хралупа, колко "
                    "лешника са представлявали половината "
                    "от предишното количество?"
                ),
                "hint": (
                    "Работете назад: отменете изваждането "
                    "на 5, като добавите 5."
                ),
            },
            3: {
                "prompt": (
                    "Ако 12 лешника са половината от "
                    "количеството преди третата хралупа, "
                    "колко е било цялото количество?"
                ),
                "hint": (
                    "Ако едната половина е 12, двете "
                    "половини дават цялото."
                ),
            },
            4: {
                "prompt": (
                    "Преди катерицата да добави още 4 "
                    "лешника във втората хралупа, колко "
                    "лешника са представлявали половината "
                    "от предишното количество?"
                ),
                "hint": (
                    "Отменете допълнителните 4, като "
                    "добавите 4 обратно."
                ),
            },
            5: {
                "prompt": (
                    "Ако 28 лешника са половината от "
                    "количеството преди втората хралупа, "
                    "колко е било цялото количество?"
                ),
                "hint": "Удвоете 28.",
            },
            6: {
                "prompt": (
                    "Преди катерицата да добави още 2 "
                    "лешника в първата хралупа, колко "
                    "лешника са представлявали половината "
                    "от първоначалното количество?"
                ),
                "hint": (
                    "Отменете допълнителните 2, като "
                    "добавите 2 обратно."
                ),
            },
            7: {
                "prompt": (
                    "Ако 58 лешника са половината от "
                    "първоначалното количество, колко "
                    "лешника е имало в началото?"
                ),
                "hint": (
                    "Удвоете 58, за да възстановите "
                    "първоначалното количество."
                ),
            },
        },
    },
}


def pst(language: str | None, key: str, **params) -> str:
    return tr(PRIMARY_SCHOOL_TEXT, language, key, **params)


def localize_primary_school_problem(
    problem: PrimarySchoolProblem,
    language: str | None,
) -> PrimarySchoolProblem:
    from src.core.i18n.locale import normalize_locale

    locale = normalize_locale(language)
    if locale != "bg":
        return problem

    overlay = PRIMARY_SCHOOL_PROBLEMS_BG.get(
        problem.problem_id,
    )
    if overlay is None:
        return problem

    steps = overlay.get("steps", {})
    localized_steps = []
    for step in problem.solution_steps:
        texts = steps.get(step.step_number, {})
        localized_steps.append(
            SolutionStep(
                step_number=step.step_number,
                skill_id=step.skill_id,
                prompt=texts.get("prompt", step.prompt),
                expected_answer=step.expected_answer,
                hint=texts.get("hint", step.hint),
                operation=step.operation,
                step_type=step.step_type,
            )
        )

    return PrimarySchoolProblem(
        problem_id=problem.problem_id,
        grade=problem.grade,
        topic=problem.topic,
        problem_type=problem.problem_type,
        title=overlay.get("title", problem.title),
        language=locale,
        problem_text=overlay.get(
            "problem_text",
            problem.problem_text,
        ),
        skills=problem.skills,
        known=problem.known,
        unknown=problem.unknown,
        strategy=problem.strategy,
        solution_steps=localized_steps,
        final_answer=problem.final_answer,
    )
