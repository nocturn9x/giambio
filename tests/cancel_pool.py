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


async def child2():
    print("[child 2] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child 2] Had a nice nap!")


async def main():
    start = giambio.clock()
    async with giambio.create_pool() as pool:
        pool.spawn(child)
        pool.spawn(child1)
        # async with giambio.create_pool() as a_pool:
            # a_pool.spawn(child2)
        await pool.cancel()  # This cancels the *whole* block
        print("[main] Children spawned, awaiting completion")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=Debugger())
