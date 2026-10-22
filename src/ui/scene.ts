import * as T from "three";
import { SVGRenderer } from "three/addons/renderers/SVGRenderer.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { forward, boxes } from "../algorithms/environments.ts";
import { obstaclesAt } from "../algorithms/dwa.ts";
import { distance, lerp, type Point, type Frame } from "../algorithms/core.ts";
export type SceneKind = "grid" | "arm" | "space" | "dwa" | "trajectory";
export interface SceneOptions {
  kind: SceneKind;
  obstacles?: Set<string>;
  inflationCells?: Set<string>;
  weights?: Map<string, number>;
  width?: number;
  height?: number;
  start?: Point;
  goal?: Point;
  obstacleRadius?: number;
  dynamic?: boolean;
  onPick?: (q: Point) => void;
}
const green = 0xb9f79f,
  cyan = 0x6cdddc,
  orange = 0xffb766;
const material = (color: number, metalness = 0.15) =>
  new T.MeshStandardMaterial({ color, roughness: 0.5, metalness });
export class World {
  scene = new T.Scene();
  camera = new T.PerspectiveCamera(42, 1, 0.01, 150);
  renderer: T.WebGLRenderer | SVGRenderer;
  fallback = false;
  controls: OrbitControls;
  root = new T.Group();
  dynamic = new T.Group();
  arm = new T.Group();
  base = new T.Group();
  robot = new T.Group();
  path?: T.Line;
  tree?: T.LineSegments;
  treeB?: T.LineSegments;
  observer: ResizeObserver;
  raf = 0;
  disposed = false;
  current?: Frame;
  playClock = 0;
  follow = true;
  edit = false;
  private lastPath = "";
  private lastRobot = "";
  private stateDots?: T.InstancedMesh;
  private openedDots?: T.InstancedMesh;
  private initialCamera = new T.Vector3();
  private initialTarget = new T.Vector3();
  private meshes: T.Mesh[] = [];
  private marker: T.Mesh;
  private ray = new T.Raycaster();
  private pointer = new T.Vector2();
  private onContext: (e: Event) => void;
  private onPointer: (e: PointerEvent) => void;
  private pointerStart?: [number, number];
  private cStart: (e: PointerEvent) => void;
  constructor(
    public host: HTMLElement,
    public options: SceneOptions,
  ) {
    try {
      this.renderer = new T.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      });
      this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.8));
      this.renderer.setClearColor(0x101f25);
      this.renderer.outputColorSpace = T.SRGBColorSpace;
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = T.PCFSoftShadowMap;
    } catch {
      const svg = new SVGRenderer();
      svg.setQuality("low");
      svg.setPrecision(2);
      svg.setClearColor(new T.Color(0x101f25), 1);
      this.renderer = svg;
      this.fallback = true;
      host.dataset.renderer = "svg";
    }
    host.append(this.renderer.domElement);
    this.renderer.domElement.setAttribute("tabindex", "0");
    this.renderer.domElement.setAttribute(
      "aria-label",
      "三维实验区域：左键旋转，右键拖动平移，滚轮缩放",
    );
    this.scene.fog = new T.Fog(0x101f25, 28, 65);
    this.scene.add(new T.HemisphereLight(0xdaf7ff, 0x324130, 2.8));
    const light = new T.DirectionalLight(0xffedd3, 3.4);
    light.position.set(7, 12, 5);
    light.castShadow = true;
    light.shadow.mapSize.set(1024, 1024);
    light.shadow.camera.left = -12;
    light.shadow.camera.right = 12;
    light.shadow.camera.top = 12;
    light.shadow.camera.bottom = -12;
    if (this.fallback) {
      light.intensity = 0.6;
      this.scene.add(new T.AmbientLight(0xffffff, 0.8));
    }
    this.scene.add(light);
    this.scene.add(this.root, this.dynamic, this.arm, this.base, this.robot);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.09;
    this.controls.enablePan = true;
    this.controls.screenSpacePanning = true;
    this.controls.panSpeed = 1.1;
    this.controls.mouseButtons = {
      LEFT: T.MOUSE.ROTATE,
      MIDDLE: T.MOUSE.DOLLY,
      RIGHT: T.MOUSE.PAN,
    };
    this.controls.touches = { ONE: T.TOUCH.ROTATE, TWO: T.TOUCH.DOLLY_PAN };
    this.controls.minDistance = 0.5;
    this.controls.maxDistance = 60;
    this.controls.maxPolarAngle = Math.PI * 0.495;
    const large = options.kind === "grid" || options.kind === "dwa";
    const size = large ? 35 : 10;
    const floor = new T.Mesh(
      new T.PlaneGeometry(size, size),
      material(0x182a30),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    if (this.fallback) floor.visible = false;
    floor.position.y = -0.03;
    this.base.add(floor);
    const grid = new T.GridHelper(size, large ? 70 : 40, 0x36565a, 0x253c42);
    if (this.fallback)
      grid.material = new T.LineBasicMaterial({ color: 0x29464b });
    grid.position.y = -0.019;
    this.base.add(grid);
    if (options.kind === "arm") {
      this.camera.position.set(3.25, 3.2, 4.5);
      this.controls.target.set(0.15, 0.35, 0.1);
      this.cylinder(
        this.root,
        [0.9, 0.4, 0.5],
        options.obstacleRadius ?? 0.15,
        0.8,
        orange,
      );
      this.armPose(options.start ?? [-Math.PI / 6, Math.PI / 2]);
    }
    if (options.kind === "space") {
      this.camera.position.set(8.4, 6.8, 8.6);
      this.controls.target.set(0, 1.25, 0);
      for (const b of boxes) {
        const m = new T.Mesh(
          new T.BoxGeometry(...(b.size as [number, number, number])),
          material(0x9d7360),
        );
        m.position.fromArray(b.center);
        m.castShadow = true;
        this.root.add(m);
        const e = new T.LineSegments(
          new T.EdgesGeometry(m.geometry),
          new T.LineBasicMaterial({
            color: orange,
            transparent: true,
            opacity: 0.6,
          }),
        );
        e.position.copy(m.position);
        this.root.add(e);
      }
      const border = new T.Box3Helper(
        new T.Box3(
          new T.Vector3(-3.2, 0.25, -3.2),
          new T.Vector3(3.2, 3.5, 3.2),
        ),
        0x355f67,
      );
      this.base.add(border);
    }
    if (options.kind === "grid") {
      this.camera.position.set(13, 16, 15);
      this.controls.target.set(0, 0, 0);
      for (const key of options.obstacles ?? []) {
        const q = key.split(",").map(Number),
          p = this.world(q);
        const m = new T.Mesh(
          new T.BoxGeometry(0.47, 0.75, 0.47),
          material(0x6e7c75),
        );
        m.position.set(p.x, 0.375, p.z);
        m.castShadow = true;
        this.root.add(m);
      }
      for (const key of options.inflationCells ?? []) {
        if (options.obstacles?.has(key)) continue;
        const q = key.split(",").map(Number);
        if (
          q[0] < 0 ||
          q[0] >= (options.width ?? 30) ||
          q[1] < 0 ||
          q[1] >= (options.height ?? 22)
        )
          continue;
        const p = this.world(q),
          mesh = new T.Mesh(
            new T.BoxGeometry(0.48, 0.055, 0.48),
            material(0x426273),
          );
        mesh.position.set(p.x, 0.0275, p.z);
        this.root.add(mesh);
      }
      for (const [k, w] of options.weights ?? []) {
        if (w <= 1) continue;
        const p = this.world(k.split(",").map(Number));
        const m = new T.Mesh(
          new T.BoxGeometry(0.47, 0.025, 0.47),
          material(0x795f3c),
        );
        m.position.set(p.x, 0.015, p.z);
        this.root.add(m);
      }
    }
    if (options.kind === "dwa") {
      this.camera.position.set(16, 17, 19);
      this.controls.target.set(0, 0, 0);
      this.buildRobot();
      this.moveRobot([2, 2, 0.3]);
      this.renderObstacles(0);
    }
    if (options.kind === "trajectory") {
      this.controls.target.set(0, 0.25, 0);
      this.camera.position.set(4, 4.4, 5.3);
      this.buildRobot();
      this.moveRobot([2, 2, 0]);
    }
    this.initialCamera.copy(this.camera.position);
    this.initialTarget.copy(this.controls.target);
    this.marker = new T.Mesh(
      new T.SphereGeometry(
        large
          ? 0.1
          : options.kind === "space"
            ? (options.obstacleRadius ?? 0.15)
            : 0.055,
        16,
        12,
      ),
      material(green),
    );
    this.marker.visible = false;
    this.dynamic.add(this.marker);
    for (const [q, col] of [
      [options.start, cyan],
      [options.goal, orange],
    ] as [Point | undefined, number][]) {
      if (!q) continue;
      const p = this.world(options.kind === "arm" ? forward(q)[2] : q);
      const sphere = new T.Mesh(
        new T.SphereGeometry(large ? 0.13 : 0.065, 20, 16),
        material(col),
      );
      sphere.position.copy(p);
      sphere.position.y += 0.08;
      this.base.add(sphere);
      const ring = new T.Mesh(
        new T.TorusGeometry(large ? 0.22 : 0.115, 0.017, 8, 36),
        new T.MeshBasicMaterial({ color: col }),
      );
      ring.rotation.x = Math.PI / 2;
      ring.position.set(p.x, 0.02, p.z);
      this.base.add(ring);
    }
    this.onContext = (e) => e.preventDefault();
    this.renderer.domElement.addEventListener("contextmenu", this.onContext);
    this.cStart = (e) => {
      if (e.button === 0) this.pointerStart = [e.clientX, e.clientY];
    };
    this.renderer.domElement.addEventListener(
      "pointerdown",
      this.cStart as EventListener,
    );
    this.onPointer = (e) => {
      if (
        e.button !== 0 ||
        !this.edit ||
        !this.pointerStart ||
        Math.hypot(
          e.clientX - this.pointerStart[0],
          e.clientY - this.pointerStart[1],
        ) > 8
      )
        return;
      const r = this.renderer.domElement.getBoundingClientRect();
      this.pointer.set(
        ((e.clientX - r.left) / r.width) * 2 - 1,
        (-(e.clientY - r.top) / r.height) * 2 + 1,
      );
      this.ray.setFromCamera(this.pointer, this.camera);
      const p = this.ray.ray.intersectPlane(
        new T.Plane(new T.Vector3(0, 1, 0), 0),
        new T.Vector3(),
      );
      if (p && options.kind === "grid")
        options.onPick?.([
          Math.floor(p.x / 0.5 + (options.width ?? 30) / 2),
          Math.floor(p.z / 0.5 + (options.height ?? 22) / 2),
        ]);
    };
    this.renderer.domElement.addEventListener(
      "pointerup",
      this.onPointer as EventListener,
    );
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(host);
    this.resize();
    let last = performance.now();
    const draw = (now: number) => {
      if (this.disposed) return;
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      this.playClock += dt;
      if (
        this.current?.path.length &&
        this.follow &&
        (options.kind === "arm" || options.kind === "space")
      ) {
        const path = this.current.path;
        const len = pathCostQuick(path);
        let travel =
            (this.playClock * (options.kind === "space" ? 1 : 0.22)) %
            Math.max(0.01, len),
          q = path[0];
        for (let i = 1; i < path.length; i++) {
          const dist = distance(path[i - 1], path[i]);
          if (travel <= dist) {
            q = lerp(path[i - 1], path[i], travel / Math.max(dist, 1e-9));
            break;
          }
          travel -= dist;
          q = path[i];
        }
        if (options.kind === "arm") this.armPose(q);
        else {
          this.marker.position.copy(this.world(q));
          this.marker.visible = true;
        }
      }
      this.controls.update();
      this.host.dataset.cameraTarget = this.controls.target
        .toArray()
        .map((x) => x.toFixed(4))
        .join(",");
      this.renderer.render(this.scene, this.camera);
      this.raf = requestAnimationFrame(draw);
    };
    this.raf = requestAnimationFrame(draw);
  }
  world(q: Point) {
    if (this.options.kind === "space") return new T.Vector3(q[0], q[1], q[2]);
    if (this.options.kind === "arm") return new T.Vector3(q[0], 0.2, q[1]);
    if (this.options.kind === "trajectory")
      return new T.Vector3(q[0] - 3, 0.13, q[1] - 3);
    if (this.options.kind === "dwa")
      return new T.Vector3(q[0] - 10, 0.13, q[1] - 7);
    return new T.Vector3(
      (q[0] + 0.5 - (this.options.width ?? 30) / 2) * 0.5,
      0.08,
      (q[1] + 0.5 - (this.options.height ?? 22) / 2) * 0.5,
    );
  }
  resize() {
    const w = Math.max(1, this.host.clientWidth),
      h = Math.max(1, this.host.clientHeight);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
  }
  setPanMode(v: boolean) {
    this.controls.mouseButtons.LEFT = v
      ? T.MOUSE.PAN
      : this.edit
        ? null
        : T.MOUSE.ROTATE;
    this.renderer.domElement.style.cursor = v
      ? "move"
      : this.edit
        ? "crosshair"
        : "grab";
  }
  resetCamera() {
    this.camera.position.copy(this.initialCamera);
    this.controls.target.copy(this.initialTarget);
    this.controls.update();
  }
  topView() {
    this.camera.position
      .copy(this.initialTarget)
      .add(new T.Vector3(0.01, this.options.kind === "arm" ? 6 : 20, 0.01));
    this.controls.target.copy(this.initialTarget);
    this.controls.update();
  }
  setEdit(v: boolean) {
    this.edit = v;
    this.controls.mouseButtons.LEFT = v ? null : T.MOUSE.ROTATE;
    this.renderer.domElement.style.cursor = v ? "crosshair" : "grab";
  }
  clearGroup(group: T.Group) {
    for (const c of [...group.children]) {
      group.remove(c);
      c.traverse((o) => {
        const m = o as T.Mesh;
        if (m.geometry) m.geometry.dispose();
        if (m.material) {
          const a = Array.isArray(m.material) ? m.material : [m.material];
          a.forEach((x) => x.dispose());
        }
      });
    }
  }
  cylinder(parent: T.Group, pos: Point, r: number, h: number, color: number) {
    const m = new T.Mesh(new T.CylinderGeometry(r, r, h, 32), material(color));
    m.position.fromArray(pos);
    m.castShadow = true;
    parent.add(m);
    return m;
  }
  armPose(q: Point) {
    const hash = q.map((v) => v.toFixed(4)).join();
    if (hash === this.lastRobot) return;
    this.lastRobot = hash;
    if (!this.meshes.length) {
      this.cylinder(this.arm, [0, 0.11, 0], 0.14, 0.22, 0x728c91);
      for (let i = 0; i < 2; i++) {
        const m = new T.Mesh(
          new T.CylinderGeometry(0.05, 0.05, 1, 16),
          material(i ? 0xd6b088 : 0x72aeb2),
        );
        m.castShadow = true;
        this.arm.add(m);
        this.meshes.push(m);
      }
      for (let i = 0; i < 3; i++) {
        const m = new T.Mesh(
          new T.SphereGeometry(0.075, 16, 12),
          material(i === 2 ? orange : 0x92d3d0),
        );
        this.arm.add(m);
        this.meshes.push(m);
      }
    }
    const p = forward(q).map((v) => new T.Vector3(v[0], 0.22, v[1]));
    for (let i = 0; i < 2; i++) {
      const a = p[i],
        b = p[i + 1];
      this.meshes[i].position.copy(a).add(b).multiplyScalar(0.5);
      this.meshes[i].quaternion.setFromUnitVectors(
        new T.Vector3(0, 1, 0),
        b.clone().sub(a).normalize(),
      );
    }
    for (let i = 0; i < 3; i++) this.meshes[2 + i].position.copy(p[i]);
  }
  buildRobot() {
    const body = new T.Mesh(
      new T.CylinderGeometry(0.27, 0.27, 0.26, 24),
      material(0xb3e6c2),
    );
    body.position.y = 0.22;
    this.robot.add(body);
    const visor = new T.Mesh(
      new T.BoxGeometry(0.32, 0.12, 0.15),
      material(0x183c43),
    );
    visor.position.set(0.18, 0.31, 0);
    this.robot.add(visor);
    const dir = new T.ArrowHelper(
      new T.Vector3(1, 0, 0),
      new T.Vector3(0, 0.12, 0),
      0.65,
      green,
      0.2,
      0.14,
    );
    this.robot.add(dir);
  }
  moveRobot(q: Point) {
    const p = this.world(q);
    this.robot.position.set(p.x, 0, p.z);
    this.robot.rotation.y = -q[2];
  }
  renderObstacles(t: number) {
    this.clearGroup(this.root);
    const obs = obstaclesAt(t, !!this.options.dynamic);
    for (const [index, ob] of obs.entries()) {
      const p = this.world(ob.p);
      this.cylinder(
        this.root,
        [p.x, 0.5, p.z],
        ob.r,
        1,
        this.options.dynamic && index === obs.length - 1 ? orange : 0xba8863,
      );
    }
  }
  line(points: Point[], color: number, group = this.dynamic, opacity = 1) {
    if (points.length < 2) return undefined;
    const geom = new T.BufferGeometry().setFromPoints(
      points.map((q) => this.world(q)),
    );
    const line = new T.Line(
      geom,
      new T.LineBasicMaterial({
        color,
        linewidth: color === green ? 3 : 1,
        transparent: opacity < 1,
        opacity,
      }),
    );
    group.add(line);
    return line;
  }
  treeLine(nodes: Point[], parents: number[], color: number) {
    const points: T.Vector3[] = [];
    parents.forEach((p, i) => {
      if (p >= 0 && nodes[i] && nodes[p])
        points.push(this.world(nodes[p]), this.world(nodes[i]));
    });
    const line = new T.LineSegments(
      new T.BufferGeometry().setFromPoints(points),
      new T.LineBasicMaterial({ color, transparent: true, opacity: 0.6 }),
    );
    this.dynamic.add(line);
    return line;
  }
  setFrame(f: Frame) {
    this.current = f;
    // Remove only transient overlays; leave the animated robot/model intact.
    for (const c of [...this.dynamic.children]) {
      if (c === this.marker) continue;
      this.dynamic.remove(c);
      const m = c as T.Mesh;
      m.geometry?.dispose();
      if (m.material)
        (Array.isArray(m.material) ? m.material : [m.material]).forEach((v) =>
          v.dispose(),
        );
    }
    if (this.options.kind === "grid") {
      const draw = (cells: Point[], color: number, opacity: number) => {
        if (!cells.length) return;
        if (this.fallback) {
          const vertices: number[] = [];
          for (const q of cells) {
            const p = this.world(q),
              x = p.x,
              z = p.z,
              r = 0.215;
            vertices.push(
              x - r,
              0.03,
              z - r,
              x + r,
              0.03,
              z - r,
              x + r,
              0.03,
              z + r,
              x - r,
              0.03,
              z - r,
              x + r,
              0.03,
              z + r,
              x - r,
              0.03,
              z + r,
            );
          }
          const g = new T.BufferGeometry();
          g.setAttribute("position", new T.Float32BufferAttribute(vertices, 3));
          this.dynamic.add(
            new T.Mesh(
              g,
              new T.MeshBasicMaterial({
                color,
                side: T.DoubleSide,
                transparent: true,
                opacity,
              }),
            ),
          );
        } else {
          const mesh = new T.InstancedMesh(
            new T.BoxGeometry(0.43, 0.035, 0.43),
            new T.MeshBasicMaterial({ color, transparent: true, opacity }),
            cells.length,
          );
          const matrix = new T.Matrix4();
          cells.forEach((q, i) => {
            const p = this.world(q);
            matrix.makeTranslation(p.x, 0.035, p.z);
            mesh.setMatrixAt(i, matrix);
          });
          this.dynamic.add(mesh);
        }
      };
      draw(f.closed ?? [], 0x77c2ae, 0.5);
      draw(f.open ?? [], 0xffbd70, 0.75);
      this.line(f.path, green);
      if (f.current) {
        this.marker.position.copy(this.world(f.current));
        this.marker.visible = true;
      }
    } else if (this.options.kind === "space") {
      if (f.nodes && f.parents) this.treeLine(f.nodes, f.parents, cyan);
      if (f.secondNodes && f.secondParents)
        this.treeLine(f.secondNodes, f.secondParents, orange);
      this.line(f.path, green);
      if (!f.path.length && f.candidate) {
        this.marker.position.copy(this.world(f.candidate));
        this.marker.visible = true;
        (this.marker.material as T.MeshStandardMaterial).color.set(
          f.accepted ? green : 0xe7766e,
        );
      }
    } else if (this.options.kind === "arm") {
      if (!f.path.length && f.candidate) this.armPose(f.candidate);
    } else {
      if (this.options.kind === "dwa")
        this.renderObstacles((f.stats.iterations - 1) * 0.15);
      for (const p of f.trajectories ?? [])
        this.line(p, 0x54868a, this.dynamic, 0.27);
      if (f.route) this.line(f.route, orange, this.dynamic, 0.75);
      if (f.chosen) this.line(f.chosen, green);
      this.line(f.path, cyan);
      if (f.robot) this.moveRobot(f.robot);
    }
  }
  getCameraState() {
    return {
      position: this.camera.position.toArray(),
      target: this.controls.target.toArray(),
    };
  }
  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.observer.disconnect();
    this.controls.dispose();
    this.renderer.domElement.removeEventListener("contextmenu", this.onContext);
    this.renderer.domElement.removeEventListener(
      "pointerdown",
      this.cStart as EventListener,
    );
    this.renderer.domElement.removeEventListener(
      "pointerup",
      this.onPointer as EventListener,
    );
    this.scene.traverse((o) => {
      const m = o as T.Mesh;
      m.geometry?.dispose();
      if (m.material)
        (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) =>
          x.dispose(),
        );
    });
    if (this.renderer instanceof T.WebGLRenderer) this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
function pathCostQuick(p: Point[]) {
  return p.slice(1).reduce((s, q, i) => s + distance(p[i], q), 0);
}
