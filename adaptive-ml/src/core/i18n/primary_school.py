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
        "not_integer": "Please enter a whole number.",
        "gen.arithmetic.title": "Compute the expression",
        "gen.arithmetic.statement": "Compute: {expression}",
        "gen.arithmetic.prompt.value": (
            "What is the value of {expression}?"
        ),
        "gen.arithmetic.prompt.inner_product": (
            "In {expression}, what is the product you "
            "should compute first?"
        ),
        "gen.arithmetic.prompt.inner_paren": (
            "In {expression}, what is the value inside "
            "the parentheses?"
        ),
        "gen.arithmetic.hint.compute": (
            "Work from left to right with the two numbers."
        ),
        "gen.arithmetic.hint.multiply_first": (
            "Do multiplication before addition."
        ),
        "gen.arithmetic.hint.add_product": (
            "Add the remaining number to the product "
            "you already found."
        ),
        "gen.arithmetic.hint.parentheses": (
            "First compute the expression inside the "
            "parentheses."
        ),
        "gen.arithmetic.hint.multiply_inner": (
            "Multiply the value from the parentheses "
            "by the remaining number."
        ),
        "gen.unknown.title": "Find the unknown number",
        "gen.unknown.statement": (
            "Find the integer x that makes this true: "
            "{equation}"
        ),
        "gen.unknown.prompt.known_addend": (
            "In {equation}, what is the known addend?"
        ),
        "gen.unknown.prompt.known_subtrahend": (
            "In {equation}, what is the known subtrahend?"
        ),
        "gen.unknown.prompt.known_factor": (
            "In {equation}, what is the known factor?"
        ),
        "gen.unknown.prompt.solve": "What is x in {equation}?",
        "gen.unknown.hint.known_addend": (
            "The known addend is the number added to x."
        ),
        "gen.unknown.hint.known_subtrahend": (
            "The known subtrahend is the number subtracted "
            "from x."
        ),
        "gen.unknown.hint.known_factor": (
            "The known factor is the number that "
            "multiplies x."
        ),
        "gen.unknown.hint.inverse_add": (
            "Subtraction is the inverse of addition. "
            "Subtract the known addend from both sides."
        ),
        "gen.unknown.hint.inverse_sub": (
            "Addition is the inverse of subtraction. "
            "Add the known subtrahend to both sides."
        ),
        "gen.unknown.hint.inverse_mul": (
            "Division is the inverse of multiplication. "
            "Divide both sides by the known factor."
        ),
        "gen.unknown.method.add": (
            "x is the unknown addend in {equation}.\n"
            "Subtraction is the inverse of addition.\n"
            "Subtract {a} from both sides:\n"
            "    {left_undo} = {right_undo}\n"
            "    x = {b} - {a}"
        ),
        "gen.unknown.method.sub": (
            "x is the unknown minuend in {equation}.\n"
            "Addition is the inverse of subtraction.\n"
            "Add {a} to both sides:\n"
            "    {left_undo} = {right_undo}\n"
            "    x = {b} + {a}"
        ),
        "gen.unknown.method.mul": (
            "x is the unknown factor in {equation}.\n"
            "Division is the inverse of multiplication.\n"
            "Divide both sides by the known factor {a}:\n"
            "    {left_undo} = {right_undo}\n"
            "    x = {b} ÷ {a}"
        ),
        "gen.unknown.complete.add": (
            "{method}\n"
            "So x = {x}.\n"
            "Check: {x} + {a} = {b}."
        ),
        "gen.unknown.complete.sub": (
            "{method}\n"
            "So x = {x}.\n"
            "Check: {x} - {a} = {b}."
        ),
        "gen.unknown.complete.mul": (
            "{method}\n"
            "So x = {x}.\n"
            "Check: {a} × {x} = {b}."
        ),
        "gen.unknown.vocab.factor.define": (
            "In multiplication, the numbers we multiply "
            "are called factors. The result is called "
            "the product.\n"
            "For example, in {ex_left} × {ex_right} = "
            "{ex_result}, {ex_left} and {ex_right} are "
            "factors, and {ex_result} is the product."
        ),
        "gen.unknown.vocab.factor.here": (
            "In {equation}, {a} is the known factor, "
            "x is the unknown factor, and {b} is the "
            "product.\n"
            "Think which number you should multiply by "
            "{a} to get {b}."
        ),
        "gen.unknown.vocab.factor.other": (
            "The current equation, {equation}, is not "
            "a multiplication, so it does not use "
            "factors in that way."
        ),
        "gen.unknown.vocab.product.define": (
            "The product is the result of multiplication.\n"
            "For example, in {ex_left} × {ex_right} = "
            "{ex_result}, the product is {ex_result}."
        ),
        "gen.unknown.vocab.product.here": (
            "In {equation}, {b} is the product of the "
            "factors {a} and x.\n"
            "Think which number you should multiply by "
            "{a} to get {b}."
        ),
        "gen.unknown.vocab.product.other": (
            "The current equation, {equation}, is not "
            "a multiplication, so it does not have a "
            "product in that way."
        ),
        "gen.unknown.vocab.addend.define": (
            "In addition, the numbers we add are called "
            "addends. The result is called the sum.\n"
            "For example, in {ex_left} + {ex_right} = "
            "{ex_result}, {ex_left} and {ex_right} are "
            "addends, and {ex_result} is the sum."
        ),
        "gen.unknown.vocab.addend.here": (
            "In {equation}, {a} is the known addend, "
            "x is the unknown addend, and {b} is the "
            "sum.\n"
            "Think which number you should add to {a} "
            "to get {b}."
        ),
        "gen.unknown.vocab.addend.other": (
            "The current equation, {equation}, is not "
            "an addition, so its known number is not "
            "an addend."
        ),
        "gen.unknown.vocab.subtrahend.define": (
            "In subtraction, the number we subtract is "
            "called the subtrahend. The number we "
            "subtract from is the minuend. The result "
            "is the difference.\n"
            "For example, in {ex_left} - {ex_right} = "
            "{ex_result}, {ex_left} is the minuend, "
            "{ex_right} is the subtrahend, and "
            "{ex_result} is the difference."
        ),
        "gen.unknown.vocab.subtrahend.here": (
            "In {equation}, x is the minuend, {a} is "
            "the known subtrahend, and {b} is the "
            "difference.\n"
            "Think which number you subtract {a} from "
            "to get {b}."
        ),
        "gen.unknown.vocab.subtrahend.other": (
            "The current equation, {equation}, is not "
            "a subtraction, so it does not have a "
            "subtrahend in that way."
        ),
        "gen.unknown.vocab.minuend.define": (
            "In subtraction, the number we subtract "
            "from is called the minuend.\n"
            "For example, in {ex_left} - {ex_right} = "
            "{ex_result}, {ex_left} is the minuend."
        ),
        "gen.unknown.vocab.minuend.here": (
            "In {equation}, x is the unknown minuend, "
            "{a} is the known subtrahend, and {b} is "
            "the difference.\n"
            "Think which number you subtract {a} from "
            "to get {b}."
        ),
        "gen.unknown.vocab.minuend.other": (
            "The current equation, {equation}, is not "
            "a subtraction, so it does not have a "
            "minuend in that way."
        ),
        "gen.patterns.title": "Number patterns",
        "gen.sequence.statement": (
            "Here is a number sequence: {sequence}, …"
        ),
        "gen.sequence.prompt.difference": (
            "What is the common difference in {sequence}?"
        ),
        "gen.sequence.prompt.next": (
            "What number comes next after {sequence}?"
        ),
        "gen.sequence.hint.difference": (
            "Subtract one term from the next term."
        ),
        "gen.sequence.hint.next": (
            "Add the common difference to the last "
            "given term."
        ),
        "gen.chain.statement.forward": (
            "Follow this operation chain. The last "
            "value is missing: {chain}"
        ),
        "gen.chain.statement.reverse": (
            "This operation chain is missing its "
            "starting number: {chain}"
        ),
        "gen.chain.prompt.after_step": (
            "After step {step_number} of {chain}, "
            "what value do you have?"
        ),
        "gen.chain.prompt.result": (
            "What is the final value of {chain}?"
        ),
        "gen.chain.prompt.undo": (
            "Undo the last remaining operation in {chain}. "
            "What value do you get?"
        ),
        "gen.chain.prompt.start": (
            "What starting number makes {chain} true?"
        ),
        "gen.chain.hint.next_forward": (
            "Apply the next written operation to the "
            "current value."
        ),
        "gen.chain.hint.last_forward": (
            "Apply the last written operation to finish "
            "the chain."
        ),
        "gen.chain.hint.undo_add": (
            "Undo addition by subtracting {amount}."
        ),
        "gen.chain.hint.undo_sub": (
            "Undo subtraction by adding {amount}."
        ),
        "gen.chain.hint.undo_mul": (
            "Undo multiplication by dividing by {amount}."
        ),
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
        "not_integer": "Моля, въведете цяло число.",
        "gen.arithmetic.title": "Пресметнете израза",
        "gen.arithmetic.statement": "Пресметнете: {expression}",
        "gen.arithmetic.prompt.value": (
            "Колко е стойността на {expression}?"
        ),
        "gen.arithmetic.prompt.inner_product": (
            "В {expression} кое произведение трябва да "
            "пресметнете първо?"
        ),
        "gen.arithmetic.prompt.inner_paren": (
            "В {expression} колко е стойността в скобите?"
        ),
        "gen.arithmetic.hint.compute": (
            "Работете с двете числа отляво надясно."
        ),
        "gen.arithmetic.hint.multiply_first": (
            "Първо умножението, после събирането."
        ),
        "gen.arithmetic.hint.add_product": (
            "Прибавете останалото число към вече "
            "намереното произведение."
        ),
        "gen.arithmetic.hint.parentheses": (
            "Първо пресметнете израза в скобите."
        ),
        "gen.arithmetic.hint.multiply_inner": (
            "Умножете стойността от скобите по "
            "останалото число."
        ),
        "gen.unknown.title": "Намерете неизвестното число",
        "gen.unknown.statement": (
            "Намерете цялото число x, за което е вярно: "
            "{equation}"
        ),
        "gen.unknown.prompt.known_addend": (
            "В {equation} кое е известното събираемо?"
        ),
        "gen.unknown.prompt.known_subtrahend": (
            "В {equation} кой е известният умалител?"
        ),
        "gen.unknown.prompt.known_factor": (
            "В {equation} кой е известният множител?"
        ),
        "gen.unknown.prompt.solve": "Колко е x в {equation}?",
        "gen.unknown.hint.known_addend": (
            "Известното събираемо е числото, което се "
            "прибавя към x."
        ),
        "gen.unknown.hint.known_subtrahend": (
            "Известният умалител е числото, което се "
            "изважда от x."
        ),
        "gen.unknown.hint.known_factor": (
            "Известният множител е числото, по което се "
            "умножава x."
        ),
        "gen.unknown.hint.inverse_add": (
            "Изваждането е обратното действие на "
            "събирането. Извадете известното събираемо "
            "от двете страни."
        ),
        "gen.unknown.hint.inverse_sub": (
            "Събирането е обратното действие на "
            "изваждането. Прибавете известния умалител "
            "към двете страни."
        ),
        "gen.unknown.hint.inverse_mul": (
            "Делението е обратното действие на "
            "умножението. Разделете двете страни на "
            "известния множител."
        ),
        "gen.unknown.method.add": (
            "x е неизвестното събираемо в {equation}.\n"
            "Изваждането е обратното действие на "
            "събирането.\n"
            "Извадете {a} от двете страни:\n"
            "    {left_undo} = {right_undo}\n"
            "    x = {b} - {a}"
        ),
        "gen.unknown.method.sub": (
            "x е неизвестното умаляемо в {equation}.\n"
            "Събирането е обратното действие на "
            "изваждането.\n"
            "Прибавете {a} към двете страни:\n"
            "    {left_undo} = {right_undo}\n"
            "    x = {b} + {a}"
        ),
        "gen.unknown.method.mul": (
            "x е неизвестният множител в {equation}.\n"
            "Делението е обратното действие на "
            "умножението.\n"
            "Разделете двете страни на известния "
            "множител {a}:\n"
            "    {left_undo} = {right_undo}\n"
            "    x = {b} ÷ {a}"
        ),
        "gen.unknown.complete.add": (
            "{method}\n"
            "Следователно x = {x}.\n"
            "Проверка: {x} + {a} = {b}."
        ),
        "gen.unknown.complete.sub": (
            "{method}\n"
            "Следователно x = {x}.\n"
            "Проверка: {x} - {a} = {b}."
        ),
        "gen.unknown.complete.mul": (
            "{method}\n"
            "Следователно x = {x}.\n"
            "Проверка: {a} × {x} = {b}."
        ),
        "gen.unknown.vocab.factor.define": (
            "При умножение числата, които умножаваме, "
            "се наричат множители. Резултатът се "
            "нарича произведение.\n"
            "Например в {ex_left} × {ex_right} = "
            "{ex_result} числата {ex_left} и "
            "{ex_right} са множители, а {ex_result} "
            "е произведението."
        ),
        "gen.unknown.vocab.factor.here": (
            "В {equation} числото {a} е известният "
            "множител, x е неизвестният множител, "
            "а {b} е произведението.\n"
            "Помисли кое число трябва да умножим по "
            "{a}, за да получим {b}."
        ),
        "gen.unknown.vocab.factor.other": (
            "Текущото уравнение {equation} не е "
            "умножение, затова в него няма множители "
            "по този начин."
        ),
        "gen.unknown.vocab.product.define": (
            "Произведението е резултатът от "
            "умножението.\n"
            "Например в {ex_left} × {ex_right} = "
            "{ex_result} произведението е {ex_result}."
        ),
        "gen.unknown.vocab.product.here": (
            "В {equation} числото {b} е произведението "
            "на множителите {a} и x.\n"
            "Помисли кое число трябва да умножим по "
            "{a}, за да получим {b}."
        ),
        "gen.unknown.vocab.product.other": (
            "Текущото уравнение {equation} не е "
            "умножение, затова в него няма произведение "
            "по този начин."
        ),
        "gen.unknown.vocab.addend.define": (
            "При събиране числата, които събираме, се "
            "наричат събираеми. Резултатът се нарича "
            "сбор.\n"
            "Например в {ex_left} + {ex_right} = "
            "{ex_result} числата {ex_left} и "
            "{ex_right} са събираеми, а {ex_result} "
            "е сборът."
        ),
        "gen.unknown.vocab.addend.here": (
            "В {equation} числото {a} е известното "
            "събираемо, x е неизвестното събираемо, "
            "а {b} е сборът.\n"
            "Помисли кое число трябва да прибавим към "
            "{a}, за да получим {b}."
        ),
        "gen.unknown.vocab.addend.other": (
            "Текущото уравнение {equation} не е "
            "събиране, затова известното число в него "
            "не е събираемо."
        ),
        "gen.unknown.vocab.subtrahend.define": (
            "При изваждане числото, което изваждаме, "
            "се нарича умалител. Числото, от което "
            "изваждаме, се нарича умаляемо. Резултатът "
            "се нарича разлика.\n"
            "Например в {ex_left} - {ex_right} = "
            "{ex_result} числото {ex_left} е "
            "умаляемото, {ex_right} е умалителят, а "
            "{ex_result} е разликата."
        ),
        "gen.unknown.vocab.subtrahend.here": (
            "В {equation} неизвестното x е "
            "умаляемото, {a} е известният умалител, "
            "а {b} е разликата.\n"
            "Помисли от кое число трябва да извадим "
            "{a}, за да получим {b}."
        ),
        "gen.unknown.vocab.subtrahend.other": (
            "Текущото уравнение {equation} не е "
            "изваждане, затова в него няма умалител "
            "по този начин."
        ),
        "gen.unknown.vocab.minuend.define": (
            "При изваждане числото, от което "
            "изваждаме, се нарича умаляемо.\n"
            "Например в {ex_left} - {ex_right} = "
            "{ex_result} числото {ex_left} е "
            "умаляемото."
        ),
        "gen.unknown.vocab.minuend.here": (
            "В {equation} x е неизвестното умаляемо, "
            "{a} е известният умалител, а {b} е "
            "разликата.\n"
            "Помисли от кое число трябва да извадим "
            "{a}, за да получим {b}."
        ),
        "gen.unknown.vocab.minuend.other": (
            "Текущото уравнение {equation} не е "
            "изваждане, затова в него няма умаляемо "
            "по този начин."
        ),
        "gen.patterns.title": "Числови редици",
        "gen.sequence.statement": (
            "Дадена е числова редица: {sequence}, …"
        ),
        "gen.sequence.prompt.difference": (
            "Каква е общата разлика в {sequence}?"
        ),
        "gen.sequence.prompt.next": (
            "Кое число следва след {sequence}?"
        ),
        "gen.sequence.hint.difference": (
            "Извадете един член от следващия."
        ),
        "gen.sequence.hint.next": (
            "Прибавете общата разлика към последния "
            "даден член."
        ),
        "gen.chain.statement.forward": (
            "Следвайте тази верига от действия. Липсва "
            "последната стойност: {chain}"
        ),
        "gen.chain.statement.reverse": (
            "В тази верига от действия липсва началното "
            "число: {chain}"
        ),
        "gen.chain.prompt.after_step": (
            "След стъпка {step_number} от {chain} "
            "каква стойност имате?"
        ),
        "gen.chain.prompt.result": (
            "Колко е крайната стойност на {chain}?"
        ),
        "gen.chain.prompt.undo": (
            "Отменете последното останало действие в "
            "{chain}. Каква стойност получавате?"
        ),
        "gen.chain.prompt.start": (
            "Кое начално число прави {chain} вярна?"
        ),
        "gen.chain.hint.next_forward": (
            "Приложете следващото записано действие към "
            "текущата стойност."
        ),
        "gen.chain.hint.last_forward": (
            "Приложете последното записано действие, "
            "за да завършите веригата."
        ),
        "gen.chain.hint.undo_add": (
            "Отменете събирането, като извадите {amount}."
        ),
        "gen.chain.hint.undo_sub": (
            "Отменете изваждането, като прибавите {amount}."
        ),
        "gen.chain.hint.undo_mul": (
            "Отменете умножението, като разделите на {amount}."
        ),
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
                input_type=step.input_type,
                answer_format=step.answer_format,
                metadata=dict(step.metadata or {}),
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
        metadata=dict(problem.metadata or {}),
    )
