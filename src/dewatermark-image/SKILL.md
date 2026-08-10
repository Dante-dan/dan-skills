---
name: dewatermark-image
description: 清除图片的元数据水印（EXIF/C2PA 溯源信息）和盲水印（像素级隐写水印，如 SynthID/C2PA caBX 隐写块），常用于处理 ChatGPT/OpenAI、Midjourney 等 AI 生成图片。当用户说"去水印"、"去除盲水印"、"清除 EXIF"、"抹掉元数据"、"清理图片来源信息"时使用。
---

# 图片去水印 (Image Dewatermark)

## 核心定位

清除 AI 生成图片（尤其是 ChatGPT/OpenAI Images）中携带的两类"水印"：

1. **元数据水印**：EXIF、PNG 文本块（tEXt/iTXt/zTXt）、以及 **C2PA 溯源块**（PNG 中的 `caBX` chunk，JPEG 中的 C2PA/XMP 段）—— 这些以明文/结构化数据形式记录来源、生成工具、编辑历史
2. **盲水印（像素级隐写水印）**：编码进像素数据本身的不可见水印（如 SynthID 类技术），肉眼不可见，仅靠删元数据无法去除，必须通过像素级扰动破坏

**重要口径**：这类处理仅用于合法场景（保护隐私、清理个人素材的来源元数据等），不用于伪造内容来源或规避版权署名义务。处理前确认用户有权处理该图片。

---

## 判断逻辑

### Step 1: 探测水印类型

先看文件里到底带了什么，而不是无脑跑一遍流程。

**PNG 文件**：解析 chunk 结构，找出非标准块

```python
import struct

with open("INPUT.png", "rb") as f:
    data = f.read()

pos = 8
out = bytearray(data[:8])
chunks = []
pos_ = 8
while pos_ < len(data):
    length = struct.unpack(">I", data[pos_:pos_+4])[0]
    ctype = data[pos_+4:pos_+8].decode("ascii", errors="replace")
    chunks.append((ctype, length))
    pos_ += 8 + length + 4
    if ctype == "IEND":
        break
print(chunks)
```

关键 chunk：
- `caBX` — **C2PA 溯源清单**（加密签名的来源/编辑历史声明），OpenAI 生成图片常见，体积通常几十 KB
- `tEXt` / `iTXt` / `zTXt` — 文本元数据（可能含 Software/Author/Description 等字段）
- `eXIf` — PNG 内嵌 EXIF 块

**JPEG 文件**：用 exiftool（若可用）或 PIL 读取

```bash
exiftool INPUT.jpg
```
或
```python
from PIL import Image
img = Image.open("INPUT.jpg")
print(img.info.keys())  # 'exif', 'icc_profile' 等
exif = img.getexif()
print(dict(exif))
```

关注 `Software`、`ImageDescription`、`XMP` 中的 C2PA/来源声明字段。

### Step 2: 剥离元数据 chunk / EXIF

**PNG — 直接按 chunk 类型过滤**（比重新编码更彻底、不损画质）：

```python
import struct

STRIP_TYPES = {b"caBX", b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME"}

with open("INPUT.png", "rb") as f:
    data = f.read()

pos = 8
out = bytearray(data[:8])
while pos < len(data):
    length = struct.unpack(">I", data[pos:pos+4])[0]
    ctype = data[pos+4:pos+8]
    chunk_full = data[pos:pos+8+length+4]
    if ctype not in STRIP_TYPES:
        out += chunk_full
    pos += 8 + length + 4
    if ctype == b"IEND":
        break

with open("_stage1_stripped.png", "wb") as f:
    f.write(out)
```

**JPEG — 用 PIL 重新保存，不带 exif/icc**：

```python
from PIL import Image
img = Image.open("INPUT.jpg").convert("RGB")
img.save("_stage1_stripped.jpg", format="JPEG", quality=95, exif=b"")
```

### Step 3: 破坏像素级盲水印

仅删元数据对盲水印无效——盲水印编码在像素数值本身。需要对像素做**有损扰动**，幅度控制在肉眼不可察觉的范围内：

