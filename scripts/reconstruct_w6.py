"""DRAFT: private approved-data reconstruction; no CPU execution or model fitting."""
import argparse,json
from fractions import Fraction as F
from pathlib import Path
from release_common import new_output,write_json
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',required=True,help='Explicit separately authorized W6 data directory');p.add_argument('--out',required=True);args=p.parse_args()
 data=Path(args.data_dir).resolve()/'observations-and-locks.json'
 if not data.is_file():raise SystemExit('W6_DATA_MISSING: restricted observations are not in the intended public payload; obtain approval for the internal W6 data package')
 obj=json.loads(data.read_text());out=new_output(args.out);groups={}
 for r in obj['observations']:
  key=(r['stage'],r['kind'],r['n'],r['pattern'],r['d_I'],r['d_D']);groups.setdefault(key,[]).append(r)
 for key,rr in groups.items():
  if len(rr)!=3 or {r['repeat'] for r in rr}!={0,1,2} or len({(r['raw'],r['kernel'],r['TI'],r['TD']) for r in rr})!=1:raise ValueError('Invalid or inconsistent three-repeat condition: '+str(key))
 unique={k:v[0] for k,v in groups.items()};corners={k[1:]:r for k,r in unique.items() if k[0] in ('F1','F2')};pred=[]
 locks={(r['stage'],r['model'],r['kind'],r['n'],r['pattern'],r['d_I'],r['d_D']):F(r['prediction']) for r in obj['locks']}
 for key,r in unique.items():
  stage,kind,n,pattern,i,d=key
  if stage not in ('H','E01','E02'):continue
  base=[corners[(kind,n,pattern,ci,cd)] for ci,cd in ((0,0),(3,0),(0,3),(3,3))];c,c30,c03,c33=[b['raw'] for b in base];a=F(c30-c,3);b=F(c03-c,3);j=F(c33-c30-c03+c,9)
  for model in (('M0','M1','M2') if stage=='H' else ('BE',)):
   value=F(c+i*base[0]['TI']+d*base[0]['TD']) if model=='M0' else c+a*i+b*d+(j*i*d if model=='M2' else 0)
   if model=='BE' and i!=0:raise ValueError('Break-even model restricted to d_I=0')
   if value!=locks[(stage,model,kind,n,pattern,i,d)]:raise ValueError('Prediction differs from frozen lock')
   residual=value-r['raw'];pred.append(dict(stage=stage,model=model,kind=kind,n=n,pattern=pattern,d_I=i,d_D=d,prediction=str(value),observed=r['raw'],residual=str(residual),primary=abs(residual)<=max(F(10),F(r['raw'],20)),maximum=abs(residual)<=max(F(10),F(3*r['raw'],20)),exact=residual==0,units='cycles'))
 summary={m:dict(total=sum(r['model']==m for r in pred),primary=sum(r['model']==m and r['primary'] for r in pred),exact=sum(r['model']==m and r['exact'] for r in pred)) for m in ('M0','M1','M2')}
 expected={'M0':(160,120,0),'M1':(160,160,0),'M2':(160,160,0)}
 for m,v in expected.items():
  if tuple(summary[m][k] for k in ('total','primary','exact'))!=v:raise ValueError('Archived scoring disagreement '+m)
 if any(r['residual']!='2' for r in pred if r['model'] in ('M1','M2')):raise ValueError('Historical +2 residual changed')
 if any(r['residual']!='0' for r in pred if r['model']=='BE'):raise ValueError('Extension residual changed')
 write_json(out/'predictions-residuals.json',pred);write_json(out/'summary.json',dict(models=summary,break_even_exact='49/3',classification='ARCHIVED_DATA_RECONSTRUCTION',scope='Compact locked numerical inputs; full original event-trace audit remains internal'))
 print('W6_NUMERICAL_RECONSTRUCTION_PASS; no CPU reproduction implied')
if __name__=='__main__':main()
