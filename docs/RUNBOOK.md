# 运行与测试指南

## 你怎样看前端页面

1. 安装并打开「微信开发者工具」。
2. 点击“导入项目”，选择本项目的 `miniprogram` 文件夹；没有 AppID 时保持“测试号/游客模式”。
3. 在终端按下节启动后端。
4. 开发者工具右上角详情 → 本地设置，开发期间勾选“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”。
5. 点击编译，默认会进入菜单页。顾客流程是：选菜 → 购物车 → 填地址 → 地图选地点/当前位置 → 模拟微信支付。

支付成功后可打开“查看订单”，或从“我的订单”进入历史订单详情；顾客只能读取自己 OpenID 创建的订单，其他订单统一显示不存在。

> 微信开发者工具运行在电脑上时，`127.0.0.1:8000` 可以访问本机后端。真机预览需要换成一个公网 HTTPS API 域名，并在小程序后台配置为合法 request 域名。

商家页面没有隐藏入口，开发时可在开发者工具的地址栏或“编译模式”打开 `pages/admin-orders/index`。在开发环境首次输入已允许手机号 `18785409634` 或 `18285424586` 并绑定后，就可以看订单、改为制作中/待配送/完成、重新打印。这个“手填手机号”快捷绑定接口只在开发/测试环境存在；正式版必须接微信 `getPhoneNumber` 的一次性凭据并在服务端验证后才可绑定，不能把手机号当作身份凭据。

## 启动后端

在项目根目录执行：

```bash
cd server
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

`alembic upgrade head` 会创建 `server/data/dev.db` 和表结构；API 启动后写入 5 个预设商品。接口文档在 <http://127.0.0.1:8000/docs>，健康检查在 <http://127.0.0.1:8000/api/health>。

运行日志默认输出到终端，可通过 `LOG_LEVEL` 调整。每个 API 响应带有 `X-Request-ID`；遇到线上问题时，提供该值即可关联请求日志。日志刻意不记录请求体、手机号、地址、支付凭据或查询字符串。

`APP_ENV=production` 当前会主动拒绝启动：这是保护措施，防止模拟支付、模拟距离或模拟打印被误用于真实收款。完成真实微信支付、腾讯地图和云打印供应商接入后，我会将它们作为显式生产配置加入，再解除该保护。

商家可通过 `GET /api/admin/orders/{order_id}/history` 查看订单操作历史。该记录用于排查“谁在何时变更状态或请求补打”，与后台重试用的打印事件分离。

商品管理 API 现已可用：`GET /api/admin/products`、`POST /api/admin/products`、`PATCH /api/admin/products/{id}`。它们均要求商家权限；顾客菜单接口只返回 `enabled=true` 的商品。

小程序商家订单页已提供“商品管理”入口，可新增、编辑商品信息以及切换上下架。第一版保持字段最小化（名称、售价、分类）；商品图片和规格选项等你提供真实菜单资料后再增加。

默认 `DELIVERY_PROVIDER=mock` 使用开发期模拟骑行距离。申请腾讯位置服务 Key 后，在服务器 `.env` 设置 `DELIVERY_PROVIDER=tencent_bicycling` 与 `TENCENT_MAP_KEY`，重启 API 即可改用腾讯骑行道路距离；Key 仅保留在服务器环境变量，绝不写进小程序代码或提交到 Git。

腾讯地图遇到网络超时、HTTP 错误或无法返回骑行路线时，报价和下单会返回 HTTP 503 与“地图距离服务暂不可用，请稍后重试”。该响应不会包含地图供应商原始报错、请求参数或 Key；顾客可保留地址后重试。

结算页会在选点后重新报价。报价尚未完成或失败时，“支付”操作会明确提示等待/重选地点，且不会用上一个地址的配送费创建订单。

默认 `DELIVERY_PRICING_MODE=fixed`，所有订单收取 `DELIVERY_FEE=2.00`。需要按道路距离收费时，将模式改成 `tiered` 并填写 `DELIVERY_DISTANCE_TIERS_JSON`；未匹配到任何距离档位时，报价和下单都会返回“超出配送范围”，历史订单金额不会被配置变更影响。

微信支付申请完成后，使用 `PAYMENT_PROVIDER=wechat_v3`，并在服务器环境变量填入商户号、小程序 AppID、32 字节 API v3 Key 和微信支付平台证书本地路径。`POST /api/payments/wechat/notify` 会先验签和 AES-GCM 解密，再核对订单号、商户号、AppID、交易状态与金额；仅验证通过才落库支付状态。回调不直接打印，而是写入既有打印事件，避免慢打印拖延微信回调。

为真实支付环境设置随机 `JOB_TOKEN` 后，由同服务器的私有定时任务或 worker 请求 `POST /api/internal/jobs/dispatch-print-events`，请求头为 `X-Job-Token`。它负责消费待打印事件；此令牌不可提供给小程序或浏览器。开发环境的模拟支付仍会立即调度，方便演示。

Docker Compose 现在默认启动 `worker` 服务，它每 5 秒消费一次待打印事件，不需要额外 cron。打印失败会按指数退避自动重试，默认每次初始间隔 30 秒、最多 5 次；达到上限仍失败时保留失败状态，商家可用“重新打印”新建一次补打事件。可用 `PRINT_RETRY_DELAY_SECONDS` 和 `PRINT_MAX_ATTEMPTS` 调整。`JOB_TOKEN` 接口仍保留给以后将 worker 放到独立任务平台时使用。真实云打印适配器接入后会替换 worker 内的模拟打印实现。

商家订单页打开时每 10 秒刷新一次，离开页面即停止；也可以下拉立即刷新。小店首版采用轮询，部署和故障排查都比常驻 WebSocket 简单；订单量或店员数量增长后可无缝替换为 WebSocket/SSE 推送。

## 直接测试后端（不需要微信开发者工具）

后端运行后，在另一个终端执行：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/products

# 绑定一个开发演示商家；真实版必须先由微信服务端验证手机号授权凭据
curl -X POST 'http://127.0.0.1:8000/api/auth/admin-bind?phone=18785409634' -H 'X-OpenID: demo-admin'

# 查看商家已支付订单
curl http://127.0.0.1:8000/api/admin/orders -H 'X-OpenID: demo-admin'
```

