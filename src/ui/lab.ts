import { World, type SceneKind } from "./scene.ts";
import { ConfigurationMap } from "./cspace.ts";
import {
  searchGrid,
  makeGrid,
  inflate,
  cellKey,
  type GridOptions,
} from "../algorithms/grid.ts";
import { samplePlan } from "../algorithms/sampling.ts";
import {
  armEnvironment,
  spaceEnvironment,
  radians,
  degrees,
} from "../algorithms/environments.ts";
import { trajectoryPlan } from "../algorithms/trajectory.ts";
import { dwaPlan } from "../algorithms/dwa.ts";
import {
  lerp,
  type Frame,
  type Point,
  type Environment,
} from "../algorithms/core.ts";
import type { Lesson } from "../content/catalog.ts";
const $ = <T extends HTMLElement = HTMLElement>(root: HTMLElement, s: string) =>
  root.querySelector<T>(s)!;
const range = (
  name: string,
  label: string,
  min: number,
  max: number,
  value: number,
  step: number,
  unit = "",
) =>
  `<label class="field"><span>${label}<output data-for="${name}">${value}${unit}</output></span><input type="range" name="${name}" min="${min}" max="${max}" value="${value}" step="${step}" data-unit="${unit}"></label>`;
const select = (
  name: string,
  label: string,
  opts: [string, string][],
  value: string,
) =>
  `<label class="field"><span>${label}</span><select name="${name}">${opts.map(([v, l]) => `<option value="${v}" ${v === value ? "selected" : ""}>${l}</option>`).join("")}</select></label>`;
