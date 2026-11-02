import { asset } from '../content/catalog.ts';
type Point=[number,number];
interface View {label:string;bounds:[number,number,number,number];metrics:Record<string,number|boolean|null>;grid:{width:number;height:number;blocked:Point[];start:Point;goal:Point};timeSeries:{path:number[][];baseline:number[][];obstacles:Point[][];radius:number;horizon:number};}
interface Replay {scope:string;views:View[];}
const esc=(s:unknown)=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export function sampleAt(p:number[][],t:number):Point {
 const i=Math.min(Math.floor(t),p.length-1),a=p[i],b=p[Math.min(i+1,p.length-1)],u=t-Math.floor(t);
 return [a[0]+u*(b[0]-a[0]),a[1]+u*(b[1]-a[1])];
}
/** Interpolate recorded Python tracks; this browser does not run a planner. */
export function mountTemporalLab(root:HTMLElement):()=>void {
 let disposed=false,index=0,t=0,timer:ReturnType<typeof setInterval>|undefined;
 const stop=()=>{if(timer)clearInterval(timer);timer=undefined;};
 root.innerHTML='<p>读取真实时序实验…</p>';
 void fetch(asset('experiments/27.json')).then(r=>{if(!r.ok)throw Error('实验记录暂未加载');return r.json()as Promise<Replay>;}).then(data=>{
  if(disposed)return;
  const val=(v:unknown)=>v===null?'时域内无解 / —':typeof v==='boolean'?(v?'可行':'不可行'):typeof v==='number'?(Number.isInteger(v)?String(v):v.toFixed(6)):esc(v);
  root.innerHTML=`<section class="callout"><span class="eyebrow">RECORDED SPACE-TIME EXPERIMENT / 27</span><h2>把路线放回时间里</h2><p>${esc(data.scope)}</p><p><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/experiments/original/27" target="_blank" rel="noopener noreferrer">打开可运行Python与独立验收 ↗</a></p></section><section class="record-controls"><label>实验阶段 <select aria-label="实验阶段" id="record-phase">${data.views.map((v,i)=>`<option value="${i}">${esc(v.label)}</option>`).join('')}</select></label><label>仿真时刻 <input id="record-time" aria-label="仿真时刻" type="range" min="0" step="0.1" value="0"><output id="record-time-label"></output></label><button class="button" id="record-play">播放时序</button><button class="button" id="record-reset">回到0秒</button></section><section class="record-plot" id="record-geometry"></section><div class="record-metrics" id="record-metrics"></div><section class="record-comparison"><h2>同模型实验账本</h2><p>青点：时空方案；金点：忽略动态的基线；橙点：预测障碍；灰格：静态禁区。虚线为位置投影，等待请看时间。当前时刻无碰撞不能代替整段检碰，最小距离由Python解析计算。</p><div class="record-table"><table><thead><tr><th>场景</th><th>到达s</th><th>等待s</th><th>中心距m</th><th>展开状态</th><th>动态基线</th></tr></thead><tbody>${data.views.map(v=>`<tr><td>${esc(v.label)}</td><td>${val(v.metrics.arrival_s)}</td><td>${val(v.metrics.wait_s)}</td><td>${val(v.metrics.min_center_separation)}</td><td>${val(v.metrics.expansions)}</td><td>${val(v.metrics.baseline_feasible)}</td></tr>`).join('')}</tbody></table></div></section>`;
  const phase=root.querySelector<HTMLSelectElement>('#record-phase')!,slider=root.querySelector<HTMLInputElement>('#record-time')!,play=root.querySelector<HTMLButtonElement>('#record-play')!;
  const draw=()=>{
   const v=data.views[index],s=v.timeSeries,[x0,y0,x1,y1]=v.bounds,unit=Math.max(x1-x0,y1-y0)/90;t=Math.min(t,s.horizon);slider.max=String(s.horizon);slider.value=String(t);root.querySelector('#record-time-label')!.textContent=` ${t.toFixed(1)} s / H=${s.horizon} s`;
   const line=(p:number[][],color:string)=>p.length?`<polyline points="${p.map(a=>`${a[0]},${-a[1]}`).join(' ')}" fill="none" stroke="${color}" stroke-width="${unit*.45}" stroke-dasharray="${unit*.8} ${unit*.5}"/>`:'';
   const dot=(p:Point,r:number,color:string)=>`<circle cx="${p[0]}" cy="${-p[1]}" r="${r}" fill="${color}" stroke="#fff" stroke-width="${unit*.12}"/>`;
   let geo='';for(let x=0;x<v.grid.width;x++)for(let y=0;y<v.grid.height;y++)geo+=`<rect x="${x-.48}" y="${-y-.48}" width=".96" height=".96" fill="#14303e"/>`;
   geo+=v.grid.blocked.map(([x,y])=>`<rect x="${x-.48}" y="${-y-.48}" width=".96" height=".96" fill="#687b85"/>`).join('');
   geo+=line(s.baseline,'#d4a852')+line(s.path,'#37d6ce');geo+=s.obstacles.map(p=>line(p,'#944d3f')).join('');
   const obs=s.obstacles.map(p=>sampleAt(p,t));geo+=obs.map(p=>dot(p,s.radius,'#e65c3b')).join('');
   const p=s.path.length?sampleAt(s.path,t):undefined,b=s.baseline.length?sampleAt(s.baseline,t):undefined;
   if(b)geo+=dot(b,s.radius,'#d4a852');if(p)geo+=dot(p,s.radius,'#37d6ce');
   const hit=(p:Point)=>obs.some(o=>Math.hypot(o[0]-p[0],o[1]-p[1])<=2*s.radius+1e-9);
   root.querySelector('#record-geometry')!.innerHTML=`<h3>${esc(v.label)}</h3><svg role="img" aria-label="${esc(v.label)}时序位置" viewBox="${x0} ${-y1} ${x1-x0} ${y1-y0}" xmlns="http://www.w3.org/2000/svg">${geo}</svg><p>t=${t.toFixed(1)}s：${p?`时空方案中心 (${p.map(n=>n.toFixed(2)).join(', ')})，${hit(p)?'此刻冲突':'此刻未冲突'}`:'本阶段无可执行时空方案'}；基线${b?(hit(b)?'此刻冲突':'此刻未冲突'):'无路线'}。</p>`;
   const labels:Record<string,string>={arrival_s:'到达 / s',oracle_s:'独立最早到达 / s',wait_s:'等待 / s',moves:'移动步数',min_center_separation:'最小中心距 / m',expansions:'展开状态',checks:'候选转移检查',baseline_feasible:'动态基线可行'};
   root.querySelector('#record-metrics')!.innerHTML=Object.entries(v.metrics).map(([k,n])=>`<div><span>${esc(labels[k]??k)}</span><strong>${val(n)}</strong></div>`).join('');
  };
  phase.onchange=()=>{stop();play.textContent='播放时序';index=Number(phase.value);t=0;draw();};
  slider.oninput=()=>{stop();play.textContent='播放时序';t=Number(slider.value);draw();};
  root.querySelector<HTMLButtonElement>('#record-reset')!.onclick=()=>{stop();play.textContent='播放时序';t=0;draw();};
  play.onclick=()=>{if(timer){stop();play.textContent='播放时序';}else{if(t>=data.views[index].timeSeries.horizon)t=0;play.textContent='暂停';timer=setInterval(()=>{t=Math.min(t+.1,data.views[index].timeSeries.horizon);draw();if(t>=data.views[index].timeSeries.horizon){stop();play.textContent='播放时序';}},100);}};
  draw();
 }).catch(e=>{if(!disposed)root.innerHTML=`<p>${esc(e)}。请返回讲义或运行Python。</p>`;});
 return()=>{disposed=true;stop();};
}
