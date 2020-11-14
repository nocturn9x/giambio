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


import socket
from .exceptions import ResourceClosed
from ._traps import sleep

try:
    from ssl import SSLWantReadError, SSLWantWriteError
    WantRead = (BlockingIOError, InterruptedError, SSLWantReadError)
    WantWrite = (BlockingIOError, InterruptedError, SSLWantWriteError)
except ImportError:
    WantRead = (BlockingIOError, InterruptedError)
    WantWrite = (BlockingIOError, InterruptedError)


class AsyncSocket(object):
    """Abstraction layer for asynchronous sockets"""

    def __init__(self, sock: socket.socket, loop):
        self.sock = sock
        self.sock.setblocking(False)
        self.loop = loop
        self._closed = False

    async def receive(self, max_size: int):
        """Receives up to max_size from a socket asynchronously"""

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        self.loop.current_task.status = "I/O"
        return await self.loop._read_sock(self.sock, max_size)

    async def accept(self):
        """Accepts the socket, completing the 3-step TCP handshake asynchronously"""

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        to_wrap = await self.loop._accept_sock(self.sock)
        return self.loop.wrap_socket(to_wrap[0]), to_wrap[1]

    async def send_all(self, data: bytes):
        """Sends all data inside the buffer asynchronously until it is empty"""

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        return await self.loop._sock_sendall(self.sock, data)

    async def close(self):
        """Closes the socket asynchronously"""

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        await sleep(0)  # Give the scheduler the time to unregister the socket first
        await self.loop._close_sock(self.sock)
        self._closed = True

    async def connect(self, addr: tuple):
        """Connects the socket to an endpoint"""

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        await self.loop._connect_sock(self.sock, addr)

    async def __aenter__(self):
        return self.sock.__enter__()

    async def __aexit__(self, *_):
        await self.close()

    def __repr__(self):
        return f"giambio.socket.AsyncSocket({self.sock}, {self.loop})"
