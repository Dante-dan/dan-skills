---
name: wechat-redpocket
description: 将素材加工为微信红包封面资产。视频→扩边羽化视频；图片→封面蒙版+横幅蒙版。当用户说"红包封面"、"处理素材"、"生成封面/横幅"、"视频扩边"时使用。
---

# 微信红包封面素材加工 (WeChat Red Pocket Asset Processor)

## 核心定位

将原始视频或图片素材加工为符合微信红包封面平台规范的发布资产。核心能力：
- **视频**：模糊扩边 + 羽化过渡 + 码率控制
- **图片**：生成带透明蒙版的封面图和横幅图（不可编辑区透明）

---

## 微信红包封面平台规格

### 视频规格
| 参数 | 值 | 说明 |
|------|------|------|
| 目标分辨率 | 958×1278 | 3:4 竖屏比例，H.264 要求偶数宽高 |
| 最大帧率 | 30 fps | 超过 30fps 时在 vf 链末尾加 `fps=30` |
| 目标码率 | 3000 kbit/s | `-b:v 3000k` |
| 音频 | 按需保留或去除 | 用户要求去音频时加 `-an`，否则保留原音频 |
| 编码器 | H.264 | `-c:v libx264` |
| 羽化半径 | 60px | geq alpha 渐变 |
| 模糊强度 | sigma=50 | 扩边背景高斯模糊 |
| 时长控制 | auto-editor 智能变速 | 基于运动检测的智能加速，非均匀加速 |

### 封面图规格 (Cover)
| 参数 | 值 |
|------|------|
| 画布尺寸 | 1053×1746 |
| 不可编辑区 | x=46→1007, y=115→1650 |
| 不可编辑区尺寸 | 961×1535 |
| 左右边距 | 各 46px（透明） |
| 上边距 | 115px（可见内容） |
| 下边距 | 96px（可见内容） |

### 横幅图规格 (Banner)
| 参数 | 值 |
|------|------|
| 画布尺寸 | 480×384 |
| 不可编辑区 | x=10→470, y=61→312 |
| 不可编辑区尺寸 | 460×251 |
| 左右边距 | 各 10px（透明） |
| 上边距 | 61px（可见内容） |
| 下边距 | 72px（可见内容） |

---

## 判断逻辑

### 一、视频输入

#### Step 0: 分析源视频
```bash
ffprobe -v quiet -print_format json -show_format -show_streams INPUT.mp4
```
提取：分辨率、码率、时长、是否有音频、FPS。

#### Step 1: 检测黑边
```bash
ffmpeg -i INPUT.mp4 -vf "cropdetect=24:2:0" -frames:v 30 -f null - 2>&1 | grep cropdetect
```
如果检测到黑边 (crop 值 ≠ 原始分辨率)，在后续管线开头加 `crop=W:H:X:Y`。

#### Step 2: 判断是否需要扩边

**情况 A — 分辨率完全匹配 (958×1278)**：
- 仅调整码率和帧率，音频按需处理
```bash
ffmpeg -y -i INPUT.mp4 -vf "fps=30" -c:v libx264 -b:v 3000k OUTPUT.mp4
```
（源帧率 ≤30 时可省略 `fps=30`）

**情况 B — 比例匹配 3:4 但尺寸不同**：
- 直接缩放 + 调整码率 + 限帧率
```bash
ffmpeg -y -i INPUT.mp4 -vf "scale=958:1278,fps=30" -c:v libx264 -b:v 3000k OUTPUT.mp4
```

**情况 C — 比例不匹配 3:4（最常见）**：
- 完整扩边管线：裁黑边 → 模糊背景 → 羽化叠加
- 计算内容区宽度：`content_w = min(source_w, int(1278 * source_w / source_h))`，确保偶数
- 完整 ffmpeg 命令：

