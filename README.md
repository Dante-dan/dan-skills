# dan-skills

Skills shared by Dan for improving daily work efficiency with Claude Code.

## Prerequisites

- Node.js environment installed
- Ability to run `npx bun` commands

## Installation

### Quick Install (Recommended)

```bash
npx skills add dante-dan/dan-skills
```

### Register as Plugin Marketplace

Run the following command in Claude Code:

```bash
/plugin marketplace add dante-dan/dan-skills
```

### Install Skills

**Option 1: Via Browse UI**

1. Select **Browse and install plugins**
2. Select **dan-skills**
3. Select the plugin(s) you want to install
4. Select **Install now**

**Option 2: Direct Install**

```bash
# Claude Code Plugin Marketplace
/plugin install fe-deploy-setup@dan-skills

# Or via npx skills
npx skills add dante-dan/dan-skills --skill fe-deploy-setup
```

**Option 3: Ask the Agent**

Simply tell Claude Code:

> Please install Skills from github.com/Dante-dan/dan-skills

## Update Skills

To update skills to the latest version:

**Plugin Marketplace:**

1. Run `/plugin` in Claude Code
2. Switch to **Marketplaces** tab (use arrow keys or Tab)
3. Select **dan-skills**
4. Choose **Update marketplace**

You can also **Enable auto-update** to get the latest versions automatically.

**npx skills:**

```bash
npx skills update
```

## Available Skills

### fe-deploy-setup

Auto-generates deployment infrastructure for **Nuxt 4 / Next.js** projects. One command to create a complete CI/CD + Docker deployment pipeline.

**Generated Files:**

| File | Purpose |
|------|---------|
| `.github/workflows/deploy.yml` | CI/CD: build → push Docker image to ghcr.io |
| `Dockerfile` | Production image (slim, non-root, build artifacts only) |
| `.dockerignore` | Docker build context exclusions |
| `deploys/docker-compose.prod.yml` | App + optional PostgreSQL orchestration |
| `deploys/deploy.sh` | VPS one-command deployment script |
| `deploys/.env.example` | Environment variable template |
| `deploys/ENV.md` | Environment variable documentation |

**Supported Frameworks:**

| Framework | Detection | Build Output |
|-----------|-----------|-------------|
| Nuxt 4 | `nuxt.config.ts` + `nuxt` in package.json | `.output/` |
| Next.js | `next.config.*` + `next` in package.json | `.next/standalone/` |

**Usage:**

Tell Claude Code any of these:

```
帮我生成部署配置
Set up deployment for this project
Generate CI/CD pipeline
```

The skill will automatically detect your project type, collect configuration through interactive questions, and generate all deployment files.

## Project Structure

```
dan-skills/
├── .claude/
│   └── skills -> ../src                  # Symlink for local dev / npx skills
├── .claude-plugin/
│   └── marketplace.json                  # Plugin Marketplace catalog
├── plugins/
│   └── fe-deploy-setup/
│       ├── .claude-plugin/
│       │   └── plugin.json               # Plugin manifest
│       └── skills/
│           └── fe-deploy-setup/
│               └── SKILL.md -> src/...   # Symlink to source
├── src/                                  # Skills source (canonical)
│   └── fe-deploy-setup/
│       ├── meta.json
│       └── SKILL.md
└── README.md
```

## License

MIT
