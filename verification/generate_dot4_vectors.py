"""Emit external DOT4 vectors; no expected-value arithmetic in the RTL harness.

Reuse the unchanged Task 004A manual constants and golden model. Manual rows
use the literal expected value, after checking the model against that literal.
Random rows use the model. The fixed corpus fingerprint must match Task 004A.
"""

import argparse
import hashlib
import json
from pathlib import Path
import random
import runpy
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.dot4_reference import dot4  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("metadata", type=Path)
    args = parser.parse_args()

    # run_name is not __main__; defining the fixture does not execute unittest.
    fixture = runpy.run_path(str(ROOT / "tests/test_dot4_reference.py"))
    manual = fixture["DIRECTED"]
    seed, count = fixture["SEED"], fixture["RANDOM_PAIRS"]
    if len(manual) != 18 or count < 10_000:
        raise ValueError("Unexpected manual/random corpus size")
    rows = []
    for name, a, b, exact, expected in manual:
        if dot4(a, b) != expected:
            raise ValueError(f"Golden model disagrees with manual case {name}")
        if int.from_bytes(expected.to_bytes(4, "little"), "little", signed=True) != exact:
            raise ValueError(f"Invalid manual bit pattern in {name}")
        rows.append(f"D {name} {a:08x} {b:08x} {expected:08x}\n")

    for a_lane in range(4):
        for b_lane in range(4):
            a, b = 0x80 << (8 * a_lane), 0x7F << (8 * b_lane)
            # Hand calculation: -128*127=-16256 only for aligned lanes.
            expected = 0xFFFFC080 if a_lane == b_lane else 0
            if dot4(a, b) != expected:
                raise ValueError("Golden model disagrees with lane-isolation case")
            rows.append(f"L lane_{a_lane}_{b_lane} {a:08x} {b:08x} {expected:08x}\n")

    rng, corpus = random.Random(seed), hashlib.sha256()
    for i in range(count):
        a, b = rng.getrandbits(32), rng.getrandbits(32)
        expected = dot4(a, b)
        corpus.update(struct.pack("<III", a, b, expected))
        rows.append(f"R random_{i:05d} {a:08x} {b:08x} {expected:08x}\n")
    expected_corpus = "07e793fcc4b37adfb553dbbc80aedd480b70c154043dfddeba7bc3e65bcaf6dd"
    if corpus.hexdigest() != expected_corpus:
        raise ValueError("Random corpus changed from Task 004A; investigate before running RTL")

    data = "".join(rows).encode("ascii")
    with args.output.open("xb") as output:
        output.write(data)
    metadata = dict(directed=len(manual), lane=16, random=count, total=len(rows),
                    seed=f"0x{seed:08x}", random_corpus_sha256=corpus.hexdigest(),
                    vectors_sha256=hashlib.sha256(data).hexdigest(),
                    vectors_bytes=len(data), python=sys.version)
    with args.metadata.open("x") as output:
        json.dump(metadata, output, indent=2)
        output.write("\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
