# 自动交易系统使用指南

## 🚀 快速开始

### 1. 准备工作

#### A. OKX账号（模拟盘）
1. 访问 https://www.okx.com/ 注册账号
2. 完成实名认证（模拟盘也需要）
3. 进入【交易】->【模拟交易】开启模拟盘
4. 获取API Key：
   - 点击右上角头像 -> 【API】
   - 创建API Key
   - 权限选择：读取 + 交易
   - 记录下：API Key、API Secret、Passphrase

#### B. Telegram机器人
1. 打开Telegram，搜索 @BotFather
2. 发送 `/newbot` 创建新机器人
3. 按提示设置名称和用户名
4. 记录下：**Bot Token**，只保存到本地私有配置或环境变量
5. 获取Chat ID：
   - 搜索你的机器人，发送一条消息
   - 访问 `https://api.telegram.org/bot<你的Token>/getUpdates`
   - 找到 `"chat":{"id":123456789` 这串数字就是Chat ID

### 2. 配置系统

保留 `config/trading_config.json` 中的凭据为空，只把真实 Token 写入本地私有配置：

```bash
cp config/trading_config.local.example.json config/trading_config.local.json
```

然后编辑 `config/trading_config.local.json`：

```json
{
    "telegram": {
        "bot_token": "你的Telegram Bot Token",
        "chat_id": "你的Chat ID"
    }
}
```

`config/trading_config.local.json` 已被 `.gitignore` 忽略，会覆盖公共配置里的空凭据。策略参数仍放在 `config/trading_config.json`：

```json
{
    "strategy": {
        "name": "DoubleMA",
        "vt_symbol": "DOGEUSDT_SWAP_OKX.GLOBAL",
        "setting": {
            "fast_window": 18,
            "slow_window": 20
        }
    },
    "strategies": [],
    "approval": {
        "enabled": true,
        "timeout_seconds": 300,
        "auto_approve_after_hours": 0
    },
    "backtest": {
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "interval": "1h",
        "capital": 10000
    }
}
```

### 3. 安装依赖

```bash
pip install python-telegram-bot
```

### 4. 启动系统

```bash
python run_auto_trading.py
```

你会看到：
```
🚀 启动自动交易系统...

📊 正在运行回测...
============================================================
📊 回测报告
============================================================
回测周期: 2024-01-01 ~ 2024-12-31
策略: DoubleMA (快线=10, 慢线=20)
------------------------------------------------------------
总收益率: +23.45%
夏普比率: 1.23
最大回撤: -8.32%
胜率: 52.3%
交易次数: 156
============================================================

✅ 已连接到OKX 模拟盘
✅ 策略已添加: DoubleMA_Auto -> DOGEUSDT_SWAP_OKX.GLOBAL
   参数: 快线=18, 慢线=20

✅ 系统启动完成！
📱 Telegram已连接，交易信号将推送到你的手机
⏳ 正在监听市场...
```

## 📱 Telegram交互

### 自动推送的消息

**1. 系统启动通知**
- 回测结果摘要
- 当前参数设置
- 系统状态

**2. 交易信号（需要确认）**
```
🟢 交易信号 #DoubleMA_Auto_TRADE_0001

📊 策略信息
├ 策略: DoubleMA_Auto
├ 品种: DOGEUSDT_SWAP_OKX.GLOBAL
└ 时间: 2025-01-15 14:30:00

⚙️ 当前参数
├ 快线: 10
└ 慢线: 20

📈 回测表现
├ 总收益: 23.45%
├ 夏普比率: 1.23
├ 最大回撤: 8.32%
└ 胜率: 52.3%

💡 交易逻辑
🟢 金叉信号：快线(42350.20)上穿慢线(42100.50)
   前一根K线：快线42100.00 < 慢线42150.00
   当前K线：快线42350.20 > 慢线42100.50
   => 趋势向上，建议做多

🎯 交易详情
├ 方向: 买入做多
├ 价格: 42350.20
├ 数量: 1
└ 当前持仓: 0

回复 /approve DoubleMA_Auto_TRADE_0001 确认
回复 /reject DoubleMA_Auto_TRADE_0001 拒绝
```

**3. 成交通知**
```
✅ 交易成交
方向: 买入
价格: 42350.20
数量: 1
时间: 2025-01-15 14:30:05
```

### 可用命令

| 命令 | 说明 |
|------|------|
| `/start` | 显示帮助信息 |
| `/status` | 查看当前状态 |
| `/approve [id]` | 确认交易（不带id确认所有） |
| `/reject [id]` | 拒绝交易（不带id拒绝所有） |
| `/disable_approval` | 关闭人工确认（自动模式） |
| `/enable_approval` | 开启人工确认 |

