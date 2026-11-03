"""Exactly nine deterministic architectural cases; no performance or fixture workflow."""
import hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
import argparse
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parents[1];C=R
sys.path.insert(0,str(R/'scripts'))
from release_common import new_output, tool
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',required=True);parser.add_argument('--riscv-prefix',default='riscv32-unknown-elf-')
parser.add_argument('--verilator',default='verilator');parser.add_argument('--make',default='make');parser.add_argument('--cxx',default='g++')
args=parser.parse_args();G=args.riscv_prefix
# Resolve tools before subprocess cwd changes; CLI relative paths mean launch cwd.
TOOLS={name:tool(G+name) for name in ('gcc','ld','objcopy','objdump','readelf','nm')}
V=tool(args.verilator);args.make=tool(args.make);args.cxx=tool(args.cxx)
O=new_output(args.out)
os.environ.pop('VERILATOR_ROOT',None)
os.environ.update(TMPDIR=str(O/'tmp'),TMP=str(O/'tmp'),TEMP=str(O/'tmp'),XDG_CACHE_HOME=str(O/'tmp'),PYTHONDONTWRITEBYTECODE='1',CCACHE_DISABLE='1',LC_ALL='C')
def dump(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2)
commands=[]
def run(label,argv,cwd=O,expected=0):
 argv=list(map(str,argv));p=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,timeout=600)
 (cwd/(label+'.stdout.log')).write_text(p.stdout);(cwd/(label+'.stderr.log')).write_text(p.stderr)
 record=dict(label=label,argv=argv,cwd=str(cwd),exit=p.returncode,expected=expected);commands.append(record)
 dump(cwd/(label+'.command.json'),record)
 if p.returncode!=expected:raise RuntimeError(label+' failed: '+str(p.returncode))
 if expected==0 and re.search(r'%Warning|warning:|clock skew',p.stdout+p.stderr,re.I):raise RuntimeError(label+' diagnostic needs review')
 return p.stdout
for label,path,version in [('gcc',TOOLS['gcc'],'14.1.0'),('ld',TOOLS['ld'],'2.42.50.20240416'),('verilator',V,'5.008'),('make',args.make,'4.3'),('g++',args.cxx,'11.4.0'),('python',sys.executable,'3.10.12')]:
 assert version in run('version-'+label,[path,'--version'])
obj=O/'obj'
run('verilate',[V,'--cc','--exe','--timescale','1ns/1ps','--top-module','p12_benchmark_bf','--prefix','Vbenchmark_soc','--Mdir',obj,'-CFLAGS','-std=c++17 -Wall -Wextra',C/'verification/targeted/p12_benchmark_bf.sv',C/'rtl/integration/p12_top_bf.sv',C/'third_party/picorv32/picorv32.v',C/'rtl/pcpi_dot4.sv',C/'rtl/dot4_unit.sv',C/'verification/targeted/targeted_tb.cpp'])
run('make',[args.make,'-C',obj,'-f','Vbenchmark_soc.mk','-j','2','CXX='+args.cxx])
def dot(a,b):
 aa=[int.from_bytes(bytes([(a>>(8*i))&255]),'little',signed=True) for i in range(4)]
 bb=[int.from_bytes(bytes([(b>>(8*i))&255]),'little',signed=True) for i in range(4)]
 terms=[x*y for x,y in zip(aa,bb)];v=sum(terms)
 return v&0xffffffff,dict(a_lanes=aa,b_lanes=bb,products=terms,signed_result=v)
