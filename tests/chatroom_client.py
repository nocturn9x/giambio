import sys
from typing import Tuple
import giambio
import logging


async def sender(sock: giambio.socket.AsyncSocket, q: giambio.Queue):
    while True:
        await sock.send_all(b"yo")
        await q.put((0, ""))


async def receiver(sock: giambio.socket.AsyncSocket, q: giambio.Queue):
    data = b""
    buffer = b""
    while True:
        while not data.endswith(b"\n"):
            data += await sock.receive(1024)
        data, rest = data.split(b"\n", maxsplit=2)
        buffer = b"".join(rest)
        await q.put((1, data.decode()))
        data = buffer        


async def main(host: Tuple[str, int]):
    """
    Main client entry point
    """

    queue = giambio.Queue()
    async with giambio.create_pool() as pool:
        async with giambio.socket.socket() as sock:
            await sock.connect(host)
            await pool.spawn(sender, sock, queue)
            await pool.spawn(receiver, sock, queue)
            while True:
                op, data = await queue.get()
                if op == 0:
                    print(f"Sent.")
                else:
                    print(f"Received: {data}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1501
    logging.basicConfig(
        level=20,
        format="[%(levelname)s] %(asctime)s %(message)s",
        datefmt="%d/%m/%Y %p",
    )
    try:
        giambio.run(main, ("localhost", port))
    except (Exception, KeyboardInterrupt) as error:  # Exceptions propagate!
        if isinstance(error, KeyboardInterrupt):
            logging.info("Ctrl+C detected, exiting")
        else:
            logging.error(f"Exiting due to a {type(error).__name__}: {error}")