## ⚙️ 配置详解

### 交易品种选择

OKX自动交易使用 VeighNa 本地合约格式：`品种USDT_SWAP_OKX.GLOBAL`

常见品种：
- `BTCUSDT_SWAP_OKX.GLOBAL`（比特币永续合约）
- `ETHUSDT_SWAP_OKX.GLOBAL`（以太坊永续合约）
- `DOGEUSDT_SWAP_OKX.GLOBAL`（DOGE永续合约）

### 多品种交易

默认的 `strategy` 字段保持单品种兼容。如果要同时交易多个品种，把
`strategies` 设置为非空列表；系统会为每个条目创建独立 CTA 策略实例，
每个实例独立订阅行情、计算信号、发 Telegram 消息和下单。

```json
"strategies": [
    {
        "strategy_name": "DoubleMA_DOGE",
        "vt_symbol": "DOGEUSDT_SWAP_OKX.GLOBAL",
        "setting": {
            "fast_window": 18,
            "slow_window": 20
        }
    },
    {
        "strategy_name": "DoubleMA_BTC",
        "vt_symbol": "BTCUSDT_SWAP_OKX.GLOBAL",
        "setting": {
            "fast_window": 18,
            "slow_window": 20
        }
    },
    {
        "strategy_name": "DoubleMA_ETH",
        "vt_symbol": "ETHUSDT_SWAP_OKX.GLOBAL",
        "setting": {
            "fast_window": 18,
            "slow_window": 20
        }
    }
]
```

多品种时 `trading.position_ratio` 是每个策略实例都会使用的比例。比如
`position_ratio=0.05` 且启用 3 个品种，极端情况下组合目标敞口可接近
15%。模拟盘首次验证建议保持 `notification.mode=notify_only`、低杠杆和小
`position_ratio`，并用 `tools/okx_auto_health.py` 检查每个品种都有新 tick。

### 策略参数调整

**DoubleMA策略：**
```json
"setting": {
    "fast_window": 10,  // 快线周期，建议5-20
    "slow_window": 20   // 慢线周期，建议15-60，必须大于快线
}
```

- 短线交易：快线=5，慢线=15
- 中线交易：快线=10，慢线=20（推荐）
- 长线交易：快线=20，慢线=60

### 人工确认设置

```json
"approval": {
    "enabled": true,           // true=需要确认，false=自动交易
    "timeout_seconds": 300     // 等待确认的超时时间（秒）
}
```

## 🔧 进阶功能

### 修改策略

1. 编辑 `double_ma_telegram_strategy.py`
2. 修改交易逻辑（`on_bar`方法）
3. 重启系统

### 添加新策略

1. 复制 `double_ma_telegram_strategy.py`
2. 修改类名和逻辑
3. 在 `run_auto_trading.py` 中导入并使用

### 每日自动报告

系统会在每天晚上23:00自动推送当日交易汇总：
- 当日盈亏
- 成交次数
- 胜率统计
- 当前持仓

## ⚠️ 风险提示

1. **模拟盘阶段**：
   - 先用模拟盘跑1-2周，熟悉系统
   - 验证策略在你的交易品种上是否有效
   - 确认Telegram推送正常

2. **转实盘前**：
   - 将 `use_simulated` 改为 `false`
   - 确保API Key有交易权限
   - 建议先小资金测试

3. **常见问题**：
   - **收不到推送**：检查Bot Token和Chat ID
   - **回测失败**：确认数据服务正常
   - **连接失败**：检查API Key是否正确

## 🆘 故障排除

### 问题1: pip安装失败
```bash
pip install python-telegram-bot --upgrade
```

### 问题2: 回测没有数据
- 确保已安装数据服务模块
- 或修改回测使用本地数据

### 问题3: Telegram消息发不出
1. 检查网络是否能访问Telegram
2. 确认Bot Token正确
3. 给机器人发送 `/start` 激活对话

## 📝 更新日志

**v1.0 (2025-01-15)**
- ✅ OKX模拟盘连接
- ✅ DoubleMA策略
- ✅ Telegram人工确认
- ✅ 回测报告展示
- ✅ 成交实时推送

## 🎯 后续计划

- [ ] 自动参数优化（每周自动调整）
- [ ] 多策略组合
- [ ] 风控系统（止损、仓位管理）
- [ ] 更详细的回测报告
- [ ] Web管理界面

---

**有问题？** 随时问我！
