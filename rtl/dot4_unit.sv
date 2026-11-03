// Standalone signed INT8 DOT4 arithmetic. No clock, state, or XIF interface.
// Arithmetic contract: docs/DOT4_ISA_SPEC.md. Lane 0 is the low byte.
module dot4_unit (
    input  logic [31:0] operand_a,
    input  logic [31:0] operand_b,
    output logic [31:0] result
);
    logic signed [7:0]  lane_a [0:3];
    logic signed [7:0]  lane_b [0:3];
    logic signed [15:0] product [0:3];
    logic signed [16:0] pair_sum_01;
    logic signed [16:0] pair_sum_23;
    logic signed [17:0] total;

    for (genvar i = 0; i < 4; i++) begin : gen_lanes
        // A part-select is unsigned; explicitly interpret its sign bit.
        assign lane_a[i] = $signed(operand_a[8*i +: 8]);
        assign lane_b[i] = $signed(operand_b[8*i +: 8]);
        // Signed multiplication in the 16-bit assignment context preserves
        // the complete 8-by-8 product, including (-128) * (-128) = 16384.
        assign product[i] = lane_a[i] * lane_b[i];
    end

    // Widen BEFORE adding. Concatenations are unsigned unless cast explicitly.
    assign pair_sum_01 = $signed({product[0][15], product[0]})
                       + $signed({product[1][15], product[1]});
    assign pair_sum_23 = $signed({product[2][15], product[2]})
                       + $signed({product[3][15], product[3]});
    assign total = $signed({pair_sum_01[16], pair_sum_01})
                 + $signed({pair_sum_23[16], pair_sum_23});

    // Exact sum is in [-65024, 65536]. Return its 32-bit two's-complement bits.
    assign result = {{14{total[17]}}, total};
endmodule
