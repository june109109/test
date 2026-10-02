"""Finite Linux loopback closed-workload lab; never targets external services."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import threading
import time


def percentile(xs,p):
    return sorted(xs)[max(0,math.ceil(len(xs)*p)-1)] if xs else None


def cpu_seconds(pid):
    parts=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return (int(parts[11])+int(parts[12]))/os.sysconf('SC_CLK_TCK')


def stage(port,pid,route,users,seconds):
    barrier=threading.Barrier(users+1);end=[None];samples=[];lock=threading.Lock()
    def worker():
        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
        local=[]
        try:
            barrier.wait(timeout=10)
            while time.perf_counter()<end[0]:
                started=time.perf_counter();ok=False
                try:
                    conn.request('GET','/'+route)
                    response=conn.getresponse();body=response.read()
                    ok=response.status==200 and json.loads(body).get('ok') is True
                except (OSError,http.client.HTTPException,ValueError):
                    conn.close();conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
                local.append((time.perf_counter()-started,ok))
        finally:
            conn.close()
            with lock:samples.extend(local)
    with ThreadPoolExecutor(max_workers=users) as pool:
        futures=[pool.submit(worker) for _ in range(users)]
        cpu_before=cpu_seconds(pid);started=time.perf_counter();end[0]=started+seconds
        barrier.wait(timeout=10)
        for f in futures:f.result(timeout=seconds+10)
        elapsed=time.perf_counter()-started;cpu=cpu_seconds(pid)-cpu_before
    successful=[t for t,ok in samples if ok];all_times=[t for t,_ in samples]
    result={'route':route,'vusers':users,'scheduled_seconds':seconds,'elapsed_with_drain_seconds':elapsed,
            'attempts':len(samples),'successes':len(successful),'errors':len(samples)-len(successful),
            'successful_rps':len(successful)/elapsed,'server_cpu_seconds':cpu,
            'server_one_core_cpu_fraction':cpu/elapsed,
            'latency_all_ms':{name:percentile(all_times,p)*1000 for name,p in [('p50',.5),('p95',.95),('p99',.99)]},
            'latency_success_ms':{name:percentile(successful,p)*1000 if successful else None for name,p in [('p50',.5),('p95',.95),('p99',.99)]},
            'all_latency_samples_ms':[round(t*1000,5) for t in all_times]}
    assert result['attempts']>0
    return result


def run(seconds):
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
    port=sock.getsockname()[1];process=None
    try:
        process=subprocess.Popen([sys.executable,'-m','uvicorn','fastapi_boundaries:create_app','--factory',
            '--app-dir',str(Path(__file__).parent),'--fd',str(sock.fileno()),'--workers','1',
            '--no-access-log','--log-level','warning'],pass_fds=(sock.fileno(),),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        deadline=time.perf_counter()+15
        while True:
            if process.poll() is not None:raise RuntimeError('server exited')
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=1)
            try:
                c.request('GET','/async-io');r=c.getresponse();body=r.read()
                if r.status==200 and json.loads(body)['ok']:break
            except (OSError,http.client.HTTPException):pass
            finally:c.close()
            if time.perf_counter()>deadline:raise TimeoutError('startup')
            time.sleep(.05)
        # Five warm-up calls for each measured route, excluded from stage counts.
        for route in ['async-blocking','async-io']:
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
            try:
                for _ in range(5):
                    c.request('GET','/'+route);r=c.getresponse();data=r.read();assert r.status==200 and json.loads(data)['ok']
            finally:c.close()
        result={'python':platform.python_version(),'versions':{n:version(n) for n in ['fastapi','uvicorn','starlette']},
                'model':'closed; zero think time; one persistent HTTP/1.1 connection per vuser; local generator and one-worker server',
                'work':'50ms sleep on event loop or asyncio.sleep; synthetic waiting, no external I/O',
                'warmup_requests_per_route':5,'stages':[]}
        for route,users in [('async-blocking',1),('async-blocking',8),('async-io',8)]:
            print(f'Start {route}: users={users}, duration={seconds}s',flush=True)
            row=stage(port,process.pid,route,users,seconds);result['stages'].append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='all_latency_samples_ms'}),flush=True)
        return result
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
            if process.stderr:process.stderr.close()
        sock.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=120);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not 1<=a.seconds<=180 or a.output.exists():p.error('Seconds 1..180 and new output path required')
    result=run(a.seconds);result['cleanup']='server stopped and listening socket closed'
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
