import requests
import datetime
import traceback
import os
import csv
from typing import Optional

try:
    import feedparser  # 用于新闻 RSS 解析
    FEEDPARSER_AVAILABLE = True
except ImportError:
    feedparser = None
    FEEDPARSER_AVAILABLE = False

# 项目根目录（脚本所在目录），克隆后可直接在项目根运行
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==== 配置区域 ====
# 支持多个 Server酱 SendKey（可以填一个或多个）
SERVERCHAN_KEYS = [
    "SCTxxxxxxxxxxxxxxxx",  # 替换为你的 SendKey，可填多个
]

# 如果你有固定的小红书主页或某篇合集笔记链接，可以配置在这里；
# 不配置（留空字符串）时，微信消息中不会出现小红书入口。
XHS_LINK = ""  # 例如："https://www.xiaohongshu.com/user/profile/xxxx"

# 外汇历史数据本地存储文件（用于简单统计分析与预测）
HISTORY_FILE = os.path.join(_BASE_DIR, "log", "fx_history.csv")

# Turbo 版 Server酱 API 域名为 sctapi.ftqq.com，使用 POST，参数为 title / desp

# 外汇 API（使用 ExchangeRate-API 的开放接口）
FX_API_BASE = "https://open.er-api.com/v6/latest"

# 需要监控的货币对列表
# 形式：("基础货币", "目标货币")
# 你可以根据需要自由增减
PAIRS = [
    ("USD", "CNY"),
    ("EUR", "CNY"),
    ("JPY", "CNY"),
    ("GBP", "CNY"),
    ("HKD", "CNY"),
    ("CZK", "CNY"),
    ("NZD", "CNY"),
]

# 连载故事配置
# 故事从该日期开始连载：
# 第 1 天第 1 集，第 2 天第 2 集，…，第 12 天第 12 集，第 12 天以后不再带连载内容（每日推送照常）
STORY_START_DATE = datetime.date(2026, 3, 1)
STORY_EPISODE_FILES = [os.path.join(_BASE_DIR, f"story_episode_{i}.md") for i in range(1, 13)]

# 下午 12 点及之后推送时，会显示「下一集」并在结尾加下集彩蛋。每条不超过 100 字，不剧透当集主要内容。
EPISODE_TEASERS = [
    "站台上的告别还没说完，城堡里已经有人念出了那个被抹去的名字。",
    "地下一层的教室亮起紫光时，谁也没想到，先出手的会是校长。",
    "禁林的落叶下，有一道门正在等人来选：推开，还是锁死。",
    "神秘事务司的暗厅里，三重圆环已经点亮。只差一步。",
    "献祭厅的紫光散尽之后，世界并没有立刻改变——直到有人开始问第三句话。",
    "冬天来了，宝石在证物库里又闪了一次。没有人知道，那是什么在叹气。",
    "北欧的庄园里，有人在一张旧纸上，写下了关于「门扉」的新预言。",
    "这一次，他们决定自己定义：谁有资格站在那道门的旁边。",
    "影子分散之后，奥勒留斯在梦里说：我不再只对你一个人说话了。",
    "有人想烧掉所有关于「第三种选择」的记录。他们要先写下来，再守住。",
    "很多年后，哈利退休的那天，阿不思说：我们试过了。",
]

# 每个新闻主题拉取的条数
NEWS_ITEMS_PER_CATEGORY = 5

