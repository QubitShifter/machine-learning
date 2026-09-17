from src.core.i18n.locale import normalize_locale
from src.core.i18n.text import tr


_FALLBACK = {
    "en": (
        "I can't provide a reliable extended answer to that "
        "question right now. Try asking it more specifically "
        "or continue with the current step."
    ),
    "bg": (
        "Не мога да дам надежден разширен отговор на този "
        "въпрос в момента. Опитайте да го формулирате "
        "по-конкретно или продължете с текущата стъпка."
    ),
}

_WEB_UNAVAILABLE = {
    "en": (
        "I couldn't retrieve a reliable external source, "
        "but I can explain it from the current problem context."
    ),
    "bg": (
        "Не успях да намеря достатъчно надежден външен източник, "
        "но мога да обясня това въз основа на текущата задача."
    ),
}

_CONTINUE = {
    "en": (
        "When you're ready, continue with the mathematical step."
    ),
    "bg": (
        "Когато сте готови, продължете с математическата стъпка."
    ),
}


def question_fallback_message(language: str | None) -> str:
    return _FALLBACK[normalize_locale(language)]


def question_web_unavailable_message(language: str | None) -> str:
    return _WEB_UNAVAILABLE[normalize_locale(language)]


QUESTION_TEXT = {
    "en": {
        "question.alternative.intro": (
            "Yes. This equation can also be solved by "
            "separation of variables."
        ),
        "question.alternative.rearrange": (
            "Rearrange the equation:"
        ),
        "question.alternative.separate": (
            "Separate the variables:"
        ),
        "question.alternative.restriction_lead": (
            "When dividing we assume that"
        ),
        "question.alternative.equilibrium_lead": (
            "Separately we check that the constant function"
        ),
        "question.alternative.equilibrium_tail": (
            "is also a solution of the original equation."
        ),
        "question.alternative.next_step": (
            "We can then integrate both sides."
        ),
        "question.alternative.unverified.if_applies": (
            "The integrating-factor method applies to this "
            "linear equation."
        ),
        "question.alternative.unverified.no_verified": (
            "I do not currently have a verified alternative "
            "transformation for this particular problem."
        ),
        "question.alternative.unverified.separation": (
            "I have not established that separation of "
            "variables applies to this equation."
        ),
        "question.alternative.unverified.not_impossible": (
            "That does not mean another method is impossible."
        ),
        "question.alternative.unverified.continue": (
            "We can continue with the integrating-factor "
            "method or examine another approach more closely."
        ),
    },
    "bg": {
        "question.alternative.intro": (
            "Да. Това уравнение може да се реши и чрез "
            "разделяне на променливите."
        ),
        "question.alternative.rearrange": (
            "Пренареждаме уравнението:"
        ),
        "question.alternative.separate": (
            "Разделяме променливите:"
        ),
        "question.alternative.restriction_lead": (
            "При делението приемаме, че"
        ),
        "question.alternative.equilibrium_lead": (
            "Отделно проверяваме, че постоянната функция"
        ),
        "question.alternative.equilibrium_tail": (
            "също е решение на първоначалното уравнение."
        ),
        "question.alternative.next_step": (
            "След това можем да интегрираме двете страни."
        ),
        "question.alternative.unverified.if_applies": (
            "Методът с интегриращ фактор е приложим за това "
            "линейно уравнение."
        ),
        "question.alternative.unverified.no_verified": (
            "На този етап нямам проверено алтернативно "
            "преобразуване за конкретната задача."
        ),
        "question.alternative.unverified.separation": (
            "Не съм установил, че разделянето на "
            "променливите е приложимо за това уравнение."
        ),
        "question.alternative.unverified.not_impossible": (
            "Това не означава, че друг метод е невъзможен."
        ),
        "question.alternative.unverified.continue": (
            "Можем да продължим с метода с интегриращ фактор "
            "или да разгледаме допълнително приложимостта на "
            "друг подход."
        ),
    },
}


def question_continue_message(language: str | None) -> str:
    return _CONTINUE[normalize_locale(language)]


def qt(language: str | None, key: str, **params) -> str:
    return tr(QUESTION_TEXT, language, key, **params)
