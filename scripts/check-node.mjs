const [major, minor] = process.versions.node.split(".").map(Number);
if (major < 22 || (major === 22 && minor < 12)) {
  console.error(
    "需要 Node.js 22.12+（推荐24 LTS）。请从 https://nodejs.org/ 安装后重试。",
  );
  process.exit(1);
}
