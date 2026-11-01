import { readFile, stat, access } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, "../public");
const manifest = JSON.parse(
  await readFile(resolve(root, "media/manifest.json"), "utf8"),
);
if (manifest.chapters.length !== 15)
  throw Error("Expected fifteen completed course chapters");
let bytes = 0;
for (const m of manifest.chapters) {
  const file = resolve(root, m.video);
  const data = await readFile(file);
  const digest = createHash("sha256").update(data).digest("hex");
  if (digest !== m.sha256 || data.length !== m.bytes)
    throw Error(`Video checksum mismatch: ${m.id}`);
  const ftyp = data.indexOf("ftyp"),
    moov = data.indexOf("moov"),
    mdat = data.indexOf("mdat");
  if (ftyp < 0 || moov < 0 || mdat < 0)
    throw Error(`Invalid MP4 container: ${m.id}`);
  await access(resolve(root, m.cover));
  const article = await readFile(resolve(root, m.article), "utf8");
  if (!article.startsWith("# ") || !article.includes("## "))
    throw Error(`Missing structured article: ${m.id}`);
  for (const match of article.matchAll(/!\[[^\]]*\]\(([^)]+)\)/g)) {
    await access(resolve(root, "articles", match[1]));
  }
  bytes += data.length;
  console.log(
    `${m.id}: article, cover, figures and video SHA-256 verified (${m.durationSeconds.toFixed(1)}s)`,
  );
}
console.log(
  `All ${manifest.chapters.length} chapters verified, ${(bytes / 1024 / 1024).toFixed(1)} MiB of full videos.`,
);

if (manifest.introduction) {
  const intro = manifest.introduction;
  const data = await readFile(resolve(root, intro.video));
  if (createHash("sha256").update(data).digest("hex") !== intro.sha256)
    throw Error("Introduction checksum mismatch");
  await access(resolve(root, intro.poster));
  console.log("Introduction video and poster verified.");
}
