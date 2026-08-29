class SkillSession:
    def __init__(
        self,
        skill_id: str,
        min_questions: int = 5,
        mastery_threshold: float = 0.90,
        required_first_attempt_streak: int = 3,
    ):
        self.skill_id = skill_id
        self.min_questions = min_questions
        self.mastery_threshold = mastery_threshold
        self.required_first_attempt_streak = required_first_attempt_streak

        self.questions_completed = 0
        self.total_attempts = 0
        self.first_attempt_correct_streak = 0

    def record_question(
        self,
        attempts: int,
        correct: bool,
    ) -> None:
        self.questions_completed += 1
        self.total_attempts += attempts

        if correct and attempts == 1:
            self.first_attempt_correct_streak += 1
        else:
            self.first_attempt_correct_streak = 0

    def is_mastered(
        self,
        mastery: float,
    ) -> bool:
        return (
            mastery >= self.mastery_threshold
            and self.questions_completed >= self.min_questions
            and self.first_attempt_correct_streak
            >= self.required_first_attempt_streak
        )

    def get_summary(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "questions_completed": self.questions_completed,
            "total_attempts": self.total_attempts,
            "first_attempt_correct_streak": (
                self.first_attempt_correct_streak
            ),
        }