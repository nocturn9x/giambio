"""

Basic abstraction layer for giambio asynchronous sockets

"""


import socket
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

        return await self.loop.read_sock(self.sock, max_size)

    async def accept(self):
        """Accepts the socket, completing the 3-step TCP handshake asynchronously"""

        to_wrap = await self.loop.accept_sock(self.sock)
        return self.loop.wrap_socket(to_wrap[0]), to_wrap[1]

    async def send_all(self, data: bytes):
        """Sends all data inside the buffer asynchronously until it is empty"""

        return await self.loop.sock_sendall(self.sock, data)

    async def close(self):
        """Closes the socket asynchronously"""

        await self.loop.close_sock(self.sock)

    async def connect(self, addr: tuple):
        """Connects the socket to an endpoint"""

        await self.loop.connect_sock(self.sock, addr)

    def __enter__(self):
        return self.sock.__enter__()

    def __exit__(self, *args):
        return self.sock.__exit__(*args)

    def __repr__(self):
        return f"giambio.socket.AsyncSocket({self.sock}, {self.loop})"

