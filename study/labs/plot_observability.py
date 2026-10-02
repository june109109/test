"""Render the saved synthetic probes; no live monitoring server."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
if a.output.exists():p.error('Choose a new output path')
x=json.loads(a.input.read_text())
fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
for name,data in x['lag'].items():
 axes[0].plot(range(len(data['samples_seconds'])),[v*1000 for v in data['samples_seconds']],marker='.',label=name)
axes[0].set(title='Event-loop lag (synthetic, one trial)',xlabel='Heartbeat sample (not equal total durations)',ylabel='Lag beyond 5 ms interval [ms]')
axes[0].legend();axes[0].grid(alpha=.2)
pool=x['anyio_pool'];axes[1].step(range(len(pool['borrowed_samples'])),pool['borrowed_samples'],where='post')
axes[1].axhline(pool['configured_tokens'],color='red',linestyle='--',label='Configured token limit')
axes[1].set(title='AnyIO: 6 tasks, 2 tokens',xlabel='Observer sample (~2 ms target interval)',ylabel='Borrowed tokens',ylim=(0,3))
axes[1].legend();axes[1].grid(alpha=.2)
fig.savefig(a.output,dpi=160);plt.close(fig)
