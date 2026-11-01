"""Create inline Chinese teaching figures from the archived course models.

Run from any directory with COURSE_CJK_FONT pointing to a CJK OpenType font:
  COURSE_CJK_FONT=/path/to/NotoSansCJKsc-Regular.otf python scripts/illustrate-articles-10-14.py
Noto CJK is available under the SIL Open Font License from github.com/notofonts/noto-cjk.
This script only writes article PNGs; it never changes algorithm inputs or reports.
"""
from pathlib import Path
import os, sys, json, importlib.util, io
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Circle, Ellipse

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / 'experiments/original'
font_path = os.environ.get('COURSE_CJK_FONT')
if font_path:
    fm.fontManager.addfont(font_path)
    family = fm.FontProperties(fname=font_path).get_name()
else:
    family = fm.FontProperties(fname=fm.findfont('Noto Sans CJK SC', fallback_to_default=False)).get_name()
plt.rcParams.update({
    'font.family': family, 'font.size': 17, 'axes.titlesize': 21,
    'axes.labelsize': 17, 'xtick.labelsize': 14, 'ytick.labelsize': 14,
    'legend.fontsize': 14, 'figure.facecolor': '#f3f6fb',
    'axes.facecolor': '#ffffff', 'text.color': '#173149',
    'axes.labelcolor': '#173149', 'xtick.color': '#496174',
    'ytick.color': '#496174', 'axes.edgecolor': '#b5c4cf',
    'grid.color': '#dde5ed', 'axes.unicode_minus': False,
    'lines.linewidth': 3, 'savefig.facecolor': '#f3f6fb',
})
C = {'teal': '#087f8c', 'orange': '#dc8c16', 'red': '#ce4856',
     'green': '#228362', 'purple': '#7959bd', 'gray': '#8194a4', 'ink': '#173149'}
generated = []

def load(n, name):
    return json.loads((E / str(n) / name).read_text())

def model(n):
    spec = importlib.util.spec_from_file_location(f'article_motion_{n}', E / str(n) / 'motion.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def figure(title, rows=1, height=None):
    fig, axes = plt.subplots(rows, 1, figsize=(8.6, height or (5.5 if rows == 1 else 9)), squeeze=False)
    fig.suptitle(title, fontsize=23, fontweight='bold', y=.985)
    return fig, axes[:, 0]

def save(n, name, fig):
    selected = os.environ.get('COURSE_FIGURE_ONLY')
    if selected and selected != name:
        plt.close(fig)
        return
    fig.tight_layout(rect=[0, .14 if name == 'article-ellipse' else .01, 1, .95], h_pad=1.7)
    p = ROOT / 'public/media' / str(n) / f'{name}.png'
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=160, metadata={'Software': 'Silicon Baby Steps / Matplotlib'})
    temporary = p.with_suffix('.png.new')
    temporary.write_bytes(buffer.getvalue())
    os.replace(temporary, p)
    plt.close(fig)
    generated.append(str(p.relative_to(ROOT)))

def clean(ax, xlabel='', ylabel=''):
    ax.set(xlabel=xlabel, ylabel=ylabel)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(alpha=.7)
    ax.set_axisbelow(True)

