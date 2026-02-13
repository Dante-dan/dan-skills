---
name: fe-deploy-setup
description: Auto-generates deployment infrastructure for Nuxt 4 / Next.js projects. Creates GitHub Actions CI/CD workflow (push to main → build → push Docker image to ghcr.io), Dockerfile, Docker Compose, deploy script, and environment variable documentation. Use when user mentions "部署", "deploy", "CI/CD", "docker", "上线", "发布到服务器".
---

# Deploy Setup

自动检测项目类型，生成完整的部署基础设施文件。

## Supported Frameworks

| Framework | Detection | Build Output | Server Command |
|-----------|-----------|-------------|----------------|
| Nuxt 4 | `nuxt.config.ts` + `nuxt` in package.json | `.output/` | `node .output/server/index.mjs` |
| Next.js | `next.config.*` + `next` in package.json | `.next/standalone/` | `node server.js` |

## Generated Files

| File | Purpose |
|------|---------|
| `.github/workflows/deploy.yml` | CI/CD: build → push Docker image to ghcr.io → (optional CDN upload) |
| `Dockerfile` | Production image (slim, non-root, build artifacts only) |
| `.dockerignore` | Docker build context exclusions |
| `deploys/docker-compose.prod.yml` | App + optional PostgreSQL orchestration |
| `deploys/deploy.sh` | VPS one-command deployment script |
| `deploys/.env.example` | Environment variable template with grouped categories |
| `deploys/ENV.md` | Environment variable documentation (required/optional tables) |

---

## Workflow

执行以下 5 个步骤，按顺序完成：

```
1. Detect   → 读取项目文件，判断框架类型、包管理器、Node 版本
2. Collect  → 通过 AskUserQuestion 收集部署配置（项目名、端口、域名等）
3. Generate → 使用 Write tool 生成 7 个部署文件
4. Audit    → 安全检查（.env 排除、端口绑定、无硬编码密钥）
5. Summary  → 告诉用户生成了什么、接下来做什么
```

---

## Step 1: Detect Project Type

读取以下文件判断框架类型：

1. **`package.json`** — check `dependencies` and `devDependencies` for `nuxt` or `next`
2. **`nuxt.config.ts` / `nuxt.config.js`** — confirms Nuxt
3. **`next.config.ts` / `next.config.js` / `next.config.mjs`** — confirms Next.js

同时提取：

- **Node.js version**: from `engines.node` in package.json (fallback: `lts`)
- **Package manager**: check for `pnpm-lock.yaml` (pnpm), `yarn.lock` (yarn), `package-lock.json` (npm)
- **Existing deploy files**: if `.github/workflows/deploy.yml`, `Dockerfile`, `deploys/` already exist, warn the user and ask before overwriting

Detection output example:
```
检测结果:
  框架: Nuxt 4
  Node.js: 24.12.0
  包管理器: pnpm
  已有部署文件: 无
```

---

## Step 2: Collect Configuration

通过 AskUserQuestion 收集用户配置。先展示检测结果，然后分组询问（每组 2-3 个相关问题，避免逐一询问的繁琐体验）：

1. **Project name** — default: `name` from package.json
   - 用于 Docker container name, compose service name, etc.
2. **Host port** — default: `3000`
   - VPS 上暴露的端口（映射到容器内部 3000）
3. **Domain name** — e.g., `example.com`
   - 用于 env template 和文档
4. **Database** — PostgreSQL yes/no
   - Hint: check if `pg`, `postgres`, `@prisma/client`, `drizzle-orm` is in dependencies
5. **CDN URL** — optional
   - 用于静态资源分发（如 Cloudflare R2）
   - 留空表示不使用 CDN
6. **Extra system deps** — e.g., `ffmpeg`, `imagemagick`
   - 用于 Dockerfile 中的 `apt-get install`
7. **Entrypoint script** — does the project need a custom entrypoint?
   - e.g., for DB migrations before server start
   - Check if `scripts/docker-entrypoint.sh` or migration files exist

---

## Step 3: Generate Files

使用 Write tool 生成以下 7 个文件。所有 `{{PLACEHOLDER}}` 占位符必须替换为实际值。

---

