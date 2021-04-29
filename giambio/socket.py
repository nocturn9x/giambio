""" Basic abstraction layer for giambio asynchronous sockets

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

import socket as builtin_socket
from giambio.run import get_event_loop
from giambio.exceptions import ResourceClosed
from giambio.traps import want_write, want_read

# TODO: Take into account SSLWantReadError and SSLWantWriteError
IOInterrupt = (BlockingIOError, InterruptedError)


class AsyncSocket:
    """
    Abstraction layer for asynchronous sockets
    """

    def __init__(self, sock: builtin_socket.socket):
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
        assert max_size >= 1, "max_size must be >= 1"
        await want_read(self.sock)
        try:
            return self.sock.recv(max_size)
        except IOInterrupt:
            await want_read(self.sock)
        return self.sock.recv(max_size)

    async def accept(self):
        """
        Accepts the socket, completing the 3-step TCP handshake asynchronously
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        await want_read(self.sock)
        try:
            to_wrap = self.sock.accept()
        except IOInterrupt:
            # Some platforms (namely OSX systems) act weird and handle
            # the errno 35 signal (EAGAIN) for sockets in a weird manner,
            # and this seems to fix the issue. Not sure about why since we
            # already called want_read above, but it ain't stupid if it works I guess
            await want_read(self.sock)
            to_wrap = self.sock.accept()
        return wrap_socket(to_wrap[0]), to_wrap[1]

    async def send_all(self, data: bytes):
        """
        Sends all data inside the buffer asynchronously until it is empty
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        while data:
            await want_write(self.sock)
            try:
                sent_no = self.sock.send(data)
            except IOInterrupt:
                await want_write(self.sock)
                sent_no = self.sock.send(data)
            data = data[sent_no:]

    async def close(self):
        """
        Closes the socket asynchronously
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        await want_write(self.sock)
        try:
            self.sock.close()
        except IOInterrupt:
            await want_write(self.sock)
            self.sock.close()
        self.loop.selector.unregister(self.sock)
        self.loop.current_task.last_io = ()
        self._closed = True

    async def connect(self, addr: tuple):
        """
        Connects the socket to an endpoint
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        await want_write(self.sock)
        try:
            self.sock.connect(addr)
        except IOInterrupt:
            await want_write(self.sock)
            self.sock.connect(addr)

    async def bind(self, addr: tuple):
        """
        Binds the socket to an address

        :param addr: The address, port tuple to bind to
        :type addr: tuple
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        self.sock.bind(addr)

    async def listen(self, backlog: int):
        """
        Starts listening with the given backlog

        :param backlog: The address, port tuple to bind to
        :type backlog: int
        """

        if self._closed:
            raise ResourceClosed("I/O operation on closed socket")
        self.sock.listen(backlog)

    def __del__(self):
        """
        Implements the destructor for the async socket,
        notifying the event loop that the socket must not
        be listened for anymore. This avoids the loop
        blocking forever on trying to read from a socket
        that's gone out of scope without being closed
        """

        if not self._closed and self.loop.selector.get_map() and self.sock in self.loop.selector.get_map():
            self.loop.selector.unregister(self.sock)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    def __repr__(self):
        return f"giambio.socket.AsyncSocket({self.sock}, {self.loop})"


def wrap_socket(sock: builtin_socket.socket) -> AsyncSocket:
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

    return AsyncSocket(builtin_socket.socket(*args, **kwargs))

