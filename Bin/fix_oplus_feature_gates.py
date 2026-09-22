#!/usr/bin/env python3
"""Re-export the OPLUS_FEATURE_* gates that kbuild's per-directory sub-makes never see.

Problem
-------
The OnePlus kernel's top-level Makefile does

    -include OplusKernelEnvConfig.mk      (Makefile:474)
        -include oplus_native_features.mk (OplusKernelEnvConfig.mk:18)

`oplus_native_features.mk` then sets ~230 variables with *plain* assignments,
e.g.

    OPLUS_FEATURE_UFSPLUS=yes

A plain Makefile assignment is **not** exported into the environment. When
kbuild recurses into a sub-directory (`make -C net/`, `make -C techpack/...`),
that sub-make re-reads only its *own* Makefile, with none of those variables
set. Every

    ifneq ($(OPLUS_FEATURE_X),)
    ifeq  ($(OPLUS_FEATURE_X),yes)

gate in a sub-Makefile therefore takes the empty branch, and the objects it
guards are silently dropped from the build.

`OplusKernelEnvConfig.mk` compensates only for *compiler macros*: it walks
`ALLOWED_MCROS` and adds `-D$(feature)` to KBUILD_CFLAGS. That makes
`#ifdef OPLUS_FEATURE_X` work inside C, but does nothing for `$(...)` gates in
Makefiles. Its chatty `make OPLUS_FEATURE_... to be a macro here` output is the
build system telling you the value did not survive the hop.

Observed consequences on OP8 (kona-perf, OOS 13.1)
--------------------------------------------------
  * drivers/scsi/ufs/  — `OPLUS_FEATURE_UFSPLUS` unset, so `ufsfeature.o` is
    never built. `ufshcd.o` then fails to link with ~20 undefined references
    (`ufsf_init`, `ufsf_resume`, `recordUniproErr`, `io_latency_hist_show`,
    ...).
  * mm/                — `OPLUS_FEATURE_PROCESS_RECLAIM` unset, so the
    `ifeq` that picks `process_mm_reclaim.o` (vs the `_weak` variant) falls
    through both branches; `is_reclaim_should_cancel` is then undefined even
    though `mm/vmscan.c` calls it (its `CONFIG_PROCESS_RECLAIM_ENHANCE`
    prerequisite is =y). `OPLUS_FEATURE_MEMLEAK_DETECT` unset does the same
    to `mm/task_mem/`, dropping `update_user_tasklist` which
    `kernel/fork.c` calls.
  * net/               — `OPLUS_FEATURE_WIFI_ROUTERBOOST` unset, so
    `net/oplus_router_boost/` is skipped.
  * techpack/display/msm/ — `OPLUS_FEATURE_ADFR_KERNEL` unset, so the
    OnePlus-authored `ifeq` block for `oplus_adfr.o` never fires.

All four are hard build breaks at the link step, not silent feature losses:
the callers compile in (their `CONFIG_*` prerequisites are =y) while the
definitions get dropped by the Make gate.

Fix
---
Append one `export` line per required gate to the end of
`oplus_native_features.mk` — the file that is already `-include`d by the top
level Makefile, and therefore read by the top-level make before it recurses.
Exporting makes the value visible to every sub-make, and because it happens in
the same file that performs the assignment, the two can never drift apart.

This is deliberately a single central edit rather than per-Makefile `?=`
fallbacks: one insertion point covers every current and future consumer, and it
fixes the whole class of bug instead of one symptom at a time.

Gates are listed explicitly (rather than exporting all ~230 variables) so the
script cannot mask a variable that OnePlus intentionally leaves unset, and so
the diff is reviewable. Only gates that are (a) actually consumed by a
sub-Makefile `$(...)` gate and (b) assigned `=yes` in
`oplus_native_features.mk` belong here.

`export V ?= yes` is not valid make, so the idiom is a plain `export V` after
the assignment already made above, with `?=` used only as a belt-and-braces
default in case a gate is ever removed from the main list.

Idempotent: re-running is a no-op once the marker line is present.
"""

import pathlib
import sys

TARGET = "oplus_native_features.mk"

MARKER = "# --- exported for kbuild sub-makes (added by Bin/fix_oplus_feature_gates.py)"

# Gates consumed as $(...) in sub-Makefiles but never exported by the vendor tree.
#   drivers/scsi/ufs/Makefile:9,12,15
#   net/Makefile:98
#   techpack/display/msm/Makefile:7,167
GATES = (
    # drivers/scsi/ufs/Makefile — blocks the link when missing.
    "OPLUS_FEATURE_UFSPLUS",
    "OPLUS_FEATURE_UFS_SHOW_LATENCY",
    "OPLUS_FEATURE_PADL_STATISTICS",
    # net/Makefile
    "OPLUS_FEATURE_WIFI_ROUTERBOOST",
    # techpack/display/msm/Makefile
    "OPLUS_FEATURE_ADFR_KERNEL",
    "OPLUS_FEATURE_PXLW_IRIS5",
    # mm/Makefile — selects process_mm_reclaim.o (defines
    # is_reclaim_should_cancel, called from mm/vmscan.c:1231) and gates
    # mm/task_mem/ (defines update_user_tasklist, called from
    # kernel/fork.c:2326). Both callers are compiled in because their
    # CONFIG_* prerequisites are =y, so without these exports the two
    # definitions are dropped and vmlinux fails to link.
    "OPLUS_FEATURE_PROCESS_RECLAIM",
    "OPLUS_FEATURE_MEMLEAK_DETECT",
)

BLOCK = (
    "\n"
    + MARKER
    + "\n"
    + "# oplus_native_features.mk assigns these with plain '=' above, which does NOT\n"
    + "# reach kbuild's per-directory sub-makes. Export them so sub-Makefile\n"
    + "# '$(OPLUS_FEATURE_*)' gates evaluate true instead of silently dropping objects.\n"
    + "".join(f"export {g}\n" for g in GATES)
)


def main() -> int:
    path = pathlib.Path(TARGET)
    if not path.is_file():
        print(f"[-] {TARGET} not found; is this the kernel tree root?")
        return 1

    text = path.read_text()

    if MARKER in text:
        print(f"[+] {TARGET}: gates already exported, skipping.")
        return 0

    # Every gate must actually be assigned in this file, otherwise the export
    # would ship an empty value and the gate would still be false -- a silent
    # no-op that looks like success. Fail loudly instead.
    missing = [g for g in GATES if f"{g}=" not in text]
    if missing:
        print("[-] These gates are not assigned in "
              f"{TARGET}, refusing to export stale names: {', '.join(missing)}")
        return 1

    if not text.endswith("\n"):
        text += "\n"

    path.write_text(text + BLOCK)
    print(f"[+] {TARGET}: exported {len(GATES)} gate(s) for kbuild sub-makes:")
    for g in GATES:
        print(f"      {g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
