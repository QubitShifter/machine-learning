from enum import Enum


class LinearODEStage(Enum):
    IDENTIFY_STANDARD_FORM = (
        "identify_standard_form"
    )

    IDENTIFY_P_Q = (
        "identify_p_q"
    )

    FIND_INTEGRATING_FACTOR = (
        "find_integrating_factor"
    )

    MULTIPLY_BY_INTEGRATING_FACTOR = (
        "multiply_by_integrating_factor"
    )

    RECOGNIZE_PRODUCT_DERIVATIVE = (
        "recognize_product_derivative"
    )

    INTEGRATE_BOTH_SIDES = (
        "integrate_both_sides"
    )

    SOLVE_FOR_Y = (
        "solve_for_y"
    )

    VERIFY_SOLUTION = (
        "verify_solution"
    )

    COMPLETE = "complete"


class LinearODESolutionSession:
    def __init__(self):
        self.stage = (
            LinearODEStage.IDENTIFY_STANDARD_FORM
        )

        self.attempts_by_stage = {
            stage: 0
            for stage in LinearODEStage
            if stage != LinearODEStage.COMPLETE
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

    def get_attempts_for_current_stage(
        self,
    ):
        return self.attempts_by_stage.get(
            self.stage,
            0,
        )

    def advance(self):
        stages = [
            LinearODEStage.IDENTIFY_STANDARD_FORM,
            LinearODEStage.IDENTIFY_P_Q,
            LinearODEStage.FIND_INTEGRATING_FACTOR,
            LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR,
            LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
            LinearODEStage.INTEGRATE_BOTH_SIDES,
            LinearODEStage.SOLVE_FOR_Y,
            LinearODEStage.VERIFY_SOLUTION,
            LinearODEStage.COMPLETE,
        ]

        current_index = stages.index(
            self.stage
        )

        if current_index < len(stages) - 1:
            self.stage = stages[
                current_index + 1
            ]

    def is_complete(self):
        return (
            self.stage
            == LinearODEStage.COMPLETE
        )

    def get_summary(self):
        return {
            "stage": self.stage.value,
            "attempts_by_stage": {
                stage.value: attempts
                for stage, attempts
                in self.attempts_by_stage.items()
            },
        }