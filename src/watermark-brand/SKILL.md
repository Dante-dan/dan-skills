---
name: watermark-brand
description: 给图片加品牌水印，明水印（可见 logo 平铺纹理/角标）+暗水印（LSB 隐写，肉眼不可见但可提取验证）。支持 X、微信公众号、小红书、抖音四个平台预设。当用户说"加水印"、"加个 X/微信/小红书/抖音水印"、"防盗图"时使用。
---

# 品牌水印 (Brand Watermark)

## 核心定位

给图片加双层水印，用于内容发布时的版权标注和防盗图：

1. **明水印**：可见的品牌 logo + 账号信息。默认样式是"LV 老花"式平铺纹理——logo 和账号名以低透明度、倾斜角度重复铺满全图，融入内容本身而非孤立的单个角标，防裁剪能力更强。也支持传统角标样式（logo+文字放在图片一角）。
2. **暗水印**：LSB（最低有效位）隐写，把水印信息编码进像素数据，肉眼完全不可见，可用脚本提取验证图片来源。注意这是水印技术里的"盲水印/隐写"含义（人眼不可见但可提取），不是抗攻击的数字版权水印——过度的图像处理（强力压缩、大幅缩放、加噪）会破坏它。

核心脚本：`scripts/watermark.py`，四个平台的官方 logo 素材在 `assets/logos/`。

---

## 平台预设

| `--platform` | 平台 | logo 来源 | 素材文件 |
|---|---|---|---|
| `x` | X (Twitter) | X 官方 Brand Toolkit (about.x.com) | `x-black.png` / `x-white.png` / `x.svg` |
| `wechat` | 微信公众号 | 微信官方 WeDesign 品牌指引站 + 官方 newsroom 图标资源 | `wechat.png`（完整标志，corner 专用）/ `wechat-icon-white.png`（纯气泡图标无文字，tile 专用） |
| `xiaohongshu` | 小红书 | 小红书官方 SVG | `xiaohongshu.png`（完整胶囊 logo）/ `xiaohongshu-mono.png`（纯文字红色，tile 专用） |
| `douyin` | 抖音 | 抖音创作者中心官方 CDN | `douyin-icon.png`（单色音符图标） |

所有 logo 均来自平台官方渠道，仅用于用户本人内容的品牌标注，不用于冒充或伪造平台官方身份。

---

## 使用方法

### 基本调用

```bash
python3 scripts/watermark.py INPUT.png OUTPUT.png --platform x --handle "@duanjl_china"
```

默认使用 `tile`（平铺纹理）样式，同时嵌入明水印和暗水印。

### 完整参数

```bash
python3 scripts/watermark.py IN.png OUT.png \
  --platform x|wechat|xiaohongshu|douyin \
  --handle "账号名/ID文字" \
  [--style tile|corner]       # 默认 tile（平铺纹理），corner 为传统角标
  [--corner br|bl|tr|tl]      # corner 样式下 logo 位置，默认 bl（左下角）
  [--opacity 60]              # tile 样式透明度 0-255，默认 60
  [--angle -22]               # tile 样式旋转角度，默认 -22
  [--no-visible]              # 跳过明水印，只做暗水印
  [--no-blind]                # 跳过暗水印，只做明水印
  [--blind-message "自定义内容"]  # 默认自动生成 "{platform}:{handle}"
```

### 提取暗水印（验证用）

```bash
python3 scripts/watermark.py --extract IMAGE.png
```

输出提取到的暗水印文本，用于核实图片是否经过本工具加水印、以及水印内容是否完整。

### 四个平台调用示例

```bash
# X
python3 scripts/watermark.py in.png out-x.png --platform x --handle "@duanjl_china"

# 微信公众号
python3 scripts/watermark.py in.png out-wechat.png --platform wechat --handle "蛋黄派的日常"

# 小红书
python3 scripts/watermark.py in.png out-xhs.png --platform xiaohongshu --handle "灯塔笔记（AI版）"

# 抖音
python3 scripts/watermark.py in.png out-douyin.png --platform douyin --handle "蛋黄派 · DHPI"
```

