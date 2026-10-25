import { readFile, access } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { lessons } from "../src/content/catalog.ts";
import { platformVideos, videosForLesson } from "../src/content/platform-videos.ts";
const root = resolve(import.meta.dirname, "../public");
const manifest = JSON.parse(await readFile(resolve(root, "media/manifest.json"), "utf8"));
const ids = manifest.chapters.map(m => m.id);
if (new Set(ids).size !== ids.length || JSON.stringify(ids) !== JSON.stringify(lessons.map(l => l.id)))
  throw Error("Media manifest must match the course catalog exactly");
for (const id of Object.keys(platformVideos)) if (!ids.includes(id)) throw Error(`Platform links reference unknown lesson: ${id}`);
let bytes = 0, ready = 0, pending = 0;
for (const m of manifest.chapters) {
  const lesson = lessons.find(l => l.id === m.id);
  await access(resolve(root, m.cover));
  const article = await readFile(resolve(root, m.article), "utf8");
  if (!article.startsWith("# ") || !article.includes("## ")) throw Error(`Missing structured article: ${m.id}`);
  for (const match of article.matchAll(/!\[[^\]]*\]\(([^)]+)\)/g)) {
    await access(resolve(root, "articles", match[1]));
  }
  if (m.videoStatus === "pending") {
    // Staging must never silently remove a previously published full video.
    if (Number(m.id) <= 14 || lesson.videoStatus !== "pending" || m.video !== null)
      throw Error(`Invalid pending-video declaration: ${m.id}`);
    pending++;
    console.log(`${m.id}: article, cover and figures verified; local MP4 pending; ${videosForLesson(m.id).length} verified official platform link(s)`);
    continue;
  }
  if (lesson.videoStatus === "pending") throw Error(`Catalog/media readiness mismatch: ${m.id}`);
  const data = await readFile(resolve(root, m.video));
  const digest = createHash("sha256").update(data).digest("hex");
  if (digest !== m.sha256 || data.length !== m.bytes) throw Error(`Video checksum mismatch: ${m.id}`);
  if (!["ftyp", "moov", "mdat"].every(atom => data.includes(atom))) throw Error(`Invalid MP4 container: ${m.id}`);
  bytes += data.length; ready++;
  console.log(`${m.id}: article, cover, figures and video SHA-256 verified (${m.durationSeconds.toFixed(1)}s)`);
}
console.log(`${manifest.chapters.length} lecture chapters verified; ${ready} full videos (${(bytes / 1024 / 1024).toFixed(1)} MiB), ${pending} local MP4s explicitly pending.`);
if (manifest.introduction) {
  const intro = manifest.introduction;
  const data = await readFile(resolve(root, intro.video));
  if (createHash("sha256").update(data).digest("hex") !== intro.sha256) throw Error("Introduction checksum mismatch");
  await access(resolve(root, intro.poster));
  console.log("Introduction video and poster verified.");
}
