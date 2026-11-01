import "./styles.css";
import { marked } from "marked";
import { lessons, roadmap, asset, type Lesson } from "./content/catalog.ts";
import { mountLab } from "./ui/lab.ts";
import { World } from "./ui/scene.ts";
import { armEnvironment } from "./algorithms/environments.ts";
import { samplePlan } from "./algorithms/sampling.ts";
const app = document.querySelector<HTMLElement>("#app")!;
let cleanup: (() => void) | undefined;
let routeToken = 0;
const escape = (s: string) =>
  s.replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
const visited = new Set<string>(
  JSON.parse(localStorage.getItem("silicon-learned") ?? "[]"),
);
function sidebar(active = "home") {
  return `<aside class="sidebar"><a class="brand" href="#/"><span class="brand-mark">硅</span><span>硅基学步<small>SILICON BABY STEPS</small></span></a><div class="brand-caption">碳硅共鸣 · 规划算法工程师的练级地图</div><nav aria-label="主导航"><a class="nav-link ${active === "home" ? "active" : ""}" href="#/"><span>◈</span> 课程总览 <small>09</small></a><a class="nav-link ${active === "roadmap" ? "active" : ""}" href="#/roadmap"><span>◎</span> 完整学习路线 <small>9 部分</small></a><a class="nav-link ${active === "experiments" ? "active" : ""}" href="#/experiments"><span>⌘</span> 算法实验室 <small>3D</small></a><a class="nav-link ${active === "about" ? "active" : ""}" href="#/about"><span>✦</span> 认识硅宝 <small>001</small></a><div class="nav-divider"></div>${[
    1, 2,
  ]
    .map(
      (p) =>
        `<p class="nav-section">0${p} / ${p === 1 ? "硅宝第一次出门" : "机械臂与采样规划"}</p>${lessons
          .filter((l) => l.part === p)
          .map(
            (l) =>
              `<a class="chapter-link ${active === l.id ? "active" : ""}" href="#/lesson/${l.id}"><span>${l.id}</span><b>${escape(l.algorithm)}</b><i>${visited.has(l.id) ? "✓" : "↗"}</i></a>`,
          )
          .join("")}`,
    )
    .join(
      "",
    )}</nav><div class="sidebar-bottom"><div class="avatar-dot">001</div><div><strong>硅宝正在陪你练级</strong><small>先跑明白，再谈优化。</small></div><a aria-label="查看GitHub仓库" href="https://github.com/luckyPT/silicon-baby-steps" target="_blank" rel="noopener">↗</a></div></aside>`;
}
function shell(content: string, active: string, bread: string) {
  app.innerHTML = `${sidebar(active)}<div class="site-body"><header class="topbar"><button class="menu-toggle" aria-label="打开课程目录">☰</button><div class="breadcrumb">工作台 <span>/</span> ${bread}</div><div class="topbar-right"><span class="status-dot"></span><span>持续生长的开源课程</span><a class="github-link" href="https://github.com/luckyPT/silicon-baby-steps" target="_blank" rel="noopener">GitHub ↗</a></div></header><main id="main">${content}</main><footer>碳硅共鸣 × 硅宝 001 <span>思路要清楚，算法要跑得出来。</span><a href="https://github.com/luckyPT/silicon-baby-steps" target="_blank" rel="noopener">一起完善这门课 ↗</a></footer></div>`;
  document
    .querySelector(".menu-toggle")
    ?.addEventListener("click", () =>
      document.body.classList.toggle("nav-open"),
    );
  document
    .querySelectorAll(".sidebar a")
    .forEach((a) =>
      a.addEventListener("click", () =>
        document.body.classList.remove("nav-open"),
      ),
    );
}
function card(l: Lesson) {
  return `<a class="lesson-card" href="#/lesson/${l.id}"><div class="card-image"><img src="${asset(`media/${l.id}/cover.jpg`)}" alt="第${Number(l.id)}集封面" loading="lazy"><span class="card-number">LESSON ${l.id}</span><span class="card-duration" data-duration="${l.id}">${l.duration || "完整视频"}</span></div><div class="card-copy"><div class="card-meta"><span>${escape(l.algorithm)}</span><span>文章 / 视频 / 实验</span></div><h3>${escape(l.title)}</h3><p>${escape(l.subtitle)}</p><div class="card-tags">${l.concepts.map((c) => `<span>${c}</span>`).join("")}</div><div class="card-bottom"><span>${visited.has(l.id) ? "✓ 已完成学习" : "开始本节练习"}</span><b>↗</b></div></div></a>`;
}
async function home() {
  shell(
    `<section class="hero"><div class="hero-copy"><div class="eyebrow"><span class="pill-dot"></span> LEARN. SIMULATE. UNDERSTAND.</div><h1>规划这件事，<br>从<span>迈出第一步</span>开始。</h1><p>和硅宝一起，把地图上的一条线，<br>变成机器人真正能走的路。</p><div class="hero-actions"><a class="button primary large" href="#/lesson/01">从第一课开始 <span>↗</span></a><a class="text-link" href="#/experiments">直接进入实验室 →</a></div><div class="hero-stats"><div><strong>09</strong><span>集完整课程</span></div><div><strong>06</strong><span>核心算法与模型</span></div><div><strong>3D</strong><span>可交互实验场景</span></div></div></div><div class="hero-scene" id="hero-scene"><div class="scene-topline"><span>LIVE LAB / 002</span><span>关节空间 → 真实姿态</span></div><div class="hero-view" id="hero-world"></div><div class="scene-bottomline"><span><i></i> RRT* · 机械臂绕障</span><small>右键拖动平移视角</small></div><div class="coordinate-label">q = (θ1, θ2)<br><small>两根连杆，一整个世界。</small></div></div></section><section class="course-section"><div class="section-heading"><div><span class="eyebrow">YOUR LEARNING PATH</span><h2>课程目录 <small>把每一个“为什么”跑出来</small></h2></div><a class="text-link" href="#/roadmap">查看完整路线 ↗</a></div><div class="course-filters"><button class="filter active" data-filter="all">全部章节 <b>9</b></button><button class="filter" data-filter="1">01 移动机器人入门</button><button class="filter" data-filter="2">02 机械臂与采样规划</button><label class="search"><span>⌕</span><input id="search" type="search" placeholder="搜索算法或关键词" aria-label="搜索课程"></label></div><div class="cards-grid" id="cards">${lessons.map(card).join("")}</div><p id="empty-search" hidden>没有匹配的章节，试试 A*、机械臂或采样。</p></section><section class="next-banner"><div><span class="eyebrow">COMING NEXT</span><h3>已经找到路，采样能不能更聪明？</h3><p>下一集 Informed RRT*：把力气花在有机会改进路径的区域。</p></div><span class="next-graphic">RRT<span>*</span><small>→ INFORMED</small></span></section>`,
    "home",
    "课程总览",
  );
  let filter = "all";
  const update = () => {
    const q = (
      document.querySelector<HTMLInputElement>("#search")?.value ?? ""
    ).toLowerCase();
    const found = lessons.filter(
      (l) =>
        (filter === "all" || String(l.part) === filter) &&
        `${l.title} ${l.algorithm} ${l.concepts.join(" ")}`
          .toLowerCase()
          .includes(q),
    );
    document.querySelector("#cards")!.innerHTML = found.map(card).join("");
    (document.querySelector("#empty-search") as HTMLElement).hidden =
      !!found.length;
  };
  document.querySelectorAll<HTMLButtonElement>("[data-filter]").forEach(
    (b) =>
      (b.onclick = () => {
        filter = b.dataset.filter!;
        document
          .querySelectorAll("[data-filter]")
          .forEach((x) => x.classList.toggle("active", x === b));
        update();
      }),
  );
  document.querySelector("#search")?.addEventListener("input", update);
  try {
    const env = armEnvironment(),
      world = new World(document.querySelector("#hero-world")!, {
        kind: "arm",
        start: env.start,
        goal: env.goal,
        obstacleRadius: 0.15,
      });
    let last;
    for (const f of samplePlan({
      algorithm: "star",
      env,
      seed: 7,
      iterations: 700,
      step: Math.PI / 18,
      radius: (Math.PI * 35) / 180,
      goalBias: 0.05,
    }))
      last = f;
    if (last) world.setFrame(last);
    cleanup = () => world.dispose();
  } catch {
    document.querySelector("#hero-world")!.innerHTML =
      '<p class="hero-fallback">文章 + 视频 + 可复现实验<br>从 Dijkstra 到 RRT*</p>';
  }
  loadDurations();
}
function roadmapPage() {
  shell(
    `<section class="page-heading"><span class="eyebrow">THE BIG PICTURE</span><h1>全局路线，逐步练级。</h1><p>保留最初的九部分知识体系。视频按当前更新顺序推进：前期优先规划，控制集中在后段。</p></section><div class="callout"><b>知识体系与视频集数是两种目录。</b><p>当前视频第一部分已在第05集收官；第二部分从第06集开始，提前引入机械臂配置空间与采样规划。下方是长期知识路线，不把未制作的章节标成已经完成。</p></div><div class="roadmap-list">${roadmap.map((p, i) => `<section class="roadmap-item"><span class="roadmap-number">${String(i + 1).padStart(2, "0")}</span><div><span class="badge">${p.status}</span><h2>${p.title}</h2><p>${p.topics}</p><div class="practice">${p.practice}</div></div></section>`).join("")}</div>`,
    "roadmap",
    "完整学习路线",
  );
}
function experimentsPage() {
  shell(
    `<section class="page-heading"><span class="eyebrow">THE ALGORITHM PLAYGROUND</span><h1>别只看算法，<span>亲手改变结果。</span></h1><p>调节参数、观察树生长、切换算法，看看它为什么成功，又为什么卡住。</p></section><div class="experiment-grid">${[
      {
        id: "02",
        n: "01",
        title: "栅格搜索实验室",
        text: "Dijkstra / A*，三维地图展示、障碍编辑、启发权重与同场景对比。",
        tag: "搜索与最优性",
      },
      {
        id: "04",
        n: "02",
        title: "动态窗口实验室",
        text: "改变速度、预测时域和评分权重，看候选轨迹与移动障碍。",
        tag: "动态局部规划",
      },
      {
        id: "06",
        n: "03",
        title: "机械臂配置空间",
        text: "拖动两个关节，让真实姿态与配置空间中的一个点同时变化。",
        tag: "运动学与检碰",
      },
      {
        id: "09",
        n: "04",
        title: "采样规划实验室",
        text: "RRT / RRT-Connect / RRT*。机械臂与三维空间绕障，固定种子做对照。",
        tag: "高维空间与路径优化",
      },
    ]
      .map(
        (l) =>
          `<a class="experiment-card" href="#/lesson/${l.id}/lab"><span class="experiment-index">${l.n} / LAB</span><div class="experiment-art">${l.n === "01" ? "▦" : l.n === "02" ? "◉" : l.n === "03" ? "⌁" : "⤴"}</div><span class="badge">${l.tag}</span><h2>${l.title}</h2><p>${l.text}</p><strong>打开实验 ↗</strong></a>`,
      )
      .join(
        "",
      )}</div><div class="callout"><b>右键平移已统一为默认操作</b><p>左键旋转，右键按住拖动平移，滚轮缩放；触屏双指缩放和平移。编辑地图时左键负责绘制，右键仍然平移。每个视图都有“重置视角”和“俯视”。</p></div>`,
    "experiments",
    "算法实验室",
  );
}
function aboutPage() {
  shell(
    `<section class="page-heading"><span class="eyebrow">MEET YOUR PLANNING PARTNER</span><h1>你好，我是<span>硅宝。</span></h1><p>碳硅共鸣的001号员工，专注规划算法。我就在《硅基学步》项目，跟大家一起练级。</p></section><section class="video-section"><div class="video-label"><span>硅宝的第一次见面</span><small>原始自我介绍视频</small></div><video controls preload="metadata" playsinline poster="${asset("media/00/cover.jpg")}"><source src="${asset("media/00/video.mp4")}" type="video/mp4"></video><div class="video-bottom"><span>算法可以很严谨，讲算法的人可以有点幽默。</span><a href="${asset("media/00/video.mp4")}" download>下载视频 ↓</a></div></section><div class="callout"><b>我负责种树、算账，偶尔撞上老板的需求。</b><p>这门课把文章、视频和可调参数的实验放在一起。你可以先听我讲一遍，再自己动手试：同一张地图，为什么A*展开得更少？同一台机械臂，为什么RRT*能继续省路？</p><p><a href="#/lesson/01">从第一课开始 →</a></p></div>`,
    "about",
    "认识硅宝",
  );
}
async function lessonPage(id: string, tab: string, token: number) {
  const l = lessons.find((x) => x.id === id);
  if (!l) {
    shell(
      '<section class="page-heading"><h1>这节课还没长出来。</h1><a href="#/">回到课程目录 →</a></section>',
      "home",
      "未找到章节",
    );
    return;
  }
  shell(
    `<section class="lesson-heading"><div><span class="eyebrow">PART 0${l.part} / LESSON ${l.id}</span><h1>${escape(l.title)}</h1><p>${escape(l.subtitle)}</p></div><a class="button quiet" href="#/">全部章节 ↗</a></section><div class="lesson-tabs"><a href="#/lesson/${id}" class="${tab !== "lab" ? "active" : ""}">课程文章与视频</a><a href="#/lesson/${id}/lab" class="${tab === "lab" ? "active" : ""}">交互实验室 <span>3D</span></a><a href="https://github.com/luckyPT/silicon-baby-steps/tree/main/src/algorithms" target="_blank" rel="noopener">算法代码 ↗</a></div><div id="lesson-content"></div>`,
    id,
    `第${Number(id)}集 · ${l.algorithm}`,
  );
  const content = document.querySelector<HTMLElement>("#lesson-content")!;
  if (tab === "lab") {
    cleanup = mountLab(content, l);
    return;
  }
  content.innerHTML = `<section class="video-section"><div class="video-label"><span><i class="pill-dot"></i> 本节完整视频</span><small>硅宝讲解 / 中文配音 / 中文字幕</small></div><video controls preload="metadata" playsinline poster="${asset(`media/${id}/cover.jpg`)}" aria-label="第${Number(id)}集视频"><source src="${asset(`media/${id}/video.mp4`)}" type="video/mp4">你的浏览器无法播放此视频，请下载后播放。</video><div class="video-bottom"><span>先看一遍，再到实验室改一改参数。</span><a href="${asset(`media/${id}/video.mp4`)}" download>下载 MP4 ↓</a></div><p id="video-error" hidden>视频加载失败。请确认已完整克隆仓库中的 public/media 目录，或直接下载本节MP4。</p></section><div class="reading-layout"><article class="article" id="article"><p>正在打开本节讲义…</p></article><aside class="reading-aside"><div class="reading-toc"><span class="eyebrow">IN THIS CHAPTER</span><nav id="toc" aria-label="本节内容索引"></nav></div><div class="reading-lab"><b>读懂了，去跑一遍。</b><p>${l.concepts.join(" · ")}</p><a class="button primary" href="#/lesson/${id}/lab">打开交互实验 ↗</a></div></aside></div><div class="chapter-pagination">${Number(id) > 1 ? `<a href="#/lesson/${String(Number(id) - 1).padStart(2, "0")}">← 上一集</a>` : "<span>从这里出发</span>"}<button class="button" id="learned">${visited.has(id) ? "✓ 已完成本节" : "标记本节已学完"}</button>${Number(id) < 9 ? `<a href="#/lesson/${String(Number(id) + 1).padStart(2, "0")}">下一集 →</a>` : "<span>下一集：Informed RRT*</span>"}</div>`;
  content.querySelector("video")?.addEventListener("error", () => {
    (document.querySelector("#video-error") as HTMLElement).hidden = false;
  });
  content.querySelector("source")?.addEventListener("error", () => {
    const el = document.querySelector<HTMLElement>("#video-error");
    if (el) el.hidden = false;
  });
  document.querySelector<HTMLButtonElement>("#learned")!.onclick = () => {
    visited.add(id);
    localStorage.setItem("silicon-learned", JSON.stringify([...visited]));
    document.querySelector("#learned")!.textContent = "✓ 已完成本节";
  };
  try {
    const response = await fetch(asset(`articles/${id}.md`));
    if (!response.ok) throw Error("讲义文件未找到");
    const source = await response.text();
    if (routeToken !== token) return;
    document.querySelector("#article")!.innerHTML = await marked.parse(
      source.replace(/\]\(\.\.\/media\//g, `](${asset("media/")}`),
    );
    const headings =
      document.querySelectorAll<HTMLHeadingElement>("#article h2");
    document.querySelector("#toc")!.innerHTML = [...headings]
      .map((h, i) => {
        h.id = `section-${i}`;
        return `<a href="#/lesson/${id}" data-scroll="${h.id}">${escape(h.textContent ?? "")}</a>`;
      })
      .join("");
    document.querySelectorAll<HTMLAnchorElement>("[data-scroll]").forEach(
      (a) =>
        (a.onclick = (e) => {
          e.preventDefault();
          document
            .getElementById(a.dataset.scroll!)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
        }),
    );
    document
      .querySelectorAll<HTMLImageElement>("#article img")
      .forEach((im) => {
        im.loading = "lazy";
        im.decoding = "async";
      });
  } catch (e) {
    if (routeToken === token)
      document.querySelector("#article")!.innerHTML =
        `<p>讲义未能加载：${escape(String(e))}。请刷新重试。</p>`;
  }
}
async function loadDurations() {
  try {
    const data = await fetch(asset("media/manifest.json")).then((r) =>
      r.json(),
    );
    for (const l of lessons) {
      const d = data.chapters.find(
        (x: { id: string }) => x.id === l.id,
      )?.durationSeconds;
      if (d) {
        l.duration = `${Math.floor(d / 60)}:${String(Math.round(d % 60)).padStart(2, "0")}`;
        document
          .querySelectorAll(`[data-duration="${l.id}"]`)
          .forEach((el) => (el.textContent = l.duration));
      }
    }
  } catch {
    /* Full video remains available without duration labels. */
  }
}
async function route() {
  routeToken++;
  const token = routeToken;
  cleanup?.();
  cleanup = undefined;
  document.body.classList.remove("nav-open");
  const p = location.hash.replace(/^#\/?/, "").split("/");
  window.scrollTo(0, 0);
  if (p[0] === "lesson") await lessonPage(p[1], p[2] ?? "article", token);
  else if (p[0] === "about") aboutPage();
  else if (p[0] === "roadmap") roadmapPage();
  else if (p[0] === "experiments") experimentsPage();
  else await home();
}
window.addEventListener("hashchange", route);
void route();
