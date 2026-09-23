#!/usr/bin/env python3
"""Clean, compress, convert, and perturb AI-generated image watermarks."""
import argparse
import json
import struct
from pathlib import Path

from PIL import Image
import numpy as np

PNG_STRIP = {b"caBX", b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME"}

def strip_png(path: Path, out: Path) -> None:
    data = path.read_bytes(); pos = 8; result = bytearray(data[:8])
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        chunk = data[pos:pos + 12 + length]
        if kind not in PNG_STRIP:
            result.extend(chunk)
        pos += 12 + length
        if kind == b"IEND": break
    out.write_bytes(result)

def clean_pixels(img: Image.Image) -> Image.Image:
    alpha = img.getchannel("A") if img.mode == "RGBA" else None
    rgb = img.convert("RGB"); w, h = rgb.size
    small = rgb.resize((max(1, round(w * .99)), max(1, round(h * .99))), Image.Resampling.LANCZOS)
    restored = small.resize((w, h), Image.Resampling.BICUBIC)
    arr = np.asarray(restored, dtype=np.int16)
    rng = np.random.default_rng(42)
    arr = np.clip(arr + rng.integers(-2, 3, size=arr.shape, dtype=np.int16), 0, 255).astype(np.uint8)
    out = Image.fromarray(arr, "RGB")
    if alpha is not None: out.putalpha(alpha)
    return out

def save_clean(src: Path, dst: Path, perturb: bool, fmt_hint: str | None = None, quality: int = 95) -> dict:
    actual = Image.open(src)
    if src.suffix.lower() == ".png":
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        strip_png(src, tmp)
        img = Image.open(tmp)
        if perturb: img = clean_pixels(img)
        fmt = (fmt_hint or "png").upper()
        if fmt == "JPEG": img = img.convert("RGB"); img.save(dst, fmt, quality=quality, optimize=True, exif=b"")
        elif fmt == "WEBP": img.save(dst, fmt, quality=quality, method=6)
        else: img.save(dst, "PNG", optimize=True)
        tmp.unlink(missing_ok=True)
    else:
        img = clean_pixels(actual) if perturb else actual.convert("RGB")
        fmt = (fmt_hint or ("jpeg" if dst.suffix.lower() in (".jpg", ".jpeg") else "webp" if dst.suffix.lower() == ".webp" else "png")).upper()
        if fmt == "JPEG": img.save(dst, fmt, quality=95, optimize=True, exif=b"")
        elif fmt == "WEBP": img.save(dst, fmt, quality=quality, method=6)
        else: img.save(dst, fmt, optimize=True)
    check = Image.open(dst)
    return {"input": str(src), "output": str(dst), "format": check.format, "exif": len(check.getexif()), "info_keys": sorted(k for k in check.info if k not in {"jfif", "jfif_version", "jfif_unit", "jfif_density"})}

def main() -> None:
    p = argparse.ArgumentParser(description="dan-watermark image cleanup")
    p.add_argument("input", type=Path); p.add_argument("output", type=Path)
    p.add_argument("--format", choices=["png", "jpeg", "webp"]); p.add_argument("--quality", type=int, default=95)
    p.add_argument("--clean", action="store_true", help="perturb likely invisible AI watermarks")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(); out = a.output
    if a.format: out = out.with_suffix("." + ("jpg" if a.format == "jpeg" else a.format))
    result = save_clean(a.input, out, a.clean, a.format, a.quality)
    if a.json: print(json.dumps(result, ensure_ascii=False))
    else: print(f"已保存: {out} | format={result['format']} | exif={result['exif']} | clean={a.clean}")

if __name__ == "__main__": main()
