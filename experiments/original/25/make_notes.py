from pathlib import Path
import json,html
B=Path(__file__).resolve().parent;Q=B/'qa';O=B/'assets/article';O.mkdir(exist_ok=True);D=json.loads((Q/'experiment.json').read_text());PH=D['phases'];BY={p['name']:p for p in PH}
def tx(x,y,s,size=25,col='#e8f2ff'):return f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}">{html.escape(str(s))}</text>'
def svg(name,title,body):
 s='<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720"><rect width="1200" height="720" fill="#071725"/><g font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif">'+tx(55,68,title,36,'#5ce0d3')+body+'</g></svg>';(O/name).write_text(s)
svg('01_weight_bound.svg','加权启发与质量界限：先交有界次优解',tx(65,145,'反向搜索：fε(u)=g(u)+εh(S,u)，ε≥1')+tx(65,210,'独立例：A的g=10、h=2；B的g=6、h=4')+tx(65,270,'ε=1：A=12、B=10，优先B；ε=3：A=16、B=18，优先A')+tx(65,360,'本例最优C*=26；完成ε=3搜索轮次后，C≤78')+tx(65,425,'实际初解C=36；上界78不是实际路径代价预测',29,'#ffca7a')+tx(65,515,'C*由独立Dijkstra事后求得，规划器不提前读入最优答案')+tx(65,625,'满足论文假设的图与完成搜索轮次；初解未找到时不凭空交付。',23,'#a4baca'))
incons=BY['ara_3']['result']['incons_nodes'];svg('02_reuse_sets.svg','ARA*：保留g，下一轮再处理INCONS',tx(65,150,'OPEN：当前候选；CLOSED：本轮已处理')+tx(65,215,'INCONS：本轮已处理，后来又找到更低报价的节点')+tx(65,290,'下一轮：OPEN←OPEN∪INCONS，清空INCONS与CLOSED')+tx(65,350,'降低ε后重排OPEN；保留g和已验证的旧路线')+tx(65,445,'固定种子34，首轮结束实际留下2个INCONS节点：',27,'#5ce0d3')+tx(65,510,str(incons),30,'#ffca7a')+tx(65,625,'INCONS不是障碍列表；没有每轮从头初始化代价。',23,'#a4baca'))
ara=PH[:5];body='';x0,y0=130,535;xs=[150+i*215 for i in range(5)];ys=[y0-(p['result']['cost']-24)*25 for p in ara];body+='<path d="M130 165 V535 H1100" fill="none" stroke="#8eabc1" stroke-width="2"/>'
for c in [26,30,34,38]:
 y=y0-(c-24)*25;body+=f'<path d="M130 {y} H1100" stroke="#244052"/>'+tx(75,y+8,c,22)
body+=f'<polyline points="'+ ' '.join(f'{x},{y}'for x,y in zip(xs,ys))+'" fill="none" stroke="#5ce0d3" stroke-width="5"/>'
for x,y,p in zip(xs,ys,ara):
 r=p['result'];body+=f'<circle cx="{x}" cy="{y}" r="7" fill="#ffca7a"/>'+tx(x-18,y-22,r['cost'],28,'#ffca7a')+tx(x-40,580,'ε='+str(r['epsilon']),24)+tx(x-57,624,'新增扩展'+str(r['expansions']),21,'#a4baca')
