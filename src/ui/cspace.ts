import { degrees } from "../algorithms/environments.ts";
import type { Environment, Frame, Point } from "../algorithms/core.ts";
export class ConfigurationMap {
  ctx: CanvasRenderingContext2D;
  background: ImageData;
  size = 260;
  constructor(
    public canvas: HTMLCanvasElement,
    public env: Environment,
  ) {
    canvas.width = canvas.height = this.size;
    this.ctx = canvas.getContext("2d")!;
    this.background = this.ctx.createImageData(this.size, this.size);
    for (let y = 0; y < this.size; y++)
      for (let x = 0; x < this.size; x++) {
        const q = [
          env.bounds[0][0] +
            (x / (this.size - 1)) * (env.bounds[0][1] - env.bounds[0][0]),
          env.bounds[1][1] -
            (y / (this.size - 1)) * (env.bounds[1][1] - env.bounds[1][0]),
        ];
        const bad = env.clearance(q) <= 0;
        const i = (y * this.size + x) * 4;
        this.background.data.set(
          bad ? [113, 57, 58, 255] : [19, 41, 48, 255],
          i,
        );
      }
    this.draw();
  }
  xy(q: Point) {
    return [
      ((q[0] - this.env.bounds[0][0]) /
        (this.env.bounds[0][1] - this.env.bounds[0][0])) *
        (this.size - 1),
      ((this.env.bounds[1][1] - q[1]) /
        (this.env.bounds[1][1] - this.env.bounds[1][0])) *
        (this.size - 1),
    ];
  }
  draw(frame?: Frame, q?: Point) {
    const c = this.ctx;
    c.putImageData(this.background, 0, 0);
    c.strokeStyle = "#2e4750";
    c.lineWidth = 1;
    for (let i = 1; i < 6; i++) {
      c.beginPath();
      c.moveTo((i * this.size) / 6, 0);
      c.lineTo((i * this.size) / 6, this.size);
      c.moveTo(0, (i * this.size) / 6);
      c.lineTo(this.size, (i * this.size) / 6);
      c.stroke();
    }
    if(frame?.informedBound){
      const a=frame.informedBound/2,start=this.env.start,goal=this.env.goal,d=Math.hypot(...goal.map((v,i)=>v-start[i])),b=Math.sqrt(Math.max(0,frame.informedBound**2-d*d))/2,angle=Math.atan2(goal[1]-start[1],goal[0]-start[0]);
      c.beginPath();for(let i=0;i<=128;i++){const t=i/128*2*Math.PI,x=a*Math.cos(t),y=b*Math.sin(t),p=this.xy([(start[0]+goal[0])/2+x*Math.cos(angle)-y*Math.sin(angle),(start[1]+goal[1])/2+x*Math.sin(angle)+y*Math.cos(angle)]);if(i)c.lineTo(p[0],p[1]);else c.moveTo(p[0],p[1]);}
      c.closePath();c.fillStyle="#ffb76616";c.fill();c.strokeStyle="#ffb766";c.lineWidth=1.5;c.stroke();
    }
    const tree = (nodes: Point[], parents: number[], color: string) => {
      c.strokeStyle = color;
      c.lineWidth = 0.7;
      c.beginPath();
      parents.forEach((p, i) => {
        if (p >= 0) {
          c.moveTo(...(this.xy(nodes[p]) as [number, number]));
          c.lineTo(...(this.xy(nodes[i]) as [number, number]));
        }
      });
      c.stroke();
    };
    if (frame?.nodes && frame.parents)
      tree(frame.nodes, frame.parents, "#58a3a8");
    if (frame?.secondNodes && frame.secondParents)
      tree(frame.secondNodes, frame.secondParents, "#c69863");
    if (frame?.path.length) {
      c.strokeStyle = "#b9f79f";
      c.lineWidth = 3;
      c.beginPath();
      frame.path.forEach((p, i) => {
        if (i) c.lineTo(...(this.xy(p) as [number, number]));
        else c.moveTo(...(this.xy(p) as [number, number]));
      });
      c.stroke();
    }
    const dot = (p: Point, col: string, r = 4) => {
      const [x, y] = this.xy(p);
      c.beginPath();
      c.arc(x, y, r, 0, Math.PI * 2);
      c.fillStyle = col;
      c.fill();
      c.strokeStyle = "#fff";
      c.lineWidth = 1;
      c.stroke();
    };
    dot(this.env.start, "#6cdddc");
    dot(this.env.goal, "#ffb766");
    if (q) dot(q, this.env.clearance(q) > 0 ? "#fff" : "#ff706d", 5);
    else if (frame?.candidate)
      dot(frame.candidate, frame.accepted ? "#fff" : "#ff706d", 4);
  }
}
