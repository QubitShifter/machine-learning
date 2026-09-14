from src.core.i18n.text import tr


ODE_TEXT = {
    "en": {
        "linear.title": "First-Order Linear ODE",
        "linear.title.generated": "Generated First-Order Linear ODE",
        "linear.statement": "Solve {equation}",
        "linear.complete": "Excellent. The linear ODE has been solved.",
        "linear.continue": "When you're ready, continue with the mathematical step.",
        "linear.identify_pq": "Please identify both P(x) and Q(x).",
        "linear.identify_pq_example": "You can write: P = ..., Q = ...",
        "linear.concept_hint": (
            "Ask a conceptual question such as "
            "'why do we use an integrating factor?' "
            "or use the current prompt as your guide."
        ),
        "linear.concept.mu": (
            "The integrating factor is chosen for a very specific reason.\n\n"
            "We start with:\n\n"
            "    y' + P(x)y = Q(x)\n\n"
            "and multiply everything by a function mu(x):\n\n"
            "    mu*y' + mu*P(x)*y = mu*Q(x)\n\n"
            "We want the two terms on the left to become the derivative "
            "of the product mu(x)*y.\n\n"
            "By the product rule:\n\n"
            "    d/dx(mu*y) = mu*y' + mu'*y\n\n"
            "So we need:\n\n"
            "    mu' = P(x)*mu\n\n"
            "The function that has this property is:\n\n"
            "    mu(x) = exp(integral(P(x)) dx)\n\n"
            "For this problem P(x) = {P}, so:\n\n"
            "    integral(P(x)) dx = {integrated_p}\n\n"
            "and therefore:\n\n"
            "    mu(x) = {mu}\n\n"
            "So the integrating factor is not an arbitrary trick. "
            "It is deliberately constructed so that the left side "
            "turns into one product derivative."
        ),
        "linear.concept.product": (
            "This comes directly from the product rule.\n\n"
            "For two functions mu(x) and y(x):\n\n"
            "    d/dx(mu*y) = mu*y' + mu'*y\n\n"
            "After multiplying the linear ODE by the integrating factor, "
            "the left side is:\n\n"
            "    mu*y' + mu*P(x)*y\n\n"
            "But the integrating factor was chosen so that:\n\n"
            "    mu' = P(x)*mu\n\n"
            "Therefore:\n\n"
            "    mu*P(x)*y = mu'*y\n\n"
            "and the left side becomes:\n\n"
            "    mu*y' + mu'*y\n\n"
            "which is exactly:\n\n"
            "    d/dx(mu*y)\n\n"
            "We are using the product rule backward."
        ),
        "linear.concept.constant": (
            "We add C because we are taking an indefinite integral.\n\n"
            "When we differentiate a constant, its derivative is zero.\n"
            "For example:\n\n"
            "    d/dx(x^2 + 5) = 2*x\n"
            "    d/dx(x^2 - 8) = 2*x\n\n"
            "So when we reverse differentiation, there are infinitely "
            "many antiderivatives that differ only by a constant.\n\n"
            "That is why we write:\n\n"
            "    integral(f(x)) dx = F(x) + C\n\n"
            "For a differential equation, C is especially important "
            "because it represents the whole family of solutions."
        ),
        "linear.concept.divide": (
            "At this stage we have an equation of the form:\n\n"
            "    mu(x)*y = F(x) + C\n\n"
            "We want y by itself, so we divide both sides by mu(x):\n\n"
            "    y = (F(x) + C) / mu(x)\n\n"
            "This is safe because an integrating factor has the form:\n\n"
            "    mu(x) = exp(...)\n\n"
            "and an exponential is always positive, so mu(x) is never zero."
        ),
        "linear.concept.pq": (
            "A first-order linear differential equation is written as:\n\n"
            "    y' + P(x)y = Q(x)\n\n"
            "P(x) is the coefficient multiplying y.\n\n"
            "Q(x) is the expression by itself on the right-hand side.\n\n"
            "So the goal is simply to compare the current equation "
            "term by term with this standard form."
        ),
        "linear.concept.fallback": (
            "This is a conceptual question about the current step. "
            "Try asking what part of the step is unclear, and I will "
            "explain the mathematical idea without advancing the problem."
        ),
        "linear.parse_error": (
            "I could not understand the mathematical input."
        ),
        "linear.feedback.standard_form.correct": (
            "Correct. The equation is already written "
            "in first-order linear standard form."
        ),
        "linear.suggestion.identify_pq": (
            "Next, identify P(x) and Q(x)."
        ),
        "linear.feedback.standard_form.missing": (
            "Please answer whether the equation is "
            "already in standard linear form."
        ),
        "linear.suggestion.standard_form.compare": (
            "Compare it with y' + P(x)y = Q(x)."
        ),
        "linear.feedback.standard_form.incorrect": (
            "This equation is already in first-order "
            "linear standard form."
        ),
        "linear.suggestion.standard_form.compare_direct": (
            "Compare it directly with "
            "y' + P(x)y = Q(x)."
        ),
        "linear.verify.compare.yes_correct": (
            "Verified. The proposed solution "
            "satisfies the original linear ODE."
        ),
        "linear.verify.compare.equal_retry": (
            "The two expressions are mathematically equal."
        ),
        "linear.verify.compare.equal_retry_suggestion": (
            "Compare the simplified left-hand side "
            "with Q(x)."
        ),
        "linear.verify.compare.no_correct": (
            "Correct. The proposed solution does not "
            "satisfy the original ODE."
        ),
        "linear.verify.compare.mismatch": (
            "The two expressions do not match."
        ),
        "linear.verify.compare.mismatch_suggestion": (
            "Compare the simplified expressions again."
        ),
        "linear.feedback.pq.correct": (
            "Correct. You identified both "
            "P(x) and Q(x)."
        ),
        "linear.suggestion.pq.next": (
            "Next, use P(x) to construct "
            "the integrating factor."
        ),
        "linear.feedback.mu.correct": (
            "Correct. You found the integrating factor."
        ),
        "linear.suggestion.mu.next": (
            "Next, multiply every term in the differential "
            "equation by the integrating factor."
        ),
        "linear.feedback.multiply.correct": (
            "Correct. You multiplied every term in the "
            "differential equation by the integrating factor."
        ),
        "linear.suggestion.multiply.next": (
            "Next, look at the two terms on the left. "
            "They form the derivative of a product."
        ),
        "linear.feedback.product.correct": (
            "Correct. The two left-hand terms are "
            "the derivative of the product mu(x)*y."
        ),
        "linear.suggestion.product.next": (
            "Next, integrate both sides with respect to x."
        ),
        "linear.feedback.integrate.correct": (
            "Correct. You integrated both sides and included "
            "the arbitrary constant C."
        ),
        "linear.suggestion.integrate.next": (
            "Next, divide by the integrating factor to "
            "solve explicitly for y."
        ),
        "linear.feedback.solve_y.correct": (
            "Correct. You divided by the integrating factor "
            "and solved explicitly for y."
        ),
        "linear.suggestion.solve_y.next": (
            "Next, verify the solution by substituting it "
            "back into the original differential equation."
        ),
        "linear.verify.diff.correct": (
            "Correct. That is the derivative of "
            "the proposed solution."
        ),
        "linear.verify.diff.suggestion": (
            "Next, substitute y and y' into "
            "y' + P(x)y."
        ),
        "linear.verify.substitute.correct": (
            "Correct. You substituted the proposed "
            "solution into the left-hand side."
        ),
        "linear.verify.substitute.suggestion": (
            "Now compare the result with Q(x)."
        ),
        "linear.stage.identify_form": (
            "A first-order linear ODE has the standard form:\n\n"
            "    y' + P(x)y = Q(x)\n\n"
            "Is the current equation already in this form?"
        ),
        "linear.stage.identify_pq": (
            "Compare the equation with:\n\n"
            "    y' + P(x)y = Q(x)\n\n"
            "Identify P(x) and Q(x)."
        ),
        "linear.stage.mu": (
            "We have:\n\n"
            "    P(x) = {P}\n\n"
            "Use:\n\n"
            "    mu(x) = exp(integral(P(x)) dx)\n\n"
            "Here integral(P(x)) dx = {integrated_p}\n\n"
            "Find mu(x)."
        ),
        "linear.stage.multiply": (
            "The integrating factor is:\n\n"
            "    mu(x) = {mu}\n\n"
            "Multiply EVERY term of\n\n"
            "    y' + ({P})*y = {Q}\n\n"
            "by the integrating factor."
        ),
        "linear.stage.product": (
            "The left-hand side now has the form:\n\n"
            "    mu*y' + mu*P(x)*y\n\n"
            "Use the product rule backward and rewrite "
            "the complete equation using:\n\n"
            "    d/dx(mu*y)"
        ),
        "linear.stage.integrate": (
            "We now have the derivative of a product.\n\n"
            "Integrate both sides with respect to x.\n\n"
            "The right-hand integrand is:\n"
            "    {integrand}\n\n"
            "Remember the arbitrary constant C."
        ),
        "linear.stage.solve_y": (
            "After integration we have:\n\n"
            "    ({mu})*y = {antiderivative} + C\n\n"
            "Divide by the integrating factor "
            "and solve explicitly for y."
        ),
        "linear.stage.verify": (
            "Verify that the proposed solution satisfies "
            "the original differential equation."
        ),
        "linear.stage.complete": "The linear ODE has been solved.",
        "linear.verify.diff": (
            "Differentiate the proposed solution "
            "y = {solution} with respect to x."
        ),
        "linear.verify.substitute": (
            "Substitute y and y' into the left-hand "
            "side of the original equation."
        ),
        "linear.verify.compare": (
            "After substitution, compare the simplified "
            "left-hand side with Q(x). Do they match?"
        ),
        "linear.compare.title": "Verification comparison",
        "linear.compare.left": "Simplified left-hand side",
        "linear.compare.right": "Right-hand side Q(x)",
        "linear.compare.question": "Do they match?",
        "separable.title": "Separable ODE",
        "separable.title.generated": "Generated Separable ODE",
        "separable.statement": "Solve {equation}",
        "separable.complete": (
            "Excellent. The separable ODE has "
            "been solved and verified."
        ),
        "separable.continue": (
            "When you're ready, continue with "
            "the mathematical step."
        ),
        "separable.stage.separate": (
            "First, separate the variables so that "
            "the y terms are on one side and the x terms "
            "are on the other."
        ),
        "separable.stage.separate_wrap": (
            "{base}\n\nOriginal equation:\n"
            "    {equation}\n\n"
            "Write the separated coefficient form, "
            "for example:\n"
            "    1/y = f(x)"
        ),
        "separable.stage.integrate": (
            "From separation we have:\n"
            "    (1/y) dy = {fx} dx\n\n"
            "Write the result after integrating both sides."
        ),
        "separable.hint.separate": (
            "For dy/dx = f(x)*y, divide both sides "
            "by y so the y-side becomes 1/y."
        ),
        "separable.hint.integrate": (
            "The y-side integrates to ln|y|. "
            "The x-side integrates {fx}."
        ),
        "separable.hint.exp": "Apply exp to both sides to undo ln.",
        "separable.hint.cancel": (
            "Simplify the expression exp(ln|y|) to |y|."
        ),
        "separable.hint.split": (
            "Use exp(a + b) = exp(a)*exp(b) to "
            "separate the + C in the exponent."
        ),
        "separable.hint.rename": (
            "Since C is arbitrary, exp(C) is just "
            "a positive constant. Rename it as K."
        ),
        "separable.hint.abs": (
            "If |y| equals a positive expression, "
            "then y can have either sign. Use +/- "
            "to represent both possibilities."
        ),
        "separable.hint.absorb": (
            "Combine +/- K into one new arbitrary constant C."
        ),
        "separable.hint.log_default": (
            "Use exp to undo ln, then handle the "
            "absolute value and arbitrary constant."
        ),
        "linear.title.stage.identify_form": (
            "Stage 1 — Recognize the linear form"
        ),
        "linear.title.stage.identify_pq": (
            "Stage 2 — Identify P(x) and Q(x)"
        ),
        "linear.title.stage.mu": (
            "Stage 3 — Find the integrating factor"
        ),
        "linear.title.stage.multiply": (
            "Stage 4 — Multiply by the integrating factor"
        ),
        "linear.title.stage.product": (
            "Stage 5 — Recognize the product derivative"
        ),
        "linear.title.stage.integrate": (
            "Stage 6 — Integrate both sides"
        ),
        "linear.title.stage.solve_y": "Stage 7 — Solve for y",
        "linear.title.stage.verify": (
            "Stage 8 — Verify the solution"
        ),
        "linear.title.stage.complete": "Complete",
        "separable.log.title.apply_exp": (
            "Step 3.1 — Apply exp to both sides"
        ),
        "separable.log.title.cancel": (
            "Step 3.2 — Simplify exp(ln|y|)"
        ),
        "separable.log.title.split": (
            "Step 3.3 — Split the exponential"
        ),
        "separable.log.title.rename": (
            "Step 3.4 — Rename exp(C)"
        ),
        "separable.log.title.abs": (
            "Step 3.5 — Remove the absolute value"
        ),
        "separable.log.title.absorb": (
            "Step 3.6 — Absorb the constants"
        ),
        "separable.log.title.complete": "Stage 3 complete",
        "separable.log.prompt.apply_exp": (
            "Starting from:\n"
            "    ln|y| = {fx} + C\n\n"
            "Apply the inverse of ln to BOTH sides.\n"
            "Write the complete transformed equation."
        ),
        "separable.log.prompt.cancel": (
            "Current equation:\n"
            "    exp(ln|y|) = exp({fx} + C)\n\n"
            "Simplify the expression exp(ln|y|).\n"
            "Write the complete equation."
        ),
        "separable.log.prompt.split": (
            "Current equation:\n"
            "    |y| = exp({fx} + C)\n\n"
            "Use:\n"
            "    exp(a + b) = exp(a)*exp(b)\n\n"
            "Rewrite the complete equation."
        ),
        "separable.log.prompt.rename": (
            "Current equation:\n"
            "    |y| = exp({fx})*exp(C)\n\n"
            "Since exp(C) is a positive constant, "
            "rename it as K.\n"
            "Rewrite the equation."
        ),
        "separable.log.prompt.abs": (
            "Current equation:\n"
            "    |y| = K*exp({fx})\n\n"
            "Remove the absolute value and represent "
            "both possible signs of y."
        ),
        "separable.log.prompt.absorb": (
            "Current equation:\n"
            "    y = +/- K*exp({fx})\n\n"
            "Combine +/- K into one new arbitrary "
            "constant C."
        ),
        "separable.log.prompt.complete": (
            "The logarithmic transformation is complete."
        ),
        "separable.verify.title.diff": (
            "Step 4.1 — Differentiate the proposed solution"
        ),
        "separable.verify.title.substitute": (
            "Step 4.2 — Substitute y into the original ODE"
        ),
        "separable.verify.title.compare": (
            "Step 4.3 — Compare both sides"
        ),
        "separable.verify.title.complete": "Verification complete",
        "separable.verify.prompt.diff": (
            "Your proposed solution is:\n"
            "    y = {solution}\n\n"
            "Differentiate it with respect to x.\n"
            "You may write:\n"
            "    dy/dx = ..."
        ),
        "separable.verify.prompt.substitute": (
            "The original differential equation has "
            "right-hand side:\n"
            "    {rhs}\n\n"
            "Substitute your proposed y into this "
            "right-hand side."
        ),
        "separable.verify.prompt.compare": (
            "Compare the two expressions:\n\n"
            "    dy/dx = {derivative}\n"
            "    RHS   = {rhs}\n\n"
            "Do they match?"
        ),
        "separable.verify.prompt.complete": (
            "The proposed solution has been verified."
        ),
        "separable.hint.verify": (
            "Differentiate the proposed solution and compare "
            "it with the original right-hand side after "
            "substituting y."
        ),
        "separable.concept.separate": (
            "A separable equation lets us move all y terms "
            "to one side and all x terms to the other. "
            "For dy/dx = f(x)*y, dividing by y produces "
            "1/y on the y-side and f(x) on the x-side."
        ),
        "separable.concept.integrate": (
            "After the variables are separated, we integrate "
            "each side with respect to its own variable. "
            "The integral of 1/y is ln|y|."
        ),
        "separable.concept.verify": (
            "Verification checks that the derivative of the "
            "proposed solution matches the original right-hand "
            "side after substituting that solution for y."
        ),
        "separable.compare.title": "Verification comparison",
        "separable.compare.left": "Derivative dy/dx",
        "separable.compare.right": (
            "Right-hand side after substitution"
        ),
        "separable.compare.question": "Do they match?",
    },
    "bg": {
        "linear.title": (
            "Линейно диференциално уравнение от първи ред"
        ),
        "linear.title.generated": (
            "Генерирано линейно ДУ от първи ред"
        ),
        "linear.statement": "Решете {equation}",
        "linear.complete": (
            "Отлично. Линейното ДУ е решено."
        ),
        "linear.continue": (
            "Когато сте готови, продължете с "
            "математическата стъпка."
        ),
        "linear.identify_pq": (
            "Моля, определете и P(x), и Q(x)."
        ),
        "linear.identify_pq_example": (
            "Можете да запишете: P = ..., Q = ..."
        ),
        "linear.concept_hint": (
            "Задайте концептуален въпрос, например "
            "„защо използваме интегриращ фактор?“ "
            "или следвайте текущата подкана."
        ),
        "linear.concept.mu": (
            "Интегриращият фактор се избира с конкретна цел.\n\n"
            "Започваме от:\n\n"
            "    y' + P(x)y = Q(x)\n\n"
            "и умножаваме всички членове по функция mu(x):\n\n"
            "    mu*y' + mu*P(x)*y = mu*Q(x)\n\n"
            "Искаме двата члена в лявата страна да образуват "
            "производната на произведението mu(x)*y.\n\n"
            "По правилото за производна на произведение:\n\n"
            "    d/dx(mu*y) = mu*y' + mu'*y\n\n"
            "Затова трябва:\n\n"
            "    mu' = P(x)*mu\n\n"
            "Функцията, която има това свойство, е:\n\n"
            "    mu(x) = exp(integral(P(x)) dx)\n\n"
            "За тази задача P(x) = {P}, следователно:\n\n"
            "    integral(P(x)) dx = {integrated_p}\n\n"
            "и затова:\n\n"
            "    mu(x) = {mu}\n\n"
            "Така интегриращият фактор не е произволен трик. "
            "Той е нарочно построен така, че лявата страна "
            "да се превърне в една производна на произведение."
        ),
        "linear.concept.product": (
            "Това следва директно от правилото за произведение.\n\n"
            "За две функции mu(x) и y(x):\n\n"
            "    d/dx(mu*y) = mu*y' + mu'*y\n\n"
            "След умножение на линейното ДУ по интегриращия фактор, "
            "лявата страна е:\n\n"
            "    mu*y' + mu*P(x)*y\n\n"
            "Но интегриращият фактор е избран така, че:\n\n"
            "    mu' = P(x)*mu\n\n"
            "Следователно:\n\n"
            "    mu*P(x)*y = mu'*y\n\n"
            "и лявата страна става:\n\n"
            "    mu*y' + mu'*y\n\n"
            "което е точно:\n\n"
            "    d/dx(mu*y)\n\n"
            "Използваме правилото за произведение назад."
        ),
        "linear.concept.constant": (
            "Добавяме C, защото вземаме неопределен интеграл.\n\n"
            "Когато диференцираме константа, производната ѝ е нула.\n"
            "Например:\n\n"
            "    d/dx(x^2 + 5) = 2*x\n"
            "    d/dx(x^2 - 8) = 2*x\n\n"
            "Затова при обратното на диференцирането има безкрайно "
            "много примитивни, които се различават само с константа.\n\n"
            "Затова пишем:\n\n"
            "    integral(f(x)) dx = F(x) + C\n\n"
            "За диференциално уравнение C е особено важна, "
            "защото представлява цялото семейство решения."
        ),
        "linear.concept.divide": (
            "След интегрирането имаме уравнение от вида:\n\n"
            "    mu(x)*y = F(x) + C\n\n"
            "За да изолираме y, разделяме двете страни "
            "на интегриращия фактор mu(x):\n\n"
            "    y = (F(x) + C) / mu(x)\n\n"
            "Това е безопасно, защото интегриращият фактор има вида:\n\n"
            "    mu(x) = exp(...)\n\n"
            "а експонента е винаги положителна, така че mu(x) "
            "никога не е нула."
        ),
        "linear.concept.pq": (
            "Линейно диференциално уравнение от първи ред "
            "се записва като:\n\n"
            "    y' + P(x)y = Q(x)\n\n"
            "P(x) е коефициентът, който умножава y.\n\n"
            "Q(x) е изразът сам по себе си в дясната страна.\n\n"
            "Целта е просто да сравните даденото уравнение "
            "член по член с този стандартен вид."
        ),
        "linear.concept.fallback": (
            "Това е концептуален въпрос за текущата стъпка. "
            "Попитайте коя част от стъпката е неясна и ще обясня "
            "математическата идея, без да придвижвам задачата."
        ),
        "linear.parse_error": (
            "Не успях да разбера математическия вход."
        ),
        "linear.feedback.standard_form.correct": (
            "Правилно. Уравнението вече е записано в "
            "стандартния вид на линейно диференциално "
            "уравнение от първи ред."
        ),
        "linear.suggestion.identify_pq": (
            "След това определете P(x) и Q(x)."
        ),
        "linear.feedback.standard_form.missing": (
            "Моля, отговорете дали уравнението вече е "
            "в стандартния линеен вид."
        ),
        "linear.suggestion.standard_form.compare": (
            "Сравнете го с y' + P(x)y = Q(x)."
        ),
        "linear.feedback.standard_form.incorrect": (
            "Това уравнение вече е в стандартния вид "
            "на линейно ДУ от първи ред."
        ),
        "linear.suggestion.standard_form.compare_direct": (
            "Сравнете го директно с y' + P(x)y = Q(x)."
        ),
        "linear.verify.compare.yes_correct": (
            "Проверено. Предложеното решение удовлетворява "
            "първоначалното линейно ДУ."
        ),
        "linear.verify.compare.equal_retry": (
            "Двата израза са математически равни."
        ),
        "linear.verify.compare.equal_retry_suggestion": (
            "Сравнете опростената лява страна с Q(x)."
        ),
        "linear.verify.compare.no_correct": (
            "Правилно. Предложеното решение не "
            "удовлетворява първоначалното ДУ."
        ),
        "linear.verify.compare.mismatch": (
            "Двата израза не съвпадат."
        ),
        "linear.verify.compare.mismatch_suggestion": (
            "Сравнете отново опростените изрази."
        ),
        "linear.feedback.pq.correct": (
            "Правилно. Определихте и P(x), и Q(x)."
        ),
        "linear.suggestion.pq.next": (
            "След това използвайте P(x), за да построите "
            "интегриращия фактор."
        ),
        "linear.feedback.mu.correct": (
            "Правилно. Намерихте интегриращия фактор."
        ),
        "linear.suggestion.mu.next": (
            "След това умножете всеки член на "
            "диференциалното уравнение по интегриращия "
            "фактор."
        ),
        "linear.feedback.multiply.correct": (
            "Правилно. Умножихте всеки член на "
            "диференциалното уравнение по интегриращия "
            "фактор."
        ),
        "linear.suggestion.multiply.next": (
            "След това погледнете двата члена отляво. "
            "Те образуват производната на произведение."
        ),
        "linear.feedback.product.correct": (
            "Правилно. Двата леви члена са производната "
            "на произведението mu(x)*y."
        ),
        "linear.suggestion.product.next": (
            "След това интегрирайте двете страни спрямо x."
        ),
        "linear.feedback.integrate.correct": (
            "Правилно. Интегрирахте двете страни и "
            "включихте произволната константа C."
        ),
        "linear.suggestion.integrate.next": (
            "След това разделете на интегриращия фактор, "
            "за да решите явно за y."
        ),
        "linear.feedback.solve_y.correct": (
            "Правилно. Разделихте на интегриращия фактор "
            "и решихте явно за y."
        ),
        "linear.suggestion.solve_y.next": (
            "След това проверете решението, като го "
            "заместите обратно в първоначалното "
            "диференциално уравнение."
        ),
        "linear.verify.diff.correct": (
            "Правилно. Това е производната на "
            "предложеното решение."
        ),
        "linear.verify.diff.suggestion": (
            "След това заместете y и y' в y' + P(x)y."
        ),
        "linear.verify.substitute.correct": (
            "Правилно. Заместихте предложеното решение "
            "в лявата страна."
        ),
        "linear.verify.substitute.suggestion": (
            "Сега сравнете резултата с Q(x)."
        ),
        "linear.stage.identify_form": (
            "Линейно ДУ от първи ред има стандартния вид:\n\n"
            "    y' + P(x)y = Q(x)\n\n"
            "Даденото уравнение от този вид ли е?"
        ),
        "linear.stage.identify_pq": (
            "Сравнете уравнението с:\n\n"
            "    y' + P(x)y = Q(x)\n\n"
            "Определете P(x) и Q(x)."
        ),
        "linear.stage.mu": (
            "Имаме:\n\n"
            "    P(x) = {P}\n\n"
            "Използвайте:\n\n"
            "    mu(x) = exp(integral(P(x)) dx)\n\n"
            "Тук integral(P(x)) dx = {integrated_p}\n\n"
            "Намерете интегриращия фактор mu(x)."
        ),
        "linear.stage.integrate": (
            "Сега имаме производна на произведение.\n\n"
            "Интегрирайте двете страни спрямо x.\n\n"
            "Подинтегралната функция вдясно е:\n"
            "    {integrand}\n\n"
            "Не забравяйте произволната константа C."
        ),
        "linear.stage.multiply": (
            "Интегриращият фактор е:\n\n"
            "    mu(x) = {mu}\n\n"
            "Умножете ВСЕКИ член на\n\n"
            "    y' + ({P})*y = {Q}\n\n"
            "по интегриращия фактор."
        ),
        "linear.stage.product": (
            "Лявата страна вече има вида:\n\n"
            "    mu*y' + mu*P(x)*y\n\n"
            "Използвайте правилото за произведение "
            "назад и препишете цялото уравнение чрез:\n\n"
            "    d/dx(mu*y)"
        ),
        "linear.stage.solve_y": (
            "След интегриране имаме:\n\n"
            "    ({mu})*y = {antiderivative} + C\n\n"
            "Разделете на интегриращия фактор и "
            "решете явно за y."
        ),
        "linear.stage.verify": (
            "Проверете дали предложеното решение "
            "удовлетворява първоначалното уравнение."
        ),
        "linear.stage.complete": "Линейното ДУ е решено.",
        "linear.verify.diff": (
            "Диференцирайте предложеното решение "
            "y = {solution} спрямо x."
        ),
        "linear.verify.substitute": (
            "Заместете y и y' в лявата страна на "
            "първоначалното уравнение."
        ),
        "linear.verify.compare": (
            "След заместване сравнете опростената "
            "лява страна с Q(x). Съвпадат ли?"
        ),
        "linear.compare.title": "Сравнение при проверка",
        "linear.compare.left": "Опростена лява страна",
        "linear.compare.right": "Дясна страна Q(x)",
        "linear.compare.question": "Съвпадат ли?",
        "separable.title": (
            "Уравнение с разделящи се променливи"
        ),
        "separable.title.generated": (
            "Генерирано уравнение с разделящи се променливи"
        ),
        "separable.statement": "Решете {equation}",
        "separable.complete": (
            "Отлично. Уравнението с разделящи се "
            "променливи е решено и проверено."
        ),
        "separable.continue": (
            "Когато сте готови, продължете с "
            "математическата стъпка."
        ),
        "separable.stage.separate": (
            "Първо разделете променливите така, че "
            "членовете с y да са от едната страна, "
            "а членовете с x — от другата."
        ),
        "separable.stage.separate_wrap": (
            "{base}\n\nПървоначално уравнение:\n"
            "    {equation}\n\n"
            "Запишете разделената форма с коефициенти, "
            "например:\n"
            "    1/y = f(x)"
        ),
        "separable.stage.integrate": (
            "След разделянето имаме:\n"
            "    (1/y) dy = {fx} dx\n\n"
            "Запишете резултата след интегриране на "
            "двете страни."
        ),
        "separable.hint.separate": (
            "За dy/dx = f(x)*y разделете двете страни "
            "на y, така че страната с y да стане 1/y."
        ),
        "separable.hint.integrate": (
            "Страната с y дава ln|y|. "
            "Страната с x интегрира {fx}."
        ),
        "separable.hint.exp": (
            "Приложете exp към двете страни, за да "
            "отмените ln."
        ),
        "separable.hint.cancel": (
            "Опростете израза exp(ln|y|) до |y|."
        ),
        "separable.hint.split": (
            "Използвайте exp(a + b) = exp(a)*exp(b), "
            "за да отделите + C в степента."
        ),
        "separable.hint.rename": (
            "Тъй като C е произволна, exp(C) е просто "
            "положителна константа. Преименувайте я на K."
        ),
        "separable.hint.abs": (
            "Ако |y| е равно на положителен израз, "
            "y може да има и двата знака. Използвайте "
            "+/-, за да покажете двете възможности."
        ),
        "separable.hint.absorb": (
            "Обединете +/- K в една нова произволна "
            "константа C."
        ),
        "separable.hint.log_default": (
            "Използвайте exp, за да отмените ln, после "
            "обработете абсолютната стойност и "
            "произволната константа."
        ),
        "linear.title.stage.identify_form": (
            "Етап 1 — Разпознайте линейния вид"
        ),
        "linear.title.stage.identify_pq": (
            "Етап 2 — Определете P(x) и Q(x)"
        ),
        "linear.title.stage.mu": (
            "Етап 3 — Намерете интегриращия фактор"
        ),
        "linear.title.stage.multiply": (
            "Етап 4 — Умножете по интегриращия фактор"
        ),
        "linear.title.stage.product": (
            "Етап 5 — Разпознайте производната на произведение"
        ),
        "linear.title.stage.integrate": (
            "Етап 6 — Интегрирайте двете страни"
        ),
        "linear.title.stage.solve_y": "Етап 7 — Решете за y",
        "linear.title.stage.verify": (
            "Етап 8 — Проверете решението"
        ),
        "linear.title.stage.complete": "Завършено",
        "separable.log.title.apply_exp": (
            "Стъпка 3.1 — Приложете exp към двете страни"
        ),
        "separable.log.title.cancel": (
            "Стъпка 3.2 — Опростете exp(ln|y|)"
        ),
        "separable.log.title.split": (
            "Стъпка 3.3 — Разделете експонентата"
        ),
        "separable.log.title.rename": (
            "Стъпка 3.4 — Преименувайте exp(C)"
        ),
        "separable.log.title.abs": (
            "Стъпка 3.5 — Премахнете абсолютната стойност"
        ),
        "separable.log.title.absorb": (
            "Стъпка 3.6 — Обединете константите"
        ),
        "separable.log.title.complete": "Етап 3 е завършен",
        "separable.log.prompt.apply_exp": (
            "Започваме от:\n"
            "    ln|y| = {fx} + C\n\n"
            "Приложете обратната операция на ln към "
            "И ДВЕТЕ страни.\n"
            "Запишете цялото преобразувано уравнение."
        ),
        "separable.log.prompt.cancel": (
            "Текущо уравнение:\n"
            "    exp(ln|y|) = exp({fx} + C)\n\n"
            "Опростете израза exp(ln|y|).\n"
            "Запишете цялото уравнение."
        ),
        "separable.log.prompt.split": (
            "Текущо уравнение:\n"
            "    |y| = exp({fx} + C)\n\n"
            "Използвайте:\n"
            "    exp(a + b) = exp(a)*exp(b)\n\n"
            "Препишете цялото уравнение."
        ),
        "separable.log.prompt.rename": (
            "Текущо уравнение:\n"
            "    |y| = exp({fx})*exp(C)\n\n"
            "Тъй като exp(C) е положителна константа, "
            "преименувайте я на K.\n"
            "Препишете уравнението."
        ),
        "separable.log.prompt.abs": (
            "Текущо уравнение:\n"
            "    |y| = K*exp({fx})\n\n"
            "Премахнете абсолютната стойност и покажете "
            "двата възможни знака на y."
        ),
        "separable.log.prompt.absorb": (
            "Текущо уравнение:\n"
            "    y = +/- K*exp({fx})\n\n"
            "Обединете +/- K в една нова произволна "
            "константа C."
        ),
        "separable.log.prompt.complete": (
            "Логаритмичното преобразуване е завършено."
        ),
        "separable.verify.title.diff": (
            "Стъпка 4.1 — Диференцирайте предложеното решение"
        ),
        "separable.verify.title.substitute": (
            "Стъпка 4.2 — Заместете y в първоначалното ДУ"
        ),
        "separable.verify.title.compare": (
            "Стъпка 4.3 — Сравнете двете страни"
        ),
        "separable.verify.title.complete": "Проверката е завършена",
        "separable.verify.prompt.diff": (
            "Предложеното решение е:\n"
            "    y = {solution}\n\n"
            "Диференцирайте го спрямо x.\n"
            "Можете да запишете:\n"
            "    dy/dx = ..."
        ),
        "separable.verify.prompt.substitute": (
            "Първоначалното диференциално уравнение има "
            "дясна страна:\n"
            "    {rhs}\n\n"
            "Заместете предложеното y в тази дясна страна."
        ),
        "separable.verify.prompt.compare": (
            "Сравнете двата израза:\n\n"
            "    dy/dx = {derivative}\n"
            "    RHS   = {rhs}\n\n"
            "Съвпадат ли?"
        ),
        "separable.verify.prompt.complete": (
            "Предложеното решение е проверено."
        ),
        "separable.hint.verify": (
            "Диференцирайте предложеното решение и го "
            "сравнете с първоначалната дясна страна след "
            "заместване на y."
        ),
        "separable.concept.separate": (
            "Уравнение с разделящи се променливи позволява "
            "всички членове с y да се преместят от едната "
            "страна, а членовете с x — от другата. "
            "За dy/dx = f(x)*y деленето на y дава "
            "1/y от страната с y и f(x) от страната с x."
        ),
        "separable.concept.integrate": (
            "След като променливите са разделени, "
            "интегрираме всяка страна спрямо собствената "
            "ѝ променлива. Интегралът на 1/y е ln|y|."
        ),
        "separable.concept.verify": (
            "Проверката установява дали производната на "
            "предложеното решение съвпада с първоначалната "
            "дясна страна след заместване на това решение за y."
        ),
        "separable.compare.title": "Сравнение при проверка",
        "separable.compare.left": "Производна dy/dx",
        "separable.compare.right": "Дясна страна след заместване",
        "separable.compare.question": "Съвпадат ли?",
    },
}


def ot(language: str | None, key: str, **params) -> str:
    return tr(ODE_TEXT, language, key, **params)
