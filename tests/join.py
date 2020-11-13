import giambio


# A test to see if tasks are properly joined


async def child(sleep: int):
    start = giambio.clock()
    print(f"[child] Gonna sleep for {sleep} seconds!")
    await giambio.sleep(sleep)
    end = giambio.clock() - start
    print(f"[child] I woke up! Slept for {end} seconds")


async def main():
    print("[parent] Spawning child")
    task = giambio.spawn(child, 5)
    start = giambio.clock()
    print("[parent] Child spawned, awaiting completion")
    await task.join()
    end = giambio.clock() - start
    print(f"[parent] Child exited in {end} seconds")


if __name__ == "__main__":
    giambio.run(main)
