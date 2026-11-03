"""Task015 independent instruction interpreter; frozen golden is never edited.
Only value/control/memory events are predicted, never cycles or CPU timing.
"""
import struct
def signed(v,n=32):return v-(1<<n) if v&(1<<(n-1)) else v
def decode(w):
    assert w&3==3,('compressed',hex(w))
    op=w&127;f=(w>>12)&7;h=w>>25
    if op==0x13:
        assert f in [0,2,3,4,6,7] or f==1 and h==0 or f==5 and h in [0,32]
    elif op==0x33:assert (h==0 or h==32 and f in [0,5] or h==1 and f in [0,1,2,3])
    elif op==3:assert f in [0,1,2,4,5]
    elif op==0x23:assert f in [0,1,2]
    elif op==0x63:assert f in [0,1,4,5,6,7]
    elif op==0x67:assert f==0
    elif op==0x73:assert w in {0xc0002473,0xc02024f3,0xc0202973,0xc00029f3}
    elif op==11:assert w==0x0062838b
    else:assert op in [0x37,0x17,0x6f],hex(w)
    return op,f,h
def trace(image,entry,return_pc,words):
    r=[0]*32;r[1]=return_pc;r[2]=0x700;r[10]=0x800;r[11]=0xc00;r[12]=words
    pc=entry;steps=[];loads=[];muls=[];composition={}
    while pc!=return_pc:
        assert len(steps)<200000 and pc%4==0
        w=struct.unpack_from('<I',image,pc)[0];op,f,h=decode(w);steps.append((pc,w))
        rd=(w>>7)&31;x=(w>>15)&31;y=(w>>20)&31;a,b=r[x],r[y];v=None;nextpc=pc+4;imm=signed(w>>20,12);label=''
        if op==0x13:
            label=['ADDI','SLLI','SLTI','SLTIU','XORI','SRLI/SRAI','ORI','ANDI'][f]
            if f==0:v=a+imm
            elif f==1:v=a<<(y&31)
            elif f==2:v=int(signed(a)<imm)
            elif f==3:v=int(a<(imm&0xffffffff))
            elif f==4:v=a^(imm&0xffffffff)
            elif f==5:v=(signed(a) if h==32 else a)>>(y&31)
            elif f==6:v=a|(imm&0xffffffff)
            else:v=a&(imm&0xffffffff)
        elif op==0x33:
            if h==1:
                assert f==0,'Only MUL required by these scalar kernels';v=a*b;label='MUL';muls.append(dict(pc=pc,word=w,a=a,b=b,result=v&0xffffffff))
            else:
                label=['ADD/SUB','SLL','SLT','SLTU','XOR','SRL/SRA','OR','AND'][f]
                if f==0:v=a-b if h==32 else a+b
                elif f==1:v=a<<(b&31)
                elif f==2:v=int(signed(a)<signed(b))
                elif f==3:v=int(a<b)
                elif f==4:v=a^b
                elif f==5:v=(signed(a) if h==32 else a)>>(b&31)
                elif f==6:v=a|b
                else:v=a&b
        elif op==3:
            addr=(a+imm)&0xffffffff;width={0:1,1:2,2:4,4:1,5:2}[f]
            assert addr%width==0 and ((0x800<=addr and addr+width<=0x800+words*4) or (0xc00<=addr and addr+width<=0xc00+words*4)),('input load bounds',addr)
            v=int.from_bytes(image[addr:addr+width],'little');v=signed(v,width*8) if f<2 else v;loads.append(addr&~3);label={0:'LB',1:'LH',2:'LW',4:'LBU',5:'LHU'}[f]
        elif op==0x63:
            off=((w>>31)<<12)|(((w>>7)&1)<<11)|(((w>>25)&63)<<5)|(((w>>8)&15)<<1)
            take={0:a==b,1:a!=b,4:signed(a)<signed(b),5:signed(a)>=signed(b),6:a<b,7:a>=b}[f]
            if take:nextpc=pc+signed(off,13)
            label='BRANCH'
        elif op==0x67:v=pc+4;nextpc=(a+imm)&0xfffffffe;label='JALR'
        elif op==0x6f:
            off=((w>>31)<<20)|(((w>>12)&255)<<12)|(((w>>20)&1)<<11)|(((w>>21)&1023)<<1)
            v=pc+4;nextpc=pc+signed(off,21);label='JAL'
        elif op==0x37:v=w&0xfffff000;label='LUI'
        elif op==0x17:v=pc+(w&0xfffff000);label='AUIPC'
        elif op==11:
            aa=struct.unpack('<4b',struct.pack('<I',a));bb=struct.unpack('<4b',struct.pack('<I',b));v=sum(x*y for x,y in zip(aa,bb));label='DOT4'
        else:raise AssertionError(('Unexpected kernel instruction/store/counter',hex(w)))
        composition[label]=composition.get(label,0)+1
        if v is not None and rd:r[rd]=v&0xffffffff
        pc=nextpc
    return dict(steps=steps,result=r[10],loads=loads,muls=muls,composition=composition)
