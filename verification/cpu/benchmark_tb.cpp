#include "Vbenchmark_soc.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
static void need(bool ok,const char *s) {if(!ok) throw std::runtime_error(s);}
#include "bus_check.h"
#include "observer.h" // TASK020_OBSERVER
struct Step {uint32_t pc,word;};
struct Part {uint32_t a,b,result;};
int main(int argc,char **argv) {
    unsigned cycle=0,ti=0,qi=0;
    try {
        need(argc==6,"image fixture d_I d_D mode"); Verilated::commandArgs(argc,argv);
        const unsigned d_I=std::stoul(argv[3]),d_D=std::stoul(argv[4]); const std::string mode=argv[5];
        std::array<uint8_t,4096> ram{};
        std::ifstream binary(argv[1],std::ios::binary); need(bool(binary),"Image open");
        binary.read(reinterpret_cast<char *>(ram.data()),ram.size()); need(binary.gcount()==4096&&binary.peek()==EOF,"Image size");
        auto word=[&](uint32_t a) {need(a<=4092&&!(a&3),"RAM address"); return uint32_t(ram[a])|uint32_t(ram[a+1])<<8|uint32_t(ram[a+2])<<16|uint32_t(ram[a+3])<<24;};
        std::ifstream in(argv[2]); need(bool(in),"Fixture open"); char kind; uint32_t expect=0,words=0,cs=0,is=0,ie=0,ce=0,entry=0;
        std::vector<Step> steps; std::vector<Part> parts; std::vector<uint32_t> load_addresses; in>>std::hex;
        while(in>>kind) {
            if(kind=='H') in>>expect>>words>>cs>>is>>ie>>ce>>entry;
            else if(kind=='T') {Step s{}; in>>s.pc>>s.word; steps.push_back(s);}
            else if(kind=='L') {uint32_t address; in>>address; load_addresses.push_back(address);}
            else if(kind=='Q') {Part p{}; in>>p.a>>p.b>>p.result; parts.push_back(p);}
            else throw std::runtime_error("Fixture kind");
            need(bool(in),"Fixture truncated");
        }
        need(!steps.empty(),"Empty reference trace");
        Vbenchmark_soc d; d.clk=0; d.resetn=0; d.mem_ready=0; d.mem_rdata=0;
        Observer observer(d_I,d_D,cs,ce); // TASK020_OBSERVER
        for(int i=0;i<5;++i) {d.clk=0;d.eval();d.clk=1;d.eval();}
        d.resetn=1;
        bool ma=false,kernel=false,started=false,ended=false,active=false,pending=false;
        uint32_t addr=0,data=0,strobe=0,instr=0; unsigned memage=0,selected_delay=0,kstart=0,kend=0,qstart=0,complete=0,rf=0;
        unsigned loads=0,stores=0,stalls=0,status=0,output_slot=0;
        uint64_t cstart=0,cend=0,istart=0,iend=0; unsigned estart=0,eend=0,nsamples=0;
        unsigned sample_rf=0,mc=0,mrf=0,mstart=0,mrd=0,mpc=0; uint32_t mr=0,mword=0,ma0=0,mb0=0; bool mactive=false,mpending=false;
        for(cycle=0;cycle<3000000;++cycle) {
            d.clk=0; d.mem_ready=0; d.eval();
            need(d.cycle_counter==cycle,"Cycle counter differs from physical clock count");
            if(d.mem_valid) {
                if(!ma) {ma=true;memage=0;addr=d.mem_addr;data=d.mem_wdata;strobe=d.mem_wstrb;instr=d.mem_instr;selected_delay=instr?d_I:d_D;}
                need(addr==d.mem_addr&&strobe==d.mem_wstrb&&instr==d.mem_instr&&(!strobe||data==d.mem_wdata),"Stalled memory changed");
                if(memage>=selected_delay) {d.mem_ready=1;d.mem_rdata=addr<4096?word(addr):0;}
                else if(kernel&&!instr) ++stalls;
                ++memage;
            } else need(!ma,"Memory withdrawn");
            d.eval(); audit_bus(d); need(!d.trap,"Unexpected trap");
            observer.pre(d,cycle,kernel,selected_delay); // TASK020_OBSERVER
            if(d.sample_cycle) {
                if(d.cpu_pc==cs) {need(nsamples==0,"Start counter repeated");cstart=d.cycle_counter;estart=cycle;}
                else {need(d.cpu_pc==ce&&nsamples==3,"End cycle sample");cend=d.cycle_counter;eend=cycle;}
                ++nsamples;
            }
            if(d.sample_instr) {
                if(d.cpu_pc==is) {need(nsamples==1,"Start instruction sample");istart=d.instruction_counter;}
                else {need(d.cpu_pc==ie&&nsamples==2,"End instruction sample");iend=d.instruction_counter;}
                ++nsamples;
            }
            if(d.rf_we) {
                if(d.cpu_pc==cs) {need(d.rf_data==cstart,"RDCYCLE RF start");++sample_rf;}
                if(d.cpu_pc==is) {need(d.rf_data==istart,"RDINSTRET RF start");++sample_rf;}
                if(d.cpu_pc==ie) {need(d.rf_data==iend,"RDINSTRET RF end");++sample_rf;}
                if(d.cpu_pc==ce) {need(d.rf_data==cend,"RDCYCLE RF end");++sample_rf;}
            }
            bool mul_write=false;
            if(mpending) {need(d.rf_we&&d.rf_addr==mrd&&d.rf_data==mr&&d.cpu_pc==mpc,"MUL actual RF mismatch");mpending=false;++mrf;mul_write=true;}
            bool custom_write=false;
            if(pending) {
                need(d.rf_we&&d.rf_addr==7&&d.rf_data==parts[qi-1].result,"DOT4 actual RF mismatch");
                pending=false; ++rf; custom_write=true;
            }
            if(d.pcpi_valid&&is_mul_word(d.pcpi_insn)) {
                need(mode=="scalar"&&kernel,"MUL outside scalar kernel");
                if(!mactive) {mactive=true;mstart=cycle;mrd=(d.pcpi_insn>>7)&31;mpc=d.cpu_pc;mword=d.pcpi_insn;ma0=d.pcpi_rs1;mb0=d.pcpi_rs2;mr=uint32_t(uint64_t(ma0)*mb0);}
                need(mword==d.pcpi_insn&&ma0==d.pcpi_rs1&&mb0==d.pcpi_rs2&&mrd!=0,"MUL request stability");
                unsigned age=cycle-mstart;
                need(((mword>>12)&7)==0&&age<=2&&!d.cpu_timeout,"MUL instruction/timing");
                need(bool(d.mul_ready)==(age==2)&&d.mul_wr==d.mul_ready&&!d.pcpi_wait&&!d.pcpi_ready,"MUL responder timing");
                if(d.mul_ready) {need(d.mul_rd==mr&&d.selected_rd==mr,"MUL arithmetic/selection");++mc;mpending=true;}
            } else if(d.pcpi_valid) {
                need(mode=="dot4"&&kernel,"PCPI outside candidate kernel");
                if(!active) {need(qi<parts.size(),"Extra DOT4");active=true;qstart=cycle;++qi;}
                const auto &p=parts[qi-1]; unsigned age=cycle-qstart;
                need(d.pcpi_insn==0x0062838b&&d.pcpi_rs1==p.a&&d.pcpi_rs2==p.b,"DOT4 identity/operands");
                need(age<=2&&d.adapter_state==age&&d.pcpi_wait&&!d.cpu_timeout,"DOT4 timing");
                need(bool(d.pcpi_ready)==(age==2)&&d.pcpi_wr==d.pcpi_ready,"DOT4 completion");
                if(d.pcpi_ready) {need(d.pcpi_rd==p.result,"DOT4 partial mismatch");++complete;pending=true;}
            } else {need(!d.pcpi_wait&&!d.pcpi_ready&&!d.pcpi_wr,"Response without valid"); if(active) {need(cycle-qstart==3,"Incomplete DOT4");active=false;}}
            if(!d.pcpi_valid&&mactive) {need(cycle-mstart==3,"Incomplete MUL");mactive=false;}
            if(d.mem_valid&&d.mem_ready) {
                if(kernel&&!d.mem_instr) {
                    if(d.mem_wstrb) ++stores;
                    else {
                        need(loads<load_addresses.size()&&d.mem_addr==load_addresses[loads],"Independent kernel load address/order"); ++loads;
                    }
                }
                if(d.mem_wstrb) {
                    need(!kernel&&d.mem_wstrb==15&&d.mem_addr==0x10000000+4*output_slot,"Unexpected output store");
                    if(output_slot==0) need(d.mem_wdata==expect,"Software result signature");
                    else if(output_slot==1) need(d.mem_wdata==cend-cstart,"Software cycle delta");
                    else if(output_slot==2) need(d.mem_wdata==iend-istart,"Software instruction delta");
                    else {need(output_slot==3&&d.mem_wdata==1,"Software failure status");status=1;}
                    ++output_slot;
                }
                ma=false;
            }
            const bool launch=d.launch,write=d.rf_we;
            const unsigned rd=d.rf_addr; const uint32_t value=d.rf_data;
            const uint64_t oldi=d.instruction_counter;
            d.clk=1;d.eval();
            need(d.instruction_counter==oldi+unsigned(launch),"Instruction counter increment contract");
            if(write) need(d.registers[rd]==value,"Actual RF storage");
            if(mul_write) std::cout<<"MUL index="<<mrf-1<<" pc="<<std::hex<<mpc<<" word="<<mword<<" a="<<ma0<<" b="<<mb0<<" result="<<mr<<" rf="<<value<<std::dec<<" request="<<mstart<<" complete="<<mstart+2<<" write="<<cycle<<"\n";
            if(custom_write) std::cout<<"DOT4 index="<<qi-1<<" rf="<<std::hex<<value<<std::dec<<" request="<<qstart<<" complete="<<qstart+2<<" write="<<cycle<<"\n";
            if(launch) {
                const uint32_t pc=d.cpu_pc;
                if(pc==entry&&!started) {started=true;kernel=true;kstart=cycle;}
                if(kernel&&pc==ie) {
                    need(ti==steps.size()&&d.registers[10]==expect,"Kernel trace/result at return");
                    kernel=false;ended=true;kend=cycle;
                } else if(kernel) {
                    if(ti>=steps.size()||pc!=steps[ti].pc||word(pc)!=steps[ti].word) {
                        std::cout<<"TRACE_MISMATCH index="<<ti<<" actual_pc="<<std::hex<<pc<<" expected_pc="<<(ti<steps.size()?steps[ti].pc:0)<<std::dec<<"\n";
                        throw std::runtime_error("Independent instruction trace");
                    }
                    ++ti;
                }
            }
            observer.post(d,cycle,kernel,started,ended,kstart,kend); // TASK020_OBSERVER
            if(status) {
                need(ended&&nsamples==4&&sample_rf==4&&output_slot==4,"Incomplete measurement");
                need(cend-cstart==eend-estart&&iend-istart==steps.size()+2,"Counter cross-check");
                need(loads==load_addresses.size()&&!stores,"Kernel memory accounting");
                need(complete==rf&&complete==parts.size()&&!active&&!pending,"PCPI accounting");
                need(mc==mrf&&mc==(mode=="scalar"?4*words:0)&&!mactive&&!mpending,"MUL accounting");
                std::cout<<"MEASURE raw_cycles="<<cend-cstart<<" counter_instructions="<<iend-istart<<" kernel_cycles="<<kend-kstart
                    <<" kernel_instructions="<<ti<<" dot4="<<complete<<" input_loads="<<loads<<" kernel_stores="<<stores
                    <<" data_stalls="<<stalls<<" app_cycles="<<cycle+1<<" result="<<std::hex<<expect<<std::dec
                    <<" mul="<<mc<<" mul_rf="<<mrf<<" cycle_start="<<estart<<" cycle_end="<<eend<<" counter_rf_checks="<<sample_rf<<"\nPASS\n";
                observer.finish(cend-cstart,kend-kstart); // TASK020_OBSERVER
                return 0;
            }
        }
        throw std::runtime_error("WATCHDOG_TIMEOUT");
    } catch(const std::exception &e) {
        std::cout<<"FAIL "<<e.what()<<" cycle="<<cycle<<" trace_index="<<ti<<" dot4_index="<<qi<<"\n";return 1;
    }
}
