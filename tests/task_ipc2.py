## Simple task IPC using giambio's NetworkChannel class
import random
import string
import giambio
from debugger import Debugger


async def task(c: giambio.NetworkChannel, name: str):
    while True:
        if await c.pending():
            print(f"[{name}] Received {(await c.read(8)).decode()!r}")
        else:
            data = "".join(random.choice(string.ascii_letters) for _ in range(8))
            print(f"[{name}] Sending {data!r}")
            await c.write(data.encode())
            await giambio.sleep(1)


async def main(channel: giambio.NetworkChannel, delay: int):
    print(f"[main] Spawning workers, exiting in {delay} seconds")
    async with giambio.skip_after(delay) as pool:
        await pool.spawn(task, channel, "one")
        await pool.spawn(task, channel, "two")
    await channel.close()
    print(f"[main] Operation complete, channel closed")
    if await channel.pending():
        print(f"[main] Channel has leftover data, clearing it")
        while await channel.pending():
            print(f"[main] Cleared {await channel.read(1)!r}")


channel = giambio.NetworkChannel()
giambio.run(main, channel, 4, debugger=())