### Template 1: `.github/workflows/deploy.yml`

GitHub Actions CI/CD workflow. 使用 `${{ secrets.GITHUB_TOKEN }}` 推送到 ghcr.io，无需额外配置 secrets.

**Adaptation notes (生成时根据检测结果调整):**
- **Package manager:** Only include `pnpm/action-setup` step if pnpm is detected. For yarn/npm, omit it.
- **Node version:** From `engines.node` in package.json, or use `lts`.
- **Install command:** `pnpm install --frozen-lockfile` / `yarn install --frozen-lockfile` / `npm ci`
- **Build command:** `pnpm build` / `yarn build` / `npm run build`
- **CDN step:** Only include the "Upload to CDN" step if user configured CDN. Adapt paths per framework:
  - Nuxt: `.output/public/_nuxt/`
  - Next.js: `.next/static/`

```yaml
name: Build and Deploy

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      # --------------------------------------------------------
      # Package Manager Setup
      # --------------------------------------------------------
      # 如果是 pnpm，包含以下步骤；yarn/npm 则省略此步骤
      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        # 自动读取 package.json 中的 packageManager 字段

      - name: Setup Node.js
        uses: actions/setup-node@v6
        with:
          node-version: '{{NODE_VERSION}}'
          cache: '{{PACKAGE_MANAGER}}'
          # pnpm / yarn / npm

      - name: Install dependencies
        run: {{INSTALL_COMMAND}}
        # pnpm install --frozen-lockfile
        # yarn install --frozen-lockfile
        # npm ci

      # --------------------------------------------------------
      # Build
      # --------------------------------------------------------
      - name: Build application
        run: {{BUILD_COMMAND}}
        # pnpm build / yarn build / npm run build

      # --------------------------------------------------------
      # Optional: Upload static assets to CDN
      # --------------------------------------------------------
      # >>> CDN 块：仅在用户配置了 CDN 时包含，否则删除整个块 <<<
      - name: Upload client assets to CDN
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.R2_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.R2_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
          R2_BUCKET_NAME: ${{ secrets.R2_BUCKET_NAME }}
          R2_ENDPOINT: ${{ secrets.R2_ENDPOINT }}
        run: |
          pip install awscli
          echo "Uploading client-side assets to CDN..."
          # Nuxt: 上传 .output/public/_nuxt/
          aws s3 sync .output/public/_nuxt/ s3://$R2_BUCKET_NAME/{{PROJECT_NAME}}/_nuxt/ \
            --endpoint-url $R2_ENDPOINT \
            --cache-control "public, max-age=31536000, immutable" \
            --exclude "*.html" \
            --no-progress
          echo "Client assets uploaded to CDN"
      # >>> CDN 块结束 <<<

      # --------------------------------------------------------
      # Docker Build & Push to ghcr.io
      # --------------------------------------------------------
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64

      # --------------------------------------------------------
      # Summary
      # --------------------------------------------------------
      - name: Deployment summary
        run: |
          echo "## Deployment Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Docker Image" >> $GITHUB_STEP_SUMMARY
          echo "- **Registry**: \`${{ env.REGISTRY }}\`" >> $GITHUB_STEP_SUMMARY
          echo "- **Image**: \`${{ env.IMAGE_NAME }}\`" >> $GITHUB_STEP_SUMMARY
          echo "- **Tags**: \`${{ steps.meta.outputs.tags }}\`" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Quick Start" >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`bash" >> $GITHUB_STEP_SUMMARY
          echo "docker pull ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest" >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
```

---

### Template 2: `Dockerfile`

Production image. Build happens in CI/CD, NOT inside the container. The Dockerfile only copies pre-built artifacts.

**Security measures:**
- `node:{{NODE_VERSION}}-slim` base image (minimal attack surface)
- Non-root user (`appuser`) when no custom entrypoint needs root
- No source code in image — only build artifacts
- `.env` excluded via `.dockerignore`
- `ENV NODE_ENV=production` set explicitly

#### Nuxt 4 variant

```dockerfile
FROM node:{{NODE_VERSION}}-slim

