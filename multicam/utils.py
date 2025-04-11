"""
Monkey-patch multiprocessing.resource_tracker so SharedMemory won't be tracked
More details at: https://bugs.python.org/issue38119

Below a link is a more detailed version of this patch:
https://github.com/python/cpython/pull/15989
https://github.com/python/cpython/pull/21516
"""

# mypy: ignore-errors

from multiprocessing import resource_tracker


def remove_shm_from_resource_tracker() -> None:
    """
    Disables resource tracking for the Shared Memory for the current process.
    When we use this function, it overrides the current implementation of resource-tracker
    register and unregister functions. That ensures the resource tracker does not track the
    shared memory objects. Without this patch, there will be a memory leak as
    the resource tracker for each process stores the name of the shared memory with itself
    such that it can destroy it later.

    Since the resource tracker cleans this memory at the end of the program, this
    list of names keeps growing to a point that it takes up the entire memory space until the docker
    container crashes and exits.

    This behavior of resource tracker happens only in multiprocessing code.
    It is better if we go with the usual behavior of python code and not use this patch code if we
    are not using a multiprocessing code.

    Caution:
        1. This should be used in multiprocessing code only.
        2. When you call this function, the resource tracker is disabled only for that process.
        3. If you run it once, then the resources are no more tracked.
        4. Be careful if you are using semaphores.
        If you disable resource tracking and due to some reason, not release the semaphores back.
        Then this might use up all the semaphores of the device.
        As the number of semaphores is limited, so it might take up all resources.
        You can know how many semaphores are in the system by the following command:
        $/> ipcs -ls
            ------ Semaphore Limits --------
            max number of arrays = 32000
            max semaphores per array = 32000
            max semaphores system-wide = 1024000000
            max ops per semop call = 500
            semaphore max value = 32767
        Semaphores are used by the OS related operations too, so it is a limited resources and thus
        used wisely.If we accidentally use all the semaphores then the OS might be blocked or wait
        state forever.

        The safety net is docker container. Since any resource leak stays inside docker container,
        and it does not reflect on the edge device. Restarting docker container solves the memory problem.

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