interface Session {
  iterator: Generator<Frame>;
  world: World;
  last?: Frame;
  done: boolean;
  map?: ConfigurationMap;
  metrics: HTMLElement;
  message: HTMLElement;
  plot: HTMLCanvasElement;
  history: { x: number; y: number }[];
}
export function mountLab(root: HTMLElement, lesson: Lesson) {
  const config = lesson.lab === "config",
    sampling = lesson.lab === "sampling",
    trajectory = lesson.lab === "trajectory",
    grid = lesson.lab === "grid",
    dwa = lesson.lab === "dwa" || lesson.lab === "system";
  const algos: [string, string][] = trajectory
    ? [
        ["limited", "限速限加速度"],
        ["stop", "停车转向（速度突变）"],
        ["instant", "瞬间拐弯（不可执行）"],
      ]
    : grid
      ? [
          ["dijkstra", "Dijkstra"],
          ["astar", "A*"],
        ]
      : sampling
        ? [
            ["rrt", "RRT"],
            ["connect", "RRT-Connect"],
            ["star", "RRT*"],
          ]
        : [["dwa", "DWA"]];
  const defaultAlg = trajectory
    ? "limited"
    : lesson.id === "02"
      ? "astar"
      : lesson.id === "08"
        ? "connect"
        : lesson.id === "09"
          ? "star"
          : grid
            ? "dijkstra"
            : sampling
              ? "rrt"
              : "dwa";
  let obstacles = makeGrid(),
    start: Point = [2, 3],
    goal: Point = [27, 18],
    sessions: Session[] = [],
    playing = false,
    timer = 0,
    closed = false;
  root.innerHTML = `<section class="lab-intro"><div><span class="eyebrow">INTERACTIVE LAB / ${lesson.id}</span><h2>${config ? "动一动关节，看一看整条胳膊" : "让算法跑给你看"}</h2><p>${trajectory ? "同一条两米加两米的折线，对照三种时间安排，观察位姿、速度与完成时间。" : config ? "关节角改变的是整条机械臂的配置。拖动滑块，同时观察红色碰撞禁区。" : grid ? "三维展示二维栅格搜索：调参数、编辑地图，比较实际展开过程。" : sampling ? "同一套算法可切换二维关节空间和真正的三维位置空间。" : "在速度动态窗口里生成候选轨迹，预测、筛选、打分，只执行第一小段。"}</p></div><span class="badge live">● ${config ? "三维运动学" : "浏览器内实时计算"}</span></section>
 <div class="lab-toolbar"><button class="button primary" id="run">${config ? "检查整段连接" : "▶ 运行"}</button>${config ? "" : '<button class="button" id="step">单步</button><button class="button" id="finish">计算至预算</button>'}<button class="button" id="reset">↺ 重置实验</button><span class="toolbar-spacer"></span><button class="button quiet" id="pan" aria-pressed="false">拖动平移</button><button class="button quiet" id="camera">重置视角</button><button class="button quiet" id="top">俯视</button><button class="button quiet" id="export">导出结果 ↓</button></div>
 <div class="lab-layout"><div class="lab-main"><div class="worlds" id="worlds"></div><div class="legend"><span><i style="background:#6cdddc"></i>${grid ? "已展开 / 起点" : sampling ? "起点树" : "实际路线"}</span><span><i style="background:#ffb766"></i>${grid ? "待展开 / 终点" : sampling ? "目标 / 目标树" : "障碍 / 引导路线"}</span><span><i style="background:#b9f79f"></i>当前最佳路径</span><span><i style="background:#bc7268"></i>碰撞禁区 / 无效候选</span></div><div class="lab-footnote"><strong>视角操作</strong> 左键旋转 · <b>右键按住拖动平移</b> · 滚轮缩放 · 触屏双指缩放和平移。${trajectory ? "差速小车的参考轨迹回放；姿态与时间同步，不代表真实闭环执行。" : sampling || config ? "机械臂为三维模型，规划变量为两个关节角；空间绕障使用(x,y,z)三个规划变量。" : grid ? "立体画面用于观察，搜索状态仍是(x,y)栅格。" : "仅教学仿真；安全停车不代表通用避障保证。"}</div></div>
 <aside class="parameters"><div class="parameters-heading"><h3>实验参数</h3><span>修改后重新运行</span></div><form id="params" autocomplete="off">
 ${config ? range("q1", "第一关节 θ1", -150, 150, -30, 1, "°") + range("q2", "第二关节 θ2", -150, 150, 90, 1, "°") : select("algorithm", "算法", algos, defaultAlg)}
 ${trajectory ? range("maxSpeed", "最高前进速度", 0.4, 2, 1, 0.1, " m/s") + range("acceleration", "前进加速度上限", 0.2, 1.5, 0.5, 0.1, " m/s²") + range("maxOmega", "最高转速", 15, 90, 45, 5, "°/s") + range("angularAcceleration", "角加速度上限", 30, 180, 90, 10, "°/s²") : ""}
 ${
   sampling
     ? select(
         "scene",
         "规划场景",
         [
           ["arm", "二连杆机械臂 · 关节空间"],
           ["space", "三维空间 · xyz绕障"],
         ],
         "arm",
       )
     : ""
 }
 ${
   grid
     ? select(
         "preset",
         "地图",
         [
           ["office", "办公室"],
           ["maze", "交错窄通道"],
           ["empty", "空白画布"],
         ],
         "office",
       ) +
       select(
         "edit",
         "左键操作",
         [
           ["orbit", "旋转视角"],
           ["paint", "添加 / 移除障碍"],
           ["start", "设置起点"],
           ["goal", "设置终点"],
         ],
         "orbit",
       ) +
       select(
         "diagonal",
         "邻接规则",
         [
           ["no", "四邻接"],
           ["yes", "八邻接（禁止切角）"],
         ],
         "yes",
       ) +
       range("inflation", "障碍膨胀半径", 0, 2, 0, 1, " 格") +
       range("terrain", "棕色区域进入成本", 1, 5, 1, 1) +
       range("heuristic", "A* 启发权重", 0, 2, 1, 0.1)
     : ""
 }
 ${sampling ? `<label class="field"><span>随机种子</span><input type="number" name="seed" min="0" max="4294967295" value="7"></label>` + range("iterations", "采样迭代预算", 100, 3000, 1200, 100) + range("step", "扩展步长", 3, 30, 10, 1, "° / 场景换算") + range("radius", "近邻半径上限", 10, 60, 35, 1, "° / 场景换算") + range("bias", "目标偏置概率", 0, 0.3, 0.05, 0.01) : ""}
 ${sampling || config ? range("obstacle", "圆柱障碍半径", 0.08, 0.3, 0.15, 0.01, " m") : ""}
 ${
   dwa
     ? select(
         "dynamic",
         "障碍场景",
         [
           ["yes", "移动障碍 + 固定障碍"],
           ["no", "只有固定障碍"],
         ],
         "yes",
       ) +
       select(
         "guided",
         "路线引导",
         [
           ["no", "直接朝任务目标"],
           ["yes", "使用参考途经点"],
         ],
         lesson.id === "05" ? "yes" : "no",
       ) +
       range("maxSpeed", "最高前进速度", 0.4, 2, 1.4, 0.1, " m/s") +
       range("horizon", "轨迹预测时域", 1, 4, 2.4, 0.2, " s") +
       range("clearance", "避障评分权重", 0, 2, 0.5, 0.1)
     : ""
 }
 ${config ? "" : range("speed", "播放速度", 1, 20, 6, 1, "×")}
 ${config ? "" : `<label class="check"><input type="checkbox" name="compare"> 开启算法对比</label>${select("second", "对比算法", algos.length > 1 ? algos : [["dwa", "DWA（另一组预测参数）"]], trajectory ? "instant" : grid ? (defaultAlg === "astar" ? "dijkstra" : "astar") : sampling ? (defaultAlg === "connect" ? "rrt" : "connect") : "dwa")}`}
 </form><div class="parameter-note" id="parameter-note">${trajectory ? "路径固定为先向右2米，再向上2米；默认限速限加速度方案总时长10.5秒。对比算法可切换理想化的瞬间拐弯。" : sampling ? "机械臂默认步长10°；三维场景按0.035 m/度换算。近邻半径独立于生成步长。" : grid ? "启发权重为1时，A*使用可采纳的曼哈顿 / 八方向距离。权重大于1不保证最优。" : config ? "红色仅表示当前配置发生碰撞；两端安全并不保证中间安全。" : "对比模式第二组预测时域增加1秒，最高4秒；其余设置相同。"}</div></aside></div>
 <section class="lab-notes"><h3>怎么做一组有意义的实验？</h3><p>${trajectory ? "同一路径，比较瞬间拐弯、停车转向与限加速度方案。默认限制下，第三种方案用时10.5秒。改变速度或加速度，观察时间如何变化；路径没有变化，执行条件却不同。" : sampling ? "固定场景和种子，先比较RRT与RRT-Connect的首次可行解，再观察RRT*最佳成本能否继续下降。这里按采样迭代预算比较，同时列出运动验证次数；它们不是相同耗时的性能基准。" : grid ? "先固定地图、邻接规则和地面成本，对照Dijkstra与启发权重1的A*。比较路径成本和展开节点，而不是只看动画跑得快不快。" : config ? "把θ1固定为−30°，将θ2从90°调到150°。两端均安全，中间约120°发生碰撞。再改变θ1，观察是否能绕开红色区域。" : "先只放固定障碍，再加入移动障碍。增减预测时域和速度，观察候选轨迹、安全筛选与局部停滞。参考途经点用于演示模块交接，不冒充由本实验自动生成的A*输出。"}</p><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/src/algorithms" target="_blank" rel="noopener">查看实验算法源码 ↗</a></section>`;
  const form = $<HTMLFormElement>(root, "#params");
  const value = (name: string) =>
    new FormData(form).get(name)?.toString() ?? "";
  const number = (name: string) => Number(value(name));
  const getKind = (): SceneKind =>
    trajectory
      ? "trajectory"
      : grid
        ? "grid"
        : dwa
          ? "dwa"
          : sampling && value("scene") === "space"
            ? "space"
            : "arm";
  const weights = () => {
    const out = new Map<string, number>();
    for (let x = 15; x < 19; x++)
      for (let y = 2; y < 18; y++) out.set(`${x},${y}`, number("terrain"));
    return out;
  };
  const environment = () =>
    value("scene") === "space"
      ? spaceEnvironment(number("obstacle"))
      : armEnvironment(number("obstacle"));
  const empty = (): Frame => ({
    kind: config ? "sampling" : grid ? "grid" : dwa ? "dwa" : "sampling",
    stats: {
      iterations: 0,
      checks: 0,
      expanded: 0,
      cost: null,
      firstSolution: null,
      status: "准备就绪",
      message: config
        ? "拖动关节角，观察实际姿态与配置空间同步变化。"
        : "点击运行或单步。参数修改会清空旧实验结果。",
    },
    path: [],
  });
  function formatCost(cost: number | null) {
    if (cost === null) return "—";
    return (
      (getKind() === "arm" ? degrees(cost) : cost).toFixed(2) +
      (getKind() === "arm" ? "°" : grid ? "" : " m")
    );
  }
  function metrics(s: Session) {
    const f = s.last ?? empty();
    s.metrics.innerHTML = [
      ["迭代", f.stats.iterations],
      ["展开 / 节点", f.stats.expanded],
      ["验证次数", f.stats.checks],
      ["路径成本", formatCost(f.stats.cost)],
      ["首次解迭代", f.stats.firstSolution ?? "—"],
    ]
      .map(([k, v]) => `<div><span>${k}</span><b>${v}</b></div>`)
      .join("");
    s.message.textContent = `${f.stats.status} · ${f.stats.message}`;
  }
  function plot(s: Session) {
    const c = s.plot.getContext("2d")!,
      w = s.plot.width,
      h = s.plot.height;
    c.clearRect(0, 0, w, h);
    c.fillStyle = "#93aaa9";
    c.font = "11px sans-serif";
    c.fillText(
      dwa || trajectory ? "累计行驶距离 / m" : "截至当前的最佳成本",
      8,
      14,
    );
    if (!s.history.length) {
      c.fillText(trajectory || dwa ? "运行后显示" : "找到路径后显示", 8, 37);
      return;
    }
    const min = Math.min(...s.history.map((v) => v.y)) * 0.95,
      max = Math.max(...s.history.map((v) => v.y)) * 1.05,
      xx = Math.max(1, ...s.history.map((v) => v.x));
    const xy = (x: number, y: number) => [
      35 + (x / xx) * (w - 46),
      h - 18 - ((y - min) / Math.max(0.01, max - min)) * (h - 43),
    ];
    c.strokeStyle = "#b9f79f";
    c.lineWidth = 2;
    c.beginPath();
    s.history.forEach((p, i) => {
      const [x, y] = xy(p.x, p.y);
      if (i) c.lineTo(x, y);
      else c.moveTo(x, y);
    });
    c.stroke();
    const tip = s.history.at(-1)!;
    const [tx, ty] = xy(tip.x, tip.y);
    c.fillStyle = "#b9f79f";
    c.beginPath();
    c.arc(tx, ty, 2.5, 0, Math.PI * 2);
    c.fill();
    c.fillStyle = "#93aaa9";
    c.fillText(max.toFixed(1), 2, 29);
    c.fillText(min.toFixed(1), 2, h - 14);
    c.fillText("迭代 →", w - 45, h - 3);
  }
  function makeIterator(algorithm: string, second: boolean) {
    if (config)
      return (function* () {
        yield empty();
      })();
    if (trajectory)
      return trajectoryPlan({
        mode: algorithm,
        maxSpeed: number("maxSpeed"),
        acceleration: number("acceleration"),
        maxOmega: radians(number("maxOmega")),
        angularAcceleration: radians(number("angularAcceleration")),
      });
    if (grid) {
      const opts: GridOptions = {
        width: 30,
        height: 22,
        start,
        goal,
        obstacles,
        weights: weights(),
        diagonal: value("diagonal") === "yes",
        inflation: number("inflation"),
        heuristicWeight: number("heuristic"),
        algorithm: algorithm as "dijkstra" | "astar",
      };
      return searchGrid(opts);
    }
    if (dwa)
      return dwaPlan({
        dynamic: value("dynamic") === "yes",
        guided: value("guided") === "yes",
        maxSpeed: number("maxSpeed"),
        horizon: Math.min(4, number("horizon") + (second ? 1 : 0)),
        clearanceWeight: number("clearance"),
        steps: 500,
      });
    const env = environment(),
      factor = env.kind === "arm" ? Math.PI / 180 : 0.035;
    return samplePlan({
      algorithm: algorithm as "rrt" | "connect" | "star",
      env,
      seed: number("seed") >>> 0,
      iterations: number("iterations"),
      step: number("step") * factor,
      radius: number("radius") * factor,
      goalBias: number("bias"),
    });
  }
  function updateConfig() {
    const q = [radians(number("q1")), radians(number("q2"))],
      env = environment();
    for (const s of sessions) {
      s.world.armPose(q);
      s.map?.draw(undefined, q);
      const clear = env.clearance(q);
      s.message.textContent = `q = (${number("q1")}°, ${number("q2")}°) · ${clear > 0 ? "当前配置安全" : "当前配置碰撞"} · 最小几何间距 ${clear.toFixed(3)} m`;
      s.last = { ...empty(), current: q };
    }
  }
  function setup() {
    playing = false;
    const ol = form
      .querySelector("input[name=obstacle]")
      ?.closest("label")
      ?.querySelector("span");
    if (ol?.firstChild)
      ol.firstChild.textContent =
        value("scene") === "space" ? "机器人安全半径" : "圆柱障碍半径";
    const pan = $(root, "#pan");
    pan.setAttribute("aria-pressed", "false");
    pan.textContent = "拖动平移";
    $<HTMLButtonElement>(root, "#run").textContent = config
      ? "检查整段连接"
      : "▶ 运行";
    for (const s of sessions) s.world.dispose();
    sessions = [];
    const container = $(root, "#worlds");
    container.innerHTML = "";
    const compare = !config && value("compare") === "on";
    container.classList.toggle("comparison", compare);
    const all = config
      ? ["配置空间"]
      : [value("algorithm"), ...(compare ? [value("second")] : [])];
    all.forEach((algorithm, index) => {
      const name = algos.find((x) => x[0] === algorithm)?.[1] ?? algorithm;
      const card = document.createElement("section");
      card.className = "world-card";
      card.innerHTML = `<div class="world-title"><b>${name}${dwa && index === 1 ? " · 较长预测时域" : ""}</b><span>${getKind() === "space" ? "3D 状态空间" : getKind() === "arm" ? "3D 机械臂" : "3D 场景"}</span></div><div class="viewport"></div>${getKind() === "arm" ? '<details class="configuration" open><summary>配置空间 θ1 × θ2 <small>−150° 至 150°</small></summary><canvas class="cspace" aria-label="二维关节空间地图"></canvas><p>横轴θ1，纵轴θ2向上；红区为碰撞配置。</p></details>' : ""}<div class="metrics"></div><p class="event-message" aria-live="polite"></p><canvas class="cost-plot" width="500" height="90" aria-label="最佳路径成本曲线"></canvas>`;
      container.append(card);
      try {
        const env = environment();
        const world = new World($(card, ".viewport"), {
          kind: getKind(),
          obstacles,
          inflationCells: grid
            ? inflate({ obstacles, inflation: number("inflation") })
            : undefined,
          width: 30,
          height: 22,
          start: trajectory ? [2, 2] : grid ? start : dwa ? [2, 2] : env.start,
          goal: trajectory ? [4, 4] : grid ? goal : dwa ? [17, 11] : env.goal,
          weights: grid ? weights() : undefined,
          obstacleRadius: number("obstacle"),
          dynamic: value("dynamic") === "yes",
          onPick: (q) => {
            if (q[0] < 0 || q[0] >= 30 || q[1] < 0 || q[1] >= 22) return;
            if (value("edit") === "paint") {
              if (cellKey(q) === cellKey(start) || cellKey(q) === cellKey(goal))
                return;
              const k = cellKey(q);
              if (obstacles.has(k)) obstacles.delete(k);
              else obstacles.add(k);
            } else if (value("edit") === "start") {
              start = q;
              obstacles.delete(cellKey(q));
            } else if (value("edit") === "goal") {
              goal = q;
              obstacles.delete(cellKey(q));
            }
            setup();
          },
        });
        const s: Session = {
          iterator: makeIterator(algorithm, index === 1),
          world,
          done: false,
          map:
            getKind() === "arm"
              ? new ConfigurationMap($<HTMLCanvasElement>(card, ".cspace"), env)
              : undefined,
          metrics: $(card, ".metrics"),
          message: $(card, ".event-message"),
          plot: $<HTMLCanvasElement>(card, ".cost-plot"),
          history: [],
        };
        sessions.push(s);
        metrics(s);
        plot(s);
        world.setEdit(grid && value("edit") !== "orbit");
      } catch (e) {
        $(card, ".viewport").innerHTML =
          `<div class="webgl-error"><b>此设备未能启动WebGL</b><p>请启用浏览器硬件加速或更换支持WebGL的浏览器。文章与视频仍可阅读。</p><code>${String(e).replace(/[<>]/g, "")}</code></div>`;
      }
    });
    if (config) updateConfig();
  }
  function step() {
    for (const s of sessions) {
      if (s.done) continue;
      const f = s.iterator.next();
      if (f.done) {
        s.done = true;
        continue;
      }
      s.last = f.value;
      s.world.setFrame(f.value);
      if (s.map) s.map.draw(f.value);
      metrics(s);
      if (f.value.stats.cost !== null) {
        s.history.push({
          x: f.value.stats.iterations,
          y:
            getKind() === "arm"
              ? degrees(f.value.stats.cost)
              : f.value.stats.cost,
        });
        plot(s);
      }
    }
    if (sessions.every((s) => s.done)) stop();
  }
  function stop() {
    playing = false;
    $<HTMLButtonElement>(root, "#run").textContent = "▶ 运行";
  }
  $(root, "#run").onclick = () => {
    if (config) {
      const env = environment(),
        q = [radians(number("q1")), radians(number("q2"))],
        ok = env.edge(env.start, q);
      sessions.forEach(
        (s) =>
          (s.message.textContent = `从起点(−30°,90°)到当前配置的整段连接：${ok ? "通过保守几何验证" : "未通过，不能将端点安全当作整段安全"}。`),
      );
      return;
    }
    if (sessions.every((s) => s.done)) setup();
    playing = !playing;
    $<HTMLButtonElement>(root, "#run").textContent = playing
      ? "Ⅱ 暂停"
      : "▶ 继续";
  };
  const finishButton = root.querySelector<HTMLButtonElement>("#finish");
  if (finishButton)
    finishButton.onclick = () => {
      stop();
      finishButton.disabled = true;
      finishButton.textContent = "计算中…";
      setTimeout(() => {
        if (closed) return;
        try {
          for (const s of sessions) {
            for (const f of s.iterator) {
              s.last = f;
              if (f.stats.cost !== null)
                s.history.push({
                  x: f.stats.iterations,
                  y: getKind() === "arm" ? degrees(f.stats.cost) : f.stats.cost,
                });
            }
            s.done = true;
            if (s.last) {
              s.world.setFrame(s.last);
              s.map?.draw(s.last);
            }
            metrics(s);
            plot(s);
          }
        } finally {
          finishButton.disabled = false;
          finishButton.textContent = "计算至预算";
        }
      }, 0);
    };
  const sb = root.querySelector<HTMLButtonElement>("#step");
  if (sb)
    sb.onclick = () => {
      stop();
      step();
    };
  $(root, "#reset").onclick = setup;
  $(root, "#camera").onclick = () =>
    sessions.forEach((s) => s.world.resetCamera());
  $(root, "#pan").onclick = () => {
    const b = $(root, "#pan"),
      on = b.getAttribute("aria-pressed") !== "true";
    b.setAttribute("aria-pressed", String(on));
    b.textContent = on ? "恢复旋转" : "拖动平移";
    sessions.forEach((s) => s.world.setPanMode(on));
  };
  $(root, "#top").onclick = () => sessions.forEach((s) => s.world.topView());
  $(root, "#export").onclick = () => {
    const data = {
      lesson: lesson.id,
      parameters: Object.fromEntries(new FormData(form)),
      comparisonBudget:
        "sampling iterations; motion-validation calls are reported separately",
      results: sessions.map((s) => ({
        stats: s.last?.stats,
        path: s.last?.path,
        costUnits:
          getKind() === "arm"
            ? "radians"
            : grid
              ? "grid transition cost"
              : "metres",
      })),
    };
    const u = URL.createObjectURL(
      new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = u;
    a.download = `silicon-baby-steps-${lesson.id}-experiment.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(u), 1000);
  };
  form.addEventListener("input", (e) => {
    const input = e.target as HTMLInputElement;
    const output = root.querySelector<HTMLOutputElement>(
      `[data-for="${input.name}"]`,
    );
    if (output) output.value = input.value + (input.dataset.unit ?? "");
    if (config && input.name.startsWith("q")) updateConfig();
  });
  form.addEventListener("change", (e) => {
    const name = (e.target as HTMLInputElement).name;
    if (name === "speed" || (config && name.startsWith("q"))) return;
    if (name === "preset") {
      obstacles =
        value("preset") === "empty" ? new Set() : makeGrid(value("preset"));
      start = [2, 3];
      goal = [27, 18];
    }
    setup();
  });
  const keydown = (e: KeyboardEvent) => {
    if (
      e.code === "Space" &&
      !/INPUT|SELECT|TEXTAREA|BUTTON/.test((e.target as HTMLElement).tagName)
    ) {
      e.preventDefault();
      $(root, "#run").click();
    }
  };
  window.addEventListener("keydown", keydown);
  let last = 0;
  const tick = (now: number) => {
    if (closed) return;
    if (playing && now - last > 70) {
      last = now;
      for (let i = 0; i < Math.max(1, Math.round(number("speed") / 2)); i++)
        step();
    }
    timer = requestAnimationFrame(tick);
  };
  timer = requestAnimationFrame(tick);
  setup();
  // A narrow inspection hook for verifying camera pan and algorithm state in browser QA.
  const inspect = {
    camera: () => sessions.map((s) => s.world.getCameraState()),
    state: () => sessions.map((s) => s.last?.stats),
  };
  Object.assign(window, { __siliconLab: inspect });
  return () => {
    closed = true;
    cancelAnimationFrame(timer);
    window.removeEventListener("keydown", keydown);
    sessions.forEach((s) => s.world.dispose());
    delete (window as unknown as Record<string, unknown>).__siliconLab;
  };
}
