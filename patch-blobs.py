#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2026 Firenza
# SPDX-License-Identifier: Apache-2.0
#
# Re-creates the pre-patched MIUI Camera JNI libs in proprietary/system_ext/lib64
# from the stock xiaomi.eu V14.0.7.0.TKPCNXM (Android 13) /system/lib64 copies.
#
# Why: each lib makes exactly one virtual call on android::Surface (found by
# Ghidra full decompile + REA blr slot scan, see the audit report). In the A13
# libgui that slot was Surface::connect(int, const sp<IProducerListener>&[, bool]).
# In the A17 / EvoX cnb libgui (frameworks/native/libs/gui/include/gui/Surface.h)
# those slots now hold detachNextBuffer (0x158) and
# connect(int, const sp<SurfaceListener>&, bool, bool, bool) (0x150). Both are
# unsafe with the MIUI arguments, so the call is retargeted to
# Surface::connect(int api) at slot 0xb8, which ignores the listener and
# installs a StubSurfaceListener. All three MIUI listeners' onBufferReleased are
# empty or log-only, so nothing is lost.
#
# The script refuses to write anything unless the input is the exact stock file
# (sha256) and the bytes at the patch offset are the expected A13 instruction.
# Re-check the 0xb8 slot whenever Surface.h changes (see --check-header).
#
# usage: patch-blobs.py <dir with stock libs> [--out DIR] [--check-header Surface.h]
#        patch-blobs.py --verify   (checks the committed patched libs)

import argparse, hashlib, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "proprietary/system_ext/lib64")

# lib: (stock sha256, patched sha256 or None, [(file offset, orig bytes, new bytes, what)])
PATCHES = {
    "libcamera_algoup_jni.xiaomi.so": (
        "dce702acc73e3785832c4e9b121ae070daea5262972863ef89e20bf0a1fa1588", "f4613e307e621de460d87e4f26f1dc504cc7b9345a4ff520be71496c8a1dd55a",
        [(0x6278, "08ad40f9", "085d40f9",
          "getANativeWindow: ldr x8,[x8,#0x158] -> ldr x8,[x8,#0xb8] (Surface::connect(int))")]),
    "libcamera_mianode_jni.xiaomi.so": (
        "c708bda54404266a03dc7e93a5487556bd6c8719407a53e15d81d30710a517bb", "11f90f59d636da485c26807e4f1bd5cb9094e31c4ac533b0474eed24e22bd2b8",
        [(0xf878, "08ad40f9", "085d40f9",
          "getANativeWindow: ldr x8,[x8,#0x158] -> ldr x8,[x8,#0xb8] (Surface::connect(int))")]),
    "libcamera_ispinterface_jni.xiaomi.so": (
        "04cfc7279e28abb2009a494276b780c905822b2945add88fdacbd2bc20c5e9d4", "aa93b0d858d47521e355a4b742ec5ffd16897d1582e70241cc106c8cd2d28d6b",
        [(0xafac, "08a940f9", "085d40f9",
          "IspInterfaceContext::setupOutputStream: ldr x8,[x8,#0x150] -> ldr x8,[x8,#0xb8] (Surface::connect(int))")]),
}

def sha(b): return hashlib.sha256(b).hexdigest()

def surface_connect_int_slot(header):
    """Itanium vtable offset of Surface::connect(int) from Surface.h declaration order.
    RefBase contributes 6 slots (D1, D0 dtors + 4 hooks); every Surface-introduced
    virtual follows in declaration order."""
    src = open(header).read()
    body = src[src.index("class Surface\n"):]
    body = body[:body.index("\n};")]
    names = re.findall(r"virtual\s+([^;{(]*?)(~?\w+)\s*\(([^)]*)\)", body)
    slot = 6
    for ret, name, args in names:
        if name.startswith("~") or ret.rstrip().endswith("~") or name == "Surface":
            continue  # ~Surface overrides RefBase's dtor slots
        # skip classes nested in Surface (ProducerListenerProxy, ...)
        if name in ("onBufferReleased", "needsReleaseNotify", "onBufferDetached",
                    "onBuffersDiscarded", "onBufferAcquired", "onBufferDropped",
                    "needsAcquiredNotify", "needsDroppedNotify", "binderDied"):
            continue
        if name == "connect" and args.strip() == "int api":
            return slot * 8
        slot += 1
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stockdir", nargs="?")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--check-header")
    a = ap.parse_args()
    if a.check_header:
        off = surface_connect_int_slot(a.check_header)
        print(f"Surface::connect(int) vtable offset per {a.check_header}: {hex(off) if off is not None else 'NOT FOUND'}")
        if off != 0xb8:
            sys.exit("slot is not 0xb8: the patch target is wrong for this libgui, STOP")
    if a.verify:
        rc = 0
        for lib, (osha, psha, edits) in PATCHES.items():
            b = open(os.path.join(a.out, lib), "rb").read()
            ok = sha(b) == psha and all(b[o:o+4].hex() == new for o, _, new, _ in edits)
            print(f"{'OK ' if ok else 'BAD'} {lib} {sha(b)}")
            rc |= not ok
        sys.exit(rc)
    if not a.stockdir:
        if not a.check_header: ap.error("stock dir required")
        return
    os.makedirs(a.out, exist_ok=True)
    for lib, (osha, psha, edits) in PATCHES.items():
        b = bytearray(open(os.path.join(a.stockdir, lib), "rb").read())
        if sha(b) != osha:
            sys.exit(f"{lib}: sha256 {sha(b)} is not the stock V14.0.7 file {osha}")
        for off, old, new, what in edits:
            if b[off:off+4].hex() != old:
                sys.exit(f"{lib}@{hex(off)}: found {b[off:off+4].hex()}, expected {old}")
            b[off:off+4] = bytes.fromhex(new)
            print(f"{lib}@{hex(off)}: {old} -> {new}  {what}")
        if psha and not psha.startswith("@") and sha(b) != psha:
            sys.exit(f"{lib}: patched sha256 {sha(b)} != expected {psha}")
        open(os.path.join(a.out, lib), "wb").write(b)
        print(f"wrote {lib} {sha(b)}")

if __name__ == "__main__":
    main()
