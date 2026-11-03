// Adapter contract tests. CPU architectural verification is in dot4_cpu_tb.cpp.
#include "Vpcpi_dot4.h"
#include "verilated.h"
#include <cstdint>
#include <iostream>
#include <stdexcept>
static void check(bool ok, const char *message) {
    if (!ok) throw std::runtime_error(message);
}
int main(int argc, char **argv) {
    try {
        Verilated::commandArgs(argc,argv);
        Vpcpi_dot4 d;
        unsigned edges=0, completions=0;
        auto eval=[&]() {d.clk=0; d.eval();};
        auto tick=[&]() {eval(); d.clk=1; d.eval(); ++edges; eval();};
        auto quiet=[&]() {eval(); check(!d.pcpi_wait && !d.pcpi_ready && !d.pcpi_wr && !d.pcpi_rd,"Unexpected response");};
        auto reset=[&]() {d.resetn=0; quiet(); tick(); quiet(); d.resetn=1;};
        d.pcpi_valid=0; d.pcpi_insn=0; d.pcpi_rs1=0; d.pcpi_rs2=0;
        reset(); quiet();
        auto request=[&](uint32_t a,uint32_t b,uint32_t expected) {
            d.pcpi_valid=1; d.pcpi_insn=0x0062838b; d.pcpi_rs1=a; d.pcpi_rs2=b;
            for (unsigned age=0;age<3;++age) {
                eval();
                check(d.pcpi_wait && bool(d.pcpi_ready)==(age==2) && d.pcpi_wr==d.pcpi_ready,"Timing contract");
                check(d.pcpi_rd==(age==2 ? expected : 0),"Result contract");
                if (age == 2) {
                    // Observation only: no signal assignments, eval calls or changed checks.
                    std::cout << "PCPI_COMPLETION id=" << (completions + 1)
                              << " edge_before=" << edges << " insn=" << d.pcpi_insn
                              << " a=" << d.pcpi_rs1 << " b=" << d.pcpi_rs2
                              << " result=" << d.pcpi_rd << " expected=" << expected
                              << " wait=" << unsigned(d.pcpi_wait)
                              << " ready=" << unsigned(d.pcpi_ready) << " wr=" << unsigned(d.pcpi_wr) << "\n";
                }
                completions+=d.pcpi_ready;
                tick();
            }
            // Deliberately hold valid after completion; only one response allowed.
            for(unsigned i=0;i<8;++i) {quiet(); tick();}
            d.pcpi_valid=0; quiet(); tick(); quiet();
        };
        request(0x80808080,0x80808080,0x10000);
        request(0xfc03fe01,0x08f906fb,0xffffffba);
        std::cout<<"PASS hold-valid-drain/rearm completions="<<completions<<"\n";
        for(uint32_t insn : {0x0062938bu,0x0262838bu,0x006283abu,0x546283abu}) {
            d.pcpi_valid=1; d.pcpi_insn=insn;
            for(unsigned i=0;i<20;++i) {quiet(); tick();}
            d.pcpi_valid=0; tick();
        }
        std::cout<<"PASS unsupported=4 hold_cycles_each=20\n";
        for(unsigned age : {1u,2u}) {
            d.pcpi_valid=1; d.pcpi_insn=0x0062838b;
            d.pcpi_rs1=0x80808080; d.pcpi_rs2=0x80808080;
            for(unsigned i=0;i<age;++i) tick();
            eval(); check(bool(d.pcpi_ready)==(age==2),"Reset target not reached");
            reset(); d.pcpi_valid=0; tick(); quiet();
            request(0x80808080,0x7f7f7f7f,0xffff0200);
            std::cout<<"PASS reset-before-edge age="<<age<<" new_result=ffff0200\n";
        }
        // Defensive early withdrawal is a local cleanup test, not a PCPI kill protocol.
        d.pcpi_valid=1; d.pcpi_insn=0x0062838b; tick();
        d.pcpi_valid=0; quiet(); tick(); quiet();
        request(0,0,0);
        check(completions==5,"Completion count");
        std::cout<<"ADAPTER_PASS completions="<<completions<<" edges="<<edges<<"\n";
        return 0;
    } catch(const std::exception &e) {
        std::cout<<"FAIL "<<e.what()<<"\n"; return 1;
    }
}
