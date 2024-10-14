class SchemaValidationException(Exception):
    """Raised when user-input schema is not valid"""

    pass


class ApplicationNotFoundException(Exception):
    """Raised when application is not found"""

    pass


class InputValidationException(Exception):
    """Raised when user-input data is not following the schema"""

    pass


class OutputValidationException(Exception):
    """Raised when output data is not following the schema"""

    pass


class LLMCallException(Exception):
    """Raised when there is an error in calling the LLM"""

    pass
