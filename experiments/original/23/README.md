# 第23集：LPA* / 终身规划A*——路口突然封了，还要从头算吗？

第五部分“环境变化与搜索复用”开篇。本章按2004年基础伪代码自写LPA*，不冒充官方库或工业性能复现。起终点固定，四邻接正权栅格，地图在查询之间变更；无移动起点D* Lite、感知、时间避碰或真实机器人执行。

运行：`python -m pip install -r requirements.txt`，再执行`python experiment.py`。程序包含8阶段主序列和3种子各30次随机开关更新，每次与重跑A*及独立反向Dijkstra核对最短代价，检查返回路径、终点一致与队列停止条件。结果含实际扩展事件，写入`qa/experiment.json`；本次摘要见`qa/summary.json`。

初次21/21次扩展，封终点92/105，重开4/21，最后封起点77/65。数字依次为LPA*/重跑A*；真实反例说明复用不保证每次省扩展。rhs扫描、队列操作与地图变化成本分开；扩展次数不是运行速度。LPA*同一节点可能重复扩展，不等于着色格子数。

讲义正文有4张文本SVG。复现图：`COURSE_CJK_FONT=/absolute/path/NotoSansCJKsc-Regular.otf python make_notes.py`。字体自行提供。完整视频、音频、模型与制作工程单独交付，不上传Git。平台发布状态以`qa/publication_record.json`（取得回执后追加）及当前交接为准；本次代码提交不代表作品已发布或网站目录已上线。
