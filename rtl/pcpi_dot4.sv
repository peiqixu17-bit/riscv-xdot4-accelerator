// Fixed PicoRV32 RV32I/PCPI=1, IRQ/QREGS/M=0 contract.
// E0 capture operands; E1 register arithmetic; E2 complete; E3 drain.
module pcpi_dot4 (
    input logic clk, resetn, pcpi_valid,
    input logic [31:0] pcpi_insn, pcpi_rs1, pcpi_rs2,
    output logic pcpi_wait, pcpi_ready, pcpi_wr,
    output logic [31:0] pcpi_rd
);
    typedef enum logic [1:0] {IDLE, EVAL, RESPONSE, DRAIN} state_t;
    state_t state_q;
    logic [31:0] operand_a_q, operand_b_q, result_q, dot4_result;
    logic live;
    assign live = resetn && pcpi_valid &&
                  ((pcpi_insn & 32'hfe00707f) == 32'h0000000b);
    assign pcpi_wait = live && (state_q != DRAIN);
    assign pcpi_ready = live && (state_q == RESPONSE);
    assign pcpi_wr = pcpi_ready;
    assign pcpi_rd = pcpi_ready ? result_q : 32'b0;

    dot4_unit arithmetic (
        .operand_a(operand_a_q), .operand_b(operand_b_q), .result(dot4_result)
    );

    always_ff @(posedge clk) begin
        if (!resetn) begin
            state_q <= IDLE;
            operand_a_q <= 0;
            operand_b_q <= 0;
            result_q <= 0;
        end else begin
            case (state_q)
                IDLE: if (live) begin
                    operand_a_q <= pcpi_rs1;
                    operand_b_q <= pcpi_rs2;
                    state_q <= EVAL;
                end
                EVAL: if (!pcpi_valid) begin
                    operand_a_q <= 0;
                    operand_b_q <= 0;
                    result_q <= 0;
                    state_q <= IDLE;
                end else begin
                    result_q <= dot4_result;
                    state_q <= RESPONSE;
                end
                RESPONSE: state_q <= DRAIN;
                DRAIN: if (!pcpi_valid) state_q <= IDLE;
                default: state_q <= IDLE;
            endcase
        end
    end
endmodule
