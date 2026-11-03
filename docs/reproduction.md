# W1–W5 Reproduction Guide

Run the following commands from the repository root in a fresh working copy with qualified tools configured. Use a new --out identifier for every attempt; outputs stay under _runs/. Do not publish those outputs. No original research directory is required by W1–W5. Set PATH or supply --verilator, --make, --cxx and --riscv-prefix (with trailing hyphen). Scripts do not install tools or access the network. These are the same eight commands qualified in S06; this revision has not been executed.

```text
python3 -B scripts/portable_workflow.py W1 --out w1-001
python3 -B scripts/portable_workflow.py W2 --out w2-001
python3 -B scripts/portable_workflow.py W3 --out w3-001
python3 -B scripts/parser_regression.py --out parser-001
python3 -B scripts/portable_workflow.py W4 --out w4-smoke-001 --riscv-prefix riscv32-corev-elf-
python3 -B scripts/run_targeted.py --out w4-targeted-001 --riscv-prefix riscv32-corev-elf-
python3 -B scripts/portable_workflow.py W5 --out w5-001 --riscv-prefix riscv32-corev-elf-
python3 -B scripts/verify_w5.py --measurements _runs/w5-001/measurements.json --out w5-check-001
```

W4 targeted uses its separate read-only raw-RF wrapper; W5 uses original performance wrapper. Run parser gate before CPU workflows. W2 requires unique arithmetic PASS and negative exits; W3 requires adapter completion; W4 requires checked CPU execution; targeted checks nine cases/all registers; W5 must pass BOTH execution and independent comparison/repeat gate. Keep all failed attempts; never change a model/fixture to match historical counters. W5 fixed orderdelay0 then3,repeat0/1/2,S2 thenDOT4,12 fresh processes. No warm-up, no empty subtraction. W5 output identity may be tool/version-sensitive; Each future reproduction must compare approved source/input/firmware hashes before accepting performance.

Use Linux/Ubuntu22.04 or equivalent qualified WSL environment, Python3.10.12, Verilator5.008, GNU Make4.3, G++11.4.0, RISC-V GCC14.1.0 and binutils2.42.50.20240416 for comparable W4/W5 results. W1 and data tooling require standard-library Python>=3.10; that does not relax targeted W4's exact-version assertions. Do not use Python -O/-OO or PYTHONOPTIMIZE. Configure PATH before launch or explicit tool paths resolved relative to the repository launch directory. Required binutils: ld, objcopy, objdump, readelf, nm. Firmware GCC requires its linker/assembler/runtime installation, not only the gcc executable. Verilator requires its share/runtime headers and C++ sources; generated V*.h and makefiles are future outputs, not missing source files.

The optional timestamp guard must be executable in the new Linux working copy. Set GNU_MAKE to an absolute path (or plain make resolved on PATH); do not set it to the guard itself. Both CPU runners resolve --make/--cxx/--verilator before changing child cwd. Keep failed output trees. Check all source-package hashes, tool versions, parser gate and newly generated W5 input/firmware/fixture identities against data/w5/input_provenance.json before accepting numerical comparisons; a mismatch is a stop, never permission to tune counters. No build or execution was performed for this documentation revision.

## W6 exclusion

The retained scripts/reconstruct_w6.py is an incomplete historical draft, not an approved public reproduction entry point. No W6 observations, prediction locks, internal data directory or event archive is supplied. Do not run it as a Tier 1 acceptance gate or infer that supplying data would complete its missing schema/policy/figure contract. Historical internal numerical reconstruction remains separate evidence. Tier 2 is excluded.

## Evidence and output policy

S06-LIMITED qualified W1–W5 from revision 0.1.1 in a fresh same-machine Ubuntu/WSL copy. The executable sources and eight reproduction commands are unchanged in this revision; no new run is claimed. This is not external independent reproduction. Full ELF/simulator bytes were not reproducible because of documented build metadata/source paths, although machine-code images, inputs, fixtures and the scoped results matched.

W6 historical internal numerical reconstruction is separate evidence. The portable public Tier 1 consumer is incomplete; Tier 2 event reconstruction and restricted internal datasets are excluded. No W6 dataset is provided by this repository, and no external private data directory is required for W1–W5. FPGA reproduction, board validation, full physical timing closure, energy and general DSP benefit are not established.

See the [source package boundary](#source-package-boundary) and [RELEASE-FILES.txt](../RELEASE-FILES.txt). Retain all successful and failed attempts privately; do not export _runs/ or build logs.

## Source package boundary

[RELEASE-FILES.txt](../RELEASE-FILES.txt) is the exact path allowlist for this source package, including itself. For source-package preparation, copy only those files from this repository root into a new empty staging directory. Reject absolute paths, parent traversal, duplicates, missing files and symlinks. Require the staged path set to equal the allowlist exactly; compare every size and SHA-256 against the externally sealed candidate_manifest.json maintained with the private review record for the corresponding version. The allowlist defines paths; the sealed manifest defines bytes. Do not copy the surrounding research project or audit directory.

No filesystem-wide or recursive project export is permitted by this packaging policy. Keep _runs/, caches, local environment files, generated model/firmware/fixture/build artifacts and private evidence outside the staged set. .gitignore provides defense in depth; ignore rules alone are not the export authority. Preserve approved PNG figures, W5 CSV/JSON and all license notices. Keep failed runs in private storage, never include them in the public staging set. Any changed or extra release file requires a new reviewed manifest.

