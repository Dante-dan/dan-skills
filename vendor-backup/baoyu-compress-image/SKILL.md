---
name: baoyu-compress-image
description: Compresses images to WebP (default) or PNG with automatic tool selection. Use when user asks to "compress image", "optimize image", "convert to webp", or reduce image file size.
---

# Image Compressor

Compresses images using best available tool (sips → cwebp → ImageMagick → Sharp).

## Script Directory

Scripts in `scripts/` subdirectory. Replace `${SKILL_DIR}` with this SKILL.md's directory path.

| Script | Purpose |
|--------|---------|
| `scripts/main.ts` | Image compression CLI |

## Preferences (EXTEND.md)

Use Bash to check EXTEND.md existence (priority order):

```bash
# Check project-level first
test -f .baoyu-skills/baoyu-compress-image/EXTEND.md && echo "project"

# Then user-level (cross-platform: $HOME works on macOS/Linux/WSL)
test -f "$HOME/.baoyu-skills/baoyu-compress-image/EXTEND.md" && echo "user"
```

┌────────────────────────────────────────────────────────┬───────────────────┐
│                          Path                          │     Location      │
├────────────────────────────────────────────────────────┼───────────────────┤
│ .baoyu-skills/baoyu-compress-image/EXTEND.md           │ Project directory │
├────────────────────────────────────────────────────────┼───────────────────┤
│ $HOME/.baoyu-skills/baoyu-compress-image/EXTEND.md     │ User home         │
└────────────────────────────────────────────────────────┴───────────────────┘

┌───────────┬───────────────────────────────────────────────────────────────────────────┐
│  Result   │                                  Action                                   │
├───────────┼───────────────────────────────────────────────────────────────────────────┤
│ Found     │ Read, parse, apply settings                                               │
├───────────┼───────────────────────────────────────────────────────────────────────────┤
│ Not found │ Use defaults                                                              │
└───────────┴───────────────────────────────────────────────────────────────────────────┘

**EXTEND.md Supports**: Default format | Default quality | Keep original preference

## Usage

```bash
npx -y bun ${SKILL_DIR}/scripts/main.ts <input> [options]
```

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `<input>` | | File or directory | Required |
| `--output` | `-o` | Output path | Same path, new ext |
| `--format` | `-f` | webp, png, jpeg | webp |
| `--quality` | `-q` | Quality 0-100 | 80 |
| `--keep` | `-k` | Keep original | false |
| `--recursive` | `-r` | Process subdirs | false |
| `--keep-metadata` | | Preserve EXIF/metadata | false (stripped by default) |
| `--clean` | | Weaken invisible AI watermarks (e.g., SynthID). Lossy, best-effort. | false |
| `--json` | | JSON output | false |

## EXIF & Watermark Notes

- **Metadata is stripped by default** (EXIF, ICC profile, AI-generation tags). Pass `--keep-metadata` to preserve.
  - cwebp uses `-metadata none`, ImageMagick uses `-strip`, Sharp omits `withMetadata()`, sips falls back to `exiftool -all=` if installed.
- `--clean` does an extra pass to perturb invisible watermarks like SynthID: 97% downsample → upsample (lanczos3) + 1° hue rotate + 0.3px blur + re-encode. **Best-effort, not guaranteed.** Slightly degrades image quality. Visible/overlay watermarks are not affected — use a separate inpainting tool for those.

## Examples

```bash
# Single file → WebP (replaces original)
npx -y bun ${SKILL_DIR}/scripts/main.ts image.png

# Keep PNG format
npx -y bun ${SKILL_DIR}/scripts/main.ts image.png -f png --keep

# Directory recursive
npx -y bun ${SKILL_DIR}/scripts/main.ts ./images/ -r -q 75

# JSON output
npx -y bun ${SKILL_DIR}/scripts/main.ts image.png --json
```

**Output**:
```
image.png → image.webp (245KB → 89KB, 64% reduction)
```

## Extension Support

Custom configurations via EXTEND.md. See **Preferences** section for paths and supported options.
