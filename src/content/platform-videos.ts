/** Public work pages verified against title and author; never media-CDN URLs. */
export type VideoPlatform = 'xigua' | 'douyin' | 'toutiao';
export interface PlatformVideo {
  platform: VideoPlatform;
  url: string;
  verifiedAt: string;
}
export const platformLabels: Record<VideoPlatform, string> = { xigua: '西瓜视频', douyin: '抖音', toutiao: '头条' };
export const platformVideos: Record<string, readonly PlatformVideo[]> = {
  '15': [{ platform: 'toutiao', url: 'https://www.toutiao.com/video/7700272491863851547/', verifiedAt: '2026-10-25' }],
  '16': [{ platform: 'toutiao', url: 'https://www.toutiao.com/video/7700408520349237796/', verifiedAt: '2026-10-25' }],
  '17': [{ platform: 'toutiao', url: 'https://www.toutiao.com/video/7700442833659937295/', verifiedAt: '2026-10-25' }],
};
export function validatePlatformVideo(video: PlatformVideo): void {
  const u = new URL(video.url);
  const hosts: Record<VideoPlatform, string> = { xigua: 'www.ixigua.com', douyin: 'www.douyin.com', toutiao: 'www.toutiao.com' };
  const pattern = video.platform === 'xigua' ? /^\/\d+\/?$/ : /^\/video\/\d+\/?$/;
  if (u.protocol !== 'https:' || u.hostname !== hosts[video.platform] || u.username || u.password || u.port || !pattern.test(u.pathname) || u.hash)
    throw new Error(`Invalid official work page: ${video.platform}`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(video.verifiedAt)) throw new Error('Missing platform verification date');
}
for (const [id, videos] of Object.entries(platformVideos)) {
  if (!/^\d{2}$/.test(id) || new Set(videos.map(v => v.platform)).size !== videos.length) throw new Error(`Invalid platform mapping: ${id}`);
  videos.forEach(validatePlatformVideo);
}
export const videosForLesson = (id: string): readonly PlatformVideo[] => platformVideos[id] ?? [];
