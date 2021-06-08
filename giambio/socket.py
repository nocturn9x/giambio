"""
Socket and networking utilities

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

import socket as _socket
from .io import AsyncSocket


def wrap_socket(sock: _socket.socket) -> AsyncSocket:
    """
    Wraps a standard socket into an async socket
    """

    return AsyncSocket(sock)


def socket(*args, **kwargs):
    """
    Creates a new giambio socket, taking in the same positional and
    keyword arguments as the standard library's socket.socket
    constructor
    """

    return AsyncSocket(_socket.socket(*args, **kwargs))
