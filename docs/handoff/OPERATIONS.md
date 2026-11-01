# 网站、Git与恢复操作

只在改站、改文章、同步代码或部署时读取本文件。先读[快速入口](../HANDOFF.md)。

## 仓库与页面

课程在`luckyPT/silicon-baby-steps/main`维护；主站在`luckyPT/luckyPT/master`。主站首页`/`有旧博客`/blog/`与课程`/planning/`两个入口。主站现有`Publish letsgogo.top`工作流会检出课程main，构建后发布到`/planning/`。两个仓库各自维护，不新建重复仓库。

| 要做什么 | 文件入口 |
|---|---|
| 本章讲义 | `public/articles/NN.md` |
| 章节、分部、知识路线 | `src/content/catalog.ts` |
| 网站目录与路由 | `src/main.ts` |
| 通用三维场景、相机 | `src/ui/scene.ts` |
| 采样规划与关节空间图 | `src/algorithms/sampling.ts`、`src/ui/cspace.ts` |
| 11—14集时间/后处理实验 | `src/algorithms/arm-course.ts`、`src/ui/arm-course-lab.ts` |
| 成片、封面、正文图 | `public/media/NN/`、`public/media/manifest.json` |
| 原始模型、输入与数值证据 | `experiments/original/NN/`，尤其`qa/` |
| 10—14集正文图解 | `scripts/illustrate-articles-10-14.py`，输出`article-*.png` |

## 最小接手与验证

1. 查询远端main当前HEAD。先检查工作区状态；不要把旧容器目录、旧Git分支或本地未提交文件当作最新远端。
2. 只取本次相关文本/代码。文章修改不需要下载整套视频工程；首次轻量读取可直接取原始文件，不必全量克隆大媒体。
3. 修改后运行对应检查。仅文档改动检查相对链接与状态一致性；图文改动解码新PNG、核对图注与数据，再运行`npm run verify:media`和`npm run build`；算法或交互改动再运行`npm test`及相关Python核验。CI会执行完整检查。
4. 提交时只纳入本次文件，保留他人并发变更。使用最新父提交与`expected_sha`更新分支，不强推。

Node要求22.12+，当前CI用24。日常命令：

```bash
npm ci
npm test
npm run verify:media
npm run build
npm run dev
```

## 完整视频的无损分段

第10—14集原始MP4按不超过10MiB的字节段存于`course-media/NN/video.partXXX`。`course-media/manifest.json`记录每段与完整文件的大小、SHA-256。`scripts/assemble-media.mjs`无损恢复到`public/media/NN/video.mp4`；`predev`、`prebuild`、`preverify:media`会自动执行，亦可手动运行`npm run assemble:media`。

不要再把重建后的10—14集MP4提交一份。第11集原片约128MB，目前也以原字节完整保留，**没有为了上传而压缩画质**。早期“第11集需要重编码”的尝试已被无损分段方案取代。

本轮GitHub连接接口实测单次请求体上限16MiB，base64会膨胀约4/3；不要再次将整集视频作为一个`create_blob`请求。10MiB原始段可落在该上限内。以后以当前接口能力与实际错误为准，不将此限制误写成GitHub所有接口的统一限制。

文本和图片通过现有GitHub能力直接创建blob/tree/commit并更新ref即可。小文件无需恢复原始渲染工程。已有可用连接时先验证一项写入，不重复安装连接器、索要令牌或提取浏览器凭据。若常规Git凭据已可用，也可正常推送。

## 提交与部署分别完成

1. 确认课程提交已在远端main，并记录SHA。
2. 需要网站更新时，运行**主站**的`Publish letsgogo.top`，选择master。不是运行另一个课程Pages工作流来替代主站。
3. GitHub能力若没有工作流触发操作，可使用已登录浏览器中的现有“Run workflow”按钮。本操作不需要新增工作流或扩大权限。
4. 等待构建与部署成功，记录run URL。再打开`/planning/`或具体章节；文章需核验新图实际加载，视频/实验变更则做对应播放/交互检查。
5. 内容可能受缓存影响，先重载并核对实际响应；不要仅凭旧截图判断部署失败，也不要仅凭任务启动就报告上线成功。

当前主站工作流另有每6小时同步计划。用户要求立即上线时直接手动运行，不让用户等待定时任务。文档维护本身不改变课程页面，通常不需要额外重部署。

## 本轮坑点与恢复

- 临时工作区曾被重置，源码、归档和执行中的内存变量可能消失。重要成果及时形成Git提交；浏览器tab编号、运行session编号、临时下载URL不能作为交接资产。
- 大视频上传失败的根因包括接口请求体限制，不是持续的仓库权限错误。先读现有分段方案，别再次申请持久化高权限导入工作流。
- 曾观察到PNG直接写出后出现不完整IDAT校验。生成器现用内存缓冲→临时文件→原子替换；上传前用Pillow解码，比较本地Git blob SHA与返回SHA，部署后核验响应。不要只检查“文件存在”。
- 中文图解使用CJK字体；给`COURSE_CJK_FONT`指定本地Noto Sans CJK SC字体。字体为生成依赖，网页PNG不要求读者安装字体。不提交临时字体、预览拼图或浏览器授权截图。
- 云浏览器实测走SVGRenderer兼容路径，仍是同一三维场景的投影；不要将它误报成预录视频，也不要把它当作WebGL路径已经实机验证。

## 完成后的交接维护

只把**实际结果**写入`state.json`：内容提交、部署回执、验证项目、剩余事项。标明“已制作/已提交审核/已公开/已部署”的差别。新限制写入对应手册；快速入口保持一页，不追加长日志。正文历史与私有素材索引在私人交接中保存，公共仓库不加入个人联系方式、凭据或私有文件ID。
