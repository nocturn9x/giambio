"""
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

from traceback import format_exception


class GiambioError(Exception):
    """Base class for giambio exceptions"""
    pass


class GiambioCriticalError(BaseException):
    """A critical error"""


class CancelledError(GiambioCriticalError):
    """Exception raised as a result of the giambio._layers.Task.cancel()  method"""


class ResourceBusy(GiambioError):
    """Exception that is raised when a resource is accessed by more than
       one task at a time"""
    pass


class BrokenPipeError(GiambioError):
    """Wrapper around the broken pipe socket.error"""
    pass


class ResourceClosed(GiambioError):
    """Raised when I/O is attempted on a closed fd"""

    pass


class ErrorStack(GiambioError):
    """Raised when multiple exceptions occur upon cancellation"""

    SEP = "----------------------------------\n"
    errors = []

    def __str__(self):
        """Taken from anyio"""

        tb_list = ['\n'.join(format_exception(type(err), err, err.__traceback__))
                   for err in self.errors]
        return f"{len(self.errors)} errors occurred, details below\n{self.SEP}{self.SEP.join(tb_list)}"

    def __repr__(self):
        return f"<{self.__class__.__name__} (contains {len(self.errors)} exceptions)>"
