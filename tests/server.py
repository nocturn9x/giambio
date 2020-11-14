import giambio
from giambio.socket import AsyncSocket
import socket
import logging
import sys


# A test to check for asynchronous I/O

logging.basicConfig(
    level=20, format="[%(levelname)s] %(asctime)s %(message)s", datefmt="%d/%m/%Y %p"
)


async def server(address: tuple):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(address)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.listen(5)
    asock = giambio.wrap_socket(sock)   # We make the socket an async socket
    logging.info(f"Echo server serving asynchronously at {address}")
    while True:
        try:
            async with giambio.async_pool() as pool:
                conn, addr = await asock.accept()
                logging.info(f"{addr} connected")
                pool.spawn(echo_handler, conn, addr)
        except TypeError:
            print("Looks like we have a naughty boy here!")


async def echo_handler(sock: AsyncSocket, addr: tuple):
    async with sock:
        await sock.send_all(b"Welcome to the server pal, feel free to send me something!\n")
        while True:
            await sock.send_all(b"-> ")
            data = await sock.receive(1024)
            if not data:
                break
            elif data == b"raise\n":
                await sock.send_all(b"I'm dead dude\n")
                raise TypeError("Oh, no, I'm gonna die!")
            to_send_back = data
            data = data.decode("utf-8").encode("unicode_escape")
            logging.info(f"Got: '{data.decode('utf-8')}' from {addr}")
            await sock.send_all(b"Got: " + to_send_back)
            logging.info(f"Echoed back '{data.decode('utf-8')}' to {addr}")
    logging.info(f"Connection from {addr} closed")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 1500
    try:
        giambio.run(server, ("", port))
    except (Exception, KeyboardInterrupt) as error:  # Exceptions propagate!
        print(f"Exiting due to a {type(error).__name__}: '{error}'")
