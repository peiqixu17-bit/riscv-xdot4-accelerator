"""Gate 2: focused producer-format regressions and subprocess failure proof."""
import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
from measurement_parser import parse_measurement,require_result
def line(v):return 'MEASURE raw_cycles=10 kernel_cycles=8 result='+v
if '--wrong-result' in sys.argv:
    require_result(parse_measurement(line('00000010'))['result'],10)
    raise SystemExit('ERROR wrong result accepted')
from release_common import new_output
import argparse
p=argparse.ArgumentParser();p.add_argument('--out',required=True);O=new_output(p.parse_args().out)
results=[]
for text,want in [('00000010',16),('0000002a',42),('0',0),('00000000',0),('fffffffe',-2),('7fffffff',2147483647),('80000000',-2147483648),('7f00',32512)]:
    got=parse_measurement(line(text));require_result(got['result'],want)
    assert got['raw_cycles']==10 and got['kernel_cycles']==8
    results.append(dict(input=text,expected_signed=want,observed_u32=got['result'],status='PASS'))
bad=['MEASURE raw_cycles=10 kernel_cycles=8',line('xyz'),line('0000002g'),line(''),line('-2'),line('0x10'),line('100000000'),line('10')+' result=10',line('10')+' raw_cycles=11']
for text in bad:
    try:parse_measurement(text)
    except ValueError as e:results.append(dict(input=text,status='EXPECTED_REJECTION',reason=str(e)))
    else:raise AssertionError('Malformed input accepted')
args=[sys.executable,'-B','-I',str(Path(__file__).resolve()),'--wrong-result']
p=subprocess.run(args,cwd=R,capture_output=True,text=True)
(O/'parser-negative.stdout.log').write_text(p.stdout)
(O/'parser-negative.stderr.log').write_text(p.stderr)
assert p.returncode!=0 and 'Result mismatch: actual=00000010, expected=0000000a' in p.stderr
with (O/'parser-gate.json').open('x') as f:json.dump(dict(status='PASS',valid_cases=8,malformed_cases=9,negative_result=dict(argv=args,exit=p.returncode,expected_nonzero=True),cases=results),f,indent=2)
print('PARSER_PASS valid=8 malformed_rejected=9 deliberately_wrong_exit='+str(p.returncode))
