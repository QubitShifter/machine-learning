from src.core.i18n.text import tr


GUIDED_TEXT = {
    "en": {
        "guided.unknown.addend.definition": "What is an addend?",
        "guided.unknown.addend.identify_known": (
            "How do I identify the known addend?"
        ),
        "guided.unknown.addend.unknown": "What is an unknown addend?",
        "guided.unknown.addend.find_unknown": (
            "Which inverse operation helps me find x?"
        ),
        "guided.unknown.minuend.definition": "What is a minuend?",
        "guided.unknown.subtrahend.definition": (
            "What is a subtrahend?"
        ),
        "guided.unknown.subtrahend.identify_known": (
            "How do I identify the known subtrahend?"
        ),
        "guided.unknown.minuend.find_unknown": (
            "Which inverse operation helps me find x?"
        ),
        "guided.unknown.factor.definition": "What is a factor?",
        "guided.unknown.product.definition": "What is a product?",
        "guided.unknown.factor.identify_known": (
            "How do I identify the known factor?"
        ),
        "guided.unknown.factor.find_unknown": (
            "How do I find the unknown factor?"
        ),
        "guided.unknown.explain.identify.add": (
            "The known addend is the number added to x. "
            "In {equation}, that number is written after "
            "the plus sign."
        ),
        "guided.unknown.explain.identify.sub": (
            "The known subtrahend is the number subtracted "
            "from x. In {equation}, that number is written "
            "after the minus sign."
        ),
        "guided.unknown.explain.identify.mul": (
            "The known factor is the number that multiplies "
            "x. In {equation}, that number is written next "
            "to x."
        ),
        "guided.unknown.explain.unknown_addend": (
            "x is the unknown addend. It is the number we "
            "add to the known addend to get the sum. The "
            "equation does not show the value of x yet."
        ),
        "guided.arith.parentheses.definition": (
            "What do parentheses mean?"
        ),
        "guided.arith.order.first": (
            "Which operation should I perform first?"
        ),
        "guided.arith.parentheses.why": (
            "Why must I calculate the parentheses first?"
        ),
        "guided.arith.left_to_right": (
            "How should I compute this expression?"
        ),
        "guided.arith.explain.parentheses": (
            "Parentheses group a part of the expression. "
            "You compute the grouped part before you use "
            "it in the next operation."
        ),
        "guided.arith.explain.multiply_first": (
            "Multiplication is done before addition when "
            "there are no parentheses around the addition. "
            "Find the product first, then add."
        ),
        "guided.arith.explain.parentheses_first": (
            "Compute the grouped part inside the "
            "parentheses first. Then use that result in "
            "the remaining operation."
        ),
        "guided.arith.explain.why_parentheses": (
            "The parentheses tell you which pair of numbers "
            "belongs together. If you skip them, you would "
            "change the meaning of the expression."
        ),
        "guided.arith.explain.left_to_right": (
            "This expression has two numbers and one "
            "operation. Work with those two numbers from "
            "left to right."
        ),
        "guided.pattern.sequence.what": (
            "What is a number pattern?"
        ),
        "guided.pattern.sequence.rule": (
            "How can I discover the rule?"
        ),
        "guided.pattern.chain.what": (
            "What is an operation chain?"
        ),
        "guided.pattern.chain.follow": (
            "How do I follow the chain?"
        ),
        "guided.pattern.chain.undo": (
            "How do I work backward through the operations?"
        ),
        "guided.pattern.explain.sequence": (
            "A number pattern is a list of numbers that "
            "follow a rule. In this exercise the rule is "
            "a common difference between neighboring terms."
        ),
        "guided.pattern.explain.rule": (
            "Look at two neighboring given numbers. The "
            "same change should appear between each pair. "
            "That change is the rule."
        ),
        "guided.pattern.explain.chain": (
            "An operation chain applies one written "
            "operation after another, starting from a "
            "first number."
        ),
        "guided.pattern.explain.follow": (
            "Read the chain from left to right. Apply only "
            "the next written operation to the value you "
            "already have."
        ),
        "guided.pattern.explain.undo": (
            "The last number is known. Undo the last "
            "written operation, then the one before it, "
            "until you recover the missing start."
        ),
        "guided.story.known": "What information is given?",
        "guided.story.unknown": "What are we trying to find?",
        "guided.story.how_to_start": "How should I start this step?",
        "guided.story.phrase.more_than": (
            'What does "more than" mean?'
        ),
        "guided.story.phrase.fewer": 'What does "fewer than" mean?',
        "guided.story.phrase.twice_as_many": (
            'What does "twice as many" mean?'
        ),
        "guided.story.phrase.times_as_many": (
            'What does "times as many" mean?'
        ),
        "guided.story.phrase.doubled": 'What does "doubled" mean?',
        "guided.story.phrase.remaining": (
            'What does "remaining" mean?'
        ),
        "guided.story.phrase.in_all": 'What does "in all" mean?',
        "guided.story.explain.known": (
            "The given facts are the numbers written in "
            "the story. Start from those visible numbers. "
            "Do not invent extra quantities."
        ),
        "guided.story.explain.unknown": (
            "The story asks for one unknown quantity. "
            "That is the number you must find after you "
            "use the relationships in the story."
        ),
        "guided.story.explain.start.identify": (
            "This step asks you to notice a number that "
            "is already written in the story. Copy that "
            "given number."
        ),
        "guided.story.explain.start.forward": (
            "This step uses one relationship from the "
            "story. Use only quantities you already know, "
            "and do one relationship at a time."
        ),
        "guided.story.explain.start.reverse": (
            "This step works backward. Undo the last "
            "change described in the story, using the "
            "inverse of that relationship."
        ),
        "guided.logic.known": "What information is given?",
        "guided.logic.unknown": "What do we need to find?",
        "guided.logic.first_clue": "Which clue should I use first?",
        "guided.logic.first_clue.distribution": (
            "Which clue should I use first?"
        ),
        "guided.logic.eliminate": (
            "How can I eliminate impossible possibilities?"
        ),
        "guided.logic.check": "How can I check my answer?",
    },
    "bg": {
        "guided.unknown.addend.definition": "Какво е събираемо?",
        "guided.unknown.addend.identify_known": (
            "Как да разпозная известното събираемо?"
        ),
        "guided.unknown.addend.unknown": (
            "Какво е неизвестно събираемо?"
        ),
        "guided.unknown.addend.find_unknown": (
            "Кое обратно действие помага да намеря x?"
        ),
        "guided.unknown.minuend.definition": "Какво е умаляемо?",
        "guided.unknown.subtrahend.definition": "Какво е умалител?",
        "guided.unknown.subtrahend.identify_known": (
            "Как да разпозная известния умалител?"
        ),
        "guided.unknown.minuend.find_unknown": (
            "Кое обратно действие помага да намеря x?"
        ),
        "guided.unknown.factor.definition": "Какво е множител?",
        "guided.unknown.product.definition": "Какво е произведение?",
        "guided.unknown.factor.identify_known": (
            "Как да разпозная известния множител?"
        ),
        "guided.unknown.factor.find_unknown": (
            "Как да намеря неизвестния множител?"
        ),
        "guided.unknown.explain.identify.add": (
            "Известното събираемо е числото, което се "
            "прибавя към x. В {equation} това число е "
            "след знака плюс."
        ),
        "guided.unknown.explain.identify.sub": (
            "Известният умалител е числото, което се "
            "изважда от x. В {equation} това число е "
            "след знака минус."
        ),
        "guided.unknown.explain.identify.mul": (
            "Известният множител е числото, по което се "
            "умножава x. В {equation} това число е до x."
        ),
        "guided.unknown.explain.unknown_addend": (
            "x е неизвестното събираемо. Това е числото, "
            "което прибавяме към известното събираемо, "
            "за да получим сбора. Уравнението още не "
            "показва стойността на x."
        ),
        "guided.arith.parentheses.definition": (
            "Какво означават скобите?"
        ),
        "guided.arith.order.first": (
            "Кое действие да извърша първо?"
        ),
        "guided.arith.parentheses.why": (
            "Защо първо пресмятаме скобите?"
        ),
        "guided.arith.left_to_right": (
            "Как да пресметна този израз?"
        ),
        "guided.arith.explain.parentheses": (
            "Скобите групират част от израза. Първо "
            "пресмятаме групираната част, после я "
            "използваме в следващото действие."
        ),
        "guided.arith.explain.multiply_first": (
            "Умножението е преди събирането, когато "
            "събирането не е в скоби. Първо намерете "
            "произведението, после съберете."
        ),
        "guided.arith.explain.parentheses_first": (
            "Първо пресметнете групираната част в "
            "скобите. После използвайте този резултат "
            "в останалото действие."
        ),
        "guided.arith.explain.why_parentheses": (
            "Скобите показват кои две числа са заедно. "
            "Ако ги пропуснем, смисълът на израза се "
            "променя."
        ),
        "guided.arith.explain.left_to_right": (
            "Този израз има две числа и едно действие. "
            "Работете с тези две числа отляво надясно."
        ),
        "guided.pattern.sequence.what": (
            "Какво е числова редица?"
        ),
        "guided.pattern.sequence.rule": (
            "Как да открия правилото?"
        ),
        "guided.pattern.chain.what": (
            "Какво е верига от действия?"
        ),
        "guided.pattern.chain.follow": (
            "Как да следвам веригата?"
        ),
        "guided.pattern.chain.undo": (
            "Как да работя назад по действията?"
        ),
        "guided.pattern.explain.sequence": (
            "Числовата редица е списък от числа с "
            "правило. Тук правилото е обща разлика "
            "между съседните членове."
        ),
        "guided.pattern.explain.rule": (
            "Погледнете две съседни дадени числа. "
            "Същата промяна трябва да се повтаря. "
            "Тази промяна е правилото."
        ),
        "guided.pattern.explain.chain": (
            "Веригата прилага едно записано действие "
            "след друго, като започва от първото число."
        ),
        "guided.pattern.explain.follow": (
            "Четете веригата отляво надясно. Приложете "
            "само следващото записано действие към "
            "стойността, която вече имате."
        ),
        "guided.pattern.explain.undo": (
            "Последното число е известно. Отменете "
            "последното записано действие, после "
            "предишното, докато възстановите началото."
        ),
        "guided.story.known": "Какво знаем от условието?",
        "guided.story.unknown": "Какво трябва да намерим?",
        "guided.story.how_to_start": (
            "Как да започна тази стъпка?"
        ),
        "guided.story.phrase.more_than": (
            "Какво означава „с повече“?"
        ),
        "guided.story.phrase.fewer": (
            "Какво означава „по-малко“?"
        ),
        "guided.story.phrase.twice_as_many": (
            "Какво означава „два пъти толкова“?"
        ),
        "guided.story.phrase.times_as_many": (
            "Какво означава „пъти толкова“?"
        ),
        "guided.story.phrase.doubled": (
            "Какво означава „удвоен“?"
        ),
        "guided.story.phrase.remaining": (
            "Какво означава „останали“?"
        ),
        "guided.story.phrase.in_all": (
            "Какво означава „общо“?"
        ),
        "guided.story.explain.known": (
            "Дадени са числата, написани в условието. "
            "Започни от тези видими числа. Не измисляй "
            "други количества."
        ),
        "guided.story.explain.unknown": (
            "Задачата иска едно неизвестно количество. "
            "Това е числото, което трябва да намериш, "
            "след като използваш връзките в текста."
        ),
        "guided.story.explain.start.identify": (
            "Тази стъпка иска да забележиш число, което "
            "вече е написано в условието. Препиши това "
            "дадено число."
        ),
        "guided.story.explain.start.forward": (
            "Тази стъпка използва една връзка от "
            "условието. Използвай само вече известни "
            "количества и само една връзка наведнъж."
        ),
        "guided.story.explain.start.reverse": (
            "Тази стъпка работи назад. Отмени последната "
            "промяна от условието с обратното действие."
        ),
        "guided.logic.known": "Какво знаем от условието?",
        "guided.logic.unknown": "Какво трябва да намерим?",
        "guided.logic.first_clue": "Коя улика да използвам първо?",
        "guided.logic.first_clue.distribution": (
            "Кое условие да използвам първо?"
        ),
        "guided.logic.eliminate": (
            "Как да изключа невъзможните варианти?"
        ),
        "guided.logic.check": "Как да проверя отговора си?",
    },
}


def gst(language: str | None, key: str, **params) -> str:
    return tr(GUIDED_TEXT, language, key, **params)
