# TeamFilePermissionCenter 文档索引

本目录存放“团队比赛项目文件权限中心”的产品/技术说明与配套图。

## 快速入口

- 说明书（含权限矩阵表）：[spec/项目说明书.md](spec/项目说明书.md)
- API 设计（后端接口草案）：[spec/API设计.md](spec/API设计.md)
- 界面信息架构（含回收站多入口）：[spec/界面信息架构.md](spec/界面信息架构.md)
- 流程/时序图（集中展示）：[diagrams/流程与时序.md](diagrams/流程与时序.md)
- 数据流向图（集中展示）：[diagrams/数据流向.md](diagrams/数据流向.md)

## 架构与数据模型图

- 系统总体架构图：[diagrams/系统总体架构图.md](diagrams/系统总体架构图.md)
- 部署拓扑图（Linux）：[diagrams/部署拓扑图.md](diagrams/部署拓扑图.md)
- ER 图（核心数据模型）：[diagrams/ER图.md](diagrams/ER图.md)
- 权限继承/覆盖图：[diagrams/权限继承与覆盖图.md](diagrams/权限继承与覆盖图.md)
- 个人区访问策略图：[diagrams/个人区访问策略图.md](diagrams/个人区访问策略图.md)

## 目录结构约定

- `docs/spec/`：说明书与规格（文字为主，必要处链接到图）
- `docs/diagrams/`：所有图（Mermaid 源码，便于版本迭代）

## MinIO（Linux 测试/部署提醒）

当前文件中心的“上传/下载”走 MinIO（S3 兼容对象存储）：后端把文件写入 MinIO，并返回浏览器可直接访问的 presigned 下载链接。

### 后端需要的环境变量

在 Linux 部署时，请在后端环境中配置：

- `MINIO_ENDPOINT`：MinIO 服务地址（例如 `127.0.0.1:9000` 或 `minio:9000`）
- `MINIO_PUBLIC_ENDPOINT`：给浏览器访问的地址（生成 presigned URL 用）
	- 如果前端用户访问域名是 `minio.example.com`，这里应填 `minio.example.com`
	- 如果 MinIO 只在内网容器网络可见，需要通过 Nginx/域名暴露给浏览器访问
- `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`
- `MINIO_BUCKET`：默认 `tfpc`
- `MINIO_SECURE`：`1` 表示 https，`0` 表示 http

### 快速启动（示例）

Docker 方式（示例，端口/路径按实际调整）：

```bash
docker run -d --name tfpc-minio \
	-p 9000:9000 -p 9001:9001 \
	-e MINIO_ROOT_USER=minioadmin \
	-e MINIO_ROOT_PASSWORD=minioadmin \
	-v /data/tfpc-minio:/data \
	minio/minio server /data --console-address ":9001"
```

### 注意事项

- presigned URL 必须让“浏览器能访问到 MinIO”：`MINIO_PUBLIC_ENDPOINT` 要填对。
- 如果用了 Nginx 反代 MinIO，记得把 MinIO 的访问域名/端口与 `MINIO_PUBLIC_ENDPOINT` 对齐。
- bucket 会在首次上传时自动创建（代码会确保 bucket 存在）。
