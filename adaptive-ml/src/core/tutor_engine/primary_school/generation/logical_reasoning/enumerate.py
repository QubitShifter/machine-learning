from itertools import product

from src.core.tutor_engine.primary_school.generation.logical_reasoning.constraints import (
    validate_spec,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    Candidate,
    DistributionCandidate,
    DistributionDomain,
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
    LogicCandidate,
    LogicDomain,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    MAX_ENUMERATED_CANDIDATES,
    NumberCandidate,
    NumberDomain,
)


def enumerate_candidates(spec: LogicalPuzzleSpec) -> tuple[Candidate, ...]:
    validate_spec(spec)
    if spec.family == FAMILY_NUMBER_DETECTIVE:
        return _enumerate_numbers(spec.domain)
    if spec.family == FAMILY_DISTRIBUTION:
        return _enumerate_distribution(spec.domain)
    return _enumerate_logic(spec.domain)


def _enumerate_numbers(domain: NumberDomain) -> tuple[Candidate, ...]:
    return tuple(
        NumberCandidate(value)
        for value in range(domain.minimum, domain.maximum + 1)
    )


def _enumerate_distribution(
    domain: DistributionDomain,
) -> tuple[Candidate, ...]:
    values = range(domain.minimum, domain.maximum + 1)
    names = domain.names
    combos = product(values, repeat=len(names))
    candidates = []
    for combo in combos:
        if len(candidates) >= MAX_ENUMERATED_CANDIDATES:
            raise LogicalReasoningVerificationError(
                "domain_too_large",
                "Distribution enumeration exceeded the safety bound.",
            )
        quantities = tuple(zip(names, combo))
        candidates.append(DistributionCandidate(quantities))
    return tuple(candidates)


def _enumerate_logic(domain: LogicDomain) -> tuple[Candidate, ...]:
    assignments = product(domain.positions, repeat=len(domain.objects))
    return tuple(
        LogicCandidate(
            assignment=tuple(zip(domain.objects, combo)),
        )
        for combo in assignments
    )
