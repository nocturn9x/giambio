import giambio
from debugger import Debugger


async def child():
    print("[child] Child spawned!! Sleeping for 5 seconds")
    await giambio.sleep(5)
    print("[child] Had a nice nap!")


async def child1():
    print("[child 1] Child spawned!! Sleeping for 10 seconds")
    await giambio.sleep(10)
    print("[child 1] Had a nice nap!")


async def main():
    start = giambio.clock()
    try:
        async with giambio.with_timeout(6) as pool:
            # TODO: We need to consider the inner part of
            #  the with block as an implicit task, otherwise
            #  timeouts and cancellations won't work properly!
            pool.spawn(child)  # This will complete
            pool.spawn(child1)  # This will not
            print("[main] Children spawned, awaiting completion")
    except giambio.exceptions.TooSlowError:
        print("[main] One or more children have timed out!")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())
