"""Independent mathematical model of four signed INT8 dot-product lanes.

Inputs and output are unsigned 32-bit *register bit patterns*, not register
indices. Lane 0 occupies bits [7:0]; lane 3 occupies bits [31:24]. No CPU, XIF,
instruction decoder, fixed-width arithmetic library, or future RTL is used.

Python integers preserve the exact mathematical sum. Masking the final sum
only converts a possibly negative integer into its 32-bit two's-complement
representation; the specified DOT4 operation cannot overflow signed 32 bits.

See docs/DOT4_ISA_SPEC.md for register aliasing, x0, and architectural effects.
In particular, discarding a result destined for x0 is the CPU's responsibility,
not the responsibility of this two-input arithmetic function.
"""

import argparse

UINT32_MAX = (1 << 32) - 1


def signed_lanes(register: int) -> tuple[int, int, int, int]:
    """Return signed lanes in increasing bit-position order (low byte first).

    Accept only built-in int values in [0, 2**32 - 1]. Reject bool, float,
    strings, and integer subclasses with TypeError; reject out-of-range ints
    with ValueError. Inputs are never silently truncated or coerced.
    """
    if type(register) is not int:
        raise TypeError("register must be a built-in int, not bool or another type")
    if not 0 <= register <= UINT32_MAX:
        raise ValueError("register must be an unsigned 32-bit bit pattern")

    lanes = []
    for index in range(4):
        byte = (register >> (8 * index)) & 0xFF
        # Two's complement: byte 0x80..0xFF denotes -128..-1.
        lanes.append(byte if byte < 0x80 else byte - 0x100)
    return tuple(lanes)


def dot4(rs1: int, rs2: int) -> int:
    """Return the 32-bit bit pattern of sum(signed8(a_i) * signed8(b_i)).

    The exact sum lies in [-65024, 65536]. Both operands use the validation
    contract of signed_lanes(). There is no accumulator or persistent state.
    """
    a = signed_lanes(rs1)
    b = signed_lanes(rs2)
    total = sum(x * y for x, y in zip(a, b))
    return total & UINT32_MAX


def main() -> None:
    """Small command-line example; supports decimal and 0x-prefixed operands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rs1", type=lambda text: int(text, 0))
    parser.add_argument("rs2", type=lambda text: int(text, 0))
    args = parser.parse_args()
    try:
        result = dot4(args.rs1, args.rs2)
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    signed = result if result < (1 << 31) else result - (1 << 32)
    print(f"0x{result:08x} (signed {signed})")


if __name__ == "__main__":
    main()
