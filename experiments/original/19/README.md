# 第19集 TrajOpt / GPMP2 机制实验

运行：`python -m pip install -r requirements.txt`，然后`python experiment.py`。结果保存到qa/experiment.json。

这是自写的静态二维点机器人教学实现，不是官方TrajOpt或GPMP2完整软件复现。包含SCO凸子问题、信赖域、铰链惩罚、GP平滑先验、插值障碍因子及解析整段/曲线复检。目标、变量与预算不同，不做速度排名。

实验已复算：仅查节点时整段净距−0.65m；整段SCO约+0.15m；GP曲线约+0.148896m，略低于0.15m惩罚余量。对称初值的失败如实保留。线段梯度差分核对最大误差约1.83e−10。

原论文：
- https://roboticsproceedings.org/rss09/p31.pdf
- https://roboticsproceedings.org/rss12/p01.pdf
- https://github.com/gtrll/gpmp2

新视频单独交付，不存入Git。
