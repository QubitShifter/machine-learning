from src.core.i18n.text import tr


LOGICAL_REASONING_TEXT = {
    "en": {
        "catalog.topic.logical_reasoning": "Logical Reasoning",
        "catalog.topic.logical_reasoning.description": (
            "Solve number clues, quantity relationships "
            "and deduction puzzles."
        ),
        "catalog.skill.grade4_logical_reasoning": (
            "Logical reasoning"
        ),
        "catalog.skill.grade4_logical_reasoning.description": (
            "Solve Grade 4 number clues, quantity "
            "relationships, and deduction puzzles."
        ),
        "gen.logic.number.title": "Number Detective",
        "gen.logic.distribution.title": "Distribution Puzzle",
        "gen.logic.logic.title": "Logic Detective",
        "gen.logic.object.red": "red",
        "gen.logic.object.blue": "blue",
        "gen.logic.object.green": "green",
        "gen.logic.box.box_a": "the first box",
        "gen.logic.box.box_b": "the second box",
        "gen.logic.box.box_c": "the third box",
        "gen.logic.clue.digit_sum": (
            "The sum of the digits is {total}."
        ),
        "gen.logic.clue.digit_diff.tens_greater": (
            "The tens digit is {absolute_amount} greater "
            "than the units digit."
        ),
        "gen.logic.clue.digit_diff.units_greater": (
            "The units digit is {absolute_amount} greater "
            "than the tens digit."
        ),
        "gen.logic.clue.digit_diff.equal": (
            "The tens digit equals the units digit."
        ),
        "gen.logic.clue.digit_order.tens_gt_units": (
            "The tens digit is greater than the units digit."
        ),
        "gen.logic.clue.digit_order.tens_lt_units": (
            "The tens digit is less than the units digit."
        ),
        "gen.logic.clue.digit_order.tens_eq_units": (
            "The tens digit is equal to the units digit."
        ),
        "gen.logic.clue.parity.even": "The number is even.",
        "gen.logic.clue.parity.odd": "The number is odd.",
        "gen.logic.clue.divisible_by": (
            "The number is divisible by {divisor}."
        ),
        "gen.logic.clue.in_interval": (
            "The number is between {low} and {high}."
        ),
        "gen.logic.clue.total.two": (
            "Two boxes contain {total} items in all."
        ),
        "gen.logic.clue.total.three": (
            "Three boxes contain {total} items in all."
        ),
        "gen.logic.clue.times_as_many": (
            "{left_name} contains {factor} times as many "
            "items as {right_name}."
        ),
        "gen.logic.clue.more_than": (
            "{left_name} contains {extra} more items than "
            "{right_name}."
        ),
        "gen.logic.clue.placed_at": (
            "The {item_name} object is in box {position}."
        ),
        "gen.logic.clue.not_placed_at": (
            "The {item_name} object is not in box {position}."
        ),
        "gen.logic.number.ask": "Find the two-digit number.",
        "gen.logic.distribution.ask": (
            "Find how many items are in each box."
        ),
        "gen.logic.logic.ask": (
            "Find the box that contains the {item_name} object."
        ),
        "gen.logic.prompt.units": "What is the units digit?",
        "gen.logic.prompt.tens": "What is the tens digit?",
        "gen.logic.prompt.number": "What is the two-digit number?",
        "gen.logic.prompt.remaining_total": (
            "After the extra amount is removed, how many "
            "items remain to share equally?"
        ),
        "gen.logic.prompt.share_count": (
            "How many equal shares are there?"
        ),
        "gen.logic.prompt.box_quantity": (
            "How many items are in {box_name}?"
        ),
        "gen.logic.prompt.extra_from_scaled": (
            "How much extra does {left_name} contain because "
            "it has {factor_word} times as many items as "
            "{right_name}?"
        ),
        "gen.logic.prompt.extra_total": (
            "How much extra do {left_name} and "
            "{extra_left_name} contain together?"
        ),
        "gen.logic.prompt.infer_position": (
            "Which box must contain the {item_name} object?"
        ),
        "gen.logic.correct.units": (
            "Yes. You found the units digit from the clues."
        ),
        "gen.logic.correct.tens": (
            "Yes. You found the tens digit from the clues."
        ),
        "gen.logic.correct.number": (
            "Yes. Those digits make the secret number."
        ),
        "gen.logic.correct.remaining_total": (
            "Yes. That is the amount left to share equally."
        ),
        "gen.logic.correct.share_count": (
            "Yes. That is how many equal shares there are."
        ),
        "gen.logic.correct.box_quantity": (
            "Yes. That quantity matches the given relationships."
        ),
        "gen.logic.correct.extra_from_scaled": (
            "Yes. The extra amount is scaled by the given factor."
        ),
        "gen.logic.correct.extra_total": (
            "Yes. That is the combined extra amount."
        ),
        "gen.logic.correct.infer_position": (
            "Yes. That placement is forced by the clues."
        ),
        "gen.logic.incorrect.units": (
            "Not yet. Use both digit clues together. "
            "Do not guess the units digit from only one clue."
        ),
        "gen.logic.incorrect.tens": (
            "Not yet. Use the digit relationship with the "
            "other clue. Do not name the tens digit until "
            "it is forced."
        ),
        "gen.logic.incorrect.number": (
            "Not yet. Combine every clue before you name "
            "the two-digit number."
        ),
        "gen.logic.incorrect.remaining_total": (
            "Not yet. Remove the extra quantity from the "
            "given total first."
        ),
        "gen.logic.incorrect.share_count": (
            "Not yet. Count the equal shares from the "
            "given relationships. Do not copy a clue number "
            "unless that count is forced."
        ),
        "gen.logic.incorrect.box_quantity": (
            "Not yet. Rebuild that box from the equal "
            "shares and the given relationship."
        ),
        "gen.logic.incorrect.extra_from_scaled": (
            "Not yet. The extra amount also scales with "
            "the given factor."
        ),
        "gen.logic.incorrect.extra_total": (
            "Not yet. Combine the extra amounts before "
            "you divide."
        ),
        "gen.logic.incorrect.infer_position": (
            "Not yet. Cross out the forbidden boxes for "
            "that object and see which box remains."
        ),
        "gen.logic.hint.units.1": (
            "Use the clue about the relationship between "
            "the digits."
        ),
        "gen.logic.hint.units.2": (
            "Look for two digits with the stated difference "
            "and the stated digit sum."
        ),
        "gen.logic.hint.units.3": (
            "Combine that relationship with the remaining "
            "clue. Do not guess from only one condition."
        ),
        "gen.logic.hint.tens.1": (
            "Use the clue about the relationship between "
            "the digits."
        ),
        "gen.logic.hint.tens.2": (
            "Once one digit is forced, the other digit "
            "follows from the same relationship."
        ),
        "gen.logic.hint.tens.3": (
            "Combine the digit relationship with the "
            "remaining clue. Leave the tens digit unnamed."
        ),
        "gen.logic.hint.number.1": (
            "Use every clue written in the puzzle."
        ),
        "gen.logic.hint.number.2": (
            "Eliminate two-digit numbers that break any "
            "one of the clues."
        ),
        "gen.logic.hint.number.3": (
            "Keep only the numbers that satisfy all clues "
            "at once. Do not name the remaining number yet."
        ),
        "gen.logic.hint.remaining_total.1": (
            "The extra items should not be shared equally."
        ),
        "gen.logic.hint.remaining_total.2": (
            "Remove the extra quantity before dividing "
            "into equal shares."
        ),
        "gen.logic.hint.remaining_total.3": (
            "Set up {setup} without evaluating it."
        ),
        "gen.logic.hint.share_count.1": (
            "Extra items are not extra shares. Use the "
            "relationships between the boxes."
        ),
        "gen.logic.hint.share_count.2": (
            "Count one share for each base box, then add "
            "the given factor for a scaled box."
        ),
        "gen.logic.hint.share_count.3": (
            "Set up {setup} without evaluating it."
        ),
        "gen.logic.hint.box_quantity.1": (
            "Use the relationship that mentions {box_name}."
        ),
        "gen.logic.hint.box_quantity.2": (
            "Rebuild {box_name} from the equal-share value "
            "and the given relationship."
        ),
        "gen.logic.hint.box_quantity.3": (
            "Set up {setup} without evaluating it."
        ),
        "gen.logic.hint.extra_from_scaled.1": (
            "The extra amount also affects {left_name}."
        ),
        "gen.logic.hint.extra_from_scaled.2": (
            "Multiply the extra amount by the given factor."
        ),
        "gen.logic.hint.extra_from_scaled.3": (
            "Set up {setup} without evaluating it."
        ),
        "gen.logic.hint.extra_total.1": (
            "More than one box carries extra."
        ),
        "gen.logic.hint.extra_total.2": (
            "Add the scaled extra to the original extra."
        ),
        "gen.logic.hint.extra_total.3": (
            "Set up {setup} without evaluating it."
        ),
        "gen.logic.hint.infer_position.1": (
            "Look at the clues about the {item_name} object."
        ),
        "gen.logic.hint.infer_position.2": (
            "Eliminate positions that the {item_name} object "
            "cannot occupy."
        ),
        "gen.logic.hint.infer_position.3": (
            "Cross out the forbidden positions and identify "
            "which position remains, without naming it."
        ),
        "gen.logic.hint.last": "This is the last hint for this step.",
        "gen.logic.hint.exhausted": (
            "All the hints for this step have already "
            "been shown."
        ),
        "gen.logic.setup.factor": "the given factor",
        "gen.logic.setup.extra": "the extra amount",
        "gen.logic.setup.total": "the given total",
        "gen.logic.setup.scaled_extra": "the scaled extra",
        "gen.logic.setup.combined_extra": "the combined extra",
        "gen.logic.setup.remaining_total": "the remaining total",
        "gen.logic.setup.share_count": "the share count",
        "gen.logic.setup.that_box": "that box",
        "gen.logic.setup.known_amount": "the known amount",
        "gen.logic.factor_word.2": "two",
        "gen.logic.factor_word.3": "three",
        "gen.logic.method.units": (
            "This step asks for the units digit. Use the "
            "digit-sum and digit-difference clues together. "
            "Do not name the digit until both clues force it."
        ),
        "gen.logic.method.tens": (
            "This step asks for the tens digit. Use the "
            "same digit relationship after the units digit "
            "is known, or combine both clues. Do not name "
            "the tens digit in advance."
        ),
        "gen.logic.method.number": (
            "This step asks for the secret two-digit number. "
            "Keep only the numbers that match every written "
            "clue. Do not guess from a single clue."
        ),
        "gen.logic.method.remaining_total": (
            "Remove the extra quantity from the given total "
            "before you divide. You may write "
            "{total} - {extra} = ? without evaluating it."
        ),
        "gen.logic.method.share_count": (
            "Count the equal shares created by the given "
            "relationships. Do not copy a clue number unless "
            "that count is forced."
        ),
        "gen.logic.method.box_quantity": (
            "Rebuild {box_name} from the equal-share value "
            "and the relationship in the clues. Use only "
            "quantities already found."
        ),
        "gen.logic.method.extra_from_scaled": (
            "Use both box clues. {extra_left_name_cap} has "
            "{extra} more items than {extra_right_name}. "
            "{left_name_cap} contains {factor_word} times "
            "as many as {right_name}, so that extra is also "
            "multiplied by {factor}. Write {factor} × "
            "{extra} = ? without evaluating it."
        ),
        "gen.logic.method.extra_total": (
            "Add the extra amounts together before you "
            "remove them from the total."
        ),
        "gen.logic.method.infer_position": (
            "Use the clues about the {item_name} object and "
            "the rule that each box holds one object. Cross "
            "out impossible boxes. Do not name the remaining "
            "box until you are asked."
        ),
        "gen.logic.method.fallback": (
            "Use only the written clues and the quantities "
            "you have already found. Do not invent extra "
            "clues, and do not name the current answer."
        ),
        "gen.logic.guide.known": (
            "The given facts are the written clues. Use "
            "only those clues and the puzzle rules."
        ),
        "gen.logic.guide.known.distribution": (
            "The given facts are: {clue_list} Use only "
            "those facts."
        ),
        "gen.logic.guide.unknown": (
            "This step asks for one whole number that is "
            "forced by the clues you already have."
        ),
        "gen.logic.guide.unknown.distribution": (
            "This step asks: {current_prompt} Find only "
            "that quantity now. Do not name later box "
            "totals yet."
        ),
        "gen.logic.guide.first_clue": (
            "Start with the first clue in the statement, "
            "then combine it with the next clue only when "
            "you need it."
        ),
        "gen.logic.guide.first_clue.distribution": (
            "Start with the relationship that {left_name} "
            "contains {factor_word} times as many items as "
            "{right_name}. That relationship is useful "
            "before any box total is found."
        ),
        "gen.logic.guide.first_clue.distribution.extra_from_scaled": (
            "Use the clue that {left_name} contains "
            "{factor_word} times as many items as "
            "{right_name}. The same multiplier applies to "
            "the extra amount."
        ),
        "gen.logic.guide.first_clue.distribution.extra_total": (
            "Both {left_name} and {extra_left_name} carry "
            "extra. Add those extra amounts before you "
            "share the rest."
        ),
        "gen.logic.guide.first_clue.distribution.remaining_total": (
            "Use the given total together with the extra "
            "amounts. Remove the extras first so the "
            "remaining items can be shared equally."
        ),
        "gen.logic.guide.first_clue.distribution.share_count": (
            "Count one share for each box, then add the "
            "extra shares from the clue that {left_name} "
            "contains {factor_word} times as many items as "
            "{right_name}."
        ),
        "gen.logic.guide.first_clue.distribution.box_quantity": (
            "Use the relationship that mentions {box_name}. "
            "Rebuild that box from quantities you have "
            "already found."
        ),
        "gen.logic.guide.eliminate": (
            "Cross out possibilities that break a clue. "
            "A possibility is gone as soon as it disagrees "
            "with any one written clue."
        ),
        "gen.logic.guide.check": (
            "After you have a candidate, check that it "
            "satisfies every written clue. Do not skip a clue."
        ),
        "gen.logic.guide.check.distribution": (
            "Check that you used only the given total and "
            "the written relationships. Do not name later "
            "box totals yet."
        ),
        "gen.logic.guide.check.distribution.extra_from_scaled": (
            "Check that you used the given extra amount "
            "and the given multiplier. Do not find the "
            "final box quantities yet."
        ),
        "gen.logic.guide.check.distribution.extra_total": (
            "Check that you added both extra amounts from "
            "the clues. Do not share the remaining items yet."
        ),
        "gen.logic.guide.check.distribution.remaining_total": (
            "Check that you removed the extras from the "
            "given total. Do not divide into shares yet."
        ),
        "gen.logic.guide.check.distribution.share_count": (
            "Check that you counted one share per box, "
            "including the extra shares from the multiplier. "
            "Do not find a box total yet."
        ),
        "gen.logic.guide.check.distribution.box_quantity": (
            "Check that {box_name} matches the given "
            "relationship with quantities you have already "
            "found. Do not name later boxes yet."
        ),
        "gen.logic.term.scaled": (
            "The scaled box is {left_name}. It contains "
            "{factor_word} times as many items as "
            "{right_name}. The multiplier also applies to "
            "the extra amount. Use that relationship to "
            "work out the extra without finding the final "
            "quantities yet."
        ),
        "gen.logic.term.scaled.none": (
            "This puzzle does not multiply one box by a "
            "factor. Use the written clues."
        ),
        "gen.logic.guide.no_eliminate": (
            "This puzzle is about sharing quantities, not "
            "about crossing out boxes. Use the given total "
            "and the relationships between the boxes."
        ),
        "gen.logic.input.one_number": (
            "Enter one number for the current step. "
            "The tutor will guide you through the remaining steps."
        ),
        "gen.logic.input.one_number.distribution": (
            "Enter one number for the current step. "
            "You don't need to enter both box quantities together. "
            "After you answer this step correctly, the tutor will "
            "ask for the remaining quantities."
        ),
    },
    "bg": {
        "catalog.topic.logical_reasoning": "Логическо мислене",
        "catalog.topic.logical_reasoning.description": (
            "Решавайте задачи с числови улики, връзки "
            "между количества и логически изводи."
        ),
        "catalog.skill.grade4_logical_reasoning": (
            "Логическо мислене"
        ),
        "catalog.skill.grade4_logical_reasoning.description": (
            "Решавайте числови улики, връзки между "
            "количества и логически пъзели за 4. клас."
        ),
        "gen.logic.number.title": "Числов детектив",
        "gen.logic.distribution.title": "Задача за разпределение",
        "gen.logic.logic.title": "Логически детектив",
        "gen.logic.object.red": "червеният",
        "gen.logic.object.blue": "синият",
        "gen.logic.object.green": "зеленият",
        "gen.logic.box.box_a": "първата кутия",
        "gen.logic.box.box_b": "втората кутия",
        "gen.logic.box.box_c": "третата кутия",
        "gen.logic.clue.digit_sum": (
            "Сборът на цифрите е {total}."
        ),
        "gen.logic.clue.digit_diff.tens_greater": (
            "Цифрата на десетиците е с {absolute_amount} "
            "по-голяма от цифрата на единиците."
        ),
        "gen.logic.clue.digit_diff.units_greater": (
            "Цифрата на единиците е с {absolute_amount} "
            "по-голяма от цифрата на десетиците."
        ),
        "gen.logic.clue.digit_diff.equal": (
            "Цифрата на десетиците е равна на цифрата "
            "на единиците."
        ),
        "gen.logic.clue.digit_order.tens_gt_units": (
            "Цифрата на десетиците е по-голяма от цифрата "
            "на единиците."
        ),
        "gen.logic.clue.digit_order.tens_lt_units": (
            "Цифрата на десетиците е по-малка от цифрата "
            "на единиците."
        ),
        "gen.logic.clue.digit_order.tens_eq_units": (
            "Цифрата на десетиците е равна на цифрата "
            "на единиците."
        ),
        "gen.logic.clue.parity.even": "Числото е четно.",
        "gen.logic.clue.parity.odd": "Числото е нечетно.",
        "gen.logic.clue.divisible_by": (
            "Числото се дели на {divisor}."
        ),
        "gen.logic.clue.in_interval": (
            "Числото е между {low} и {high}."
        ),
        "gen.logic.clue.total.two": (
            "В две кутии има общо {total} предмета."
        ),
        "gen.logic.clue.total.three": (
            "В три кутии има общо {total} предмета."
        ),
        "gen.logic.clue.times_as_many": (
            "В {left_name} има {factor} пъти повече "
            "предмети, отколкото в {right_name}."
        ),
        "gen.logic.clue.more_than": (
            "В {left_name} има с {extra} предмета повече, "
            "отколкото в {right_name}."
        ),
        "gen.logic.clue.placed_at": (
            "{item_name} предмет е в кутия {position}."
        ),
        "gen.logic.clue.not_placed_at": (
            "{item_name} предмет не е в кутия {position}."
        ),
        "gen.logic.number.ask": "Намерете двуцифреното число.",
        "gen.logic.distribution.ask": (
            "Намерете колко предмета има във всяка кутия."
        ),
        "gen.logic.logic.ask": (
            "Намерете кутията, в която е {item_name} предмет."
        ),
        "gen.logic.prompt.units": (
            "Коя е цифрата на единиците?"
        ),
        "gen.logic.prompt.tens": (
            "Коя е цифрата на десетиците?"
        ),
        "gen.logic.prompt.number": "Кое е двуцифреното число?",
        "gen.logic.prompt.remaining_total": (
            "След като се махне излишъкът, колко предмета "
            "остават за равно дялове?"
        ),
        "gen.logic.prompt.share_count": (
            "Колко равни дяла има?"
        ),
        "gen.logic.prompt.box_quantity": (
            "Колко предмета има в {box_name}?"
        ),
        "gen.logic.prompt.extra_from_scaled": (
            "В {extra_left_name} има {extra} допълнителни "
            "предмета. Колко допълнителни предмета се "
            "получават в {left_name}, когато умножим този "
            "брой по {factor}?"
        ),
        "gen.logic.prompt.extra_total": (
            "Колко е излишъкът в {left_name} и "
            "{extra_left_name} заедно?"
        ),
        "gen.logic.prompt.infer_position": (
            "В коя кутия трябва да е {item_name} предмет?"
        ),
        "gen.logic.correct.units": (
            "Да. Намерихте цифрата на единиците от уликите."
        ),
        "gen.logic.correct.tens": (
            "Да. Намерихте цифрата на десетиците от уликите."
        ),
        "gen.logic.correct.number": (
            "Да. Тези цифри образуват тайното число."
        ),
        "gen.logic.correct.remaining_total": (
            "Да. Това е количеството, което остава за "
            "равно разпределяне."
        ),
        "gen.logic.correct.share_count": (
            "Да. Толкова са равните дялове."
        ),
        "gen.logic.correct.box_quantity": (
            "Да. Това количество отговаря на дадените връзки."
        ),
        "gen.logic.correct.extra_from_scaled": (
            "Да. Излишъкът се умножава по дадения множител."
        ),
        "gen.logic.correct.extra_total": (
            "Да. Това е общият излишък."
        ),
        "gen.logic.correct.infer_position": (
            "Да. Това място се налага от уликите."
        ),
        "gen.logic.incorrect.units": (
            "Още не. Използвайте двете улики за цифрите "
            "заедно. Не отгатвайте цифрата на единиците "
            "само от една улика."
        ),
        "gen.logic.incorrect.tens": (
            "Още не. Използвайте връзката между цифрите "
            "заедно с другата улика. Не казвайте цифрата "
            "на десетиците, преди да е наложена."
        ),
        "gen.logic.incorrect.number": (
            "Още не. Комбинирайте всички улики, преди да "
            "назовете двуцифреното число."
        ),
        "gen.logic.incorrect.remaining_total": (
            "Още не. Първо махнете излишъка от дадения сбор."
        ),
        "gen.logic.incorrect.share_count": (
            "Още не. Пребройте равните дялове от дадените "
            "връзки. Не преписвайте число от улика, ако "
            "броят не е наложителен."
        ),
        "gen.logic.incorrect.box_quantity": (
            "Още не. Възстановете тази кутия от равния дял "
            "и дадената връзка."
        ),
        "gen.logic.incorrect.extra_from_scaled": (
            "Още не. Излишъкът също се умножава по дадения "
            "множител."
        ),
        "gen.logic.incorrect.extra_total": (
            "Още не. Съберете излишъците, преди да делите."
        ),
        "gen.logic.incorrect.infer_position": (
            "Още не. Задраскайте забранените кутии за този "
            "предмет и вижте коя кутия остава."
        ),
        "gen.logic.hint.units.1": (
            "Използвайте уликата за връзката между цифрите."
        ),
        "gen.logic.hint.units.2": (
            "Търсете две цифри с дадената разлика и дадения "
            "сбор на цифрите."
        ),
        "gen.logic.hint.units.3": (
            "Комбинирайте тази връзка с останалата улика. "
            "Не отгатвайте само от едно условие."
        ),
        "gen.logic.hint.tens.1": (
            "Използвайте уликата за връзката между цифрите."
        ),
        "gen.logic.hint.tens.2": (
            "Когато едната цифра е наложена, другата следва "
            "от същата връзка."
        ),
        "gen.logic.hint.tens.3": (
            "Комбинирайте връзката между цифрите с "
            "останалата улика. Не назовавайте цифрата "
            "на десетиците."
        ),
        "gen.logic.hint.number.1": (
            "Използвайте всяка улика, написана в задачата."
        ),
        "gen.logic.hint.number.2": (
            "Изключете двуцифрените числа, които нарушават "
            "която и да е улика."
        ),
        "gen.logic.hint.number.3": (
            "Запазете само числата, които изпълняват всички "
            "улики заедно. Все още не назовавайте останалото "
            "число."
        ),
        "gen.logic.hint.remaining_total.1": (
            "Излишъкът не се дели поравно."
        ),
        "gen.logic.hint.remaining_total.2": (
            "Махнете излишъка, преди да делите на равни дялове."
        ),
        "gen.logic.hint.remaining_total.3": (
            "Запишете {setup}, без да пресмятате."
        ),
        "gen.logic.hint.share_count.1": (
            "Излишъкът не е допълнителен дял. Използвайте "
            "връзките между кутиите."
        ),
        "gen.logic.hint.share_count.2": (
            "Пребройте по един дял за всяка основна кутия, "
            "после добавете дадения множител за кутията с "
            "умножение."
        ),
        "gen.logic.hint.share_count.3": (
            "Запишете {setup}, без да пресмятате."
        ),
        "gen.logic.hint.box_quantity.1": (
            "Използвайте връзката, която споменава {box_name}."
        ),
        "gen.logic.hint.box_quantity.2": (
            "Възстановете {box_name} от равния дял и дадената "
            "връзка."
        ),
        "gen.logic.hint.box_quantity.3": (
            "Запишете {setup}, без да пресмятате."
        ),
        "gen.logic.hint.extra_from_scaled.1": (
            "Допълнителните предмета засягат и {left_name}."
        ),
        "gen.logic.hint.extra_from_scaled.2": (
            "Умножете допълнителните предмета по {factor}."
        ),
        "gen.logic.hint.extra_from_scaled.3": (
            "Запишете {setup}, без да пресмятате."
        ),
        "gen.logic.hint.extra_total.1": (
            "Излишък има в повече от една кутия."
        ),
        "gen.logic.hint.extra_total.2": (
            "Съберете допълнителните предмета от двете кутии."
        ),
        "gen.logic.hint.extra_total.3": (
            "Запишете {setup}, без да пресмятате."
        ),
        "gen.logic.hint.infer_position.1": (
            "Погледнете уликите за {item_name} предмет."
        ),
        "gen.logic.hint.infer_position.2": (
            "Изключете местата, които {item_name} предмет "
            "не може да заема."
        ),
        "gen.logic.hint.infer_position.3": (
            "Задраскайте забранените места и вижте кое "
            "остава, без да го назовавате."
        ),
        "gen.logic.hint.last": "Това е последният подсказ за тази стъпка.",
        "gen.logic.hint.exhausted": (
            "Всички подсказки за тази стъпка вече са показани."
        ),
        "gen.logic.setup.factor": "дадения множител",
        "gen.logic.setup.extra": "излишъка",
        "gen.logic.setup.total": "дадения сбор",
        "gen.logic.setup.scaled_extra": "пренесения излишък",
        "gen.logic.setup.combined_extra": "сборния излишък",
        "gen.logic.setup.remaining_total": "останалия сбор",
        "gen.logic.setup.share_count": "броя дялове",
        "gen.logic.setup.that_box": "тази кутия",
        "gen.logic.setup.known_amount": "вече намереното количество",
        "gen.logic.factor_word.2": "два",
        "gen.logic.factor_word.3": "три",
        "gen.logic.method.units": (
            "Тази стъпка иска цифрата на единиците. Използвайте "
            "уликите за сбор и разлика на цифрите заедно. Не "
            "назовавайте цифрата, преди двете улики да я наложат."
        ),
        "gen.logic.method.tens": (
            "Тази стъпка иска цифрата на десетиците. Използвайте "
            "същата връзка след цифрата на единиците или "
            "комбинирайте двете улики. Не назовавайте цифрата "
            "предварително."
        ),
        "gen.logic.method.number": (
            "Тази стъпка иска тайното двуцифрено число. "
            "Запазете само числата, които отговарят на всяка "
            "написана улика. Не отгатвайте само от една улика."
        ),
        "gen.logic.method.remaining_total": (
            "Махнете излишъка от дадения сбор, преди да "
            "делите. Може да запишете {total} - {extra} = ? "
            "без да пресмятате."
        ),
        "gen.logic.method.share_count": (
            "Пребройте равните дялове от дадените връзки. "
            "Не преписвайте число от улика, ако броят не "
            "е наложителен."
        ),
        "gen.logic.method.box_quantity": (
            "Възстановете {box_name} от равния дял и връзката "
            "в уликите. Използвайте само вече намерени количества."
        ),
        "gen.logic.method.extra_from_scaled": (
            "Използвайте двете условия за кутиите. "
            "В {extra_left_name} има {extra} предмета повече, "
            "отколкото в {extra_right_name}. {left_name_cap} "
            "има {factor_word} пъти повече предмети, "
            "отколкото в {right_name}, затова тези "
            "допълнителни предмета също се умножават по "
            "{factor}. Запишете {factor} × {extra} = ?, "
            "без да пресмятате резултата."
        ),
        "gen.logic.method.extra_total": (
            "Съберете излишъците, преди да ги махнете от сбора."
        ),
        "gen.logic.method.infer_position": (
            "Използвайте уликите за {item_name} предмет и "
            "правилото, че във всяка кутия има по един предмет. "
            "Задраскайте невъзможните кутии. Не назовавайте "
            "останалата кутия, докато не бъдете попитани."
        ),
        "gen.logic.method.fallback": (
            "Използвайте само написаните улики и вече "
            "намерените количества. Не измисляйте нови "
            "улики и не назовавайте текущия отговор."
        ),
        "gen.logic.guide.known": (
            "Дадени са написаните улики. Използвайте само "
            "тях и правилата на задачата."
        ),
        "gen.logic.guide.known.distribution": (
            "Дадени са: {clue_list} Използвайте само тези факти."
        ),
        "gen.logic.guide.unknown": (
            "Тази стъпка иска едно цяло число, което се "
            "налага от вече дадените улики."
        ),
        "gen.logic.guide.unknown.distribution": (
            "Тази стъпка пита: {current_prompt} Намерете "
            "само това количество сега. Не назовавайте "
            "късните количества в кутиите."
        ),
        "gen.logic.guide.first_clue": (
            "Започнете с първата улика в условието. "
            "Добавете следващата само когато е нужна."
        ),
        "gen.logic.guide.first_clue.distribution": (
            "Започнете с връзката, че в {left_name} има "
            "{factor_word} пъти повече предмети, отколкото "
            "в {right_name}. Тази връзка е полезна преди "
            "да се намерят количествата в кутиите."
        ),
        "gen.logic.guide.first_clue.distribution.extra_from_scaled": (
            "Използвайте условието, че в {left_name} има "
            "{factor_word} пъти повече предмети, отколкото "
            "в {right_name}. Умножението по {factor} важи "
            "и за допълнителните предмета."
        ),
        "gen.logic.guide.first_clue.distribution.extra_total": (
            "И {left_name}, и {extra_left_name} носят "
            "излишък. Съберете тези излишъци, преди да "
            "делите останалото."
        ),
        "gen.logic.guide.first_clue.distribution.remaining_total": (
            "Използвайте дадения сбор заедно с излишъците. "
            "Махнете излишъците първо, за да останат "
            "предметите за равно дялове."
        ),
        "gen.logic.guide.first_clue.distribution.share_count": (
            "Пребройте по един дял за всяка кутия, после "
            "добавете дяловете от условието, че в "
            "{left_name} има {factor_word} пъти повече "
            "предмети, отколкото в {right_name}."
        ),
        "gen.logic.guide.first_clue.distribution.box_quantity": (
            "Използвайте връзката, която споменава "
            "{box_name}. Възстановете тази кутия от вече "
            "намерените количества."
        ),
        "gen.logic.guide.eliminate": (
            "Задраскайте вариантите, които нарушават улика. "
            "Вариантът отпада веднага щом противоречи на "
            "която и да е написана улика."
        ),
        "gen.logic.guide.check": (
            "След като имате кандидат, проверете, че "
            "изпълнява всяка написана улика. Не пропускайте "
            "улика."
        ),
        "gen.logic.guide.check.distribution": (
            "Проверете, че сте използвали само дадения "
            "сбор и написаните връзки. Не назовавайте "
            "късните количества в кутиите."
        ),
        "gen.logic.guide.check.distribution.extra_from_scaled": (
            "Проверете, че сте използвали дадения излишък "
            "и дадения множител. Не търсете крайните "
            "количества в кутиите още."
        ),
        "gen.logic.guide.check.distribution.extra_total": (
            "Проверете, че сте събрали двата броя "
            "допълнителни предмета от условията. Не делете "
            "останалото още."
        ),
        "gen.logic.guide.check.distribution.remaining_total": (
            "Проверете, че сте махнали излишъците от "
            "дадения сбор. Не делете на дялове още."
        ),
        "gen.logic.guide.check.distribution.share_count": (
            "Проверете, че сте преброили по един дял за "
            "всяка кутия, включително допълнителните дялове "
            "от множителя. Не търсете количество в кутия още."
        ),
        "gen.logic.guide.check.distribution.box_quantity": (
            "Проверете, че {box_name} отговаря на дадената "
            "връзка с вече намерените количества. Не "
            "назовавайте следващите кутии още."
        ),
        "gen.logic.term.scaled": (
            "Умножената кутия е {left_name}. В нея има "
            "{factor_word} пъти повече предмети, отколкото "
            "в {right_name}. Същият множител важи и за "
            "излишъка. Използвайте тази връзка, за да "
            "намерите излишъка, без още да търсите крайните "
            "количества."
        ),
        "gen.logic.term.scaled.none": (
            "В тази задача никоя кутия не се умножава по "
            "множител. Използвайте написаните улики."
        ),
        "gen.logic.guide.no_eliminate": (
            "Тази задача е за разпределение на количества, "
            "не за задраскване на кутии. Използвайте дадения "
            "сбор и връзките между кутиите."
        ),
        "gen.logic.input.one_number": (
            "Въведи едно число за текущата стъпка. "
            "Ще преминеш към следващите стъпки след правилен отговор."
        ),
        "gen.logic.input.one_number.distribution": (
            "Въведи едно число за текущата стъпка. Не е необходимо "
            "да въвеждаш количествата в двете кутии едновременно. "
            "След като отговориш правилно, ще преминеш към "
            "следващите стъпки."
        ),
    },
}


def lrt(language: str | None, key: str, **params) -> str:
    return tr(LOGICAL_REASONING_TEXT, language, key, **params)
