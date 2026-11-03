// Standalone Verilator harness. Expected values come ONLY from the vector file.
// This file has no multiplication, lane extraction, or dot-product oracle.
#include "Vdot4_unit.h"
#include "verilated.h"

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

static uint32_t hex_word(const std::string& token) {
    if (token.size() != 8 || !std::all_of(token.begin(), token.end(),
            [](unsigned char c) { return std::isxdigit(c) != 0; })) {
        throw std::runtime_error("expected exactly eight hex digits: " + token);
    }
    return static_cast<uint32_t>(std::stoul(token, nullptr, 16));
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: Vdot4_unit vectors.txt\n";
        return 2;
    }
    std::ifstream input(argv[1]);
    if (!input) {
        std::cerr << "Cannot open vector file: " << argv[1] << '\n';
        return 2;
    }
    VerilatedContext context;
    context.commandArgs(argc, argv);
    Vdot4_unit dut(&context);
    unsigned directed = 0, lane = 0, random = 0, total = 0;
    std::string line;
    try {
        while (std::getline(input, line)) {
            std::istringstream fields(line);
            std::string kind, name, a_text, b_text, expected_text, extra;
            if (!(fields >> kind >> name >> a_text >> b_text >> expected_text)
                    || (fields >> extra)) {
                throw std::runtime_error("malformed row " + std::to_string(total + 1));
            }
            if (kind == "D") ++directed;
            else if (kind == "L") ++lane;
            else if (kind == "R") ++random;
            else throw std::runtime_error("invalid category: " + kind);

            const uint32_t a = hex_word(a_text);
            const uint32_t b = hex_word(b_text);
            const uint32_t expected = hex_word(expected_text);
            dut.operand_a = a;
            dut.operand_b = b;
            dut.eval();  // Settle combinational logic; no clock or time step.
            const uint32_t actual = dut.result;
            ++total;
            if (actual != expected) {
                std::cerr << "MISMATCH row=" << total << " kind=" << kind
                          << " case=" << name << std::hex << std::setfill('0')
                          << " a=0x" << std::setw(8) << a
                          << " b=0x" << std::setw(8) << b
                          << " expected=0x" << std::setw(8) << expected
                          << " actual=0x" << std::setw(8) << actual << '\n';
                dut.final();
                return 1;
            }
            if (kind == "D") {
                std::cout << "DIRECTED_PASS " << name << std::hex << std::setfill('0')
                          << " a=" << std::setw(8) << a << " b=" << std::setw(8) << b
                          << " expected=" << std::setw(8) << expected
                          << " actual=" << std::setw(8) << actual << std::dec << '\n';
            }
        }
        if (input.bad()) throw std::runtime_error("vector file read error");
        // Reject empty/truncated/extra files; never allow a vacuous PASS.
        if (directed != 18 || lane != 16 || random != 10000 || total != 10034) {
            throw std::runtime_error("COUNT_ERROR directed=" + std::to_string(directed)
                + " lane=" + std::to_string(lane) + " random=" + std::to_string(random)
                + " total=" + std::to_string(total));
        }
    } catch (const std::exception& error) {
        std::cerr << "TESTBENCH_ERROR " << error.what() << '\n';
        dut.final();
        return 2;
    }
    dut.final();
    std::cout << "DOT4_RTL_PASS directed=" << directed << " lane=" << lane
              << " random=" << random << " total=" << total << '\n';
    return 0;
}
