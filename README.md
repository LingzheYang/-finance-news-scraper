# 金融快讯爬虫 (finance-news-scraper)

爬取同花顺市场快讯，自动进行单条分析和综合市场分析。

## 安装

```bash
pip install requests
```

## 使用方法

### 默认（最近1小时 + 分析）

```bash
python ~/.claude/skills/finance-news-scraper/scraper.py
```

### 指定时间段

```bash
python ~/.claude/skills/finance-news-scraper/scraper.py --start 14:00 --end 15:00
```

### 只获取数据，不进行分析

```bash
python ~/.claude/skills/finance-news-scraper/scraper.py --no-advice
```

### 保存到指定文件

```bash
python ~/.claude/skills/finance-news-scraper/scraper.py --output my_news.json
```

**默认输出**: `latest.json`（最近运行的结果）

## 输出内容

1. **单条快讯分析**: 每条快讯显示原文内容、情绪（看多/看空/中性）、涉及板块、板块影响分析、信号、风险、建议
2. **综合分析报告**: 市场情绪统计、板块详细影响分析、热门机会、风险提示、投资建议

## 数据源

| 源 | 状态 |
|---|---|
| 同花顺 | ✅ 可用 |

## 板块覆盖

| 板块 | 利好因素 | 利空因素 |
|------|---------|---------|
| 黄金 | 避险、冲突、战争、制裁、通胀 | 加息、美元走强 |
| 原油 | 减产、供应中断、需求增长 | 增产、库存增加 |
| 军工 | 军费增长、地缘冲突 | 和平、裁军 |
| 半导体 | AI、算力、国产替代 | 出口管制、制裁 |
| 金融 | 牛市、成交放量 | 熊市、成交萎缩 |
| 消费 | 消费增长、政策刺激 | 消费降级 |

## JSON输出格式

```json
{
  "news": [
    {
      "time": "14:38:30",
      "title": "北约军费增长推动军工板块",
      "content": "完整原文内容...",
      "source": "同花顺",
      "analysis": {
        "sentiment": "看多",
        "sectors": ["军工"],
        "sector_impacts": [{
          "sector": "军工",
          "direction": "利好",
          "desc": "军工板块受益于地缘紧张和军费增长"
        }],
        "signals": ["增长"],
        "risks": [],
        "suggestion": "关注 军工 板块"
      }
    }
  ],
  "advice": {
    "summary": "共分析 18 条快讯",
    "stats": {"positive": 8, "negative": 3, "sectors": {...}},
    "sector_analysis": [{
      "sector": "军工",
      "direction": "利好",
      "impact_desc": "军工板块受益于地缘紧张和军费增长"
    }],
    "recommendation": "综合建议：市场情绪较强，可适度关注..."
  }
}
```
