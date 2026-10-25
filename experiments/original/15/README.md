# 第15集导读实验

只运行已经实现的RRT、RRT-Connect、RRT*和Informed RRT*，用于明确对比口径。新算法将在后续各集实现。本集机制图不作运行结果。

在仓库根目录执行：

```
node --experimental-strip-types experiments/original/15/run-comparison.ts
```

固定2R模型、0.15m障碍半径、1200采样迭代、10°步长、35°近邻上限、0.05目标偏置，种子1/7/42。`comparison.json`记录12次实际运行、路径和整段复检；path关节角和cost为弧度。检碰预算不同，没有测量或比较墙钟耗时。复检调用同一模型验证器，不宣称独立物理模型认证。

正文五张中文图由`scripts/illustrate-article-15.py`生成。指定`COURSE_CJK_FONT`为本地Noto CJK字体路径。图片是思想示意或已完成链路说明，没有把未来课程的算法当成已实现能力。

完整配音稿见`narration.txt`；视频与字幕、发布回执最终另行记录。教学仿真不代表真机安全、控制跟踪或动力学验收。
