"""Bounded context propagation, event-loop lag and AnyIO limiter experiments."""
import argparse
import asyncio
import contextvars
import io
import json
import logging
from pathlib import Path
import statistics
import time
import tracemalloc
import anyio

request_id=contextvars.ContextVar('request_id',default=None)


class JSONFormatter(logging.Formatter):
    def format(self,record):
        return json.dumps({'level':record.levelname,'event':record.getMessage(),'request_id':request_id.get()})


async def contexts():
    sink=io.StringIO();handler=logging.StreamHandler(sink);handler.setFormatter(JSONFormatter())
    logger=logging.getLogger('study-observe');logger.handlers=[handler];logger.setLevel(logging.INFO);logger.propagate=False
    async def request(name):
        token=request_id.set(name)
        try:
            await asyncio.sleep(0)
            logger.info('request_observed')
            return {'task':request_id.get(),'to_thread':await asyncio.to_thread(request_id.get),
                    'run_in_executor':await asyncio.get_running_loop().run_in_executor(None,request_id.get)}
        finally:request_id.reset(token)
    try:
        values=await asyncio.gather(request('request-A'),request('request-B'))
        logs=[json.loads(line) for line in sink.getvalue().splitlines()]
        assert values==[{'task':n,'to_thread':n,'run_in_executor':None} for n in ['request-A','request-B']]
        assert sorted(x['request_id'] for x in logs)==['request-A','request-B'] and request_id.get() is None
        return {'values':values,'logs':logs,'parent_context_after_reset':request_id.get()}
    finally:logger.removeHandler(handler);handler.close()


async def lag_case(block):
    samples=[];stop=False
    async def heartbeat():
        previous=time.perf_counter()
        while not stop:
            await asyncio.sleep(0.005)
            now=time.perf_counter();samples.append(max(0,now-previous-0.005));previous=now
    sampler=asyncio.create_task(heartbeat())
    try:
        await asyncio.sleep(0.02)
        if block:time.sleep(0.06)
        else:await asyncio.to_thread(time.sleep,0.06)
        await asyncio.sleep(0.02)
    finally:stop=True;await sampler
    return {'samples_seconds':samples,'max_lag_seconds':max(samples),'median_lag_seconds':statistics.median(samples)}


async def pool_case():
    limiter=anyio.to_thread.current_default_thread_limiter();old=limiter.total_tokens
    limiter.total_tokens=2;observed=[];done=0
    async def work():
        nonlocal done
        await anyio.to_thread.run_sync(time.sleep,0.03);done+=1
    async def sample():
        while done<6:
            observed.append(limiter.borrowed_tokens);await asyncio.sleep(0.002)
    try:
        started=time.perf_counter()
        await asyncio.gather(sample(),*(work() for _ in range(6)))
        assert done==6 and max(observed)==2
        return {'configured_tokens':2,'requests':6,'completed':done,'peak_borrowed_tokens':max(observed),
                'duration_seconds':time.perf_counter()-started,'borrowed_samples':observed}
    finally:limiter.total_tokens=old


def allocations():
    tracemalloc.start()
    try:
        before=tracemalloc.take_snapshot()
        retained=[bytearray(1024) for _ in range(1000)]
        after=tracemalloc.take_snapshot()
        delta=sum(stat.size_diff for stat in after.compare_to(before,'lineno'))
        assert delta>=1024*1000 and len(retained)==1000
        return {'retained_objects':1000,'payload_bytes_each':1024,'traced_size_delta_bytes':delta,
                'scope':'Python-traced allocations, not RSS or a native allocation inventory'}
    finally:tracemalloc.stop()


async def run():
    c=await contexts();blocked=await lag_case(True);offloaded=await lag_case(False);pool=await pool_case()
    assert blocked['max_lag_seconds']>=0.04
    return {'contexts':c,'lag':{'blocking':blocked,'offloaded':offloaded},'anyio_pool':pool,'allocations':allocations(),
            'scope':'synthetic in-process probes; no Prometheus server, Grafana or OpenTelemetry collector'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Choose new output path')
    result=asyncio.run(run())
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'context_checks':result['contexts'],'max_lag':{k:v['max_lag_seconds'] for k,v in result['lag'].items()},
                      'pool_peak':result['anyio_pool']['peak_borrowed_tokens'],'allocations':result['allocations']},indent=2))