```python
from PIL import Image
import numpy as np

img = Image.open("_stage1_stripped.png").convert("RGB")
w, h = img.size

# 1) 轻微缩放抖动：99% 缩小再放大回原尺寸，用不同重采样核，打乱隐写图案的空间对齐
small = img.resize((round(w * 0.99), round(h * 0.99)), Image.LANCZOS)
restored = small.resize((w, h), Image.BICUBIC)

# 2) 极轻微随机噪声：±2 灰阶，破坏 LSB / 频域隐写，不影响肉眼观感
arr = np.array(restored).astype(np.int16)
rng = np.random.default_rng(42)
noise = rng.integers(-2, 3, size=arr.shape, dtype=np.int16)
arr = np.clip(arr + noise, 0, 255).astype(np.uint8)

out = Image.fromarray(arr, mode="RGB")
out.save("_stage2_dewatermarked.png", format="PNG", optimize=True)
```

**关键细节**：
- 缩放比例控制在 98%~99.5% 之间：太小会有肉眼可见的细节损失，太接近 100% 可能不足以破坏隐写对齐
- 缩小和放大必须用**不同**的重采样算法（如 LANCZOS 缩小 + BICUBIC 放大），单一算法的可逆插值更容易被隐写检测算法"看穿"
- 噪声幅度 ±2~3 灰阶足够破坏大多数 LSB 隐写，且在正常观看下不可察觉；如用户反馈画质下降，可降到 ±1
- 如果图片后续要发布到对隐写水印检测严格的平台，可以叠加一次轻度 JPEG 重压缩（quality=90 左右再转回 PNG）进一步破坏频域水印

### Step 4: 校验结果

**确认元数据已清空**（PNG 应只剩 `IHDR` / `IDAT` / `IEND`）：

```python
import struct
with open("_stage2_dewatermarked.png", "rb") as f:
    data = f.read()
pos = 8
chunks = []
while pos < len(data):
    length = struct.unpack(">I", data[pos:pos+4])[0]
    ctype = data[pos+4:pos+8].decode("ascii", errors="replace")
    chunks.append((ctype, length))
    pos += 8 + length + 4
    if ctype == "IEND":
        break
assert all(c[0] in ("IHDR", "IDAT", "IEND", "PLTE", "tRNS") for c in chunks), chunks
print("clean:", chunks[:3], "...", chunks[-2:])
```

**视觉核对**：用 Read 工具打开处理前后的图片，确认画质无明显劣化、构图不变。

### Step 5: 清理临时文件、交付

```bash
mv _stage2_dewatermarked.png "OUTPUT.png"
rm -f _stage1_stripped.* _stage2_dewatermarked.*
```

---

## 命名规范

| 场景 | 命名格式 | 示例 |
|------|----------|------|
| 默认输出 | `{原文件名}_clean.{ext}` | `ChatGPT Image xxx_clean.png` |
| 用户指定输出名 | 以用户要求为准 | — |

不覆盖原文件，保留原图作为备份，除非用户明确要求原地替换。

---

## 交付清单

| 交付物 | 说明 |
|--------|------|
| 去水印后的图片 | 无 EXIF/C2PA/文本元数据 chunk，像素经轻微扰动重编码 |
| 处理说明 | 简述移除了哪些元数据块、是否检测到盲水印痕迹 |

---

## 注意事项

1. **先探测再处理**：不同来源的图片携带的水印类型不同（有的只有 EXIF，有的有 C2PA caBX，有的两者都有），Step 1 探测决定后续要不要跑像素扰动
2. **PNG chunk 过滤优于重新编码**：能用 chunk 级过滤解决的（纯元数据水印），不要用有损重新编码，避免不必要的画质损失
3. **像素扰动是有损操作**：仅在确认存在或怀疑存在盲水印（如图片来自 ChatGPT/OpenAI、Midjourium 等已知使用隐写水印的平台）时执行 Step 3；如果只是清理普通 EXIF（如手机拍照的 GPS/设备信息），做到 Step 2 即可
4. **JPEG 需重新编码**：JPEG 没有 PNG 那样清晰的 chunk 结构，去 EXIF 通常伴随重新编码，quality 建议 ≥95 以控制画质损失
5. **合法使用边界**：仅用于清理用户自己拥有或有权处理的图片的隐私/来源元数据，不用于伪造 AI 生成内容为人工创作、规避平台内容标识规定等场景
6. **工具依赖**：Python 需要 `Pillow` + `numpy`；如系统装有 `exiftool`/`imagemagick`（`identify`/`convert`）可用于辅助探测，非必需
