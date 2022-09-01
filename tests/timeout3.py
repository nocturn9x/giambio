import giambio
from debugger import Debugger


async def child(name: int):
    print(f"[child {name}] Child spawned!! Sleeping for {name} seconds")
    await giambio.sleep(name)
    print(f"[child {name}] Had a nice nap!")
    return name


async def worker(coro, *args):
    try:
        async with giambio.with_timeout(2):
            await coro(*args)
    except giambio.exceptions.TooSlowError:
        return True
    return False


async def main():
    start = giambio.clock()
    try:
        async with giambio.with_timeout(5) as pool:
            task = await pool.spawn(worker, child, 5)
            print(f"[main] Child has returned: {await task.join()}")
            print(f"[main] Sleeping")
            await giambio.sleep(500)   # This will trigger the timeout
    except giambio.exceptions.TooSlowError:
        print("[main] One or more children have timed out!")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")
    return 12


if __name__ == "__main__":
    giambio.run(main, debugger=Debugger())
