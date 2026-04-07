---
name: dan-publish-all
description: One-click publish markdown articles with auto-generated illustrations and covers to blog (dhpie.com) and WeChat. Triggers on "发布各个平台", "publish all", "全平台发布", "发布到所有平台", "publish everywhere".
---

# dan-publish-all

一键发布 markdown 文章到所有平台：自动配图、生成封面、上传 CDN、发布博客和微信公众号。

## Language

Match user's language.

## Workflow Overview

```
输入文章 → 检查配图 → 检查封面 → 上传 R2 → 并行发布博客 + 公众号
```

### Step 1: Select Articles

List all `.md` files in current directory, sorted by modification time (newest first). Present as numbered list for user to select (single or multiple).

If user already specified files, skip this step.

### Step 2: Analyze Each Article

For each selected article, read the file and determine:

| Check | How |
|-------|-----|
| **Has illustrations?** | Scan for `![` references pointing to `illustrations/` directory |
| **Has cover?** | Scan for `![` references pointing to `cover-image/` directory, or check if `cover-image/{slug}/cover.jpg` exists |
| **Language** | Detect from content: Chinese → `zh`, English → `en` |
| **Is paired?** | Check if a corresponding zh/en version exists in the same directory |

Report findings to user:

```
文章分析结果：
1. ✓/✗ 配图 | ✓/✗ 封面 | zh | [title]
2. ✓/✗ 配图 | ✓/✗ 封面 | en | [title]
...
```

### Step 3: Generate Missing Assets (Parallel)

**CRITICAL**: Use sub-agents (Agent tool) to parallelize image generation across articles. Each article's assets are independent and can be generated concurrently.

#### 3a: Generate Illustrations (if missing)

For each article missing illustrations, launch a sub-agent that:

1. Reads the article content
2. Analyzes structure to identify 2-4 illustration positions
3. Generates illustrations with these settings:
   - **Density**: balanced (per-section)
   - **Type**: mixed (auto-select per illustration: framework, comparison, flowchart, infographic, etc.)
   - **Style**: blueprint (dark background, cyan/teal lines, tech schematic feel)
   - **Language**: bilingual (中文主标签 + English subtitle)
   - **Aspect ratio**: 16:9
4. Creates prompt files in `illustrations/{topic-slug}/prompts/`
5. Generates images using `baoyu-imagine`:
   ```bash
   bun "/Users/duan/.claude/plugins/marketplaces/baoyu-skills/skills/baoyu-imagine/scripts/main.ts" \
     --promptfiles <prompt_file> --image <output_path> --ar 16:9 --quality 2k --provider google
   ```
6. Post-processes each image:
   ```bash
   # Compress to JPEG
   bun "/Users/duan/.claude/plugins/marketplaces/baoyu-skills/skills/baoyu-compress-image/scripts/main.ts" \
     <image.png> --format jpeg --quality 95 --output <image.jpg>
   # Strip EXIF
   sips --deleteProperty all <image.jpg>
   ```
7. Inserts `![description](illustrations/{slug}/XX-type-name.jpg)` into the article at appropriate positions
8. If article has a paired zh/en version, inserts same image references into both

#### 3b: Generate Cover (if missing)

For each article (or article pair) missing a cover, launch a sub-agent that:

1. Reads the article content
2. Generates a cover image prompt with:
   - **Type**: conceptual
   - **Palette**: cool (articles 1-2) or dark (article 3) — auto-select based on content
   - **Rendering**: flat-vector
   - **Text**: title-subtitle (中文标题 + English subtitle)
   - **Mood**: balanced
   - **Font**: clean
   - **Aspect ratio**: 2.35:1
3. Creates prompt file in `cover-image/{topic-slug}/prompts/cover.md`
4. Generates image using `baoyu-imagine`
5. Post-processes (compress to JPEG q95 + strip EXIF)
6. Inserts `![cover](cover-image/{slug}/cover.jpg)` after front matter in the article
7. If article has a paired zh/en version, inserts same cover reference into both

### Step 4: Upload to R2

