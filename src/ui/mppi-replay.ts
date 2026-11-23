import { asset } from '../content/catalog.ts';

type Point = [number, number];
type Pose = [number, number, number];
type Wall = [number, number, number, number];
interface Metrics {
  success: boolean;
  duration: number;
  clearance: number;
  endDistance: number;
}
interface Run {
  label: string;
  seed: number;
  states: Pose[];
  controls: Point[];
  predictions: Point[][];
  samples: Point[][];
  metrics: Metrics;
}
interface Replay {
  dt: number;
  horizonSteps: number;
  radius: number;
  goalRadius: number;
  goal: Point;
  walls: Wall[];
  views: Run[];
  results: {label: string; runs: Metrics[]}[];
}

const scale = 128;
const toScreen = ([x,y]: Point) => [330 + scale*x, 240 - scale*y] as const;
const points = (path: Point[]) => path.map((point) => toScreen(point).join(',')).join(' ');

export function mountMppiReplay(root: HTMLElement): () => void {
  const request = new AbortController();
  root.innerHTML = '<p>正在读取第29集实验记录…</p>';

  void fetch(asset('experiments/29.json'), {signal: request.signal}).then(async (response) => {
    if (!response.ok) throw Error('读取实验记录失败');
    const data = await response.json() as Replay;
    if (request.signal.aborted) return;
    const walls = data.walls.map(([left,bottom,right,top]) => {
      const [x,y] = toScreen([left,top]);
      return `<rect x="${x}" y="${y}" width="${scale*(right-left)}" height="${scale*(top-bottom)}" fill="#bc594c"/>`;
    }).join('');
    const [gx,gy] = toScreen(data.goal);
    const horizon = (data.dt*data.horizonSteps).toFixed(2);

    root.innerHTML = `
      <section class="callout"><h2>倒车脱困 · MPC / MPPI 回放</h2>
        <p>切换工况后先看 0 秒的首个动作，再拖动滑块查看每轮 ${horizon} 秒的预测。数据由 Python 离线复算。</p>
        <p><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/experiments/original/29">打开可运行 Python 实验</a> · <a href="#/lesson/29">返回讲义</a></p>
      </section>
      <section class="record-controls">
        <label>实验工况 <select id="mppi-run"></select></label>
        <label>仿真时刻 <input type="range" id="mppi-time" min="0" value="0" step="1"><output id="mppi-clock" for="mppi-time"></output></label>
      </section>
      <section class="record-plot">
        <svg role="img" aria-label="死胡同、车身、已执行轨迹和当前有限窗口预测" viewBox="0 0 690 480">
          ${walls}
          <circle cx="${gx}" cy="${gy}" r="${scale*data.goalRadius}" fill="#425d47" stroke="#cfe799" stroke-width="2"/>
          <g id="mppi-samples" fill="none" stroke="#789aaa" stroke-width="1.4" opacity=".35"></g>
          <polyline id="mppi-prediction" fill="none" stroke="#ffd386" stroke-width="4" stroke-dasharray="8 7"/>
          <polyline id="mppi-track" fill="none" stroke="#5ee1ce" stroke-width="4"/>
          <g id="mppi-car">
            <circle r="${scale*data.radius}" fill="#da724f" stroke="#fff0d5" stroke-width="2"/>
            <path d="M -8 0 H 11 m -6 -5 6 5 -6 5" fill="none" stroke="#fff0d5" stroke-width="3"/>
          </g>
        </svg>
        <p>红色为墙，绿色圆为到达判定区。青线是已执行轨迹，金色虚线是本轮预测。MPPI 的 0 秒处显示首批候选的少量样本。</p>
      </section>
      <div class="record-metrics" id="mppi-metrics"></div>
      <section class="record-comparison"><h2>同一张地图的四组结果</h2>
        <p>到达数按各组实际运行次数统计。距离、净距和仿真时长列均来自种子 29 的回放。</p>
        <div class="record-table"><table><thead><tr><th>工况</th><th>到达数 / 运行数</th><th>最终目标距离</th><th>最小净距</th><th>记录时长</th></tr></thead><tbody id="mppi-results"></tbody></table></div>
      </section>`;

    const select = root.querySelector<HTMLSelectElement>('#mppi-run')!;
    const slider = root.querySelector<HTMLInputElement>('#mppi-time')!;
    const clock = root.querySelector<HTMLOutputElement>('#mppi-clock')!;
    const car = root.querySelector('#mppi-car')!;
    const track = root.querySelector('#mppi-track')!;
    const forecast = root.querySelector('#mppi-prediction')!;
    const samples = root.querySelector('#mppi-samples')!;
    const metrics = root.querySelector('#mppi-metrics')!;
    const table = root.querySelector<HTMLTableSectionElement>('#mppi-results')!;

    data.views.forEach((run, i) => select.add(new Option(run.label, String(i))));
    data.results.forEach(({label,runs}) => {
      const first = runs[0];
      const row = table.insertRow();
      [label, `${runs.filter(run => run.success).length} / ${runs.length}`,
        `${first.endDistance.toFixed(3)} m`, `${(first.clearance*100).toFixed(1)} cm`,
        `${first.duration.toFixed(2)} s`].forEach((value) => { row.insertCell().textContent = value; });
    });

    const update = () => {
      const run = data.views[Number(select.value)];
      const index = slider.valueAsNumber;
      const [x,y,heading] = run.states[index];
      const [sx,sy] = toScreen([x,y]);
      car.setAttribute('transform', `translate(${sx} ${sy}) rotate(${-heading*180/Math.PI})`);
      track.setAttribute('points', points(run.states.slice(0,index+1).map(([px,py]) => [px,py])));
      forecast.setAttribute('points', points(run.predictions[index] ?? []));
      samples.setAttribute('visibility', index === 0 ? 'visible' : 'hidden');
      clock.value = `${(index*data.dt).toFixed(2)} s`;
      slider.setAttribute('aria-valuetext', clock.value);
      const [v,w] = run.controls[index] ?? [];
      metrics.innerHTML = `<div><span>下一步线速度</span><strong>${v === undefined ? '已结束' : v.toFixed(3)+' m/s'}</strong></div>
        <div><span>下一步角速度</span><strong>${w === undefined ? '已结束' : w.toFixed(3)+' rad/s'}</strong></div>
        <div><span>离目标距离</span><strong>${Math.hypot(x-data.goal[0],y-data.goal[1]).toFixed(3)} m</strong></div>`;
    };
    const reset = () => {
      const run = data.views[Number(select.value)];
      slider.max = String(run.states.length-1);
      slider.value = '0';
      samples.innerHTML = run.samples.map((path) => `<polyline points="${points(path)}"/>`).join('');
      update();
    };
    select.onchange = reset;
    slider.oninput = update;
    reset();
  }).catch(() => {
    if (!request.signal.aborted) root.innerHTML = '<p>第29集实验记录加载失败。<a href="#/lesson/29">返回讲义</a></p>';
  });
  return () => request.abort();
}
