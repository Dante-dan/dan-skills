#!/usr/bin/env bun

/**
 * dan-blog-sync: Publish a post to dhpie.com blog via API
 *
 * Usage:
 *   bun run blog-publish.ts --payload '<json>'
 *   bun run blog-publish.ts --payload-file <path>
 *
 * The payload JSON should contain all fields ready to send to the API.
 * Auth token is read from DHPIE_TOKEN env var or .env file.
 */

import { readFileSync, existsSync } from "fs";
import { dirname, resolve } from "path";

const API_BASE = "https://api.dhpie.com/api/v3";

function getToken(): string {
  const envToken = process.env.DHPIE_TOKEN;
  if (envToken) return envToken;

  const scriptDir = dirname(decodeURIComponent(new URL(import.meta.url).pathname));
  const envFile = resolve(scriptDir, "../.env");
  if (existsSync(envFile)) {
    const content = readFileSync(envFile, "utf-8");
    const match = content.match(/^DHPIE_TOKEN=(.+)$/m);
    if (match) return match[1].trim();
  }

  throw new Error(
    "DHPIE_TOKEN not found. Set via environment or ~/.claude/skills/dan-blog-sync/.env"
  );
}

async function checkAuth(token: string): Promise<boolean> {
  // v3: public endpoints return 200 even as guest, so we must inspect the
  // check_logged body — data.ok === 1 only with valid admin credentials.
  try {
    const res = await fetch(`${API_BASE}/owner/check_logged`, {
      headers: {
        "x-api-key": token,
        Accept: "application/json",
      },
    });
    if (!res.ok) return false;
    const json = (await res.json()) as { data?: { ok?: number } };
    return json?.data?.ok === 1;
  } catch {
    return false;
  }
}

async function checkSlugExists(slug: string, token: string): Promise<boolean> {
  // v3 removed /slugs/:slug; get-url/:slug returns 200 if the slug is taken,
  // 404 (POST_NOT_FOUND) if it is available.
  try {
    const res = await fetch(
      `${API_BASE}/posts/get-url/${encodeURIComponent(slug)}`,
      {
        headers: {
          "x-api-key": token,
          Accept: "application/json",
        },
      }
    );
    return res.ok;
  } catch {
    return false;
  }
}

async function createPost(
  payload: Record<string, unknown>,
  token: string
): Promise<{ ok: boolean; status: number; data: unknown }> {
  const res = await fetch(`${API_BASE}/posts`, {
    method: "POST",
    headers: {
      "x-api-key": token,
      Accept: "application/json",
      "Content-Type": "application/json;charset=UTF-8",
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => res.text());
  return { ok: res.ok, status: res.status, data };
}

async function main() {
  const args = process.argv.slice(2);

  // Parse args
  let payloadStr: string | undefined;

  const payloadIdx = args.indexOf("--payload");
  const fileIdx = args.indexOf("--payload-file");

  if (payloadIdx !== -1 && args[payloadIdx + 1]) {
    payloadStr = args[payloadIdx + 1];
  } else if (fileIdx !== -1 && args[fileIdx + 1]) {
    const filePath = args[fileIdx + 1];
    if (!existsSync(filePath)) {
      console.error(`Payload file not found: ${filePath}`);
      process.exit(1);
    }
    payloadStr = readFileSync(filePath, "utf-8");
  }

  // Special command: --check-auth
  if (args.includes("--check-auth")) {
    const token = getToken();
    const valid = await checkAuth(token);
    if (valid) {
      console.log("AUTH_OK");
    } else {
      console.log("AUTH_EXPIRED");
    }
    process.exit(valid ? 0 : 1);
  }

  // Special command: --check-slug <slug>
  const slugIdx = args.indexOf("--check-slug");
  if (slugIdx !== -1 && args[slugIdx + 1]) {
    const token = getToken();
    const exists = await checkSlugExists(args[slugIdx + 1], token);
    console.log(exists ? "SLUG_EXISTS" : "SLUG_AVAILABLE");
    process.exit(exists ? 1 : 0);
  }

  if (!payloadStr) {
    console.error("Usage:");
    console.error("  bun run blog-publish.ts --payload '<json>'");
    console.error("  bun run blog-publish.ts --payload-file <path>");
    console.error("  bun run blog-publish.ts --check-auth");
    console.error("  bun run blog-publish.ts --check-slug <slug>");
    process.exit(1);
  }

  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(payloadStr);
  } catch (e) {
    console.error("Invalid JSON payload");
    process.exit(1);
  }

  const token = getToken();

  // Check auth first
  const authValid = await checkAuth(token);
  if (!authValid) {
    console.error("TOKEN_EXPIRED: Authorization token is expired or invalid. Please update DHPIE_TOKEN.");
    process.exit(2);
  }

  // Publish
  const result = await createPost(payload, token);

  if (!result.ok) {
    console.error(`API_ERROR ${result.status}:`);
    console.error(JSON.stringify(result.data, null, 2));
    process.exit(1);
  }

  console.log("PUBLISHED");
  console.log(JSON.stringify(result.data, null, 2));
}

main().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
