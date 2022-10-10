"""
Basic abstraction layers for all async I/O primitives

Copyright (C) 2020 nocturn9x

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import socket
import warnings
import os
import giambio
from giambio.exceptions import ResourceClosed
from giambio.traps import want_write, want_read, io_release, notify_closing


try:
    from ssl import SSLWantReadError, SSLWantWriteError, SSLSocket

    WantRead = (BlockingIOError, InterruptedError, SSLWantReadError)
    WantWrite = (BlockingIOError, InterruptedError, SSLWantWriteError)
except ImportError:
    WantRead = (BlockingIOError, InterruptedError)
    WantWrite = (BlockingIOError, InterruptedError)


class AsyncStream:
    """
    A generic asynchronous stream over
    a file descriptor. Only works on Linux
    & co because windows doesn't like select()
    to be called on non-socket objects
    (Thanks, Microsoft)
    """

    def __init__(self, fd: int, open_fd: bool = True, close_on_context_exit: bool = True, **kwargs):
        self._fd = fd
        self.stream = None
        if open_fd:
            self.stream = os.fdopen(self._fd, **kwargs)
            os.set_blocking(self._fd, False)
        self.close_on_context_exit = close_on_context_exit

    async def read(self, size: int = -1):
        """
        Reads up to size bytes from the
        given stream. If size == -1, read
        until EOF is reached
        """

        while True:
            try:
                return self.stream.read(size)
            except WantRead:
                await want_read(self.stream)

    async def write(self, data):
        """
        Writes data b to the file.
        Returns the number of bytes
        written
        """

        while True:
            try:
                return self.stream.write(data)
            except WantWrite:
                await want_write(self.stream)

    async def close(self):
        """
        Closes the stream asynchronously
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed stream")
        self._fd = -1
        await notify_closing(self.stream)
        await io_release(self.stream)
        self.stream.close()
        self.stream = None

    @property
    async def fileno(self):
        """
        Wrapper socket method
        """

        return self._fd

    async def __aenter__(self):
        self.stream.__enter__()
        return self

    async def __aexit__(self, *args):
        if self._fd != -1 and self.close_on_context_exit:
            await self.close()

    async def dup(self):
        """
        Wrapper stream method
        """

        return type(self)(os.dup(self._fd))

    def __repr__(self):
        return f"AsyncStream({self.stream})"

    def __del__(self):
        """
        Stream destructor. Do *not* call
        this directly: stuff will break
        """

        if self._fd != -1:
            try:
                os.set_blocking(self._fd, False)
                os.close(self._fd)
            except OSError as e:
                warnings.warn(f"An exception occurred in __del__ for stream {self} -> {type(e).__name__}: {e}")


