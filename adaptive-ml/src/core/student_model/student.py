class StudentModel:
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.mastery = {}

    def initialize_skill(
        self,
        skill_id: str,
        initial_mastery: float = 0.5
    ) -> None:
        if skill_id not in self.mastery:
            self.mastery[skill_id] = initial_mastery

    def get_mastery(
        self,
        skill_id: str
    ) -> float:
        return self.mastery.get(
            skill_id,
            0.5
        )

    def update_mastery_after_question(
        self,
        skill_id: str,
        attempts: int,
        final_evaluation: dict
    ) -> float:
        current = self.get_mastery(
            skill_id
        )

        # Completely unparsable / abandoned type result.
        if final_evaluation.get(
            "parse_error",
            False
        ):
            change = 0.0

        # Fully correct solution.
        elif final_evaluation.get(
            "correct",
            False
        ):
            if attempts == 1:
                change = 0.10

            elif attempts == 2:
                change = 0.06

            else:
                change = 0.03

        # Main mathematics is correct,
        # but something minor is missing,
        # such as the integration constant.
        elif final_evaluation.get(
            "core_correct",
            False
        ):
            change = 0.02

        # Student did not solve the question.
        else:
            change = -0.08

        updated = current + change

        # Keep mastery between 0 and 1.
        updated = max(
            0.0,
            min(
                1.0,
                updated
            )
        )

        self.mastery[skill_id] = updated

        return updated