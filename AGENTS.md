# 维护约定

先读 `docs/HANDOFF.md`（一页快速交接），再按当前任务只选读对应手册与源文件。不要默认加载完整聊天、历史交接、全部视频工程或大型媒体。任务完成后更新 `docs/handoff/state.json` 的已验证事实、证据及未完成项。

- 在现有luckyPT/silicon-baby-steps维护，每章保留结构化文章、完整视频、可运行实验及有条件的对比。
- 后续不在头条号发布新配套文章，Git讲义继续维护，不删除旧文章。
- 原始MP4无损分段存于course-media，dev/build/verify:media前自动重建；不要把生成的10—14集MP4重复提交。
- 改动模型后运行npm test、npm run verify:media、npm run build；必要时复算Python。
- 提交与letsgogo.top/planning/部署分别核验；主站联合构建位于luckyPT/luckyPT。
- 音画、角色、封面与平台约定见docs/WORKFLOW.md。
