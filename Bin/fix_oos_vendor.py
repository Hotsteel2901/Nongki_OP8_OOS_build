#!/usr/bin/env python3
"""Fix the OOS vendor tree so it matches this workflow's directory layout.

Why this is needed
------------------
OnePlus ships its kernel modules in a separate repo
(`android_kernel_modules_and_devicetree_oneplus_sm8250`). Its oplus charger
drivers reference kernel headers with a *relative* include:

    vendor/oplus/kernel/charger/charger_ic/oplus_battery_msm8250.c
    #include "../../../../kernel/msm-4.19/drivers/power/supply/qcom/smb5-reg.h"

`#include "..."` resolves relative to the *including file's own directory*,
so what matters is the path from `charger_ic/` to the header. With this
workflow's layout (vendor at `$GITHUB_WORKSPACE/vendor`, kernel at
`$GITHUB_WORKSPACE/kernel/msm-4.19`) that distance is exactly five levels:

    $ python3 -c "import os;print(os.path.relpath(
        'kernel/msm-4.19/drivers/power/supply/qcom/smb5-reg.h',
        'vendor/oplus/kernel/charger/charger_ic'))"
    ../../../../../kernel/msm-4.19/drivers/power/supply/qcom/smb5-reg.h

The shipped four levels fall one short and resolve to a path that does not
exist:

    $ realpath -m vendor/oplus/kernel/charger/charger_ic/../../../../kernel/msm-4.19
    $GITHUB_WORKSPACE/vendor/kernel/msm-4.19        # no such directory

OnePlus's own build system consumes the repo with the vendor tree one level
deeper than this workflow places it, which is why four levels work there.
Without this fix `oplus_battery_msm8250.c` (the charger driver OP8 actually
builds) fails on missing `smb5-reg.h` / `battery.h` / `step-chg-jeita.h` /
`storm-watch.h`.

Scope
-----
Only `kernel/msm-4.19` references are rewritten. The same files also carry
4-level includes for `msm-4.14` / `msm-5.4` / `kernel-4.19` used by other
platforms; those branches are never taken on this device, so they are left
untouched to keep the diff minimal.

Idempotency
-----------
The naive `sed -E 's|(\\.\\./){4}kernel/msm-4\\.19/|../../../../../kernel/msm-4.19/|g'`
is NOT idempotent: the replacement still contains a run of four `../`
followed by `kernel/msm-4.19/`, so with `g` a re-run matches its own output
and adds one more level each time (4 -> 5 -> 6 -> ...). This script uses a
negative lookbehind `(?<!\\.\\./)` so only a *positional* run of exactly four
levels matches; an already-rewritten five-level path is never matched again.

Line endings
------------
Several of these files ship with CRLF terminators. Everything here is done in
binary mode so the original line endings are preserved byte-for-byte; a
`read_text()` / `write_text()` round-trip would silently rewrite the whole
file to LF and produce a diff touching every line.

Usage: run from the vendor tree root; exits non-zero if anything looks wrong.
"""

import pathlib
import re
import sys

# Only these carry msm-4.19 includes for the code paths OP8 builds.
# charger_ic: msm7250_Q / msm7250_R / msm8250 are the ones selected by its Makefile.
TARGET_GLOBS = (
    "oplus/kernel/charger/charger_ic/*.c",
    "oplus/kernel/charger/charger_ic/*.h",
    "oplus/kernel/system/slabtrace/slabtrace.h",
)

# Exactly four levels of "../" immediately before kernel/msm-4.19/
FOUR = re.compile(rb"(?<!\.\./)(\.\./){4}kernel/msm-4\.19/")
# Exactly five levels (the desired end state)
FIVE = re.compile(rb"(?<!\.\./)(\.\./){5}kernel/msm-4\.19/")

FIVE_LEVEL = b"../../../../../kernel/msm-4.19/"

# 23 includes exist across the three charger files plus slabtrace.h.
MIN_EXPECTED = 23


def main() -> int:
    root = pathlib.Path(".")
    files = []
    for pattern in TARGET_GLOBS:
        files.extend(sorted(root.glob(pattern)))

    if not files:
        print("[-] No target files found; is this the vendor tree root?")
        return 1

    rewritten = 0
    for path in files:
        try:
            data = path.read_bytes()
        except OSError as exc:
            print(f"[-] Cannot read {path}: {exc}")
            return 1

        hits = len(FOUR.findall(data))
        if hits:
            path.write_bytes(FOUR.sub(FIVE_LEVEL, data))
            rewritten += hits

    remaining = 0
    at_five = 0
    for path in files:
        data = path.read_bytes()
        remaining += len(FOUR.findall(data))
        at_five += len(FIVE.findall(data))

    if remaining:
        print(f"[-] {remaining} include path(s) are still at four levels.")
        return 1

    print(
        f"[+] Rewrote {rewritten} include path(s) from 4 to 5 levels; "
        f"{at_five} now at 5 levels across {len(files)} file(s)."
    )

    if at_five < MIN_EXPECTED:
        print(f"[-] Expected at least {MIN_EXPECTED} five-level includes, found {at_five}.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