# 安装系统依赖（根据用户配置调整）
# 如无额外依赖，删除此 RUN 块
RUN apt-get update && apt-get install -y --no-install-recommends \
    {{SYSTEM_DEPS}} && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制 CI/CD 中预构建的产物（不在 Docker 内构建）
COPY .output /app/.output
COPY package.json /app/package.json

# --- 可选: 自定义 entrypoint（如需数据库迁移） ---
# COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
# COPY server/database/migrations /app/server/database/migrations
# RUN chmod +x /app/docker-entrypoint.sh

# 创建非 root 用户
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --create-home appuser

# 设置文件所有权
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 3000

ENV NODE_ENV=production

# 如有自定义 entrypoint:
# ENTRYPOINT ["/app/docker-entrypoint.sh"]
# 否则直接启动:
CMD ["node", ".output/server/index.mjs"]
```

#### Next.js variant (standalone output)

**IMPORTANT:** Requires `output: 'standalone'` in `next.config.js` / `next.config.ts`. 生成时提醒用户检查此配置。

```dockerfile
FROM node:{{NODE_VERSION}}-slim

WORKDIR /app

# 复制 standalone 构建产物
COPY .next/standalone /app/
COPY .next/static /app/.next/static
COPY public /app/public

# 创建非 root 用户
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --create-home appuser

# 设置文件所有权
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 3000

ENV NODE_ENV=production
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

**Adaptation notes (生成时调整):**
- If user has system dependencies (`ffmpeg`, `imagemagick`, etc.), add `apt-get install` block
- If user needs custom entrypoint (DB migrations), add ENTRYPOINT and COPY migration files
- If user has binary tools to copy, add corresponding COPY commands
- For Nuxt: remind user about `.output/` directory structure
- For Next.js: remind user to set `output: 'standalone'` in `next.config`
- If custom entrypoint needs root-level operations, move `USER appuser` to after those operations or handle in entrypoint script with `gosu`

---

### Template 3: `.dockerignore`

**Nuxt 4 版本：**

```
node_modules
.nuxt
.git
.gitignore
.env
.env.*
.DS_Store
.idea
.vscode
*.log
deploys
docs
*.md
!package.json
```

**Next.js 版本：**

```
node_modules
.next/cache
.git
.gitignore
.env
.env.*
.DS_Store
.idea
.vscode
*.log
deploys
docs
*.md
!package.json
```

**Adaptation notes:**
- **Nuxt 4:** `.output/` is NOT ignored — it contains the pre-built server and client assets needed by the Docker image. `.nuxt/` (dev cache) IS ignored.
- **Next.js:** `.next/standalone/` and `.next/static/` are NOT ignored — they are the build output. Only `.next/cache/` is ignored. Do NOT add `.next` as a blanket exclusion, or the Dockerfile COPY will fail.
- `deploys/` is ignored to prevent .env files from leaking into the image
- `!package.json` is explicitly un-ignored because `*.md` might catch it in some glob implementations

---

### Template 4: `deploys/docker-compose.prod.yml`

Docker Compose production configuration. All ports bind to `127.0.0.1` only (requires reverse proxy for public access).

**Adaptation notes (生成时调整):**
- Replace all `{{PROJECT_NAME}}` with user's project name
- Replace `{{HOST_PORT}}` with user's chosen port
- If **no database**: remove entire `postgres` service, `depends_on` block, database environment variables, and `postgres_data` volume
- Environment variables: scan project's existing `.env.example`, `nuxt.config.ts` `runtimeConfig`, or `next.config.*` `env` to populate the environment section
- Port binding: ALWAYS use `127.0.0.1:` prefix (localhost only, behind reverse proxy)

