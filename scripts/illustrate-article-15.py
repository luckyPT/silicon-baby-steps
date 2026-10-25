"""Code-native Chinese teaching diagrams for the static planning introduction."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import os,io
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/media/15';OUT.mkdir(exist_ok=True)
FP=os.environ.get('COURSE_CJK_FONT','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
C={'bg':'#071726','panel':'#102d42','line':'#3c6075','white':'#edf7ff','cyan':'#63dfd6','gold':'#ffd28a','muted':'#afc4d2','red':'#f48c85'}
def make(title,sub):
 im=Image.new('RGB',(1600,1000),C['bg']);d=ImageDraw.Draw(im);text(d,(65,45),title,48,'cyan');text(d,(65,120),sub,27,'muted');return im,d
def text(d,p,s,n=32,c='white'):d.text(p,s,font=ImageFont.truetype(FP,n),fill=C.get(c,c))
def panel(d,r):d.rounded_rectangle(r,22,fill=C['panel'],outline=C['line'],width=2)
def save(im,name):
 buf=io.BytesIO();im.save(buf,format='PNG');p=OUT/name;tmp=p.with_suffix('.pending');tmp.write_bytes(buf.getvalue());tmp.replace(p);Image.open(p).load()
im,d=make('前十四集：从通路到轨迹验收','不同模块解决不同问题；新方法也需要明确后续处理与验收职责')
rows=[('01 找通路','配置空间 / RRT系列','起点、终点之间是否存在避障连接？'),('02 改形状','删点 / 圆角 / 整段复检','路线变短或变圆之后，是否仍然有效？'),('03 排时间','梯形 / S曲线 / 时间伸缩','什么时刻到什么位置，各关节幅值是否过限？'),('04 看边界','碰撞 / 连续性 / 实机跟踪','几何可行与幅值通过，不自动等于真机放行')]
for i,(a,b,c) in enumerate(rows):
 y=205+i*175;panel(d,(65,y,1535,y+145));text(d,(95,y+20),a,35,'gold');text(d,(420,y+18),b,34);text(d,(420,y+78),c,29,'muted')
text(d,(65,940),'第四部分继续补充静态环境中的空间表示、优化与计算分配方法。',27,'muted');save(im,'article-chain.png')
im,d=make('四张需求卡：为什么继续补充规划工具箱？','这些是观察角度，可以在同一系统中组合，并非互斥分类')
for i,(a,b,c) in enumerate([('局部决策','吸引与排斥 → 人工势场','简单直观，也可能停在非目标位置'),('计算复用','建图与查询分离 → PRM','固定环境多次查询，需计入建图成本'),('轨迹质量','修改整条轨迹 → 轨迹优化','权衡平滑、间距和运动量，仍需复检'),('有限预算','排序候选与验证 → 启发式规划','考虑路径代价，也考虑计算工作')]):
 x=65+(i%2)*765;y=215+(i//2)*340;panel(d,(x,y,x+705,y+285));text(d,(x+30,y+26),a,45,'gold');text(d,(x+30,y+110),b,30);text(d,(x+30,y+185),c,27,'muted')
text(d,(65,940),'RRT系列继续有用；不同方法针对不同任务与预算作取舍。',28,'muted');save(im,'article-questions.png')
im,d=make('固定环境：先建路网，再回答不同查询','PRM机制示意；本图不是算法运行日志或性能结果')
pts=[(170,505),(410,300),(760,280),(1140,315),(1410,505),(1130,745),(760,770),(400,740)]
d.rectangle((550,405,1030,640),fill='#673d49',outline=C['red'],width=4);text(d,(675,495),'固定障碍',40)
for a,b in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,0)]:d.line([pts[a],pts[b]],fill=C['line'],width=9)
d.line([pts[i] for i in [0,1,2,3,4]],fill=C['gold'],width=12)
for x,y in pts:d.ellipse((x-13,y-13,x+13,y+13),fill=C['cyan'])
text(d,(65,865),'总成本 = 建图成本 + 各次查询成本；候选连接通过验证后才能采用。',29)
text(d,(65,932),'灰：可用连接示意   金：一次候选路线   环境或模型改变后需重新判断有效性',25,'muted');save(im,'article-roadmap.png')
im,d=make('轨迹优化：修改对象相近，数学表达与更新方式不同','示意目标 J = 长度项 + 平滑项 + 障碍项；具体方法的变量、代价和约束并不相同')
for i,(a,b,c) in enumerate([('CHOMP','梯度式轨迹改进','利用目标变化方向更新轨迹'),('STOMP','随机扰动式轨迹优化','利用带噪候选的代价信息更新轨迹'),('TrajOpt','逐次凸优化','构建并求解一系列局部近似问题'),('GPMP2','高斯过程 / 因子图','把规划表达为概率推断问题')]):
 x=65+(i%2)*765;y=220+(i//2)*310;panel(d,(x,y,x+705,y+255));text(d,(x+30,y+23),a,43,'gold');text(d,(x+30,y+104),b,32,'cyan');text(d,(x+30,y+172),c,27)
text(d,(65,895),'共同关注：初始轨迹、局部最优、碰撞与约束复检。',32,'gold');text(d,(65,950),'本集不运行这四种优化器；视频质量示例来自已验证的旧章后处理。',26,'muted');save(im,'article-optimization.png')
im,d=make('第四部分：静态环境规划加餐 · 七集地图','第15集导读；第16—21集为已确认安排，尚未全部制作或实现')
for i,(n,a,b) in enumerate([('15','为什么RRT之后还要学？','局部决策 / 复用 / 质量 / 预算'),('16','人工势场','吸引、排斥与局部极小值'),('17','PRM / Lazy PRM','路网复用与延迟验证'),('18','CHOMP / STOMP','梯度改进与随机扰动'),('19','TrajOpt / GPMP2','逐次凸优化与概率推断'),('20','FMT* / BIT*','批量采样与搜索'),('21','AIT* / EIT* / MIT*','启发信息与计算分配；MIT*为较新进展')]):
 y=205+i*99;panel(d,(65,y,1535,y+81));text(d,(90,y+12),n,33,'gold');text(d,(190,y+13),a,31,'cyan');text(d,(805,y+17),b,27)
text(d,(65,940),'动态环境、增量修复与在线重规划，后续单独开章。',29,'muted');save(im,'article-course.png')
print('Five Chinese PNGs generated and decoded')
