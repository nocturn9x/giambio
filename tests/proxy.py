from debugger import Debugger
import giambio
import socket


async def proxy_one_way(source: giambio.socket.AsyncSocket, sink: giambio.socket.AsyncSocket):
    """
    Sends data from source to sink
    """

    sink_addr = ":".join(map(str, await sink.getpeername()))
    source_addr = ":".join(map(str, await source.getpeername()))
    while True:
        data = await source.receive(1024)
        if not data:
            print(f"{source_addr} has exited, closing connection to {sink_addr}")
            await sink.shutdown(socket.SHUT_WR)
            break
        print(f"Got {data.decode('utf8', errors='ignore')!r} from {source_addr}, forwarding it to {sink_addr}")
        await sink.send_all(data)


async def proxy_two_way(a: giambio.socket.AsyncSocket, b: giambio.socket.AsyncSocket):
    """
    Sets up a two-way proxy from a to b and from b to a
    """

    async with giambio.create_pool() as pool:
        await pool.spawn(proxy_one_way, a, b)
        await pool.spawn(proxy_one_way, b, a)


async def main(delay: int, a: tuple, b: tuple):
    """
    Sets up the proxy
    """

    start = giambio.clock()
    print(f"Starting two-way proxy from {a[0]}:{a[1]} to {b[0]}:{b[1]}, lasting for {delay} seconds")
    async with giambio.skip_after(delay) as p:
        sock_a = giambio.socket.socket()
        sock_b = giambio.socket.socket()
        await sock_a.connect(a)
        await sock_b.connect(b)
        async with sock_a, sock_b:
            await proxy_two_way(sock_a, sock_b)
    print(f"Proxy has exited after {giambio.clock() - start:.2f} seconds")
    

try:
    giambio.run(main, 60, ("localhost", 12345), ("localhost", 54321), debugger=())
except (Exception, KeyboardInterrupt) as error:  # Exceptions propagate!
        if isinstance(error, KeyboardInterrupt):
            print("Ctrl+C detected, exiting")
        else:
            print(f"Exiting due to a {type(error).__name__}: {error}")