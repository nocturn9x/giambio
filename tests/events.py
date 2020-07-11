import giambio


async def child(notifier: giambio.Event, reply: giambio.Event, pause: int):
    print("[child] Child is alive! Going to sleep until notified")
    notification = await notifier.pause()
    print(f"[child] Parent said: '{notification}', replying in {pause} seconds")
    await giambio.sleep(pause)
    print("[child] Replying to parent")
    await reply.set("Hi daddy!")


async def parent(pause: int = 1):
    event = giambio.Event()
    reply = giambio.Event()
    print("[parent] Spawning child task")
    task = scheduler.create_task(child(event, reply, pause))
    print(f"[parent] Sleeping {pause} second(s) before setting the event")
    await giambio.sleep(pause)
    await event.set("Hi, my child")
    print("[parent] Event set, awaiting reply")
    reply = await reply.pause()
    print(f"[parent] Child replied: '{reply}'")
    await task.join()
    print("[parent] Child exited")


if __name__ == "__main__":
    scheduler = giambio.AsyncScheduler()
    scheduler.start(parent(5))