def label(ax, text, xy, xytext, color='ink', **kwargs):
    ax.annotate(text, xy=xy, xytext=xytext, color=C[color], fontsize=16,
                arrowprops={'arrowstyle': '->', 'color': C[color], 'lw': 1.5},
                bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': .92, 'pad': 3}, **kwargs)

def curve(parts, steps=800):
    out = []
    for part in parts:
        p = np.array(part['controls_deg']); u = np.linspace(0, 1, steps)[:, None]
        q = ((1-u)*p[0]+u*p[1] if part['kind'] == 'line' else
             (1-u)**2*p[0]+2*u*(1-u)*p[1]+u*u*p[2])
        out.extend(q if not out else q[1:])
    return np.array(out)

post = load(11, 'qa/postprocess_validation.json')
run = load(10, 'assets/informed_run.json')
validation = load(10, 'qa/algorithm_validation.json')
report14 = load(14, 'qa/motion_validation.json')
m12, m14 = model(12), model(14)
sys.path.insert(0, str(E / '10'))
from rrt import clearances

def collision_map(ax):
    a = np.linspace(-54, -23, 320); b = np.linspace(85, 153, 420)
    x, y = np.meshgrid(a, b)
    z = clearances(np.radians(np.column_stack([x.ravel(), y.ravel()]))).reshape(x.shape)
    ax.contourf(x, y, z, levels=[-2, 0], colors=['#f8dce1'], alpha=.8)
    ax.contour(x, y, z, levels=[0], colors=['#cf6c79'], linewidths=1)
    ax.axhspan(150, 153, color='#dce2e8', alpha=.8)
    ax.set(xlim=(-54, -23), ylim=(85, 153))
    clean(ax, '关节 θ1 / °', '关节 θ2 / °')

def arm(ax, q, title, color='teal'):
    q = np.radians(q); elbow = np.array([np.cos(q[0]), np.sin(q[0])])
    tip = elbow + [np.cos(q.sum()), np.sin(q.sum())]
    points = np.array([[0, 0], elbow, tip])
    ax.add_patch(Circle((.9, .5), .15, fc='#f5d099', ec=C['orange'], lw=2, zorder=2))
    ax.plot(points[:, 0], points[:, 1], color=C[color], lw=13, solid_capstyle='round', zorder=3)
    ax.scatter(points[:, 0], points[:, 1], s=[180, 120, 90], c='white', edgecolors=C[color], linewidths=2, zorder=4)
    ax.set(title=title, xlim=(-.3, 1.7), ylim=(-1.05, 1.05), aspect='equal')
    clean(ax, '工作空间 x / m', 'y / m')

# Episode 10: lower-bound geometry, direct sampling, whole-arm collision, seed comparison.
f, (ax,) = figure('10 · 有希望的区域，为什么是椭圆？')
t = np.linspace(0, 2*np.pi, 600)
for best, col in [(80, 'orange'), (70, 'teal')]:
    aa = best/2; bb = np.sqrt(best*best-60*60)/2
    ax.fill(-30+bb*np.sin(t), 120+aa*np.cos(t), color=C[col], alpha=.10)
    ax.plot(-30+bb*np.sin(t), 120+aa*np.cos(t), c=C[col], label=f'当前最好长度 {best}°')
ax.scatter([-30, -30], [90, 150], c=C['ink'], s=65, zorder=5)
ax.text(-28, 90, '起点', fontsize=16); ax.text(-28, 149, '目标', fontsize=16)
ax.axhspan(150, 164, color='#bac5cf', alpha=.35)
ax.axhline(150, color=C['gray'], ls='--', lw=1.3)
ax.text(-66, 160, '灰区：超出本例关节范围，要重新采样', fontsize=13)
ax.annotate('', xy=(-30, 160), xytext=(-30, 120), arrowprops={'arrowstyle':'<->','color':C['orange'],'lw':2})
ax.text(-28, 127, '80°时\na = 40°\nb ≈ 26.46°', color=C['orange'], fontsize=16)
ax.set(xlim=(-70, 10), ylim=(76, 164)); clean(ax, '关节 θ1 / °', '关节 θ2 / °')
ax.set_aspect('equal', adjustable='box')
f.legend(*ax.get_legend_handles_labels(), loc='lower center', bbox_to_anchor=(.5,.012), ncol=2, fontsize=13)
save(10, 'article-ellipse', f)

rng = np.random.default_rng(20261024); r = np.sqrt(rng.random(800)); angle = rng.uniform(0, 2*np.pi, 800)
u = np.column_stack([r*np.cos(angle), r*np.sin(angle)])
f, axs = figure('10 · 直接采样：圆盘 → 拉伸 → 旋转平移', rows=3, height=11.5)
datasets = [u, u*[40, np.sqrt(700)], np.column_stack([-30-u[:, 1]*np.sqrt(700), 120+u[:, 0]*40])]
for i, (ax, q) in enumerate(zip(axs, datasets)):
    ax.scatter(q[:,0], q[:,1], s=7, color=C['teal'], alpha=.42)
    ax.set_title(['① 单位圆盘均匀采样：r = √U', '② 沿两个半轴拉伸：40、26.46', '③ 旋转90°，移到起终点中间'][i], loc='left', fontsize=18)
    clean(ax, ['x', '局部横轴 / °', '关节 θ1 / °'][i], ['y', '局部纵轴 / °', '关节 θ2 / °'][i])
    ax.set_aspect('equal', adjustable='box')
    if i == 0: ax.set(xlim=(-1.1,1.1), ylim=(-1.1,1.1))
    elif i == 1: ax.set(xlim=(-44,44), ylim=(-30,30))
    else: ax.set(xlim=(-62,2), ylim=(76,164))
axs[2].axhline(150, color=C['red'], ls='--', lw=1.5)
axs[2].text(-68, 155, '界外点拒绝，不能夹到边界', fontsize=13, color=C['red'])
save(10, 'article-sampling', f)

f, axs = plt.subplots(1, 3, figsize=(11.4, 5.0))
f.suptitle('10 · 两端都安全，连接中间却会撞', fontsize=23, fontweight='bold')
for ax, q, title, color in zip(axs, [[-30,90],[-30,120],[-30,150]], ['起点：安全','中间：碰撞','目标：安全'], ['teal','red','teal']):
    arm(ax, q, title, color); ax.set_xlabel(''); ax.set_ylabel(''); ax.set_xticks([]); ax.set_yticks([])
    ax.text(.5, -.08, f'q = ({q[0]}°, {q[1]}°)', transform=ax.transAxes, ha='center', fontsize=15)
save(10, 'article-arm-collision', f)

stats = validation['stats']; f, (ax,) = figure('10 · 同为6000次整段验证，三组结果都保留')
x = np.arange(3)
for off, inds, name, col in [(-.19, [0,2,4], 'RRT*', 'orange'), (.19,[1,3,5], 'Informed RRT*','teal')]:
    values = [stats[i]['best_cost_degrees'] for i in inds]
    bars = ax.bar(x+off, values, .36, color=C[col], label=name)
    ax.bar_label(bars, labels=[f'{v:.2f}°' for v in values], padding=5, fontsize=15)
ax.set(xticks=x, xticklabels=['种子 1', '种子 7', '种子 42'], ylim=(0, 91))
clean(ax, '', '关节空间路径长度 / °'); ax.set_ylim(0,102); ax.legend(loc='upper center', ncol=2)
save(10, 'article-seeds', f)

# Episode 11: raw/shortcut, two blends, physical poses, conservative clearance.
f, (ax,) = figure('11 · 少两个点，只省了约0.019°')
collision_map(ax)
for key, name, col, marker in [('original', '原始5点：68.870810°', 'gray', 'o'), ('shortcut', '简化3点：68.851578°', 'teal', 's')]:
    q = np.array(post['original_vertices_deg'] if key == 'original' else post['shortcut_vertices_deg'])
    ax.plot(q[:,0], q[:,1], c=C[col], marker=marker, ms=8, label=name)
ax.text(-52, 146, '淡红：碰撞配置', color=C['red'], fontsize=14)
ax.legend(loc='lower left', fontsize=14); save(11, 'article-shortcut', f)

f, (ax,) = figure('11 · 圆角更大、更短，也可能切进障碍')
collision_map(ax)
for key, name, col in [('shortcut','简化折线','gray'),('aggressive_blend_alpha_0_5','大圆角 α=0.5：碰撞','red'),('accepted_blend_alpha_0_25','小圆角 α=0.25：采用','teal')]:
    q = curve(post['paths'][key]); ax.plot(q[:,0], q[:,1], c=C[col], label=name, lw=3)
critical = post['metrics']['aggressive_blend_alpha_0_5']['critical_q_deg']
ax.scatter(*critical, marker='x', c=C['red'], s=130, lw=3, zorder=5)
ax.legend(loc='lower left', fontsize=14); save(11, 'article-blends', f)

f, axs = figure('11 · 检查整条胳膊，而不只是检查端点', rows=2, height=9.5)
for ax, key, title, col in [(axs[0],'aggressive_blend_alpha_0_5','大圆角的最小间距姿态：发生碰撞','red'),(axs[1],'accepted_blend_alpha_0_25','小圆角的最小间距姿态：保留余量','teal')]:
    arm(ax, post['metrics'][key]['critical_q_deg'], title, col)
save(11, 'article-recheck', f)

f, (ax,) = figure('11 · 采用方案还要通过10mm教学余量')
keys=['original','shortcut','accepted_blend_alpha_0_25','aggressive_blend_alpha_0_5']
vals=np.array([post['metrics'][k]['model_clearance_lower_bound_m']*1000 for k in keys])
bars=ax.barh(['原始折线','快捷连接','小圆角 α=0.25','大圆角 α=0.5'], vals, color=[C['gray'],C['purple'],C['teal'],C['red']])
for i,v in enumerate(vals): ax.text(v+.8 if v>=0 else .8, i, f'{v:.2f} mm', va='center', fontsize=16, color=C['red'] if v<0 else C['ink'])
ax.axvline(0, color=C['ink'], lw=1); ax.axvline(10, color=C['green'], ls='--', lw=2, label='10mm 教学阈值')
ax.invert_yaxis(); ax.set_xlim(-22, 33); clean(ax, '整段路径的间距保守下界 / mm', '')
ax.legend(loc='lower right'); save(11, 'article-clearance', f)

# Episode 12: same geometry, ideal endpoint jumps, area accounting, short task.
t = np.linspace(0, 6, 1001); s, v, a = m12.scalar(t)
f, axs = figure('12 · 路径决定经过哪里，时间表决定何时到达', rows=2, height=9)
q=curve(post['paths']['accepted_blend_alpha_0_25'])
axs[0].plot(q[:,0], q[:,1], c=C['gray'])
for progress, name in [(0,'起点 s=0'),(.5,'中途 s=0.5'),(1,'终点 s=1')]:
    z=m12.q_at(progress); axs[0].scatter(*z,s=75,color=C['teal']);axs[0].annotate(name,z,xytext=(7,7),textcoords='offset points',fontsize=15)
clean(axs[0], 'θ1 / °', 'θ2 / °')
axs[1].plot(t,t/6,c=C['purple'],label='6秒匀速参考');axs[1].plot(t,s,c=C['teal'],label='6秒梯形方案')
axs[1].axvline(1,c=C['gray'],lw=1,ls='--');axs[1].scatter([1,1],[1/6,.0625],c=[C['purple'],C['teal']],s=60)
clean(axs[1], '共同时间 / s', '路径进度 s');axs[1].legend(loc='lower right')
save(12, 'article-path-clock', f)

f, (ax,) = figure('12 · 匀速的难题，出在起步和停车')
ax.plot([-.4,0,0,6,6,6.4],[0,0,1/6,1/6,0,0],c=C['purple'],label='理想匀速参考')
tt=np.linspace(-.4,6.4,1001);ax.plot(tt,m12.scalar(tt)[1],c=C['teal'],label='梯形速度')
label(ax,'起步速度跳变',(0,.13),(1,.08),'purple');label(ax,'到站速度跳变',(6,.12),(3.9,.05),'purple')
clean(ax,'时间 / s','进度速度 / 1/s');ax.set_ylim(-.015,.31);ax.legend(loc='upper right')
save(12,'article-start-stop',f)

f,(ax,)=figure('12 · 速度曲线下的面积，刚好等于总进度1')
for lo,hi,col,name,xy in [(0,2,'purple','加速\n0.25',(1,.06)),(2,4,'teal','保持\n0.50',(3,.11)),(4,6,'orange','减速\n0.25',(5,.06))]:
    mask=(t>=lo)&(t<=hi);ax.fill_between(t[mask],v[mask],color=C[col],alpha=.25);ax.text(*xy,name,ha='center',fontsize=20,color=C[col])
ax.plot(t,v,c=C['ink']);ax.set(xticks=[0,2,4,6],ylim=(0,.30));clean(ax,'2秒加速 + 2秒保持 + 2秒减速','进度速度 / 1/s')
save(12,'article-trapezoid-area',f)

f,axs=figure('12 · 短任务跑不到速度上限，梯形变三角形',rows=2,height=9)
for ax,p,title,col in [(axs[0],m12.FULL,'完整任务 D=1：6秒','teal'),(axs[1],m12.SHORT,'短任务 D=0.25：约2.83秒','orange')]:
    tt=np.linspace(0,p['T'],700);vv=m12.scalar(tt,p)[1]
    ax.fill_between(tt,vv,color=C[col],alpha=.17);ax.plot(tt,vv,c=C[col]);ax.axhline(.25,c=C['gray'],ls='--',lw=1.5)
    ax.set(title=title,xlim=(0,6.2),ylim=(0,.31));clean(ax,'时间 / s','进度速度 / 1/s')
    ax.text(3,.27,'上限 0.25/s',fontsize=14,color=C['gray'])
label(axs[1],'峰值约 0.1768/s',(np.sqrt(2),np.sqrt(.03125)),(2.4,.12),'orange')
save(12,'article-short-task',f)

# Episode 13: acceleration continuity, seven phases, same task durations, curvature join.
tt=np.linspace(-.25,7.25,2001);ss,vv,aa,jj=m14.s_curve(tt);tr=m14.trapezoid(tt)
f,(ax,)=figure('13 · 速度接上了，加速度却还在跳台阶')
ax.plot(tt,tr[2],c=C['orange'],label='梯形：加速度有跳变');ax.plot(tt,aa,c=C['teal'],label='S曲线：进度加速度连续')
clean(ax,'时间 / s','进度加速度 / 1/s²');ax.set_ylim(-.18,.19);ax.legend(loc='upper right',fontsize=13)
save(13,'article-acceleration',f)

f,axs=figure('13 · 七段S曲线：每段1秒，积分连续交接',rows=2,height=9)
for ax in axs:
    for i in range(7):ax.axvspan(i,i+1,color=C['teal'] if i%2==0 else C['gray'],alpha=.06)
    ax.set(xticks=np.arange(8),xlim=(0,7));ax.axhline(0,c=C['gray'],lw=1)
axs[0].plot(tt,aa,c=C['teal']);clean(axs[0],'时间 / s','进度加速度 / 1/s²')
axs[1].step(np.arange(8),[.125,0,-.125,0,-.125,0,.125,0],where='post',c=C['purple'])
for i,y in enumerate([.125,0,-.125,0,-.125,0,.125]):axs[1].text(i+.5,y+(.022 if y>=0 else -.045),str(i+1),ha='center',fontsize=18,color=C['purple'])
axs[1].set_ylim(-.2,.21);clean(axs[1],'数字1—7表示七个阶段','进度 jerk / 1/s³')
save(13,'article-seven-phases',f)

f,(ax,)=figure('13 · 同一条路径：这组参数下，6秒与7秒')
ax.plot(tt,tr[1],c=C['orange'],ls='--',label='梯形：6秒完成')
ax.plot(tt,vv,c=C['teal'],label='S曲线：7秒完成')
for lo,hi,text,x in [(0,3,'0.375',1.9),(3,4,'0.25',3.5),(4,7,'0.375',5.1)]:
    mask=(tt>=lo)&(tt<=hi);ax.fill_between(tt[mask],vv[mask],color=C['teal'],alpha=.13)
    ax.text(x,.07,text,ha='center',fontsize=19,color=C['teal'])
ax.set_ylim(-.01,.34);clean(ax,'时间 / s','进度速度 / 1/s');ax.legend(loc='upper right',fontsize=13)
save(13,'article-duration',f)

join_t=report14['all_path_joins_checked_on_both_sides'][0]['base_time']
local_t=np.linspace(join_t-.15,join_t+.15,1001);q,qv,qa,*_=m14.joint_state(local_t)
f,axs=figure('13 · 标量S曲线平顺，不等于关节加速度连续',rows=2,height=9)
for i,col in [(0,'teal'),(1,'purple')]:
    axs[0].plot(local_t,qv[:,i],c=C[col],label=f'θ{i+1}');axs[1].plot(local_t,qa[:,i],c=C[col],label=f'θ{i+1}')
for ax in axs:ax.axvline(join_t,c=C['red'],ls='--',lw=1.5);ax.legend(loc='upper left');ax.ticklabel_format(useOffset=False,axis='x')
clean(axs[0],'时间 / s','关节速度 / °/s');clean(axs[1],'时间 / s','关节加速度 / °/s²')
label(axs[1],'几何接缝：左右极限不同',(join_t,4),(join_t+.025,2),'red')
save(13,'article-geometry-join',f)

# Episode 14: chain-rule terms, precise peaks, time scaling, retained discontinuity.
t=np.linspace(0,7,2201);ss,vv,aa,jj=m14.s_curve(t);q,qs,qss=m14.path_derivatives(ss)
curvature=qss[:,0]*vv**2;timing=qs[:,0]*aa
f,(ax,)=figure('14 · 关节加速度，必须把两项一起算')
ax.fill_between(t,curvature,color=C['orange'],alpha=.18)
ax.fill_between(t,timing,color=C['teal'],alpha=.18)
ax.plot(t,curvature,c=C['orange'],label='路径弯曲项 qss × (ds/dt)²')
ax.plot(t,timing,c=C['teal'],label='进度加减速项 qs × d²s/dt²')
ax.plot(t,curvature+timing,c=C['purple'],lw=3.5,label='两项相加：θ1的加速度')
clean(ax,'时间 / s','关节加速度 / °/s²');ax.legend(loc='upper left',fontsize=13)
save(14,'article-chain-rule',f)

base_v=np.array([x['abs_peak'] for x in report14['original_peaks']['velocity']]);base_a=np.array([x['abs_peak'] for x in report14['original_peaks']['acceleration']])
ratios=np.r_[base_v/12,base_a/20];values=np.r_[base_v,base_a]
f,(ax,)=figure('14 · 原始7秒方案：两根轴卡在不同项目')
names=['θ1 速度','θ2 速度','θ1 加速度','θ2 加速度'];y=np.arange(4)
bars=ax.barh(y,ratios,color=[C['red'] if z>1 else C['green'] for z in ratios],height=.6)
ax.bar_label(bars,labels=[f'{z:.2f}'+(' °/s' if i<2 else ' °/s²') for i,z in enumerate(values)],padding=8,fontsize=16)
ax.axvline(1,c=C['ink'],ls='--',lw=2);ax.text(1.02,3.65,'限值 = 1倍',fontsize=14)
ax.set(yticks=y,yticklabels=names,xlim=(0,1.95),ylim=(-.65,3.95));ax.invert_yaxis();clean(ax,'峰值 ÷ 对应教学限值','')
save(14,'article-original-limits',f)

f,axs=figure('14 · 所有关节共享时间轴，一起拉长1.5倍',rows=2,height=9)
for ax,time,stretch,title in [(axs[0],3.5,1,'原方案 t=3.5秒'),(axs[1],5.25,1.5,'拉长后 t=5.25秒：同一姿态')]:
    pose=m14.joint_state(time,stretch)[0];arm(ax,pose,title,'teal')
assert np.allclose(m14.joint_state(3.5)[0],m14.joint_state(5.25,1.5)[0])
save(14,'article-same-pose',f)

f,(ax,)=figure('14 · 7秒 → 10.5秒，四项幅值重新过关')
scaled=np.r_[np.array(report14['adjusted_peak_velocity_deg_s'])/12,np.array(report14['adjusted_peak_acceleration_deg_s2'])/20]
ax.barh(y-.18,ratios,.32,color=C['orange'],label='原始 k=1')
bars=ax.barh(y+.18,scaled,.32,color=C['teal'],label='统一伸缩 k=1.5')
ax.bar_label(bars,labels=[f'{z:.2f}倍' for z in scaled],padding=6,fontsize=15)
ax.axvline(1,c=C['red'],ls='--',lw=2,label='教学限值')
ax.set(yticks=y,yticklabels=names,xlim=(0,1.8));ax.invert_yaxis();clean(ax,'峰值 ÷ 对应教学限值','');ax.legend(loc='lower right',fontsize=13)
save(14,'article-stretched-limits',f)

f,(ax,)=figure('14 · 放慢会减小加速度跳变，但不会消除')
progress=np.linspace(.42,.455,700);lo=np.zeros_like(progress);hi=np.full_like(progress,7.)
for _ in range(55):
    mid=(lo+hi)/2;mask=m14.s_curve(mid)[0]<progress;lo=np.where(mask,mid,lo);hi=np.where(mask,hi,mid)
times=(lo+hi)/2
for stretch,col,name in [(1,'orange','原始 k=1'),(1.5,'teal','放慢 k=1.5')]:
    accel=m14.joint_state(times*stretch,stretch)[2][:,0];ax.plot(progress,accel,c=C[col],label=name)
ax.axvline(m14.JOINS[0],c=C['gray'],ls='--',lw=1.5)
clean(ax,'同一几何位置：路径进度 s','θ1 加速度 / °/s²');ax.legend(loc='upper left')
save(14,'article-remaining-jump',f)

print(json.dumps({'figures': generated, 'count': len(generated)}, ensure_ascii=False, indent=2))
