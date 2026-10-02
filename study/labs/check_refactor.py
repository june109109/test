"""Apply refactored module to a temporary copy, run existing contract tests."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():p.error('Choose a new path')
root=Path(__file__).parent;original=(root/'testing_demo/pricing.py').read_bytes()
with tempfile.TemporaryDirectory(prefix='study-refactor-') as d:
    target=Path(d)/'demo';shutil.copytree(root/'testing_demo',target,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
    shutil.copyfile(root/'pricing_refactored.py',target/'pricing.py')
    result=subprocess.run([sys.executable,'-m','pytest','-q','-c','pytest.ini'],cwd=target,capture_output=True,text=True,timeout=30)
    assert result.returncode==0 and '21 passed' in result.stdout,result.stdout+result.stderr
assert (root/'testing_demo/pricing.py').read_bytes()==original
with a.output.open('x') as f:
    json.dump({'change':'extract subtotal, apply_discount, shipping_fee; preserve validation and API',
               'passed':21,'failed':0,'original_unchanged':True,'stdout':result.stdout,'stderr':result.stderr},f,indent=2);f.write('\n')
print('Refactored temporary copy: 21 passed; original unchanged')
