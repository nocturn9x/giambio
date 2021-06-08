"""
Exceptions for giambio

Copyright (C) 2020 nocturn9x

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import traceback
from typing import List


class GiambioError(Exception):
    """
    Base class for giambio exceptions
    """

    ...


class InternalError(GiambioError):
    """
    Internal exception
    """

    ...


class CancelledError(GiambioError):
    """
    Exception raised by the giambio.objects.Task.cancel() method
    to terminate a child task. This should NOT be caught, or
    at least it should be re-raised and never ignored
    """

    ...


class ResourceBusy(GiambioError):
    """
    Exception that is raised when a resource is accessed by more than
    one task at a time
    """

    ...


class ResourceClosed(GiambioError):
    """
    Raised when I/O is attempted on a closed resource
    """

    ...


class TooSlowError(GiambioError):
    """
    This is raised if the timeout of a pool created using
    giambio.with_timeout expires
    """


class ErrorStack(GiambioError):
    """
    This exception wraps multiple exceptions
    and shows each individual traceback of them when
    printed. This is to ensure that no exception is
    lost even if 2 or more tasks raise at the
    same time.
    """

    def __init__(self, errors: List[BaseException]):
        """
        Object constructor
        """

        super().__init__()
        self.errors = errors

    def __str__(self):
        """
        Returns str(self)
        """

        tracebacks = ""
        for i, err in enumerate(self.errors):
            if i not in (1, len(self.errors)):
                tracebacks += f"\n{''.join(traceback.format_exception(type(err), err, err.__traceback__))}\n{'-' * 32}\n"
            else:
                tracebacks += f"\n{''.join(traceback.format_exception(type(err), err, err.__traceback__))}"
        return f"Multiple errors occurred:\n{tracebacks}"
