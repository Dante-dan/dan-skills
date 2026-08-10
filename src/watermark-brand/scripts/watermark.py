#!/usr/bin/env python3
"""
品牌水印工具：明水印（可见 logo 平铺纹理 / 角标）+ 暗水印（LSB 隐写）。

用法：
  python3 watermark.py IN.png OUT.png --platform x --handle "@duanjl_china" [--style tile|corner] [--corner br|bl] [--blind-message "..."]
  python3 watermark.py --extract IN.png   # 从图片中提取暗水印内容（校验用）

平台预设（--platform）：
  x            X (Twitter)      默认 handle 形如 @xxx
  wechat       微信公众号        默认 handle 为账号名文字
  xiaohongshu  小红书            默认 handle 为账号名文字
  douyin       抖音              默认 handle 形如 名称 · ID:xxx
"""

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
LOGO_DIR = SCRIPT_DIR.parent / "assets" / "logos"

PLATFORM_LOGOS = {
    "x": LOGO_DIR / "x-black.png",
    "wechat": LOGO_DIR / "wechat.png",
    "xiaohongshu": LOGO_DIR / "xiaohongshu.png",
    "douyin": LOGO_DIR / "douyin-icon.png",
}

# tile 纹理水印使用的 logo（部分平台用简化/单色版本，避免整块底色或过多细节在低透明度下糊成色斑）
PLATFORM_LOGOS_TILE = {
    "x": LOGO_DIR / "x-black.png",
    "wechat": LOGO_DIR / "wechat-mono.png",
    "xiaohongshu": LOGO_DIR / "xiaohongshu-mono.png",
    "douyin": LOGO_DIR / "douyin-icon.png",
}

FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_logo_rgba(platform: str, target_h: int, for_tile: bool = False) -> Image.Image:
    """加载平台 logo 并缩放到目标高度，返回 RGBA。for_tile=True 时优先用纹理专用素材。"""
    table = PLATFORM_LOGOS_TILE if for_tile else PLATFORM_LOGOS
    path = table.get(platform)
    if path is None or not path.exists():
        raise SystemExit(f"找不到平台 logo 文件: {path}")
    logo = Image.open(path).convert("RGBA")

    scale = target_h / logo.height
    new_w = max(1, int(logo.width * scale))
    return logo.resize((new_w, target_h), Image.LANCZOS)


PLATFORM_KEEP_COLOR = {
    # 彩色/品牌色 logo：纹理水印保留原始颜色，只整体调透明度（保留品牌识别度）
    "wechat": True,
    "xiaohongshu": True,
    # 单色图标：纹理水印统一改成低调深色，避免纯黑在深色文字区域太突兀
    "x": False,
    "douyin": False,
}


def recolor(logo: Image.Image, color: tuple, opacity: int) -> Image.Image:
    """按 alpha 形状重新着色，统一透明度（用于纯色 logo 的低对比叠加）。"""
    _, _, _, a = logo.split()
    solid = Image.new("RGBA", logo.size, color + (0,))
    solid.putalpha(a.point(lambda p: int(p * opacity / 255)))
    return solid


def fade(logo: Image.Image, opacity: int) -> Image.Image:
    """保留 logo 原始颜色，只整体调低透明度（用于彩色/品牌色 logo）。"""
    r, g, b, a = logo.split()
    faded_a = a.point(lambda p: int(p * opacity / 255))
    return Image.merge("RGBA", (r, g, b, faded_a))


# ---------------- 明水印：平铺纹理 ----------------

