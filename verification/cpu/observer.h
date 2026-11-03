#pragma once
#include <array>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <vector>

// All DUT access is const. No eval(), drive, clock, RAM, or delay-selection logic.
class Observer {
    static constexpr unsigned NONE=std::numeric_limits<unsigned>::max();
    struct Transaction {
        unsigned id,first,complete=NONE,waits=0,instr,addr,strobe,wdata,selected_delay;
    };
    unsigned d_I_,d_D_,cs_,ce_,cycle_=0,tracked_=NONE,raw_start_=NONE,raw_end_=NONE;
    unsigned kernel_start_=NONE,kernel_end_=NONE,pcpi_id_=0,pcpi_first_=NONE;
    unsigned pcpi_word_=0,pcpi_rd_=0,pcpi_pc_=0,pcpi_value_=0,pcpi_complete_=NONE;
    bool pcpi_active_=false,pcpi_done_=false,pcpi_rf_pending_=false;
    std::array<uint64_t,36> pre_{};
    std::vector<Transaction> transactions_;
    std::vector<std::pair<unsigned,unsigned>> waits_;
    std::ofstream samples_{"samples.tsv"},events_{"events.jsonl"};
    static void check(bool b,const char* s) {if(!b) throw std::runtime_error(s);}
    std::ostream& event(const char* kind,const char* phase,unsigned c) {
        events_<<"{\"event\":\""<<kind<<"\",\"phase\":\""<<phase<<"\",\"cycle\":"<<c<<",\"edge\":"<<c+5;
        return events_;
    }
    void boundary(const char* name,unsigned c) {
        auto& o=event(name,"PRE",c);
        o<<",\"counter\":"<<pre_[13]<<",\"pc\":"<<pre_[10]<<",\"pending\":"<<(tracked_!=NONE);
        if(tracked_!=NONE) {
            const auto& t=transactions_[tracked_];
            o<<",\"id\":"<<t.id<<",\"age\":"<<c-t.first<<",\"prior_waits\":"<<t.waits;
        }
        o<<"}\n";
    }
public:
    Observer(unsigned d_I,unsigned d_D,unsigned cs,unsigned ce):d_I_(d_I),d_D_(d_D),cs_(cs),ce_(ce) {
        check(bool(samples_)&&bool(events_),"OBS output open");
        samples_<<"cycle\tedge\tpre_mem_valid\tpre_mem_ready\tpre_mem_instr\tpre_mem_addr\tpre_mem_wstrb\tpre_mem_wdata\tpre_mem_rdata\tpre_legacy_kernel\tpre_cpu_pc\tpre_sample_cycle\tpre_sample_instr\tpre_cycle_counter\tpre_instruction_counter\tpre_pcpi_valid\tpre_pcpi_insn\tpre_pcpi_rs1\tpre_pcpi_rs2\tpre_selected_wait\tpre_selected_ready\tpre_selected_wr\tpre_selected_rd\tpre_external_wait\tpre_external_ready\tpre_external_wr\tpre_mul_wait\tpre_mul_ready\tpre_mul_wr\tpre_rf_we\tpre_rf_addr\tpre_rf_data\tpre_launch\tpre_cpu_timeout\tpre_adapter_state\tpre_driver_selected_delay\tpost_cpu_pc\tpost_cycle_counter\tpost_instruction_counter\tpost_rf_stored\tpost_legacy_kernel\tpost_started\tpost_ended\tpost_kstart\tpost_kend\n";
    }
    template<class D> void pre(const D& d,unsigned c,bool legacy_kernel,unsigned driver_selected_delay) {
        cycle_=c;
        pre_={c,c+5,uint64_t(d.mem_valid),uint64_t(d.mem_ready),uint64_t(d.mem_instr),d.mem_addr,d.mem_wstrb,d.mem_wdata,d.mem_rdata,
              uint64_t(legacy_kernel),d.cpu_pc,uint64_t(d.sample_cycle),uint64_t(d.sample_instr),d.cycle_counter,d.instruction_counter,
              uint64_t(d.pcpi_valid),d.pcpi_insn,d.pcpi_rs1,d.pcpi_rs2,uint64_t(d.selected_wait),uint64_t(d.selected_ready),uint64_t(d.selected_wr),d.selected_rd,
              uint64_t(d.pcpi_wait),uint64_t(d.pcpi_ready),uint64_t(d.pcpi_wr),uint64_t(d.mul_wait),uint64_t(d.mul_ready),uint64_t(d.mul_wr),
              uint64_t(d.rf_we),d.rf_addr,d.rf_data,uint64_t(d.launch),uint64_t(d.cpu_timeout),d.adapter_state,driver_selected_delay};
        check(pre_[13]==c,"OBS PRE cycle mapping");
        if(d.mem_valid) {
            if(tracked_==NONE) {
                tracked_=transactions_.size();
                Transaction t{};t.id=tracked_;t.first=c;t.instr=d.mem_instr;t.addr=d.mem_addr;t.strobe=d.mem_wstrb;t.wdata=d.mem_wdata;t.selected_delay=driver_selected_delay;
                check(t.selected_delay==(t.instr?d_I_:d_D_),"OBS captured class delay");
                transactions_.push_back(t);
                event("MEM_FIRST","PRE",c)<<",\"id\":"<<t.id<<",\"instr\":"<<t.instr<<",\"addr\":"<<t.addr<<",\"strobe\":"<<t.strobe<<",\"wdata\":"<<t.wdata<<",\"delay\":"<<t.selected_delay<<",\"d_I\":"<<d_I_<<",\"d_D\":"<<d_D_<<"}\n";
            }
            const auto& t=transactions_[tracked_];
            check(t.instr==d.mem_instr&&t.addr==d.mem_addr&&t.strobe==d.mem_wstrb&&(!t.strobe||t.wdata==d.mem_wdata),"OBS memory stability");
            check(driver_selected_delay==t.selected_delay,"OBS driver delay changed");
            check(bool(d.mem_ready)==(c-t.first>=t.selected_delay),"OBS selected delay changed");
        } else check(tracked_==NONE,"OBS memory request lost");
        if(d.sample_cycle) {
            if(d.cpu_pc==cs_) {check(raw_start_==NONE,"OBS repeated raw start");raw_start_=c;boundary("RAW_START",c);}
            else {check(d.cpu_pc==ce_&&raw_start_!=NONE&&raw_end_==NONE,"OBS ambiguous raw end");raw_end_=c;boundary("RAW_END",c);}
        }
        if(d.sample_instr) event("INSTRUCTION_CSR_SAMPLE","PRE",c)<<",\"pc\":"<<d.cpu_pc<<",\"counter\":"<<d.instruction_counter<<"}\n";
        if(d.mem_valid&&!d.mem_ready) {
            auto& t=transactions_[tracked_];++t.waits;waits_.push_back({c,t.instr});
            event("MEM_PENDING","PRE",c)<<",\"id\":"<<t.id<<",\"age\":"<<c-t.first<<",\"waits\":"<<t.waits<<"}\n";
        }
        if(d.pcpi_valid) {
            if(!pcpi_active_) {
                check(!pcpi_rf_pending_,"OBS PCPI request before previous RF");
                pcpi_active_=true;pcpi_done_=false;pcpi_first_=c;pcpi_word_=d.pcpi_insn;pcpi_rd_=(d.pcpi_insn>>7)&31;pcpi_pc_=d.cpu_pc;
                event("PCPI_REQUEST","PRE",c)<<",\"id\":"<<pcpi_id_<<",\"insn\":"<<pcpi_word_<<",\"pc\":"<<pcpi_pc_<<",\"rs1\":"<<d.pcpi_rs1<<",\"rs2\":"<<d.pcpi_rs2<<"}\n";
            }
            check(pcpi_word_==d.pcpi_insn,"OBS PCPI identity changed");
        } else if(pcpi_active_) {
            check(pcpi_done_,"OBS PCPI lost completion");pcpi_active_=false;
        }
    }
    template<class D> void post(const D& d,unsigned c,bool kernel,bool started,bool ended,unsigned kstart,unsigned kend) {
        check(c==cycle_&&d.cycle_counter==uint64_t(c)+1,"OBS POST edge mapping");
        for(size_t i=0;i<pre_.size();++i) samples_<<(i?"\t":"")<<pre_[i];
        samples_<<'\t'<<d.cpu_pc<<'\t'<<d.cycle_counter<<'\t'<<d.instruction_counter<<'\t'<<(pre_[29]?d.registers[pre_[30]]:0)
                <<'\t'<<kernel<<'\t'<<started<<'\t'<<ended<<'\t'<<kstart<<'\t'<<kend<<'\n';
        if(pre_[2]&&pre_[3]) {
            check(tracked_!=NONE,"OBS completion without request");
            auto& t=transactions_[tracked_];check(t.complete==NONE,"OBS duplicate completion");
            t.complete=c;check(c-t.first==t.selected_delay&&t.waits==t.selected_delay,"OBS wait sample count");
            event("MEM_COMPLETE","POST",c)<<",\"id\":"<<t.id<<",\"instr\":"<<t.instr<<",\"addr\":"<<t.addr<<",\"strobe\":"<<t.strobe<<",\"wdata\":"<<pre_[7]<<",\"rdata\":"<<pre_[8]<<",\"first_cycle\":"<<t.first<<",\"waits\":"<<t.waits<<"}\n";
            tracked_=NONE;
        }
        if(pcpi_rf_pending_) {
            check(pre_[29]&&pre_[30]==pcpi_rd_&&pre_[31]==pcpi_value_&&d.registers[pcpi_rd_]==pcpi_value_,"OBS actual PCPI RF");
            event("PCPI_RF","POST",c)<<",\"id\":"<<pcpi_id_<<",\"rd\":"<<pcpi_rd_<<",\"value\":"<<d.registers[pcpi_rd_]<<",\"request_cycle\":"<<pcpi_first_<<",\"observed_complete_cycle\":"<<pcpi_complete_<<"}\n";
            pcpi_rf_pending_=false;++pcpi_id_;
        }
        if(pre_[15]&&pre_[20]) {
            check(pcpi_active_&&!pcpi_done_&&pre_[21],"OBS PCPI completion identity");
            pcpi_done_=true;pcpi_rf_pending_=true;pcpi_complete_=c;pcpi_value_=pre_[22];
            event("PCPI_COMPLETE","POST",c)<<",\"id\":"<<pcpi_id_<<",\"rd\":"<<pcpi_rd_<<",\"value\":"<<pcpi_value_<<",\"request_cycle\":"<<pcpi_first_<<"}\n";
        }
        if(pre_[32]) event("CPU_LAUNCH","POST",c)<<",\"pc\":"<<d.cpu_pc<<"}\n";
        if(pre_[29]) event("CPU_RF","POST",c)<<",\"rd\":"<<pre_[30]<<",\"value\":"<<d.registers[pre_[30]]<<",\"pre_pc\":"<<pre_[10]<<"}\n";
        if(started&&kernel_start_==NONE) {check(kstart==c,"OBS kernel start phase");kernel_start_=c;event("KERNEL_START","POST",c)<<"}\n";}
        if(ended&&kernel_end_==NONE) {check(kend==c,"OBS kernel end phase");kernel_end_=c;event("KERNEL_END","POST",c)<<"}\n";}
    }
    void finish(uint64_t raw,unsigned kernel_cycles) {
        check(raw_start_!=NONE&&raw_end_!=NONE&&raw_end_-raw_start_==raw,"OBS raw interval mismatch");
        check(kernel_start_!=NONE&&kernel_end_!=NONE&&kernel_end_-kernel_start_==kernel_cycles,"OBS kernel interval mismatch");
        check(!pcpi_active_&&!pcpi_rf_pending_,"OBS PCPI incomplete at finish");
        std::array<unsigned,2> first{},completed{},wait{};
        unsigned cross_start=0,cross_end=0,before_inside=0,inside_after=0,span=0,open=0;
        const auto inside=[&](unsigned c){return c>=raw_start_&&c<raw_end_;};
        for(const auto& t:transactions_) {
            if(inside(t.first)) ++first[t.instr];
            if(t.complete!=NONE&&inside(t.complete)) ++completed[t.instr];
            const bool a=t.first<raw_start_&&(t.complete==NONE||t.complete>=raw_start_);
            const bool b=t.first<raw_end_&&(t.complete==NONE||t.complete>=raw_end_);
            cross_start+=a;cross_end+=b;
            const bool bi=t.first<raw_start_&&t.complete!=NONE&&inside(t.complete);
            const bool ia=inside(t.first)&&(t.complete==NONE||t.complete>=raw_end_);
            before_inside+=bi;inside_after+=ia;span+=a&&b;open+=t.complete==NONE;
            if(a||b||t.complete==NONE)
                event("MEM_BOUNDARY_CLASSIFICATION","SUMMARY",cycle_)<<",\"id\":"<<t.id<<",\"cross_start\":"<<a<<",\"cross_end\":"<<b<<",\"before_to_inside\":"<<bi<<",\"inside_to_after\":"<<ia<<",\"span_both\":"<<(a&&b)<<",\"open_at_end\":"<<(t.complete==NONE)<<"}\n";
        }
        for(const auto& w:waits_) if(inside(w.first)) ++wait[w.second];
        std::ofstream summary("observer-summary.json");
        summary<<"{\"b_start\":"<<raw_start_+5<<",\"b_end\":"<<raw_end_+5<<",\"kernel_start_edge\":"<<kernel_start_+5<<",\"kernel_end_edge\":"<<kernel_end_+5
               <<",\"raw_i_first\":"<<first[1]<<",\"raw_i_completed\":"<<completed[1]<<",\"raw_d_first\":"<<first[0]<<",\"raw_d_completed\":"<<completed[0]
               <<",\"raw_i_wait_samples\":"<<wait[1]<<",\"raw_d_wait_samples\":"<<wait[0]<<",\"cross_start\":"<<cross_start<<",\"cross_end\":"<<cross_end
               <<",\"before_to_inside\":"<<before_inside<<",\"inside_to_after\":"<<inside_after<<",\"span_both\":"<<span<<",\"open_at_end\":"<<open
               <<",\"all_transactions_first\":"<<transactions_.size()<<",\"all_transactions_completed\":"<<transactions_.size()-open<<"}\n";
        summary.flush();samples_.flush();events_.flush();
        check(bool(summary)&&bool(samples_)&&bool(events_),"OBS output write failure");
    }
};
