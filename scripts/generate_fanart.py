#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate 1280x720 ambient fanart backdrop for Kodi System Tools addon."""

import math
import os
import struct
import time
import zlib


def clamp(val, low=0.0, high=1.0):
    return max(low, min(high, val))


def render_fanart(width=1280, height=720):
    print(f"Rendering {width}x{height} fanart backdrop...")
    t0 = time.time()
    pixels = bytearray(width * height * 4)

    half_w = width / 2.0
    half_h = height / 2.0

    for y in range(height):
        v = y / float(height)
        py = y - half_h
        row_offset = y * width * 4

        for x in range(width):
            u = x / float(width)
            px = x - half_w

            # Base Dark Midnight Gradient: Slate 950 to Slate 900
            # (10, 15, 30) -> (15, 23, 42)
            r = 10.0 + 8.0 * v
            g = 15.0 + 12.0 * v
            b = 30.0 + 20.0 * v

            # Ambient Right-Side Glow (Cyber Blue / Cyan)
            d_glow1 = math.hypot(px - 350.0, py + 80.0)
            a_glow1 = max(0.0, 1.0 - (d_glow1 / 650.0)) ** 2
            r += 14.0 * a_glow1
            g += 90.0 * a_glow1
            b += 160.0 * a_glow1

            # Ambient Top-Left Glow (Deep Indigo)
            d_glow2 = math.hypot(px + 450.0, py - 180.0)
            a_glow2 = max(0.0, 1.0 - (d_glow2 / 700.0)) ** 2
            r += 25.0 * a_glow2
            g += 30.0 * a_glow2
            b += 80.0 * a_glow2

            # Subtle Diagonal Tech Grid / Scanline Accents
            diag = (x + y * 0.6) % 64.0
            if diag < 1.2:
                grid_lum = 12.0 * (1.0 - abs(px) / half_w)
                r += grid_lum
                g += grid_lum * 1.5
                b += grid_lum * 2.0

            # Vignette at edges
            vignette = 1.0 - 0.45 * ((px / half_w) ** 2 + (py / half_h) ** 2)
            vignette = clamp(vignette, 0.4, 1.0)
            r *= vignette
            g *= vignette
            b *= vignette

            pix_idx = row_offset + x * 4
            pixels[pix_idx] = int(clamp(r, 0, 255))
            pixels[pix_idx + 1] = int(clamp(g, 0, 255))
            pixels[pix_idx + 2] = int(clamp(b, 0, 255))
            pixels[pix_idx + 3] = 255

    print(f"Fanart render completed in {time.time() - t0:.2f}s")
    return pixels, width, height


def encode_png(pixels, width, height):
    png = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    png += struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    raw_scanlines = bytearray()
    row_bytes = width * 4
    for y in range(height):
        raw_scanlines.append(0)
        start = y * row_bytes
        raw_scanlines.extend(pixels[start:start + row_bytes])

    compressed = zlib.compress(bytes(raw_scanlines), level=7)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF)
    png += struct.pack(">I", len(compressed)) + b"IDAT" + compressed + idat_crc

    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    png += struct.pack(">I", 0) + b"IEND" + iend_crc
    return png


def main():
    pixels, w, h = render_fanart(1280, 720)
    png_data = encode_png(pixels, w, h)

    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(addon_dir, "resources", "fanart.jpg")

    with open(target_path, "wb") as f:
        f.write(png_data)
    print(f"Saved fanart: {target_path} ({len(png_data) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
