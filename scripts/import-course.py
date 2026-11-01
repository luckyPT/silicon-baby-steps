"""Import previously authored publication archives and locally materialized videos.
Usage: python3 scripts/import-course.py /path/to/course_materials
No platform credentials or Library identifiers are required or stored.
"""
from pathlib import Path
import json,sys,re,zipfile,shutil,subprocess,hashlib
from PIL import Image,ImageOps
B=Path(__file__).resolve().parents[1];source=Path(sys.argv[1]) if len(sys.argv)>1 else B.parent/'course_materials';manifest=[]
for num in range(1,10):
 id=f'{num:02}';dest=B/'public/media'/id;dest.mkdir(parents=True,exist_ok=True)
 if num<9:
  archive=next(source.rglob(f'sibao_lesson{id}*.zip'));z=zipfile.ZipFile(archive);article=json.loads(z.read(next(x for x in z.namelist()if x.endswith('article.json'))));(B/f'public/articles/{id}.json').write_text(json.dumps(article,ensure_ascii=False,indent=2))
  image_names=set()
  if 'sections' in article:
   for section in article['sections']:
    if section.get('image'):image_names.add(Path(section['image']).name)
  else:
   for block in article['blocks']:
    if block['type']=='image':image_names.add(Path(block['file']).name)
  for name in image_names:
   member=next(x for x in z.namelist()if Path(x).name==name);(dest/name).write_bytes(z.read(member))
  out=['# '+article['title'],'']
  def add_image(name,caption):out.extend([f'![{caption}](../media/{id}/{Path(name).name})',f'*{caption}*',''])
  if 'sections' in article:
   for section in article['sections']:
    if section.get('heading'):out.extend(['## '+section['heading'],''])
    for p in section.get('paragraphs',[]):out.extend([p,''])
    if section.get('image'):add_image(section['image'],section.get('caption',''))
  else:
   for block in article['blocks']:
    typ=block['type']
    if typ=='image':add_image(block['file'],block.get('caption',''))
    elif typ=='h2':out.extend(['## '+block['text'],''])
    elif typ=='h3':out.extend(['### '+block['text'],''])
    elif typ=='p':out.extend([block['text'],''])
    else:raise ValueError(f'Unhandled article block type: {typ}')
  original=B/'docs/articles-original';original.mkdir(parents=True,exist_ok=True);(original/f'{id}.txt').write_bytes(z.read(next(x for x in z.namelist()if x.endswith('article.txt'))))
  choices=[x for x in z.namelist()if x.lower().endswith(('.jpg','.png'))and ('cover_1920x1080' in x or 'cover_douyin_horizontal' in x or 'douyin_cover_1440x1080' in x)]
  if choices:
   import io
   cover=Image.open(io.BytesIO(z.read(choices[-1]))).convert('RGB')
  else:cover=Image.open(B.parent/f'sibao_lesson{id}/cover_1920x1080.jpg').convert('RGB')
 else:
  lesson=json.loads((B.parent/'sibao_lesson09/lesson.json').read_text());out=['# RRT*：路找到了，能不能少绕一点？','']
  for ch in lesson:
   out.extend(['## '+ch['title'],''])
   sentences=re.split(r'(?<=[。？！])',ch['text'].replace('Informed，RRT星','Informed RRT*').replace('RRT星','RRT*'))
   paragraph=''
   for sentence in sentences:
    if len(paragraph)+len(sentence)>150 and paragraph:out.extend([paragraph,'']);paragraph=''
    paragraph+=sentence
   if paragraph.strip():out.extend([paragraph.strip(),''])
   name={'parent':'parent_chosen','rewire':'rewire_changed','children':'child_changed','improve':'curve_final','experiment':'experiment','limits':'execution'}.get(ch['id'])
   if name:
    shutil.copy2(B.parent/f'sibao_lesson09/qa/{name}.jpg',dest/f'{name}.jpg');add_image(f'{name}.jpg',ch['title'])
  out.extend(['## 用代码把两笔账写清楚','','```python','g_new = g[parent] + distance(parent, q_new)','# choose parent: minimize g[parent] + edge_cost, subject to collision-free edge','# rewire: if g_new + distance(q_new, q_old) < g[q_old], change parent','# propagate the cost change to every descendant; keep the tree acyclic','```','','本节视频实验按每次6000次整段运动验证预算比较；网站交互实验可调采样迭代预算，同时分别显示验证次数。两种预算口径不同，不能把网站动画当作视频中的逐帧实验重放。','','## 技术参考','','- [Karaman与Frazzoli：Sampling-based Algorithms for Optimal Motion Planning](https://arxiv.org/abs/1105.1186)','- [Revisiting the Asymptotic Optimality of RRT*](https://arxiv.org/abs/1909.09688)','- [OMPL RRTstar 实现](https://ompl.kavrakilab.org/RRTstar_8cpp_source.html)',''])
  cover=Image.open(B.parent/'sibao_lesson09/cover_1920x1080.jpg').convert('RGB')
 out.extend(['## 亲手做一组对照','','[打开本节交互实验室](#/lesson/'+id+'/lab)。所有算法在浏览器中实际运行；三维区域支持左键旋转、右键平移与滚轮缩放。','','实验参数和预算口径以实验界面说明为准。机械臂的真实姿态在三维世界展示，搜索变量仍是两个关节角；三维空间场景则以(x,y,z)为状态。',''])
 (B/f'public/articles/{id}.md').write_text('\n'.join(out))
 fitted=ImageOps.contain(cover,(1920,1080),Image.Resampling.LANCZOS);canvas=Image.new('RGB',(1920,1080),'#071525');canvas.paste(fitted,((1920-fitted.width)//2,(1080-fitted.height)//2));canvas.save(dest/'cover.jpg',quality=92)
 video=(B.parent/'sibao_lesson09/sibao_lesson09_review.mp4')if num==9 else next(source.rglob(f'sibao_lesson{id}_review.mp4'));shutil.copy2(video,dest/'video.mp4')
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(dest/'video.mp4')]));v=next(x for x in info['streams']if x['codec_type']=='video');duration=float(info['format']['duration']);manifest.append({'id':id,'article':f'articles/{id}.md','video':f'media/{id}/video.mp4','cover':f'media/{id}/cover.jpg','durationSeconds':duration,'bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'width':v['width'],'height':v['height']});print(id,round(duration,2),video.stat().st_size)
(B/'public/media/manifest.json').write_text(json.dumps({'chapters':manifest,'content':'Full locally hosted MP4 files; not temporary links','updated':'2026-10-22'},ensure_ascii=False,indent=2))
