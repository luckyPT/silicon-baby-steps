/** Public work pages verified against title and author; never media-CDN URLs. */
export type VideoPlatform = 'xigua' | 'douyin' | 'toutiao';
export interface PlatformVideo {
  platform: VideoPlatform;
  url: string;
  verifiedAt: string;
}
export const platformLabels: Record<VideoPlatform, string> = { xigua: '西瓜视频', douyin: '抖音', toutiao: '头条' };
import platformLinks from './platform-links.json' with { type: 'json' };
export const platformVideos = platformLinks as Record<string, readonly PlatformVideo[]>;
export function validatePlatformVideo(video: PlatformVideo): void {
  const u = new URL(video.url);
  const hosts: Record<VideoPlatform, string> = { xigua: 'www.ixigua.com', douyin: 'www.douyin.com', toutiao: 'www.toutiao.com' };
  const pattern = video.platform === 'xigua' ? /^\/\d+\/?$/ : video.platform === 'toutiao' ? /^(?:\/video\/\d+\/?|\/i\d+)$/ : /^\/video\/\d+\/?$/;
  if (u.protocol !== 'https:' || u.hostname !== hosts[video.platform] || u.username || u.password || u.port || !pattern.test(u.pathname) || u.hash)
    throw new Error(`Invalid official work page: ${video.platform}`);
  if ([...u.searchParams].some(([k,v])=>k!=='enter_from'||v!=='mp_group_management')) throw new Error('Unexpected work-page query');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(video.verifiedAt)) throw new Error('Missing platform verification date');
}
for (const [id, videos] of Object.entries(platformVideos)) {
  if (!/^\d{2}$/.test(id) || new Set(videos.map(v => v.platform)).size !== videos.length) throw new Error(`Invalid platform mapping: ${id}`);
  videos.forEach(validatePlatformVideo);
}
export const videosForLesson = (id: string): readonly PlatformVideo[] => platformVideos[id] ?? [];

import pendingLinks from './platform-pending.json' with { type: 'json' };
interface PendingPlatform {platform:VideoPlatform;status:'under_review'|'not_submitted';}
export const pendingPlatforms = pendingLinks as Record<string, readonly PendingPlatform[]>;
export const pendingForLesson = (id: string): readonly VideoPlatform[] => (pendingPlatforms[id]??[]).map(p=>p.platform);
export const pendingMessage = (id:string):string => (pendingPlatforms[id]??[]).map(p=>platformLabels[p.platform]+'：'+(p.status==='under_review'?'审核中':'待发布')).join('；');
for(const [id,states] of Object.entries(pendingPlatforms)){
 const platforms=states.map(p=>p.platform);
 if(!/^\d{2}$/.test(id)||new Set(platforms).size!==platforms.length||platforms.some(p=>!['toutiao','douyin'].includes(p)||videosForLesson(id).some(v=>v.platform===p))||states.some(s=>!['under_review','not_submitted'].includes(s.status)))throw Error('Invalid pending platform state');
}
