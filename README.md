# RISC-V DOT4 — Private Candidate 0.1.5-private-s08r01

DRAFT — NOT RELEASE-APPROVED. Author: Peiqi Xu. Public Release remains NO-GO until separate explicit authorization following final review.

The reproducible core is W1–W5: Python reference arithmetic, standalone DOT4 RTL, PCPI interface tests, CPU smoke/targeted verification and the fixed S2/DOT4 simulated-cycle comparison. DOT4 multiplies four corresponding signed INT8 lanes from two 32-bit sources and sums into a signed 32-bit destination, without accumulation or saturation.

Read [reproduction instructions](docs/reproduction.md), [prerequisites and scope](docs/dependencies.md), and the [research reading draft](docs/research_reading_v0.1.md). The reading draft is an abridged derivative, not the exact internally accepted manuscript or an externally peer-reviewed publication.

S06-LIMITED qualified W1–W5 from revision 0.1.1 in a fresh same-machine Ubuntu/WSL copy. The executable sources and eight reproduction commands are unchanged in this revision; no new run is claimed. This is not external independent reproduction. Full ELF/simulator bytes were not reproducible because of documented build metadata/source paths, although machine-code images, inputs, fixtures and the scoped results matched.

W6 historical internal numerical reconstruction is separate evidence. The portable public Tier 1 consumer is incomplete; Tier 2 event reconstruction and restricted internal datasets are excluded. No W6 dataset is provided by this candidate, and no external private data directory is required for W1–W5. FPGA reproduction, board validation, full physical timing closure, energy and general DSP benefit are not established.

Under the frozen W5 N=1024 conditions, all twelve S06 runs returned 5366. Three process repetitions per implementation/delay gave raw cycles S2/DOT4=23068/8476 at (0,0) and 29212/10012 at (0,3). These are prepacked-input simulated cycle counts, not physical-time or energy gains.

Current licensing is implemented through LICENSE-MAP.json and ATTRIBUTION.md: original RTL under CERN-OHL-P-2.0, original software under Apache-2.0, and original documentation/figures/data under CC-BY-4.0. PicoRV32 retains its ISC notices. A09 firmware/link.ld original portions are covered by Apache-2.0 on Peiqi Xu's first-hand declaration and a narrow check finding no specific conflicting evidence; authorship is not independently certified. Historical Q12 remains unresolved, with no inferred rights for other linker files. Historical Q18 fixtures remain excluded. Copyright years are not invented.

## Packaging boundary

[RELEASE-FILES.txt](RELEASE-FILES.txt) is the exact path allowlist for this candidate, including itself. It is not publication approval. For future separately authorized repository preparation, copy only those files from this candidate root into a new empty staging directory. Reject absolute paths, parent traversal, duplicates, missing files and symlinks. Require the staged path set to equal the allowlist exactly; compare every size and SHA-256 against the externally sealed candidate_manifest.json for this version. The allowlist defines paths; the sealed manifest defines bytes. Do not copy the surrounding research project or audit directory.

No filesystem-wide or recursive project export is permitted by this packaging policy. Keep _runs/, caches, local environment files, generated model/firmware/fixture/build artifacts and private evidence outside the staged set. .gitignore provides defense in depth; ignore rules alone are not the export authority. Preserve approved PNG figures, W5 CSV/JSON and all license notices. Keep failed runs in private storage, never include them in the public staging set. Any changed or extra release file requires a new reviewed manifest.

## Review history and AI assistance

S06 established scoped W1–W5 execution. S07-R03 closed candidate A09 licensing on researcher attestation. S08 identified inaccurate W6 bundle-location text and missing packaging rules. This revision corrects those delivery documents and adds the allowlist/exclusions; it does not complete W6 or rerun tests. Superseded documents and exact diffs are retained in the private stage audit outside this payload. Current commands, scope and grants are stated here rather than in appended superseded status notices.

The researcher declares independent creation or assistance from Codex/ChatGPT. This editorial revision was prepared with Codex assistance; that disclosure is not independent legal certification. No Git repository creation or publication is implied.
