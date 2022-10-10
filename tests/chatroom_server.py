import giambio
from giambio.socket import AsyncSocket
import logging
import sys

# An asynchronous chatroom

clients: dict[AsyncSocket, list[str, str]] = {}
names: set[str] = set()


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
                    clients[conn] = ["", f"{address_tuple[0]}:{address_tuple[1]}"]
                    logging.info(f"{address_tuple[0]}:{address_tuple[1]} connected")
                    await pool.spawn(handler, conn)
                except Exception as err:
                    # Because exceptions just *work*
                    logging.info(f"{address_tuple[0]}:{address_tuple[1]} has raised {type(err).__name__}: {err}")


async def handler(sock: AsyncSocket):
    """
    Handles a single client connection

    :param sock: The AsyncSocket object connected to the client
    """

    address = clients[sock][1]
    name = ""
    async with sock:  # Closes the socket automatically
        await sock.send_all(b"Welcome to the chatroom pal, may you tell me your name?\n> ")
        while True:
            while not name.endswith("\n"):
                name = (await sock.receive(64)).decode()
            name = name[:-1]
            if name not in names:
                names.add(name)
                clients[sock][0] = name
                break
            else:
                await sock.send_all(b"Sorry, but that name is already taken. Try again!\n> ")
        await sock.send_all(f"Okay {name}, welcome to the chatroom!\n".encode())
        logging.info(f"{name} has joined the chatroom ({address}), informing clients")
        for i, client_sock in enumerate(clients):
            if client_sock != sock and clients[client_sock][0]:
                await client_sock.send_all(f"{name} joins the chatroom!\n> ".encode())
        while True:
            await sock.send_all(b"> ")
            data = await sock.receive(1024)
            if not data:
                break
            logging.info(f"Got: {data!r} from {address}")
            for i, client_sock in enumerate(clients):
                if client_sock != sock and clients[client_sock][0]:
                    logging.info(f"Sending {data!r} to {':'.join(map(str, await client_sock.getpeername()))}")
                    if not data.endswith(b"\n"):
                        data += b"\n"
                    await client_sock.send_all(f"[{name}] ({address}): {data.decode()}> ".encode())
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
