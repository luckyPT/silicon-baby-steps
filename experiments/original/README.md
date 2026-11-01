# 视频实验原始算法

这里保存第07—14集使用过的 Python 算法实现与几何检碰模块，和浏览器的 TypeScript 交互实现分开保存。网站文章与视频保留原先的实验口径；网站实验可以调整参数，不冒充视频中的逐帧回放。

```bash
python3 -m venv .venv
# Linux / macOS
. .venv/bin/activate
pip install numpy
cd experiments/original/09
python3 rrt_star.py
```

Windows 激活命令为 `.venv\Scripts\Activate.ps1`。第08集运行 `rrt_connect.py`，第07集运行 `rrt.py`。脚本从所在目录读写 `assets/`、`qa/`，请先建立这两个目录（原始压缩包内目录不参与Git跟踪）。第09集脚本会自动建立目录。

- `07/rrt.py`：单树几何RRT，关节空间采样、近邻、扩展、整段检碰与回溯。
- `08/rrt_connect.py`：双树，固定目标的Connect，逐段验收与双侧回溯。
- `09/rrt_star.py`：选父、重连、后代成本传播；6次固定检碰预算对照。
- `*/arm_model.py`：连杆几何与检碰模型。
- `*/qa/reference_validation.json`：原视频生成时保留的核验结果。

第01—06集的可运行实验已在 `src/algorithms/` 中实现：`grid.ts`、`trajectory.ts`、`dwa.ts` 和 `environments.ts`。文章发布原文位于 `docs/articles-original/`。

视频的大量逐帧PNG、配音缓存与Blender渲染工具不属于算法实验依赖，没有放进网站源码；完整成片已存放在 `public/media/`。


## 第10—14集复算

从仓库根目录运行：

```bash
pip install -r experiments/original/requirements.txt
python experiments/original/10/informed_rrt_star.py
python experiments/original/11/verify_postprocess.py
python experiments/original/12/validate_motion.py
python experiments/original/13/validate_motion.py
python experiments/original/14/validate_motion.py
python scripts/render-course-figures.py
```

第10集生成六次固定检碰预算运行；其余四集依次使用同一条种子7路径和几何证书，验证后处理、梯形、S曲线与关节幅值。`qa`保留失败候选和通过项，不能只替换输入继续沿用旧结论。浏览器与Python的随机数、预算与插值精度不同，不冒充逐帧一致的执行。
