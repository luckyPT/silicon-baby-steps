import { mountTemporalLab } from './temporal-lab.ts';
import { asset, type Lesson } from '../content/catalog.ts';
type Point = [number, number];
interface View {
  label: string; path: Point[]; comparison?: Point[]; bounds: [number,number,number,number];
  metrics: Record<string,number|boolean|null>; points?: Point[]; tree?: [Point,Point][];
  circles?: [number,number,number][]; boxes?: [number,number,number,number][]; robotHalfwidth?: number;
  grid?: {width:number;height:number;blocked:Point[];soft:{cell:Point;cost:number}[];start:Point;goal:Point};
}
interface RecordData {episode:number;mode:string;scope:string;views:View[]}
const esc = (s:unknown) => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const names:Record<string,string>={cost:'路线代价',length:'长度 / m',oracle:'同图最优 / m',oracle_cost:'同图最优代价',expansions:'有效扩展',astar_expansions:'重跑A*扩展',checks:'边检碰',clearance:'净距 / m',curve_clearance:'曲线净距 / m',segment_clearance:'整段净距 / m',knot_clearance:'节点净距 / m',energy:'平滑目标',epsilon:'ε',queue:'待处理节点',nodes:'保留节点',pops:'有效出队',scans:'邻接扫描',rewires:'重连',edge_checks:'边检查',orphans:'撤销后代',stale:'过期堆项',lower_bound:'松弛下界 / m',rounded_length:'舍入路线 / m',relative_bound_gap:'相对上下界差',continuity_residual:'交接残差',reverse_edge_visits:'反向邻接访问',invalid_count:'发现无效边',restarts:'重启搜索',km:'km',lazy_key_updates:'关键字重入队',predecessor_scans:'前驱扫描',neighbor_scans:'后继扫描',cumulative_expansions:'累计扩展',completed:'轮次完成',success:'返回路线'};
const value = (v:unknown) => v===null?'无路径 / ∞':typeof v==='boolean'?(v?'是':'否'):typeof v==='number'?(Number.isInteger(v)?String(v):Math.abs(v)<1e-5?v.toExponential(3):v.toFixed(6)):esc(v);
/** A recorded experiment viewer, deliberately not presented as a live solver. */
export function mountRecordedLab(root:HTMLElement, lesson:Lesson):()=>void {
 if(lesson.id==='27')return mountTemporalLab(root);
 let disposed=false, timer:ReturnType<typeof setInterval>|undefined, index=0;
 const stop=()=>{if(timer)clearInterval(timer);timer=undefined;};
 root.innerHTML='<p>正在读取原始实验记录…</p>';
 void fetch(asset(`experiments/${lesson.id}.json`)).then(r=>{if(!r.ok)throw Error('实验记录暂未加载');return r.json() as Promise<RecordData>;}).then(data=>{
  if(disposed)return;
  root.innerHTML=`<section class="callout"><span class="eyebrow">RECORDED EXPERIMENT / ${lesson.id}</span><h2>真实实验回放与对比</h2><p>${esc(data.scope)}</p><p><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/experiments/original/${lesson.id}" target="_blank" rel="noopener noreferrer">打开可运行Python实验与依赖 ↗</a> · <a href="#/lesson/${lesson.id}">返回公式与讲义 →</a></p></section><section class="record-controls"><label>实验阶段 <select aria-label="实验阶段" id="record-phase">${data.views.map((v,i)=>`<option value="${i}">${esc(v.label)}</option>`).join('')}</select></label><button class="button" id="record-play">自动切换阶段</button><button class="button" id="record-reset">回到第一阶段</button></section><section class="record-plot"><div id="record-geometry"></div><p>青色：本阶段路线；金色虚线：对照路线。红色：障碍；淡红外圈：方形机器人膨胀边界（第26集）。没有路线时保留空结果。</p></section><div id="record-metrics" class="record-metrics"></div><section class="record-comparison"><h2>同章实验账本</h2><p>各行保留自己的图版本、种子和预算。指标名称与单位分开报告，不据此排列算法速度。</p><div class="record-table"><table><thead><tr><th>阶段</th><th>主要代价 / 长度</th><th>扩展 / 出队</th><th>检碰 / 邻接扫描</th></tr></thead><tbody>${data.views.map((v,i)=>`<tr><td><button class="text-link" data-phase="${i}">${esc(v.label)}</button></td><td>${value(v.metrics.cost??v.metrics.length??v.metrics.rounded_length??null)}</td><td>${value(v.metrics.expansions??v.metrics.pops??v.metrics.expanded??null)}</td><td>${v.metrics.checks!==undefined?'边检碰 '+value(v.metrics.checks):v.metrics.scans!==undefined?'邻接扫描 '+value(v.metrics.scans):'—'}</td></tr>`).join('')}</tbody></table></div></section>`;
  const select=root.querySelector<HTMLSelectElement>('#record-phase')!;
  const draw=()=>{
   const v=data.views[index], [x0,y0,x1,y1]=v.bounds, w=x1-x0,h=y1-y0, unit=Math.max(w,h)/90;
   const path=(p:Point[]|undefined,color:string,dash='')=>p?.length?`<polyline points="${p.map(([x,y])=>`${x},${-y}`).join(' ')}" fill="none" stroke="${color}" stroke-width="${unit*.48}" stroke-linecap="round" stroke-linejoin="round" ${dash}/>`:'';
   const rect=(b:number[],color:string,opacity=1)=>`<rect x="${b[0]}" y="${-b[3]}" width="${b[2]-b[0]}" height="${b[3]-b[1]}" fill="${color}" opacity="${opacity}"/>`;
   let geometry='';
   if(v.grid){for(let x=0;x<v.grid.width;x++)for(let y=0;y<v.grid.height;y++)geometry+=`<rect x="${x-.48}" y="${-y-.48}" width=".96" height=".96" fill="#14303e"/>`;geometry+=v.grid.soft.map(({cell:[x,y],cost})=>rect([x-.46,y-.46,x+.46,y+.46],'#a4722e',Math.min(.85,cost/8))).join('');geometry+=v.grid.blocked.map(([x,y])=>rect([x-.48,y-.48,x+.48,y+.48],'#bc594c')).join('');}
   geometry+=(v.boxes??[]).map(b=>(v.robotHalfwidth?rect([b[0]-v.robotHalfwidth,b[1]-v.robotHalfwidth,b[2]+v.robotHalfwidth,b[3]+v.robotHalfwidth],'#c15d50',.25):'')+rect(b,'#bc594c',.8)).join('');
   geometry+=(v.circles??[]).map(([x,y,r])=>`<circle cx="${x}" cy="${-y}" r="${r}" fill="#bc594c" opacity=".8"/>`).join('');
   geometry+=(v.tree??[]).map(p=>path(p,'#244d5d')).join('');
   geometry+=(v.points??[]).map(([x,y])=>`<circle cx="${x}" cy="${-y}" r="${unit*.10}" fill="#6a9ba8"/>`).join('');
   geometry+=path(v.comparison,'#ffd08a',`stroke-dasharray="${unit*.9} ${unit*.6}"`)+path(v.path,'#5ce0d3');
   if(v.path.length)geometry+=v.path.filter((_,i)=>i===0||i===v.path.length-1).map(([x,y])=>`<circle cx="${x}" cy="${-y}" r="${unit*.65}" fill="#effaf7"/>`).join('');
   root.querySelector('#record-geometry')!.innerHTML=`<h3>${esc(v.label)}</h3><svg role="img" aria-label="${esc(v.label)}路线与当前障碍" viewBox="${x0-unit} ${-y1-unit} ${w+2*unit} ${h+2*unit}" xmlns="http://www.w3.org/2000/svg">${geometry}</svg>${v.path.length?'':'<p class="record-no-path">当前阶段没有返回路线</p>'}`;
   root.querySelector('#record-metrics')!.innerHTML=Object.entries(v.metrics).map(([k,val])=>`<div><span>${esc(names[k]??k)}</span><strong>${value(val)}</strong></div>`).join('');select.value=String(index);
  };
  select.onchange=()=>{stop();root.querySelector('#record-play')!.textContent='自动切换阶段';index=Number(select.value);draw();};
  root.querySelector<HTMLButtonElement>('#record-play')!.onclick=()=>{if(timer){stop();root.querySelector('#record-play')!.textContent='自动切换阶段';}else{root.querySelector('#record-play')!.textContent='暂停阶段切换';timer=setInterval(()=>{index=(index+1)%data.views.length;draw();},1800);}};
  root.querySelector<HTMLButtonElement>('#record-reset')!.onclick=()=>{stop();index=0;root.querySelector('#record-play')!.textContent='自动切换阶段';draw();};
  root.querySelectorAll<HTMLButtonElement>('[data-phase]').forEach(b=>b.onclick=()=>{stop();index=Number(b.dataset.phase);root.querySelector('#record-play')!.textContent='自动切换阶段';draw();root.querySelector('.record-plot')!.scrollIntoView({behavior:'smooth'});});draw();
 }).catch(e=>{if(!disposed)root.innerHTML=`<p>${esc(e)}。<a href="#/lesson/${lesson.id}">返回讲义</a></p>`;});
 return()=>{disposed=true;stop();};
}