```yaml
services:
  # ----------------------------------------------------------
  # PostgreSQL Database
  # 仅在需要数据库时包含此 service
  # ----------------------------------------------------------
  postgres:
    image: postgres:16-alpine
    container_name: {{PROJECT_NAME}}-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-{{PROJECT_NAME}}}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-{{PROJECT_NAME}}}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M

  # ----------------------------------------------------------
  # Application
  # ----------------------------------------------------------
  app:
    image: ghcr.io/${GITHUB_REPOSITORY}:latest
    container_name: {{PROJECT_NAME}}
    # 仅在使用数据库时包含 depends_on
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      # 只绑定到 localhost，避免直接暴露到公网
      # 通过反向代理（Nginx/Caddy/Cloudflare Tunnel）访问
      - "127.0.0.1:${APP_PORT:-{{HOST_PORT}}}:3000"
    environment:
      # Database（仅在启用数据库时包含）
      - DATABASE_URL=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-{{PROJECT_NAME}}}
      # Application
      - NODE_ENV=production
      # --- 根据项目扫描结果添加更多环境变量 ---
      # - NUXT_PUBLIC_SITE_URL=${NUXT_PUBLIC_SITE_URL}
      # - NUXT_PUBLIC_CDN_URL=${CDN_URL:-}
    volumes:
      - app-temp:/tmp/{{PROJECT_NAME}}
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000/', (res) => { if (res.statusCode === 200) process.exit(0); else process.exit(1); }).on('error', () => process.exit(1))"]
      interval: 5s
      timeout: 10s
      retries: 10
      start_period: 10s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M

networks:
  app-network:
    driver: bridge

volumes:
  app-temp:
    driver: local
  # 仅在使用数据库时包含
  postgres_data:
    driver: local
```

---

### Template 5: `deploys/deploy.sh`

VPS 一键部署脚本。具备环境检查、配置验证、彩色输出、滚动更新。

**Adaptation notes:**
- Replace `{{PROJECT_NAME}}` with user's project name
- This is the default version. If user wants advanced rolling updates (per-service health check with timeout), generate the advanced version modeled after the reference `deploy.sh`.

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "{{PROJECT_NAME}} - Deploy"
echo "=========================================="
echo ""

# ============================================================
# 环境检查
# ============================================================

echo "检查运行环境..."
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker 未安装${NC}"
    echo "安装: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 检查 Docker Compose V2
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose V2 不可用${NC}"
    exit 1
fi

# 检查 Docker 守护进程
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker 守护进程未运行${NC}"
    echo "请启动 Docker: systemctl start docker"
    exit 1
fi

# 检查是否以 root 运行（警告但不阻止）
if [ "$(whoami)" = "root" ]; then
    echo -e "${YELLOW}Warning: 当前以 root 用户运行${NC}"
    echo "建议: usermod -aG docker YOUR_USER"
    echo ""
fi

echo -e "${GREEN}Docker 环境检查通过${NC}"
echo ""

# ============================================================
# 配置文件检查
# ============================================================

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        chmod 600 .env
        echo -e "${YELLOW}已创建 .env 文件（从 .env.example 复制）${NC}"
        echo "请编辑 .env 文件后重新运行此脚本。"
        echo ""
        echo "  vim .env"
        echo "  bash deploy.sh"
        echo ""
        exit 0
    else
        echo -e "${RED}Error: .env.example 文件不存在${NC}"
        exit 1
    fi
fi

# 加载环境变量
set -a
source .env
set +a

# 验证必填变量
if [ -z "${GITHUB_REPOSITORY:-}" ]; then
    echo -e "${RED}Error: GITHUB_REPOSITORY 未配置${NC}"
    echo "请编辑 .env，设置 GITHUB_REPOSITORY=owner/repo"
    exit 1
fi

# 如果启用了数据库，验证密码已设置
if grep -q "postgres:" docker-compose.prod.yml 2>/dev/null; then
    if [ -z "${POSTGRES_PASSWORD:-}" ] || [ "${POSTGRES_PASSWORD}" = "your_secure_password_here" ]; then
        echo -e "${RED}Error: POSTGRES_PASSWORD 未配置或使用了默认值${NC}"
        echo "请编辑 .env，设置安全的数据库密码"
        exit 1
    fi
fi

echo -e "${GREEN}配置文件验证通过${NC}"
echo ""

# 显示配置摘要
echo "部署配置:"
echo "  镜像: ghcr.io/$GITHUB_REPOSITORY:latest"
echo "  端口: ${APP_PORT:-3000}"
echo ""

# ============================================================
# GitHub Container Registry 认证检查
# ============================================================

echo "检查镜像仓库认证..."

