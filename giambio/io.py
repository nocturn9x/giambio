"""
Basic abstraction layers for all async I/O primitives

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

from giambio.exceptions import ResourceClosed
from giambio.traps import want_write, want_read, io_release

try:
    from ssl import SSLWantReadError, SSLWantWriteError

    WantRead = (BlockingIOError, InterruptedError, SSLWantReadError)
    WantWrite = (BlockingIOError, InterruptedError, SSLWantWriteError)
except ImportError:
    WantRead = (BlockingIOError, InterruptedError)
    WantWrite = (BlockingIOError, InterruptedError)


class AsyncSocket:
    """
    Abstraction layer for asynchronous sockets
    """

    def __init__(self, sock, do_handshake_on_connect: bool = True):
        self.sock = sock
        self.do_handshake_on_connect = do_handshake_on_connect
        self._fd = sock.fileno()
        self.sock.setblocking(False)

    async def receive(self, max_size: int, flags: int = 0) -> bytes:
        """
        Receives up to max_size bytes from a socket asynchronously
        """

        assert max_size >= 1, "max_size must be >= 1"
        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        while True:
            try:
                return self.sock.recv(max_size, flags)
            except WantRead:
                await want_read(self.sock)
            except WantWrite:
                await want_write(self.sock)

    async def connect(self, address):
        """
        Wrapper socket method
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        while True:
            try:
                self.sock.connect(address)
                if self.do_handshake_on_connect:
                    await self.do_handshake()
                return
            except WantWrite:
                await want_write(self.sock)

    async def accept(self):
        """
        Accepts the socket, completing the 3-step TCP handshake asynchronously
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        while True:
            try:
                remote, addr = self.sock.accept()
                return type(self)(remote), addr
            except WantRead:
                await want_read(self.sock)

    async def send_all(self, data: bytes, flags: int = 0):
        """
        Sends all data inside the buffer asynchronously until it is empty
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        while data:
            try:
                sent_no = self.sock.send(data, flags)
            except WantRead:
                await want_read(self.sock)
            except WantWrite:
                await want_write(self.sock)
            data = data[sent_no:]

    async def close(self):
        """
        Closes the socket asynchronously
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        await io_release(self.sock)
        self.sock.close()
        self._fd = -1
        self.sock = None

    async def shutdown(self, how):
        """
        Wrapper socket method
        """

        if self.sock:
            self.sock.shutdown(how)

    async def bind(self, addr: tuple):
        """
        Binds the socket to an address

        :param addr: The address, port tuple to bind to
        :type addr: tuple
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        self.sock.bind(addr)

    async def listen(self, backlog: int):
        """
        Starts listening with the given backlog

        :param backlog: The socket's backlog
        :type backlog: int
        """

        if self._fd == -1:
            raise ResourceClosed("I/O operation on closed socket")
        self.sock.listen(backlog)

    async def __aenter__(self):
        self.sock.__enter__()
        return self

    async def __aexit__(self, *args):
        if self.sock:
            self.sock.__exit__(*args)

    # Yes, I stole these from Curio because I could not be
    # arsed to write a bunch of uninteresting simple socket
    # methods from scratch, deal with it.

    def fileno(self):
        """
        Wrapper socket method
        """

        return self._fd

    def settimeout(self, seconds):
        """
        Wrapper socket method
        """

        raise RuntimeError("Use with_timeout() to set a timeout")

    def gettimeout(self):
        """
        Wrapper socket method
        """

        return None

    def dup(self):
        """
        Wrapper socket method
        """

        return type(self)(self._socket.dup())

    async def do_handshake(self):
        """
        Wrapper socket method
        """

        if not hasattr(self.sock, "do_handshake"):
            return
        while True:
            try:
                return self.sock.do_handshake()
            except WantRead:
                await want_read(self.sock)
            except WantWrite:
                await want_write(self.sock)

    async def recvfrom(self, buffersize, flags=0):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.sock.recvfrom(buffersize, flags)
            except WantRead:
                await want_read(self.sock)
            except WantWrite:
                await want_write(self.sock)

    async def recvfrom_into(self, buffer, bytes=0, flags=0):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.sock.recvfrom_into(buffer, bytes, flags)
            except WantRead:
                await want_read(self.sock)
            except WantWrite:
                await want_write(self.sock)

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
                return self.sock.sendto(bytes, flags, address)
            except WantWrite:
                await want_write(self.sock)
            except WantRead:
                await want_read(self.sock)
    
    async def getpeername(self):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.sock.getpeername()
            except WantWrite:
                await want_write(self.sock)
            except WantRead:
                await want_read(self.sock)

    async def getsockname(self):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.sock.getpeername()
            except WantWrite:
                await want_write(self.sock)
            except WantRead:
                await want_read(self.sock)

    async def recvmsg(self, bufsize, ancbufsize=0, flags=0):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.sock.recvmsg(bufsize, ancbufsize, flags)
            except WantRead:
                await want_read(self.sock)

    async def recvmsg_into(self, buffers, ancbufsize=0, flags=0):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.sock.recvmsg_into(buffers, ancbufsize, flags)
            except WantRead:
                await want_read(self.sock)

    async def sendmsg(self, buffers, ancdata=(), flags=0, address=None):
        """
        Wrapper socket method
        """

        while True:
            try:
                return self.sock.sendmsg(buffers, ancdata, flags, address)
            except WantRead:
                await want_write(self.sock)

    def __repr__(self):
        return f"AsyncSocket({self.sock})"