# 新闻 RSS 源（首选 + 备选），优先选用中国新闻网的官方 RSS，
# 如需调整，可自行替换为你本地能访问的其他 RSS 源。
NEWS_FEEDS = {
    # 经济类：财经为主，辅以要闻和即时
    "经济": [
        "https://www.chinanews.com.cn/rss/finance.xml",       # 财经（首选）
        "https://www.chinanews.com.cn/rss/importnews.xml",    # 要闻导读（备选）
        "https://www.chinanews.com.cn/rss/scroll-news.xml",   # 即时滚动新闻（备选）
    ],
    # 政治类：时政 + 国际
    "政治": [
        "https://www.chinanews.com.cn/rss/china.xml",         # 时政（首选）
        "https://www.chinanews.com.cn/rss/world.xml",         # 国际新闻（备选）
        "https://www.chinanews.com.cn/rss/importnews.xml",    # 要闻导读（备选）
    ],
    # 旅游类：生活方式 + 大湾区 + 文化
    "旅游": [
        "https://www.chinanews.com.cn/rss/life.xml",          # 生活频道，含大量出行/消费内容（首选）
        "https://www.chinanews.com.cn/rss/dwq.xml",           # 大湾区相关资讯（备选）
        "https://www.chinanews.com.cn/rss/culture.xml",       # 文娱文化（备选）
    ],
    # 科技类：东西问（深度）、国际、要闻
    "科技": [
        "https://www.chinanews.com.cn/rss/dxw.xml",           # 东西问，深度评论与观察（首选，常含科技/创新话题）
        "https://www.chinanews.com.cn/rss/world.xml",         # 国际新闻（备选）
        "https://www.chinanews.com.cn/rss/importnews.xml",    # 要闻导读（备选）
    ],
    # 投资类：财经为主，辅以华人/大湾区经贸信息
    "投资": [
        "https://www.chinanews.com.cn/rss/finance.xml",       # 财经（首选）
        "https://www.chinanews.com.cn/rss/chinese.xml",       # 华人（常见经贸/投资相关内容，备选）
        "https://www.chinanews.com.cn/rss/dwq.xml",           # 大湾区（区域经贸与投资热点，备选）
    ],
}


def fetch_rates_grouped_by_base(pairs):
    """
    按基础货币分组请求，避免重复调用 API
    返回示例：
    { "USD": {"CNY": 7.1, ...}, "EUR": {...} }
    """
    bases = {base for base, _ in pairs}
    all_rates = {}

    for base in bases:
        url = f"{FX_API_BASE}/{base}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("result") != "success":
            raise RuntimeError(f"FX API error for {base}: {data}")

        all_rates[base] = data["rates"]

    return all_rates


def build_content(
    pairs,
    all_rates,
    analysis_text: Optional[str] = None,
    news_text: Optional[str] = None,
    story_text: Optional[str] = None,
):
    """
    根据汇率数据构造推送内容（包括当前汇率信息，可选附加大数据预测）
    """
    lines = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"时间：{now}")
    lines.append("")

    # 今日连载放在最上面（时间之后，其他内容之前）
    if story_text:
        lines.append("—— 今日连载 ——")
        lines.append("")
        lines.extend(story_text.splitlines())
        lines.append("")

    # 使用 Markdown 表格展示当前汇率
    lines.append("| 基础货币 | 目标货币 | 当前汇率 |")
    lines.append("| -------- | -------- | -------- |")
    for base, target in pairs:
        rates = all_rates.get(base, {})
        rate = rates.get(target)
        if rate is None:
            display = "无数据"
        else:
            display = f"{rate:.4f}"
        lines.append(f"| {base} | {target} | {display} |")

    lines.append("")
    lines.append("数据来源：ExchangeRate-API 开放接口（open.er-api.com）")

    if analysis_text:
        lines.append("")
        lines.append("—— 大数据趋势与预测 ——")
        lines.append("")
        lines.extend(analysis_text.splitlines())

    if news_text:
        lines.append("")
        lines.append("—— 今日全球重点新闻 ——")
        lines.append("")
        lines.extend(news_text.splitlines())

    # 小红书入口（如果配置了链接，则在消息底部给出跳转入口）
    if XHS_LINK:
        lines.append("")
        lines.append("—— 小红书长文 ——")
        lines.append("")
        lines.append(f"- [点这里查看今日长文]({XHS_LINK})")

    return "\n".join(lines)


def push_wechat_for_key(sendkey: str, title: str, content: str = ""):
    """
    使用单个 Server酱 SendKey 推送到微信
    """
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": title,
        "desp": content,
    }
    resp = requests.post(url, data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def append_history(timestamp: datetime.datetime, pairs, all_rates):
    """
    将本次获取的汇率追加写入本地历史文件
    """
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    file_exists = os.path.exists(HISTORY_FILE)

    with open(HISTORY_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "base", "target", "rate"])

        ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        for base, target in pairs:
            rates = all_rates.get(base, {})
            rate = rates.get(target)
            if rate is None:
                continue
            writer.writerow([ts_str, base, target, rate])


