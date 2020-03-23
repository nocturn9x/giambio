class GiambioError(Exception):
    """Base class for gaimbio exceptions"""
    pass


class AlreadyJoinedError(GiambioError):
    pass


class CancelledError(GiambioError):
    """Exception raised as a result of the giambio.core.cancel() method"""

    def __repr__(self):
        return "giambio.exceptions.CancelledError"
