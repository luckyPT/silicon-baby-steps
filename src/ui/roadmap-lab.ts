import { compareRoadmaps, roadmapObstacles, type RoadmapPoint, type RoadmapEdge } from '../algorithms/roadmap.ts';

export function mountRoadmapLab(root: HTMLElement): () => void {
  root.innerHTML = `<section class="lab-intro"><div><span class="eyebrow">INTERACTIVE LAB / 17</span><h2>先建路网，再按需检碰</h2><p>PRM 与边延迟验证共用同一张候选图。参数改变后在浏览器重新计算，播放回放本次真实检碰日志。</p></div><span class="badge live">● 实时计算 · 2D</span></section>
  <div class="lab-toolbar"><button class="button primary" data-action="play">▶ 播放验证</button><button class="button" data-action="step">单步</button><button class="button" data-action="reset">↺ 重置回放</button><button class="button" data-action="export">导出计算结果 ↓</button></div>
  <div class="lab-layout"><div class="lab-main"><div class="world-card"><div class="world-title"><b>静态二维点机器人 · 膨胀圆盘障碍</b><span>长度单位 m</span></div><div data-view></div><div class="metrics" data-metrics></div><p class="event-message" data-message aria-live="polite"></p></div><p class="lab-footnote">灰：未知候选边；青：已验证有效；红：已验证碰撞；金：本轮候选路径；绿：整段验证后的最终路径。淡紫虚线为 PRM 的最终路径。</p></div>
  <aside class="parameters"><h3>同条件实验参数</h3><form data-params><label class="field"><span>固定种子</span><input name="seed" type="number" value="17" step="1"></label><label class="field"><span>有效采样点 N（20—400）</span><input name="n" type="number" min="20" max="400" step="1" value="180"></label><label class="field"><span>近邻数 k（须小于 N）</span><input name="k" type="number" min="1" max="30" step="1" value="10"></label><label class="field"><span>依次查询，复用基础边缓存</span><select name="query"><option value="0">查询 1：左下 → 右上</option><option value="1">查询 2：左上 → 右下</option><option value="2">查询 3：左中 → 右中</option></select></label></form><p class="parameter-note">计数为算法阶段线段检碰，不含点检测、搜索与最终独立复检，不是运行时间。查询 2/3 保留前序基础边缓存；临时起终点和接入边不跨查询复用。</p></aside></div>
  <section class="lab-notes"><h3>Lazy 省下的是哪些工作？</h3><p>本实现先验证所有采样点，只延迟候选边检测；不是原论文中同时延迟节点的完整变体。发现无效边后删边重搜，只有整条路径验证通过才可返回。有限路网无解不证明连续空间无路。</p><p>浏览器使用 Mulberry32，原始 Python 使用 NumPy；相同种子在两种实现中不代表相同样本。本页两种方法始终共用同一张浏览器图，原片数值请看原始报告。几何路径不是动力学或真机安全认证。</p><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/experiments/original/17" target="_blank" rel="noopener">原始实验与核验报告 ↗</a></section>`;
  const $ = <T extends HTMLElement = HTMLElement>(s: string) => root.querySelector<T>(s)!;
  const form = $<HTMLFormElement>('[data-params]'), play = $<HTMLButtonElement>('[data-action="play"]'), step = $<HTMLButtonElement>('[data-action="step"]');
  let result: ReturnType<typeof compareRoadmaps> | undefined, frame = 0, timer: ReturnType<typeof setInterval> | undefined;
  const stop = () => { if (timer !== undefined) clearInterval(timer); timer = undefined; play.textContent = '▶ 播放验证'; };
  const queryIndex = () => Number(new FormData(form).get('query') ?? 0);
  const xy = (p: RoadmapPoint): RoadmapPoint => [40 + (p[0] + .4) * 100, 40 + (2.5 - p[1]) * 100];
  const line = (vertices: RoadmapPoint[], e: RoadmapEdge, color: string, width = 1, dash = '') => {
    const a = xy(vertices[e[0]]), b = xy(vertices[e[1]]);
    return `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${color}" stroke-width="${width}" ${dash ? `stroke-dasharray="${dash}"` : ''}/>`;
  };
  function draw() {
    if (!result) return;
    const index = queryIndex(), q = result.queries[index], shown = q.trace.slice(0, frame), current = shown.at(-1), complete = frame >= q.trace.length;
    const known = new Map(q.initialKnownEdges.map(x => [x.edge.join(','), x.valid]));
    for (const event of shown) for (const t of event.tested) known.set(t.edge.join(','), t.valid);
    const path = current?.candidate ?? [], validPath = complete && q.lazyPath.length > 0;
    let svg = `<svg viewBox="0 0 670 580" role="img" aria-label="PRM与Lazy PRM二维路网和逐轮验证" style="display:block;width:100%;background:#10212b"><rect x="40" y="40" width="590" height="500" fill="none" stroke="#536775"/>`;
    for (const e of q.edges) svg += line(q.vertices, e, known.get(e.join(',')) === true ? '#37b7bd88' : known.get(e.join(',')) === false ? '#ed7780' : '#66778730', known.get(e.join(',')) === false ? 2 : 1);
    for (const o of roadmapObstacles) { const p = xy(o.center); svg += `<circle cx="${p[0]}" cy="${p[1]}" r="${o.radius * 100}" fill="#b4566355" stroke="#ed7780"/>`; }
    for (const p of result.graph.vertices) { const c = xy(p); svg += `<circle cx="${c[0]}" cy="${c[1]}" r="2" fill="#85a5b6"/>`; }
    for (let i = 1; i < q.eagerPath.length; i++) svg += line(q.vertices, [q.eagerPath[i - 1], q.eagerPath[i]], '#b3a2f4', 5, '7 5');
    for (let i = 1; i < path.length; i++) svg += line(q.vertices, [path[i - 1], path[i]], validPath ? '#64df9f' : '#f0bd68', 3);
    if (current?.invalid) svg += line(q.vertices, current.invalid, '#ff5369', 5);
    for (const [j, label] of [[result.n, 'S'], [result.n + 1, 'G']] as const) { const p = xy(q.vertices[j]); svg += `<circle cx="${p[0]}" cy="${p[1]}" r="7" fill="${label === 'S' ? '#6cdddc' : '#ffb766'}"/><text x="${p[0] + 11}" y="${p[1] - 10}" fill="#fff" font-size="18">${label}</text>`; }
    svg += '<text x="40" y="565" fill="#b6cad4" font-size="14">x ∈ [−0.4, 5.5] m；y ∈ [−2.5, 2.5] m</text></svg>';
    $('[data-view]').innerHTML = svg;
    const checks = shown.reduce((sum, e) => sum + e.tested.length, 0), priorLazy = result.queries.slice(0, index).reduce((sum, z) => sum + z.lazyChecks, 0), eagerCumulative = result.eagerBaseChecks + result.queries.slice(0, index + 1).reduce((sum, z) => sum + z.eagerChecks, 0);
    $('[data-metrics]').innerHTML = `<div><span>验证轮次</span><b>${frame} / ${q.trace.length}</b></div><div><span>PRM 累计检碰</span><b>${eagerCumulative}</b></div><div><span>Lazy 累计检碰</span><b>${priorLazy + checks}</b></div><div><span>本次最终成本 / m</span><b>${complete ? q.lazyCost?.toFixed(3) ?? '当前图无解' : '尚未验证'}</b></div>`;
    $('[data-message]').textContent = frame === 0 ? `图已重算：${result.n} 个有效点，${result.graph.edges.length} 条基础候选边。点击单步观察 Lazy 检碰。` : complete ? q.lazyPath.length ? `两种方法返回同成本路径：PRM ${q.eagerCost!.toFixed(4)} m / Lazy ${q.lazyCost!.toFixed(4)} m。所有返回边已复检。三次查询总检碰：${result.eagerTotalChecks} / ${result.lazyTotalChecks}；不等于耗时排名。` : '当前有限路网没有可行路径。可以增加 N 或 k 重新建图，不把未知边当成可执行路径。' : `第 ${frame} 轮新增检测 ${current!.tested.length} 条边；发现无效边 ${current!.invalid?.join(' ↔ ')}，下一轮删边重搜。金色候选尚未获准执行。`;
    step.disabled = complete; play.disabled = complete;
  }
  function setup() {
    stop(); frame = 0;
    try {
      const data = new FormData(form), seed = Number(data.get('seed')), n = Number(data.get('n')), k = Number(data.get('k'));
      if (n < 20 || n > 400 || k > 30) throw new Error('N 需在 20—400 之间，k 需在 1—30 之间且小于 N。');
      result = compareRoadmaps({ seed, n, k }); draw();
    } catch (error) { result = undefined; $('[data-view]').innerHTML = ''; $('[data-metrics]').innerHTML = ''; $('[data-message]').textContent = String(error); play.disabled = true; step.disabled = true; }
  }
  const advance = () => { if (!result) return; frame = Math.min(frame + 1, result.queries[queryIndex()].trace.length); draw(); if (frame >= result.queries[queryIndex()].trace.length) stop(); };
  play.onclick = () => { if (timer !== undefined) stop(); else { play.textContent = 'Ⅱ 暂停'; advance(); if (!play.disabled) timer = setInterval(advance, 800); } };
  step.onclick = () => { stop(); advance(); };
  $('[data-action="reset"]').onclick = () => { stop(); frame = 0; draw(); };
  form.onchange = event => { if ((event.target as HTMLInputElement).name === 'query') { stop(); frame = 0; draw(); } else setup(); };
  $('[data-action="export"]').onclick = () => {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })), link = document.createElement('a');
    link.href = url; link.download = `lesson17-roadmap-seed${result.seed}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  setup(); return stop;
}
