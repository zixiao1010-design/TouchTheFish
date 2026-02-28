# TouchTheFish

每日定时把外汇汇率、简单大数据分析、全球重点新闻（及可选连载故事）推送到微信。

## 功能

- **外汇汇率**：多币种表格（如 USD/CNY, EUR/CNY 等），数据来自 [ExchangeRate-API](https://www.exchangerate-api.com/)
- **大数据趋势与预测**：基于本地历史 CSV 的简单统计与趋势描述（仅供参考）
- **今日全球重点新闻**：经济、政治、旅游、科技、投资五类，每类若干条（中国新闻网 RSS）
- **今日连载**（可选）：按配置的起始日期连续 10 天推送故事内容，之后自动不再带连载
- **多 SendKey**：支持多个 Server酱 Turbo SendKey，同一条内容会推送给每个 Key
- **小红书入口**：可配置一条链接，在消息底部展示「点这里查看今日长文」

## 环境与依赖

- Python 3.7+
- `pip install -r requirements.txt`（主要：`requests`, `feedparser`）

## 配置

在 `fx_wechat_multi.py` 顶部修改：

- `SERVERCHAN_KEYS`：你的 Server酱 Turbo SendKey 列表（[sct.ftqq.com](https://sct.ftqq.com/)）
- `XHS_LINK`：小红书主页或某篇笔记链接，不需要则留空 `""`
- `PAIRS`：要展示的货币对
- `STORY_START_DATE`：连载起始日期（默认 3 月 1 日），连续 10 天有故事内容
- `NEWS_FEEDS`：各分类的 RSS 源（可换成你能访问的源）

脚本内路径已改为**相对项目目录**，克隆后可直接在项目根目录运行。

## 运行

```bash
python3 fx_wechat_multi.py
```

日志会打印到 stdout；若用 cron，可重定向到 `log/fx_wechat_multi.log`。

## 定时任务（crontab）

每天早上 5 点执行一次示例：

```bash
0 5 * * * /usr/bin/python3 /path/to/TouchTheFish/fx_wechat_multi.py >> /path/to/TouchTheFish/log/fx_wechat_multi.log 2>&1
```

将 `/path/to/TouchTheFish` 换成你本地的项目路径。

## 说明

- 汇率历史会写入项目下 `log/fx_history.csv`，用于简单趋势分析；该文件已在 `.gitignore` 中，不会提交到仓库。
- 连载 10 集结束后，脚本仍会每天正常推送（汇率 + 分析 + 新闻），仅不再附带故事内容，并在日志中输出 `[INFO] 超出连载推送周期，今日无连载内容。`
