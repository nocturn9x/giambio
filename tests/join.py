import giambio


async def child(sleep: int, ident: int):
    start = giambio.clock()   # This returns the current time from giambio's perspective
    print(f"[child {ident}] Gonna sleep for {sleep} seconds!")
    await giambio.sleep(sleep)
    end = giambio.clock() - start
    print(f"[child {ident}] I woke up! Slept for {end} seconds")


async def main():
    print("[parent] Spawning children")
    task = giambio.spawn(child, 1, 1)   # We spawn a child task
    task2 = giambio.spawn(child, 2, 2)  # and why not? another one!
    start = giambio.clock()
    print("[parent] Children spawned, awaiting completion")
    await task.join()
    await task2.join()
    end = giambio.clock() - start
    print(f"[parent] Execution terminated in {end} seconds")


if __name__ == "__main__":
    giambio.run(main)    # Start the async context