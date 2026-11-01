# 第18集 CHOMP / STOMP 原始实验

保留原始 `experiment.py`、第17集种子17第一查询路线 `assets/initial_route.json`、完整 `qa/experiment.json` 与原讲义。只依赖 NumPy：

```bash
python -m pip install numpy
python experiments/original/18/experiment.py
```

脚本重新计算主实验、三个STOMP种子、对称失败案例和平均碰撞反例，并核对解析梯度、固定端点和接受步骤的成本单调性。重新运行会更新QA日志中的计算时间。

模型为静态二维点机器人；41点、固定两端，五点高斯障碍积分，解析线段圆盘验收。不是完整机械臂、论文全功能基准或真机安全认证。原始脚本和输入未被网页移植替换。

网页实现位于 `src/algorithms/optimization.ts`。CHOMP默认140轮结果用原始报告回归测试。STOMP网页随机数为Mulberry32 + Box–Muller，Python是NumPy PCG64；同种子在各自实现内可复现，但不承诺二者随机序列一致。网页总目标回溯接受是本教学实现的工程保护；STOMP未调用解析梯度。网页比较同轮数，不宣称同计算量或普遍性能排名。
