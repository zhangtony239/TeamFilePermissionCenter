# API 设计（草案）

> 目标：提供稳定的前后端协作接口，覆盖：鉴权、项目/成员、文件操作（含 Range 预览）、ACL、回收站、审计、检索、备份。

## 0. 约定

- 基础路径：`/api/v1`
- 认证：建议 `Authorization: Bearer <token>`（或 Session Cookie；二选一）
- 响应格式：
  - 成功：`{ "ok": true, "data": ... }`
  - 失败：`{ "ok": false, "error": { "code": "...", "message": "...", "details": ... } }`
- 常见错误码：
  - `AUTH_REQUIRED`（未登录）
  - `AUTH_FORBIDDEN`（无权限）
  - `NOT_FOUND`（资源不存在）
  - `PATH_INVALID`（路径非法/越界）
  - `CONFLICT`（冲突，如重名）
  - `VALIDATION_ERROR`（参数校验失败）

## 1. 鉴权 Auth

### 1.1 登录
- `POST /api/v1/auth/login`
  - body: `{ "username": "...", "password": "..." }`
  - resp.data: `{ "token": "...", "user": {"id":1,"username":"...","display_name":"..."} }`

### 1.2 当前用户
- `GET /api/v1/auth/me`

### 1.3 登出
- `POST /api/v1/auth/logout`

## 2. 项目与成员 Projects

### 2.1 项目列表/创建
- `GET /api/v1/projects`
- `POST /api/v1/projects`
  - body: `{ "code": "PRJ2025...", "name": "...", "description":"...", "status": "ACTIVE", "start_date":"2025-07-14", "end_date":"2025-09-01", "competition_stage":"SCHOOL|CITY|PROVINCE|NATIONAL", "progress_percent": 45 }`

### 2.2 项目详情/更新
- `GET /api/v1/projects/{projectId}`
- `PATCH /api/v1/projects/{projectId}`

项目详情建议返回字段（用于“项目管理页右侧详情”）：
- `code` 编码
- `description` 描述
- `created_at` 创建日期
- `start_date`/`end_date` 起止日期
- `competition_stage` 当前比赛阶段（校/市/省/国）
- `progress_percent` 进度（0-100）
- `members_count` 成员数（列表页可带）

### 2.3 成员管理
- `GET /api/v1/projects/{projectId}/members`
- `POST /api/v1/projects/{projectId}/members`
  - body: `{ "user_id": 123, "role": "Member|ProjectAdmin" }`
- `PATCH /api/v1/projects/{projectId}/members/{memberId}`
- `DELETE /api/v1/projects/{projectId}/members/{memberId}`

> 实现建议：成员列表接口返回用户简要信息（display_name/username/email）与在队状态。

## 2.4 奖项（Project Awards）

- `GET /api/v1/awards?project={projectId}`（项目奖项列表）
- `POST /api/v1/awards`
  - body: `{ "project": 1, "stage": "SCHOOL", "title": "一等奖", "level":"校级", "awarded_at":"2025-08-01", "description":"..." }`
- `PATCH /api/v1/awards/{awardId}`
- `DELETE /api/v1/awards/{awardId}`

## 2.5 赛程/里程碑（Project Events）

- `GET /api/v1/events?project={projectId}`
- `POST /api/v1/events`
  - body: `{ "project": 1, "title": "材料提交截止", "start_at": "2025-08-10T18:00:00+08:00", "end_at": null, "stage": "SCHOOL", "description": "..." }`
- `PATCH /api/v1/events/{eventId}`
- `DELETE /api/v1/events/{eventId}`

## 2.6 任务（看板/甘特基础数据）（Project Tasks）

- `GET /api/v1/tasks?project={projectId}`
- `POST /api/v1/tasks`
  - body: `{ "project": 1, "title": "完善计划书", "status":"TODO|DOING|DONE", "start_date":"2025-07-14", "end_date":"2025-07-20", "progress_percent": 30, "sort_order": 10, "description":"..." }`
- `PATCH /api/v1/tasks/{taskId}`
- `DELETE /api/v1/tasks/{taskId}`

## 3. 文件 Files

> 路径统一使用项目内相对路径 `path`（例如 `docs/plan.pdf`），后端做规范化并保证不越出项目根目录。

