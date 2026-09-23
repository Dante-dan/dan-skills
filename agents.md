# Repository Agent Instructions

每当仓库新增 skill 或 plugin，都要在 `~/.claude/skills`、`~/.codex/skills` 和 `~/.agents/skills` 中为仓库内对应的 skill 建立指向当前仓库源目录的软链，并检查和补齐已有但遗漏的软链。若目标名称已存在，先确认目标指向；只替换失效或指向旧位置的仓库 skill 链接，不覆盖其他来源的文件或目录。Plugin 本身按各工具支持的发现方式登记；至少确保其包含的 skills 在上述目录可用。