if ! docker manifest inspect "ghcr.io/$GITHUB_REPOSITORY:latest" &> /dev/null; then
    echo -e "${YELLOW}Warning: 无法访问镜像，可能需要认证${NC}"
    echo ""
    echo "请先登录 GitHub Container Registry:"
    echo '  echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin'
    echo ""
    echo "其中 GITHUB_TOKEN 需要 read:packages 权限"
    echo ""
fi

# ============================================================
# 拉取最新镜像
# ============================================================

echo "拉取最新镜像..."
echo ""

if ! docker compose -f docker-compose.prod.yml pull; then
    echo ""
    echo -e "${RED}镜像拉取失败${NC}"
    echo "可能原因: 1) 未登录 ghcr.io  2) 镜像不存在  3) 网络问题"
    exit 1
fi

echo ""
echo -e "${GREEN}镜像拉取成功${NC}"
echo ""

# ============================================================
# 部署
# ============================================================

# 检查是否首次部署
FIRST_DEPLOY=false
if ! docker compose -f docker-compose.prod.yml ps --services --filter "status=running" 2>/dev/null | grep -q .; then
    FIRST_DEPLOY=true
fi

if [ "$FIRST_DEPLOY" = true ]; then
    echo "首次部署，启动所有服务..."
    docker compose -f docker-compose.prod.yml up -d --wait
else
    echo "滚动更新..."
    # 逐个服务更新，确保零停机
    SERVICES=$(docker compose -f docker-compose.prod.yml config --services)
    for SERVICE in $SERVICES; do
        echo "  更新 $SERVICE ..."
        docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps "$SERVICE"

        # 等待健康检查
        echo -n "  等待健康检查"
        WAIT_TIME=0
        MAX_WAIT=90
        while [ $WAIT_TIME -lt $MAX_WAIT ]; do
            HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' \
                "$(docker compose -f docker-compose.prod.yml ps -q "$SERVICE" 2>/dev/null)" 2>/dev/null || echo "starting")
            if [ "$HEALTH" = "healthy" ] || [ "$HEALTH" = "running" ]; then
                echo ""
                echo -e "  ${GREEN}$SERVICE 更新完成${NC}"
                break
            fi
            echo -n "."
            sleep 2
            WAIT_TIME=$((WAIT_TIME + 2))
        done
        if [ $WAIT_TIME -ge $MAX_WAIT ]; then
            echo ""
            echo -e "  ${RED}$SERVICE 健康检查超时${NC}"
            docker compose -f docker-compose.prod.yml logs --tail=20 "$SERVICE"
        fi
    done

    # 清理孤立容器
    docker compose -f docker-compose.prod.yml up -d --remove-orphans
fi

echo ""

# ============================================================
# 清理旧镜像
# ============================================================

echo "清理未使用的镜像..."
docker image prune -f > /dev/null 2>&1 || true
echo ""

# ============================================================
# 最终状态
# ============================================================

echo "=========================================="
echo "服务状态"
echo "=========================================="
docker compose -f docker-compose.prod.yml ps
echo ""

echo -e "${GREEN}部署完成!${NC}"
echo ""

echo "常用命令:"
echo "  查看日志:   docker compose -f docker-compose.prod.yml logs -f"
echo "  查看状态:   docker compose -f docker-compose.prod.yml ps"
echo "  重启服务:   docker compose -f docker-compose.prod.yml restart"
echo "  停止服务:   docker compose -f docker-compose.prod.yml down"
echo ""
echo "访问地址:   http://localhost:${APP_PORT:-3000}"
echo ""
echo -e "${BLUE}下次更新只需运行: ./deploy.sh${NC}"
echo ""
```

---

### Template 6: `deploys/.env.example`

通过扫描项目自动生成环境变量模板。

**Generation process (生成流程):**
1. Read `nuxt.config.ts` / `next.config.*` for `runtimeConfig` / `env` references
2. Read existing `.env.example` or `.env.local.example` if present
3. Check `package.json` dependencies for known services (Clerk, Stripe, NextAuth, Prisma, etc.)
4. Group by category with Chinese+English comments

```bash
# ============================================================
# {{PROJECT_NAME}} - 生产环境配置模板
# ============================================================
# 使用说明:
#   1. 复制: cp .env.example .env
#   2. 编辑: 填写必填项
#   3. 部署: bash deploy.sh
# ============================================================

