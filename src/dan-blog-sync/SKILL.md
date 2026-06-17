---
name: dan-blog-sync
description: Use when user wants to publish markdown articles to their blog at dhpie.com. Triggers on "发布博客", "同步博客", "blog sync", "publish to blog", "发到博客", or mentions dhpie.com publishing.
---

# Dan Blog Sync

Publish markdown files to dhpie.com blog.

## Language

Match user's language.

## Script

Determine this SKILL.md directory as `SKILL_DIR`. Publishing script: `${SKILL_DIR}/scripts/blog-publish.ts`

## Workflow

### Step 1: Check Auth

```bash
bun run ${SKILL_DIR}/scripts/blog-publish.ts --check-auth
```

If output is `AUTH_EXPIRED`, STOP and tell user:

> Token 已过期，请更新 `~/.Codex/skills/dan-blog-sync/.env` 中的 DHPIE_TOKEN。
> 登录 https://api.dhpie.com/proxy/qaqdmin 后从浏览器请求中复制新的 bearer token。

### Step 2: List Files

List all `.md` files in current directory, sorted by modification time (newest first). Present as numbered list for user to select (single or multiple).

### Step 3: For Each Selected File

For each file, read the content, then use LLM intelligence to generate:

| Field | Rule |
|-------|------|
| **title** | Filename without `.md` extension |
| **language** | Detect from content: Chinese → `zh`, English → `en` |
| **categoryId** | `zh` → `6684e45331b55c96fe1592f3`, `en` → `66853f5931b55c96fe159a4f` |
| **slug** | Generate URL-friendly slug from title. Must be unique — check with `--check-slug`. For zh/en pair, use different slugs. |
| **tags** | Generate 3-5 relevant tags based on content semantics |
| **summary** | Generate a concise summary (1-2 sentences) |
| **hook** | Generate an engaging hook in blockquote format (`> ...`) to attract readers. **Insert at the top of the original md file** after generating. |
| **text** | File content with images converted (see below) |
| **images** | `[]` (empty) |
| **copyright** | `true` |
| **allowComment** | `true` |
| **pin** | `false` |
| **pinOrder** | `1` |
| **relatedId** | `[]` |
| **isPublished** | `true` |

### Step 4: Image Path Check

Scan all `![alt](path)` in the markdown:

1. **Remote URLs** (`https://...`, `http://...`) → no action needed
2. **Local paths** (relative like `illustrations/foo/bar.jpg`, `imgs/foo.png`) → ask user:

> 检测到本地图片路径，是否需要调用 `duan-r2-upload` skill 上传到 CDN？

- If **yes** → invoke `dan-r2-skill` skill, which handles upload + path replacement automatically
- If **no** → skip image processing, keep local paths as-is (user will handle manually)

### Step 5: Preview & Confirm

Show preview of each post (title, slug, tags, summary, hook) and ask user to confirm before publishing.

### Step 6: Publish

Write payload to a temp JSON file, then:

```bash
bun run ${SKILL_DIR}/scripts/blog-publish.ts --payload-file /tmp/blog-post-payload.json
```

If output contains `TOKEN_EXPIRED`, remind user to update token (see Step 1).

### Step 7: Update Source File

After successful publish, update the original markdown file:

1. **Insert hook** (blockquote) at the top of the content (after frontmatter)
2. **Add `slug` and `link` to frontmatter** — so future conversations can reference the published URL without guessing:
   - `slug`: the slug used for publishing
   - `link`: full URL, e.g. `https://dhpie.com/posts/cn/<slug>` or `https://dhpie.com/posts/en/<slug>`
   - If these fields already exist in frontmatter, update them; otherwise add them

## Auth

Token stored in `${SKILL_DIR}/.env`:

```
DHPIE_TOKEN=your_token_here
```

Supports two token types:
- **API Key (recommended):** `txo*` format, created via blog admin panel (`/api/v2/auth/token`). Never expires.
- **JWT:** `eyJ*` format, expires every 14 days. If expired, user must re-login to get a new one.
