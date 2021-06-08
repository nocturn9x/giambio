import giambio
from debugger import Debugger


async def child(name: int):
    print(f"[child {name}] Child spawned!! Sleeping for {name} seconds")
    await giambio.sleep(name)
    print(f"[child {name}] Had a nice nap!")


async def main():
    start = giambio.clock()
    try:
        async with giambio.with_timeout(10) as pool:
            await pool.spawn(child, 7)  # This will complete
            await child(20)  # TODO: Broken
    except giambio.exceptions.TooSlowError:
        print("[main] One or more children have timed out!")
    print(
        f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds"
    )


if __name__ == "__main__":
    giambio.run(main, debugger=())
