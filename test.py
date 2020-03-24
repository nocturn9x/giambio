import giambio
from giambio.socket import AsyncSocket
import socket
import logging


loop = giambio.core.EventLoop()

logging.basicConfig(level=20,
                    format="[%(levelname)s] %(asctime)s %(message)s",
                    datefmt='%d/%m/%Y %p')


async def make_srv(address: tuple):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(address)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.listen(5)
    asock = loop.wrap_socket(sock)
    logging.info(f"Echo server serving asynchronously at {address}")
    while True:
        conn, addr = await asock.accept()
        logging.info(f"{addr} connected")
        task = loop.spawn(echo_server(conn, addr))


async def echo_server(sock: AsyncSocket, addr: tuple):
    with sock:
        await sock.send_all(b"Welcome to the server pal!\n")
        while True:
            data = await sock.receive(1000)
            if not data:
                break
            to_send_back = data
            data = data.decode("utf-8").encode('unicode_escape')
            logging.info(f"Got: '{data.decode('utf-8')}' from {addr}")
            await sock.send_all(b"Got: " + to_send_back)
            logging.info(f"Echoed back '{data.decode('utf-8')}' to {addr}")
    logging.info(f"Connection from {addr} closed")


try:
    loop.start(make_srv, ('', 1501))
except KeyboardInterrupt:      # Exceptions propagate!
    pass
