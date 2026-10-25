import { PF_MODEL, PF_DEFAULTS, runPotentialField, pfForces, pfDistance, type PFPoint, type PFResult } from '../algorithms/potential-field.ts';

/** Computation is live; playback only reveals the already computed iterations. */
export function mountPotentialFieldLab(root: HTMLElement): () => void {
  const $ = <T extends HTMLElement = HTMLElement>(s: string) => root.querySelector<T>(s)!;
  root.innerHTML = `<section class="lab-intro"><div><span class="eyebrow">INTERACTIVE LAB / 16</span><h2>眼前是下坡，终点却还很远</h2><p>同一静态地图、同一组参数：左侧基础势场，右侧停滞后启用明确给定的临时目标。浏览器重新计算，不是预录轨迹。</p></div><span class="badge live">二维教学模型</span></section>
    <div class="lab-toolbar"><button class="button primary" id="pf-play">▶ 播放迭代</button><button class="button" id="pf-step">单步</button><button class="button" id="pf-reset">↺ 重置回放</button><button class="button" id="pf-default">恢复默认参数</button><span class="toolbar-spacer"></span><button class="button" id="pf-export">导出结果 ↓</button></div>
    <div class="lab-layout"><div class="lab-main"><div class="worlds comparison" id="pf-worlds"></div><label class="field"><span>共同迭代序号 <output id="pf-clock"></output></span><input id="pf-time" type="range" min="0" max="1" value="0" step="1"></label><p class="lab-footnote">这是二维俯视图，位置单位为米。圆盘已含机器人膨胀；不表示三维搜索或真实硬件。青色为吸引箭头，金色为排斥箭头，白色为合力；箭头为几何指引，不是牛顿力。</p></div>
    <aside class="parameters"><h3>共同参数</h3><form id="pf-params"><label class="field"><span>吸引系数 k_a <output id="pf-ka-label">1.00</output></span><input name="attraction" type="range" min=".2" max="3" step=".1" value="1"></label><label class="field"><span>斥力系数 k_r <output id="pf-kr-label">2.144</output></span><input name="repulsion" type="range" min=".2" max="5" step="any" value="${PF_DEFAULTS.repulsion}"></label><label class="field"><span>步长系数 α <output id="pf-gain-label">0.035</output></span><input name="gain" type="range" min=".005" max=".08" step=".005" value=".035"></label></form><p class="parameter-note">修改参数立即重算并暂停。最大单步0.075 m，影响净距1.5 m，预算2400次循环；每次候选整段检碰并回溯至当前目标势能不增加。回放序号不是物理时间，计算量也不是运行耗时。</p><div id="pf-summary" aria-live="polite"></div></aside></div>
    <section class="lab-notes"><h3>先看失败，再看恢复</h3><p>默认基础势场在约(1, 0)停滞，距终点仍4 m。右侧检测相同停滞后，依次尝试(0.8, −2.2)、(3.6, −2.2)和原终点。临时目标是本例预先指定的教学策略，并非算法自动找出的全局路线；换地图或参数不保证成功。</p><p>“位置没动”不等于已到达：必须另外检查目标误差。本例用最近60个位置均在3 mm内且尚未到达作为停滞检测；失败会明确停止，不把预算耗尽叫成功。所有接受的线段在膨胀圆盘模型内解析复检，顶点最小净距不冒充整段净距下界。</p><p><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/experiments/original/16" target="_blank" rel="noopener">原始Python、随机扰动与RRT-Connect完整对照 ↗</a></p></section>`;
  const form = $<HTMLFormElement>('#pf-params'), timeline = $<HTMLInputElement>('#pf-time');
  let runs: PFResult[] = [], frame = 0, maxFrame = 1, playing = false, disposed = false, raf = 0, last = 0, carry = 0;
  const statusText: Record<PFResult['status'], string> = { reached: '到达误差范围', stagnated: '停滞，未到达', subgoal_stagnated: '临时目标策略仍停滞', iteration_budget_exhausted: '预算耗尽，未到达' };
  const cards = ['基础人工势场', '停滞后启用临时目标'].map(title => {
    const card = document.createElement('section'); card.className = 'world-card';
    card.innerHTML = `<div class="world-title"><b>${title}</b><span>2D / 静态</span></div><canvas width="640" height="440" style="width:100%;display:block;background:#0b1820" aria-label="${title}的二维轨迹与合力"></canvas><div class="metrics"></div><p class="event-message"></p>`;
    $('#pf-worlds').append(card); return card;
  });
  function pause() { playing = false; carry = 0; $('#pf-play').textContent = '▶ 播放迭代'; }
  function plot(canvas: HTMLCanvasElement, run: PFResult, index: number) {
    const context = canvas.getContext('2d'); if (!context) return;
    const c: CanvasRenderingContext2D = context;
    const scale = 70, x = (v: number) => 100 + (v + .5) * scale, y = (v: number) => 220 - v * scale;
    c.clearRect(0, 0, canvas.width, canvas.height); c.font = '13px sans-serif';
    c.strokeStyle = '#243c47'; c.lineWidth = 1;
    for (let v = 0; v <= 5; v++) { c.beginPath(); c.moveTo(x(v), y(-2.6)); c.lineTo(x(v), y(2.6)); c.stroke(); c.fillStyle = '#90a8b4'; c.fillText(`${v}`, x(v) - 4, y(-2.6) + 20); }
    for (let v = -2; v <= 2; v++) { c.beginPath(); c.moveTo(x(-.5), y(v)); c.lineTo(x(5.6), y(v)); c.stroke(); c.fillText(`${v}`, x(-.5) - 24, y(v) + 4); }
    c.fillText('x / m', x(5) + 20, 432); c.fillText('y / m', 32, 42);
    for (const obstacle of PF_MODEL.obstacles) { c.beginPath(); c.arc(x(obstacle[0]), y(obstacle[1]), PF_MODEL.radius * scale, 0, Math.PI * 2); c.fillStyle = '#ac6473'; c.fill(); c.strokeStyle = '#f0a6b5'; c.stroke(); }
    if (run.mode === 'subgoal') {
      c.setLineDash([4, 5]); c.strokeStyle = '#b6a3e177';
      for (const q of PF_MODEL.subgoals.slice(0, -1)) { c.strokeRect(x(q[0]) - 6, y(q[1]) - 6, 12, 12); }
      c.setLineDash([]);
    }
    for (const [q, label, color] of [[PF_MODEL.start, '起点', '#80c7f4'], [PF_MODEL.goal, '终点', '#8ae9b3']] as const) {
      c.beginPath(); c.arc(x(q[0]), y(q[1]), 6, 0, Math.PI * 2); c.fillStyle = color; c.fill(); c.fillText(label, x(q[0]) - 12, y(q[1]) - 16);
    }
    c.beginPath(); c.strokeStyle = '#70dedb'; c.lineWidth = 2.5;
    run.path.slice(0, index + 1).forEach((q, i) => i ? c.lineTo(x(q[0]), y(q[1])) : c.moveTo(x(q[0]), y(q[1]))); c.stroke();
    const p = run.path[index], g = run.goals[index], forces = pfForces(p, g, run.options);
    function arrow(v: PFPoint, color: string) {
      const dx = v[0] * scale * .16, dy = -v[1] * scale * .16;
      if (Math.hypot(dx, dy) < .5) return;
      const angle = Math.atan2(dy, dx), ex = x(p[0]) + dx, ey = y(p[1]) + dy;
      c.strokeStyle = color; c.fillStyle = color; c.lineWidth = 2;
      c.beginPath(); c.moveTo(x(p[0]), y(p[1])); c.lineTo(ex, ey); c.stroke();
      c.beginPath(); c.moveTo(ex, ey); c.lineTo(ex - 7 * Math.cos(angle - .4), ey - 7 * Math.sin(angle - .4)); c.lineTo(ex - 7 * Math.cos(angle + .4), ey - 7 * Math.sin(angle + .4)); c.closePath(); c.fill();
    }
    arrow(forces.attraction, '#50ded9'); arrow(forces.repulsion, '#ffbb71'); arrow(forces.total, '#ffffff');
    c.fillStyle = '#fff'; c.beginPath(); c.arc(x(p[0]), y(p[1]), 4, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#c3d5dd'; c.fillText(`p=(${p[0].toFixed(3)}, ${p[1].toFixed(3)})`, 12, 20);
    c.fillText(`当前吸引目标=(${g[0].toFixed(1)}, ${g[1].toFixed(1)})`, 315, 20);
  }
  function draw() {
    timeline.value = String(frame); $('#pf-clock').textContent = `${frame} / ${maxFrame}`;
    runs.forEach((run, i) => {
      const index = Math.min(frame, run.path.length - 1), p = run.path[index];
      plot(cards[i].querySelector('canvas')!, run, index);
      cards[i].querySelector('.metrics')!.innerHTML = `<div><span>当前目标距离</span><b>${pfDistance(p, PF_MODEL.goal).toFixed(3)} m</b></div><div><span>最终路径长度</span><b>${run.lengthM.toFixed(3)} m</b></div><div><span>整段检查（含复检）</span><b>${run.planningChecks + run.validationChecks}</b></div><div><span>最终顶点净距</span><b>${run.minVertexClearanceM.toFixed(3)} m</b></div>`;
      const active = run.events.filter(e => e.step + 1 <= index).at(-1);
      cards[i].querySelector('.event-message')!.textContent = index === run.path.length - 1 ? `结果：${statusText[run.status]}。接受线段复检：${run.allEdgesCollisionFree ? '全部无碰撞' : '未通过'}。` : `回放第${index}步${active?.kind === 'temporary_goals_enabled' ? '；已启用预设临时目标' : ''}。最终统计已在计算后显示，不代表回放已完成。`;
    });
  }
  function setup() {
    pause(); frame = 0;
    const values = new FormData(form), attraction = Number(values.get('attraction')), repulsion = Number(values.get('repulsion')), gain = Number(values.get('gain'));
    $('#pf-ka-label').textContent = attraction.toFixed(2); $('#pf-kr-label').textContent = repulsion.toFixed(3); $('#pf-gain-label').textContent = gain.toFixed(3);
    runs = ['baseline', 'subgoal'].map(mode => runPotentialField(mode as 'baseline' | 'subgoal', { attraction, repulsion, gain }));
    maxFrame = Math.max(...runs.map(r => r.path.length - 1)); timeline.max = String(maxFrame);
    $('#pf-summary').innerHTML = `<p>已重新计算：<br>基础势场：${statusText[runs[0].status]}<br>临时目标：${statusText[runs[1].status]}</p>`; draw();
  }
  $('#pf-play').onclick = () => { if (frame >= maxFrame) frame = 0; playing = !playing; $('#pf-play').textContent = playing ? 'Ⅱ 暂停' : '▶ 播放迭代'; draw(); };
  $('#pf-step').onclick = () => { pause(); frame = Math.min(frame + 1, maxFrame); draw(); };
  $('#pf-reset').onclick = () => { pause(); frame = 0; draw(); };
  $('#pf-default').onclick = () => { form.reset(); setup(); };
  timeline.oninput = () => { pause(); frame = Number(timeline.value); draw(); };
  form.oninput = setup;
  $('#pf-export').onclick = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify({ lesson: 16, model: 'Static 2D point robot with inflated disks; no hardware guarantee', runs }, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = 'lesson-16-potential-field.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  setup();
  function tick(now: number) {
    if (disposed) return;
    if (playing) {
      carry += Math.min(.1, (now - last) / 1000) * 40;
      if (carry >= 1) { const steps = Math.floor(carry); carry -= steps; frame = Math.min(maxFrame, frame + steps); if (frame >= maxFrame) pause(); draw(); }
    }
    last = now; raf = requestAnimationFrame(tick);
  }
  raf = requestAnimationFrame(tick);
  return () => { disposed = true; cancelAnimationFrame(raf); };
}
