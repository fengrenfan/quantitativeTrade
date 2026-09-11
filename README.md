# 量化趋势看板 · quantitativeTrade

A 股日线趋势看板：支持 **多标的 / 多策略 / 多周期 / 多参数** 四个维度切换，展示 K 线、买卖信号、净值曲线与绩效指标。

技术选型遵循「**Python 干重活，Spring Boot 当门面，React + ECharts 做脸**」：

```
React + ECharts（深色霓虹）
   └─ Spring Boot 薄网关（JWT / 路由 / Redis 缓存）
        └─ Python 量化引擎（AkShare + pandas 向量化）
             └─ AkShare 行情 + MySQL / Redis / ES
```

## 目录结构

```
quantitativeTrade/
├── engine/              # Python 量化引擎
│   ├── config.py        # 配置（标的池、默认参数、成本）
│   ├── data.py          # AkShare 取数 + CSV 缓存 + 合成兜底
│   ├── mock_data.py     # 离线合成行情
│   ├── strategies.py    # 双均线 / MACD / 布林 / 动量
│   ├── backtest.py      # 向量化回测（shift(1) 防未来函数）
│   ├── metrics.py       # 年化 / 夏普 / 回撤 / 卡玛
│   ├── service.py       # 编排：取数→策略→回测→绩效
│   ├── app.py           # FastAPI 服务
│   └── main.py          # CLI
├── backend/             # Spring Boot 薄网关
│   └── src/main/java/com/fengrenfan/quant/
│       ├── controller/SignalController.java
│       ├── service/SignalService.java
│       ├── client/EngineClient.java
│       ├── config/{QuantProperties,WebConfig}.java
│       └── security/JwtAuthFilter.java
├── web/                 # React + ECharts 看板
│   └── src/components/{Dashboard,KlineChart,EquityChart}.tsx
├── docker-compose.yml
└── .env.example
```

## 一、本地开发

### 1) 引擎（Python）

```bash
cd engine
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 从项目根目录运行 CLI
cd ..
python -m engine.main --catalog
python -m engine.main --symbol 600519.SH --strategy dual_ma --fast 5 --slow 20

# 启动 HTTP 服务（供后端调用）
uvicorn engine.app:app --host 0.0.0.0 --port 8000
```

> 未安装 AkShare 或断网时，引擎会自动回退到**合成行情**，保证系统可跑通（仅供演示）。
> 响应中的 `source` 字段会标明数据来源（`akshare` / `tencent` / `cache` / `mock`）。

### 2) 后端（Spring Boot，需 JDK 17 + Maven）

```bash
cd backend
mvn spring-boot:run
# 默认端口 8081
```

### 3) 前端（Node 18+）

```bash
cd web
npm install
npm run dev
# 打开 http://localhost:5174（已把 /api 代理到 8081）
```

## 二、Docker Compose 部署

```bash
cp .env.example .env   # 填好 Redis / JWT / 端口
docker compose up -d --build
# 前端 http://<服务器>:8090
```

### 端口可配置（避免与已占用端口冲突）

三个服务的主机端口都能用 `.env` 覆盖：

| 变量 | 默认 | 说明 |
|------|------|------|
| `ENGINE_PORT` | `8000` | Python 引擎 |
| `BACKEND_PORT` | `8081` | Spring Boot 网关 |
| `WEB_PORT` | `8090` | 前端（唯一需要对外暴露的） |

### 服务器本地覆盖：docker-compose.override.yml

该文件已在 `.gitignore` 中，用于放「只属于这台机器」的配置。国内服务器建议同时指定镜像源，
否则 pip / npm / maven 下载会慢到几十分钟：

```yaml
services:
  engine:
    build:
      args:
        PIP_INDEX_URL: https://pypi.tuna.tsinghua.edu.cn/simple
  backend:
    build:
      args:
        MAVEN_MIRROR: https://maven.aliyun.com/repository/public
    networks:
      - default
      - blognet          # 接入博客网络以复用 blog-redis
  web:
    build:
      args:
        NPM_REGISTRY: https://registry.npmmirror.com

networks:
  blognet:
    external: true
    name: docker_default
```

- `web`（nginx）会把 `/api/` 反代到 `backend:8081`。
- 复用博客 Redis：让 `backend` 接入博客所在网络，`REDIS_HOST` 填博客 Redis 的容器名
  （如 `blog-redis`）；Redis 不可用时网关自动降级为直连引擎，功能不受影响。
- 生产建议在宿主 nginx 上挂子域名（如 `quant.xiaodigua.shop`）并配 HTTPS，
  这样只需复用已放通的 80/443，不必额外开放端口。

### 数据源与容灾

`engine/data.py` 按 **东方财富 → 腾讯 → 合成数据** 依次尝试，全部失败才回退合成数据，
并在响应里用 `source` 字段标明来源，前端顶部有对应徽标：

| `source` | 含义 |
|----------|------|
| `akshare` | 东方财富真实行情 |
| `tencent` | 腾讯真实行情（东财不可用时的备选） |
| `cache` | 引擎本地 CSV 缓存 |
| `mock` | 合成数据（不可用于投资决策，前端会黄色告警） |

> 注意：东方财富在密集请求后会**限流整个 IP**，此时接口会直接断连。
> 代码已给 `requests` 注入浏览器 UA（默认 UA 会被拒），并内置腾讯备选源。

## 三、接入你的博客底座

复制 `.env.example` 为 `.env` 并填写（**切勿提交**）：

| 变量 | 说明 |
|------|------|
| `QUANT_ENGINE_URL` | Python 引擎地址，compose 内为 `http://engine:8000` |
| `QUANT_AUTH_ENABLED` | 是否启用 JWT 鉴权（复用博客登录态） |
| `JWT_SECRET` | 博客 JWT 密钥（HS256，需 ≥ 32 字节） |
| `REDIS_HOST/PORT/PASSWORD` | 博客 Redis 连接信息 |
| `MYSQL_*` | 后续接自选股 / 回测记录时启用 |

> 鉴权默认**关闭**；打开后 `/api/signal` 需带 `Authorization: Bearer <token>`，`/api/health`、`/api/catalog` 始终放行。

## 四、API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/catalog` | 可用标的 / 策略 / 周期 / 默认参数 |
| GET | `/api/signal?symbol=600519.SH&strategy=dual_ma&timeframe=daily&fast=5&slow=20` | 信号 + K线 + 净值 + 绩效 |
| GET | `/api/health` | 网关与引擎健康状态 |

策略取值：`dual_ma` / `macd` / `bollinger` / `momentum`；周期：`daily` / `weekly` / `60min`。

## 五、设计原则（来自对主流开源项目的调研）

1. **策略与执行解耦**：策略只产出 `[标的, CASH]` 权重表，回测/绩效由独立模块负责。
2. **杜绝未来函数**：收益用「昨日权重」计算（`weights.shift(1)`）。
3. **复权价 + 交易成本**：回测用复权价，并计入换手成本。
4. **参数可分离**：`symbol/strategy/timeframe/fast/slow` 全部作为参数，支撑前端任意切换。

## 六、后续路线

- **MVP（当前）**：四维切换 + 四策略。
- **增强**：参数扫描 / 自动寻参（参考 Freqtrade Hyperopt）、多标的批量对比。
- **进阶**：ML 因子（参考 Qlib / vnpy.alpha 的 Alpha158）、实盘接入（vnpy + XTP / QMT）。

> 免责声明：本项目仅用于技术学习与研究，不构成任何投资建议。回测表现不代表未来收益。
