import giambio
from debugger import Debugger


# TODO: How to create a race condition of 2 exceptions at the same time?

async def child():
    print("[child] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child] Had a nice nap!")


async def child1():
    print("[child 1] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child 1] Had a nice nap!")
    raise Exception("bruh")


async def main():
    start = giambio.clock()
    try:
        async with giambio.create_pool() as pool:
            pool.spawn(child)
            pool.spawn(child1)
            print("[main] Children spawned, awaiting completion")
    except Exception as error:
        # Because exceptions just *work*!
        print(f"[main] Exception from child caught! {repr(error)}")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())