### 3.1 列表/目录树（含个人区开关）
- `GET /api/v1/projects/{projectId}/files/list?path=/&include_personal=true|false`
  - resp.data: `{ "path": "/", "items": [ {"name":"...","kind":"file|dir","rel_path":"...","size":123,"updated_at":"...","is_personal":false} ] }`

### 3.2 元信息
- `GET /api/v1/projects/{projectId}/files/meta?path=...`

### 3.3 预览（Range 支持）
- `GET /api/v1/projects/{projectId}/files/preview?path=...`
  - 说明：
    - 必须支持 HTTP Range（`Range: bytes=...`）
    - 返回头：`Accept-Ranges: bytes`、`ETag`、`Last-Modified`（便于缓存）

### 3.4 下载
- `GET /api/v1/projects/{projectId}/files/download?path=...`

### 3.5 上传/新建
- `POST /api/v1/projects/{projectId}/files/upload?path=目标目录相对路径`
  - multipart: `file`

### 3.6 覆盖更新
- `PUT /api/v1/projects/{projectId}/files/content?path=...`
  - multipart 或二进制 body

### 3.7 移动/改名
- `POST /api/v1/projects/{projectId}/files/move`
  - body: `{ "src": "a/b.txt", "dst": "a/c.txt" }`

### 3.8 删除（进入回收站）
- `POST /api/v1/projects/{projectId}/files/delete`
  - body: `{ "path": "a/b.txt" }`

### 3.9 个人区标记（可选接口）
> 若你希望“任意文件/目录都能一键转为个人区”，可提供此接口；否则仅支持固定个人区目录策略。
- `POST /api/v1/projects/{projectId}/files/personalize`
  - body: `{ "path": "...", "is_personal": true, "owner_user_id": 123 }`

## 4. 权限 ACL

### 4.1 查询某路径有效权限
- `GET /api/v1/projects/{projectId}/acl/effective?path=...`

### 4.2 列出该路径的显式 ACL
- `GET /api/v1/projects/{projectId}/acl?path=...`

### 4.3 授权/拒绝
- `POST /api/v1/projects/{projectId}/acl/grant`
  - body: `{ "target_path": "...", "target_kind":"file|dir", "subject_kind":"user|role", "subject_value":"123|Member", "effect":"ALLOW|DENY", "actions":["LIST","PREVIEW"], "inherit": true }`

### 4.4 删除 ACL 条目
- `DELETE /api/v1/projects/{projectId}/acl/{aclId}`

## 5. 回收站 Recycle

> 所有入口复用同一套 API。

- `GET /api/v1/projects/{projectId}/recycle/list?query=...&page=1&page_size=50`
- `POST /api/v1/projects/{projectId}/recycle/restore`
  - body: `{ "recycle_item_id": 1, "restore_to": "可选新路径" }`
- `POST /api/v1/projects/{projectId}/recycle/purge`
  - body: `{ "recycle_item_id": 1 }`（或批量）

## 6. 审计 Audit

- `GET /api/v1/projects/{projectId}/audit/list?action=DOWNLOAD&actor=...&path=...&from=...&to=...&page=...`

## 7. 搜索 Search（无 OCR）

- `GET /api/v1/projects/{projectId}/search?query=...&scope=pathPrefix&path=...`
  - 后端返回前必须二次做权限过滤（LIST/PREVIEW）。

## 8. 备份 Backup

- `POST /api/v1/projects/{projectId}/backup/run`
  - body: `{ "mode": "INCREMENTAL|FULL" }`
- `GET /api/v1/projects/{projectId}/backup/list`
- `POST /api/v1/projects/{projectId}/backup/restore`
  - body: `{ "backup_id": 1 }`

## 9. 审计写入点（实现提示）

建议在以下 API 入口统一写审计：
- 文件：LIST/PREVIEW/DOWNLOAD/UPLOAD/UPDATE/MOVE/DELETE/RESTORE
- 权限：ACL_GRANT/ACL_DENY/ACL_DELETE
- 成员：MEMBER_ADD/MEMBER_REMOVE/ROLE_CHANGE
- 任务：INDEX_START/INDEX_DONE/BACKUP_START/BACKUP_DONE
