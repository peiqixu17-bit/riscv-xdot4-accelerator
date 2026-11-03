"""DRAFT — NOT RELEASE-APPROVED. New source-based inputs, never archived binary inputs.
Recipe adapted from the eligible Task015 experiment/build records. Equivalence untested.
"""
import random
import re
import struct
from release_common import identity, run, source, tool, write_json
from cpu_oracle import trace
from dot4_reference import dot4

def prepare(args, out):
    gcc, objcopy, nm = [tool(args.riscv_prefix + s) for s in ("gcc", "objcopy", "nm")]
    for name, exe in (("gcc", gcc), ("objcopy", objcopy), ("nm", nm)):
        run([exe, "--version"], out, name + "-version")
    elf, raw = out / "firmware.elf", out / "firmware.bin"
    run([gcc, "-O3", "-march=rv32i_zmmul", "-mabi=ilp32", "-nostdlib", "-nostartfiles",
         "-ffreestanding", "-Wl,--build-id=none", "-Wl,-T," + str(source("firmware/link.ld")),
         source("firmware/firmware.S"), source("firmware/scalar.c"), "-o", elf],
        out, "firmware-compile", reject_warnings=True)
    run([objcopy, "-O", "binary", elf, raw], out, "firmware-objcopy")
    text = run([nm, "-n", "-S", elf], out, "firmware-symbols")
    symbols = {name: int(addr, 16) for addr, name in re.findall(
        r"^([0-9a-fA-F]+) (?:[0-9a-fA-F]+ )?[Tt] (\w+)$", text, re.M)}
    needed = {"s2_kernel", "dot4_kernel", "cycle_start", "inst_start", "inst_end", "cycle_end"}
    if not needed <= symbols.keys():
        raise RuntimeError("Required symbols missing: " + str(sorted(needed - symbols.keys())))
    code = raw.read_bytes()
    if not 0 < len(code) < 0x600 or len(code) % 4:
        raise RuntimeError("Firmware violates the reserved code region / 32-bit instruction boundary")
    for label, word in (("cycle_start", 0xc0002473), ("inst_start", 0xc02024f3),
                        ("inst_end", 0xc0202973), ("cycle_end", 0xc00029f3)):
        if symbols[label] + 4 > len(code) or struct.unpack_from("<I", code, symbols[label])[0] != word:
            raise RuntimeError("Counter encoding or layout changed: " + label)
    if args.workflow == "W4":
        av, bv = bytes([128, 127, 255, 0]), bytes([128, 127, 1, 255])
        dataset = "candidate-boundary-4-v1"
    else:
        rng = random.Random(0x504A)
        av = bytes(rng.getrandbits(8) for _ in range(1024))
        bv = bytes(rng.getrandbits(8) for _ in range(1024))
        dataset = "candidate-random-1024-seed-0x504a-v1"
    signed8 = lambda x: x - 256 if x >= 128 else x
    signed_sum = sum(signed8(a) * signed8(b) for a, b in zip(av, bv))
    expected, words = signed_sum & 0xffffffff, len(av) // 4
    pairs = [(int.from_bytes(av[i:i+4], "little"), int.from_bytes(bv[i:i+4], "little"))
             for i in range(0, len(av), 4)]
    partials = [dot4(a, b) for a, b in pairs]
    signed32 = lambda x: x - (1 << 32) if x >= (1 << 31) else x
    if sum(signed32(x) for x in partials) != signed_sum:
        raise RuntimeError("Independent signed-byte sum and DOT4 reference disagree")
    inputs = []
    for kind in ("s2", "dot4"):
        entry = symbols[kind + "_kernel"]
        image = bytearray(4096)
        image[:len(code)] = code
        image[0x800:0x800 + len(av)] = av
        image[0xc00:0xc00 + len(bv)] = bv
        struct.pack_into("<III", image, 0x700, entry, words, expected)
        traced = trace(image, entry, symbols["inst_end"], words)
        if traced["result"] != expected:
            raise RuntimeError("Instruction oracle disagrees with arithmetic reference")
        if len(traced["loads"]) != words * (8 if kind == "s2" else 2):
            raise RuntimeError("Unexpected input-load count; inspect compiler/ISA compatibility")
        if kind == "s2" and len(traced["muls"]) != len(av):
            raise RuntimeError("Unexpected scalar MUL count")
        head = [expected, words, symbols["cycle_start"], symbols["inst_start"],
                symbols["inst_end"], symbols["cycle_end"], entry]
        lines = ["H " + " ".join(f"{x:x}" for x in head)]
        if kind == "dot4":
            lines += [f"Q {a:x} {b:x} {v:x}" for (a, b), v in zip(pairs, partials)]
        lines += [f"L {addr:x}" for addr in traced["loads"]]
        lines += [f"T {pc:x} {word:x}" for pc, word in traced["steps"]]
        image_path, fixture = out / (kind + ".bin"), out / (kind + ".fixture")
        with image_path.open("xb") as f:
            f.write(image)
        with fixture.open("x", encoding="ascii", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        inputs.append((kind, image_path, fixture))
    (out / "input-a.bin").write_bytes(av)
    (out / "input-b.bin").write_bytes(bv)
    write_json(out / "generated-inputs.json", {
        "dataset": dataset, "n": len(av), "words": words, "expected_u32": expected,
        "a": identity(out / "input-a.bin"), "b": identity(out / "input-b.bin"),
        "firmware": identity(raw), "symbols": symbols,
        "inputs": [{"kind": k, "image": identity(i), "fixture": identity(f)} for k, i, f in inputs],
        "historical_equivalence": "NOT_ESTABLISHED; no archived binaries or fixtures read",
        "qualification": "Requires future independent fixture and CPU validation"})
    return inputs
