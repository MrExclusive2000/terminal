#!/usr/bin/env python3
"""
Generate packaging/argus.ico with no image-library dependency.

Writes PNG-compressed ICO entries (supported since Vista), so the whole icon is
produced from zlib and struct alone and the build has one less thing to install.

The mark is an eye: Argus Panoptes, the hundred-eyed watchman who never slept.
It also happens to be what the product does - watch filings nobody reads.
Rendered with 4x supersampling because an aliased 16px icon looks broken in a
taskbar, which is the size most people will actually see.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

GROUND = (12, 16, 19)      # #0C1013 - the terminal ground, never pure black
ACCENT = (53, 181, 168)    # #35B5A8
PUPIL = (10, 14, 16)

SIZES = (16, 24, 32, 48, 64, 128, 256)
SS = 4                     # supersample factor


def _inside(px: float, py: float, n: float) -> tuple[bool, bool, bool]:
    """Rounded-square ground, lens-shaped iris, round pupil, in unit space."""
    x, y = px / n - 0.5, py / n - 0.5

    # rounded square (squircle) ground
    r = 0.46
    k = 4.0
    ground = (abs(x) / r) ** k + (abs(y) / r) ** k <= 1.0

    # Vesica: intersection of two circles offset vertically -> an eye outline.
    # The lens half-height is (cr - cy), and the pupil must sit comfortably
    # inside it: a pupil taller than the lens clips through the iris and the
    # mark stops reading as an eye at all.
    cy, cr = 0.22, 0.44
    lens = ((x * x + (y + cy) ** 2) <= cr * cr) and ((x * x + (y - cy) ** 2) <= cr * cr)

    pupil = (x * x + y * y) <= 0.112 ** 2
    return ground, lens, pupil


def render(size: int) -> bytes:
    n = size * SS
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            gs = ls = ps = 0
            for sy in range(SS):
                for sx in range(SS):
                    g, l, p = _inside(px * SS + sx + 0.5, py * SS + sy + 0.5, n)
                    gs += g
                    ls += l
                    ps += p
            tot = SS * SS
            ga, la, pa = gs / tot, ls / tot, ps / tot
            if ga <= 0:
                row += bytes((0, 0, 0, 0))
                continue
            # ground, then iris over it, then pupil over that
            r, g_, b = GROUND
            for (cr, cg, cb), a in ((ACCENT, la), (PUPIL, pa)):
                r = round(r * (1 - a) + cr * a)
                g_ = round(g_ * (1 - a) + cg * a)
                b = round(b * (1 - a) + cb * a)
            row += bytes((r, g_, b, round(255 * ga)))
        rows.append(bytes(row))

    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def build(out: Path) -> Path:
    imgs = [(s, render(s)) for s in SIZES]
    header = struct.pack("<HHH", 0, 1, len(imgs))
    offset = 6 + 16 * len(imgs)
    entries, blobs = b"", b""
    for size, png in imgs:
        dim = 0 if size >= 256 else size          # 0 means 256 in the ICO header
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
        blobs += png
    out.write_bytes(header + entries + blobs)
    return out


if __name__ == "__main__":
    p = build(Path(__file__).with_name("argus.ico"))
    print(f"{p} ({p.stat().st_size:,} bytes, {len(SIZES)} sizes)")
