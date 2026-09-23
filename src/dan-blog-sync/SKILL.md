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

> Token 已过期，请更新 `~/.claude/skills/dan-blog-sync/.env` 中的 DHPIE_TOKEN。
> 登录 https://api.dhpie.com/proxy/qaqdmin → 设定 → API Key，新建一个 `txo` 开头的 API Key 填入。

### Step 2: List Files

List all `.md` files in current directory, sorted by modification time (newest first). Present as numbered list for user to select (single or multiple).

### Step 3: For Each Selected File

For each file, read the content, then use LLM intelligence to generate:

| Field | Rule |
|-------|------|
| **title** | Filename without `.md` extension |
| **language** | Detect from content: Chinese → `zh`, English → `en` |
| **categoryId** | `zh` → `158511301872074752` (cn), `en` → `158511301876269056` (en)。若报 categoryId 无效，用 `curl -s https://api.dhpie.com/api/v3/categories` 重新获取（v13 起为 Snowflake 字符串 ID） |
| **slug** | Generate URL-friendly slug from title. Must be unique — check with `--check-slug`. For zh/en pair, use different slugs. |
| **tags** | 3-5 tags. **先拉线上已有标签词表优先复用**：`curl -s "https://api.dhpie.com/api/v3/posts?size=50&page=1"`（及 page=2）汇总 `tags` 字段。命名规则（与 Obsidian 侧一致）：中文概念用中文（软件工程、自托管、数据迁移）；专有名词保持原文（AI、Docker、MCP、mx-space）；英文多词概念用 kebab-case（harness-engineering、context-engineering）；同一概念不要中英各建一个（已有 `软件工程` 就不要再造 `Software Engineering`）。文章若有 Obsidian frontmatter tags，直接沿用 |
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

## Updating an existing article

When the user specifies an existing article, update it in place; do not create another post or generate a new slug.

1. Resolve its ID from `GET /api/v3/posts?size=50&page=1` (paginate as needed), then read `GET /api/v3/posts/:id`. `GET /posts/get-url/:slug` returns only the category/slug path, not the ID or content. Back up the original response and local Markdown.
2. Merge edits into the latest `data.text`. Preserve unrelated content, original publication date, slug, category, tags, images, and publishing settings. For a dated report, mark later additions with their actual date.
3. Send **`PUT https://api.dhpie.com/api/v3/posts/:id`** with a complete editable payload. The admin interface uses this endpoint; creation uses `POST /posts`.
4. Use the existing API Key via `x-api-key`. Browser cookies, session tokens and copied browser fingerprint headers are unnecessary and must not be saved in skill files or examples.

Map read fields to write fields: `category_id` → `categoryId`, `content_format` → `contentFormat`, `is_published` → `isPublished`, `pin_at` → `pin`, `pin_order` → `pinOrder`, and `related[].id` → `relatedId`. Carry over `title`, `slug`, `text`, `summary`, `tags`, `images`, `meta`, and `copyright`. Do not blindly send the entire GET response. Omit `draftId` unless intentionally publishing a specific draft; it is not the post ID. Only alter summary or other metadata when the requested edit calls for it.

```bash
bun run ${SKILL_DIR}/scripts/blog-publish.ts \
  --update-id <post-id> \
  --expected-modified-at <modified_at-from-latest-GET> \
  --payload-file /tmp/blog-update-payload.json
```

The timestamp check detects changes before PUT, but is not an atomic server-side conditional write. If it fails, re-read and merge; do not overwrite concurrent edits. After success, GET the post again and compare text, links and preserved metadata; then synchronize the local Markdown. If the write outcome is uncertain, read back before retrying. Explicit user authorization to update the identified article is sufficient; do not add another routine publishing confirmation.

## Auth

Token stored in `${SKILL_DIR}/.env`:

```
DHPIE_TOKEN=your_token_here
```

Token type (core v13+, Better Auth):
- **API Key:** created in the blog admin panel (设定 → API Key). Sent as **`x-api-key: <key>` header** — NOT `Authorization: Bearer` (Bearer silently degrades to guest, since public endpoints still return 200).
- Legacy JWTs (`eyJ*`) from pre-v10 no longer work — the v10 auth rebuild invalidated them.

API notes (core v13): base is `/api/v3`; request bodies remain camelCase, responses come back as `{ data, meta }` with snake_case fields.
