import { globSync } from "glob";
import { statSync, existsSync } from "fs";
import { resolve } from "path";
import { platform } from "os";
import { execSync } from "child_process";

export interface ScannedFile {
  absolutePath: string;
  relativePath: string;
  createdDate: string; // YYYY-MM-DD
  fileName: string;
}

/**
 * Get file creation date (birthtime).
 * On macOS, use stat -f %SB for reliable birthtime.
 * Falls back to mtime if birthtime unavailable.
 */
function getFileCreatedDate(filePath: string): string {
  try {
    if (platform() === "darwin") {
      const output = execSync(
        `stat -f '%SB' -t '%Y-%m-%d' "${filePath}"`,
        { encoding: "utf-8" }
      ).trim();
      if (/^\d{4}-\d{2}-\d{2}$/.test(output)) return output;
    }
  } catch {
    // fall through
  }

  const stat = statSync(filePath);
  const date = stat.birthtime.getTime() > 0 ? stat.birthtime : stat.mtime;
  return date.toISOString().slice(0, 10);
}

export function scanFiles(dir: string, globs: string[]): ScannedFile[] {
  const absDir = resolve(dir);
  if (!existsSync(absDir)) {
    throw new Error(`Directory not found: ${absDir}`);
  }

  const files: ScannedFile[] = [];
  const seen = new Set<string>();

  for (const pattern of globs) {
    const matches = globSync(pattern, {
      cwd: absDir,
      nodir: true,
      dot: false,
      ignore: ["**/node_modules/**", "**/.git/**", "**/.dan/**"],
    });
    for (const rel of matches) {
      if (seen.has(rel)) continue;
      seen.add(rel);
      const abs = resolve(absDir, rel);
      const fileName = rel.split("/").pop()!;
      files.push({
        absolutePath: abs,
        relativePath: rel,
        createdDate: getFileCreatedDate(abs),
        fileName,
      });
    }
  }

  return files.sort((a, b) => a.relativePath.localeCompare(b.relativePath));
}

export function scanSpecificFiles(dir: string, relativePaths: string[]): ScannedFile[] {
  const absDir = resolve(dir);
  const files: ScannedFile[] = [];

  for (const rel of relativePaths) {
    const abs = resolve(absDir, rel);
    if (!existsSync(abs)) {
      console.warn(`[warn] File not found: ${rel}`);
      continue;
    }
    const fileName = rel.split("/").pop()!;
    files.push({
      absolutePath: abs,
      relativePath: rel,
      createdDate: getFileCreatedDate(abs),
      fileName,
    });
  }

  return files;
}
