from debugger import Debugger
import giambio
import socket as sock
import ssl
import sys
import time

_print = print


def print(*args, **kwargs):
    sys.stdout.write(f"[{time.strftime('%H:%M:%S')}] ")
    _print(*args, **kwargs)


async def test(host: str, port: int, bufsize: int = 4096):
    socket = giambio.socket.wrap_socket(
        ssl.create_default_context().wrap_socket(
            sock=sock.socket(),
            # Note: do_handshake_on_connect MUST
            # be set to False on the synchronous socket!
            # Giambio handles the TLS handshake asynchronously
            # and making the SSL library handle it blocks
            # the entire event loop. To perform the TLS
            # handshake upon connection, set the this
            # parameter in the AsyncSocket class instead
            do_handshake_on_connect=False,
            server_hostname=host,
        )
    )
    print(f"Attempting a connection to {host}:{port}")
    await socket.connect((host, port))
    print("Connected")
    async with giambio.skip_after(2) as p:
        print(f"Pool with {p.timeout - giambio.clock():.2f} seconds timeout created")
        async with socket:
            # Closes the socket automatically
            print("Entered socket context manager, sending request data")
            await socket.send_all(
                b"""GET / HTTP/1.1\r\nHost: google.com\r\nUser-Agent: owo\r\nAccept: text/html\r\nConnection: keep-alive\r\nAccept: */*\r\n\r\n"""
            )
            print("Data sent")
            buffer = b""
            while not buffer.endswith(b"\r\n\r\n"):
                print(f"Requesting up to {bufsize} bytes (current response size: {len(buffer)})")
                data = await socket.receive(bufsize)
                print(f"Received {len(data)} bytes")
                if data:
                    buffer += data
                else:
                    print("Received empty stream, closing connection")
                    break
    print(f"Request has{' not' if not p.timed_out else ''} timed out!")
    if buffer:
        data = buffer.decode().split("\r\n")
        print(f"HTTP Response below {'(might be incomplete)' if p.timed_out else ''}")
        _print(f"Response: {data[0]}")
        _print("Headers:")
        content = False
        for i, element in enumerate(data):
            if i == 0:
                continue
            else:
                if not element.strip() and not content:
                    # This only works because google sends a newline
                    # before the content
                    sys.stdout.write("\nContent:")
                    content = True
                if not content:
                    _print(f"\t{element}")
                else:
                    for line in element.split("\n"):
                        _print(f"\t{line}")


giambio.run(test, "google.com", 443, 256, debugger=())
