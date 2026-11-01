# 第17集原始 PRM / Lazy PRM 实验

从既有第17集制作工程恢复，`experiment.py` 与 `qa/experiment.json` 原样保留。不是本次重做的浏览器结果。

```bash
python -m pip install numpy
python experiments/original/17/experiment.py
```

运行会重写同目录 `qa/experiment.json`，其中耗时字段会变化。模型是二维点机器人和膨胀圆盘，180个有效点、k=10；先验证节点，只延迟边验证。基础边缓存跨三次查询共享，临时接入边不共享。计数为线段检碰，不是耗时。

浏览器移植使用另一随机数生成器，保留同模型和同条件比较，但不声称与 NumPy 同种子逐点一致。UI位于 `src/ui/roadmap-lab.ts`，算法位于 `src/algorithms/roadmap.ts`。
