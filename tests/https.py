import giambio
import socket as sock
import ssl


async def test(host: str, port: int):
    socket = giambio.socket.wrap_socket(ssl.wrap_socket(sock.socket()))
    await socket.connect((host, port))
    async with socket:
        await socket.send_all(b"""GET / HTTP/1.1\r
                                  Host: google.com\r
                                  User-Agent: owo\r
                                  Accept: text/html\r
                                  Connection: keep-alive\r\n\r\n""")
        buffer = b""
        while True:
           data = await socket.receive(4096)
           if data:
               buffer += data
           else:
               break
        print("\n".join(buffer.decode().split("\r\n")))


giambio.run(test, "google.com", 443)
