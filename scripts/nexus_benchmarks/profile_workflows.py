"""Reusable profiling for synchronous functions and fixed local Dask workers.

Requires psutil; crossmatch additionally requires lsdb, astropy, and Dask.

Notebook usage (place this module beside your notebook):

    from dask.distributed import Client, LocalCluster
    from profile_workflows import crossmatch, profile_resources

    with LocalCluster(
        n_workers=8, threads_per_worker=1, memory_limit=None,
    ) as cluster, Client(cluster) as client:
        xmatch, metrics = crossmatch(nrows=10_000, client=client)
    print(metrics)

For another synchronous function:

    @profile_resources(sample_seconds=0.05)
    def my_calculation(data):
        return data.sum()

    result, metrics = my_calculation(data)

To include Dask workers, give the decorated function an explicit ``client``
parameter and use that client for its computation. Return the computed result,
not a lazy Dask collection or futures. Workers must already be running, must
remain alive until profiling finishes, and must not adapt/scale during the run.
CPU totals deduplicate shared processes; calling-process and worker subtotals
overlap if workers share the calling process, so do not sum those subtotals.

The crossmatch measurement includes catalog opening, graph construction, data
loading, computation, and result transfer, but excludes cluster startup/shutdown.
No cache clearing or repeated execution happens automatically. For independent
fresh-process trials, restart the kernel and workers between calls; OS and
remote-service caches may still be warm. RSS peak minus baseline is an observed
resident-memory increase, not a count of total allocations. Sampling is not
atomic across processes and can miss spikes shorter than the interval.
"""

import inspect
import math
import threading
import time
from functools import wraps

import psutil

import yaml


def _process_identity():
    process = psutil.Process()
    return process.pid, process.create_time()


def profile_resources(*, sample_seconds=0.05):
    """Return a decorator that returns (function_result, metrics).

    Measures the calling process and, if the function receives a non-None
    argument named ``client``, that distributed Client's fixed local workers.
    Create the cluster before calling the function and close it afterward.
    Without a client, only the calling process and its threads are measured.

    Functions must finish their work before returning: asynchronous functions,
    generators, lazy results, and background work are not supported. Exceptions
    propagate; failed or invalid measurements do not return metrics.

    CPU is user + system process time, including native threads. Memory is
    sampled aggregate RSS, not allocations; shared pages may be double-counted.
    Worker subprocesses and nanny processes are excluded. Use an otherwise idle
    process/cluster; unrelated activity and profiling overhead are included.
    """
    if not math.isfinite(sample_seconds) or sample_seconds <= 0:
        raise ValueError("sample_seconds must be finite and positive.")

    def decorate(function):
        if (
            inspect.iscoroutinefunction(function)
            or inspect.isgeneratorfunction(function)
            or inspect.isasyncgenfunction(function)
        ):
            raise TypeError("Only synchronous, non-generator functions are supported.")
        signature = inspect.signature(function)

        @wraps(function)
        def measured(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            client = bound.arguments.get("client")
            kernel = psutil.Process()
            kernel_identity = _process_identity()
            workers_before = {}
            if client is not None:
                workers_before = client.run(_process_identity)
                if not workers_before:
                    raise RuntimeError("No Dask workers are available.")
                local_identities = {
                    (process.pid, process.create_time())
                    for process in [kernel, *kernel.children(recursive=True)]
                }
                if not set(workers_before.values()).issubset(local_identities):
                    raise RuntimeError(
                        "Workers must be in the calling process's local process "
                        "tree. Remote/external clusters require worker-side profiling."
                    )

            worker_identities = set(workers_before.values())
            identities = {kernel_identity, *worker_identities}
            processes = {
                identity: psutil.Process(identity[0]) for identity in identities
            }

            def snapshot():
                cpu = {}
                rss = 0
                for identity, process in processes.items():
                    if process.create_time() != identity[1]:
                        raise RuntimeError("A monitored process was replaced.")
                    times = process.cpu_times()
                    cpu[identity] = times.user + times.system
                    rss += process.memory_info().rss
                return cpu, rss

            cpu_before, baseline = snapshot()
            peak = [baseline]
            errors = []
            stop = threading.Event()

            def sample_memory():
                try:
                    while not stop.wait(sample_seconds):
                        _, rss = snapshot()
                        peak[0] = max(peak[0], rss)
                except Exception as error:
                    # Propagate thread failures to the caller, not partial metrics.
                    errors.append(error)
                    stop.set()

            sampler = threading.Thread(target=sample_memory, daemon=True)
            sampler.start()
            start = time.perf_counter()
            try:
                result = function(*args, **kwargs)
                wall_seconds = time.perf_counter() - start
                cpu_after, final = snapshot()
            finally:
                stop.set()
                sampler.join()

            if errors:
                raise RuntimeError(
                    "Memory sampling failed; discard this run."
                ) from errors[0]
            if client is not None and client.run(_process_identity) != workers_before:
                raise RuntimeError(
                    "Workers changed during measurement; discard this run. "
                    "Disable adaptive scaling and retry."
                )
            cpu_deltas = {
                identity: cpu_after[identity] - cpu_before[identity]
                for identity in identities
            }
            if any(delta < 0 for delta in cpu_deltas.values()):
                raise RuntimeError("CPU counters decreased; discard this run.")

            peak[0] = max(peak[0], final)
            gb = 1000**3
            metrics = {
                "function": function.__name__,
                "wall_seconds": wall_seconds,
                "cpu_hours": sum(cpu_deltas.values()) / 3600,
                "calling_process_cpu_hours": cpu_deltas[kernel_identity] / 3600,
                "worker_cpu_hours": sum(
                    cpu_deltas[identity] for identity in worker_identities
                ) / 3600,
                "baseline_rss_gb": baseline / gb ,
                "sampled_peak_rss_gb": peak[0] / gb,
                "peak_increase_gb": (peak[0] - baseline) / gb,
                "final_rss_gb": final / gb,
                "monitored_processes": len(identities),
                "sample_seconds": sample_seconds,
            }
            return result, metrics

        return measured

    return decorate


def save_results(file, testname, description, results):

    with open(file, 'a+') as outfile:
        outfile.seek(0)

        current_data = yaml.safe_load(outfile)

        try:
            if testname in current_data.keys():
                current_data[testname]['results'].append(results)
            else:
                current_data[testname] = {
                    'description': description,
                    'results': [results]
                }
        except AttributeError:
            current_data = {
                testname: {
                    'description': description,
                    'results': [results]
                }
            }
    
        outfile.seek(0)
        outfile.truncate()
        yaml.safe_dump(current_data, outfile, sort_keys=False)