```bash
ffmpeg -y -i INPUT.mp4 -filter_complex "
[0:v]crop=CW:CH:CX:CY[cropped];
[cropped]scale=958:1278,gblur=sigma=50[bg];
[cropped]scale=CONTENT_W:1278,format=yuva420p,
geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':
a='if(lt(X,60),X*255/60,if(gt(X,W-60),(W-X)*255/60,255))'
[main];
[bg][main]overlay=(W-w)/2:0
" -c:v libx264 -b:v 3000k OUTPUT.mp4
```

**关键细节**：
- `crop=CW:CH:CX:CY` — 仅在 Step 1 检测到黑边时添加，否则去掉此行，直接用 `[0:v]`
- `CONTENT_W` 必须是偶数（H.264 要求），如果计算结果为奇数则 +1 或 -1
- `scale=958:1278` 中 958 和 1278 都是偶数
- 羽化公式：左边 60px 内 alpha 从 0→255 线性渐变，右边 60px 内 255→0，中间 255
- **音频默认保留**，仅当用户明确要求去音频时才加 `-an`

#### Step 3: 截图验证
处理完成后截取首帧和尾帧检查：
```bash
ffmpeg -y -i OUTPUT.mp4 -vf "select=eq(n\,0)" -vframes 1 check_first.png
ffmpeg -y -i OUTPUT.mp4 -sseof -0.1 -vframes 1 check_last.png
```
检查要点：无黑边、羽化过渡自然、扩边模糊正确。

#### Step 4（按需）: 智能变速
当用户要求缩短时长时，优先使用 auto-editor 进行基于运动检测的智能变速。

**方案 A：auto-editor 智能变速（首选）**

auto-editor 会在画面运动少的片段自动加速，运动多的片段保持原速，实现自然的时长压缩。

```bash
auto-editor OUTPUT.mp4 --margin 1 --edit motion --output OUTPUT_SPEED.mp4
```

**注意事项**：
- margin 参数只接受整数，不接受浮点数
- 安装方式：`pipx install auto-editor`（不要用 pip，系统环境限制）
- 智能变速保持首尾帧，在不重要的地方加速

**方案 B：均匀加速（auto-editor 不可用时的降级方案）**

当 auto-editor 未安装或执行失败时，使用 `setpts` 滤镜进行均匀加速：

```bash
# 计算加速倍率
speed = source_duration / target_duration

# 应用加速（音频同步调整）
ffmpeg -y -i INPUT.mp4 -filter_complex "[0:v]setpts=PTS/SPEED[v];[0:a]atempo=SPEED[a]" -map "[v]" -map "[a]" OUTPUT.mp4
```

**限制**：
- `atempo` 滤镜范围：0.5 ≤ speed ≤ 2.0
- 超出范围需级联：如 speed=4.0 需要 `atempo=2.0,atempo=2.0`
- 无音频时省略 atempo，仅用 `setpts`

#### Step 5（按需）: 去除音频
仅当用户明确要求时：
```bash
ffmpeg -y -i INPUT.mp4 -c:v copy -an OUTPUT.mp4
```

---

### 二、图片输入

#### Step 0: 分析源图片
```python
from PIL import Image
import numpy as np

src = Image.open("INPUT.png").convert("RGBA")
arr = np.array(src)
alpha = arr[:, :, 3]
print(f"Size: {src.size}, Has transparency: {np.any(alpha < 255)}")
```

#### Step 1: 检测内容区域
对于有透明通道的图片，自动检测内容分布：
```python
row_has_content = np.any(alpha > 10, axis=1)
col_has_content = np.any(alpha > 10, axis=0)
content_rows = np.where(row_has_content)[0]
content_cols = np.where(col_has_content)[0]
```

如果图片有多个分离的内容区域（如上下两部分），检测间隔：
```python
diffs = np.diff(content_rows)
if np.max(diffs) > 50:  # 存在明显间隔
    gap_idx = np.argmax(diffs)
    top_region_end = content_rows[gap_idx]
    bottom_region_start = content_rows[gap_idx + 1]
```

