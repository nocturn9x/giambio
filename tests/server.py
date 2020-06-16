import giambio
from giambio.socket import AsyncSocket
import socket
import logging

sched = giambio.AsyncScheduler()

logging.basicConfig(level=20,
                    format="[%(levelname)s] %(asctime)s %(message)s",
                    datefmt='%d/%m/%Y %p')


async def server(address: tuple):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(address)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.listen(5)
    asock = sched.wrap_socket(sock)
    logging.info(f"Echo server serving asynchronously at {address}")
    while True:
        conn, addr = await asock.accept()
        logging.info(f"{addr} connected")
        task = sched.create_task(echo_handler(conn, addr))

async def echo_handler(sock: AsyncSocket, addr: tuple):
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


if __name__ == "__main__":
    sched.create_task(server(('', 25000)))
    try:
        sched.run()
    except KeyboardInterrupt:      # Exceptions propagate!
        print("Exiting...")
