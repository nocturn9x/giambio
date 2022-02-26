import giambio
from debugger import Debugger


async def producer(q: giambio.Queue, n: int):
    for i in range(n):
        await q.put(i)
        print(f"Produced {i}")
    await q.put(None)
    print("Producer done")


async def consumer(q: giambio.Queue):
    while True:
        item = await q.get()
        if item is None:
            print("Consumer done")
            break
        print(f"Consumed {item}")
        await giambio.sleep(1)


async def main(q: giambio.Queue, n: int):
    async with giambio.create_pool() as pool:
        await pool.spawn(producer, q, n)
        await pool.spawn(consumer, q)
    


queue = giambio.Queue(2)
giambio.run(main, queue, 5, debugger=())
