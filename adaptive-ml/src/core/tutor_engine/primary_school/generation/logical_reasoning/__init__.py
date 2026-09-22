from src.core.tutor_engine.primary_school.generation.logical_reasoning.constraints import (
    candidate_satisfies,
    validate_candidate,
    validate_spec,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.enumerate import (
    enumerate_candidates,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    AllDifferent,
    DigitDifference,
    DigitOrder,
    DigitSum,
    DistMoreThan,
    DistTimes,
    DistTotal,
    DistributionCandidate,
    DistributionDomain,
    DivisibleBy,
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
    InInterval,
    LogicCandidate,
    LogicDomain,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    NumberCandidate,
    NumberDomain,
    NumberParity,
    NotPlacedAt,
    PlacedAt,
    PRIVATE_PUZZLE_FIELDS,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.distribution_puzzles import (
    DistributionPuzzle,
    generate_distribution_puzzle,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.logic_detective import (
    LogicDetectivePuzzle,
    generate_logic_detective,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.number_detective import (
    NumberDetectivePuzzle,
    generate_number_detective,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.compile import (
    compile_logical_reasoning_puzzle,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.generate import (
    LOGICAL_REASONING_FAMILIES,
    generate_logical_reasoning_problem,
    select_logical_reasoning_family,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.verify import (
    VerificationResult,
    assert_public_view_is_safe,
    satisfying_candidates,
    verify_unique_solution,
)

__all__ = [
    "AllDifferent",
    "DigitDifference",
    "DigitOrder",
    "DigitSum",
    "DistMoreThan",
    "DistTimes",
    "DistTotal",
    "DistributionCandidate",
    "DistributionDomain",
    "DistributionPuzzle",
    "DivisibleBy",
    "FAMILY_DISTRIBUTION",
    "FAMILY_LOGIC_DETECTIVE",
    "FAMILY_NUMBER_DETECTIVE",
    "InInterval",
    "NumberDetectivePuzzle",
    "LogicCandidate",
    "LogicDetectivePuzzle",
    "LogicDomain",
    "LogicalPuzzleSpec",
    "LogicalReasoningVerificationError",
    "NumberCandidate",
    "NumberDomain",
    "NumberParity",
    "NotPlacedAt",
    "PRIVATE_PUZZLE_FIELDS",
    "PlacedAt",
    "VerificationResult",
    "assert_public_view_is_safe",
    "candidate_satisfies",
    "compile_logical_reasoning_puzzle",
    "enumerate_candidates",
    "generate_distribution_puzzle",
    "generate_logical_reasoning_problem",
    "generate_logic_detective",
    "generate_number_detective",
    "LOGICAL_REASONING_FAMILIES",
    "select_logical_reasoning_family",
    "satisfying_candidates",
    "validate_candidate",
    "validate_spec",
    "verify_unique_solution",
]
