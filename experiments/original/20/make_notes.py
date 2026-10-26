from pathlib import Path
import json,math,os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager,FontProperties
B=Path(__file__).parent;F=B/'assets/figures';F.mkdir(exist_ok=True)
fontpath=Path(os.environ.get('COURSE_CJK_FONT','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'));fontManager.addfont(str(fontpath));plt.rcParams.update({'font.family':FontProperties(fname=fontpath).get_name(),'axes.unicode_minus':False,'font.size':11,'svg.fonttype':'none'})
D=json.loads((B/'qa/experiment.json').read_text());r=D['runs'][0]
def save(fig,n):
 fig.tight_layout();fig.savefig(F/(n+'.png'),dpi=160);fig.savefig(F/(n+'.svg'));plt.close(fig)
def world(ax):
 ax.add_patch(plt.Circle((2.5,0),.8,color='#e77863',alpha=.7));ax.scatter([0,5],[0,0],c=['#225f94','#1d9f73'],s=65,zorder=5);ax.set(xlim=(-.5,5.5),ylim=(-2.5,2.5),xlabel='x / m',ylabel='y / m');ax.set_aspect('equal');ax.grid(alpha=.2)
fig,ax=plt.subplots(figsize=(8,5));world(ax);p=np.array(r['fmt']['points']);ax.scatter(*p.T,s=7,c='#aaa');h=r['fmt']['history'][len(r['fmt']['history'])//2]
for a,b in h['edges']:ax.plot(*p[[a,b]].T,c='#2a9d8f',lw=.8)
ax.scatter(*p[h['open']].T,s=22,c='#e9b84e',label='当前波前');ax.set_title('FMT*：按已到达代价推进的真实树（种子1）');ax.legend();save(fig,'01_fmt_front')
fig,ax=plt.subplots(figsize=(8,4));x=np.arange(3);w=.35;ax.bar(x-w/2,[x['fmt']['checks']for x in D['runs']],w,label='FMT*按需检边');ax.bar(x+w/2,[x['eager']['checks']for x in D['runs']],w,label='相同点集/半径，全部候选边先验');ax.set_xticks(x,[str(x['seed'])for x in D['runs']]);ax.set(xlabel='种子',ylabel='边检碰调用数',title='仅比较边检碰调用；不等同运行时间或普遍性能');ax.legend(fontsize=9);save(fig,'02_checks')
fig,ax=plt.subplots(figsize=(8,4))
for r0 in D['runs']:ax.step([b['batch']for b in r0['bit']['batches']],[b['best']for b in r0['bit']['batches']],where='post',marker='o',label=f'种子{r0["seed"]}')
ax.set(xlabel='批次（每批80个自由样本）',ylabel='当前最好路径长度 / m',xticks=[1,2,3,4],title='BIT*：真实批次末结果；有限预算不证明全局最短');ax.grid(alpha=.2);ax.legend();save(fig,'03_bit_batches')
fig,axs=plt.subplots(1,2,figsize=(11,4.5));world(axs[0]);a=3;b=math.sqrt(11)/2;t=np.linspace(0,math.tau,250);axs[0].plot(2.5+a*np.cos(t),b*np.sin(t),c='#d28c2e');axs[0].set_title('独立手算椭圆：cbest=6m，cmin=5m')
world(axs[1]);p=np.array(D['sparse_failure']['points']);axs[1].scatter(*p.T,s=20,c='#477d9c');axs[1].set_title('真实失败：25点、r=0.45m，无返回路径');save(fig,'04_ellipse_failure')
table='\n'.join(f'| {z["seed"]} | {z["fmt"]["length"]:.6f} | {z["fmt"]["checks"]} | {z["eager"]["checks"]} | {z["bit"]["length"]:.6f} | {z["bit"]["checks"]} |'for z in D['runs'])
notes=r'''# 硅基学步20：先撒点，再排队，怎样越找越好？

FMT* / BIT*：批量采样与搜索结合。硅宝，碳硅共鸣001号员工，和大家一起练级。

## 1 从PRM、RRT和轨迹优化接过问题

前两集在已有初始轨迹上优化；本集回到寻找路径。PRM先建路网，RRT边采边长。FMT*和BIT*把一批自由样本看作隐式随机几何图，只在需要时生成邻边或验证碰撞。候选邻边并不是已经安全可行的边。

本实现：静态二维点机器人，起点(0,0)m、目标(5,0)m，圆心(2.5,0)m、半径0.8m，矩形范围[-0.5,5.5]×[-2.5,2.5]m。代价为欧氏弧长，局部连接为直线，解析检验整条线段与圆的净距。三维画面只是展示，不增加规划自由度；不证明真实机器人可执行。

## 2 FMT*：三组样本与代价波前

未访问、波前、已扩展三组样本不相交。起点先进入波前，g(start)=0。每轮选择

$$z=\arg\min_{v\in V_{open}}g_T(v).$$

对于z附近未连接的x，在x邻域内的波前节点中，按下式选一个父节点：

$$y^*=\arg\min_{y\in N_r(x)\cap V_{open}}\left[g_T(y)+\|y-x\|_2\right].$$

先比代价，再只验证选中的连接。如果边无碰撞才接入树。新节点在本轮末一并放进波前，之后把z放入已扩展集合。如果选中边碰撞，本轮不把备用父节点挨个试完；x仍可在后续扩展中重新被考虑。这是懒动态规划的重要细节，不能改成完整邻图最短路后仍称标准FMT*。

![FMT代价波前](assets/figures/01_fmt_front.svg)

图1：种子1的真实中间树；金色为当时波前，青色为已通过整段检碰的树边。

独立手算：A已有代价2.0m，连接1.5m，合计3.5m；B已有代价2.5m，连接0.7m，合计3.2m，先验B边。数字说明递推规则，不冒充图1中的具体节点。

## 3 半径、懒检查与有限样本边界

典型邻域尺度为 $r_n=\gamma(\log n/n)^{1/d}$，系数、采样和空间须满足对应理论假设。半径过小可能断图，过大增加邻边工作。星号的渐近最优不等于有限点集上一定全局最短；FMT*在有障碍的有限图上也可能因懒处理产生次优连接或失败。

本例FMT用320个自由样本，固定r=0.95m。对照为相同点集、相同半径先验证所有候选边，再Dijkstra搜索。这里只检验边检查次数的差别，不排名运行时间。三个种子在本例恰好得到相同长度，不由此断言两种方法总是等价。

![边检碰次数](assets/figures/02_checks.svg)

图2：边检碰调用数；不含绘图，不等同CPU时间。本例碰撞几何很便宜，不能把调用数直接换成实机加速比。

## 4 BIT*：启发式双队列与复用

BIT*在越来越密的隐式图中搜索，复用树和最好解。点队列产生候选边，边队列安排检查优先级：

$$k_V(v)=g_T(v)+\widehat h(v),$$
$$k_E(v,x)=g_T(v)+\widehat c(v,x)+\widehat h(x).$$

如果某点能产生比当前最好候选边更有前景的边，先展开点。只有通过便宜乐观筛选后才计算实际边成本。无碰撞直线成本是长度，碰撞则为无穷大。新接点可以重连树节点，必须同步更新后代代价与队列有效优先级。

这里区分真实树路径账单与最优代价下界：

$$\widehat g(x)\le g^*(x)\le g_T(x).$$

gT不能冒充全局乐观下界。某条已有前缀在本轮没有改善希望，不等于这个状态未来永远没有价值。

独立手算：边A的三项为2.1+1.2+2.0=5.3m，边B为1.8+1.5+2.3=5.6m。当前最好5.5m时先考虑A；B当前前缀可暂不检查，树路径改善后须重新评估。

## 5 改善区域与批次

对于长度目标，必要改善条件是 $\|x-s\|+\|x-g\|<c_{best}$。二维为椭圆：$a=c_{best}/2$，$b=\sqrt{c_{best}^2-c_{min}^2}/2$。手算cbest=6m、cmin=5m，a=3m，b≈1.658312m。区域内部仍可能有障碍，须同时检验采样点与连接边。

本实现每批80个自由样本、4批，采用矩形域拒绝采样，保留满足改善条件的自由点。半径使用论文r-disc尺度，体积取整个矩形域的保守上界，因而可能比精确改善域半径更大；优先队列用集合实时计算最小键，而非性能优化堆。边检查缓存仅用于本次同一静态地图。它们影响工作量，不作为官方实现速度复现。

![BIT批次曲线](assets/figures/03_bit_batches.svg)

图3：每批结束时保留的真实最好解；种子1长度为5.642646、5.310974、5.298753、5.293434m。最好值不增，但单批不保证改善，最终结果不证明连续空间最优。

## 6 三种种子的完整口径

| 种子 | FMT长度/m | FMT检边 | 全验图检边 | BIT长度/m | BIT检边 |
|---|---:|---:|---:|---:|---:|
TABLE

FMT和全验图共享相同点集与半径；BIT使用不同批次、改善区域和半径策略。两边各生成320个自由样本只是相同样本数量，不是等计算预算、等点集或等运行时间。三个种子的全部最终折线均通过解析整段净距检验。没有做平滑后再偷偷把长度算给规划器。

## 7 失败、恢复与工程验收

![椭圆与稀疏失败](assets/figures/04_ellipse_failure.svg)

图4左为独立几何手算，右为种子7、25个样本、r=0.45m的实际失败。几何空间有绕行路，不保证采样图连通。先查几何与起终点，再查覆盖和邻域尺度；有需要时采用有覆盖保障的窄通道采样，增加样本/预算。启发式不能修复断图。

预算耗尽时保留已验证旧解；没有解就报告失败。静态地图下可继续加批；地图或机器人模型改变后不能照搬旧边安全缓存。整段几何复检之后，还要处理时间参数化、速度约束和闭环跟踪；本集不展示虚构真机效果。

## 8 复现与来源

运行 `python experiment.py` 生成qa/experiment.json，依赖numpy、scipy。覆盖检查：起终点直连穿圆、无障碍FMT与同图搜索一致、FMT结果不优于完整同图最短路、BIT保留解单调不增、返回路径均无碰撞、稀疏失败。

原始机制参考：

- Janson等，Fast Marching Tree，IJRR 2015： https://lucasjanson.fas.harvard.edu/papers/Fast_Marching_Tree_A_Fast_Marching_Sampling_Based_Method-Janson_ea-2015.pdf
- Gammell等，BIT*，ICRA 2015，算法1—3： https://publications.ri.cmu.edu/storage/publications/pub_files/2015/5/Gammell15-bitstar.pdf

下一集已定为AIT* / EIT* / MIT*：启发信息与计算分配。本文配套完整有声视频单独保存；Git只保留代码、文档与文本SVG图解，不存视频、音频或模型二进制。
'''.replace('TABLE',table)
(B/'讲义.md').write_text(notes)
(B/'README.md').write_text('第20集 FMT*/BIT* 教学工程。\n运行：python experiment.py；python make_notes.py。\n公开仓库只提交代码、讲义、文本SVG及实验JSON；视频/声音/模型单独归档。\n实验结果和限制详见讲义.md，非官方算法性能复现。\n')
print('NOTES AND FOUR FIGURES READY')
