from src.core.i18n.text import tr


STORY_GUIDANCE_TEXT = {
    "en": {
        "story.guide.given.cards_total": (
            "We know Maya has {red} red cards and {blue} "
            "blue cards. The total is not given — that is "
            "what we need to find."
        ),
        "story.guide.ask.cards_total": (
            "We need to find how many cards Maya has in "
            "all, after we put the red cards and the blue "
            "cards together."
        ),
        "story.guide.step.identify.cards_total.red": (
            "This step asks how many red cards Maya has. "
            "Read the story: Maya has {red} red cards. "
            "That number is already given."
        ),
        "story.guide.step.forward.cards_total.total": (
            "This step asks how many cards Maya has in "
            "all. You already know the {red} red cards "
            "and the {blue} blue cards. In all means add "
            "those two groups."
        ),
        "story.guide.phrase.here.cards_total.in_all": (
            "In this story, in all means the red cards "
            "and the blue cards together."
        ),
        "story.guide.given.stamps_then_stickers": (
            "We know Maya starts with {stamps} stamps, "
            "buys {more} more stamps, and then buys "
            "{times} times as many stickers as the stamps "
            "she has after that. The number of stickers "
            "is not given — that is what we need to find."
        ),
        "story.guide.ask.stamps_then_stickers": (
            "We need to find how many stickers Maya "
            "buys, using the stamps she has after buying "
            "{more} more."
        ),
        "story.guide.step.identify.stamps_then_stickers.stamps": (
            "This step asks how many stamps Maya has at "
            "the start. Read the story: she has {stamps} "
            "stamps. That number is already given."
        ),
        "story.guide.step.forward.stamps_then_stickers.stamps_now": (
            "Maya starts with {stamps} stamps and buys "
            "{more} more. This step asks how many stamps "
            "she has after that. Use only those two given "
            "amounts."
        ),
        "story.guide.step.forward.stamps_then_stickers.stickers": (
            "The story says Maya buys {times} times as "
            "many stickers as the stamps she now has. "
            "Times as many means multiplication, using "
            "the stamps after she bought more."
        ),
        "story.guide.phrase.here.stamps_then_stickers.times_as_many": (
            "In this story, the stickers are several "
            "times as many as the stamps Maya has after "
            "buying more."
        ),
        "story.guide.given.boxes_then_stickers": (
            "We know Leo packed {boxes} boxes with {each} "
            "stamps in each box, then bought {more} more "
            "stamps, and then bought {times} times as many "
            "stickers as the stamps he has after that. The "
            "number of stickers is not given — that is "
            "what we need to find."
        ),
        "story.guide.ask.boxes_then_stickers": (
            "We need to find how many stickers Leo bought, "
            "using the stamps he has after packing the "
            "boxes and buying more."
        ),
        "story.guide.step.identify.boxes_then_stickers.each": (
            "This step asks how many stamps Leo put in "
            "one box. Read the story: there are {each} "
            "stamps in each box. That number is already "
            "given."
        ),
        "story.guide.step.forward.boxes_then_stickers.boxed": (
            "There are {boxes} boxes with {each} stamps "
            "in each box. This step asks for the stamps "
            "packed in the boxes. Use those two given "
            "numbers."
        ),
        "story.guide.step.forward.boxes_then_stickers.stamps_now": (
            "After packing the boxes, Leo bought {more} "
            "more stamps. This step asks how many stamps "
            "he has then. Add that extra given amount to "
            "the stamps from the boxes."
        ),
        "story.guide.step.forward.boxes_then_stickers.stickers": (
            "The story says Leo bought {times} times as "
            "many stickers as the stamps he now has. "
            "Times as many means multiplication."
        ),
        "story.guide.phrase.here.boxes_then_stickers.times_as_many": (
            "In this story, the stickers are several "
            "times as many as the stamps Leo has after "
            "packing the boxes and buying more."
        ),
        "story.guide.given.more_than": (
            "We know Leo has {base} marbles and Nina has "
            "{extra} more than Leo. Nina's number is not "
            "given — that is what we need to find."
        ),
        "story.guide.ask.more_than": (
            "We need to find how many marbles Nina has, "
            "knowing she has {extra} more than Leo's "
            "{base} marbles."
        ),
        "story.guide.step.identify.more_than.base": (
            "This step asks how many marbles Leo has. "
            "Read the story: Leo has {base} marbles. "
            "That number is already given."
        ),
        "story.guide.step.forward.more_than.nina": (
            "Nina has {extra} more marbles than Leo. "
            "More than means add that extra amount to "
            "Leo's marbles."
        ),
        "story.guide.phrase.here.more_than.more_than": (
            "In this story, Nina has a fixed extra "
            "amount more than Leo, so Nina has more "
            "marbles than Leo."
        ),
        "story.guide.given.fewer_than": (
            "We know Nina has {base} marbles and Leo "
            "has {fewer} fewer than Nina. Leo's number "
            "is not given — that is what we need to find."
        ),
        "story.guide.ask.fewer_than": (
            "We need to find how many marbles Leo has, "
            "knowing he has {fewer} fewer than Nina's "
            "{base} marbles."
        ),
        "story.guide.step.identify.fewer_than.base": (
            "This step asks how many marbles Nina has. "
            "Read the story: Nina has {base} marbles. "
            "That number is already given."
        ),
        "story.guide.step.forward.fewer_than.leo": (
            "Leo has {fewer} fewer marbles than Nina. "
            "Fewer than means subtract that amount from "
            "Nina's marbles."
        ),
        "story.guide.phrase.here.fewer_than.fewer": (
            "In this story, Leo has a fixed amount fewer "
            "than Nina, so Leo has fewer marbles than Nina."
        ),
        "story.guide.given.twice_as_many": (
            "We know Leo has {base} marbles and Nina has "
            "twice as many marbles as Leo. Nina's number "
            "is not given — that is what we need to find."
        ),
        "story.guide.ask.twice_as_many": (
            "We need to find how many marbles Nina has, "
            "knowing she has twice as many as Leo's "
            "{base} marbles."
        ),
        "story.guide.step.identify.twice_as_many.base": (
            "This step asks how many marbles Leo has. "
            "Read the story: Leo has {base} marbles. "
            "That number is already given."
        ),
        "story.guide.step.forward.twice_as_many.nina": (
            "Nina has twice as many marbles as Leo. "
            "Twice as many means two times Leo's marbles, "
            "not two more."
        ),
        "story.guide.phrase.here.twice_as_many.twice_as_many": (
            "In this story, Nina has twice as many "
            "marbles as Leo."
        ),
        "story.guide.given.more_then_together": (
            "We know Leo has {base} marbles and Nina has "
            "{extra} more than Leo. Their total is not "
            "given — that is what we need to find."
        ),
        "story.guide.ask.more_then_together": (
            "We need to find how many marbles Leo and "
            "Nina have together, after we first use that "
            "Nina has {extra} more than Leo."
        ),
        "story.guide.step.identify.more_then_together.base": (
            "This step asks how many marbles Leo has. "
            "Read the story: Leo has {base} marbles. "
            "That number is already given."
        ),
        "story.guide.step.forward.more_then_together.nina": (
            "Nina has {extra} more marbles than Leo. "
            "More than means add that extra amount to "
            "Leo's marbles first."
        ),
        "story.guide.step.forward.more_then_together.total": (
            "This step asks how many marbles they have "
            "together. Together means add Leo's marbles "
            "and Nina's marbles."
        ),
        "story.guide.phrase.here.more_then_together.more_than": (
            "In this story, Nina has a fixed extra "
            "amount more than Leo."
        ),
        "story.guide.phrase.here.more_then_together.in_all": (
            "In this story, together means Leo's marbles "
            "and Nina's marbles added."
        ),
        "story.guide.given.books_from_class": (
            "We know there are {girls} girls and {extra} "
            "more boys than girls, and there are twice as "
            "many books as children. The number of books "
            "is not given — that is what we need to find."
        ),
        "story.guide.ask.books_from_class": (
            "We need to find how many books there are, "
            "knowing there are twice as many books as "
            "children in the class."
        ),
        "story.guide.step.identify.books_from_class.girls": (
            "This step asks how many girls are in the "
            "class. Read the story: there are {girls} "
            "girls. That number is already given."
        ),
        "story.guide.step.forward.books_from_class.boys": (
            "There are {extra} more boys than girls. "
            "More than means add that extra amount to "
            "the number of girls."
        ),
        "story.guide.step.forward.books_from_class.children": (
            "This step asks how many children are in the "
            "class. The children are the girls and the "
            "boys together."
        ),
        "story.guide.step.forward.books_from_class.books": (
            "The story says there are twice as many books "
            "as children. Twice as many means two times "
            "the number of children, not two extra books."
        ),
        "story.guide.phrase.here.books_from_class.more_than": (
            "In this story, there are a fixed extra "
            "number of boys compared with the girls."
        ),
        "story.guide.phrase.here.books_from_class.twice_as_many": (
            "In this story, the books are twice as many "
            "as the children."
        ),
        "story.guide.given.remaining_after_taken": (
            "We know that {taken} bottles were taken out "
            "and {remaining} bottles were left. The "
            "starting number is not given — that is what "
            "we need to find."
        ),
        "story.guide.ask.remaining_after_taken": (
            "We need to find how many bottles were in the "
            "crate at the very beginning, before {taken} "
            "bottles were taken out."
        ),
        "story.guide.step.identify.remaining_after_taken.remaining": (
            "This step asks how many bottles were left. "
            "Read the story: {remaining} bottles were "
            "left. That number is already given."
        ),
        "story.guide.step.undo.remaining_after_taken.start": (
            "At first {taken} bottles were taken out. To "
            "recover the starting number, put those "
            "{taken} bottles back by adding."
        ),
        "story.guide.phrase.here.remaining_after_taken.remaining": (
            "In this story, remaining means the bottles "
            "left after some were taken out."
        ),
        "story.guide.given.removed_then_doubled": (
            "We know that {taken} bottles were removed, "
            "the remaining number was doubled, and there "
            "were {final} bottles after that. The starting "
            "number is not given — that is what we need "
            "to find."
        ),
        "story.guide.ask.removed_then_doubled": (
            "We need to find how many bottles were in the "
            "crate at the very beginning, before {taken} "
            "bottles were removed."
        ),
        "story.guide.step.identify.removed_then_doubled.final": (
            "This step asks how many bottles there were "
            "after the remaining bottles were doubled. "
            "Read the story: after that there were "
            "{final} bottles. That number is already given."
        ),
        "story.guide.step.undo.removed_then_doubled.remaining": (
            "The remaining bottles were doubled, that is "
            "multiplied by 2. To go back, use the inverse "
            "operation — divide by 2."
        ),
        "story.guide.step.undo.removed_then_doubled.start": (
            "At first {taken} bottles were removed. To "
            "recover the starting number, put those "
            "{taken} bottles back by adding."
        ),
        "story.guide.phrase.here.removed_then_doubled.doubled": (
            "In this problem, the remaining bottles after "
            "the removal were doubled."
        ),
        "story.guide.phrase.here.removed_then_doubled.remaining": (
            "In this story, remaining means the bottles "
            "left after some were taken out, before that "
            "number was doubled."
        ),
        "story.guide.given.removed_doubled_then_added": (
            "We know that {taken} bottles were removed, "
            "the remaining number was doubled, {added} "
            "bottles were then added, and there were "
            "{final} bottles at the end. The starting "
            "number is not given — that is what we need "
            "to find."
        ),
        "story.guide.ask.removed_doubled_then_added": (
            "We need to find how many bottles were in the "
            "crate at the very beginning, before {taken} "
            "bottles were removed."
        ),
        "story.guide.step.identify.removed_doubled_then_added.final": (
            "The first step asks how many bottles there "
            "were at the end. Read the story: “After that "
            "there were {final} bottles.” That number is "
            "already given."
        ),
        "story.guide.step.undo.removed_doubled_then_added.doubled": (
            "In the last action they added {added} "
            "bottles. To go back one step, use the "
            "inverse operation — subtraction. Think about "
            "what you should subtract from the final "
            "number."
        ),
        "story.guide.step.undo.removed_doubled_then_added.remaining": (
            "The number was doubled, that is multiplied "
            "by 2. To go back, use the inverse operation "
            "— divide by 2."
        ),
        "story.guide.step.undo.removed_doubled_then_added.start": (
            "At first they removed {taken} bottles. To "
            "recover the starting number, put those "
            "{taken} bottles back by adding."
        ),
        "story.guide.phrase.here.removed_doubled_then_added.doubled": (
            "In this problem, the remaining bottles after "
            "the removal were doubled."
        ),
        "story.guide.phrase.here.removed_doubled_then_added.remaining": (
            "In this story, remaining means the bottles "
            "left after some were taken out, before that "
            "number was doubled."
        ),
        "story.guide.phrase.doubled.define": (
            "Doubled means multiplied by 2. For example, "
            "if we have {ex_left} bottles and double "
            "them, we get {ex_result}."
        ),
        "story.guide.phrase.doubled.simpler_words": (
            "Doubled means we make the amount twice as "
            "large. Imagine two equal groups."
        ),
        "story.guide.phrase.doubled.analogy": (
            "Imagine a row of bottles, then put another "
            "row of the same length next to it. That "
            "doubles how many there are."
        ),
        "story.guide.phrase.doubled.example.apples": (
            "If we have 3 apples and double that number, "
            "we have 6 apples. That is multiplying by 2. "
            "This is a separate example, not the numbers "
            "from the story."
        ),
        "story.guide.phrase.remaining.define": (
            "Remaining means how many are still there "
            "after some are taken away."
        ),
        "story.guide.phrase.more_than.define": (
            "More than means add a fixed extra amount. "
            "For example, {ex_extra} more than {ex_left} "
            "is {ex_result}."
        ),
        "story.guide.phrase.fewer.define": (
            "Fewer than means subtract a fixed amount. "
            "For example, {ex_extra} fewer than {ex_left} "
            "is {ex_result}."
        ),
        "story.guide.phrase.twice_as_many.define": (
            "Twice as many means two times as many, not "
            "two more. For example, if Leo has {ex_left} "
            "marbles, twice as many is {ex_result}."
        ),
        "story.guide.phrase.times_as_many.define": (
            "Times as many means multiplication. For "
            "example, {ex_times} times as many as "
            "{ex_left} is {ex_result}."
        ),
        "story.guide.phrase.in_all.define": (
            "In all, or together, means add the groups "
            "to find the total."
        ),
        "story.method.setup": (
            "You can write {setup} without finishing the "
            "arithmetic yet."
        ),
        "story.method.fallback": (
            "I can help with this step without giving the "
            "finished number. Look at the last action in "
            "the story and undo that action. The starting "
            "amount is found only after every action is "
            "reversed."
        ),
        "story.hint.understand.identify": (
            "This number is already written in the story. "
            "We need that given amount, not a hidden "
            "starting number."
        ),
        "story.hint.operation.identify": (
            "Copy the given number the step is asking for. "
            "Do not work backwards yet."
        ),
        "story.hint.understand.undo.add": (
            "The last action added {other} more bottles. "
            "We need the count immediately before that "
            "addition."
        ),
        "story.hint.operation.undo.add": (
            "To undo adding {other} bottles, use the "
            "inverse of addition — subtraction."
        ),
        "story.hint.understand.undo.double": (
            "The remaining quantity was doubled. We need "
            "the number from just before that doubling."
        ),
        "story.hint.operation.undo.double": (
            "Use the inverse of multiplying by 2: divide "
            "by 2."
        ),
        "story.hint.understand.undo.sub": (
            "The story says {other} were taken out. We "
            "need the number from just before they were "
            "taken out."
        ),
        "story.hint.operation.undo.sub": (
            "Use the inverse of subtraction: addition."
        ),
        "story.hint.understand.undo.mul": (
            "The story multiplies by {other}. We need the "
            "number from just before that multiplication."
        ),
        "story.hint.operation.undo.mul": (
            "Use the inverse of multiplication: division."
        ),
        "story.hint.understand.forward.add": (
            "The story asks us to put these groups together."
        ),
        "story.hint.operation.forward.add": (
            "Use addition to combine the groups."
        ),
        "story.hint.understand.forward.sub": (
            "The story takes one amount away from another."
        ),
        "story.hint.operation.forward.sub": (
            "Use subtraction to find how many are left."
        ),
        "story.hint.understand.forward.mul": (
            "The story makes one amount a number of times "
            "as large as another."
        ),
        "story.hint.operation.forward.mul": (
            "Use multiplication."
        ),
        "story.hint.understand.forward.double": (
            "The story doubles one of the amounts."
        ),
        "story.hint.operation.forward.double": (
            "Doubling means multiply by 2."
        ),
        "story.hint.understand.generic": (
            "Look at the story relationship this step is "
            "asking about."
        ),
        "story.hint.operation.generic": (
            "Use the inverse of the last action, or the "
            "operation the story names for this step."
        ),
        "story.hint.setup.expression": (
            "Set up the calculation: {setup}"
        ),
        "story.hint.setup.identify": (
            "Use the given number from the story. Do not "
            "work backwards yet."
        ),
        "story.hint.setup.generic": (
            "Set up the inverse of the last action. Do not "
            "skip ahead to the starting number."
        ),
        "story.hint.last": (
            "This is the last hint for this step."
        ),
        "story.hint.exhausted": (
            "Those are all the hints for this step. You "
            "can still try an answer."
        ),
        "story.incorrect.identify": (
            "That is not the correct result. Check the "
            "number already written in the story."
        ),
        "story.incorrect.undo": (
            "That is not the correct result. Check what "
            "the last action in the story was and try to "
            "undo it."
        ),
        "story.incorrect.forward": (
            "That is not the correct result. Check which "
            "groups the story asks you to combine."
        ),
    },
    "bg": {
        "story.guide.given.cards_total": (
            "Знаем, че Мая има {red} червени картички и "
            "{blue} сини картички. Общият брой не е "
            "даден — него трябва да намерим."
        ),
        "story.guide.ask.cards_total": (
            "Търсим колко картички има Мая общо, след "
            "като съберем червените и сините."
        ),
        "story.guide.step.identify.cards_total.red": (
            "Тази стъпка пита колко червени картички има "
            "Мая. Прочети условието: Мая има {red} "
            "червени картички. Този брой вече е даден."
        ),
        "story.guide.step.forward.cards_total.total": (
            "Тази стъпка пита колко картички има Мая "
            "общо. Вече знаеш {red} червени и {blue} "
            "сини картички. Общо означава да събереш "
            "тези две групи."
        ),
        "story.guide.phrase.here.cards_total.in_all": (
            "В тази задача „общо“ означава червените и "
            "сините картички заедно."
        ),
        "story.guide.given.stamps_then_stickers": (
            "Знаем, че Мая започва с {stamps} марки, "
            "купува още {more} марки и после купува "
            "{times} пъти толкова лепенки, колкото са "
            "марките ѝ след това. Броят на лепенките не "
            "е даден — него трябва да намерим."
        ),
        "story.guide.ask.stamps_then_stickers": (
            "Търсим колко лепенки купува Мая, като "
            "използваме марките ѝ, след като е купила "
            "още {more}."
        ),
        "story.guide.step.identify.stamps_then_stickers.stamps": (
            "Тази стъпка пита с колко марки започва Мая. "
            "Прочети условието: тя има {stamps} марки. "
            "Този брой вече е даден."
        ),
        "story.guide.step.forward.stamps_then_stickers.stamps_now": (
            "Мая започва с {stamps} марки и купува още "
            "{more}. Тази стъпка пита колко марки има "
            "след това. Използвай само тези две дадени "
            "числа."
        ),
        "story.guide.step.forward.stamps_then_stickers.stickers": (
            "В условието пише, че Мая купува {times} "
            "пъти толкова лепенки, колкото са марките ѝ "
            "сега. Пъти толкова означава умножение с "
            "марките след покупката."
        ),
        "story.guide.phrase.here.stamps_then_stickers.times_as_many": (
            "В тази задача лепенките са няколко пъти "
            "толкова, колкото са марките на Мая след "
            "покупката."
        ),
        "story.guide.given.boxes_then_stickers": (
            "Знаем, че Лео е напълнил {boxes} кутии по "
            "{each} марки в кутия, после е купил още "
            "{more} марки и след това {times} пъти "
            "толкова лепенки, колкото са марките му "
            "тогава. Броят на лепенките не е даден — "
            "него трябва да намерим."
        ),
        "story.guide.ask.boxes_then_stickers": (
            "Търсим колко лепенки е купил Лео, като "
            "използваме марките му след кутиите и "
            "покупката."
        ),
        "story.guide.step.identify.boxes_then_stickers.each": (
            "Тази стъпка пита по колко марки е сложил "
            "Лео в една кутия. Прочети условието: в "
            "кутия има {each} марки. Този брой вече е "
            "даден."
        ),
        "story.guide.step.forward.boxes_then_stickers.boxed": (
            "Има {boxes} кутии по {each} марки в кутия. "
            "Тази стъпка пита за марките в кутиите. "
            "Използвай тези две дадени числа."
        ),
        "story.guide.step.forward.boxes_then_stickers.stamps_now": (
            "След кутиите Лео е купил още {more} марки. "
            "Тази стъпка пита колко марки има тогава. "
            "Прибави това дадено число към марките от "
            "кутиите."
        ),
        "story.guide.step.forward.boxes_then_stickers.stickers": (
            "В условието пише, че Лео е купил {times} "
            "пъти толкова лепенки, колкото са марките му "
            "сега. Пъти толкова означава умножение."
        ),
        "story.guide.phrase.here.boxes_then_stickers.times_as_many": (
            "В тази задача лепенките са няколко пъти "
            "толкова, колкото са марките на Лео след "
            "кутиите и покупката."
        ),
        "story.guide.given.more_than": (
            "Знаем, че Лео има {base} топчета, а Нина "
            "има с {extra} повече от Лео. Броят на Нина "
            "не е даден — него трябва да намерим."
        ),
        "story.guide.ask.more_than": (
            "Търсим колко топчета има Нина, като знаем, "
            "че има с {extra} повече от {base} топчета "
            "на Лео."
        ),
        "story.guide.step.identify.more_than.base": (
            "Тази стъпка пита колко топчета има Лео. "
            "Прочети условието: Лео има {base} топчета. "
            "Този брой вече е даден."
        ),
        "story.guide.step.forward.more_than.nina": (
            "Нина има с {extra} топчета повече от Лео. "
            "Повече означава да прибавиш това число към "
            "топчетата на Лео."
        ),
        "story.guide.phrase.here.more_than.more_than": (
            "В тази задача Нина има определено число "
            "топчета повече от Лео, затова Нина има "
            "повече топчета."
        ),
        "story.guide.given.fewer_than": (
            "Знаем, че Нина има {base} топчета, а Лео "
            "има с {fewer} по-малко от Нина. Броят на "
            "Лео не е даден — него трябва да намерим."
        ),
        "story.guide.ask.fewer_than": (
            "Търсим колко топчета има Лео, като знаем, "
            "че има с {fewer} по-малко от {base} "
            "топчета на Нина."
        ),
        "story.guide.step.identify.fewer_than.base": (
            "Тази стъпка пита колко топчета има Нина. "
            "Прочети условието: Нина има {base} топчета. "
            "Този брой вече е даден."
        ),
        "story.guide.step.forward.fewer_than.leo": (
            "Лео има с {fewer} топчета по-малко от Нина. "
            "По-малко означава да извадиш това число от "
            "топчетата на Нина."
        ),
        "story.guide.phrase.here.fewer_than.fewer": (
            "В тази задача Лео има определено число "
            "топчета по-малко от Нина."
        ),
        "story.guide.given.twice_as_many": (
            "Знаем, че Лео има {base} топчета, а Нина "
            "има два пъти толкова топчета, колкото Лео. "
            "Броят на Нина не е даден — него трябва да "
            "намерим."
        ),
        "story.guide.ask.twice_as_many": (
            "Търсим колко топчета има Нина, като знаем, "
            "че има два пъти толкова, колкото са {base} "
            "топчета на Лео."
        ),
        "story.guide.step.identify.twice_as_many.base": (
            "Тази стъпка пита колко топчета има Лео. "
            "Прочети условието: Лео има {base} топчета. "
            "Този брой вече е даден."
        ),
        "story.guide.step.forward.twice_as_many.nina": (
            "Нина има два пъти толкова топчета, колкото "
            "Лео. Два пъти толкова означава умножение "
            "по 2, а не с 2 повече."
        ),
        "story.guide.phrase.here.twice_as_many.twice_as_many": (
            "В тази задача Нина има два пъти толкова "
            "топчета, колкото Лео."
        ),
        "story.guide.given.more_then_together": (
            "Знаем, че Лео има {base} топчета, а Нина "
            "има с {extra} повече от Лео. Общият им брой "
            "не е даден — него трябва да намерим."
        ),
        "story.guide.ask.more_then_together": (
            "Търсим колко топчета имат Лео и Нина "
            "заедно, след като използваме, че Нина има "
            "с {extra} повече от Лео."
        ),
        "story.guide.step.identify.more_then_together.base": (
            "Тази стъпка пита колко топчета има Лео. "
            "Прочети условието: Лео има {base} топчета. "
            "Този брой вече е даден."
        ),
        "story.guide.step.forward.more_then_together.nina": (
            "Нина има с {extra} топчета повече от Лео. "
            "Повече означава първо да прибавиш това "
            "число към топчетата на Лео."
        ),
        "story.guide.step.forward.more_then_together.total": (
            "Тази стъпка пита колко топчета имат заедно. "
            "Заедно означава да събереш топчетата на "
            "Лео и на Нина."
        ),
        "story.guide.phrase.here.more_then_together.more_than": (
            "В тази задача Нина има определено число "
            "топчета повече от Лео."
        ),
        "story.guide.phrase.here.more_then_together.in_all": (
            "В тази задача „заедно“ означава топчетата "
            "на Лео и на Нина събрани."
        ),
        "story.guide.given.books_from_class": (
            "Знаем, че има {girls} момичета и с {extra} "
            "повече момчета от момичетата, а книгите са "
            "два пъти толкова, колкото са децата. Броят "
            "на книгите не е даден — него трябва да "
            "намерим."
        ),
        "story.guide.ask.books_from_class": (
            "Търсим колко книги има, като знаем, че "
            "книгите са два пъти толкова, колкото са "
            "децата в класа."
        ),
        "story.guide.step.identify.books_from_class.girls": (
            "Тази стъпка пита колко момичета има в "
            "класа. Прочети условието: има {girls} "
            "момичета. Този брой вече е даден."
        ),
        "story.guide.step.forward.books_from_class.boys": (
            "Момчетата са с {extra} повече от "
            "момичетата. Повече означава да прибавиш "
            "това число към броя на момичетата."
        ),
        "story.guide.step.forward.books_from_class.children": (
            "Тази стъпка пита колко деца има в класа. "
            "Децата са момичетата и момчетата заедно."
        ),
        "story.guide.step.forward.books_from_class.books": (
            "В условието пише, че книгите са два пъти "
            "толкова, колкото са децата. Два пъти "
            "толкова означава умножение по 2, а не с 2 "
            "повече книги."
        ),
        "story.guide.phrase.here.books_from_class.more_than": (
            "В тази задача момчетата са с определено "
            "число повече от момичетата."
        ),
        "story.guide.phrase.here.books_from_class.twice_as_many": (
            "В тази задача книгите са два пъти толкова, "
            "колкото са децата."
        ),
        "story.guide.given.remaining_after_taken": (
            "Знаем, че са извадили {taken} бутилки и са "
            "останали {remaining} бутилки. Първоначалният "
            "брой не е даден — него трябва да намерим."
        ),
        "story.guide.ask.remaining_after_taken": (
            "Търсим колко бутилки е имало в касата в "
            "самото начало, преди да извадят {taken} "
            "бутилки."
        ),
        "story.guide.step.identify.remaining_after_taken.remaining": (
            "Тази стъпка пита колко бутилки са останали. "
            "Прочети условието: останали са {remaining} "
            "бутилки. Този брой вече е даден."
        ),
        "story.guide.step.undo.remaining_after_taken.start": (
            "Първоначално са извадили {taken} бутилки. "
            "За да възстановим началния брой, трябва да "
            "върнем тези {taken} бутилки чрез събиране."
        ),
        "story.guide.phrase.here.remaining_after_taken.remaining": (
            "В тази задача „останали“ са бутилките, "
            "които са останали след изваждането."
        ),
        "story.guide.given.removed_then_doubled": (
            "Знаем, че първо са извадили {taken} "
            "бутилки, после броят на останалите е бил "
            "удвоен и след това е имало {final} бутилки. "
            "Първоначалният брой не е даден — него "
            "трябва да намерим."
        ),
        "story.guide.ask.removed_then_doubled": (
            "Търсим колко бутилки е имало в касата в "
            "самото начало, преди да извадят {taken} "
            "бутилки."
        ),
        "story.guide.step.identify.removed_then_doubled.final": (
            "Тази стъпка пита колко бутилки е имало, "
            "след като останалите били удвоени. Прочети "
            "условието: след това е имало {final} "
            "бутилки. Този брой вече е даден."
        ),
        "story.guide.step.undo.removed_then_doubled.remaining": (
            "Броят на останалите бутилки е бил удвоен, "
            "тоест умножен по 2. За да се върнем назад, "
            "използваме обратното действие — деление "
            "на 2."
        ),
        "story.guide.step.undo.removed_then_doubled.start": (
            "Първоначално са извадили {taken} бутилки. "
            "За да възстановим началния брой, трябва да "
            "върнем тези {taken} бутилки чрез събиране."
        ),
        "story.guide.phrase.here.removed_then_doubled.doubled": (
            "В тази задача е удвоен броят на бутилките, "
            "останали след изваждането."
        ),
        "story.guide.phrase.here.removed_then_doubled.remaining": (
            "В тази задача „останали“ са бутилките след "
            "изваждането, преди броят им да бъде удвоен."
        ),
        "story.guide.given.removed_doubled_then_added": (
            "Знаем, че първо са извадили {taken} "
            "бутилки, после броят на останалите е бил "
            "удвоен, след това са добавили още {added} "
            "бутилки и накрая е имало {final} бутилки. "
            "Първоначалният брой не е даден — него "
            "трябва да намерим."
        ),
        "story.guide.ask.removed_doubled_then_added": (
            "Търсим колко бутилки е имало в касата в "
            "самото начало, преди да извадят {taken} "
            "бутилки."
        ),
        "story.guide.step.identify.removed_doubled_then_added.final": (
            "Първата стъпка пита колко бутилки е имало "
            "накрая. Прочети условието: „Накрая имало "
            "{final} бутилки.“ Този брой вече е даден."
        ),
        "story.guide.step.undo.removed_doubled_then_added.doubled": (
            "В последното действие са добавили {added} "
            "бутилки. За да се върнем една стъпка "
            "назад, трябва да използваме обратното "
            "действие — изваждане. Помисли какво трябва "
            "да извадиш от крайния брой."
        ),
        "story.guide.step.undo.removed_doubled_then_added.remaining": (
            "Броят е бил удвоен, тоест умножен по 2. "
            "За да се върнем назад, използваме обратното "
            "действие — деление на 2."
        ),
        "story.guide.step.undo.removed_doubled_then_added.start": (
            "Първоначално са извадили {taken} бутилки. "
            "За да възстановим началния брой, трябва да "
            "върнем тези {taken} бутилки чрез събиране."
        ),
        "story.guide.phrase.here.removed_doubled_then_added.doubled": (
            "В тази задача е удвоен броят на бутилките, "
            "останали след изваждането."
        ),
        "story.guide.phrase.here.removed_doubled_then_added.remaining": (
            "В тази задача „останали“ са бутилките след "
            "изваждането, преди броят им да бъде удвоен."
        ),
        "story.guide.phrase.doubled.define": (
            "Удвоен означава умножен по 2. Например, "
            "ако имаме {ex_left} бутилки и удвоим броя "
            "им, ще станат {ex_result}."
        ),
        "story.guide.phrase.doubled.simpler_words": (
            "Удвоен означава, че правим количеството "
            "два пъти по-голямо. Представи си, че имаш "
            "две еднакви групи."
        ),
        "story.guide.phrase.doubled.analogy": (
            "Представи си, че имаш една редица от "
            "бутилки и поставиш до нея още една също "
            "толкова дълга редица. Така удвояваш броя им."
        ),
        "story.guide.phrase.doubled.example.apples": (
            "Ако имаме 3 ябълки и удвоим броя им, ще "
            "имаме 6 ябълки. Това е умножение по 2. "
            "Това е отделен пример, не числата от "
            "задачата."
        ),
        "story.guide.phrase.remaining.define": (
            "Останали означава колко още има, след като "
            "част от количеството е махната."
        ),
        "story.guide.phrase.more_than.define": (
            "Повече означава да се прибави определено "
            "число. Например с {ex_extra} повече от "
            "{ex_left} е {ex_result}."
        ),
        "story.guide.phrase.fewer.define": (
            "По-малко означава да се извади определено "
            "число. Например с {ex_extra} по-малко от "
            "{ex_left} е {ex_result}."
        ),
        "story.guide.phrase.twice_as_many.define": (
            "Два пъти толкова означава умножение по 2, "
            "а не с 2 повече. Например, ако Лео има "
            "{ex_left} топчета, два пъти толкова е "
            "{ex_result}."
        ),
        "story.guide.phrase.times_as_many.define": (
            "Пъти толкова означава умножение. Например "
            "{ex_times} пъти толкова, колкото {ex_left}, "
            "е {ex_result}."
        ),
        "story.guide.phrase.in_all.define": (
            "Общо, или заедно, означава да се съберат "
            "групите, за да се намери целият брой."
        ),
        "story.method.setup": (
            "Можеш да запишеш {setup}, без още да "
            "довършваш сметката."
        ),
        "story.method.fallback": (
            "Мога да помогна за тази стъпка, без да кажа "
            "готовото число. Погледни последното действие "
            "в историята и го върни назад. Началният брой "
            "се намира едва след като се върнат всички "
            "действия."
        ),
        "story.hint.understand.identify": (
            "Това число вече е написано в историята. "
            "Трябва даденият брой, не скритият начален "
            "брой."
        ),
        "story.hint.operation.identify": (
            "Препиши даденото число, за което пита "
            "стъпката. Още не работи назад."
        ),
        "story.hint.understand.undo.add": (
            "Накрая са добавили още {other} бутилки. "
            "Търсим броя непосредствено преди добавянето."
        ),
        "story.hint.operation.undo.add": (
            "За да върнем добавянето на {other} бутилки, "
            "използваме обратното действие на събирането "
            "— изваждане."
        ),
        "story.hint.understand.undo.double": (
            "Останалото количество е било удвоено. Трябва "
            "броят точно преди удвояването."
        ),
        "story.hint.operation.undo.double": (
            "Използвай обратната операция на умножение по "
            "2: деление на 2."
        ),
        "story.hint.understand.undo.sub": (
            "В историята са извадени {other}. Трябва броят "
            "точно преди да ги извадят."
        ),
        "story.hint.operation.undo.sub": (
            "Използвай обратната операция на изваждането: "
            "събиране."
        ),
        "story.hint.understand.undo.mul": (
            "В историята има умножение по {other}. Трябва "
            "броят точно преди това умножение."
        ),
        "story.hint.operation.undo.mul": (
            "Използвай обратната операция на умножението: "
            "деление."
        ),
        "story.hint.understand.forward.add": (
            "Историята иска да съберем тези групи."
        ),
        "story.hint.operation.forward.add": (
            "Използвай събиране, за да обединиш групите."
        ),
        "story.hint.understand.forward.sub": (
            "Историята маха едно количество от друго."
        ),
        "story.hint.operation.forward.sub": (
            "Използвай изваждане, за да намериш колко "
            "остават."
        ),
        "story.hint.understand.forward.mul": (
            "Историята прави едно количество няколко пъти "
            "по-голямо от друго."
        ),
        "story.hint.operation.forward.mul": (
            "Използвай умножение."
        ),
        "story.hint.understand.forward.double": (
            "Историята удвоява едно от количествата."
        ),
        "story.hint.operation.forward.double": (
            "Удвояване означава умножение по 2."
        ),
        "story.hint.understand.generic": (
            "Погледни връзката от историята, за която "
            "пита тази стъпка."
        ),
        "story.hint.operation.generic": (
            "Използвай обратната операция на последното "
            "действие или операцията, която историята "
            "назовава за тази стъпка."
        ),
        "story.hint.setup.expression": (
            "Запиши сметката: {setup}"
        ),
        "story.hint.setup.identify": (
            "Използвай даденото число от историята. Още "
            "не работи назад."
        ),
        "story.hint.setup.generic": (
            "Запиши обратната операция на последното "
            "действие. Не прескачай към началния брой."
        ),
        "story.hint.last": (
            "Това е последната подсказка за тази стъпка."
        ),
        "story.hint.exhausted": (
            "Това са всички подсказки за тази стъпка. "
            "Можеш пак да опиташ с отговор."
        ),
        "story.incorrect.identify": (
            "Това не е правилният резултат. Провери "
            "числото, което вече е написано в историята."
        ),
        "story.incorrect.undo": (
            "Това не е правилният резултат. Провери кое е "
            "последното действие в историята и опитай да "
            "го върнеш назад."
        ),
        "story.incorrect.forward": (
            "Това не е правилният резултат. Провери кои "
            "групи историята иска да обединиш."
        ),
    },
}


def sgt(language: str | None, key: str, **params) -> str:
    return tr(STORY_GUIDANCE_TEXT, language, key, **params)


def has_story_guidance_key(language: str | None, key: str) -> bool:
    from src.core.i18n.locale import DEFAULT_LOCALE, normalize_locale

    locale = normalize_locale(language)
    table = STORY_GUIDANCE_TEXT.get(locale) or STORY_GUIDANCE_TEXT[DEFAULT_LOCALE]
    fallback = STORY_GUIDANCE_TEXT[DEFAULT_LOCALE]
    return key in table or key in fallback