# ------------------------------------------------------------
# GitHub Container Registry (必填)
# ------------------------------------------------------------
# 格式: owner/repository
# 示例: duan/my-app
GITHUB_REPOSITORY=owner/repo

# ------------------------------------------------------------
# 应用配置
# ------------------------------------------------------------
# 应用名称
APP_NAME={{PROJECT_NAME}}

# 主机端口（映射到容器 3000 端口）
APP_PORT={{HOST_PORT}}

# 站点 URL（用于 SEO、sitemap 等）
# 示例: https://example.com
# NUXT_PUBLIC_SITE_URL=https://{{DOMAIN}}
# NEXT_PUBLIC_SITE_URL=https://{{DOMAIN}}

# ------------------------------------------------------------
# CDN 配置（可选）
# ------------------------------------------------------------
# CDN URL（留空则使用本地静态文件）
# 示例: https://static.example.com/my-app
# CDN_URL=

# ------------------------------------------------------------
# 数据库配置 (PostgreSQL) — 仅在启用数据库时包含
# ------------------------------------------------------------
# 数据库名称
POSTGRES_DB={{PROJECT_NAME}}

# 数据库用户名
POSTGRES_USER=postgres

# 数据库密码（必填: 请设置强密码！）
POSTGRES_PASSWORD=

# 数据库连接 URL（自动构建，无需修改）
# DATABASE_URL=postgresql://postgres:PASSWORD@postgres:5432/{{PROJECT_NAME}}

# ------------------------------------------------------------
# 以下根据项目扫描结果自动添加
# 检测到 Clerk → 添加 Clerk 配置
# 检测到 Stripe → 添加 Stripe 配置
# 检测到其他服务 → 添加对应配置
# ------------------------------------------------------------
# 示例 - Clerk 认证:
# CLERK_SECRET_KEY=sk_test_...
# NUXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
# CLERK_WEBHOOK_SECRET=whsec_...

# 示例 - Stripe 支付:
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_WEBHOOK_SECRET=whsec_...
# NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

**Adaptation notes:**
- 根据项目实际依赖填充环境变量（不要留示例注释，直接生成真实条目）
- Database section: only include if user chose PostgreSQL
- CDN section: only include if user provided CDN URL
- Service-specific sections: auto-detect from `package.json` dependencies
- All secret values should be left empty with `# 必填` or `# REQUIRED` comment
- Non-secret defaults should have sensible values pre-filled

---

### Template 7: `deploys/ENV.md`

环境变量文档，说明每个变量的用途、是否必填、默认值。

```markdown
# Environment Variables / 环境变量说明

## Required Variables / 必填变量

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_REPOSITORY` | GitHub 仓库路径 (owner/repo) | `user/my-app` |
| `POSTGRES_PASSWORD` | 数据库密码（使用强随机密码） | `aB3$xK9mP2qR` |

## Optional Variables / 可选变量

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | 应用名称 | `{{PROJECT_NAME}}` |
| `APP_PORT` | 主机端口 | `{{HOST_PORT}}` |
| `CDN_URL` | CDN 地址（留空使用本地） | _(empty)_ |
| `POSTGRES_DB` | 数据库名称 | `{{PROJECT_NAME}}` |
| `POSTGRES_USER` | 数据库用户名 | `postgres` |

## Security Notes / 安全说明

- **Never** commit `.env` to git
- Set `chmod 600 .env` on production server
- Use strong, random passwords for `POSTGRES_PASSWORD`
- Auth secrets (Clerk/NextAuth/etc.): obtain from respective dashboards
- ghcr.io access: `GITHUB_TOKEN` is automatic in CI; on VPS use `docker login ghcr.io`

## GitHub Actions Secrets

CI/CD 中需要配置的 Secrets（在 GitHub repo Settings → Secrets 中设置）：

