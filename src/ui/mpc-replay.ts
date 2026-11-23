import { asset } from '../content/catalog.ts';

type Point = [number, number];
type State = [number, number, number, number, number];
interface Run {
  id: string;
  label: string;
  states: State[];
  predictions: Point[][];
  perturbationTime: number | null;
  metrics: {
    duration: number;
    minMargin: number;
    endSpeed: number;
    maxDeviation: number;
    successfulSolves: number;
  };
}
interface Replay {
  dt: number;
  road: Point[];
  footprint: [number, number, number];
  roadHalfWidth: number;
  views: Run[];
}

const number = (n: number) => n.toFixed(1);
const xy = ([x, y]: Point) => [590 + 230 * x, 225 - 230 * y] as const;
const points = (section: Point[]) => section.map((p) => xy(p).map(number).join(',')).join(' ');

export function mountMpcReplay(root: HTMLElement): () => void {
  const request = new AbortController();
  let animation = 0;
  let last = 0;
  let elapsed = 0;
  let playing = false;
  const stop = () => { playing = false; cancelAnimationFrame(animation); };
  root.innerHTML = '<p>正在读取第28集实验记录…</p>';

  void fetch(asset('experiments/28.json'), { signal: request.signal }).then(async (response) => {
    if (!response.ok) throw Error('读取实验记录失败');
    const data = await response.json() as Replay;
    const top = data.road.map(([x, y]): Point => [x, y + data.roadHalfWidth]);
    const bottom = data.road.map(([x, y]): Point => [x, y - data.roadHalfWidth]);
    const [rear, front, halfWidth] = data.footprint;
    root.innerHTML = `
      <section class="callout"><h2>机械臂推车 · MPC 闭环回放</h2>
        <p>切换跟线策略，拖动时间查看车身、当前速度和两秒预测。轨迹由 Python 离线求解。</p>
        <p><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/experiments/original/28">打开可运行 Python 实验</a> · <a href="#/lesson/28">返回讲义</a></p>
      </section>
      <section class="record-controls"><label>实验工况 <select id="mpc-run"></select></label>
        <label>仿真时刻 <input type="range" id="mpc-time" min="0" value="0" step="0.1"><output id="mpc-clock"></output></label>
        <button class="button" id="mpc-play" type="button">播放</button><button class="button" id="mpc-reset" type="button">回到 0 秒</button>
      </section>
      <section class="record-plot">
        <svg role="img" aria-label="S弯、车身轮廓、实际与预测轨迹" viewBox="0 0 1100 448">
          <polygon points="${points([...top, ...bottom.slice().reverse()])}" fill="#1f3a43"/>
          <polyline points="${points(top)}" fill="none" stroke="#e5988a" stroke-width="3"/>
          <polyline points="${points(bottom)}" fill="none" stroke="#e5988a" stroke-width="3"/>
          <polyline points="${points(data.road)}" fill="none" stroke="#b2a77e" stroke-width="2" stroke-dasharray="7 10"/>
          <polyline id="mpc-old" fill="none" stroke="#ee9b91" stroke-width="3" stroke-dasharray="5 8"/>
          <polyline id="mpc-forecast" fill="none" stroke="#ffd386" stroke-width="4" stroke-dasharray="8 8"/>
          <polyline id="mpc-track" fill="none" stroke="#5ee1ce" stroke-width="4"/>
          <g id="mpc-car"><rect x="${rear*230}" y="${-halfWidth*230}" width="${(front-rear)*230}" height="${halfWidth*460}" rx="5" fill="#ff784c" stroke="#fff0d5" stroke-width="2"/><path d="M 14 0 H 41 m -9 -6 9 6 -9 6" fill="none" stroke="#fff0d5" stroke-width="3"/></g>
        </svg>
        <p>青线为已执行轨迹，金色虚线为本轮的预测窗口。受扰回放中，淡红虚线保留受扰前的预测。</p>
      </section>
      <div class="record-metrics" id="mpc-metrics"></div>
      <section class="record-comparison"><h2>同一条 S 弯，四次结果</h2>
        <p>边界余量按车身四角到地图上下边界的纵坐标差计算。负值代表越线。两套跟线规则使用固定高速目标，MPC 根据约束联合调整速度和转向。</p>
        <div class="record-table"><table><thead><tr><th>工况</th><th>记录时长</th><th>最小边界余量</th><th>末帧速度</th></tr></thead><tbody id="mpc-results"></tbody></table></div>
      </section>`;
    const select = root.querySelector<HTMLSelectElement>('#mpc-run')!;
    const slider = root.querySelector<HTMLInputElement>('#mpc-time')!;
    const clock = root.querySelector<HTMLOutputElement>('#mpc-clock')!;
    const button = root.querySelector<HTMLButtonElement>('#mpc-play')!;
    const car = root.querySelector('#mpc-car')!;
    const track = root.querySelector('#mpc-track')!;
    const forecast = root.querySelector('#mpc-forecast')!;
    const old = root.querySelector('#mpc-old')!;
    const metrics = root.querySelector('#mpc-metrics')!;
    const table = root.querySelector<HTMLTableSectionElement>('#mpc-results')!;
    data.views.forEach((run, i) => {
      select.add(new Option(run.label, String(i)));
      const row = table.insertRow();
      [run.label, number(run.metrics.duration)+' s', number(run.metrics.minMargin*100)+' cm', run.metrics.endSpeed.toFixed(3)+' m/s']
        .forEach((value) => { row.insertCell().textContent = value; });
    });
    const selected = () => data.views[Number(select.value)];
    const update = () => {
      const run = selected();
      const index = Math.min(Math.floor(elapsed/data.dt+1e-7), run.states.length-1);
      const [x,y,heading,speed,steer] = run.states[index];
      const [sx,sy] = xy([x,y]);
      car.setAttribute('transform', `translate(${sx} ${sy}) rotate(${-heading*180/Math.PI})`);
      track.setAttribute('points', points(run.states.slice(0,index+1).map(([px,py]) => [px,py])));
      forecast.setAttribute('points', points(run.predictions[index] ?? []));
      const perturbationFrame = run.perturbationTime === null ? -1 : Math.round(run.perturbationTime/data.dt);
      const showOld = perturbationFrame >= 0 && index >= perturbationFrame && index < perturbationFrame + 9;
      old.setAttribute('points', points(showOld ? run.predictions[perturbationFrame-1] : []));
      clock.value = number(index*data.dt)+' s';
      slider.value = String(index*data.dt);
      metrics.innerHTML = `<div><span>当前速度</span><strong>${speed.toFixed(2)} m/s</strong></div>
        <div><span>前轮转角</span><strong>${number(steer*180/Math.PI)}°</strong></div>
        <div><span>求解次数（整次实验）</span><strong>${run.metrics.successfulSolves}</strong></div>`;
    };
    const reset = () => {
      stop(); button.textContent = '播放'; elapsed = 0;
      slider.max = String(selected().metrics.duration); update();
    };
    const tick = (timestamp: number) => {
      if (!playing) return;
      elapsed = Math.min(selected().metrics.duration, elapsed + (timestamp-last)/1000);
      last = timestamp;
      update();
      if (elapsed < selected().metrics.duration) animation = requestAnimationFrame(tick);
      else { stop(); button.textContent = '重播'; }
    };
    select.onchange = reset;
    slider.oninput = () => { stop(); button.textContent = '播放'; elapsed = Number(slider.value); update(); };
    root.querySelector<HTMLButtonElement>('#mpc-reset')!.onclick = reset;
    button.onclick = () => {
      if (playing) { stop(); button.textContent = '播放'; return; }
      if (elapsed >= selected().metrics.duration) elapsed = 0;
      playing = true; button.textContent = '暂停'; last = performance.now();
      animation = requestAnimationFrame(tick);
    };
    reset();
  }).catch(() => {
    if (!request.signal.aborted) root.innerHTML = '<p>第28集实验记录加载失败。<a href="#/lesson/28">返回讲义</a></p>';
  });
  return () => { request.abort(); stop(); };
}
