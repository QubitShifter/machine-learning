from src.core.i18n.text import tr


KINEMATICS_TEXT = {
    "en": {
        "title.fixed": "Car accelerating from rest",
        "title.generated": "Generated 1D kinematics",
        "statement.fixed": (
            "A car starts from rest and accelerates "
            "uniformly at $3\\ \\mathrm{m/s^2}$ for "
            "$4\\ \\mathrm{s}$.\n\n"
            "Find:\n"
            "1. the final velocity\n"
            "2. the distance traveled"
        ),
        "statement.from_rest": (
            "An object starts from rest and accelerates "
            "uniformly at ${a}\\ \\mathrm{m/s^2}$ for "
            "${t}\\ \\mathrm{s}$. Find the final velocity."
        ),
        "statement.constant_velocity": (
            "An object moves at constant velocity "
            "${v}\\ \\mathrm{m/s}$ for ${t}\\ "
            "\\mathrm{s}$. Find the displacement."
        ),
        "statement.v_and_dx": (
            "An object has initial velocity "
            "${v0}\\ \\mathrm{m/s}$ and {motion} at "
            "${a}\\ \\mathrm{m/s^2}$ for ${t}\\ "
            "\\mathrm{s}$. Find the final velocity and "
            "the displacement."
        ),
        "motion.slows": "slows uniformly",
        "motion.accelerates": "accelerates uniformly",
        "statement.solve_t": (
            "An object changes from "
            "${v0}\\ \\mathrm{m/s}$ to "
            "${v}\\ \\mathrm{m/s}$ with constant "
            "acceleration ${a}\\ \\mathrm{m/s^2}$. "
            "Find the elapsed time."
        ),
        "statement.solve_dx": (
            "An object changes from "
            "${v0}\\ \\mathrm{m/s}$ to "
            "${v}\\ \\mathrm{m/s}$ with constant "
            "acceleration ${a}\\ \\mathrm{m/s^2}$. "
            "Time is not given. Find the displacement."
        ),
        "step.identify_v0": "Identify the initial velocity $v_0$.",
        "hint.identify_v0_rest": (
            "Read the starting velocity. Rest means $v_0 = 0$."
        ),
        "hint.identify_v0": "Read $v_0$ from the problem statement.",
        "step.identify_a": "Identify the acceleration $a$.",
        "hint.identify_a": (
            "Acceleration is the given constant rate "
            "of change of velocity."
        ),
        "hint.identify_a_short": "Acceleration is given and constant.",
        "hint.identify_a_sign": (
            "Pay attention to the sign of acceleration."
        ),
        "step.identify_t": "Identify the elapsed time $t$.",
        "hint.identify_t": "Use the time interval stated in the problem.",
        "hint.identify_t_short": "Use the given time interval.",
        "step.formula_velocity_long": (
            "Choose the equation for final velocity "
            "when acceleration is constant."
        ),
        "hint.formula_velocity_long": (
            "Which equation connects initial velocity, "
            "acceleration, and time directly?"
        ),
        "step.formula_velocity": (
            "Choose the equation for final velocity."
        ),
        "hint.formula_velocity": (
            "Which equation connects $v_0$, $a$, and $t$?"
        ),
        "step.calculate_v": "Calculate the final velocity $v$.",
        "hint.calculate_v": (
            "Substitute the known $v_0$, $a$, and $t$ "
            "into $v = v_0 + at$."
        ),
        "hint.calculate_v_short": (
            "Substitute the known values into $v = v_0 + at$."
        ),
        "step.formula_displacement_long": (
            "Choose the equation for displacement "
            "when $v_0$, $a$, and $t$ are known."
        ),
        "hint.formula_displacement_long": (
            "Since acceleration is constant and time "
            "is known, use the equation containing "
            "$v_0$, $a$, and $t$."
        ),
        "step.calculate_dx": (
            "Calculate the displacement $\\Delta x$."
        ),
        "hint.calculate_dx": (
            "Substitute into "
            "$\\Delta x = v_0 t + \\frac{1}{2} a t^2$."
        ),
        "step.summary_v_dx": (
            "State the final velocity and the "
            "distance traveled, including SI units."
        ),
        "hint.summary_v_dx": (
            "Report both $v$ and $\\Delta x$ with units."
        ),
        "step.summary_v": (
            "State the final velocity with its SI unit."
        ),
        "hint.summary_v": "Include both the number and m/s.",
        "step.identify_v_const": (
            "Identify the constant velocity $v$."
        ),
        "hint.identify_v_const": (
            "Speed does not change in this problem."
        ),
        "step.formula_const_v": (
            "Choose the displacement equation for "
            "constant velocity."
        ),
        "hint.formula_const_v": (
            "With $a = 0$, displacement is velocity "
            "times time."
        ),
        "hint.calculate_dx_vt": "Use $\\Delta x = v t$.",
        "step.summary_dx": (
            "State the displacement with its SI unit."
        ),
        "hint.summary_dx": "Include both the number and m.",
        "step.identify_v": "Identify the final velocity $v$.",
        "hint.identify_v": (
            "Read the later velocity from the statement."
        ),
        "step.formula_time": (
            "Choose the equation that finds $t$ "
            "from $v$, $v_0$, and $a$."
        ),
        "hint.formula_time": (
            "Rearrange $v = v_0 + at$ to solve for time."
        ),
        "step.calculate_t": "Calculate the elapsed time $t$.",
        "hint.calculate_t": (
            "Use $t = (v - v_0)/a$. Time must be positive."
        ),
        "step.summary_t": (
            "State the elapsed time with its SI unit."
        ),
        "hint.summary_t": "Include both the number and s.",
        "step.formula_velocity_sq": (
            "Choose an equation for $\\Delta x$ that "
            "does not require time."
        ),
        "hint.formula_velocity_sq": (
            "Use $v^2 = v_0^2 + 2 a \\Delta x$ when "
            "$t$ is unknown."
        ),
        "hint.calculate_dx_no_t": (
            "Rearrange to "
            "$\\Delta x = (v^2 - v_0^2)/(2a)$."
        ),
        "continue": "Good. Let's continue.",
        "complete": (
            "Excellent. You solved the kinematics problem."
        ),
        "feedback.not_numeric": (
            "I could not read a numeric value. "
            "Include the number and its SI unit."
        ),
        "feedback.invalid_expected": (
            "The tutor could not validate this step."
        ),
        "feedback.missing_unit": (
            "Include the SI unit for {quantity}."
        ),
        "feedback.unknown_unit": (
            "I could not recognize that unit. Use {unit}."
        ),
        "feedback.wrong_dimension": (
            "The numeric value may be close, "
            "but the unit should represent {dimension}."
        ),
        "feedback.wrong_unit": "Use the SI unit {unit}.",
        "feedback.wrong_sign": (
            "Check the chosen positive direction "
            "and the sign of acceleration."
        ),
        "feedback.wrong_value": (
            "Check the substitution and arithmetic. "
            "Raw input was {raw}."
        ),
        "feedback.correct": "Correct.",
        "feedback.missing_equals": (
            "Write a complete equation using =."
        ),
        "feedback.wrong_formula": (
            "That equation does not relate the "
            "known quantities for this step."
        ),
        "feedback.summary_wrong": (
            "State each requested result with its SI unit."
        ),
        "feedback.summary_correct": (
            "Correct. Those are the final results."
        ),
        "quantity.v0": "initial velocity",
        "quantity.v": "velocity",
        "quantity.a": "acceleration",
        "quantity.t": "time",
        "quantity.dx": "displacement",
        "dimension.velocity": "velocity",
        "dimension.length": "length",
        "dimension.time": "time",
        "dimension.acceleration": "acceleration",
    },
    "bg": {
        "title.fixed": "Автомобил, ускоряващ от покой",
        "title.generated": (
            "Генерирана задача по едномерна кинематика"
        ),
        "statement.fixed": (
            "Автомобил тръгва от покой и се движи с "
            "постоянно ускорение $3\\ \\mathrm{m/s^2}$ "
            "в продължение на $4\\ \\mathrm{s}$.\n\n"
            "Намерете:\n"
            "1. крайната скорост\n"
            "2. изминатия път"
        ),
        "statement.from_rest": (
            "Тяло тръгва от покой и се движи с постоянно "
            "ускорение ${a}\\ \\mathrm{m/s^2}$ в "
            "продължение на ${t}\\ \\mathrm{s}$. "
            "Намерете крайната скорост."
        ),
        "statement.constant_velocity": (
            "Тяло се движи с постоянна скорост "
            "${v}\\ \\mathrm{m/s}$ в продължение на "
            "${t}\\ \\mathrm{s}$. Намерете преместването."
        ),
        "statement.v_and_dx": (
            "Тяло има начална скорост "
            "${v0}\\ \\mathrm{m/s}$ и {motion} с "
            "${a}\\ \\mathrm{m/s^2}$ в продължение на "
            "${t}\\ \\mathrm{s}$. Намерете крайната "
            "скорост и преместването."
        ),
        "motion.slows": "намалява равномерно скоростта си",
        "motion.accelerates": "ускорява равномерно",
        "statement.solve_t": (
            "Тяло променя скоростта си от "
            "${v0}\\ \\mathrm{m/s}$ до "
            "${v}\\ \\mathrm{m/s}$ с постоянно "
            "ускорение ${a}\\ \\mathrm{m/s^2}$. "
            "Намерете изминалото време."
        ),
        "statement.solve_dx": (
            "Тяло променя скоростта си от "
            "${v0}\\ \\mathrm{m/s}$ до "
            "${v}\\ \\mathrm{m/s}$ с постоянно "
            "ускорение ${a}\\ \\mathrm{m/s^2}$. "
            "Времето не е дадено. Намерете преместването."
        ),
        "step.identify_v0": (
            "Определете началната скорост $v_0$."
        ),
        "hint.identify_v0_rest": (
            "Прочетете началната скорост. Покой означава "
            "$v_0 = 0$."
        ),
        "hint.identify_v0": (
            "Прочетете $v_0$ от условието на задачата."
        ),
        "step.identify_a": "Определете ускорението $a$.",
        "hint.identify_a": (
            "Ускорението е дадената постоянна скорост "
            "на изменение на скоростта."
        ),
        "hint.identify_a_short": (
            "Ускорението е дадено и е постоянно."
        ),
        "hint.identify_a_sign": (
            "Обърнете внимание на знака на ускорението."
        ),
        "step.identify_t": "Определете изминалото време $t$.",
        "hint.identify_t": (
            "Използвайте времевия интервал от условието."
        ),
        "hint.identify_t_short": (
            "Използвайте дадения времеви интервал."
        ),
        "step.formula_velocity_long": (
            "Изберете уравнението за крайната скорост "
            "при постоянно ускорение."
        ),
        "hint.formula_velocity_long": (
            "Кое уравнение свързва директно началната "
            "скорост, ускорението и времето?"
        ),
        "step.formula_velocity": (
            "Изберете уравнението за крайната скорост."
        ),
        "hint.formula_velocity": (
            "Кое уравнение свързва $v_0$, $a$ и $t$?"
        ),
        "step.calculate_v": (
            "Пресметнете крайната скорост $v$."
        ),
        "hint.calculate_v": (
            "Заместете известните $v_0$, $a$ и $t$ в "
            "$v = v_0 + at$."
        ),
        "hint.calculate_v_short": (
            "Заместете известните стойности в "
            "$v = v_0 + at$."
        ),
        "step.formula_displacement_long": (
            "Изберете уравнението за преместване, "
            "когато $v_0$, $a$ и $t$ са известни."
        ),
        "hint.formula_displacement_long": (
            "Тъй като ускорението е постоянно и времето "
            "е известно, използвайте уравнението с "
            "$v_0$, $a$ и $t$."
        ),
        "step.calculate_dx": (
            "Пресметнете преместването $\\Delta x$."
        ),
        "hint.calculate_dx": (
            "Заместете в "
            "$\\Delta x = v_0 t + \\frac{1}{2} a t^2$."
        ),
        "step.summary_v_dx": (
            "Запишете крайната скорост и изминатия път "
            "заедно със SI единиците."
        ),
        "hint.summary_v_dx": (
            "Посочете $v$ и $\\Delta x$ с единици."
        ),
        "step.summary_v": (
            "Запишете крайната скорост със SI единицата."
        ),
        "hint.summary_v": "Включете числото и m/s.",
        "step.identify_v_const": (
            "Определете постоянната скорост $v$."
        ),
        "hint.identify_v_const": (
            "В тази задача скоростта не се променя."
        ),
        "step.formula_const_v": (
            "Изберете уравнението за преместване при "
            "постоянна скорост."
        ),
        "hint.formula_const_v": (
            "При $a = 0$ преместването е скорост по време."
        ),
        "hint.calculate_dx_vt": "Използвайте $\\Delta x = v t$.",
        "step.summary_dx": (
            "Запишете преместването със SI единицата."
        ),
        "hint.summary_dx": "Включете числото и m.",
        "step.identify_v": "Определете крайната скорост $v$.",
        "hint.identify_v": (
            "Прочетете по-късната скорост от условието."
        ),
        "step.formula_time": (
            "Изберете уравнението, което намира $t$ "
            "от $v$, $v_0$ и $a$."
        ),
        "hint.formula_time": (
            "Превъртете $v = v_0 + at$, за да намерите "
            "времето."
        ),
        "step.calculate_t": "Пресметнете изминалото време $t$.",
        "hint.calculate_t": (
            "Използвайте $t = (v - v_0)/a$. Времето "
            "трябва да е положително."
        ),
        "step.summary_t": (
            "Запишете изминалото време със SI единицата."
        ),
        "hint.summary_t": "Включете числото и s.",
        "step.formula_velocity_sq": (
            "Изберете уравнение за $\\Delta x$, което "
            "не изисква време."
        ),
        "hint.formula_velocity_sq": (
            "Използвайте $v^2 = v_0^2 + 2 a \\Delta x$, "
            "когато $t$ е неизвестно."
        ),
        "hint.calculate_dx_no_t": (
            "Превъртете до "
            "$\\Delta x = (v^2 - v_0^2)/(2a)$."
        ),
        "continue": "Добре. Да продължим.",
        "complete": (
            "Отлично. Решихте задачата по кинематика."
        ),
        "feedback.not_numeric": (
            "Не успях да прочета числова стойност. "
            "Добавете числото и неговата SI единица."
        ),
        "feedback.invalid_expected": (
            "Учебният помощник не можа да провери "
            "тази стъпка."
        ),
        "feedback.missing_unit": (
            "Добавете SI единицата за {quantity}."
        ),
        "feedback.unknown_unit": (
            "Не разпознах тази единица. Използвайте {unit}."
        ),
        "feedback.wrong_dimension": (
            "Числовата стойност може да е близка, "
            "но единицата трябва да означава {dimension}."
        ),
        "feedback.wrong_unit": (
            "Използвайте SI единицата {unit}."
        ),
        "feedback.wrong_sign": (
            "Проверете избраната положителна посока "
            "и знака на ускорението."
        ),
        "feedback.wrong_value": (
            "Проверете заместването и пресмятането. "
            "Въведеният текст беше {raw}."
        ),
        "feedback.correct": "Правилно.",
        "feedback.missing_equals": (
            "Напишете пълно уравнение със знака =."
        ),
        "feedback.wrong_formula": (
            "Това уравнение не свързва известните "
            "величини за тази стъпка."
        ),
        "feedback.summary_wrong": (
            "Посочете всеки искан резултат със "
            "SI единицата му."
        ),
        "feedback.summary_correct": (
            "Правилно. Това са крайните резултати."
        ),
        "quantity.v0": "начална скорост",
        "quantity.v": "скорост",
        "quantity.a": "ускорение",
        "quantity.t": "време",
        "quantity.dx": "преместване",
        "dimension.velocity": "скорост",
        "dimension.length": "дължина",
        "dimension.time": "време",
        "dimension.acceleration": "ускорение",
    },
}


def kt(language: str | None, key: str, **params) -> str:
    return tr(KINEMATICS_TEXT, language, key, **params)
