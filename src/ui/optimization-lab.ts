import { optimizeTrajectory, optimizationProblem, type OptimizationFrame, type OptimizationOptions, type OptimizationScene, type XY } from '../algorithms/optimization.ts';

/** Live numerical experiment, not playback of the Python reference histories. */
export function mountOptimizationLab(root: HTMLElement) {
  const $ = <T extends HTMLElement = HTMLElement>(s: string) => root.querySelector<T>(s)!;
  root.innerHTML = `<section class="lab-intro"><div><span class="eyebrow">INTERACTIVE LAB / 18</span><h2>整条路线一起改，再逐段验收</h2><p>CHOMP 与 STOMP 共用初值、目标和地图；每一步都在浏览器重新计算。</p></div><span class="badge live">● 实时计算 · 二维</span></section>
  <div class="lab-toolbar"><button class="button primary" id="opt-play">▶ 运行</button><button class="button" id="opt-step">单步</button><button class="button" id="opt-finish">计算至预算</button><button class="button" id="opt-reset">↺ 重置</button><span class="toolbar-spacer"></span><button class="button" id="opt-export">导出日志 ↓</button></div>
  <div class="lab-layout"><div class="lab-main"><div class="worlds comparison" id="opt-worlds"></div><label class="field"><span>回看已计算轮次 <output id="opt-clock"></output></span><input id="opt-time" type="range" min="0" max="0" step="1" value="0"></label><canvas id="opt-history" width="960" height="210" style="display:block;width:100%;background:#101f25;border-radius:12px" aria-label="CHOMP与STOMP总目标的实际迭代曲线"></canvas><p class="lab-footnote">二维点机器人，坐标单位米；灰线是初值，青/金线是当前路线，红线表示未通过整段检碰。圆盘已包含机器人尺寸与余量，虚线为0.30米惩罚影响区。</p></div>
  <aside class="parameters"><h3>同条件实验参数</h3><form id="opt-params"><label class="field"><span>地图与初值</span><select name="scene"><option value="route">第17集已有路线</option><option value="symmetry">对称直线失败案例</option></select></label><label class="field"><span>两边各自迭代预算</span><select name="iterations"><option>20</option><option>80</option><option selected>140</option><option>160</option></select></label><label class="field"><span>STOMP 随机种子</span><input name="seed" type="number" min="0" max="999999" step="1" value="7"></label><label class="field"><span>STOMP 扰动幅度 σ / m</span><select name="sigma"><option>.10</option><option selected>.30</option><option>.55</option><option>.80</option></select></label></form><p class="parameter-note">固定41点、39个内点、每轮32份STOMP候选；J = Js + 35 Jo。参数变化会清空本次日志并重算。相同轮数不等于相同计算量。</p><p class="parameter-note">浏览器使用 Mulberry32 + Box–Muller，Python原片使用 NumPy PCG64。种子可在本实现内复现，不与原片逐个随机数对应。</p></aside></div>
  <section class="lab-notes"><h3>成本下降，不等于安全证书</h3><p>本实验复用原始五点高斯求积、解析梯度与二阶差分度量。STOMP 不调用成本梯度；两种方法都加了总目标下降回溯。软惩罚允许碰撞候选，最终另做解析线段—圆盘检测。若本轮结果不通过，不要覆盖原来的可行路线。</p><p>尝试对称直线：确定性纯梯度CHOMP没有横向破对称机制；STOMP随机扰动可能绕开，也可能在预算内失败。切换场景自动采用 σ=0.55米、160轮，两边仍同轮数，不据此宣布普遍性能排名。这里不是完整机械臂规划、时间参数化或真机安全验证。</p><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/experiments/original/18" target="_blank" rel="noopener">原始Python、初值与实验日志 ↗</a></section>`;
  const form = $<HTMLFormElement>('#opt-params'), worlds = $('#opt-worlds');
  const methods = ['chomp', 'stomp'] as const, colors = ['#6cdddc', '#ffb766'];
  methods.forEach((method, i) => {
    const card = document.createElement('section'); card.className = 'world-card';
    card.innerHTML = `<div class="world-title"><b>${method.toUpperCase()}</b><span>二维点机器人 / m</span></div><canvas width="600" height="480" style="display:block;width:100%;background:#101f25" aria-label="${method.toUpperCase()}实时路径与圆盘障碍"></canvas><div class="metrics"></div><p class="event-message" aria-live="polite"></p>`;
    worlds.append(card);
  });
  let options: Omit<OptimizationOptions, 'method'>, histories: OptimizationFrame[][] = [], iterators: Generator<OptimizationFrame>[] = [], finished = [false, false], shown = 0, mode: 'paused' | 'play' | 'finish' = 'paused', disposed = false, raf = 0, last = 0;
  function pause() { mode = 'paused'; $('#opt-play').textContent = '▶ 运行'; }
  function end() { return finished.every(Boolean); }
  function setup() {
    pause();
    const data = new FormData(form), seedInput = form.elements.namedItem('seed') as HTMLInputElement;
    const seed = Math.min(999999, Math.max(0, Math.trunc(Number(data.get('seed')) || 0))); seedInput.value = String(seed);
    options = { scene: data.get('scene') as OptimizationScene, iterations: Number(data.get('iterations')), seed, sigma: Number(data.get('sigma')) };
    iterators = methods.map(method => optimizeTrajectory({ ...options, method }));
    histories = iterators.map(iterator => [iterator.next().value!]); finished = [false, false]; shown = 0; draw();
  }
  function advance() {
    iterators.forEach((iterator, i) => {
      if (finished[i]) return;
      const result = iterator.next();
      if (result.done) finished[i] = true;
      else { histories[i].push(result.value); if (result.value.stalled || result.value.iteration >= options.iterations!) finished[i] = true; }
    });
    shown = Math.max(...histories.map(h => h.length - 1));
    if (end()) pause();
  }
  function plotPath(canvas: HTMLCanvasElement, frame: OptimizationFrame, color: string) {
    const ctx = canvas.getContext('2d')!, w = canvas.width, h = canvas.height, scale = 78, x = (v: number) => w / 2 + (v - 2.5) * scale, y = (v: number) => h / 2 - v * scale;
    const problem = optimizationProblem(options.scene);
    ctx.clearRect(0, 0, w, h); ctx.font = '12px sans-serif'; ctx.lineWidth = 1;
    for (let i = -2; i <= 5; i++) { ctx.strokeStyle = '#2a414a'; ctx.beginPath(); ctx.moveTo(x(i), y(-2.5)); ctx.lineTo(x(i), y(2.5)); ctx.stroke(); ctx.fillStyle = '#91aab3'; ctx.fillText(String(i), x(i) - 3, y(-2.5) + 17); }
    for (let j = -2; j <= 2; j++) { ctx.strokeStyle = '#2a414a'; ctx.beginPath(); ctx.moveTo(x(-.5), y(j)); ctx.lineTo(x(5.5), y(j)); ctx.stroke(); }
    for (const disc of problem.discs) {
      ctx.fillStyle = '#873f41'; ctx.beginPath(); ctx.arc(x(disc.center[0]), y(disc.center[1]), disc.radius * scale, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#cf7477'; ctx.setLineDash([4, 5]); ctx.beginPath(); ctx.arc(x(disc.center[0]), y(disc.center[1]), (disc.radius + .3) * scale, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
    }
    const line = (path: XY[], stroke: string, width: number) => { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.beginPath(); path.forEach((q, i) => i ? ctx.lineTo(x(q[0]), y(q[1])) : ctx.moveTo(x(q[0]), y(q[1]))); ctx.stroke(); };
    line(problem.initial, '#81939a', 1.5); line(frame.path, frame.collisionFree ? color : '#ff7979', 3);
    frame.path.forEach((q, i) => { ctx.fillStyle = i === 0 || i === frame.path.length - 1 ? '#fff' : color; ctx.beginPath(); ctx.arc(x(q[0]), y(q[1]), i === 0 || i === frame.path.length - 1 ? 5 : 2, 0, Math.PI * 2); ctx.fill(); });
    ctx.fillStyle = '#c9dee3'; ctx.fillText('起点', x(frame.path[0][0]) + 8, y(frame.path[0][1]) - 10); ctx.fillText('目标', x(frame.path.at(-1)![0]) - 33, y(frame.path.at(-1)![1]) - 13); ctx.fillText('x / m', w - 45, h - 15);
  }
  function drawHistory() {
    const canvas = $<HTMLCanvasElement>('#opt-history'), ctx = canvas.getContext('2d')!, w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h); ctx.fillStyle = '#c9dee3'; ctx.font = '13px sans-serif'; ctx.fillText('总目标 J（对数纵轴；实际计算日志）', 16, 22);
    const all = histories.flat(), lo = Math.floor(Math.log10(Math.max(1e-6, Math.min(...all.map(f => f.cost))))), hi = Math.ceil(Math.log10(Math.max(...all.map(f => f.cost), .1))), span = Math.max(1, hi - lo), x = (it: number) => 72 + it / options.iterations! * (w - 100), y = (value: number) => 44 + (hi - Math.log10(Math.max(1e-6, value))) / span * (h - 76);
    ctx.strokeStyle = '#324d56'; ctx.lineWidth = 1;
    for (let exponent = lo; exponent <= hi; exponent++) { const yy = y(10 ** exponent); ctx.beginPath(); ctx.moveTo(70, yy); ctx.lineTo(w - 28, yy); ctx.stroke(); ctx.fillText(`1e${exponent}`, 16, yy + 4); }
    histories.forEach((history, i) => { ctx.strokeStyle = colors[i]; ctx.lineWidth = 2; ctx.beginPath(); history.forEach((f, j) => j ? ctx.lineTo(x(f.iteration), y(f.cost)) : ctx.moveTo(x(f.iteration), y(f.cost))); ctx.stroke(); ctx.fillStyle = colors[i]; ctx.fillText(methods[i].toUpperCase(), w - 190 + i * 90, 22); });
    ctx.strokeStyle = '#fff9'; ctx.beginPath(); ctx.moveTo(x(shown), 36); ctx.lineTo(x(shown), h - 26); ctx.stroke(); ctx.fillStyle = '#c9dee3'; ctx.fillText(`0 → ${options.iterations} 轮`, w - 108, h - 8);
  }
  function draw() {
    const max = Math.max(...histories.map(h => h.length - 1)), time = $<HTMLInputElement>('#opt-time'); time.max = String(max); time.value = String(shown); $('#opt-clock').textContent = `${shown} / 已计算 ${max} / 预算 ${options.iterations}`;
    histories.forEach((history, i) => {
      const frame = history[Math.min(shown, history.length - 1)], card = worlds.children[i] as HTMLElement;
      plotPath(card.querySelector('canvas')!, frame, colors[i]);
      card.querySelector('.metrics')!.innerHTML = `<div><span>总目标 J</span><b>${frame.cost.toFixed(5)}</b></div><div><span>平滑代理 Js</span><b>${frame.smooth.toFixed(5)}</b></div><div><span>障碍积分 Jo</span><b>${frame.obstacle.toFixed(5)}</b></div><div><span>路径长度</span><b>${frame.length.toFixed(3)} m</b></div><div><span>整段最小净距</span><b>${frame.clearance.toFixed(3)} m</b></div><div><span>优化成本评估</span><b>${frame.evaluations}</b></div>`;
      card.querySelector('.event-message')!.textContent = `第 ${frame.iteration} 轮 · ${frame.collisionFree ? '通过本模型整段检碰' : '未通过整段检碰，不能交付'}${frame.stalled ? ' · 无下降步长，已停滞' : frame.iteration === options.iterations ? ' · 已达预算' : frame.iteration > 0 && !frame.accepted ? ' · 此轮修改未接受' : ''}。不含显示与验收计算的成本评估计数，不能当成运行时间。`;
    });
    $<HTMLButtonElement>('#opt-step').disabled = end(); $<HTMLButtonElement>('#opt-finish').disabled = end(); drawHistory();
  }
  $('#opt-play').onclick = () => { if (mode !== 'paused') pause(); else if (!end()) { mode = 'play'; $('#opt-play').textContent = 'Ⅱ 暂停'; } };
  $('#opt-step').onclick = () => { pause(); advance(); draw(); };
  $('#opt-finish').onclick = () => { if (!end()) { mode = 'finish'; $('#opt-play').textContent = 'Ⅱ 暂停'; } };
  $('#opt-reset').onclick = setup;
  $<HTMLInputElement>('#opt-time').oninput = e => { pause(); shown = Number((e.target as HTMLInputElement).value); draw(); };
  form.onsubmit = e => e.preventDefault();
  form.onchange = e => {
    if ((e.target as HTMLInputElement).name === 'scene') {
      const symmetry = new FormData(form).get('scene') === 'symmetry';
      (form.elements.namedItem('sigma') as HTMLSelectElement).value = symmetry ? '.55' : '.30';
      (form.elements.namedItem('iterations') as HTMLSelectElement).value = symmetry ? '160' : '140';
    }
    setup();
  };
  $('#opt-export').onclick = () => {
    const blob = new Blob([JSON.stringify({ lesson: 18, scope: 'Static 2D point robot; fixed grid; no physical execution. Browser STOMP RNG differs from NumPy reference.', options, chomp: histories[0], stomp: histories[1] }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'episode18-optimization.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  setup();
  const tick = (now: number) => {
    if (disposed) return;
    if (mode !== 'paused' && (mode === 'finish' || now - last > 140)) {
      const start = performance.now(), count = mode === 'finish' ? 6 : 1;
      for (let i = 0; i < count && !end(); i++) { advance(); if (performance.now() - start > 16) break; }
      draw(); last = now;
    }
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => { disposed = true; pause(); cancelAnimationFrame(raf); iterators.forEach(iterator => iterator.return(undefined)); };
}
