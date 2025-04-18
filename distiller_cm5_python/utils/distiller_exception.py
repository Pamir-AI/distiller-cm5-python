class LogOnlyError(Exception):
    """Exception that only needs to be logged and does not need to be shown to the user immediately."""

    def __init__(self, message):
        super().__init__(message)


class UserVisibleError(Exception):
    """Exception for serious errors that need to be shown directly to the user."""

    def __init__(self, message):
        super().__init__(message)
