import giambio
from debugger import Debugger


async def child(name: int):
    print(f"[child {name}] Child spawned!! Sleeping for {name} seconds")
    await giambio.sleep(name)
    print(f"[child {name}] Had a nice nap!")


async def worker(coro, *args):
    try:
        async with giambio.with_timeout(10):
            await coro(*args)
    except giambio.exceptions.TooSlowError:
        return True
    return False


async def main():
    start = giambio.clock()
    async with giambio.skip_after(10) as pool:
        t = await pool.spawn(worker, child, 7)
        await giambio.sleep(2)
        t2 = await pool.spawn(worker, child, 15)
    if any([await t.join(), await t2.join()]):
        print("[main] One or more children have timed out!")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())