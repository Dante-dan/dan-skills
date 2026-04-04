import { readFileSync, writeFileSync } from "fs";
import { globSync } from "glob";
import { resolve } from "path";
import type { UploadResult } from "./uploader.js";

export interface ReplaceResult {
  file: string;
  replacements: number;
}

/**
 * Scan markdown files in `dir` and replace local image/file references
 * with their R2 public URLs based on upload results.
 */
export function replaceInMarkdown(
  dir: string,
  uploadResults: UploadResult[],
  dryRun: boolean
): ReplaceResult[] {
  // Build a map: relativePath -> publicUrl
  const urlMap = new Map<string, string>();
  for (const result of uploadResults) {
    if (!result.skipped) {
      urlMap.set(result.file.relativePath, result.publicUrl);
      // Also map just the filename for flat references like ![](image.png)
      urlMap.set(result.file.fileName, result.publicUrl);
    }
  }

  if (urlMap.size === 0) return [];

  const mdFiles = globSync("**/*.md", {
    cwd: resolve(dir),
    nodir: true,
    ignore: ["**/node_modules/**", "**/.git/**"],
  });

  const results: ReplaceResult[] = [];

  for (const mdRel of mdFiles) {
    const mdPath = resolve(dir, mdRel);
    let content = readFileSync(mdPath, "utf-8");
    let count = 0;

    // Match markdown image/link syntax: ![alt](path) and [text](path)
    // Also match raw HTML <img src="path">
    const replacedContent = content.replace(
      /(!\[[^\]]*\]\()([^)]+)(\))|(<img\s[^>]*src=["'])([^"']+)(["'][^>]*>)/g,
      (match, mdPre, mdPath, mdPost, htmlPre, htmlPath, htmlPost) => {
        if (mdPre) {
          // Markdown syntax: ![alt](path)
          const localPath = decodeURIComponent(mdPath).replace(/^\.\//, "");
          const url = urlMap.get(localPath);
          if (url) {
            count++;
            return `${mdPre}${url}${mdPost}`;
          }
        } else if (htmlPre) {
          // HTML syntax: <img src="path">
          const localPath = decodeURIComponent(htmlPath).replace(/^\.\//, "");
          const url = urlMap.get(localPath);
          if (url) {
            count++;
            return `${htmlPre}${url}${htmlPost}`;
          }
        }
        return match;
      }
    );

    if (count > 0) {
      if (!dryRun) {
        writeFileSync(mdPath, replacedContent, "utf-8");
      }
      console.log(`[${dryRun ? "dry-run" : "replaced"}] ${mdRel}: ${count} reference(s)`);
      results.push({ file: mdRel, replacements: count });
    }
  }

  return results;
}
