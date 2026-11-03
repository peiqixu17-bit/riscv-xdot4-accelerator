"""DRAFT: independently check new W5 measurement records and archived baseline."""
import argparse,csv,json
from fractions import Fraction
from pathlib import Path
from release_common import ROOT,new_output,write_json
def main():
 p=argparse.ArgumentParser();p.add_argument('--measurements',required=True);p.add_argument('--out',required=True);args=p.parse_args();data=json.loads(Path(args.measurements).read_text());rr=data['runs']
 expected=[(0,d,r,k) for d in (0,3) for r in range(3) for k in ('s2','dot4')]
 if [(r['d_I'],r['d_D'],r['repeat'],r['kind']) for r in rr]!=expected:raise ValueError('Expected exact frozen twelve-run order')
 archived={(r['kind'],int(r['d_D']),int(r['repeat'])):r for r in csv.DictReader((ROOT/'data/w5/measurements.csv').open())};ratios=[]
 for r in rr:
  m=r['metrics'];a=archived[r['kind'],r['d_D'],r['repeat']]
  if m['result']!=5366:raise ValueError('Incorrect independent expected result')
  for key in ('raw_cycles','kernel_cycles','app_cycles','input_loads','dot4','mul','kernel_stores'):
   if m[key]!=int(a[key]):raise ValueError('Archived-condition difference '+str((r['kind'],r['d_D'],key)))
 for d in (0,3):
  for kind in ('s2','dot4'):
   ms=[r['metrics'] for r in rr if r['d_D']==d and r['kind']==kind]
   if not all(m==ms[0] for m in ms):raise ValueError('Inconsistent deterministic repeats')
  for rep in range(3):
   pair={r['kind']:r['metrics'] for r in rr if r['d_D']==d and r['repeat']==rep}
   ratios.append(dict(d_I=0,d_D=d,repeat=rep,raw=str(Fraction(pair['s2']['raw_cycles'],pair['dot4']['raw_cycles'])),kernel=str(Fraction(pair['s2']['kernel_cycles'],pair['dot4']['kernel_cycles']))))
 statistics=[]
 for delay in (0,3):
  for kind in ('s2','dot4'):
   selected=[r['metrics'] for r in rr if r['d_D']==delay and r['kind']==kind]
   for field in selected[0]:
    values=[m[field] for m in selected]
    statistics.append(dict(d_D=delay,kind=kind,field=field,mean=str(Fraction(sum(values),len(values))),minimum=min(values),maximum=max(values)))
 out=new_output(args.out);write_json(out/'comparison.json',dict(status='MATCH',ratios=ratios,statistics=statistics,all_repetitions_equal=True,scope='New clean run comparison; preserve mismatches, never retune or replace samples'))
 print('W5_COMPARISON_PASS')
if __name__=='__main__':main()
