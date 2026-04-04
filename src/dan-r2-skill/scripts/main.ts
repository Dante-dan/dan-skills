import minimist from "minimist";
import { resolve } from "path";
import { existsSync, mkdirSync, writeFileSync, unlinkSync, readFileSync } from "fs";
import { dirname } from "path";
import { loadConfig, validateConfig, resolveGlobs, getConfigPath } from "./config.js";
import { scanFiles } from "./scanner.js";
import { uploadFiles } from "./uploader.js";
import { replaceInMarkdown } from "./replacer.js";

const HELP = `
dan-r2-skill — Upload files to Cloudflare R2

Usage:
  npx -y bun <script>/main.ts [options]

Options:
  --dir <path>        Upload directory (default: current directory)
  --content <type>    images | docs | all (default: from config or "images")
  --glob <pattern>    Custom glob pattern (overrides --content)
  --dry-run           Preview what would be uploaded
  --clean             Delete local files after successful upload
  --no-replace        Skip markdown path replacement
  --init              Create/update config file
  --init-level <lvl>  "user" or "project" (default: "user")
  --help              Show this help
`.trim();

function printHelp() {
  console.log(HELP);
  process.exit(0);
}

async function initConfig(level: "user" | "project", cwd: string) {
  const configPath = getConfigPath(level, cwd);
  const dir = dirname(configPath);

  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  // Read existing config to show current values
  let existing: any = {};
  if (existsSync(configPath)) {
    try {
      existing = JSON.parse(readFileSync(configPath, "utf-8"));
    } catch {}
  }

  const template = {
    r2: {
      accountId: existing?.r2?.accountId || "",
      accessKeyId: existing?.r2?.accessKeyId || "",
      secretAccessKey: existing?.r2?.secretAccessKey || "",
      bucket: existing?.r2?.bucket || "",
      endpoint: existing?.r2?.endpoint || "",
      publicDomain: existing?.r2?.publicDomain || "",
    },
    upload: {
      pathPrefix: existing?.upload?.pathPrefix || "blog/{date}",
      content: existing?.upload?.content || "images",
      customGlob: existing?.upload?.customGlob || null,
      replace: existing?.upload?.replace ?? true,
      clean: existing?.upload?.clean ?? false,
    },
  };

  writeFileSync(configPath, JSON.stringify(template, null, 2) + "\n", "utf-8");
  console.log(`Config ${existsSync(configPath) ? "updated" : "created"} at: ${configPath}`);
  console.log("Please edit the config file to fill in your R2 credentials.");
}

async function main() {
  const args = minimist(process.argv.slice(2), {
    boolean: ["dry-run", "clean", "help", "init", "replace"],
    string: ["dir", "content", "glob", "init-level"],
    default: { replace: true },
    alias: { h: "help" },
  });

  if (args.help) printHelp();

  const cwd = args.dir ? resolve(args.dir) : process.cwd();

  // --init mode
  if (args.init) {
    const level = (args["init-level"] === "project" ? "project" : "user") as "user" | "project";
    await initConfig(level, cwd);
    return;
  }

  // Load merged config
  const config = loadConfig(cwd);

  // Apply CLI overrides
  if (args.content) {
    config.upload = config.upload || {};
    config.upload.content = args.content;
  }
  if (args.glob) {
    config.upload = config.upload || {};
    config.upload.customGlob = args.glob;
  }
  if (args.clean) {
    config.upload = config.upload || {};
    config.upload.clean = true;
  }
  if (args.replace === false) {
    config.upload = config.upload || {};
    config.upload.replace = false;
  }

  const dryRun = !!args["dry-run"];

  // Validate
  const errors = validateConfig(config);
  if (errors.length > 0) {
    console.error("Config errors:");
    errors.forEach((e) => console.error(`  - ${e}`));
    console.error(`\nRun with --init to create a config file.`);
    process.exit(1);
  }

  // Scan
  const globs = resolveGlobs(config);
  console.log(`Scanning ${cwd} with patterns: ${globs.join(", ")}`);
  const files = scanFiles(cwd, globs);

  if (files.length === 0) {
    console.log("No files found matching the patterns.");
    return;
  }

  console.log(`Found ${files.length} file(s)${dryRun ? " (dry-run)" : ""}:\n`);

  // Upload
  const pathPrefix = config.upload?.pathPrefix || "blog/{date}";
  const results = await uploadFiles(files, config.r2!, pathPrefix, dryRun);

  const uploaded = results.filter((r) => !r.skipped);
  const failed = results.filter((r) => r.skipped);

  // Replace in markdown
  const doReplace = config.upload?.replace !== false;
  if (doReplace && uploaded.length > 0) {
    console.log("\n--- Markdown replacement ---");
    replaceInMarkdown(cwd, results, dryRun);
  }

  // Clean local files
  if (config.upload?.clean && !dryRun) {
    console.log("\n--- Cleaning local files ---");
    for (const result of uploaded) {
      try {
        unlinkSync(result.file.absolutePath);
        console.log(`[deleted] ${result.file.relativePath}`);
      } catch (err: any) {
        console.error(`[error] Could not delete ${result.file.relativePath}: ${err.message}`);
      }
    }
  }

  // Summary
  console.log(`\n--- Summary ---`);
  console.log(`Total: ${files.length} | Uploaded: ${uploaded.length} | Failed: ${failed.length}`);
  if (dryRun) console.log("(dry-run mode — no changes made)");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
