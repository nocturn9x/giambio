from debugger import Debugger
import email
from io import StringIO
import giambio
import socket as sock
import ssl


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
                                           server_hostname=host)
                                       )
    print(f"Attempting a connection to {host}:{port}")
    await socket.connect((host, port))
    print("Connected")
    async with giambio.skip_after(2) as p:
        print(f"Pool with {p.timeout - giambio.clock():.2f} seconds timeout created")
        async with socket:
            print("Entered socket context manager, sending request data")
            await socket.send_all(b"""GET / HTTP/1.1\r\nHost: google.com\r\nUser-Agent: owo\r\nAccept: text/html\r\nConnection: keep-alive\r\nAccept: */*\r\n\r\n""")
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
        print(f"HTTP Response below {'(might be incomplete)' if p.timed_out else ''}\n")
        print("\n".join(buffer.decode().split("\r\n")))


giambio.run(test, "google.com", 443, debugger=())

