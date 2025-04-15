"""
Monkey-patch multiprocessing.resource_tracker so SharedMemory won't be tracked
More details at:
https://bugs.python.org/issue38119
https://github.com/python/cpython/issues/82300

Below a link is a more detailed version of this patch:
https://github.com/python/cpython/pull/15989
https://github.com/python/cpython/pull/21516
"""

# mypy: ignore-errors

from multiprocessing import resource_tracker


def remove_shm_from_resource_tracker() -> None:
    """
    Patches the resource tracker to prevent memory leaks when using shared memory in multiprocessing.

    This function disables resource tracking for shared memory objects only in the process where it is called.
    It overrides the default implementation of `register` and `unregister` in the `multiprocessing.resource_tracker`,
    ensuring the resource tracker does not track shared memory objects in that process.

    ### Why this patch is necessary:
    In this scenario, shared memory is created in one process and released in another.
    However, the resource tracker maintains a dictionary of shared memory names until they're explicitly released.
    If a process that creates shared memory never releases it, the name persists in the dictionary,
    causing the tracker’s internal data structure to grow indefinitely. Over time, this leads to a memory leak,
    eventually consuming all available memory and crashing the program.

    ### Usage:
    - Call this function only in multiprocessing classes or functions that use shared memory.
    - Once called, the resource tracker will no longer track shared memory resources in that process.

    ### Caution:
    1. Use only in multiprocessing contexts.
    2. The patch is process-local, it affects only the process where it is applied.
    3. Once tracking is disabled, it is your responsibility to manually manage and clean up shared memory.
    4. Be especially careful when using semaphores. If the tracker is disabled, and they are not properly released,
       you may exhaust the system’s semaphore limits, which could block the OS or leave it in a wait state.

    You can inspect system semaphore limits with:
    $/> ipcs -ls

    ### Docker Consideration:
    If running inside a Docker container, resource leaks caused by this patch will remain isolated to the container.
    Restarting the container will clear any leaked resources.
    """

    def fix_register(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.register(name=name, rtype=rtype)

    def fix_unregister(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.unregister(name=name, rtype=rtype)

    # Swapping the fixes.
    resource_tracker.register = fix_register
    resource_tracker.unregister = fix_unregister

    if "shared_memory" in resource_tracker._CLEANUP_FUNCS:
        del resource_tracker._CLEANUP_FUNCS["shared_memory"]
