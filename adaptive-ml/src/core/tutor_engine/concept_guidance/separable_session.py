from enum import Enum


class SeparableStage(Enum):
    SEPARATE_VARIABLES = "separate_variables"
    INTEGRATE_BOTH_SIDES = "integrate_both_sides"
    SOLVE_LOG_EQUATION = "solve_log_equation"
    FINAL_SOLUTION = "final_solution"
    COMPLETE = "complete"


class LogSolveStage(Enum):
    APPLY_EXP = "apply_exp"
    CANCEL_LOG = "cancel_log"
    SPLIT_EXPONENTIAL = "split_exponential"
    RENAME_EXP_CONSTANT = "rename_exp_constant"
    REMOVE_ABSOLUTE_VALUE = "remove_absolute_value"
    ABSORB_CONSTANT = "absorb_constant"
    COMPLETE = "complete"


class SeparableSolutionSession:
    def __init__(self):
        self.stage = (
            SeparableStage.SEPARATE_VARIABLES
        )

        self.log_stage = (
            LogSolveStage.APPLY_EXP
        )

        self.attempts_by_stage = {
            SeparableStage.SEPARATE_VARIABLES: 0,
            SeparableStage.INTEGRATE_BOTH_SIDES: 0,
            SeparableStage.SOLVE_LOG_EQUATION: 0,
            SeparableStage.FINAL_SOLUTION: 0,
        }

    def get_stage(self):
        return self.stage

    def get_stage_name(self):
        return self.stage.value

    def record_attempt(self):
        if self.stage in self.attempts_by_stage:
            self.attempts_by_stage[
                self.stage
            ] += 1

    def get_attempts_for_current_stage(self):
        return self.attempts_by_stage.get(
            self.stage,
            0,
        )

    def advance(self):
        if (
            self.stage
            == SeparableStage.SEPARATE_VARIABLES
        ):
            self.stage = (
                SeparableStage.INTEGRATE_BOTH_SIDES
            )

        elif (
            self.stage
            == SeparableStage.INTEGRATE_BOTH_SIDES
        ):
            self.stage = (
                SeparableStage.SOLVE_LOG_EQUATION
            )

        elif (
            self.stage
            == SeparableStage.SOLVE_LOG_EQUATION
        ):
            self.stage = (
                SeparableStage.FINAL_SOLUTION
            )

        elif (
            self.stage
            == SeparableStage.FINAL_SOLUTION
        ):
            self.stage = (
                SeparableStage.COMPLETE
            )

    def is_complete(self):
        return (
            self.stage
            == SeparableStage.COMPLETE
        )

    def get_log_stage(self):
        return self.log_stage

    def advance_log_stage(self):
        if (
            self.log_stage
            == LogSolveStage.APPLY_EXP
        ):
            self.log_stage = (
                LogSolveStage.CANCEL_LOG
            )

        elif (
            self.log_stage
            == LogSolveStage.CANCEL_LOG
        ):
            self.log_stage = (
                LogSolveStage.SPLIT_EXPONENTIAL
            )

        elif (
            self.log_stage
            == LogSolveStage.SPLIT_EXPONENTIAL
        ):
            self.log_stage = (
                LogSolveStage.RENAME_EXP_CONSTANT
            )

        elif (
            self.log_stage
            == LogSolveStage.RENAME_EXP_CONSTANT
        ):
            self.log_stage = (
                LogSolveStage.REMOVE_ABSOLUTE_VALUE
            )

        elif (
            self.log_stage
            == LogSolveStage.REMOVE_ABSOLUTE_VALUE
        ):
            self.log_stage = (
                LogSolveStage.ABSORB_CONSTANT
            )

        elif (
            self.log_stage
            == LogSolveStage.ABSORB_CONSTANT
        ):
            self.log_stage = (
                LogSolveStage.COMPLETE
            )

    def advance_log_stage_by(
        self,
        steps: int,
    ):
        for _ in range(steps):
            if (
                self.log_stage
                == LogSolveStage.COMPLETE
            ):
                break

            self.advance_log_stage()

    def is_log_stage_complete(self):
        return (
            self.log_stage
            == LogSolveStage.COMPLETE
        )

    def get_prompt(self):
        if (
            self.stage
            == SeparableStage.SEPARATE_VARIABLES
        ):
            return (
                "First, separate the variables so that "
                "the y terms are on one side and the x terms "
                "are on the other."
            )

        if (
            self.stage
            == SeparableStage.INTEGRATE_BOTH_SIDES
        ):
            return (
                "Now integrate both sides of the "
                "separated equation."
            )

        if (
            self.stage
            == SeparableStage.SOLVE_LOG_EQUATION
        ):
            return (
                "Now solve the logarithmic equation for y. "
                "Think about which operation reverses ln."
            )

        if (
            self.stage
            == SeparableStage.FINAL_SOLUTION
        ):
            return (
                "Now verify the general solution "
                "against the original differential equation."
            )

        return "The solution is complete."

    def get_summary(self):
        return {
            "stage": self.stage.value,
            "log_stage": self.log_stage.value,
            "attempts_by_stage": {
                stage.value: attempts
                for stage, attempts
                in self.attempts_by_stage.items()
            },
        }