cases=[('T01',[(0,5,6)]),('T02',[(7,0,6)]),('T03',[(7,5,0)]),('T04',[(7,5,5)]),('T05',[(5,5,6)]),('T06',[(6,5,6)]),('T07',[(5,5,5)]),('T08',[(5,5,6),(7,5,6)]),('T09',[(7,5,6)])]
all_results=[]
for name,ops in cases:
 D=O/name;D.mkdir();regs=[0]*32;regs[5]=0x00ff7f80;regs[6]=0xff017f80;regs[7]=0xdeadbeef;regs[8]=55
 if name in ('T08','T09'):regs[5]=0xffffffff;regs[6]=0x01010101
 asm=['.option norvc','.option norelax','.section .text','.globl _start','_start:']+[f'addi x{i},x0,0' for i in range(1,32)]
 asm += [f'li x{i},0x{regs[i]:08x}' for i in (5,6,7,8)]
 ordinary=[];predictions=[]
 if name=='T09':
  asm+=['addi_before:','addi x5,x5,-1'];regs[5]=(regs[5]-1)&0xffffffff;ordinary.append(('addi_before',5,regs[5]))
 for i,(rd,rs1,rs2) in enumerate(ops):
  a,b=regs[rs1],regs[rs2];v,arithmetic=dot(a,b);word=0x0b|(rd<<7)|(rs1<<15)|(rs2<<20)
  predictions.append(dict(label='custom_'+str(i),word=word,rd=rd,rs1=rs1,rs2=rs2,a=a,b=b,result=v,oracle=arithmetic))
  asm += ['custom_'+str(i)+':',f'.insn r 0x0b,0,0,x{rd},x{rs1},x{rs2}']
  if rd:regs[rd]=v
 if name=='T01':
  asm+=['read_x0:','addi x8,x0,0'];regs[8]=0;ordinary.append(('read_x0',8,0));outreg=8
 elif name=='T09':
  asm+=['addi_after:','addi x8,x7,3'];regs[8]=(regs[7]+3)&0xffffffff;ordinary.append(('addi_after',8,regs[8]));outreg=8
 else:outreg=ops[-1][0]
 signature=regs[outreg];asm+=['lui x30,0x10000',f'sw x{outreg},0(x30)','addi x31,x0,1','sw x31,4(x30)','done:','j done'];regs[30]=0x10000000;regs[31]=1
 (D/'program.S').write_text('\n'.join(asm)+'\n')
 dump(D/'oracle-before-execution.json',dict(case=name,events=predictions,ordinary=ordinary,final_registers=regs,signature=signature,seed=None))
 flags=['-O3','-march=rv32i_zmmul','-mabi=ilp32','-nostdlib','-nostartfiles','-ffreestanding','-Wl,--build-id=none','-Wl,-T,'+str(C/'firmware/link.ld')]
 run('compile',[TOOLS['gcc'],*flags,D/'program.S','-o',D/'program.elf'],D)
 run('objcopy',[TOOLS['objcopy'],'-O','binary',D/'program.elf',D/'program.bin'],D)
 dis=run('disassembly',[TOOLS['objdump'],'-d','-M','no-aliases',D/'program.elf'],D)
 attrs=run('attributes',[TOOLS['readelf'],'-h','-A',D/'program.elf'],D)
 symbols=run('symbols',[TOOLS['nm'],'-n',D/'program.elf'],D)
 pos={m[2]:int(m[1],16) for m in re.finditer(r'^([0-9a-f]+) [Tt] (\w+)$',symbols,re.M)}
 binary=(D/'program.bin').read_bytes();assert len(binary)<4096 and len(binary)%4==0
 assert 'ELF32' in attrs and 'RISC-V' in attrs and 'rv32i2p1_zmmul1p0' in attrs
 enc=[]
 for p in predictions:
  p['pc']=pos[p['label']];assert struct.unpack_from('<I',binary,p['pc'])[0]==p['word']
  enc.append('E '+' '.join(f'{v:x}' for v in [p['pc'],p['word'],p['a'],p['b'],p['result'],p['rd']]))
  # Explicit decode complements objdump's .4byte for an unregistered custom instruction.
  assert (p['word']>>7)&31==p['rd'] and (p['word']>>15)&31==p['rs1'] and (p['word']>>20)&31==p['rs2']
 if name=='T08':assert predictions[1]['pc']==predictions[0]['pc']+4
 if name=='T09':assert pos['addi_before']+4==predictions[0]['pc'] and pos['addi_after']==predictions[0]['pc']+4
 enc+=['A '+' '.join(f'{v:x}' for v in [pos[label],rd,value]) for label,rd,value in ordinary]
 enc += [f'F {i:x} {value:x}' for i,value in enumerate(regs)]+[f'S {signature:x}']
 (D/'expectations.txt').write_text('\n'.join(enc)+'\n');dump(D/'decoded-instructions.json',predictions)
 stdout=run('simulation',[obj/'Vbenchmark_soc',D/'program.bin',D/'expectations.txt'],D)
 assert 'TARGETED_PASS dot4='+str(len(predictions)) in stdout
 trace=[json.loads(s) for s in (D/'cycles.jsonl').read_text().splitlines()]
 actual=[s for s in trace if s['valid']];assert len(actual)==3*len(predictions)
 completions=[s for s in actual if s['ready']];assert len(completions)==len(predictions)
 for p,e in zip(predictions,completions):
  assert (e['pc'],e['insn'],e['a'],e['b'],e['result'])==(p['pc'],p['word'],p['a'],p['b'],p['result'])
  q=trace[e['cycle']+1];assert q['raw_rf_we']==1 and q['rd']==p['rd'] and q['rf_we']==int(p['rd']!=0) and q['rf_data']==p['result']
 final={int(i):int(v,16) for i,v in re.findall(r'^FINAL r=(\d+) value=([0-9a-f]+)$',stdout,re.M)}
 assert len(final)==32 and all(final[i]==regs[i] for i in range(32))
 all_results.append(dict(case=name,status='PASS',events=predictions,actual_completions=completions,final_registers=final,signature=signature,cycles=len(trace),exit=0,firmware_sha256=hashlib.sha256(binary).hexdigest()))
 dump(D/'result.json',all_results[-1])
 print(name+' PASS DOT4='+str(len(predictions)),flush=True)
dump(O/'targeted-results.json',dict(status='PASS',cases=all_results,case_count=9,dot4_completions=10,seed=None,W5='NOT_RUN',W6='NOT_RUN'))
