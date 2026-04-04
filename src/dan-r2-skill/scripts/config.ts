import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";

export interface R2Config {
  accountId?: string;
  accessKeyId?: string;
  secretAccessKey?: string;
  bucket?: string;
  endpoint?: string;
  publicDomain?: string;
}

export interface UploadConfig {
  pathPrefix?: string;
  content?: "images" | "docs" | "all";
  customGlob?: string | null;
  replace?: boolean;
  clean?: boolean;
}

export interface DanConfig {
  r2?: R2Config;
  upload?: UploadConfig;
}

const USER_CONFIG_PATH = join(homedir(), ".dan", "config.json");

function getProjectConfigPath(cwd: string): string {
  return join(cwd, ".dan", "config.json");
}

function loadJsonFile(path: string): Partial<DanConfig> {
  if (!existsSync(path)) return {};
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch {
    console.error(`Warning: Failed to parse config at ${path}`);
    return {};
  }
}

function deepMerge(base: any, override: any): any {
  const result = { ...base };
  for (const key of Object.keys(override)) {
    if (
      override[key] !== null &&
      typeof override[key] === "object" &&
      !Array.isArray(override[key]) &&
      typeof base[key] === "object"
    ) {
      result[key] = deepMerge(base[key], override[key]);
    } else {
      result[key] = override[key];
    }
  }
  return result;
}

export function loadConfig(cwd: string): DanConfig {
  const userConfig = loadJsonFile(USER_CONFIG_PATH);
  const projectConfig = loadJsonFile(getProjectConfigPath(cwd));
  return deepMerge(userConfig, projectConfig);
}

export function getConfigPath(level: "user" | "project", cwd: string): string {
  return level === "user" ? USER_CONFIG_PATH : getProjectConfigPath(cwd);
}

const CONTENT_GLOBS: Record<string, string[]> = {
  images: ["**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.webp", "**/*.gif", "**/*.svg"],
  docs: ["**/*.pdf", "**/*.doc", "**/*.docx", "**/*.xls", "**/*.xlsx", "**/*.ppt", "**/*.pptx"],
  all: ["**/*.*"],
};

export function resolveGlobs(config: DanConfig): string[] {
  if (config.upload?.customGlob) {
    return [config.upload.customGlob];
  }
  const content = config.upload?.content || "images";
  return CONTENT_GLOBS[content] || CONTENT_GLOBS.images;
}

export function validateConfig(config: DanConfig): string[] {
  const errors: string[] = [];
  if (!config.r2?.accountId) errors.push("r2.accountId is required");
  if (!config.r2?.accessKeyId) errors.push("r2.accessKeyId is required");
  if (!config.r2?.secretAccessKey) errors.push("r2.secretAccessKey is required");
  if (!config.r2?.bucket) errors.push("r2.bucket is required");
  if (!config.r2?.publicDomain) errors.push("r2.publicDomain is required");
  return errors;
}
