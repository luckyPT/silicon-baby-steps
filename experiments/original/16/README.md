# 第16集：人工势场原始实验

`experiment.py`、`qa/experiment.json` 与 `narration.txt` 从已有制作工程恢复，保留原始内容。

```bash
python -m pip install numpy
python experiments/original/16/experiment.py
```

脚本会重新计算基础人工势场、受限随机扰动、预设临时目标和 RRT-Connect 引导/已验证路线回退，覆盖原始指定种子，并写入 `qa/experiment.json`。该报告中的检查次数包含最终线段复检；随机种子保证同一实现可复现，不代表不同方法逐个消耗相同样本。

网站的 `src/algorithms/potential-field.ts` 忠实移植**确定性的基础势场与临时目标两分支**；默认每个轨迹点、状态、循环次数、路径长度及检查次数均通过与本报告比较的回归测试。浏览器没有声称执行随机扰动或 RRT-Connect 分支。交互参数变更后由浏览器重新计算。

模型为静态二维点机器人和膨胀圆盘；虚拟力不是电机力，动画迭代不是物理时间。临时目标是预设教学策略，不是自动寻路；有路不保证势场到达。路径长度仅对达到同一终点的方案才有可比性。只验证几何碰撞，不包含速度、加速度、力矩、跟踪或真机认证。
