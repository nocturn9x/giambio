import giambio
from debugger import Debugger


async def child(name: int):
    print(f"[child {name}] Child spawned!! Sleeping for {name} seconds")
    await giambio.sleep(name)
    print(f"[child {name}] Had a nice nap!")
    return name


async def main():
    start = giambio.clock()
    try:
        async with giambio.with_timeout(5) as pool:
            task = await pool.spawn(child, 2)
            print(f"Child has returned: {await task.join()}")
            await giambio.sleep(5)   # This will trigger the timeout
    except giambio.exceptions.TooSlowError:
        print("[main] One or more children have timed out!")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")
    return 12


if __name__ == "__main__":
    giambio.run(main, debugger=())