def load_history():
    """
    从本地历史文件读取所有历史数据
    返回结构：{(base, target): [rate1, rate2, ...]}
    """
    history = {}
    if not os.path.exists(HISTORY_FILE):
        return history

    with open(HISTORY_FILE, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            base = row.get("base")
            target = row.get("target")
            try:
                rate = float(row.get("rate", "nan"))
            except ValueError:
                continue
            if not base or not target:
                continue
            key = (base, target)
            history.setdefault(key, []).append(rate)

    return history


def fetch_rss_top_n(url: str, limit: int):
    """
    从单个 RSS 源获取前 limit 条新闻（标题 + 链接）
    """
    # 先用 requests 控制超时时间，再交给 feedparser 解析
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"[WARN] 获取 RSS 失败（{url}）: {e}")
        return []
    items = []
    for entry in getattr(feed, "entries", []):
        title = (getattr(entry, "title", "") or "").strip()
        link = (getattr(entry, "link", "") or "").strip()
        if not title:
            continue
        items.append((title, link))
        if len(items) >= limit:
            break
    return items


def fetch_global_news():
    """
    拉取多个主题的全球新闻
    返回结构：{主题: [(title, link), ...]}
    """
    all_news = {}
    for category, feeds in NEWS_FEEDS.items():
        collected = []
        for url in feeds:
            try:
                collected.extend(fetch_rss_top_n(url, NEWS_ITEMS_PER_CATEGORY))
            except Exception:
                continue

        # 去重 & 截断
        seen = set()
        uniq = []
        for title, link in collected:
            if title in seen:
                continue
            seen.add(title)
            uniq.append((title, link))
            if len(uniq) >= NEWS_ITEMS_PER_CATEGORY:
                break

        all_news[category] = uniq

    return all_news


def build_news_text(all_news: dict) -> str:
    """
    将新闻按主题渲染为 Markdown 文本
    """
    lines = []
    lines.append("### 今日全球重点新闻")
    lines.append("")
    lines.append("> 资讯来自公开新闻 RSS，仅供快速浏览。")
    lines.append("")

    for category, items in all_news.items():
        lines.append(f"**{category}（最多 {NEWS_ITEMS_PER_CATEGORY} 条）**")
        if not items:
            lines.append("- 暂无可用新闻数据。")
        else:
            for title, link in items:
                # 微信里 Markdown 链接会显示为可点击标题
                lines.append(f"- [{title}]({link})")
        lines.append("")

    return "\n".join(lines)


def generate_analysis_text(history, pairs, all_rates):
    """
    基于本地历史数据做一个非常简单的统计分析与“预测”（仅供参考）
    """
    lines = []
    lines.append("### 大数据趋势与预测")
    lines.append("")
    lines.append("> 以下内容基于本地历史数据的简单统计分析，仅供参考，不构成任何投资建议。")
    lines.append("")

    for base, target in pairs:
        key = (base, target)
        rates_history = history.get(key, [])
        current_rate = all_rates.get(base, {}).get(target)

        if current_rate is None:
            lines.append(f"**{base}/{target}**")
            lines.append("- **当前状态**：无有效数据，暂无法分析。")
            lines.append("")
            continue

        if not rates_history:
            lines.append(f"**{base}/{target}**")
            lines.append(f"- **当前汇率**：{current_rate:.4f}")
            lines.append("- **历史数据**：样本过少，仅记录当前值。")
            lines.append("- **趋势判断**：暂无法给出有统计意义的判断，短期更可能维持震荡。")
            lines.append("")
            continue

        avg_rate = sum(rates_history) / len(rates_history)
        if avg_rate == 0:
            lines.append(f"**{base}/{target}**")
            lines.append("- **数据状态**：历史平均为 0，数据异常，暂不分析。")
            lines.append("")
            continue

        diff_pct = (current_rate - avg_rate) / avg_rate * 100

        if diff_pct > 1.0:
            trend_comment = "当前汇率明显高于本地记录的近期平均水平，短期存在一定回调压力。"
        elif diff_pct < -1.0:
            trend_comment = "当前汇率明显低于本地记录的近期平均水平，短期存在一定上行修复空间。"
        else:
            trend_comment = "当前汇率接近本地记录的近期平均水平，短期大概率维持震荡运行。"

        lines.append(f"**{base}/{target}**")
        lines.append(f"- **当前汇率**：{current_rate:.4f}")
        lines.append(f"- **近期均值**：{avg_rate:.4f}（偏离 {diff_pct:+.2f}%）")
        lines.append(f"- **趋势判断**：{trend_comment}")
        lines.append("")

    return "\n".join(lines)


