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

    async def receive(self, max_size: int):
        """Receives up to max_size from a socket asynchronously"""

        closed = False
        try:
            return await self.loop.read_sock(self.sock, max_size)
        except OSError:
            closed = True
        if closed:
            raise ResourceClosed("I/O operation on closed socket")

    async def accept(self):
        """Accepts the socket, completing the 3-step TCP handshake asynchronously"""

        closed = False
        try:
            to_wrap = await self.loop.accept_sock(self.sock)
            return self.loop.wrap_socket(to_wrap[0]), to_wrap[1]
        except OSError:
            closed = True
        if closed:
            raise ResourceClosed("I/O operation on closed socket")

    async def send_all(self, data: bytes):
        """Sends all data inside the buffer asynchronously until it is empty"""

        closed = False
        try:
            return await self.loop.sock_sendall(self.sock, data)
        except OSError:
            closed = True
        if closed:
            raise ResourceClosed("I/O operation on closed socket")

    async def close(self):
        """Closes the socket asynchronously"""

        await self.loop.close_sock(self.sock)

    async def connect(self, addr: tuple):
        """Connects the socket to an endpoint"""

        closed = False
        try:
            await self.loop.connect_sock(self.sock, addr)
        except OSError:
            closed = True
        if closed:
            raise ResourceClosed("I/O operation on closed socket")

    def __enter__(self):
        return self.sock.__enter__()

    def __exit__(self, *args):
        return self.sock.__exit__(*args)

    def __repr__(self):
        return f"giambio.socket.AsyncSocket({self.sock}, {self.loop})"

