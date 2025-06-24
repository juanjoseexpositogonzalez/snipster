class SnippetNotFoundError(Exception):
    """Exception raised when a Snipster resource is not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        self.message = message
