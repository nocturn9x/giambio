import giambio


# A test for events


async def child(ev: giambio.Event, pause: int):
    print("[child] Child is alive! Going to wait until notified")
    start_total = giambio.clock()
    await ev.wait()
    end_pause = giambio.clock() - start_total
    print(f"[child] Parent set the event, exiting in {pause} seconds")
    start_sleep = giambio.clock()
    await giambio.sleep(pause)
    end_sleep = giambio.clock() - start_sleep
    end_total = giambio.clock() - start_total
    print(f"[child] Done! Slept for {end_total} seconds total ({end_pause} paused, {end_sleep} sleeping), nice nap!")


async def parent(pause: int = 1):
    async with giambio.create_pool() as pool:
        event = giambio.Event()
        print("[parent] Spawning child task")
        pool.spawn(child, event, pause + 2)
        start = giambio.clock()
        print(f"[parent] Sleeping {pause} second(s) before setting the event")
        await giambio.sleep(pause)
        await event.trigger()
        print("[parent] Event set, awaiting child")
    end = giambio.clock() - start
    print(f"[parent] Child exited in {end} seconds")


if __name__ == "__main__":
    giambio.run(parent, 3)
