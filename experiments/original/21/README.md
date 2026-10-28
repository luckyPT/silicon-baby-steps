# 第21集：AIT* / EIT* / MIT*——路太多，先算哪条才不白忙？

第四部分静态规划收官。本目录保留可运行教学组件、结构化讲义、四张中文文本SVG及实际三种子日志摘要。完整视频、音频、人物模型和制作工程不上传Git，另行交付。

运行：`python -m pip install -r requirements.txt`，然后 `python experiment.py`。生成含完整树历史的 `qa/experiment.json`。图解复现：`COURSE_CJK_FONT=/absolute/path/NotoSansCJKsc-Regular.otf python make_notes.py`，需要自行安装中文字体。

实验1是冻结随机几何图上的固定欧氏启发与适应性图启发，反向全量Dijkstra重算，非AIT*的LPA*增量实现。实验2是EIT*计算分配的独立候选路线账本，非完整EIT*。实验3拆解MIT*估计采样域与障碍附近采样组件，阈值由教学实验直接设置，非完整自动策略。不得把这些结果当作论文复现或官方速度排名。

`experiment.py`包含真实返回路径的解析整段检碰、独立全验图最优代价对照、每次反向修正的可采纳性检查、过窄采样域失败与恢复、三点漏检反例等断言。种子1/7/17同一组内两策略共享点集与半径；不同估计域点集不同。

视频制作与平台发布状态以 `qa/publication_record.json`（取得回执后写入）与项目当前交接为准。本次代码提交不代表视频已发布，也不代表网站目录新增本章。
