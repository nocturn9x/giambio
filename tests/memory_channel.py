import giambio
from debugger import Debugger


async def sender(c: giambio.MemoryChannel, n: int):
    for i in range(n):
        await c.write(str(i))
        print(f"Sent {i}")
    await c.close()
    print("Sender done")


async def receiver(c: giambio.MemoryChannel):
    while True:
        if not await c.pending() and c.closed:
            print("Receiver done")
            break
        item = await c.read()
        print(f"Received {item}")
        await giambio.sleep(1)


async def main(channel: giambio.MemoryChannel, n: int):
    print("Starting sender and receiver")
    async with giambio.create_pool() as pool:
        await pool.spawn(sender, channel, n)
        await pool.spawn(receiver, channel)
    print("All done!")


giambio.run(main, giambio.MemoryChannel(2), 5, debugger=())  # 2 is the max size of the channel
