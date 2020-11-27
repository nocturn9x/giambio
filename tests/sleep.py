import giambio


class Debugger(giambio.debug.BaseDebugger):
    """
    A simple debugger for this test
    """

    def on_start(self):
        print("## Started running")

    def on_exit(self):
        print("## Finished running")

    def on_task_schedule(self, task, delay: int):
        print(f">> A task named '{task.name}' was scheduled to run in {delay:.2f} seconds")

    def on_task_spawn(self, task):
        print(f">> A task named '{task.name}' was spawned")

    def on_task_exit(self, task):
        print(f"<< Task '{task.name}' exited")

    def before_task_step(self, task):
        print(f"-> About to run a step for '{task.name}'")

    def after_task_step(self, task):
        print(f"<- Ran a step for '{task.name}'")

    def before_sleep(self, task, seconds):
        print(f"# About to put '{task.name}' to sleep for {seconds:.2f} seconds")
  
    def after_sleep(self, task, seconds):
        print(f"# Task '{task.name}' slept for {seconds:.2f} seconds")

    def before_io(self, timeout):
        print(f"!! About to check for I/O for up to {timeout:.2f} seconds")

    def after_io(self, timeout):
        print(f"!! Done I/O check (waited for {timeout:.2f} seconds)")

    def before_cancel(self, task):
        print(f"// About to cancel '{task.name}'")

    def after_cancel(self, task):
        print(f"// Cancelled '{task.name}'")


async def child():
    print("[child] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child] Had a nice nap!")
    # raise TypeError("rip")  # Uncomment this line and watch the exception magically propagate!


async def child1():
    print("[child 1] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child 1] Had a nice nap!")


async def main():
    start = giambio.clock()
    try:
        async with giambio.create_pool() as pool:
            pool.spawn(child)
            pool.spawn(child1)
            print("[main] Children spawned, awaiting completion")
    except Exception as error:
        # Because exceptions just *work*!
        print(f"[main] Exception from child caught! {repr(error)}")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main)
