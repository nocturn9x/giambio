"""
Basic abstraction layer for giambio asynchronous sockets

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

from .run import get_event_loop
import socket
from .exceptions import ResourceClosed


class AsyncSocket:
    """
    Abstraction layer for asynchronous sockets
    """

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.loop = get_event_loop()
        self._closed = False
        self.sock.setblocking(False)

    async def receive(self, max_size: int):
        """
        Receives up to max_size bytes from a socket asynchronously
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        return await self.loop.read_sock(self.sock, max_size)

    async def accept(self):
        """
        Accepts the socket, completing the 3-step TCP handshake asynchronously
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        to_wrap = await self.loop.accept_sock(self.sock)
        return wrap_socket(to_wrap[0]), to_wrap[1]

    async def send_all(self, data: bytes):
        """
        Sends all data inside the buffer asynchronously until it is empty
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        return await self.loop.sock_sendall(self.sock, data)

    async def close(self):
        """
        Closes the socket asynchronously
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        await self.loop.close_sock(self.sock)
        self._closed = True

    async def connect(self, addr: tuple):
        """
        Connects the socket to an endpoint
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        await self.loop.connect_sock(self.sock, addr)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    def __repr__(self):
        return f"giambio.socket.AsyncSocket({self.sock}, {self.loop})"


def wrap_socket(sock: socket.socket) -> AsyncSocket:
    """
    Wraps a standard socket into an async socket
    """

    return AsyncSocket(sock)