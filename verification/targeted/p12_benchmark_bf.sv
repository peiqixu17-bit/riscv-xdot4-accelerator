// Simulation-only read-only taps; not a synthesis top.
// Test wrapper; all hierarchical signals below are read-only monitor taps.
`timescale 1ns/1ps
module p12_benchmark_bf (
    input logic clk, resetn,
    output wire trap, mem_valid, mem_instr,
    input logic mem_ready,
    output wire [31:0] mem_addr, mem_wdata,
    output wire [3:0] mem_wstrb,
    input logic [31:0] mem_rdata,
    output wire pcpi_valid, pcpi_wait, pcpi_ready, pcpi_wr,
    output wire [31:0] pcpi_insn, pcpi_rs1, pcpi_rs2, pcpi_rd,
    output wire rf_we, raw_rf_we,
    output wire [4:0] rf_addr,
    output wire [31:0] rf_data, x7, x8, cpu_pc,
    output wire [31:0] registers [0:31],
    output wire internal_ready,
    output wire cpu_timeout,
    output wire launch, sample_cycle, sample_instr,
    output wire [63:0] cycle_counter, instruction_counter,
    output wire [1:0] adapter_state,
    output wire [3:0] timeout_counter,
    output wire mul_ready, mul_wr, mul_wait, selected_ready, selected_wr, selected_wait,
    output wire [31:0] mul_rd, selected_rd
);
    p12_top_bf dut (.clk(clk), .resetn(resetn), .trap(trap), .mem_valid(mem_valid), .mem_instr(mem_instr), .mem_ready(mem_ready), .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb), .mem_rdata(mem_rdata));
    assign pcpi_valid = dut.pcpi_valid;
    assign pcpi_wait = dut.pcpi_wait;
    assign pcpi_ready = dut.pcpi_ready;
    assign pcpi_wr = dut.pcpi_wr;
    assign pcpi_insn = dut.pcpi_insn;
    assign pcpi_rs1 = dut.pcpi_rs1;
    assign pcpi_rs2 = dut.pcpi_rs2;
    assign pcpi_rd = dut.pcpi_rd;
    assign mul_ready = dut.cpu.pcpi_mul_ready;
    assign mul_wait = dut.cpu.pcpi_mul_wait;
    assign mul_wr = dut.cpu.pcpi_mul_wr;
    assign mul_rd = dut.cpu.pcpi_mul_rd;
    assign selected_ready = dut.cpu.pcpi_int_ready;
    assign selected_wr = dut.cpu.pcpi_int_wr;
    assign selected_wait = dut.cpu.pcpi_int_wait;
    assign selected_rd = dut.cpu.pcpi_int_rd;
    assign launch = resetn && dut.cpu.launch_next_insn;
    assign sample_cycle = resetn && (dut.cpu.cpu_state == 8'b00100000) && dut.cpu.instr_rdcycle;
    assign sample_instr = resetn && (dut.cpu.cpu_state == 8'b00100000) && dut.cpu.instr_rdinstr;
    assign cycle_counter = dut.cpu.count_cycle;
    assign instruction_counter = dut.cpu.count_instr;
    assign adapter_state = dut.accelerator.state_q;
    assign rf_we = resetn && dut.cpu.cpuregs_write && (dut.cpu.latched_rd != 0);
    assign raw_rf_we = resetn && dut.cpu.cpuregs_write;
    assign rf_addr = dut.cpu.latched_rd;
    assign rf_data = dut.cpu.cpuregs_wrdata;
    assign x7 = dut.cpu.cpuregs[7];
    assign x8 = dut.cpu.cpuregs[8];
    assign cpu_pc = dut.cpu.reg_pc;
    assign cpu_timeout = dut.cpu.pcpi_timeout;
    assign timeout_counter = dut.cpu.pcpi_timeout_counter;
    assign internal_ready = dut.cpu.pcpi_mul_ready || dut.cpu.pcpi_div_ready;
    assign registers[0] = 32'b0;
    for (genvar i=1; i<32; i=i+1) begin : read_only_regs
        assign registers[i] = dut.cpu.cpuregs[i];
    end
endmodule
