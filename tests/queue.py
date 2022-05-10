import giambio
from debugger import Debugger


async def producer(q: giambio.Queue, n: int):
    for i in range(n):
        # This will wait until the
        # queue is emptied by the
        # consumer
        await q.put(i)
        print(f"Produced {i}")
    await q.put(None)
    print("Producer done")


async def consumer(q: giambio.Queue):
    while True:
        # Hangs until there is 
        # something on the queue
        item = await q.get()
        if item is None:
            print("Consumer done")
            break
        print(f"Consumed {item}")
        # Simulates some work so the
        # producer waits before putting
        # the next value
        await giambio.sleep(1)


async def main(q: giambio.Queue, n: int):
    async with giambio.create_pool() as pool:
        await pool.spawn(producer, q, n)
        await pool.spawn(consumer, q)
    print("Bye!")


queue = giambio.Queue(1)  # Queue has size limit of 1
giambio.run(main, queue, 5, debugger=())
