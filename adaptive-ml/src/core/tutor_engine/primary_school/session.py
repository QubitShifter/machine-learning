from dataclasses import dataclass, field

from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
    SolutionStep,
)


@dataclass
class PrimarySchoolSession:
    """
    Track progress through one primary-school problem.
    """

    problem: PrimarySchoolProblem

    current_step_index: int = 0

    attempts_by_step: dict[int, int] = field(
        default_factory=dict
    )

    hints_used_by_step: dict[int, int] = field(
        default_factory=dict
    )

    math_errors_by_step: dict[int, int] = field(
        default_factory=dict
    )

    completed: bool = False


    def get_current_step(
        self,
    ) -> SolutionStep | None:
        """
        Return the current tutoring step.
        """

        if self.completed:
            return None

        if (
            self.current_step_index
            >= len(self.problem.solution_steps)
        ):
            return None

        return self.problem.solution_steps[
            self.current_step_index
        ]


    def record_attempt(
        self,
    ) -> None:
        """
        Record one mathematical attempt for the
        current step.
        """

        step = self.get_current_step()

        if step is None:
            return

        step_number = step.step_number

        current_count = self.attempts_by_step.get(
            step_number,
            0,
        )

        self.attempts_by_step[
            step_number
        ] = current_count + 1


    def record_hint(
        self,
    ) -> None:
        """
        Record that the student requested or received
        a hint for the current step.
        """

        step = self.get_current_step()

        if step is None:
            return

        step_number = step.step_number

        current_count = self.hints_used_by_step.get(
            step_number,
            0,
        )

        self.hints_used_by_step[
            step_number
        ] = current_count + 1


    def get_attempts_for_current_step(
        self,
    ) -> int:
        """
        Return the number of attempts on the
        current step.
        """

        step = self.get_current_step()

        if step is None:
            return 0

        return self.attempts_by_step.get(
            step.step_number,
            0,
        )


    def get_hints_for_current_step(
        self,
    ) -> int:
        """
        Return the number of hints used on the
        current step.
        """

        step = self.get_current_step()

        if step is None:
            return 0

        return self.hints_used_by_step.get(
            step.step_number,
            0,
        )


    def record_math_error(
        self,
    ) -> None:
        """
        Record one genuine mathematical error for
        the current step. Format errors are not
        recorded here.
        """

        step = self.get_current_step()

        if step is None:
            return

        step_number = step.step_number

        current_count = self.math_errors_by_step.get(
            step_number,
            0,
        )

        self.math_errors_by_step[
            step_number
        ] = current_count + 1


    def get_math_errors_for_current_step(
        self,
    ) -> int:
        """
        Return genuine mathematical errors on the
        current step.
        """

        step = self.get_current_step()

        if step is None:
            return 0

        return self.math_errors_by_step.get(
            step.step_number,
            0,
        )


    def advance(
        self,
    ) -> None:
        """
        Advance to the next solution step.

        If there are no more steps, mark the
        problem complete.
        """

        if self.completed:
            return

        self.current_step_index += 1

        if (
            self.current_step_index
            >= len(self.problem.solution_steps)
        ):
            self.completed = True


    def is_complete(
        self,
    ) -> bool:
        """
        Return True when all tutoring steps
        have been completed.
        """

        return self.completed


    def get_completed_step_count(
        self,
    ) -> int:
        """
        Return how many solution steps have
        already been completed.
        """

        return min(
            self.current_step_index,
            len(self.problem.solution_steps),
        )


    def get_total_attempts(
        self,
    ) -> int:
        """
        Return total mathematical attempts across
        all steps.
        """

        return sum(
            self.attempts_by_step.values()
        )


    def get_total_hints_used(
        self,
    ) -> int:
        """
        Return total hints used across all steps.
        """

        return sum(
            self.hints_used_by_step.values()
        )