| Secret | Required | Description |
|--------|----------|-------------|
| `GITHUB_TOKEN` | Auto | 内置 token，无需手动配置 |
| `R2_ACCESS_KEY_ID` | If CDN | Cloudflare R2 access key |
| `R2_SECRET_ACCESS_KEY` | If CDN | Cloudflare R2 secret key |
| `R2_BUCKET_NAME` | If CDN | R2 bucket name |
| `R2_ENDPOINT` | If CDN | R2 endpoint URL |

## VPS Deployment / 服务器部署

```bash
# 1. 克隆仓库
git clone https://github.com/OWNER/REPO.git
cd REPO/deploys

# 2. 创建配置文件
cp .env.example .env
chmod 600 .env

# 3. 编辑配置（填写必填项）
vim .env

# 4. 登录 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 5. 部署
bash deploy.sh
```

## Reverse Proxy / 反向代理

部署后需配置反向代理以支持 HTTPS。应用监听 `127.0.0.1:{{HOST_PORT}}`。

### Nginx 示例

```nginx
server {
    listen 443 ssl http2;
    server_name {{DOMAIN}};

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:{{HOST_PORT}};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Caddy 示例

```
{{DOMAIN}} {
    reverse_proxy 127.0.0.1:{{HOST_PORT}}
}
```
```

**Adaptation notes:**
- 根据项目实际变量填充 Required 和 Optional 表格
- If no database, remove database-related rows
- If no CDN, remove CDN-related GitHub Actions Secrets rows
- Add project-specific variables detected from scanning
- Include links to service dashboards (Clerk, Stripe, etc.) where applicable

---

## Step 4: Security Audit

生成文件后，执行以下安全检查。如发现问题，自动修复：

- [ ] `.env` and `.env.*` listed in `.dockerignore`
- [ ] `.env` and `.env.*` listed in `.gitignore` (add if missing)
- [ ] No hardcoded secrets in any generated file (all secrets use `${}` or are empty)
- [ ] Database port NOT exposed to host (only on internal Docker network)
- [ ] App port bound to `127.0.0.1` only (not `0.0.0.0`)
- [ ] Non-root user in Dockerfile (`USER appuser`)
- [ ] `GITHUB_TOKEN` used for ghcr.io authentication (no extra secrets needed for Docker push)
- [ ] Health checks configured for all services in Docker Compose
- [ ] `set -euo pipefail` in deploy.sh
- [ ] `.env` file permission set to `600` in deploy.sh flow

如果 `.gitignore` 中缺少 `.env`，自动添加：
```
# Environment files
.env
.env.*
!.env.example
```

---

## Step 5: Output Summary

生成完成后，告诉用户以下信息：

### 1. Generated Files / 已生成文件

```
Created:
  .github/workflows/deploy.yml    — CI/CD: push to main → build → push to ghcr.io
  Dockerfile                      — Production image (slim, non-root)
  .dockerignore                   — Docker build exclusions
  deploys/docker-compose.prod.yml — App + Database orchestration
  deploys/deploy.sh               — VPS one-command deployment
  deploys/.env.example            — Environment variable template
  deploys/ENV.md                  — Environment variable documentation
```

### 2. Configuration Required / 需要配置

提醒用户在 `deploys/.env` 中填写的关键变量（列出所有 `# REQUIRED` 标记的变量）。

### 3. GitHub Repository Setup / GitHub 仓库设置

- `packages:write` permission is automatic with `GITHUB_TOKEN` — no extra secrets needed for Docker push
- If CDN is configured, remind user to set R2 secrets in repo Settings → Secrets

### 4. VPS Deployment Steps / 服务器部署步骤

```bash
# On your VPS:
cd /path/to/project/deploys
cp .env.example .env
vim .env           # 填写必填项
bash deploy.sh     # 一键部署
```

### 5. Post-Deployment / 部署后

- Set up reverse proxy (Nginx/Caddy) for HTTPS → point to `127.0.0.1:{{HOST_PORT}}`
- (Optional) Set up monitoring / log aggregation
- (Optional) Configure automatic Docker image cleanup cron job

### 6. Next.js Reminder

If the project is Next.js, remind:
```
IMPORTANT: Ensure next.config has `output: 'standalone'` for the Docker deployment to work:

// next.config.ts
export default {
  output: 'standalone',
  // ...
}
```
