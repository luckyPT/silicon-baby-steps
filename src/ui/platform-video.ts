import { videosForLesson, platformLabels } from '../content/platform-videos.ts';
const escapeAttribute = (value: string) => value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
/** Normal links only: no third-party player, script or cookies loaded on visit. */
export function renderPlatformVideoSection(id: string): string {
  const videos = videosForLesson(id);
  if (!videos.length) return `<section class="callout video-pending" aria-label="视频状态"><b>本节视频待补 · 讲义与实验已开放</b><p>当前尚无已核实的公开作品链接。先阅读讲义、运行实验；确认视频发布后会在这里补充观看入口。</p><a class="button primary" href="#/lesson/${id}/lab">先运行本节实验 ↗</a></section>`;
  return `<section class="callout platform-video" aria-label="本节平台视频"><span class="eyebrow">WATCH ON THE OFFICIAL PLATFORM</span><h2>本节视频已发布</h2><p>前往已核实的官方作品页观看完整视频。本站暂不托管本节 MP4；平台可能要求登录或打开 App，播放条件以平台为准。</p><div class="platform-video-actions">${videos.map(video => `<a class="button primary" href="${escapeAttribute(video.url)}" target="_blank" rel="noopener noreferrer" aria-label="在${platformLabels[video.platform]}观看第${Number(id)}集（新窗口）">${platformLabels[video.platform]}观看 ↗</a>`).join('')}<a class="button quiet" href="#/lesson/${id}/lab">运行本节实验 →</a></div><p class="platform-video-note">链接指向公开作品页，不是原片下载地址。当前未接入站内播放器，不会在打开本页时自动加载第三方视频。</p></section>`;
}