body+=tx(65,680,'同一张图，最优26；新增扩展共110次。界限收紧不等于每轮路线都改变。',22,'#a4baca');svg('03_anytime_cost.svg','真实日志：36 → 34 → 34 → 30 → 26',body)
svg('04_dynamic_budget.svg','AD*：地图版本、可行性与完成界限一起检查',tx(65,145,'原图：C=26（已完成ε=1轮次）')+tx(65,205,'封(11,4)：旧路线失效；新图最优28')+tx(65,265,'修复ε=2.5：C=34；再改善ε=1：C=28',29,'#ffca7a')+tx(65,345,'未完成首轮：没有合格初解，不宣布新界限')+tx(65,405,'同图改善中断：可保留验证过的旧路线，沿用旧界限')+tx(65,465,'地图变化后修复中断：旧路线穿封格，不能继续执行',26,'#5ce0d3')+tx(65,555,'270次AD*完成查询 + 100次额外ARA*完成查询通过复核')+tx(65,625,'扩展预算不是毫秒；停止离散移动不等于验证了真实制动安全。',23,'#a4baca'))
rows='\n'.join(f'| {p["name"]} | {p["algorithm"]} | {p["result"]["epsilon"]} | {"无路"if p["result"]["cost"]is None else p["result"]["cost"]} | {"无路"if p["oracle_cost"]is None else p["oracle_cost"]} | {p["result"]["expansions"]} | {len(p["result"]["incons_nodes"])} |'for p in PH)
notes=r'''# 第25集：ARA* → AD*——时间不够，先交哪条路线？

## 1. 承接D* Lite：最优答案也可能来得太晚

上一集处理移动当前位置与图代价变化，求当前已知图最短路。本集固定起终点，在复杂搜索中先完成有质量界限的路线，再继续改善；地图变化时还要修复。Anytime不意味着任意短预算内都已有初解。

自写教学实现采用ICAPS 2005中的反向ARA*（Figure 3）与基础AD*（Figures 4—5）；不是官方库或真实机器人。正权四邻接图，边代价为两端软代价最大值且至少1，使用一致曼哈顿启发。静态改善轮次之间图不变；图变化在查询之间一次性安装。

## 2. 加权启发与质量界限

$$f_\epsilon(u)=g(u)+\epsilon h(S,u),\qquad C\leq\epsilon C^*,\quad\epsilon\geq1.$$

反向实现从目标传播g，启发距离指向固定起点。系数大通常更偏向启发方向，但不保证任意图都更快。质量界限约束完成轮次所交付路线在当前离散图中的代价；不约束物理时间或未来障碍碰撞。

![加权与界限](assets/article/01_weight_bound.svg)

*图1：独立候选排序手算与实际图质量上界分开。最优26由独立Dijkstra事后核验，不作为算法输入。*

ε=3时界限是78，实际初解36，不是必须走78；“三倍”也不是“多三米”。

## 3. ARA*怎样复用

保留g、OPEN与INCONS。CLOSED记录本轮已扩展节点；本轮已扩展而后来g又改善的节点进入INCONS，留到下一轮。降低ε前，把INCONS并入OPEN并清空，重排优先级、清空CLOSED，再继续搜索。

![三组状态](assets/article/02_reuse_sets.svg)

*图2：种子34首轮实际留下两个INCONS节点，下一轮并回OPEN；不是障碍列表。*

本实现ARA*主关键字相同后用g作为确定性平局规则。反向ARA*在起点已被发现且满足标量停止条件时即可结束，不一定弹出起点。

## 4. 真实改善与不变的平台期

演示种子按能展示分阶段改善及INCONS的条件选为34，不用它做统计性能推断。系数3、2.5、2、1.5、1对应路线36、34、34、30、26；新增有效扩展32、5、0、16、57，共110。ε从2.5降到2时，无需新增有效扩展便满足新轮次停止条件，路线不变。

![改善曲线](assets/article/03_anytime_cost.svg)

*图3：横轴是教学选择的系数阶段，不是时间；纵轴是实际路线代价。*

累计扩展不保证比直接求最优少。Anytime的价值还包括中途可以获得已验证的可用路线。

## 5. AD*：改善与图修复结合

维护目标代价g与后继递推的一步前瞻rhs，更新有向边u→v后先更新源节点u。OPEN/CLOSED/INCONS支持分轮改善与修复。关键字区分两种情况：

$$K(u)=\begin{cases}[rhs(u)+\epsilon h(S,u),rhs(u)],&g(u)>rhs(u),\\[g(u)+h(S,u),g(u)],&g(u)\leq rhs(u).\end{cases}$$

旧低估失效的处理使用未膨胀启发，不能把D* Lite的全部关键字一律乘ε。独立手算h=4、ε=2：g10/rhs6得到[14,6]，g6/rhs10得到[10,6]。

本教学按阶段手动选择ε及地图更新，不实现“显著变化”的自动阈值策略，也不加入移动起点km；后者已在第24集独立讲解。

## 6. 真实封路、重开与无路恢复

下表ARA*阶段共享原图，AD*各图版本按序变化。AD*先求至26，封路线上的(11,4)后旧路线失效；新图最优为28，先修得34，再改善至28。重开后先保留28，降低ε后才回到26。封x=12整列时无路；再打开原可行路线经过的门格后恢复26。

| 阶段 | 算法 | ε | 实际路线代价 | 独立最优 | 新增有效扩展 | 结束INCONS |
|---|---|---|---|---|---|---|
'''+rows+r'''

![动态修复与预算](assets/article/04_dynamic_budget.svg)

*图4：当前图版本、路径可行性和完成轮次的质量界限必须一起核对。*

ARA*与AD*的终止条件、起点处理及撤销事件口径不同，不直接用两者扩展次数做通用速度排名。AD*完成后按c(u,v)+g(v)贪心提取路线，实际路线代价可低于存储g(S)，均独立复算并检查ε界限。

## 7. 三类预算中断

1. 首轮只给5次扩展：未完成，无合格初解，不把最终完整路线冒充预算内结果。
2. 同一图已完成ε3的代价36路线，设置ε1后只给1次扩展：新轮未完成，可保留同图已验证旧路线，但仍只能沿用旧完成界限。
3. 地图封格后只给1次修复扩展：旧路线独立复检穿过障碍，不能继续照走。中断状态继续保存，等待后续完整修复；不发布未完成的新界限。

预算是每次有效扩展之间检查的确定性节点上限，不是毫秒截止、抢占式调度或硬实时承诺；本例停止离散移动不等于真机制动安全验收。

## 8. 复核与适用边界

3种子×30次图变化×3个完成系数阶段=270次AD*查询；包含封路、重开及软代价变化。另20张静态图×5阶段=100次ARA*查询。逐条检查端点、邻接、阻塞、实际代价，并与独立Dijkstra的最优值核对：C≤εC*，ε1时C=C*；新鲜A*也核对最优代价。

有限测试不替代理论证明。计算事件数不等于运行时间；堆、重排、路径提取、感知和执行都有开销。本集没有未来运动预测、连续时间避碰、动力学或真机实验。

## 9. 复现

```bash
python -m pip install -r requirements.txt
python experiment.py
python make_notes.py
```

`grid.py`包含共享图、独立Dijkstra及重跑A*；`experiment.py`实现ARA*、AD*和预算测试；`qa/experiment.json`为完整真实日志，`qa/summary.json`为简表。原论文PDF未随工程重新分发。

## 10. 原始来源

- Likhachev, Gordon & Thrun (2003), ARA*: Anytime A* with Provable Bounds on Sub-Optimality：https://www.cs.cmu.edu/~maxim/files/ara_nips03.pdf
- Likhachev et al. (2005), Anytime Dynamic A*: An Anytime, Replanning Algorithm，Figures 3—5：https://www.cs.cmu.edu/~maxim/files/ad_icaps05.pdf
'''
(B/'README.md').write_text(notes);(B/'讲义.md').write_text(notes);(Q/'summary.json').write_text(json.dumps(dict(episode=25,seed=D['seed'],phases=[dict(name=p['name'],algorithm=p['algorithm'],epsilon=p['result']['epsilon'],cost=p['result']['cost'],optimal=p['oracle_cost'],expansions=p['result']['expansions'],incons=len(p['result']['incons_nodes']))for p in PH],mixed_updates=90,mixed_queries=270,additional_ara_queries=100,budgets=dict(first_completed=D['budgets']['first']['completed'],improvement_completed=D['budgets']['improvement_interrupted']['completed'],repair_completed=D['budgets']['changed_map_partial']['completed'],changed_map_old_path_invalid=True),all_checks='passed'),ensure_ascii=False,indent=2));print('NOTES + 4 SVG READY')