---

## 明水印样式说明

### tile（默认，平铺纹理）

logo 缩小后按网格平铺、整体旋转 -22°，裁剪覆盖全图，模拟"品牌图案"效果：
- 深色/复杂内容区域：水印自然被内容盖过，不抢视觉焦点
- 浅色留白区域：水印清晰可辨，起到防盗图作用
- 覆盖面积大，局部裁剪也很难完全去除水印

**颜色处理策略**（`PLATFORM_KEEP_COLOR` 决定）：
- **小红书**：保留品牌色（小红书红），只调整透明度（`fade()`），tile 专用素材是简化过的纯色形状（`xiaohongshu-mono.png` 只保留"小红书"文字），避免大面积底色在低透明度下糊成模糊色斑
- **X、微信、抖音**：logo 统一改成低调深棕色（`recolor()`），在浅色背景上可见、不过分突兀。微信 tile 专用素材是从官方图标裁出的纯气泡图标（`wechat-icon-white.png`，不含 "WeChat" 文字），配文字层的账号名一起平铺，不出现"微信"字样

### corner（角标）

logo + 账号文字放在图片一角，默认左下角（`--corner bl`）。更紧凑、不遮挡主视觉，但防盗图能力较弱（裁剪一角即可去除）。

选左下角作为默认角标位置的原因：右下角常与图片自带的文字/来源标注冲突（AI 生成图常见），左下角更少冲突。

---

## 暗水印技术细节

`embed_blind_watermark()` / `extract_blind_watermark()`：

- 把 `消息长度(4字节) + UTF-8消息内容` 编码进 RGB 图像红色通道的最低位（LSB），重复写入 20 次（`repeat=20`）铺满图像容量
- 提取时用多数投票（`Counter.most_common`）从 20 份副本中恢复出正确内容，即使部分区域被裁剪/覆盖仍可能恢复
- 必须无损保存（PNG），JPEG 有损压缩会破坏最低位、导致水印丢失
- 这不是抗攻击的鲁棒水印——用户如果对图片做去水印类的像素扰动处理（参考 `dewatermark-image` skill 的缩放+加噪流程），暗水印同样会被破坏。两者是对立技术，不要在同一张图上先加暗水印又跑去水印流程

---

## 新增平台 / 更新 logo

1. 从平台官方渠道获取 logo（官方 Brand Kit / 品牌资源页面，不用第三方素材站的非官方版本）
2. 存入 `assets/logos/{platform}.png`，如果 logo 复杂（多色/大面积底色），额外做一版简化的纯形状 tile 专用素材 `assets/logos/{platform}-mono.png`（提取文字/图标轮廓，转单一品牌色，透明背景）
3. 在 `scripts/watermark.py` 的 `PLATFORM_LOGOS`、`PLATFORM_LOGOS_TILE`、`PLATFORM_KEEP_COLOR` 三个字典里注册新平台

---

## 注意事项

1. **只用官方 logo 素材**：不自行绘制/复刻平台 logo，必须从官方渠道获取（Brand Toolkit、品牌指引站、创作者中心等），避免商标风险
2. **tile 样式的复杂 logo 需要简化**：直接把带渐变色或大面积底色的原始 logo 缩小做低透明度平铺，效果会糊成模糊色斑（微信、小红书踩过这个坑）——提取纯文字/线条轮廓做成单色 mono 版本效果更好
3. **暗水印与去水印流程互斥**：暗水印基于像素 LSB，任何有损压缩或像素扰动都会破坏它；不要指望一张图同时"有暗水印"又"抗各种压缩/裁剪"
4. **PNG 优先**：明暗水印全流程建议全程用 PNG（无损），中间不要转 JPEG，否则暗水印会丢失、明水印细节也可能因压缩伪影劣化
5. **默认输出**：不覆盖原图，输出到用户指定路径或 `{原文件名}-watermarked.png`
