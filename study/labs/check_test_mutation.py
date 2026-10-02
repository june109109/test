"""Mutate a temporary copy to check whether assertions catch a boundary bug."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():p.error('Choose new output path')
source=Path(__file__).parent/'testing_demo'
with tempfile.TemporaryDirectory(prefix='study-mutation-') as d:
    target=Path(d)/'demo'
    shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','.coverage'))
    file=target/'pricing.py';old=file.read_text();assert old.count('discounted >= 10000')==1
    file.write_text(old.replace('discounted >= 10000','discounted > 10000'))
    result=subprocess.run([sys.executable,'-m','pytest','-q','-c','pytest.ini'],cwd=target,text=True,capture_output=True,timeout=30)
    assert result.returncode==1, result.stdout+result.stderr
    assert 'test_free_shipping_boundary' in result.stdout and '3 failed, 18 passed' in result.stdout, result.stdout
    output={'mutation':'temporary copy: discounted >= 10000 changed to > 10000',
            'expected_pytest_exit_code':1,'actual_exit_code':result.returncode,
            'failed':3,'passed':18,'classification':'expected mutation detection, original suite passed 21',
            'stdout':result.stdout,'stderr':result.stderr}
assert file.exists() is False and (source/'pricing.py').read_text()==old
with a.output.open('x') as f:json.dump(output,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in output.items() if k not in ('stdout','stderr')},indent=2))
