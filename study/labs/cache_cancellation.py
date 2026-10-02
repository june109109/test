"""Local cache process boundaries and cancellation of a running thread."""
import argparse
import asyncio
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import json
import multiprocessing
from pathlib import Path
import tempfile
import threading


@lru_cache(maxsize=16)
def cached_read(path):
    return Path(path).read_text()


def read(path, clear=False):
    if clear:cached_read.cache_clear()
    return cached_read(path)


def cache_case():
    with tempfile.TemporaryDirectory(prefix='study-cache-') as d:
        p=Path(d)/'source.txt';p.write_text('version-1')
        ctx=multiprocessing.get_context('spawn')
        with ProcessPoolExecutor(max_workers=1,mp_context=ctx) as a, ProcessPoolExecutor(max_workers=1,mp_context=ctx) as b:
            first=[a.submit(read,str(p)).result(timeout=10),b.submit(read,str(p)).result(timeout=10)]
            p.write_text('version-2')  # all reads complete before this write
            changed=[a.submit(read,str(p),True).result(timeout=10),b.submit(read,str(p)).result(timeout=10)]
            assert first==['version-1','version-1'] and changed==['version-2','version-1']
            final=b.submit(read,str(p),True).result(timeout=10)
            assert final=='version-2'
    return {'initial':first,'only_A_invalidated':changed,'B_after_invalidation':final,
            'source':'shared temporary file, NOT Redis'}


async def cancellation_case():
    loop=asyncio.get_running_loop()
    started,finished=asyncio.Event(),asyncio.Event()
    release=threading.Event()
    running=threading.Event()
    def blocking():
        running.set();loop.call_soon_threadsafe(started.set)
        try:
            if not release.wait(timeout=3):raise TimeoutError('test cleanup did not release thread')
        finally:
            running.clear();loop.call_soon_threadsafe(finished.set)
    task=asyncio.create_task(asyncio.to_thread(blocking))
    try:
        await asyncio.wait_for(started.wait(),timeout=2)
        timed_out=False
        try:
            async with asyncio.timeout(0.02):await task
        except TimeoutError:timed_out=True
        alive=running.is_set()
        assert timed_out and task.cancelled() and alive
    finally:
        release.set()
        await asyncio.wait_for(finished.wait(),timeout=2)
    assert not running.is_set()
    return {'timeout_observed':timed_out,'async_task_cancelled':task.cancelled(),
            'blocking_thread_still_running_after_timeout':alive,'thread_finished_after_explicit_release':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output path')
    result={'cache':cache_case(),'cancellation':asyncio.run(cancellation_case())}
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