def get_today_story_text(today: datetime.date, run_dt: Optional[datetime.datetime] = None) -> Optional[str]:
    """
    根据连载起始日期、今日日期与运行时刻，选择对应的一集故事内容。
    - 12 点之前跑：显示「当日」对应的一集。
    - 12 点及之后跑：显示「下一集」内容，并在结尾追加下集彩蛋（不超过 100 字，不剧透）。
    第 1 天第 1 集，…，第 12 天第 12 集；第 13 天及以后返回 None（连载结束）。
    """
    if not STORY_EPISODE_FILES:
        return None

    delta_days = (today - STORY_START_DATE).days
    if delta_days < 0 or delta_days > 11:
        return None

    if run_dt is None:
        run_dt = datetime.datetime.now()
    # 12 点及之后视为「下午」，选下一集
    use_next_episode = run_dt.hour >= 12
    idx = min(delta_days + (1 if use_next_episode else 0), len(STORY_EPISODE_FILES) - 1)
    path = STORY_EPISODE_FILES[idx]

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except Exception as e:
        print(f"[WARN] 读取故事文件失败: {path} - {e}")
        return None

    # 下午跑且当前不是最后一集时，追加下集彩蛋（不剧透、≤100 字）
    if use_next_episode and idx < len(STORY_EPISODE_FILES) - 1 and idx < len(EPISODE_TEASERS):
        teaser = EPISODE_TEASERS[idx].strip()
        if len(teaser) > 100:
            teaser = teaser[:100]
        if teaser:
            content = content + "\n\n【下集彩蛋】\n" + teaser

    return content


def main():
    if not SERVERCHAN_KEYS:
        raise RuntimeError("请先在脚本中配置至少一个 SERVERCHAN_KEYS（你的 Server酱 SendKey 列表）。")

    # 简单校验是否还保留了占位符
    for k in SERVERCHAN_KEYS:
        if k.startswith("SCTxxxxxxxx"):
            raise RuntimeError("检测到占位的 SendKey（SCTxxxxxxxx 开头），请将 SERVERCHAN_KEYS 替换为你自己的真实 SendKey。")

    now_dt = datetime.datetime.now()
    delta_days = (now_dt.date() - STORY_START_DATE).days

    # 拉取汇率
    all_rates = fetch_rates_grouped_by_base(PAIRS)

    # 写入本次历史数据
    append_history(now_dt, PAIRS, all_rates)

    # 读取所有历史数据并生成分析与预测文本
    history = load_history()
    analysis_text = generate_analysis_text(history, PAIRS, all_rates)

    # 拉取全球新闻（如缺少 feedparser 则跳过）
    news_text = None
    if FEEDPARSER_AVAILABLE:
        try:
            all_news = fetch_global_news()
            news_text = build_news_text(all_news)
        except Exception as e:
            # 不因为新闻失败而终止整个脚本
            print(f"[WARN] 获取新闻失败: {e}")
    else:
        print("[WARN] 未安装 feedparser，已跳过新闻部分。可运行 `python3 -m pip install feedparser` 启用。")

    # 获取今日连载故事文本（仅 3 月 1 日起 12 天内有内容，之后为 None）
    story_text = get_today_story_text(now_dt.date(), now_dt)
    if delta_days > 11:
        ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[INFO] {ts} 超出连载推送周期（delta_days={delta_days}），今日无连载内容。")

    # 构造内容（汇率 + 大数据预测 + 全球新闻 + 连载故事 放在同一条消息里）
    content = build_content(
        PAIRS,
        all_rates,
        analysis_text=analysis_text,
        news_text=news_text,
        story_text=story_text,
    )

    # 标题简单用第一个货币对做概括
    first_base, first_target = PAIRS[0]
    now_short = datetime.datetime.now().strftime("%H:%M")
    title = f"外汇汇率 + 大数据预测 {now_short} - {first_base}/{first_target}"

    # 依次向每个 SendKey 推送（单条消息，包含汇率 + 预测）
    results = {}
    for sendkey in SERVERCHAN_KEYS:
        result = push_wechat_for_key(sendkey, title, content)
        results[sendkey] = result

    # 成功时简单打一行 OK 日志
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[OK] {ts} 推送成功，Server酱返回: {results}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[ERROR] {ts} 运行失败: {e}")
        traceback.print_exc()
        raise