#### Step 2: 生成封面图 (Cover 1053×1746)
```python
TW, TH = 1053, 1746

# 将内容缩放适配画布（可能需要 1.2x 等比例放大使内容充满可见区）
# 上部内容贴顶 y=0，下部内容贴底 y=TH-h
canvas = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
canvas.paste(top_scaled, (x_center, 0), top_scaled)
canvas.paste(bottom_scaled, (x_center, TH - bottom_h), bottom_scaled)

# 不可编辑区透明化
canvas_arr = np.array(canvas)
canvas_arr[115:1650, 46:1007, 3] = 0  # 不可编辑区

# 左右边距透明化
canvas_arr[:, :46, 3] = 0   # 左侧
canvas_arr[:, 1007:, 3] = 0  # 右侧

result = Image.fromarray(canvas_arr)
result.save("cover.png")
```

#### Step 3: 生成横幅图 (Banner 480×384)
```python
TW, TH = 480, 384

canvas = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
# 同理缩放、贴顶、贴底
canvas.paste(top_scaled, (x_center, 0), top_scaled)
canvas.paste(bottom_scaled, (x_center, TH - bottom_h), bottom_scaled)

# 不可编辑区透明化
canvas_arr = np.array(canvas)
canvas_arr[61:312, 10:470, 3] = 0  # 不可编辑区

# 左右边距透明化
canvas_arr[:, :10, 3] = 0
canvas_arr[:, 470:, 3] = 0

result = Image.fromarray(canvas_arr)
result.save("banner.png")
```

#### Step 4: 压缩
所有 PNG 使用 pngquant 压缩到 300KB 以内：
```bash
pngquant --quality=45-85 --force --output OUTPUT.png INPUT.png
```

---

## 命名规范

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| 处理后视频 | `{name}-processed.mp4` | `star-dream-processed.mp4` |
| 封面图 | `{name}-cover.png` | `star-dream-cover.png` |
| 横幅图 | `{name}-banner.png` | `star-dream-banner.png` |

用户可指定其他命名，以用户要求为准。

---

## 交付清单

### 输入为视频时
| 交付物 | 格式 | 规格 |
|--------|------|------|
| 处理后视频 | .mp4 | 958×1278, 3000kbit/s, H.264, 模糊扩边+60px羽化 |

音频保留/去除、智能变速均按用户要求执行。

### 输入为图片时
| 交付物 | 格式 | 规格 |
|--------|------|------|
| 封面蒙版图 | .png | 1053×1746, 不可编辑区透明, 左右透明, <300KB |
| 横幅蒙版图 | .png | 480×384, 不可编辑区透明, 左右透明, <300KB |

### 输入为视频+图片时
以上全部交付。

---

## 用户可调参数

处理过程中如用户要求微调，支持以下操作：
- **不可编辑区移动**：上移/下移/左移/右移 N px（重新生成蒙版）
- **不可编辑区扩展**：从中心向左右各扩展 N px
- **码率调整**：修改 `-b:v` 值
- **羽化半径**：修改 geq 中的 60 为其他值
- **智能变速**：通过 auto-editor 基于运动检测智能缩短视频时长（非均匀加速）
- **去除音频**：按用户要求加 `-an`
- **内容缩放比例**：调整图片内容在画布中的放大比例

---

## 注意事项

1. **H.264 偶数要求**：所有视频宽高必须为偶数，奇数时 +1 调整
2. **黑边检测优先**：处理前务必 cropdetect，源视频常有 2-4px 隐藏黑边
3. **截图验证**：视频处理后必须截取首尾帧检查黑边和羽化效果
4. **透明区域压缩**：大面积透明的 PNG 经 pngquant 压缩效率极高（通常 <50KB）
5. **auto-editor 安装**：使用 `pipx install auto-editor`，不要用 pip（系统环境限制）
6. **覆盖文件**：ffmpeg 命令始终加 `-y` 避免交互式确认阻塞
7. **变速优先级**：时长控制优先使用 auto-editor 智能变速；auto-editor 不可用时降级为 setpts 均匀加速
8. **音频默认保留**：不主动去除音频，仅在用户明确要求时才加 `-an`
9. **帧率不超过 30fps**：源视频帧率 >30 时，必须在 vf 滤镜链末尾加 `fps=30`；≤30 时可省略
