from debugger import Debugger
import giambio


async def child(start: int, limit: int, q: giambio.Queue, l: giambio.Lock):
    async with l:   # If you comment this line, the resulting queue will
                    # be all mixed up!
        # Locked! If any other task
        # tries to acquire the lock,
        # they'll wait for us to finish
        while start <= limit:
            print(f"[locked ({limit})] {start}")
            await q.put(start)
            start += 1
            await giambio.sleep(1)


async def other(stop: int):
    # Other tasks are unaffected
    # by the lock if they don't
    # acquire it
    n = stop
    while n:
        print(f"[unlocked ({stop})] {n}")
        n -= 1
        await giambio.sleep(1)
    

async def main():
    queue = giambio.Queue()
    lock = giambio.Lock()
    async with giambio.create_pool() as pool:
        await pool.spawn(child, 1, 5, queue, lock)
        await pool.spawn(child, 6, 10, queue, lock)
        await pool.spawn(other, 10)
        await pool.spawn(other, 5)
    print(f"Result: {queue}")   # Queue is ordered!
    print("[main] Done")


giambio.run(main, debugger=())