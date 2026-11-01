# 第22集：GCS / 凸集图规划——绕哪边、怎么走，能一起算吗？

第四部分静态规划补篇。本目录保留实际Drake GraphOfConvexSets + Clarabel实验、一阶入口/出口长度模型、结构化讲义、四张中文文本SVG和真实数值摘要。完整视频、音频、模型及制作工程单独交付，不上传Git。

运行：`python -m pip install -r requirements.txt`，再运行`python experiment.py`。实验自动执行独立整段线段—矩形检碰、区域归属、连续性、目标值、两分支穷举/解析值、缺区域失败恢复、车身保守膨胀恢复断言。需要受支持的Drake Python环境。使用Clarabel，不需要Mosek许可。

图解复现：`COURSE_CJK_FONT=/absolute/path/NotoSansCJKsc-Regular.otf python make_notes.py`，中文字体需自行安装。`qa/experiment.json`由运行生成；已提交的`qa/summary.json`为本次实际结果摘要。

三个种子只变更同一场景的舍入随机数。松弛下界约5米、可行路径约5.4721米，本例不紧；模型内最优通过两分支穷举及解析核对确定。存在5.1729米覆盖外可行参考线，故不声称连续空间全局最短。不作跨规划器速度排名，不含时间参数化、动力学或真机执行。

视频制作与平台状态以`qa/publication_record.json`及当前交接为准。封面按2026-10-29用户新要求，醒目显示“GCS｜凸集图规划”。本次提交不代表网站目录已经新增第22集。
