export interface Lesson {
  id: string;
  title: string;
  subtitle: string;
  algorithm: string;
  part: number;
  duration: string;
  minutes: number;
  concepts: string[];
  lab: "grid" | "trajectory" | "dwa" | "system" | "config" | "sampling" | "arm-course";
}
export const lessons: Lesson[] = [
  {
    id: "01",
    title: "Dijkstra：先别撞上椅子",
    subtitle: "老板只提了一个需求：到桌子那边去。",
    algorithm: "Dijkstra",
    part: 1,
    duration: "",
    minutes: 8,
    concepts: ["累计成本", "优先队列", "父节点回溯"],
    lab: "grid",
  },
  {
    id: "02",
    title: "A*：给搜索加一点方向感",
    subtitle: "Dijkstra很认真，但老板不想等他巡完全公司。",
    algorithm: "A*",
    part: 1,
    duration: "",
    minutes: 7,
    concepts: ["启发函数", "f = g + h", "最优性条件"],
    lab: "grid",
  },
  {
    id: "03",
    title: "路找到了，车就能走吗？",
    subtitle: "路径、轨迹和车身约束，别让数学替保险公司上班。",
    algorithm: "路径与轨迹",
    part: 1,
    duration: "",
    minutes: 8,
    concepts: ["车身膨胀", "路径与轨迹", "可执行性"],
    lab: "trajectory",
  },
  {
    id: "04",
    title: "DWA：椅子会动，怎么办？",
    subtitle: "世界不会等你的全局地图更新完再开门。",
    algorithm: "DWA",
    part: 1,
    duration: "",
    minutes: 8,
    concepts: ["动态窗口", "轨迹预测", "滚动规划"],
    lab: "dwa",
  },
  {
    id: "05",
    title: "第一部分收官：让算法组队上班",
    subtitle: "A*认路，局部规划看眼前，系统负责交接与验收。",
    algorithm: "全局 × 局部",
    part: 1,
    duration: "",
    minutes: 8,
    concepts: ["路线引导", "模块交接", "系统验收"],
    lab: "system",
  },
  {
    id: "06",
    title: "机械臂的地图，为什么画在关节角度里？",
    subtitle: "手到了，不代表胳膊没撞墙。",
    algorithm: "配置空间",
    part: 2,
    duration: "",
    minutes: 8,
    concepts: ["正运动学", "碰撞禁区", "整段连接"],
    lab: "config",
  },
  {
    id: "07",
    title: "RRT：老板让我找路，我先种了棵树",
    subtitle: "高维空间里，不必先给每一寸地方铺满网格。",
    algorithm: "RRT",
    part: 2,
    duration: "",
    minutes: 8,
    concepts: ["随机采样", "最近邻", "扩展与检碰"],
    lab: "sampling",
  },
  {
    id: "08",
    title: "RRT-Connect：两棵树，怎样接上头？",
    subtitle: "一边从起点，一边从目标，朝同一个点连续靠近。",
    algorithm: "RRT-Connect",
    part: 2,
    duration: "7:00",
    minutes: 8,
    concepts: ["双树", "Extend / Connect", "双向回溯"],
    lab: "sampling",
  },
  {
    id: "09",
    title: "RRT*：路找到了，能不能少绕一点？",
    subtitle: "这一次，不光要会种树，还得会算差旅费。",
    algorithm: "RRT*",
    part: 2,
    duration: "7:53",
    minutes: 8,
    concepts: ["选择父节点", "重新连接", "后代成本更新"],
    lab: "sampling",
  },
  {"id": "10", "title": "Informed RRT*：把采样花在有希望的地方", "subtitle": "从真实路径出发，把每一步验收跑明白。", "algorithm": "Informed RRT*", "part": 2, "lab": "sampling", "concepts": ["成本下界", "椭圆采样", "同条件对比"], "duration": "6:50", "minutes": 8},
  {"id": "11", "title": "路径后处理：删点、圆角与碰撞复检", "subtitle": "从真实路径出发，把每一步验收跑明白。", "algorithm": "路径后处理", "part": 2, "lab": "arm-course", "concepts": ["快捷连接", "Bezier圆角", "整段复检"], "duration": "5:50", "minutes": 8},
  {"id": "12", "title": "时间参数化：给路径排时刻表", "subtitle": "从真实路径出发，把每一步验收跑明白。", "algorithm": "梯形速度", "part": 3, "lab": "arm-course", "concepts": ["路径与轨迹", "梯形与三角形", "任务终点"], "duration": "4:18", "minutes": 8},
  {"id": "13", "title": "S曲线：让加速度也有过渡", "subtitle": "从真实路径出发，把每一步验收跑明白。", "algorithm": "S曲线与jerk", "part": 3, "lab": "arm-course", "concepts": ["七段积分", "jerk", "曲率接缝"], "duration": "3:48", "minutes": 8},
  {"id": "14", "title": "关节约束验收与统一时间伸缩", "subtitle": "从真实路径出发，把每一步验收跑明白。", "algorithm": "关节约束验收", "part": 3, "lab": "arm-course", "concepts": ["链式法则", "时间伸缩", "单侧极限"], "duration": "3:57", "minutes": 8},
];
export const roadmap = [
  {
    title: "硅宝第一次出门",
    topics: "规划、路径、车身约束与最小系统",
    practice: "主线：到桌子那边去；工业案例：移动平台绕障与到站验收。",
    status: "已完成 01—05",
  },
  {
    title: "认识自己的身体",
    topics: "状态、坐标、运动模型、可达性",
    practice:
      "主线：同一个指令为什么走出不同结果；工业案例：车体尺寸、机械臂关节与执行边界。",
    status: "相关内容已提前穿插",
  },
  {
    title: "先找到一条路",
    topics: "地图、碰撞检测、Dijkstra、A*、Hybrid A*、RRT系列",
    practice: "主线：迷宫、窄通道、倒车入库；工业案例：有车身约束的避障。",
    status: "01—02、06—11 持续展开",
  },
  {
    title: "有路了，为什么还是走不了",
    topics: "路径与轨迹、样条、多项式、速度规划、加速度与jerk、DWA / TEB",
    practice: "主线：急弯减速、突然来人；工业案例：带动态障碍的重规划。",
    status: "03—05 入门，11—14 已展开后处理与时间参数化",
  },
  {
    title: "把车开稳",
    topics: "PID、积分饱和、Pure Pursuit、Stanley、前馈与反馈",
    practice: "主线：直线、圆与S弯跟踪；工业案例：超调、蛇形、切弯与高速失稳。",
    status: "后续课程 · 控制集中在后段",
  },
  {
    title: "提前想几步再行动",
    topics: "状态空间、线性化、QP、LQR、线性与非线性MPC、软硬约束",
    practice: "主线：控制器对照；工业案例：转角与加速度限制、求解无解和超时。",
    status: "后续课程",
  },
  {
    title: "给硅宝制造麻烦",
    topics: "状态估计、时间戳、坐标链、多频率、延迟、噪声与模型失配",
    practice:
      "主线：注入定位偏差、丢消息、打滑；工业案例：故障传播与异常恢复。",
    status: "后续课程",
  },
  {
    title: "从轮子升级到机械臂",
    topics: "正逆运动学、雅可比、奇异位形、自碰撞、时间参数化与执行接口",
    practice: "主线：从二连杆到多关节；工业案例：机械臂路径、工艺姿态与约束。",
    status: "06—11 提前进入采样规划",
  },
  {
    title: "从能演示到能交付",
    topics: "需求与验收、指标体系、场景覆盖、自动回归、日志回放、部署管理",
    practice:
      "主线：整合全流程并接受陌生场景；工业案例：测试报告、故障分析和回归放行。",
    status: "综合项目 · 后续课程",
  },
];
export const asset = (path: string) => `${import.meta.env.BASE_URL}${path}`;
