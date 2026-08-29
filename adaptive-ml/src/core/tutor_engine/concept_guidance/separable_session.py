from enum import Enum


class SeparableStage(Enum):
    SEPARATE_VARIABLES = "separate_variables"
    INTEGRATE_BOTH_SIDES = "integrate_both_sides"
    SOLVE_LOG_EQUATION = "solve_log_equation"
    FINAL_SOLUTION = "final_solution"
    COMPLETE = "complete"


class SeparableSolutionSession:
    def __init__(self):
        self.stage = SeparableStage.SEPARATE_VARIABLES
        self.attempts_by_stage = {
            SeparableStage.SEPARATE_VARIABLES: 0,
            SeparableStage.INTEGRATE_BOTH_SIDES: 0,
            SeparableStage.SOLVE_LOG_EQUATION: 0,
            SeparableStage.FINAL_SOLUTION: 0,
        }

    def get_stage(self) -> SeparableStage:
        return self.stage

    def get_stage_name(self) -> str:
        return self.stage.value

    def record_attempt(self) -> None:
        if self.stage in self.attempts_by_stage:
            self.attempts_by_stage[self.stage] += 1

    def get_attempts_for_current_stage(self) -> int:
        return self.attempts_by_stage.get(
            self.stage,
            0,
        )

    def advance(self) -> None:
        if self.stage == SeparableStage.SEPARATE_VARIABLES:
            self.stage = SeparableStage.INTEGRATE_BOTH_SIDES

        elif self.stage == SeparableStage.INTEGRATE_BOTH_SIDES:
            self.stage = SeparableStage.SOLVE_LOG_EQUATION

        elif self.stage == SeparableStage.SOLVE_LOG_EQUATION:
            self.stage = SeparableStage.FINAL_SOLUTION

        elif self.stage == SeparableStage.FINAL_SOLUTION:
            self.stage = SeparableStage.COMPLETE

    def is_complete(self) -> bool:
        return self.stage == SeparableStage.COMPLETE

    def get_prompt(self) -> str:
        if self.stage == SeparableStage.SEPARATE_VARIABLES:
            return (
                "First, separate the variables. "
                "Write a form where the y terms are on one side "
                "and the x terms are on the other."
            )

        if self.stage == SeparableStage.INTEGRATE_BOTH_SIDES:
            return (
                "Now integrate both sides. "
                "Write what you get after performing the two integrals."
            )

        if self.stage == SeparableStage.SOLVE_LOG_EQUATION:
            return (
                "Now solve the logarithmic equation for y. "
                "Think about which operation reverses ln."
            )

        if self.stage == SeparableStage.FINAL_SOLUTION:
            return (
                "Write the final general solution for y, "
                "including the arbitrary constant C."
            )

        return "This solution is complete."

    def get_summary(self) -> dict:
        return {
            "stage": self.stage.value,
            "attempts": {
                stage.value: attempts
                for stage, attempts in self.attempts_by_stage.items()
            },
        }