---
name: dan-watermark
description: 处理图片水印和图像输出：添加或移除 X、微信公众号、小红书、抖音水印，清除 EXIF/C2PA/AI 来源标记和不可见盲水印，并压缩、优化、转换格式、减少图片体积。当用户说“加水印”“去水印”“去盲水印”“清除 EXIF”“压缩图片”“优化图片”“转换格式”或“减少图片体积”时使用。
---

# dan-watermark

统一处理博客和社交媒体图片的水印与输出质量。源代码在 `src/dan-watermark/`，不依赖 `baoyu-*` skill。

## 能力

- 去除 PNG 的 `caBX`、EXIF、tEXt/iTXt/zTXt、时间等来源元数据；清理 JPEG/WebP 的 EXIF 和生成信息。
- 对来自 ChatGPT/OpenAI、Gemini、Midjourney 等生成器的图片执行轻度像素扰动，削弱 SynthID 等不可见盲水印。该操作有损且尽力而为，不能移除可见文字或覆盖式水印。
- 压缩图片、优化图片、转换 PNG/JPEG/WebP 格式、减少图片体积。
- 添加 X、微信公众号、小红书、抖音平台预设的可见平铺/角标水印，也可写入 LSB 暗水印并提取验证。

## 去水印、清理和格式处理

```bash
python3 scripts/image.py INPUT.png OUTPUT.png --clean
python3 scripts/image.py INPUT.png OUTPUT.jpg --format jpeg --quality 95
python3 scripts/image.py INPUT.png OUTPUT.webp --format webp --quality 90
```

默认保留原图，输出到指定路径；不传 `--clean` 时只清理元数据，不做像素扰动。输出完成后应检查 `exif=0`，并确认没有非标准 PNG 元数据块。

## 添加平台水印

添加任何平台水印前，必须先执行一次去水印/清理步骤，再把清理后的文件作为 `watermark.py` 的输入。这样可以先清除原图中的元数据和不可见水印，避免在旧水印基础上继续叠加。默认保留原图，使用单独的中间文件：

```bash
python3 scripts/image.py INPUT.png /tmp/dan-watermark-clean.png --clean
python3 scripts/watermark.py /tmp/dan-watermark-clean.png OUTPUT.png --platform x --handle "@duanjl_china"
```

如果输入格式或路径不适合 `/tmp`，也可以在工作目录使用其他明确的中间输出路径；不得直接跳过清理步骤把原图交给 `watermark.py`。该清理步骤针对元数据和不可见水印，不能移除已经合成到像素中的可见文字或图案。

```bash
python3 scripts/watermark.py CLEAN_INPUT.png OUTPUT.png --platform x --handle "@duanjl_china"
python3 scripts/watermark.py CLEAN_INPUT.png OUTPUT.png --platform wechat --handle "账号名" --style corner
python3 scripts/watermark.py CLEAN_INPUT.png OUTPUT.png --platform xiaohongshu --handle "灯塔笔记"
```

`--platform` 支持 `x`、`wechat`、`xiaohongshu`、`douyin`；`--style` 支持 `tile` 和 `corner`。默认同时写入可见水印和 LSB 暗水印；用 `--no-visible` 或 `--no-blind` 可关闭其中一层。提取暗水印：

```bash
python3 scripts/watermark.py --extract IMAGE.png
```

暗水印依赖 PNG 无损保存；JPEG 压缩、缩放和去水印扰动都可能破坏它。只处理用户拥有或获授权处理的图片，不用于伪造来源或规避平台署名要求。

## 依赖和交付

需要 Python 3、Pillow；执行 `--clean` 需要 NumPy。默认不覆盖原图。报告时说明输出路径、格式、质量、元数据是否清除，以及是否执行了像素扰动。
