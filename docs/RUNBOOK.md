# 运行与测试指南

## 你怎样看前端页面

1. 安装并打开「微信开发者工具」。
2. 点击“导入项目”，选择本项目的 `miniprogram` 文件夹；没有 AppID 时保持“测试号/游客模式”。
3. 在终端按下节启动后端。
4. 开发者工具右上角详情 → 本地设置，开发期间勾选“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”。
5. 点击编译，默认会进入菜单页。顾客流程是：选菜 → 购物车 → 填地址 → 地图选地点/当前位置 → 模拟微信支付。

> 微信开发者工具运行在电脑上时，`127.0.0.1:8000` 可以访问本机后端。真机预览需要换成一个公网 HTTPS API 域名，并在小程序后台配置为合法 request 域名。

商家页面没有隐藏入口，开发时可在开发者工具的地址栏或“编译模式”打开 `pages/admin-orders/index`。首次输入已允许手机号 `18785409634` 或 `18285424586` 并绑定后，就可以看订单、改为制作中/待配送/完成、重新打印。

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
