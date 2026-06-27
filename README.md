# 不语奈何 AI 数据标注平台 (Buyunaihe AI Data Annotation Platform)

<div align="center">

![Vue 3](https://img.shields.io/badge/Vue-3-41B883?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?logo=rabbitmq&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-E2231A?logo=minio&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

</div>

**不奈何 AI 数据标注平台** 是一个面向 **AI 数据生产、数据标注与质量审核** 场景的全栈数据标注平台，参考 [LabelHub](https://gitee.com/astralChord/labelhub) 的设计目标构建，提供从原始数据到高质量标注结果的全流程管理。

平台围绕 **数据集导入 → 模板搭建 → 任务创建与分发 → 标注员作业 → AI Agent 辅助标注与自动预审 → 人工复核 → 结果导出** 构建完整业务闭环，支持文本分类、实体抽取、JSON 标注、文件/图片上传、LLM Prompt 等多类标注任务。

> 与原 LabelHub 的差异：后端由 Spring Boot 替换为 **Python FastAPI**，AI Agent 保持 Python (Flask + LangChain)，前端保持 Vue 3，整体仍为「前端 + 后端 + Python AI Agent + 基础中间件」的解耦式架构。

---

## 目录

- [项目介绍](#项目介绍)
- [系统架构](#系统架构)
- [快速部署](#快速部署)
- [默认账号](#默认账号)
- [核心业务闭环](#核心业务闭环)
- [项目结构](#项目结构)
- [AI 能力与降级策略](#ai-能力与降级策略)
- [常用运维命令](#常用运维命令)

---

## 项目介绍

平台面向四类核心角色：

| 角色 | 核心职责 |
| --- | --- |
| Owner / Admin 管理员 | 创建任务、导入数据集、配置模板、分配标注员与审核员、查看统计、导出结果 |
| Labeler 标注员 | 领取任务、按模板完成标注、查看 AI 建议、保存草稿、提交结果 |
| Reviewer 审核员 | 查看标注结果和 AI 预审报告，执行通过、驳回、修改并通过 |
| AI Agent | 自动生成标注建议，对已提交结果执行规则校验、评分和审核报告 |

核心能力：

- **可配置模板搭建**：输入框、文本域、单选、多选、下拉、数字、文件上传、图片上传、JSON、LLM Prompt 等物料组件，Schema 驱动动态渲染
- **数据集导入与字段映射**：支持 JSON / JSONL / CSV / Excel 上传与解析
- **任务生命周期管理**：创建、发布、领取、标注、提交、审核、导出全流程
- **AI 建议与自动预审**：AI 建议走 HTTP 同步触发，AI 预审走 RabbitMQ 异步消费
- **人工最终决策**：AI 结果仅作辅助，最终结论由审核员确认
- **多格式结果导出**：JSON / JSONL / CSV / XLSX
- **权限与角色控制**：RBAC 多角色协同

---

## 系统架构

「前端 + Python 后端 + Python AI Agent + 基础中间件」的解耦式架构：

| 层级 | 技术选型 | 职责 |
| --- | --- | --- |
| 前端应用 | Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、ECharts | 登录、任务广场、标注工作台、审核工作台、模板搭建、数据集管理、统计看板 |
| 业务后端 | Python、FastAPI、SQLAlchemy、JWT、Redis、pika、minio | 用户权限、任务流转、模板管理、数据集解析、标注提交、审核操作、导出、Agent 编排 |
| AI Agent Web | Python、Flask、LangChain、OpenAI-compatible Client | AI 建议生成（同步）、结果查询、健康检查 |
| AI Agent Worker | Python、RabbitMQ / pika、SQLAlchemy | 消费 AI 预审消息、规则校验、调用 LLM、写入审核结果 |
| 基础中间件 | MySQL、Redis、RabbitMQ、MinIO、Nginx | 业务库、缓存/登录态、异步消息、对象存储、前端静态资源 |

### AI 链路

**AI 建议生成链路（同步 HTTP）**
标注员点击「生成 AI 建议」→ 前端请求后端 → 后端调用 `agent-web` `/suggestion` → Agent 结合模板与原始数据生成建议写入 Agent 库 → 前端轮询查询结果并展示 → 标注员可一键应用到表单。

**AI 预审链路（异步 RabbitMQ）**
标注员提交结果 → 后端生成 `audit_id` 并投递 RabbitMQ `ai_audit` 队列 → `agent-worker` 消费消息，执行字段规则校验 + LLM 评分 → 写入 `ai_audit_reports` → 审核员在审核工作台查看 AI 预审报告（评分、问题、依据）并做最终决策。

### 数据模型

- **用户权限域**：users、roles、permissions、role_permissions
- **模板配置域**：templates（Schema 驱动物料）
- **数据集域**：datasets、dataset_files、dataset_items
- **任务处理域**：tasks、task_assignments、task_items、task_transitions、task_progress
- **标注审核域**：annotation_results、review_opinions
- **导出域**：export_records、export_files
- **Agent 结果库（隔离）**：ai_suggestions、ai_audit_reports

> 业务主库 `labelhub` 与 Agent 结果库 `labelhub_agent` 隔离，降低 AI 失败对主业务的影响；审核页通过 `audit_id` 经 `agent-web` 查询 Agent 结果。

---

## 快速部署

### 环境要求

- Docker 24+
- Docker Compose v2+
- （可选）OpenAI 兼容 LLM API Key，用于启用真实 AI；不填则自动降级为规则模式

### 一键启动

**Windows PowerShell**
```powershell
.\deploy\deploy.ps1
```

**Linux / macOS**
```bash
sh deploy/deploy.sh
```

部署脚本会：
1. 从 `deploy/docker.env.example` 复制 `deploy/docker.env`（如不存在）
2. 构建所有镜像
3. 运行 `agent-migrate` 一次性初始化 Agent 数据库表
4. 启动 `minio-init` 自动创建 `annotation / dataset / export / template` 四个桶并设置匿名读取
5. 启动全部常驻服务

### 环境变量

编辑 `deploy/docker.env`，重点关注：

```env
# AI（留空则使用规则/启发式模式，无需外部 Key 即可跑通全流程）
AI_AUDIT_BASE_URL=
AI_AUDIT_API_KEY=
AI_AUDIT_MODEL=gpt-4o-mini

# 必填：请设置强密码，留空会导致中间件无法启动
MYSQL_ROOT_PASSWORD=
MYSQL_PASSWORD=
RABBITMQ_PASSWORD=
MINIO_ROOT_PASSWORD=
JWT_SECRET=
LABELHUB_MINIO_PUBLIC_URL=http://localhost:9000
```

### 默认访问地址

> 主机端口默认避开本机已运行的 MySQL/Redis/Web 服务（可在 `deploy/docker.env` 中通过 `FRONTEND_HOST_PORT` / `MYSQL_HOST_PORT` / `REDIS_HOST_PORT` 调整）。

| 服务 | 地址 |
| --- | --- |
| 前端页面 | http://localhost:8088 |
| 后端接口 | http://localhost:8080 |
| Agent HTTP 服务 | http://localhost:5001 |
| RabbitMQ 管理台 | http://localhost:15672 |
| MinIO 控制台 | http://localhost:9001 |
| MySQL（主机映射） | localhost:3307 |

---

## 初始账号

首次启动时，后端会自动创建初始管理员账号。初始密码来源：

- **若在 `deploy/docker.env` 设置了 `APP_ADMIN_PASSWORD`**：三个初始账号（`admin`/`labeler1`/`reviewer1`）均使用该密码。
- **若未设置（留空）**：后端自动生成随机密码，并打印到 backend 启动日志中，查找类似 `Generated initial passwords` 的行即可获取。**请登录后立即在「用户管理」修改密码。**

| 用户名 | 角色 |
| --- | --- |
| `admin` | owner（管理员） |
| `labeler1` | labeler（标注员） |
| `reviewer1` | reviewer（审核员） |

> 出于安全考虑，本仓库不内置任何默认明文密码。请通过环境变量或日志获取初始密码后及时修改。

---

## 核心业务闭环

1. **管理员** 在「模板管理」拖拽配置物料，发布模板
2. **管理员** 在「数据集管理」上传 JSON/JSONL/CSV/Excel，系统解析为数据项
3. **管理员** 在「任务管理」绑定模板与数据集，分配标注员与审核员，开启 AI 预审/建议，发布任务
4. **标注员** 在「任务广场」领取任务，进入「标注工作台」：
   - 查看原始数据，按模板动态表单标注
   - 点击「生成 AI 建议」获取智能辅助，可一键应用
   - 保存草稿 / 提交（提交后触发 AI 预审）
5. **审核员** 在「审核工作台」查看标注结果与 AI 预审报告（评分、问题、依据），执行通过 / 驳回 / 修改并通过
6. **管理员** 在「导出」选择格式（JSON/JSONL/CSV/XLSX），下载最终结果

---

## 项目结构

```text
.
├─ Frontend/          # Vue 3 + TypeScript + Vite 前端
│  ├─ src/{api,components,views,stores,router,types,constants,utils,...}
│  └─ Dockerfile
├─ Backend/           # FastAPI 业务后端（替代 Spring Boot）
│  ├─ app/{main,config,database,models,schemas,deps,security,response,
│  │       minio_client,rabbitmq, routers/{auth,users,templates,datasets,
│  │       tasks,annotation,review,export,stats,upload}}
│  └─ Dockerfile
├─ Agent/             # AI Agent：Flask web + RabbitMQ worker
│  ├─ app.py  run_agent.py  run_audit_worker.py
│  ├─ annotation_agent/{config,database,models,llm,suggestion,audit,worker,migrate}
│  └─ Dockerfile
├─ deploy/
│  ├─ mysql/{labelhub.sql, labelhub_agent.sql}   # 数据库初始化
│  ├─ nginx/nginx.conf
│  ├─ minio-init.sh
│  ├─ docker.env.example
│  ├─ deploy.ps1  deploy.sh
├─ docs/CONTRACTS.md  # 服务间契约（API / RabbitMQ 消息 / 数据模型）
├─ compose.yaml
└─ README.md
```

---

## AI 能力与降级策略

`agent-web` 与 `agent-worker` **均可在无 LLM Key 的情况下完整运行**：

- **未配置 Key**：AI 建议使用启发式预填（按物料类型给默认值），AI 预审使用规则校验评分（`score = max(0, 100 - 15 × 违规数)`），`model` 标记为 `heuristic` / `rule-based`。闭环可完整跑通。
- **配置 Key**：通过 LangChain `ChatOpenAI` 调用 OpenAI 兼容接口生成建议与评分，LLM 失败时自动回退到规则模式。

---

## 常用运维命令

```bash
# 查看服务状态
docker compose --env-file deploy/docker.env ps

# 查看后端日志
docker compose --env-file deploy/docker.env logs -f backend

# 查看 Agent Worker 日志
docker compose --env-file deploy/docker.env logs -f agent-worker

# 停止
docker compose --env-file deploy/docker.env down

# 重新构建并启动
docker compose --env-file deploy/docker.env build
docker compose --env-file deploy/docker.env up -d
```

---

## License

AGPL-3.0
