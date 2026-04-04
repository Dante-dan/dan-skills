import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { readFileSync } from "fs";
import type { R2Config } from "./config.js";
import type { ScannedFile } from "./scanner.js";

export interface UploadResult {
  file: ScannedFile;
  r2Key: string;
  publicUrl: string;
  skipped: boolean;
  error?: string;
}

function getContentType(fileName: string): string {
  const ext = fileName.split(".").pop()?.toLowerCase();
  const types: Record<string, string> = {
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    gif: "image/gif",
    webp: "image/webp",
    svg: "image/svg+xml",
    pdf: "application/pdf",
    doc: "application/msword",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    xls: "application/vnd.ms-excel",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ppt: "application/vnd.ms-powerpoint",
    pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  };
  return types[ext || ""] || "application/octet-stream";
}

function buildR2Key(file: ScannedFile, pathPrefix: string): string {
  const prefix = pathPrefix.replace("{date}", file.createdDate);
  const cleanPrefix = prefix.replace(/\/+/g, "/").replace(/\/$/, "");
  return `${cleanPrefix}/${file.fileName}`;
}

function createS3Client(r2Config: R2Config): S3Client {
  const endpoint = r2Config.endpoint || `https://${r2Config.accountId}.r2.cloudflarestorage.com`;
  return new S3Client({
    region: "auto",
    endpoint,
    credentials: {
      accessKeyId: r2Config.accessKeyId!,
      secretAccessKey: r2Config.secretAccessKey!,
    },
  });
}

export async function uploadFiles(
  files: ScannedFile[],
  r2Config: R2Config,
  pathPrefix: string,
  dryRun: boolean
): Promise<UploadResult[]> {
  const client = createS3Client(r2Config);
  const bucket = r2Config.bucket!;
  const domain = r2Config.publicDomain!.replace(/\/$/, "");
  const results: UploadResult[] = [];

  for (const file of files) {
    const r2Key = buildR2Key(file, pathPrefix);
    const publicUrl = `${domain}/${r2Key}`;

    if (dryRun) {
      results.push({ file, r2Key, publicUrl, skipped: false });
      console.log(`[dry-run] ${file.relativePath} → ${publicUrl}`);
      continue;
    }

    try {
      const body = readFileSync(file.absolutePath);
      await client.send(
        new PutObjectCommand({
          Bucket: bucket,
          Key: r2Key,
          Body: body,
          ContentType: getContentType(file.fileName),
        })
      );
      console.log(`[uploaded] ${file.relativePath} → ${publicUrl}`);
      results.push({ file, r2Key, publicUrl, skipped: false });
    } catch (err: any) {
      console.error(`[error] ${file.relativePath}: ${err.message}`);
      results.push({ file, r2Key, publicUrl, skipped: true, error: err.message });
    }
  }

  client.destroy();
  return results;
}