def make_tile_pattern(
    logo_rgba: Image.Image,
    text: str,
    W: int,
    H: int,
    tile_size: int = 150,
    angle: float = -22,
    opacity: int = 60,
    color: tuple = (70, 55, 25),
    font_size: int = 20,
    text_opacity: int = None,
    keep_color: bool = False,
) -> Image.Image:
    if text_opacity is None:
        text_opacity = min(255, int(opacity * 1.2))

    # tile 宽度需要容纳文字实际宽度（+留白），否则长账号名会在平铺时首尾相连糊成一片
    font = load_font(font_size)
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = measure.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    tile_size = max(tile_size, int(text_w * 1.35))

    tile = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))

    logo_h = int(tile_size * 0.30)
    scale = logo_h / logo_rgba.height
    logo_resized = logo_rgba.resize((max(1, int(logo_rgba.width * scale)), logo_h), Image.LANCZOS)
    logo_tinted = fade(logo_resized, opacity) if keep_color else recolor(logo_resized, color, opacity)
    tile.alpha_composite(logo_tinted, ((tile_size - logo_tinted.width) // 2, int(tile_size * 0.10)))

    draw = ImageDraw.Draw(tile)
    tw = text_w
    draw.text(((tile_size - tw) // 2, int(tile_size * 0.55)), text, font=font, fill=color + (text_opacity,))

    diag = int(math.hypot(W, H)) + tile_size * 2
    cols = diag // tile_size + 2
    rows = diag // tile_size + 2
    big = Image.new("RGBA", (cols * tile_size, rows * tile_size), (0, 0, 0, 0))
    for r in range(rows):
        for c in range(cols):
            big.paste(tile, (c * tile_size, r * tile_size), tile)

    big = big.rotate(angle, expand=True)
    bx, by = big.size
    left = (bx - W) // 2
    top = (by - H) // 2
    return big.crop((left, top, left + W, top + H))


# ---------------- 明水印：角标 ----------------

def make_corner_badge(
    img_rgba: Image.Image,
    logo_rgba: Image.Image,
    text: str,
    corner: str = "br",
    margin_ratio: float = 0.028,
    logo_h_ratio: float = 0.026,
    font_ratio: float = 0.022,
) -> Image.Image:
    W, H = img_rgba.size
    margin = int(H * margin_ratio)
    logo_h = int(H * logo_h_ratio)
    scale = logo_h / logo_rgba.height
    logo = logo_rgba.resize((max(1, int(logo_rgba.width * scale)), logo_h), Image.LANCZOS)

    font = load_font(int(H * font_ratio))
    draw = ImageDraw.Draw(img_rgba)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    gap = int(H * 0.01)
    total_w = logo.width + gap + text_w
    y_center = H - margin - max(logo.height, text_h) // 2

    if corner in ("br", "tr"):
        x_start = W - margin - total_w
    else:
        x_start = margin
    if corner in ("tr", "tl"):
        y_center = margin + max(logo.height, text_h) // 2

    logo_y = y_center - logo.height // 2
    img_rgba.alpha_composite(logo, (x_start, logo_y))

    text_y = y_center - text_h // 2 - bbox[1]
    tx = x_start + logo.width + gap
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        draw.text((tx + dx, text_y + dy), text, font=font, fill=(255, 255, 255, 160))
    draw.text((tx, text_y), text, font=font, fill=(30, 30, 30, 220))

    return img_rgba


# ---------------- 暗水印：LSB 隐写 ----------------

def embed_blind_watermark(img: Image.Image, message: str, repeat: int = 20) -> Image.Image:
    has_alpha = img.mode == "RGBA"
    rgb_img = img.convert("RGB")
    arr = np.array(rgb_img)
    h, w, _ = arr.shape

    payload = message.encode("utf-8")
    header = len(payload).to_bytes(4, "big")
    full = (header + payload) * repeat
    bits = np.unpackbits(np.frombuffer(full, dtype=np.uint8))

    flat = arr.reshape(-1, 3)
    capacity = flat.shape[0]
    if len(bits) > capacity:
        bits = bits[:capacity]

    channel = flat[: len(bits), 0]
    channel = (channel & 0xFE) | bits
    flat[: len(bits), 0] = channel

    result = Image.fromarray(flat.reshape(h, w, 3), mode="RGB")
    if has_alpha:
        r, g, b = result.split()
        alpha = img.split()[3]
        result = Image.merge("RGBA", (r, g, b, alpha))
    return result


def extract_blind_watermark(img: Image.Image, repeat: int = 20):
    arr = np.array(img.convert("RGB"))
    flat = arr.reshape(-1, 3)
    bits = flat[:, 0] & 1

    header_bits = bits[:32]
    header_bytes = np.packbits(header_bits).tobytes()
    length = int.from_bytes(header_bytes, "big")
    if length <= 0 or length > 10000:
        return None

    unit_bits = 32 + length * 8
    votes = []
    for r in range(repeat):
        start = r * unit_bits + 32
        end = start + length * 8
        if end > len(bits):
            break
        payload_bits = bits[start:end]
        votes.append(np.packbits(payload_bits).tobytes())

    if not votes:
        return None

    from collections import Counter

    best = Counter(votes).most_common(1)[0][0]
    try:
        return best.decode("utf-8")
    except UnicodeDecodeError:
        return None


# ---------------- CLI ----------------

def main():
    parser = argparse.ArgumentParser(description="品牌水印工具（明水印 + 暗水印）")
    parser.add_argument("input", nargs="?", help="输入图片路径")
    parser.add_argument("output", nargs="?", help="输出图片路径")
    parser.add_argument("--platform", choices=["x", "wechat", "xiaohongshu", "douyin"], help="平台预设")
    parser.add_argument("--handle", help="明水印文字内容（账号/ID）")
    parser.add_argument("--style", choices=["tile", "corner"], default="tile", help="明水印样式，默认 tile 平铺纹理")
    parser.add_argument("--corner", choices=["br", "bl", "tr", "tl"], default="bl", help="corner 样式下 logo 位置，默认左下角")
    parser.add_argument("--opacity", type=int, default=60, help="tile 样式透明度 0-255，默认 60")
    parser.add_argument("--angle", type=float, default=-22, help="tile 样式旋转角度，默认 -22")
    parser.add_argument("--no-visible", action="store_true", help="跳过明水印，只做暗水印")
    parser.add_argument("--no-blind", action="store_true", help="跳过暗水印，只做明水印")
    parser.add_argument("--blind-message", help="暗水印内容，默认根据 platform+handle 自动生成")
    parser.add_argument("--extract", metavar="IMG", help="从图片中提取暗水印内容并打印，不做其它处理")
    args = parser.parse_args()

    if args.extract:
        img = Image.open(args.extract)
        msg = extract_blind_watermark(img)
        if msg:
            print(f"提取到暗水印: {msg}")
        else:
            print("未检测到暗水印（或已被破坏）")
        return

    if not args.input or not args.output:
        parser.error("需要提供 input 和 output 路径（或使用 --extract）")

    src = Image.open(args.input)
    has_alpha = src.mode in ("RGBA", "LA") or (src.mode == "P" and "transparency" in src.info)
    canvas = src.convert("RGBA")
    W, H = canvas.size
    original_alpha = canvas.split()[3] if has_alpha else None

    if not args.no_visible:
        if not args.platform or not args.handle:
            parser.error("加明水印需要 --platform 和 --handle")

        if args.style == "tile":
            logo = load_logo_rgba(args.platform, target_h=200, for_tile=True)
            keep_color = PLATFORM_KEEP_COLOR.get(args.platform, False)
            pattern = make_tile_pattern(
                logo, args.handle, W, H,
                angle=args.angle, opacity=args.opacity,
                keep_color=keep_color,
            )
            canvas.alpha_composite(pattern)
        else:
            logo = load_logo_rgba(args.platform, target_h=200)
            canvas = make_corner_badge(canvas, logo, args.handle, corner=args.corner)

    if has_alpha:
        # 保留原图透明区域：水印只叠加在不透明像素上，透明区域的 alpha 维持原状
        r, g, b, _ = canvas.split()
        canvas = Image.merge("RGBA", (r, g, b, original_alpha))
        result = canvas
    else:
        result = canvas.convert("RGB")

    if not args.no_blind:
        message = args.blind_message or f"{args.platform}:{args.handle}"
        result = embed_blind_watermark(result, message)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, format="PNG", optimize=True)
    print(f"已保存: {args.output}")


if __name__ == "__main__":
    main()
