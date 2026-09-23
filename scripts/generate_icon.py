#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate refined Apple/macOS-grade minimalist 512x512 icon for Kodi System Tools."""

import math
import os
import struct
import time
import zlib


def clamp(val, low=0.0, high=1.0):
    return max(low, min(high, val))


def smoothstep(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0))
    return t * t * (3.0 - 2.0 * t)


def length(x, y):
    return math.hypot(x, y)


def rot(x, y, rad):
    s, c = math.sin(rad), math.cos(rad)
    return x * c - y * s, x * s + y * c


def sdf_rounded_box(px, py, bx, by, r):
    dx = abs(px) - (bx - r)
    dy = abs(py) - (by - r)
    ax = max(dx, 0.0)
    ay = max(dy, 0.0)
    inside = min(max(dx, dy), 0.0)
    return length(ax, ay) + inside - r


def sdf_circle(px, py, r):
    return length(px, py) - r


def sdf_ring(px, py, r, th):
    return abs(length(px, py) - r) - th


def sdf_segment(px, py, ax, ay, bx, by, th):
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    h = clamp((pax * bax + pay * bay) / max(0.0001, bax * bax + bay * bay))
    dx = pax - bax * h
    dy = pay - bay * h
    return length(dx, dy) - th


def sdf_precision_wrench(px, py):
    """Mathematically pure, elegant combination wrench.

    Positioned along the X axis:
    - Tail at -95: Box-end ring (outer r=44, inner r=23)
    - Handle: Smooth tapered beam from -75 to +68, thickness 13.5
    - Head at +92: Open-end jaw with precision capsule U-cutout (outer r=46, slot r=17.5)
    """
    # 1. Closed ring at tail (-95)
    d_tail_out = sdf_circle(px + 95.0, py, 43.0)
    d_tail_in = sdf_circle(px + 95.0, py, 22.0)
    d_tail = max(d_tail_out, -d_tail_in)

    # 2. Main Handle Beam
    d_handle = sdf_segment(px, py, -80.0, 0, 70.0, 0, 13.5)

    # 3. Open Jaw Head (+92) with smooth U-shaped capsule mouth
    d_head_out = sdf_circle(px - 92.0, py, 46.0)
    d_jaw_cut = sdf_segment(px - 92.0, py, -6.0, 0, 50.0, 0, 17.5)
    d_head = max(d_head_out, -d_jaw_cut)

    return min(d_handle, min(d_tail, d_head))


