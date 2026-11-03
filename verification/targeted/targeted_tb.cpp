#include "Vbenchmark_soc.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
static void need(bool x,const char* s){if(!x)throw std::runtime_error(s);}
struct Event{uint32_t pc,word,a,b,result,rd;};
struct RegCheck{uint32_t pc,rd,value;};
int main(int argc,char**argv){
 unsigned cycle=0,completed=0,writes=0,seen=0,checks=0;
 try{
  need(argc==3,"binary and expectations required");Verilated::commandArgs(argc,argv);
  std::array<uint8_t,4096> ram{};std::ifstream bin(argv[1],std::ios::binary);
  need(bool(bin),"binary open");bin.read(reinterpret_cast<char*>(ram.data()),ram.size());
  need(bin.gcount()>0&&bin.gcount()<4096&&bin.eof(),"binary size");
  auto word=[&](uint32_t a){need(a<4093&&!(a&3),"RAM alignment/range");return uint32_t(ram[a])|uint32_t(ram[a+1])<<8|uint32_t(ram[a+2])<<16|uint32_t(ram[a+3])<<24;};
  std::ifstream spec(argv[2]);need(bool(spec),"expectations open");spec>>std::hex;
  std::vector<Event> events;std::vector<RegCheck> regchecks;std::array<uint32_t,32> final{};std::array<bool,32> present{};
  uint32_t signature=0;char tag;
  while(spec>>tag){if(tag=='E'){Event e{};spec>>e.pc>>e.word>>e.a>>e.b>>e.result>>e.rd;events.push_back(e);}
   else if(tag=='F'){unsigned r;uint32_t v;spec>>r>>v;need(r<32&&!present[r],"duplicate final reg");final[r]=v;present[r]=true;}
   else if(tag=='A'){RegCheck r{};spec>>r.pc>>r.rd>>r.value;regchecks.push_back(r);}
   else if(tag=='S'){spec>>signature;}
   else {throw std::runtime_error("spec tag");}
   need(bool(spec),"truncated spec");
  }
  need(!events.empty(),"empty cases");for(bool p:present)need(p,"missing final register");
  std::ofstream trace("cycles.jsonl");need(bool(trace),"trace open");
  Vbenchmark_soc d;d.clk=0;d.resetn=0;d.mem_ready=0;d.mem_rdata=0;
  for(int i=0;i<5;++i){d.clk=0;d.eval();d.clk=1;d.eval();}d.resetn=1;
  bool active=false,pending=false;unsigned start=0,slot=0;bool done=false;
  for(cycle=0;cycle<10000;++cycle){
   d.clk=0;d.mem_ready=0;d.eval();
   if(d.mem_valid){d.mem_ready=1;d.mem_rdata=d.mem_addr<4096?word(d.mem_addr):0;}d.eval();
   need(!d.trap&&!d.cpu_timeout,"trap or PCPI timeout");
   trace<<"{\"cycle\":"<<cycle<<",\"pc\":"<<d.cpu_pc<<",\"valid\":"<<unsigned(d.pcpi_valid)<<",\"insn\":"<<d.pcpi_insn<<",\"a\":"<<d.pcpi_rs1<<",\"b\":"<<d.pcpi_rs2<<",\"wait\":"<<unsigned(d.pcpi_wait)<<",\"ready\":"<<unsigned(d.pcpi_ready)<<",\"wr\":"<<unsigned(d.pcpi_wr)<<",\"result\":"<<d.pcpi_rd<<",\"raw_rf_we\":"<<unsigned(d.raw_rf_we)<<",\"rf_we\":"<<unsigned(d.rf_we)<<",\"rd\":"<<unsigned(d.rf_addr)<<",\"rf_data\":"<<d.rf_data<<",\"state\":"<<unsigned(d.adapter_state)<<"}\n";
   if(pending){const auto&e=events[seen-1];need(cycle==start+3,"writeback cycle");
    need(d.raw_rf_we&&d.rf_addr==e.rd&&d.rf_data==e.result,"CPU selected writeback");
    need(bool(d.rf_we)==(e.rd!=0),"architectural x0 write suppression");
    std::cout<<"WRITE index="<<seen-1<<" cycle="<<cycle<<" rd="<<e.rd<<" raw_we="<<unsigned(d.raw_rf_we)<<" arch_we="<<unsigned(d.rf_we)<<" data="<<std::hex<<d.rf_data<<std::dec<<"\n";
    ++writes;pending=false;
   }
   if(d.pcpi_valid){
    if(!active){need(seen<events.size(),"extra or stale request");active=true;start=cycle;++seen;}
    const auto&e=events[seen-1];unsigned age=cycle-start;
    need(d.cpu_pc==e.pc&&d.pcpi_insn==e.word,"intended DOT4 PC/encoding");
    need(d.pcpi_rs1==e.a&&d.pcpi_rs2==e.b,"actual sources");
    need(age<=2&&d.adapter_state==age&&d.pcpi_wait,"DOT4 age/state/wait");
    need(bool(d.pcpi_ready)==(age==2)&&d.pcpi_wr==d.pcpi_ready,"completion timing");
    need(!d.mul_ready&&!d.internal_ready&&d.selected_ready==d.pcpi_ready&&d.selected_wr==d.pcpi_wr,"responder selection");
    if(d.pcpi_ready){need(d.pcpi_rd==e.result&&d.selected_rd==e.result,"independent arithmetic result");++completed;pending=true;
     std::cout<<"COMPLETE index="<<seen-1<<" cycle="<<cycle<<" pc="<<std::hex<<e.pc<<" word="<<e.word<<" a="<<d.pcpi_rs1<<" b="<<d.pcpi_rs2<<" result="<<d.pcpi_rd<<std::dec<<"\n";}
   }else{need(!d.pcpi_ready&&!d.pcpi_wr&&!d.pcpi_wait,"stale completion without valid");if(active){need(cycle==start+3,"request did not retire");active=false;}}
   if(d.rf_we){for(const auto&r:regchecks)if(d.cpu_pc==r.pc){need(d.rf_addr==r.rd&&d.rf_data==r.value,"ordinary ADDI result");++checks;std::cout<<"ADDI pc="<<std::hex<<r.pc<<" rd="<<r.rd<<" value="<<d.rf_data<<std::dec<<" cycle="<<cycle<<"\n";}}
   if(d.mem_valid&&d.mem_ready&&d.mem_wstrb){need(d.mem_wstrb==15&&d.mem_addr==0x10000000u+4*slot,"MMIO sequence");
    need(d.mem_wdata==(slot==0?signature:1u),"CPU-visible signature");++slot;if(slot==2)done=true;}
   bool we=d.rf_we;unsigned rd=d.rf_addr;uint32_t data=d.rf_data;
   d.clk=1;d.eval();if(we)need(d.registers[rd]==data,"actual register storage");
   if(done){need(!pending&&!active&&seen==events.size()&&completed==seen&&writes==seen,"exact completion accounting");need(checks==regchecks.size(),"ADDI coverage count");
    for(unsigned r=0;r<32;++r){need(d.registers[r]==final[r],"final register state");std::cout<<"FINAL r="<<r<<" value="<<std::hex<<d.registers[r]<<std::dec<<"\n";}
    std::cout<<"TARGETED_PASS dot4="<<completed<<" cpu_writeback_events="<<writes<<" ordinary_checks="<<checks<<" cycles="<<cycle+1<<"\n";return 0;}
  }throw std::runtime_error("watchdog");
 }catch(const std::exception&e){std::cout<<"TARGETED_FAIL "<<e.what()<<" cycle="<<cycle<<" completed="<<completed<<" writes="<<writes<<"\n";return 1;}
}
