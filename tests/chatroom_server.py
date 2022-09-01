from typing import List
import giambio
from giambio.socket import AsyncSocket
import logging
import sys

# An asynchronous chatroom

clients: List[giambio.socket.AsyncSocket] = []


async def serve(bind_address: tuple):
    """
    Serves asynchronously forever

    :param bind_address: The address to bind the server to represented as a tuple
    (address, port) where address is a string and port is an integer
    """

    sock = giambio.socket.socket()
    await sock.bind(bind_address)
    await sock.listen(5)
    logging.info(f"Serving asynchronously at {bind_address[0]}:{bind_address[1]}")
    async with giambio.create_pool() as pool:
        async with sock:
            while True:
                try:
                    conn, address_tuple = await sock.accept()
                    clients.append(conn)
                    logging.info(f"{address_tuple[0]}:{address_tuple[1]} connected")
                    await pool.spawn(handler, conn, address_tuple)
                except Exception as err:
                    # Because exceptions just *work*
                    logging.info(f"{address_tuple[0]}:{address_tuple[1]} has raised {type(err).__name__}: {err}")


async def handler(sock: AsyncSocket, client_address: tuple):
    """
    Handles a single client connection

    :param sock: The AsyncSocket object connected to the client
    :param client_address: The client's address represented as a tuple
    (address, port) where address is a string and port is an integer
    :type client_address: tuple
    """

    address = f"{client_address[0]}:{client_address[1]}"
    async with sock:  # Closes the socket automatically
        await sock.send_all(b"Welcome to the chatroom pal, start typing and press enter!\n")
        while True:
            data = await sock.receive(1024)
            if not data:
                break
            elif data == b"exit\n":
                await sock.send_all(b"I'm dead dude\n")
                raise TypeError("Oh, no, I'm gonna die!")
            logging.info(f"Got: {data!r} from {address}")
            for i, client_sock in enumerate(clients):
                logging.info(f"Sending {data!r} to {':'.join(map(str, await client_sock.getpeername()))}")
                if client_sock != sock:
                    await client_sock.send_all(data)
            logging.info(f"Sent {data!r} to {i} clients")
    logging.info(f"Connection from {address} closed")
    clients.remove(sock)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1501
    logging.basicConfig(
        level=20,
        format="[%(levelname)s] %(asctime)s %(message)s",
        datefmt="%d/%m/%Y %p",
    )
    try:
        giambio.run(serve, ("localhost", port))
    except (Exception, KeyboardInterrupt) as error:  # Exceptions propagate!
        if isinstance(error, KeyboardInterrupt):
            logging.info("Ctrl+C detected, exiting")
        else:
            logging.error(f"Exiting due to a {type(error).__name__}: {error}")