After all images for an article are generated, upload new images to R2:

```bash
SKILL_DIR="/Users/duan/Codebase/dan-skills/src/dan-r2-skill"
bun "$SKILL_DIR/scripts/main.ts" \
  --files "<comma-separated list of new image files>" \
  --dir "<article directory>"
```

This automatically:
- Uploads files to Cloudflare R2
- Replaces local paths in markdown files with CDN URLs

### Step 5: Publish to All Platforms (Parallel)

Launch sub-agents in parallel for each platform:

#### 5a: Publish to Blog (dhpie.com)

Invoke `dan-blog-sync` skill for all selected articles:

```bash
SKILL_DIR="/Users/duan/.claude/skills/dan-blog-sync"

# 1. Check auth
bun run $SKILL_DIR/scripts/blog-publish.ts --check-auth

# 2. For each article, generate payload and publish
bun run $SKILL_DIR/scripts/blog-publish.ts --payload-file /tmp/blog-post-payload-N.json
```

Payload fields:

| Field | Rule |
|-------|------|
| **title** | Filename without `.md` extension |
| **language** | `zh` or `en` (detected in Step 2) |
| **categoryId** | zh → `6684e45331b55c96fe1592f3`, en → `66853f5931b55c96fe159a4f` |
| **slug** | Generate URL-friendly slug from title (check uniqueness with `--check-slug`) |
| **tags** | From front matter, or generate 3-5 relevant tags |
| **summary** | From front matter, or generate 1-2 sentence summary |
| **hook** | From front matter `hook_a`, format as blockquote `> ...` |
| **text** | Full markdown content (without front matter) |
| **images** | `[]` |
| **copyright** | `true` |
| **allowComment** | `true` |
| **pin** | `false` |
| **pinOrder** | `1` |
| **relatedId** | `[]` |
| **isPublished** | `true` |

After publishing, insert hook blockquote at top of source file.

#### 5b: Publish to WeChat (Chinese articles only)

**IMPORTANT**: WeChat publishing MUST happen AFTER blog publishing, because the blog URL is needed as the WeChat article's original link (原文链接).

For each Chinese article, invoke `baoyu-post-to-wechat` skill:

1. Convert markdown to WeChat-compatible HTML using `baoyu-markdown-to-html`
2. Upload cover image as WeChat thumb media
3. Set `content_source_url` (原文链接) to the blog URL from Step 5a, format: `https://dhpie.com/posts/cn/{slug}`
4. Publish via WeChat API as draft

### Step 6: Report Results

```
发布完成！

配图：X 篇文章生成了 Y 张插图
封面：生成了 Z 张封面图
R2：上传了 N 个文件
博客：发布了 A 篇文章到 dhpie.com
  - [title1]: [url1]
  - [title2]: [url2]
公众号：发布了 B 篇草稿到微信公众号
  - [title1]: media_id
  - [title2]: media_id

请前往微信公众号后台发布草稿：https://mp.weixin.qq.com
```

## Parallelization Strategy

```
                    ┌─ Agent: Article 1 illustrations ─┐
Step 3 (parallel) ──┼─ Agent: Article 2 illustrations ─┼── wait all
                    ├─ Agent: Article 3 illustrations  │
                    ├─ Agent: Cover 1                  │
                    ├─ Agent: Cover 2                  │
                    └─ Agent: Cover 3                 ─┘
                              │
Step 4 (sequential) ── R2 upload (--files, all new images)
                              │
Step 5a ── Agent: Blog publish (all articles) ── get blog URLs
                              │
Step 5b ── Agent: WeChat publish (zh only, with blog URL as 原文链接)
                              │
Step 6 ── Report results
```

## Notes

- All image generation uses `baoyu-imagine` with Google provider
- Blueprint style ensures visual consistency across the series
- Paired zh/en articles share the same illustrations and covers
- WeChat only receives Chinese articles; blog receives both zh and en
- R2 upload uses `--files` flag to only upload newly generated images
- If auth for any platform expires, report which platform and stop that branch only
