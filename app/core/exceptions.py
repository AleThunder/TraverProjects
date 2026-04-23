class TravelPlannerError(Exception):
    """Base exception for expected application-level failures."""

    status_code = 500
    detail = "Unexpected application error"

    def __init__(self, detail: str | None = None) -> None:
        """Initialize the exception with an optional client-facing detail."""
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(TravelPlannerError):
    """Raised when a requested project, place, or external artwork is missing."""

    status_code = 404
    detail = "Resource not found"


class BusinessRuleError(TravelPlannerError):
    """Raised when a request violates travel planning business rules."""

    status_code = 400
    detail = "Business rule violation"


class ConflictError(TravelPlannerError):
    """Raised when a request conflicts with an existing resource or DB constraint."""

    status_code = 409
    detail = "Resource conflict"


class UnauthorizedError(TravelPlannerError):
    """Raised when authentication credentials are missing or invalid."""

    status_code = 401
    detail = "Authentication required"


class ExternalServiceError(TravelPlannerError):
    """Raised when a required third-party API cannot complete the operation."""

    status_code = 502
    detail = "External service error"
