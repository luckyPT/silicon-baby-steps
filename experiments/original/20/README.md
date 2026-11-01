# 第20集：FMT* / BIT*

静态二维点机器人的批量采样与搜索教学实现，非官方性能复现。

- `experiment.py`：生成三种种子的实际路径、树、检边统计与稀疏失败记录。
- `讲义.md`：公式、手算、四张文本SVG图解、真实条件与失败恢复。
- `lesson.json`、`cards.json`：本集旁白与讲解卡片。
- `qa/summary.json`：实际条件、最终路径与批次摘要；运行experiment.py可生成完整树历史qa/experiment.json；不含任何视频或音频。

复现：安装requirements.txt后，运行 `python experiment.py`。生成中文图解时指定 `COURSE_CJK_FONT=/path/to/NotoSansCJKsc-Regular.otf python make_notes.py`，字体需自行安装。

FMT与全验图共享点集和半径；BIT使用四批各80个改善域自由样本。相同样本数量不等于相同图、半径或计算预算。全部路径以解析线段—圆净距复检。

完整视频、声音、口型与模型另行归档，不上传Git。