def render_minimal_icon(width=512, height=512):
    print(f"Rendering {width}x{height} refined minimalist icon...")
    t0 = time.time()
    pixels = bytearray(width * height * 4)

    # Minimalist Palette
    c_bg_top = (15, 23, 42)        # Slate 900
    c_bg_bot = (3, 40, 76)         # Deep Obsidian Navy

    c_wrench_top = (255, 255, 255) # Pure White
    c_wrench_bot = (226, 232, 240) # Slate 200

    c_gauge_start = (14, 165, 233) # Sky 500 (Base speed)
    c_gauge_peak = (52, 211, 153)  # Emerald 400 (Max speed)

    half_w = width / 2.0
    half_h = height / 2.0

    for y in range(height):
        v = y / float(height)
        py_c = y - half_h
        row_offset = y * width * 4

        for x in range(width):
            u = x / float(width)
            px_c = x - half_w

            # 1. Base Squircle (iOS smooth rounded rectangle)
            d_squircle = sdf_rounded_box(px_c, py_c, 218, 218, 72)
            alpha_card = 1.0 - smoothstep(-1.0, 1.0, d_squircle)

            if alpha_card <= 0.001:
                # Soft Ambient Drop Shadow
                d_sh = sdf_rounded_box(px_c, py_c - 12, 218, 218, 72)
                if d_sh < 28.0:
                    sh_a = (1.0 - smoothstep(0.0, 28.0, d_sh)) * 0.38
                    idx = row_offset + x * 4
                    pixels[idx] = 0
                    pixels[idx + 1] = 0
                    pixels[idx + 2] = 0
                    pixels[idx + 3] = int(sh_a * 255)
                continue

            # Card Background: Matte Vertical Gradient
            r = c_bg_top[0] + (c_bg_bot[0] - c_bg_top[0]) * (v * 0.85 + u * 0.15)
            g = c_bg_top[1] + (c_bg_bot[1] - c_bg_top[1]) * (v * 0.85 + u * 0.15)
            b = c_bg_top[2] + (c_bg_bot[2] - c_bg_top[2]) * (v * 0.85 + u * 0.15)

            # Top-left ambient soft sheen
            d_sheen = length(px_c + 90, py_c + 120)
            sheen_a = max(0.0, 1.0 - d_sheen / 320.0) * 0.20
            r += (255 - r) * sheen_a
            g += (255 - g) * sheen_a
            b += (255 - b) * sheen_a

            # Refined 1px Outer Rim Highlight
            d_rim = abs(d_squircle + 1.8) - 1.2
            rim_a = (1.0 - smoothstep(0.0, 2.0, d_rim)) * (0.40 - v * 0.2)
            r += (186 - r) * rim_a
            g += (230 - g) * rim_a
            b += (253 - b) * rim_a

            # --- 2. Minimalist Tachometer / Performance Speed Arc ---
            # Radius 162, Thickness 5.0 (frames the wrench comfortably)
            d_gauge = sdf_ring(px_c, py_c, 162.0, 4.0)

            # Convert angle to polar: 0 at +X (3 o'clock), math.pi/2 at +Y (6 o'clock)
            # Tachometer gauge spans from 140 deg (bottom-left) over top to 35 deg (bottom-right max)
            angle = math.atan2(py_c, px_c)  # -pi to +pi
            # Map angle so top (12 o'clock = -pi/2) is central:
            # Span from -2.44 rad (-140 deg) clockwise to +0.65 rad (+37 deg)
            arc_start = -2.44
            arc_end = 0.65
            # Clockwise from arc_start (-140 deg) through -pi/2 (-90 deg) through 0 to arc_end (+37 deg)
            in_gauge_arc = (arc_start <= angle <= arc_end)

            if in_gauge_arc:
                a_gauge = 1.0 - smoothstep(-1.0, 1.0, d_gauge)
                if a_gauge > 0.0:
                    gauge_t = clamp((angle - arc_start) / (arc_end - arc_start))
                    gr = c_gauge_start[0] + (c_gauge_peak[0] - c_gauge_start[0]) * gauge_t
                    gg = c_gauge_start[1] + (c_gauge_peak[1] - c_gauge_start[1]) * gauge_t
                    gb = c_gauge_start[2] + (c_gauge_peak[2] - c_gauge_start[2]) * gauge_t
                    r = r * (1.0 - a_gauge) + gr * a_gauge
                    g = g * (1.0 - a_gauge) + gg * a_gauge
                    b = b * (1.0 - a_gauge) + gb * a_gauge

            # Terminal Peak Node Dot (Max Speed indicator at arc_end)
            node_x = 162.0 * math.cos(arc_end)
            node_y = 162.0 * math.sin(arc_end)
            d_node = sdf_circle(px_c - node_x, py_c - node_y, 6.5)
            if d_node < 16.0:
                glow_node = (1.0 - smoothstep(0.0, 16.0, d_node)) * 0.95
                r += (c_gauge_peak[0] - r) * glow_node
                g += (c_gauge_peak[1] - g) * glow_node
                b += (c_gauge_peak[2] - b) * glow_node

            # --- 3. Hero Element: The Minimalist Wrench ---
            # Rotated 45 degrees
            wx, wy = rot(px_c, py_c, -math.pi / 4.0)
            d_wrench = sdf_precision_wrench(wx, wy)

            # Soft contact drop shadow behind wrench
            d_w_shadow = sdf_precision_wrench(wx, wy + 8.0)
            if d_w_shadow < 18.0 and d_wrench > 0:
                w_sh = (1.0 - smoothstep(0.0, 18.0, d_w_shadow)) * 0.58
                r *= (1.0 - w_sh)
                g *= (1.0 - w_sh)
                b *= (1.0 - w_sh)

            # Draw Wrench
            a_wrench = 1.0 - smoothstep(-1.2, 1.2, d_wrench)
            if a_wrench > 0.0:
                wt = clamp((wy + 35.0) / 70.0)
                wr = c_wrench_top[0] + (c_wrench_bot[0] - c_wrench_top[0]) * wt
                wg = c_wrench_top[1] + (c_wrench_bot[1] - c_wrench_top[1]) * wt
                wb = c_wrench_top[2] + (c_wrench_bot[2] - c_wrench_top[2]) * wt

                # Clean upper specular edge highlight
                if wy < -1.2 and d_wrench < -1.0:
                    wr += (255 - wr) * 0.42
                    wg += (255 - wg) * 0.42
                    wb += (255 - wb) * 0.42

                r = r * (1.0 - a_wrench) + wr * a_wrench
                g = g * (1.0 - a_wrench) + wg * a_wrench
                b = b * (1.0 - a_wrench) + wb * a_wrench

            # 4. Accent Detail: Inset Precision Groove along Wrench Handle
            d_groove = sdf_segment(wx, wy, -48.0, 0, 42.0, 0, 3.8)
            a_groove = 1.0 - smoothstep(-0.8, 0.8, d_groove)
            if a_groove > 0.0 and d_wrench < -2.0:
                gr_r, gr_g, gr_b = 26.0, 48.0, 78.0
                r = r * (1.0 - a_groove * 0.70) + gr_r * a_groove * 0.70
                g = g * (1.0 - a_groove * 0.70) + gr_g * a_groove * 0.70
                b = b * (1.0 - a_groove * 0.70) + gr_b * a_groove * 0.70

            # Pack pixel RGBA
            pix_idx = row_offset + x * 4
            pixels[pix_idx] = int(clamp(r, 0, 255))
            pixels[pix_idx + 1] = int(clamp(g, 0, 255))
            pixels[pix_idx + 2] = int(clamp(b, 0, 255))
            pixels[pix_idx + 3] = int(clamp(alpha_card * 255, 0, 255))

    print(f"Minimalist render completed in {time.time() - t0:.2f}s")
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

    compressed = zlib.compress(bytes(raw_scanlines), level=9)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF)
    png += struct.pack(">I", len(compressed)) + b"IDAT" + compressed + idat_crc

    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    png += struct.pack(">I", 0) + b"IEND" + iend_crc
    return png


def main():
    pixels, w, h = render_minimal_icon(512, 512)
    png_data = encode_png(pixels, w, h)

    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_paths = [
        os.path.join(addon_dir, "resources", "icon.png"),
        os.path.join(addon_dir, "icon.png"),
    ]

    for p in target_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(png_data)
        print(f"Saved: {p} ({len(png_data) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
