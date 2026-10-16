class ImportedPlannerError(RuntimeError):
    pass


class ImportedPlannerUnavailableError(ImportedPlannerError):
    pass


class ImportedPlannerTimeoutError(ImportedPlannerError):
    pass


class ImportedPlannerRequestError(ImportedPlannerError):
    pass


class ImportedPlanParseError(ImportedPlannerError):
    pass


class ImportedProblemCompileError(ValueError):
    pass


class UnsupportedImportedProblem(ImportedProblemCompileError):
    reason = "unsupported_problem_type"
