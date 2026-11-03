// Read-only per-cycle internal/external response checks; no DUT arithmetic changes.
#pragma once
#include <stdexcept>
#include <cstdint>
static void bus_need(bool ok,const char *s) {if(!ok) throw std::runtime_error(s);}
static bool is_mul_word(uint32_t w) {return (w&0xfe00007f)==0x02000033&&((w>>12)&7)<4;}
template<class D> static void audit_bus(const D &d) {
    bus_need(!(d.pcpi_ready&&d.mul_ready),"Conflicting PCPI responders");
    bus_need(!d.mul_wait,"FAST_MUL wait must remain zero");
    bus_need(bool(d.selected_wait)==bool(d.pcpi_wait||d.mul_wait),"PCPI wait selection");
    bus_need(bool(d.selected_ready)==bool(d.pcpi_ready||d.mul_ready),"PCPI ready selection");
    bus_need(d.internal_ready==d.mul_ready,"Unexpected divider response");
    if(d.pcpi_ready) {
        bus_need(d.pcpi_valid&&(d.pcpi_insn&0xfe00707f)==11,"DOT4 response identity");
        bus_need(d.selected_wr==d.pcpi_wr&&d.selected_rd==d.pcpi_rd,"DOT4 response selection");
    }
    if(d.mul_ready) {
        bus_need(d.pcpi_valid&&is_mul_word(d.pcpi_insn),"MUL response identity");
        bus_need(d.selected_wr==d.mul_wr&&d.selected_rd==d.mul_rd,"MUL response selection");
    }
    if(d.pcpi_valid&&is_mul_word(d.pcpi_insn)) bus_need(!d.pcpi_wait&&!d.pcpi_ready&&!d.pcpi_wr,"DOT4 claimed MUL");
}
