import giambio
from debugger import Debugger


async def child():
    print("[child] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child] Had a nice nap!")
    raise TypeError("rip")


async def child1():
    print("[child 1] Child spawned!! Sleeping for 8 seconds")
    await giambio.sleep(8)
    print("[child 1] Had a nice nap!")
    # raise TypeError("rip")


async def main():
    start = giambio.clock()
    try:
        async with giambio.create_pool() as pool:
            await pool.spawn(child)
            await pool.spawn(child1)
            print("[main] Children spawned, awaiting completion")
    except Exception as error:
        # Because exceptions just *work*!
        print(f"[main] Exception from child caught! {repr(error)}")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())