在前端完成一次模拟支付后，最后一条命令将显示订单。也可以在 `/docs` 中点接口逐个执行。

下单接口支持可选请求头 `X-Idempotency-Key`（最长 64 字符）。小程序会为一次结算自动生成并在网络重试时复用它；相同顾客和相同键会返回原订单，不会多建订单。第三方客户端也应在用户点击“支付”时生成一次并复用该值，不能为每次重试生成新值。

## 切到 PostgreSQL

开发阶段 SQLite 足够。要验证长期部署使用的 PostgreSQL，先执行：

```bash
docker compose up -d
```

然后把 `server/.env` 的 `DATABASE_URL` 改为：

```dotenv
DATABASE_URL=postgresql+psycopg://wechat_deliver:change-me-before-production@127.0.0.1:5432/wechat_deliver
```

执行 `alembic upgrade head` 后再重启 API。项目从现在开始使用 Alembic 迁移，不依赖应用启动时自动建表。

## 用 Docker 启动部署环境

1. 在服务器项目根目录执行 `cp .env.production.example .env`。
2. 编辑 `.env`，至少将 `POSTGRES_PASSWORD` 与 `DATABASE_URL` 中的同一密码替换为随机强密码。
3. 执行 `docker compose up -d --build`。
4. 用 `docker compose ps` 确认 `postgres` 与 `api` 均为 healthy，再访问 `http://服务器地址:8000/api/ready`。

API 容器在启动前自动执行 `alembic upgrade head`，并以非 root 用户运行。`/api/health` 只检查进程存活，`/api/ready` 还会执行一次数据库查询；Docker 使用后者判断服务可用性。此 compose 文件仅开放 API 的 8000 端口；正式上线时应由 Nginx/Caddy 提供 HTTPS 并只暴露 443。当前 `APP_ENV=production` 会按安全策略拒绝启动，直到真实支付、地图、打印供应商已完成接入；部署演练先保持 `development`。

## 上线前必须替换的模拟能力

| 当前开发实现 | 正式替换点 |
| --- | --- |
| `MockCyclingDistanceProvider` | 腾讯地图骑行路线 API，保存其实际道路距离 |
| `mock-payment-callback` | 微信支付 JSAPI 下单、回调验签、交易号与回调幂等表 |
| `MockPrinter` | 选定云打印机的 API，保存请求 ID、失败原因、重试记录 |
| 手填 `X-OpenID` / 演示 OpenID | `wx.login` code 服务端换 OpenID，签发自己的会话令牌 |
| 直接手机号参数绑定 | 小程序 `getPhoneNumber` 一次性 code 服务端解密/换取手机号后再比对白名单 |

还要在小程序后台申请 AppID、合规主体与微信支付商户号，配置 HTTPS 域名；订阅消息需要在下单/付款前让用户主动订阅相应模板。支付成功只以微信支付服务器回调为准。

### 支付回调与打印的上线原则

支付订单现在记录支付渠道、渠道交易号、支付状态和一条持久化打印事件。正式接入微信支付时，回调路由只做验签、去重、落库并迅速返回 `204`；独立 worker 再消费待处理打印事件。这样微信重复通知不会重复改订单，打印接口慢或临时故障也不会拖慢支付回调。打印供应商接入时须把事件 `idempotency_key` 一并传给供应商（若支持），并保留失败原因和重试次数。
