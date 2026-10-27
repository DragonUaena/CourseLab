# CourseLab

CourseLab 是一个本地多账号的 AI 学习路线规划应用。输入想学的主题、目标、基础和每周可投入时间，
它会先用 Tavily 搜索资料，再由 CrewAI 组织资料策展、路线设计和计划审查三个 Agent，最后输出带引用
学习路线、资料索引、可用性评分和 Markdown 报告。

![CourseLab 学习路线首页](output/playwright/courselab-home.png)

![带资料引用和可用性评测的演示报告](output/playwright/courselab-demo.png)

## 功能

- 多账号注册登录，每个用户只能访问自己的学习计划。
- Tavily 按主题、目标和项目实践需求实时搜索资料。
- 资料策展 Agent 只从搜索结果中选来源，路线不直接编造 URL。
- 路线架构 Agent 将先修、核心知识、练习和综合项目安排到指定周期。
- 审查 Agent 从目标匹配、顺序、工作量、资料质量和可执行性五项评分。
- 程序审计补充检查阶段资料覆盖、周期一致性和引用数量。
- 计划异步生成，页面自动显示检索、编排和审查进度。
- 生成结果保存到本地 SQLite，支持重试、删除和 Markdown 下载。
- 内置一份不消耗 API 的 FastAPI 六周演示报告。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 多 Agent 编排 | CrewAI `1.15` |
| Web API | FastAPI、Pydantic |
| 数据库 | SQLAlchemy、SQLite（可切换 PostgreSQL） |
| 资料检索 | Tavily |
| 账号安全 | Argon2、JWT、Fernet 加密 Key |
| 前端 | Vue 3、Vue Router、Vite |
| 测试 | pytest、FastAPI TestClient |

## 工作流

```text
用户目标
  ↓
Tavily 四路检索与 URL 去重
  ↓
资料策展 Agent：筛选相关来源
  ↓
路线架构 Agent：安排阶段、练习和交付物
  ↓
计划审查 Agent：五项评分与改进建议
  ↓
程序审计 + 合并评分
  ↓
SQLite 保存路线、资料、评测与 Markdown 报告
```

## 本地启动

要求 Python 3.10+、Node.js 20+。

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

cd frontend
npm install
cd ..
```

打开两个终端。

后端：

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

前端：

```powershell
cd frontend
npm run dev
```

访问：

- 应用：<http://127.0.0.1:5173>
- Swagger：<http://127.0.0.1:8000/docs>
- 演示报告：<http://127.0.0.1:5173/demo>

首次使用请在应用内注册账号，再到“模型设置”填写 Tavily 和模型 Key。演示报告不需要 Key。

## 配置

`.env` 中的共享配置可用于本地开发：

| 变量 | 说明 |
| --- | --- |
| `COURSELAB_SECRET_KEY` | JWT 签名密钥，建议设置成长随机字符串 |
| `COURSELAB_CREDENTIAL_KEY` | 用户 API Key 加密密钥；留空时自动生成 `data/.credential_key` |
| `COURSELAB_DATABASE_URL` | 默认 SQLite，正式部署可替换为 PostgreSQL URL |
| `TAVILY_API_KEY` | 所有用户共享的 Tavily 默认 Key，可选 |
| `OPENAI_API_KEY` | 所有用户共享的模型默认 Key，可选 |
| `COURSELAB_LLM_MODEL` | LiteLLM 模型名，默认 `openai/gpt-4o-mini` |

网页中填写的 Key 会在后端使用 Fernet 加密后保存，不会原样写入数据库或返回浏览器。
每个用户的学习计划通过 JWT 中的用户身份和后端 `user_id` 条件隔离。

## 数据位置

本地运行产生的数据都保存在当前电脑：

```text
data/
├── courselab.db        # 用户、加密 Key、学习计划
└── .credential_key     # 未配置 COURSELAB_CREDENTIAL_KEY 时自动生成
```

`data/` 已加入 `.gitignore`。上传 GitHub 或 fork 不会携带任何账号、计划或 API Key。

## 测试

```powershell
.\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\ruff.exe check app tests
cd frontend
npm run build
```

测试覆盖账号隔离、API Key 加密、缺少 Key 的失败提示、演示报告、周数归一化和计划可用性审计。

## 在线部署

当前版本面向本地使用。后续上线时，可保持应用代码不变，把 `COURSELAB_DATABASE_URL` 切换为 PostgreSQL，
并在服务器环境设置共享 Key、HTTPS 域名、访问限流和用户额度。公开站点的学习计划将保存在服务器数据库，
而不是访问者电脑。