class AsyncSocket(AsyncStream):
    """
    Abstraction layer for asynchronous sockets
    """

    def __init__(self, sock: socket.socket, close_on_context_exit: bool = True, do_handshake_on_connect: bool = True):
        super().__init__(sock.fileno(), open_fd=False, close_on_context_exit=close_on_context_exit)
        self.do_handshake_on_connect = do_handshake_on_connect
        self.stream = socket.fromfd(self._fd, sock.family, sock.type, sock.proto)
        self.stream.setblocking(False)
        # A socket that isn't connected doesn't
        # need to be closed
        self.needs_closing: bool = False

    async def receive(self, max_size: int, flags: int = 0) -> bytes:
        """
        Receives up to max_size bytes from a socket asynchronously
        """

        assert max_size >= 1, "max_size must be >= 1"
        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        while True:
            try:
                return self.stream.recv(max_size, flags)
            except WantRead:
                await want_read(self.stream)
            except WantWrite:
                await want_write(self.stream)

    async def connect(self, address):
        """
        Wrapper socket method
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        while True:
            try:
                self.stream.connect(address)
                if self.do_handshake_on_connect:
                    await self.do_handshake()
                break
            except WantWrite:
                await want_write(self.stream)
        self.needs_closing = True

    async def close(self):
        """
        Wrapper socket method
        """

        if self.needs_closing:
            await super().close()

    async def accept(self):
        """
        Accepts the socket, completing the 3-step TCP handshake asynchronously
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        while True:
            try:
                remote, addr = self.stream.accept()
                return type(self)(remote), addr
            except WantRead:
                await want_read(self.stream)

    async def send_all(self, data: bytes, flags: int = 0):
        """
        Sends all data inside the buffer asynchronously until it is empty
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        sent_no = 0
        while data:
            try:
                sent_no = self.stream.send(data, flags)
            except WantRead:
                await want_read(self.stream)
            except WantWrite:
                await want_write(self.stream)
            data = data[sent_no:]

    async def shutdown(self, how):
        """
        Wrapper socket method
        """

        if self.stream:
            self.stream.shutdown(how)
            await giambio.sleep(0)  # Checkpoint

    async def bind(self, addr: tuple):
        """
        Binds the socket to an address

        :param addr: The address, port tuple to bind to
        :type addr: tuple
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        self.stream.bind(addr)

    async def listen(self, backlog: int):
        """
        Starts listening with the given backlog

        :param backlog: The socket's backlog
        :type backlog: int
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        self.stream.listen(backlog)

    # Yes, I stole these from Curio because I could not be
    # arsed to write a bunch of uninteresting simple socket
    # methods from scratch, deal with it.

    async def settimeout(self, seconds):
        """
        Wrapper socket method
        """

        raise RuntimeError("Use with_timeout() to set a timeout")

    async def gettimeout(self):
        """
        Wrapper socket method
        """

        return None

    async def dup(self):
        """
        Wrapper socket method
        """

        return type(self)(self.stream.dup(), self.do_handshake_on_connect)

    async def do_handshake(self):
        """
        Wrapper socket method
        """

        if not hasattr(self.stream, "do_handshake"):
            return
        while True:
            try:
                self.stream: SSLSocket  # Silences pycharm warnings
                return self.stream.do_handshake()
            except WantRead:
                await want_read(self.stream)
            except WantWrite:
                await want_write(self.stream)

    async def recvfrom(self, buffersize, flags=0):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.stream.recvfrom(buffersize, flags)
            except WantRead:
                await want_read(self.stream)
            except WantWrite:
                await want_write(self.stream)

    async def recvfrom_into(self, buffer, bytes=0, flags=0):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.stream.recvfrom_into(buffer, bytes, flags)
            except WantRead:
                await want_read(self.stream)
            except WantWrite:
                await want_write(self.stream)

    async def sendto(self, bytes, flags_or_address, address=None):
        """
        Wrapper socket method
        """

        if address:
            flags = flags_or_address
        else:
            address = flags_or_address
            flags = 0
        while True:
            try:
                return self.stream.sendto(bytes, flags, address)
            except WantWrite:
                await want_write(self.stream)
            except WantRead:
                await want_read(self.stream)

    async def getpeername(self):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.stream.getpeername()
            except WantWrite:
                await want_write(self.stream)
            except WantRead:
                await want_read(self.stream)

    async def getsockname(self):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.stream.getpeername()
            except WantWrite:
                await want_write(self.stream)
            except WantRead:
                await want_read(self.stream)

    async def recvmsg(self, bufsize, ancbufsize=0, flags=0):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.stream.recvmsg(bufsize, ancbufsize, flags)
            except WantRead:
                await want_read(self.stream)

    async def recvmsg_into(self, buffers, ancbufsize=0, flags=0):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.stream.recvmsg_into(buffers, ancbufsize, flags)
            except WantRead:
                await want_read(self.stream)

    async def sendmsg(self, buffers, ancdata=(), flags=0, address=None):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.stream.sendmsg(buffers, ancdata, flags, address)
            except WantRead:
                await want_write(self.stream)

    def __repr__(self):
        return f"AsyncSocket({self.stream})"

    def __del__(self):
        if self.needs_closing:
            super().__del__()
