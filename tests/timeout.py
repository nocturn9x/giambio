import giambio
from debugger import Debugger


async def child(name: int):
    print(f"[child {name}] Child spawned!! Sleeping for {name} seconds")
    await giambio.sleep(name)
    print(f"[child {name}] Had a nice nap!")


async def main():
    start = giambio.clock()
    try:
        async with giambio.with_timeout(6) as pool:
            # TODO: We need to consider the inner part of
            #  the with block as an implicit task, otherwise
            #  timeouts and cancellations won't work with await fn()!
            pool.spawn(child, 5)  # This will complete
            pool.spawn(child, 10)  # This will not
            print("[main] Children spawned, awaiting completion")
    except giambio.exceptions.TooSlowError:
        print("[main] One or more children have timed out!")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())
