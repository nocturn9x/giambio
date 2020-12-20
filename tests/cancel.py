import giambio
from debugger import Debugger


async def child():
    print("[child] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child] Had a nice nap!")


async def child1():
    print("[child 1] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child 1] Had a nice nap!")


async def main():
    start = giambio.clock()
    async with giambio.create_pool() as pool:
        pool.spawn(child)   # If you comment this line, the pool will exit immediately!
        task = pool.spawn(child1)
        await task.cancel()
        print("[main] Children spawned, awaiting completion")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=Debugger())
