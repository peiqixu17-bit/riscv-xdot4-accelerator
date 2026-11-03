"""Software-only DOT4 checks; no CPU execution or XIF correctness claim.

Run from the project root:
    python3 -u -m unittest discover -s tests -p test_dot4_reference.py -v

Directed expectations are literal, manually derived values. The random oracle
uses the standard library's signed-byte unpacking and signed integer encoding,
not the reference model's shift/mask/sign-conversion helpers.
"""

import hashlib
import random
import struct
import unittest

from scripts.dot4_reference import dot4, signed_lanes

SEED = 0xD0742026
RANDOM_PAIRS = 10_000

# name, rs1 bits, rs2 bits, exact signed sum, final unsigned register bits.
# The calculations for these constants are recorded in DOT4_ISA_SPEC.md.
DIRECTED = (
    ("both_zero", 0x00000000, 0x00000000, 0, 0x00000000),
    ("zero_left", 0x00000000, 0x807FFF01, 0, 0x00000000),
    ("zero_right", 0x807FFF01, 0x00000000, 0, 0x00000000),
    ("positive_asymmetric", 0x04030201, 0x08070605, 70, 0x00000046),
    ("negative_both", 0xFCFDFEFF, 0xF8F9FAFB, 70, 0x00000046),
    ("mixed", 0xFC03FE01, 0x08F906FB, -70, 0xFFFFFFBA),
    ("all_127", 0x7F7F7F7F, 0x7F7F7F7F, 64516, 0x0000FC04),
    ("maximum_sum", 0x80808080, 0x80808080, 65536, 0x00010000),
    ("minimum_sum", 0x80808080, 0x7F7F7F7F, -65024, 0xFFFF0200),
    ("minimum_sum_swapped", 0x7F7F7F7F, 0x80808080, -65024, 0xFFFF0200),
    ("negative_ones", 0xFFFFFFFF, 0xFFFFFFFF, 4, 0x00000004),
    ("opposite_ones", 0xFFFFFFFF, 0x01010101, -4, 0xFFFFFFFC),
    ("lane0_negative_one", 0x000000FF, 0x00000001, -1, 0xFFFFFFFF),
    ("lane3_negative_one", 0xFF000000, 0x01000000, -1, 0xFFFFFFFF),
    ("lane3_negative_128", 0x80000000, 0x01000000, -128, 0xFFFFFF80),
    ("mixed_boundaries", 0x807FFF01, 0x01010101, -1, 0xFFFFFFFF),
    ("cancellation", 0x01FF01FF, 0x01010101, 0, 0x00000000),
    ("lane_permutation", 0x04030201, 0x05060708, 60, 0x0000003C),
)


def independent_oracle(rs1: int, rs2: int) -> tuple[int, int]:
    """Decode signed bytes via struct, then encode an exact signed 32-bit sum."""
    a = struct.unpack("<4b", rs1.to_bytes(4, "little"))
    b = struct.unpack("<4b", rs2.to_bytes(4, "little"))
    exact = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]
    bits = int.from_bytes(exact.to_bytes(4, "little", signed=True), "little")
    return exact, bits


class Dot4ReferenceTests(unittest.TestCase):
    def test_directed_manual_expectations(self):
        for name, a, b, exact, expected in DIRECTED:
            with self.subTest(case=name):
                # Check both the literal encoding and the model's output.
                signed_expected = int.from_bytes(
                    expected.to_bytes(4, "little"), "little", signed=True
                )
                self.assertEqual(signed_expected, exact)
                self.assertEqual(dot4(a, b), expected)
                print(f"DIRECTED {name}: {a:08x} {b:08x} -> {expected:08x} ({exact})")
        print(f"DIRECTED_CASES={len(DIRECTED)}")

    def test_lane_positions_and_cross_lane_isolation(self):
        # A lone -128 and a lone +127 contribute only in the same lane.
        # A permutation applied to both sources leaves a dot product unchanged:
        # this test alone cannot establish the public lane numbering contract.
        for a_lane in range(4):
            for b_lane in range(4):
                with self.subTest(a_lane=a_lane, b_lane=b_lane):
                    expected = 0xFFFFC080 if a_lane == b_lane else 0
                    self.assertEqual(dot4(0x80 << (8 * a_lane),
                                          0x7F << (8 * b_lane)), expected)
        print("LANE_ISOLATION_PAIRS=16")

    def test_signed_lane_numbering(self):
        # Directly check numbering; whole-dot symmetry cannot check it alone.
        for word, expected in (
            (0x04030201, (1, 2, 3, 4)),
            (0x807FFF01, (1, -1, 127, -128)),
            (0x80FF7F00, (0, 127, -1, -128)),
            (0xFFFFFFFF, (-1, -1, -1, -1)),
        ):
            with self.subTest(word=word):
                self.assertEqual(signed_lanes(word), expected)
        print("LANE_NUMBERING_CASES=4")

    def test_out_of_range_inputs(self):
        for invalid in (-1, 1 << 32):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    dot4(invalid, 0)
                with self.assertRaises(ValueError):
                    dot4(0, invalid)
        print("RANGE_REJECTIONS=4")

    def test_non_integer_inputs(self):
        class IntegerSubclass(int):
            pass

        for invalid in (True, False, 1.0, "1", None, [], IntegerSubclass(1)):
            with self.subTest(value=invalid):
                with self.assertRaises(TypeError):
                    dot4(invalid, 0)
                with self.assertRaises(TypeError):
                    dot4(0, invalid)
        print("TYPE_REJECTIONS=14")

    def test_seeded_random_against_independent_oracle(self):
        rng = random.Random(SEED)
        digest = hashlib.sha256()
        for index in range(RANDOM_PAIRS):
            a, b = rng.getrandbits(32), rng.getrandbits(32)
            exact, expected = independent_oracle(a, b)
            with self.subTest(index=index, rs1=f"{a:08x}", rs2=f"{b:08x}"):
                self.assertGreaterEqual(exact, -65024)
                self.assertLessEqual(exact, 65536)
                actual = dot4(a, b)
                self.assertEqual(actual, expected)
                self.assertIs(type(actual), int)
                self.assertGreaterEqual(actual, 0)
                self.assertLessEqual(actual, 0xFFFFFFFF)
                # Useful secondary property; not a substitute for the oracle.
                self.assertEqual(dot4(b, a), expected)
            # Fingerprint the ordered input pairs AND independent expected bits.
            digest.update(struct.pack("<III", a, b, expected))
        print(f"RANDOM_SEED=0x{SEED:08x}")
        print(f"RANDOM_PAIRS={RANDOM_PAIRS}")
        print(f"RANDOM_CORPUS_SHA256={digest.hexdigest()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
