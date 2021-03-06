import giambio
from giambio.socket import AsyncSocket
from debugger import Debugger
import socket
import logging
import sys

# A test to check for asynchronous I/O


async def serve(bind_address: tuple):
    """
    Serves asynchronously forever

    :param bind_address: The address to bind the server to represented as a tuple
    (address, port) where address is a string and port is an integer
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(bind_address)
    sock.listen(5)
    async_sock = giambio.wrap_socket(sock)   # We make the socket an async socket
    logging.info(f"Serving asynchronously at {bind_address[0]}:{bind_address[1]}")
    async with giambio.create_pool() as pool:
        while True:
            conn, address_tuple = await async_sock.accept()
            logging.info(f"{address_tuple[0]}:{address_tuple[1]} connected")
            pool.spawn(handler, conn, address_tuple)


async def handler(sock: AsyncSocket, client_address: tuple):
    """
    Handles a single client connection

    :param sock: The giambio.socket.AsyncSocket object connected
    to the client
    :type sock: :class: giambio.socket.AsyncSocket
    :param client_address: The client's address represented as a tuple
    (address, port) where address is a string and port is an integer
    :type client_address: tuple
    """

    address = f"{client_address[0]}:{client_address[1]}"
    async with sock:   # Closes the socket automatically
        await sock.send_all(b"Welcome to the server pal, feel free to send me something!\n")
        while True:
            await sock.send_all(b"-> ")
            data = await sock.receive(1024)
            if not data:
                break
            elif data == b"exit\n":
                await sock.send_all(b"I'm dead dude\n")
                raise TypeError("Oh, no, I'm gonna die!")
            logging.info(f"Got: {data!r} from {address}")
            await sock.send_all(b"Got: " + data)
            logging.info(f"Echoed back {data!r} to {address}")
    logging.info(f"Connection from {address} closed")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    logging.basicConfig(level=20, format="[%(levelname)s] %(asctime)s %(message)s", datefmt="%d/%m/%Y %p")
    try:
        giambio.run(serve, ("localhost", port), debugger=None)
    except (Exception, KeyboardInterrupt) as error:  # Exceptions propagate!
        if isinstance(error, KeyboardInterrupt):
            logging.info("Ctrl+C detected, exiting")
        else:
            logging.error(f"Exiting due to a {type(error).__name__}: {error}")
