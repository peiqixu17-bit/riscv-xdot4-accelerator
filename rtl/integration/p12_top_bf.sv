// Task008 preparation only: native memory boundary; no RAM, IO buffers or debug taps.
// CPU parameters match frozen P4/P5. No keep/dont_touch attributes.
`timescale 1ns/1ps
module p12_top_bf (
    input wire clk, resetn,
    output wire trap, mem_valid, mem_instr,
    input wire mem_ready,
    output wire [31:0] mem_addr, mem_wdata,
    output wire [3:0] mem_wstrb,
    input wire [31:0] mem_rdata
);
    wire pcpi_valid, pcpi_wait, pcpi_ready, pcpi_wr;
    wire [31:0] pcpi_insn, pcpi_rs1, pcpi_rs2, pcpi_rd;
    picorv32 #(
        .ENABLE_COUNTERS(1), .ENABLE_COUNTERS64(1),
        .ENABLE_REGS_16_31(1), .ENABLE_REGS_DUALPORT(1),
        .LATCHED_MEM_RDATA(0), .TWO_STAGE_SHIFT(1), .BARREL_SHIFTER(0),
        .TWO_CYCLE_COMPARE(0), .TWO_CYCLE_ALU(0), .COMPRESSED_ISA(0),
        .CATCH_MISALIGN(1), .CATCH_ILLINSN(1), .ENABLE_PCPI(1),
        .ENABLE_MUL(0), .ENABLE_FAST_MUL(1), .ENABLE_DIV(0),
        .ENABLE_IRQ(0), .ENABLE_IRQ_QREGS(0), .ENABLE_IRQ_TIMER(0),
        .ENABLE_TRACE(0), .REGS_INIT_ZERO(0),
        .MASKED_IRQ(32'h00000000), .LATCHED_IRQ(32'hffffffff),
        .PROGADDR_RESET(0), .PROGADDR_IRQ(32'h10), .STACKADDR(32'hffffffff)
    ) cpu (
        .clk(clk), .resetn(resetn), .trap(trap),
        .mem_valid(mem_valid), .mem_instr(mem_instr), .mem_ready(mem_ready),
        .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb), .mem_rdata(mem_rdata),
        .mem_la_read(), .mem_la_write(), .mem_la_addr(), .mem_la_wdata(), .mem_la_wstrb(),
        .pcpi_valid(pcpi_valid), .pcpi_insn(pcpi_insn), .pcpi_rs1(pcpi_rs1), .pcpi_rs2(pcpi_rs2),
        .pcpi_wait(pcpi_wait), .pcpi_ready(pcpi_ready), .pcpi_wr(pcpi_wr), .pcpi_rd(pcpi_rd),
        .irq(32'b0), .eoi(), .trace_valid(), .trace_data()
    );
    pcpi_dot4 accelerator (
        .clk(clk), .resetn(resetn), .pcpi_valid(pcpi_valid), .pcpi_insn(pcpi_insn),
        .pcpi_rs1(pcpi_rs1), .pcpi_rs2(pcpi_rs2), .pcpi_wait(pcpi_wait),
        .pcpi_ready(pcpi_ready), .pcpi_wr(pcpi_wr), .pcpi_rd(pcpi_rd)
    );
endmodule

