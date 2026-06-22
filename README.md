# 📅 CronAdmin 项目

`CronAdmin` 是一个基于 **Vue 3** 和 **FastAPI** 的**动态定时任务调度与系统端口自愈监控管理系统**。
它将传统的 Cron 定时任务与现代化的 Web UI 结合，并独创性地引入了基于端口状态检测的**服务自愈（Auto-healing）机制**，可有效降低多服务环境下的手动运维成本。

🌐 **Demo 演示网址**：[https://115.190.183.156:5173/login](https://115.190.183.156:5173/login)

---

## 🌟 项目亮点 (Highlights)

### ⚡ 全异步非阻塞架构 (Fully Asynchronous)
  后端从 HTTP 路由入口（FastAPI）、数据库读写（SQLAlchemy + aiosqlite）到任务运行日志的异步流式写入（aiofiles），均采用 Python 的 `async/await` 协程机制，大幅提升了在海量定时任务并发与高频监控下的系统性能。

### 🔄 任务配置热加载与防重叠机制
  * **配置热加载**：
    调度引擎定时扫描 DB 配置，利用 MD5 算法对任务参数进行哈希校验。在不重启系统的前提下，动态加载、更新或移除定时任务调度。
  * **防重叠执行**：
    在 APScheduler 中限制单个任务的 `max_instances=1`，防止脚本由于上一次执行超时而在下一个周期发生阻塞或重叠，确保高频任务运行的稳定性。

### 🩹 独创性端口故障自愈 (Port Auto-healing)
  系统除了能监控端口外，还允许将指定端口绑定到特定的“恢复定时任务”上。每当系统检测到配置 of 端口处于掉线（DOWN）状态时，它会自动在后台即时并异步地拉起恢复脚本进行故障自愈。

### 📦 单端口生产托管 (Single-Port Hosting)
  生产模式下，FastAPI 后端通过静态文件挂载无缝托管了前端构建出的 `frontend/dist` 目录，并接管了前端路由的 404 捕获。整个系统在生产环境中仅需对外暴露一个 Web 端口，极其精简，有利于安全网络隔离。

### 📦 一键部署（One Key For All）
  install.sh 可自动探测安装whiptail、python、node模块，无需手动安装。即使是IT小白或纯净linux、容器linux，也能自动解决环境问题，真正做到一键部署。

---

## 📋 项目功能模块 (Key Features)

* **🔐 JWT 安全登录与认证**：前端通过 SHA-256 加密传输密码，后端结合 bcrypt 盐哈希存储和 JWT（JSON Web Token）无状态校验。
* **📅 定时任务工作台**：
  * 支持 Cron 表达式配置，且可定制专属的 Python 运行环境或环境变量。
  * 提供执行日志流式展示、历史执行退回状态码、脚本实时输出查看等运维工具。
  * 支持手动一键触发、开启/关闭调度开关。
* **🔌 系统监听端口监控**：展示宿主机上所有处于 `LISTEN` 状态的端口、关联 PID、进程名及占用信息。
* **🛠️ 环境变量与环境设置**：可视化展示并统一管理系统的动态配置和 Python 运行解释器。

---

## 📦 关键脚本功能说明

项目根目录下提供了三个快捷运维与部署脚本：

1. 📥 **`install.sh`**（环境初始化脚本）
   * **功能**：自动探测当前系统环境，自动创建/验证 Python 解释器并安装后端 `requirements.txt` 内的所有包，同时自动安装前端 `node_modules` 依赖，完成首次部署准备。
   * **执行命令**：`bash install.sh`
   * **注意必须使用bash，因为用到了 whiptail**

2. 🏗️ **`build.sh`**（前端构建打包脚本）
   * **功能**：用于编译前端生产资源。它会自动寻找本机的 node/npm 环境并执行构建，最终输出并生成用于生产部署托管的 `frontend/dist` 静态打包资源文件夹。并且自动打包上传到服务器
   * **执行命令**：`bash build.sh`

3. 🏃 **`start_prod.sh`**（生产运行拉起脚本）
   * **功能**：用于生产环境的一键部署。清理冲突的端口进程占用，后台异步拉起 FastAPI 后端，并**由后端单端口模式直接挂载并托管**前端 `frontend/dist` 的静态页面。
   * **执行命令**：`bash start_prod.sh`

---

## 📂 项目结构 (Project Directory Tree)

```text
cronadmin/
├── backend/                        # 🐍 后端服务代码
│   ├── app/
│   │   ├── api/                    # 接口控制层 (auth, task, port, env 路由)
│   │   ├── core/                   # 核心安全、JWT 配置与鉴权校验
│   │   ├── database/               # 数据库 Session 连接管理
│   │   ├── models/                 # SQLAlchemy 数据库模型定义 (SQLite)
│   │   ├── schemas/                # Pydantic 输入与输出数据模型
│   │   └── services/               # 核心业务逻辑 (任务调度、端口自愈与系统监控)
│   ├── cronadmin.db                # 系统数据库 (SQLite 文件)
│   └── requirements.txt            # 后端 Python 依赖配置文件
│
├── frontend/                       # ⚡ 前端页面代码
│   ├── src/
│   │   ├── api/                    # Axios 封装与请求层接口
│   │   ├── components/             # 公共可复用 UI 组件
│   │   ├── router/                 # Vue Router 路由配置
│   │   ├── store/                  # Pinia 状态管理器
│   │   ├── views/                  # 功能页面 (任务工作台、端口监控、设置与登录)
│   │   └── App.vue & main.ts       # 前端应用入口
│   ├── dist/                       # 前端编译打包静态资源输出目录
│   ├── package.json                # 前端 NPM 依赖及运行脚本配置
│   └── vite.config.ts              # Vite 配置文件
│
├── install.sh                      # 本地环境一键依赖配置与初始化脚本
├── start.sh                        # 调试/开发环境拉起脚本
├── start_prod.sh                   # 生产环境前后端单端口拉起脚本
└── remote_final_deploy.sh          # 远程自动化部署方案
```

---

## 🛠️ 技术栈 (Tech Stack)

* **💻 前端 (Frontend)**
  * **核心框架**：Vue 3 (基于 Composition API `<script setup>`) + TypeScript
  * **构建配置**：Vite (高性能前端构建工具)
  * **UI 框架与样式**：Element Plus + Tailwind CSS (v4.3.0) + Headless UI Vue
  * **状态管理与路由**：Pinia (轻量状态管理) + Vue Router (路由)
  * **网络请求与安全**：Axios + Crypto-JS (登录密码在前端进行 SHA-256 加密传输)
  * **测试工具**：Playwright (端到端自动化测试)

* **⚙️ 后端 (Backend)**
  * **高性能 Web 服务**：FastAPI + Uvicorn (全异步的 ASGI Web 框架)
  * **动态任务调度**：APScheduler (支持基于 Crontab 表达式的任务动态调度与并发管理)
  * **系统与网络监控**：psutil (获取系统硬件指标、端口监听状态及进程 PID 映射)
  * **数据库与 ORM**：SQLAlchemy (异步引擎 API) + aiosqlite (异步 SQLite)
  * **数据校验**：Pydantic & Pydantic-Settings (配置与环境变量校验)
  * **系统日志**：Loguru (结构化、易用的高性能日志库)

* **🐳 运维与部署 (Ops & Deployment)**
  * **反向代理**：Caddy (提供自签 TLS 证书及 Host 模式反向代理)

---

## 🚀 快速开始 (Quick Start)

### 开发调试模式

1. **前端启动**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   * 开发服务器运行在：`http://localhost:3000`（API 代理已自动指向后端接口）。

2. **后端启动**
   ```bash
   cd backend
   # 安装依赖
   pip install -r requirements.txt
   # 启动开发服务器
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8342 --reload
   ```
   * 开发版接口文档：`http://localhost:8342/docs`

### 生产托管部署模式

1. **安装环境依赖**：
   ```bash
   ./install.sh
   ```
2. **编译前端静态资源**：
   ```bash
   ./build.sh
   ```
3. **一键拉起单端口生产服务**：
   ```bash
   ./start_prod.sh
   ```
   * 服务成功运行后，直接访问 `http://localhost:8123`（默认端口可在 `.cronadmin_env` 内修改）即可，前端与后端在单端口下流畅并行！
