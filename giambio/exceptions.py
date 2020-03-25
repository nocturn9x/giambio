class GiambioError(Exception):
    """Base class for gaimbio exceptions"""
    pass


class AlreadyJoinedError(GiambioError):
    pass


class CancelledError(GiambioError):
    """Exception raised as a result of the giambio.core.cancel() method"""

    def __repr__(self):
        return "giambio.exceptions.CancelledError"

class TaskCancelled(GiambioError):
    """This exception is raised when the user attempts to join a cancelled task"""