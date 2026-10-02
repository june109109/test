"""Plot saved closed-model observations, not a live dashboard."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
if a.output.exists():p.error('Choose a new output path')
x=json.loads(a.input.read_text());stages=x['stages']
labels=['blocking / 1 VU','blocking / 8 VU','async wait / 8 VU']
fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
axes[0].bar(labels,[s['successful_rps'] for s in stages],color=['#5271a5','#d37942','#3a9477'])
axes[0].set(title='Successful throughput (closed model)',ylabel='Successful requests / elapsed second')
for s,label in zip(stages,labels):
 values=sorted(s['all_latency_samples_ms'])
 axes[1].plot(values,[(i+1)/len(values) for i in range(len(values))],label=label)
axes[1].set(title='Client-observed latency: empirical CDF',xlabel='End-to-end latency [ms]',ylabel='Fraction at or below latency',ylim=(0,1.01))
axes[1].legend();axes[1].grid(alpha=.2)
fig.suptitle('120 seconds per stage; one worker; loopback; one trial; synthetic 50 ms wait')
fig.savefig(a.output,dpi=160);plt.close(fig)
