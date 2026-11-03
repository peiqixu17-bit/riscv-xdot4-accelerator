# Dependencies, licensing and limitations — 0.1.5-private-s08r01

DRAFT — NOT RELEASE-APPROVED. Author: Peiqi Xu.

Qualified environment: Ubuntu 22.04/WSL, Python 3.10.12, Verilator 5.008, GNU Make 4.3, GCC/G++ 11.4.0, CORE-V RISC-V GCC 14.1.0 and binutils 2.42.50.20240416. Full compiler/assembler/linker/runtime installations and Verilator headers/runtime are required, alongside Perl and a POSIX shell. No executables are bundled. Other native platforms are not qualified.

Use PATH or CLI tool selection. Required binutils include ld, objcopy, objdump, readelf and nm. CPU firmware uses RV32I_Zmmul / ILP32, -O3, freestanding, no standard startup/library, build-id disabled. Python standard-library helpers require >=3.10, but exact W4/W5 environment assertions still apply. Disable Python optimization. See reproduction.md for the executable timestamp guard, GNU_MAKE and fresh-output requirements. No Vivado is required for W1–W5; FPGA reproduction is excluded.

PicoRV32 recorded local commit ef203c2b0a3fb793280f5114941416c425c5b461; no new remote verification. The original source and third_party/picorv32/COPYING retain their copyright, ISC license and disclaimer. External compiler/simulator installations are not redistributed.

S06-LIMITED qualified W1–W5 from revision 0.1.1 in a fresh same-machine Ubuntu/WSL copy. The executable sources and eight reproduction commands are unchanged in this revision; no new run is claimed. This is not external independent reproduction. Full ELF/simulator bytes were not reproducible because of documented build metadata/source paths, although machine-code images, inputs, fixtures and the scoped results matched.

W6 historical internal numerical reconstruction is separate evidence. The portable public Tier 1 consumer is incomplete; Tier 2 event reconstruction and restricted internal datasets are excluded. No W6 dataset is provided by this candidate, and no external private data directory is required for W1–W5. FPGA reproduction, board validation, full physical timing closure, energy and general DSP benefit are not established.

Current licensing is implemented through LICENSE-MAP.json and ATTRIBUTION.md: original RTL under CERN-OHL-P-2.0, original software under Apache-2.0, and original documentation/figures/data under CC-BY-4.0. PicoRV32 retains its ISC notices. A09 firmware/link.ld original portions are covered by Apache-2.0 on Peiqi Xu's first-hand declaration and a narrow check finding no specific conflicting evidence; authorship is not independently certified. Historical Q12 remains unresolved, with no inferred rights for other linker files. Historical Q18 fixtures remain excluded. Copyright years are not invented.

Publication remains separately gated. Required license texts are in LICENSES/. Private audit history and restricted W6 data are not candidate dependencies or distributed content. See [packaging policy](../README.md) for the exact export boundary.
