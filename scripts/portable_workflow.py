"""DRAFT — NOT RELEASE-APPROVED. No candidate execution occurred in P9-S04A."""
import argparse
import json
from measurement_parser import parse_measurement, require_result
from fractions import Fraction
import re
import sys
sys.dont_write_bytecode = True
from release_common import ROOT, identity, new_output, run, source, tool, write_json

def build_sim(args, out, top, prefix, sources, bench, strict=False):
    verilator, make, cxx = tool(args.verilator), tool(args.make), tool(args.cxx)
    for name, exe in (("verilator", verilator), ("make", make), ("cxx", cxx)):
        run([exe, "--version"], out, name + "-version")
    obj = out / "obj"
    cmd = [verilator, "--cc", "--exe", "--timescale", "1ns/1ps",
           "--top-module", top, "--prefix", prefix, "--Mdir", obj,
           "-CFLAGS", "-std=c++17 -Wall -Wextra"]
    if strict:
        cmd.append("--Wall")
    cmd += [source(s) for s in sources] + [source(bench)]
    run(cmd, out, "verilate", reject_warnings=True)
    run([make, "-C", obj, "-f", prefix + ".mk", "-j", "2", "CXX=" + cxx],
        out, "compile", reject_warnings=True)
    exe = obj / prefix
    if not exe.is_file():
        raise RuntimeError("Expected simulator was not generated; host compatibility unverified")
    return exe

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workflow", choices=["W1", "W2", "W3", "W4", "W5"])
    p.add_argument("--out", required=True, help="Fresh ID under candidate/_runs")
    p.add_argument("--verilator", default="verilator")
    p.add_argument("--make", default="make")
    p.add_argument("--cxx", default="g++")
    p.add_argument("--riscv-prefix", default="riscv32-unknown-elf-")
    args = p.parse_args()
    out = new_output(args.out)
    run([sys.executable, "--version"], out, "python-version")
    if args.workflow == "W1":
        run([sys.executable, "-B", "-m", "unittest", "discover", "-s", source("tests/test_dot4_reference.py").parent,
             "-p", "test_dot4_reference.py", "-v"], out, "reference-tests")
    elif args.workflow == "W2":
        vectors, metadata = out / "vectors.txt", out / "vector-metadata.json"
        run([sys.executable, "-B", source("verification/generate_dot4_vectors.py"), vectors, metadata], out, "generate-vectors")
        exe = build_sim(args, out, "dot4_unit", "Vdot4_unit", ["rtl/dot4_unit.sv"], "verification/dot4_tb.cpp", True)
        text = run([exe, vectors], out, "simulation")
        if "DOT4_RTL_PASS directed=18 lane=16 random=10000 total=10034" not in text:
            raise RuntimeError("Missing expected standalone arithmetic completion marker")
        fields = vectors.read_text().splitlines()[0].split()
        fields[-1] = f"{int(fields[-1], 16) ^ 1:08x}"
        bad, empty = out / "intentional-mismatch.txt", out / "intentional-empty.txt"
        bad.write_text(" ".join(fields) + "\n", encoding="ascii")
        empty.write_text("", encoding="ascii")
        if "MISMATCH " not in run([exe, bad], out, "negative-mismatch", expected=1):
            raise RuntimeError("Negative mismatch diagnostic missing")
        if "TESTBENCH_ERROR COUNT_ERROR " not in run([exe, empty], out, "negative-empty", expected=2):
            raise RuntimeError("Negative empty diagnostic missing")
    elif args.workflow == "W3":
        exe = build_sim(args, out, "pcpi_dot4", "Vpcpi_dot4",
                        ["rtl/pcpi_dot4.sv", "rtl/dot4_unit.sv"], "verification/pcpi/dot4_pcpi_tb.cpp")
        if "ADAPTER_PASS " not in run([exe], out, "pcpi-simulation"):
            raise RuntimeError("PCPI completion marker missing")
    else:
        from source_firmware import prepare
        inputs = prepare(args, out)
        exe = build_sim(args, out, "p12_benchmark_bf", "Vbenchmark_soc",
                        ["rtl/integration/p12_benchmark_bf.sv", "rtl/integration/p12_top_bf.sv",
                         "third_party/picorv32/picorv32.v", "rtl/pcpi_dot4.sv", "rtl/dot4_unit.sv"],
                        "verification/cpu/benchmark_tb.cpp")
        results = []
        delays = [0] if args.workflow == "W4" else [0, 3]
        repeats = [0] if args.workflow == "W4" else range(3)
        for delay in delays:
            for repeat in repeats:
                for kind, image, fixture in inputs:
                    label = f"{kind}-d{delay}-r{repeat}"
                    work = out / label
                    work.mkdir()
                    text = run([exe, image, fixture, "0", str(delay), "scalar" if kind == "s2" else "dot4"],
                               out, label, cwd=work)
                    lines = text.splitlines()
                    measures = [s for s in lines if s.startswith("MEASURE ")]
                    if "PASS" not in lines or len(measures) != 1:
                        raise RuntimeError(f"{label}: missing unique measurement or PASS")
                    values = parse_measurement(measures[0])
                    expected = json.loads((out / "generated-inputs.json").read_text())["expected_u32"]
                    require_result(values["result"], expected)
                    results.append({"kind": kind, "d_I": 0, "d_D": delay, "repeat": repeat, "metrics": values})
        comparisons = []
        for delay in (delays if args.workflow == "W5" else []):
            for repeat in repeats:
                pair = {r["kind"]: r["metrics"] for r in results if r["d_D"] == delay and r["repeat"] == repeat}
                baseline, custom = pair["s2"], pair["dot4"]
                if baseline["result"] != custom["result"] or custom["raw_cycles"] <= 0 or custom["kernel_cycles"] <= 0:
                    raise RuntimeError("Invalid matched S2/DOT4 measurement pair")
                comparisons.append({"d_I": 0, "d_D": delay, "repeat": repeat,
                    "raw_cycle_ratio_s2_over_dot4": str(Fraction(baseline["raw_cycles"], custom["raw_cycles"])),
                    "kernel_cycle_ratio_s2_over_dot4": str(Fraction(baseline["kernel_cycles"], custom["kernel_cycles"])),
                    "s2_raw_minus_kernel": baseline["raw_cycles"] - baseline["kernel_cycles"],
                    "dot4_raw_minus_kernel": custom["raw_cycles"] - custom["kernel_cycles"]})
        write_json(out / "measurements.json", {"scope": "NEW candidate execution, not historical replay",
                   "runs": results, "matched_comparisons": comparisons})
    write_json(out / "completion.json", {"workflow": args.workflow, "status": "COMMANDS_COMPLETED",
               "scope": "Future local run only; independent reproduction and release approval not implied"})

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"WORKFLOW_FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
