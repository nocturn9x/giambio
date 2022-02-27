import random
import string
import giambio
from debugger import Debugger


async def task(c: giambio.MemoryChannel, name: str):
    while True:
        if await c.pending():
            print(f"[{name}] Received {await c.read()!r}")
        else:
            data = "".join(random.choice(string.ascii_letters) for _ in range(8))
            print(f"[{name}] Sending {data!r}")
            await c.write(data)
        await giambio.sleep(1)


async def main(channel: giambio.MemoryChannel, delay: int):
    print(f"[main] Spawning workers, exiting in {delay} seconds")
    async with giambio.skip_after(delay) as pool:
        await pool.spawn(task, channel, "one")
        await pool.spawn(task, channel, "two")
        await pool.spawn(task, channel, "three")
    await channel.close()
    print(f"[main] Operation complete, channel closed")
    if await channel.pending():
        print(f"[main] Channel has {len(channel.buffer)} leftover packet{'s' if len(channel.buffer) > 1 else ''} of data, clearing it")
        while await channel.pending():
            print(f"[main] Cleared {await channel.read()!r}")


channel = giambio.MemoryChannel()
giambio.run(main, channel, 6, debugger=())