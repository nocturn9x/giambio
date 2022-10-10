import sys
import giambio
import logging

from debugger import Debugger


async def reader(q: giambio.Queue, prompt: str = ""):
    in_stream = giambio.io.AsyncStream(sys.stdin.fileno(), close_on_context_exit=False, mode="r")
    out_stream = giambio.io.AsyncStream(sys.stdout.fileno(), close_on_context_exit=False, mode="w")
    while True:
        await out_stream.write(prompt)
        await q.put((0, await in_stream.read()))


async def receiver(sock: giambio.socket.AsyncSocket, q: giambio.Queue):
    data = b""
    while True:
        while not data.endswith(b"\n"):
            temp = await sock.receive(1024)
            if not temp:
                raise EOFError("end of file")
            data += temp
        data, rest = data.split(b"\n", maxsplit=2)
        buffer = b"".join(rest)
        await q.put((1, data.decode()))
        data = buffer


async def main(host: tuple[str, int]):
    """
    Main client entry point
    """

    queue = giambio.Queue()
    out_stream = giambio.io.AsyncStream(sys.stdout.fileno(), close_on_context_exit=False, mode="w")
    async with giambio.create_pool() as pool:
        async with giambio.socket.socket() as sock:
            await sock.connect(host)
            await out_stream.write("Connection successful\n")
            await pool.spawn(receiver, sock, queue)
            await pool.spawn(reader, queue, "> ")
            while True:
                op, data = await queue.get()
                if op == 1:
                    await out_stream.write(data)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1501
    logging.basicConfig(
        level=20,
        format="[%(levelname)s] %(asctime)s %(message)s",
        datefmt="%d/%m/%Y %p",
    )
    try:
        giambio.run(main, ("localhost", port), debugger=Debugger())
    except (Exception, KeyboardInterrupt) as error:  # Exceptions propagate!
        if isinstance(error, KeyboardInterrupt):
            logging.info("Ctrl+C detected, exiting")
        else:
            logging.error(f"Exiting due to a {type(error).__name__}: {error}")
