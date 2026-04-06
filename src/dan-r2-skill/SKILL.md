---
name: dan-r2-skill
description: Upload files from current directory to Cloudflare R2 and replace local paths in markdown. Use when user mentions "上传R2", "upload to R2", "上传图片到R2", "R2上传", "upload images".
---

# dan-r2-skill

将当前目录的文件上传到 Cloudflare R2，并自动替换 markdown 中的本地路径为公开 URL。

## Script Directory

Scripts are located at: `${SKILL_DIR}/scripts/`

## Prerequisites

Config must exist. If not, run init first.

## Workflow

### Step 1: Check config exists

```bash
cat ~/.dan/config.json
```

If file doesn't exist or R2 credentials are empty, run:

```bash
npx -y bun ${SKILL_DIR}/scripts/main.ts --init
```

Then ask user to fill in their R2 credentials via AskUserQuestion, offering two levels:
- **User level** (`~/.dan/config.json`): shared across all projects
- **Project level** (`.dan/config.json` in project root): overrides user-level for this project

### Step 2: Ask user preferences

Use AskUserQuestion to ask:

1. **Upload content type**: images (default) / docs / all / custom glob
2. **Upload directory**: current directory (default) or specify path
3. **Additional options**: dry-run preview first? clean local files after?

### Step 3: Execute upload

Run the script with the appropriate flags:

```bash
# Preview first (recommended)
npx -y bun ${SKILL_DIR}/scripts/main.ts --dry-run [--dir <path>] [--content <type>] [--glob <pattern>]

# Then actual upload
npx -y bun ${SKILL_DIR}/scripts/main.ts [--dir <path>] [--content <type>] [--glob <pattern>] [--clean] [--no-replace]
```

### Step 4: Report results

Show user:
- Number of files uploaded
- Public URLs generated
- Number of markdown references replaced
- Any errors encountered

## CLI Options

| Flag | Description |
|------|-------------|
| `--dir <path>` | Upload directory (default: cwd) |
| `--content <type>` | `images` / `docs` / `all` (default: `images`) |
| `--glob <pattern>` | Custom glob (overrides --content) |
| `--files <paths>` | Comma-separated specific files to upload (e.g. `--files "a.jpg,b.png"`) |
| `--new-only` | Only upload files not already on R2 (incremental upload) |
| `--dry-run` | Preview only, no upload |
| `--clean` | Delete local files after upload |
| `--no-replace` | Skip markdown path replacement |
| `--init` | Create/update config file |
| `--init-level <lvl>` | `user` or `project` |

## Config

Two-level config with project overriding user:

- User: `~/.dan/config.json`
- Project: `.dan/config.json`

```json
{
  "r2": {
    "accountId": "",
    "accessKeyId": "",
    "secretAccessKey": "",
    "bucket": "",
    "endpoint": "",
    "publicDomain": ""
  },
  "upload": {
    "pathPrefix": "blog/{date}",
    "content": "images",
    "replace": true,
    "clean": false
  }
}
```

`{date}` in pathPrefix is replaced with the file's creation date (YYYY-MM-DD).
