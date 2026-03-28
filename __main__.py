#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融快讯爬虫 - 同花顺版
支持分页获取历史数据 + 投资建议分析
"""
import os
import sys
import json
import argparse
import requests
import io
import warnings
from datetime import datetime

# ========== 修复 Windows 终端编码问题 ==========
# 优先使用 UTF-8 编码
if sys.platform == 'win32':
    # Windows 上强制设置 stdout 为 UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        # 降级方案：使用 io.TextIOWrapper 包装
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # 禁用 urllib3 的不安全请求警告（避免输出乱码）
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    # 禁用所有 urllib3 相关的警告
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass
else:
    # 非 Windows 系统也配置 UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# 安全打印函数，处理编码错误
def safe_print(msg, fallback_msg="[内容包含无法显示的字符]"):
    """安全打印，处理终端编码问题"""
    try:
        print(msg)
    except UnicodeEncodeError:
        # 尝试替换无法编码的字符
        try:
            print(msg.encode('utf-8', errors='replace').decode('utf-8'))
        except Exception:
            print(fallback_msg)


class TonghuashunScraper:
    """同花顺快讯爬虫"""

    BASE_URL = 'https://news.10jqka.com.cn/tapp/news/push/stock/'

    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://news.10jqka.com.cn/',
        }

    def fetch_page(self, page=1, page_size=20):
        """获取指定页码的数据"""
        url = f'{self.BASE_URL}?page={page}&pageSize={page_size}'
        try:
            r = self.session.get(url, headers=self.headers, timeout=15, verify=False)
            if r.status_code == 200:
                data = json.loads(r.content)
                return data.get('data', {}).get('list', [])
        except Exception as e:
            print(f'[错误] 请求失败: {e}')
        return []

    def fetch_time_range(self, start_hour, end_hour, max_pages=30, start_min=0, end_min=59):
        """获取指定时间段内的快讯"""
        all_news = []

        print(f'[*] 搜索 {start_hour}:{start_min:02d}-{end_hour}:{end_min:02d} 的快讯...')

        for page in range(1, max_pages + 1):
            items = self.fetch_page(page)
            if not items:
                break

            first_time = datetime.fromtimestamp(int(items[0].get('ctime', 0)))
            last_time = datetime.fromtimestamp(int(items[-1].get('ctime', 0)))
            print(f'  Page {page}: {first_time.strftime("%H:%M")} - {last_time.strftime("%H:%M")}')

            for item in items:
                ctime = int(item.get('ctime', 0))
                dt = datetime.fromtimestamp(ctime)

                # 时间过滤：检查是否在指定时间段内
                in_range = False
                if start_hour < end_hour:
                    # 同一天，如 9:30-15:00
                    if start_hour <= dt.hour <= end_hour:
                        if dt.hour == start_hour and dt.minute < start_min:
                            continue
                        if dt.hour == end_hour and dt.minute > end_min:
                            continue
                        in_range = True
                elif start_hour == end_hour:
                    # 同一小时，如 09:00-09:59
                    if dt.hour == start_hour and dt.minute >= start_min and dt.minute <= end_min:
                        in_range = True
                else:
                    # 跨天情况（从0点到现在），如 22:00-08:00
                    if dt.hour >= start_hour or dt.hour <= end_hour:
                        if dt.hour == end_hour and dt.minute > end_min:
                            continue
                        in_range = True

                if in_range:
                    all_news.append({
                        'time': dt.strftime('%H:%M:%S'),
                        'full_time': dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'title': item.get('title', ''),
                        'content': item.get('short', '') or item.get('digest', ''),
                        'source': '同花顺',
                        'page': page
                    })

            # 如果最后一页的时间已经早于开始时间，停止
            if last_time.hour < start_hour:
                print(f'[*] 已越过目标时间段，停止搜索')
                break

        return all_news


class InvestmentAdvisor:
    """投资建议分析器"""

    # 板块影响力映射：板块 -> {利好因素, 利空因素}
    SECTOR_IMPACT = {
        '黄金': {
            'keywords': ['黄金', '金价', '现货金', '期货金', '贵金属'],
            'positive': ['避险', '冲突', '战争', '制裁', '通胀', '宽松', '降息', '量化宽松'],
            'negative': ['加息', '紧缩', '美元走强', '风险偏好', '抛售'],
            'impact_desc': '黄金是典型避险资产，地缘冲突/通胀预期上升时上涨'
        },
        '原油': {
            'keywords': ['原油', '油价', '石油', '能源', '天然气', 'OPEC'],
            'positive': ['减产', '供应中断', '需求增长', '库存下降', '制裁'],
            'negative': ['增产', '库存增加', '需求下降', '经济衰退'],
            'impact_desc': '原油受供需和地缘双重影响，供应中断或需求增长时上涨'
        },
        '军工': {
            'keywords': ['军工', '航天', '航空', '导弹', '国防', '军费', '国防支出', '军事'],
            'positive': ['军费增长', '国防预算', '地缘冲突', '武器出口', '演习'],
            'negative': ['和平', '裁军', '军费削减'],
            'impact_desc': '军工板块受益于地缘紧张和军费增长，冲突时期表现强劲'
        },
        '半导体': {
            'keywords': ['半导体', '芯片', 'AI', '人工智能', '算力', '集成电路', '晶圆'],
            'positive': ['AI', '人工智能', '算力', '增长', '突破', '创新', '国产替代'],
            'negative': ['出口管制', '制裁', '砍单', '库存积压'],
            'impact_desc': '半导体受益于AI热潮和国产替代，外部制裁是主要风险'
        },
        '消费': {
            'keywords': ['消费', '零售', '旅游', '食品', '餐饮', '家电', '汽车'],
            'positive': ['消费增长', '政策刺激', '五一', '十一', '春节', '促销'],
            'negative': ['消费降级', '居民储蓄', '收入下降'],
            'impact_desc': '消费板块与居民收入和消费意愿高度相关'
        },
        '金融': {
            'keywords': ['银行', '保险', '证券', '券商', '期货', '多元金融'],
            'positive': ['牛市', '成交放量', '利率上升', '业绩增长'],
            'negative': ['熊市', '成交萎缩', '利率下降', '坏账'],
            'impact_desc': '金融板块受益于市场活跃度和利率环境'
        },
        '创业板': {
            'keywords': ['创业板', '新能源', '光伏', '风电', '锂电池', '储能'],
            'positive': ['政策支持', '技术突破', '海外市场', '增长'],
            'negative': ['补贴退坡', '产能过剩', '价格战', '出口受阻'],
            'impact_desc': '创业板以新能源为主，受政策和技术周期影响大'
        },
        '房地产': {
            'keywords': ['地产', '房产', '万科', '恒大', '碧桂园', '房价'],
            'positive': ['政策松绑', '降息', '销售增长', '并购'],
            'negative': ['政策收紧', '销售下降', '债务危机', '房价下跌'],
            'impact_desc': '房地产受政策影响大，当前处于风险消化期'
        },
        '航运': {
            'keywords': ['航运', '港口', '集装箱', '油轮', '海运'],
            'positive': ['运费上涨', '贸易增长', '封锁', '绕道'],
            'negative': ['运费下跌', '贸易萎缩', '运力过剩'],
            'impact_desc': '航运板块与全球贸易和地缘事件高度相关'
        },
        '医药': {
            'keywords': ['医药', '疫苗', '医疗器械', '中药', '创新药', '生物医药'],
            'positive': ['研发进展', '政策支持', '业绩增长', '出口'],
            'negative': ['集采', '医保谈判', '业绩下滑'],
            'impact_desc': '医药板块受政策影响大，创新药和出口是看点'
        }
    }

    # 全局情绪关键词
    POSITIVE_WORDS = [
        '涨', '上涨', '拉升', '反弹', '回升', '利好', '突破', '创新高',
        '增持', '买入', '推荐', '看好', '布局', '机会', '增长', '盈利',
        '签约', '合作', '订单', '中标', '业绩增长', '同比增长', '大幅增长'
    ]

    NEGATIVE_WORDS = [
        '跌', '下跌', '暴跌', '回落', '利空', '止损', '减持', '卖出',
        '亏损', '下降', '下滑', '减少', '风险', '警告', '制裁', '冲突'
    ]

    RISK_ALERTS = [
        '警告', '风险', '避险', '恐慌', '制裁', '冲突', '战争',
        '无人机', '导弹', '袭击', '封锁', '暴跌', '跳水', '违约'
    ]

    def _detect_sectors(self, text):
        """检测涉及的所有板块"""
        found = []
        for sector, info in self.SECTOR_IMPACT.items():
            for kw in info['keywords']:
                if kw in text:
                    found.append(sector)
                    break
        return found

    def _analyze_sector_impact(self, text, sector):
        """分析某事件对特定板块的影响"""
        info = self.SECTOR_IMPACT.get(sector, {})
        if not info:
            return None

        impact = {'sector': sector, 'direction': '中性', 'reasons': [], 'desc': info.get('impact_desc', '')}

        # 检查利好因素
        pos_count = sum(1 for w in info['positive'] if w in text)
        # 检查利空因素
        neg_count = sum(1 for w in info['negative'] if w in text)

        # 检查全局涨跌信号
        for w in self.POSITIVE_WORDS:
            if w in text and '增长' not in impact['reasons'] and '上涨' not in impact['reasons']:
                impact['reasons'].append(f'包含正面信号:{w}')
                break

        for w in self.NEGATIVE_WORDS:
            if w in text:
                if '下降' in text or '下跌' in text or '亏损' in text:
                    if '利空' not in impact['reasons']:
                        impact['reasons'].append(f'包含负面信号:{w}')
                break

        # 判断方向
        if pos_count > neg_count:
            impact['direction'] = '利好'
        elif neg_count > pos_count:
            impact['direction'] = '利空'

        return impact

    def analyze(self, news_list):
        """分析快讯，生成详细的投资建议"""
        if not news_list:
            return {
                'summary': '暂无数据',
                'trends': [],
                'sector_analysis': [],
                'opportunities': [],
                'risks': [],
                'recommendation': '建议：数据不足，无法做出分析'
            }

        # 统计
        stats = {
            'total': len(news_list),
            'positive': 0,
            'negative': 0,
            'sectors': {},
            'alerts': []
        }

        # 板块分析结果
        sector_impacts = {}  # sector -> {direction, reasons, news}

        opportunities = []
        risks = []

        for news in news_list:
            title = news.get('title', '')
            content = news.get('content', '')
            text = title + ' ' + content

            # 检测情绪
            pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text)
            neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text)

            if pos_count > neg_count:
                stats['positive'] += 1
            elif neg_count > pos_count:
                stats['negative'] += 1

            # 检测板块
            detected_sectors = self._detect_sectors(text)
            for sector in detected_sectors:
                stats['sectors'][sector] = stats['sectors'].get(sector, 0) + 1

                # 深入分析该板块影响
                impact = self._analyze_sector_impact(text, sector)
                if impact and impact['direction'] != '中性':
                    if sector not in sector_impacts:
                        sector_impacts[sector] = {
                            'direction': impact['direction'],
                            'reasons': [],
                            'news': []
                        }
                    sector_impacts[sector]['reasons'].extend(impact['reasons'])
                    sector_impacts[sector]['news'].append({
                        'title': title[:50],
                        'time': news['time'],
                        'direction': impact['direction']
                    })

            # 检测风险
            for alert_word in self.RISK_ALERTS:
                if alert_word in text:
                    if alert_word not in [r['alert'] for r in risks]:
                        risks.append({
                            'alert': alert_word,
                            'title': title[:60],
                            'time': news['time'],
                            'sectors': detected_sectors
                        })

            # 收集机会
            if detected_sectors:
                for sector in detected_sectors[:1]:
                    if sector not in [o['sector'] for o in opportunities]:
                        opportunities.append({
                            'sector': sector,
                            'title': title[:60],
                            'time': news['time']
                        })

        # 生成板块分析
        sector_analysis = []
        for sector, data in sorted(sector_impacts.items(), key=lambda x: stats['sectors'].get(x[0], 0), reverse=True):
            analysis = {
                'sector': sector,
                'direction': data['direction'],
                'news_count': stats['sectors'].get(sector, 0),
                'impact_desc': self.SECTOR_IMPACT.get(sector, {}).get('impact_desc', ''),
                'news': data['news'][:2]  # 最多2条代表新闻
            }
            sector_analysis.append(analysis)

        # 生成建议
        trends = []
        if stats['positive'] > stats['negative']:
            trends.append(f'市场情绪偏多（正面{stats["positive"]}条 vs 负面{stats["negative"]}条）')
        elif stats['negative'] > stats['positive']:
            trends.append(f'市场情绪偏空（负面{stats["negative"]}条 vs 正面{stats["positive"]}条）')
        else:
            trends.append('市场情绪中性')

        # 热门板块
        if stats['sectors']:
            hot_sectors = sorted(stats['sectors'].items(), key=lambda x: x[1], reverse=True)[:5]
            trends.append(f'热门板块: {", ".join([s[0] for s in hot_sectors])}')

        # 风险提示
        risk_alerts = list(set([r['alert'] for r in risks]))[:5]
        if risk_alerts:
            trends.append(f'风险关注: {", ".join(risk_alerts)}')

        # 生成详细建议
        recommendation = '综合建议：'
        if stats['positive'] > stats['negative'] * 2:
            recommendation += '市场情绪较强，可适度关注；'
        elif stats['negative'] > stats['positive'] * 2:
            recommendation += '市场情绪较弱，保持谨慎；'
        else:
            recommendation += '市场情绪分化，注意风险；'

        # 板块具体建议
        for sa in sector_analysis[:3]:
            if sa['direction'] == '利好':
                recommendation += f'{sa["sector"]}板块受利好推动，可关注；'
            elif sa['direction'] == '利空':
                recommendation += f'{sa["sector"]}板块面临压力，谨慎；'

        recommendation = recommendation.rstrip('；') + '。'

        return {
            'summary': f'共分析 {stats["total"]} 条快讯',
            'stats': stats,
            'trends': trends,
            'sector_analysis': sector_analysis,
            'opportunities': opportunities[:5],
            'risks': risks[:5],
            'recommendation': recommendation
        }

    def analyze_single(self, news_item):
        """分析单条快讯，返回详细分析结果"""
        title = news_item.get('title', '')
        content = news_item.get('content', '')
        text = title + ' ' + content

        result = {
            'sentiment': '中性',
            'sectors': [],
            'sector_impacts': [],  # 新增：每个板块的影响分析
            'signals': [],
            'risks': [],
            'suggestion': None
        }

        # 检测情绪
        pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text)

        if pos_count > neg_count:
            result['sentiment'] = '看多'
        elif neg_count > pos_count:
            result['sentiment'] = '看空'

        # 检测板块及其影响
        detected_sectors = self._detect_sectors(text)
        for sector in detected_sectors:
            result['sectors'].append(sector)

            # 分析该板块的具体影响
            impact = self._analyze_sector_impact(text, sector)
            if impact:
                result['sector_impacts'].append(impact)

        # 检测风险关键词
        for alert_word in self.RISK_ALERTS:
            if alert_word in text and alert_word not in result['risks']:
                result['risks'].append(alert_word)

        # 记录信号
        for w in self.POSITIVE_WORDS:
            if w in text and w not in result['signals']:
                result['signals'].append(w)
                if len(result['signals']) >= 3:
                    break

        # 生成建议
        if result['sentiment'] == '看多' and result['sectors']:
            impacts = [f"{s['sector']}({s['direction']})" for s in result['sector_impacts']]
            result['suggestion'] = f'关注 {"/".join(result["sectors"])} 板块 - {" ".join([i for i in impacts if "利好" in i])}'
        elif result['sentiment'] == '看空':
            result['suggestion'] = '注意风险，谨慎操作'
        elif result['risks']:
            result['suggestion'] = f'关注市场风险，板块: {", ".join(result["sectors"]) if result["sectors"] else "待观察"}'

        return result


def parse_time(time_str):
    """解析时间字符串，返回小时"""
    return int(time_str.split(':')[0])


def parse_time_full(time_str):
    """解析时间字符串，返回(小时, 分钟)"""
    parts = time_str.split(':')
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def get_current_time_str():
    """获取当前时间字符串 HH:MM"""
    now = datetime.now()
    return now.strftime('%H:%M')


def get_one_hour_ago_str():
    """获取1小时前的时间字符串 HH:MM"""
    from datetime import timedelta
    one_hour_ago = datetime.now() - timedelta(hours=1)
    return one_hour_ago.strftime('%H:%M')


def main():
    parser = argparse.ArgumentParser(description='金融快讯爬虫 + 投资建议')
    parser.add_argument('--source', default='tonghuashun', choices=['tonghuashun', 'jin10'],
                        help='数据源 (默认: tonghuashun)')
    parser.add_argument('--start', default=None, help='开始时间 HH:MM (默认: 1小时前)')
    parser.add_argument('--end', default=None, help='结束时间 HH:MM (默认: 当前时间)')
    parser.add_argument('--output', default=None, help='输出文件路径')
    parser.add_argument('--pages', type=int, default=5, help='最大翻页数 (默认: 5)')
    parser.add_argument('--no-advice', action='store_true', help='不生成投资建议')

    args = parser.parse_args()

    # 如果未指定开始时间，默认获取最近1小时
    if args.start is None:
        args.start = get_one_hour_ago_str()
        print(f'[*] 未指定开始时间，获取最近1小时数据: {args.start} - 现在')

    # 如果未指定结束时间，使用当前时间
    if args.end is None:
        args.end = get_current_time_str()
        print(f'[*] 未指定结束时间，使用当前时间: {args.end}')

    start_hour, start_min = parse_time_full(args.start)
    end_hour, end_min = parse_time_full(args.end)

    # 如果结束时间早于开始时间，说明是次日，添加一天的处理
    # 但这里简化处理：只比较小时
    if end_hour < start_hour:
        print(f'[!] 结束时间早于开始时间，将获取跨天数据...')

    print(f'='*60)
    print(f'金融快讯爬虫 - {args.source}')
    print(f'时间段: {args.start} - {args.end}')
    print(f'='*60)

    if args.source == 'tonghuashun':
        scraper = TonghuashunScraper()
        news = scraper.fetch_time_range(start_hour, end_hour, max_pages=args.pages,
                                         start_min=start_min, end_min=end_min)

        print(f'\n[+] 共获取 {len(news)} 条快讯')

        if news:
            # 初始化投资建议分析器
            advisor = InvestmentAdvisor() if not args.no_advice else None

            # 先为每条快讯添加单独分析（避免重复计算）
            news_with_analysis = []
            single_analyses = []  # 保存单独分析结果用于打印
            for item in news:
                analysis = advisor.analyze_single(item) if advisor else None
                single_analyses.append(analysis)
                item_with_analysis = item.copy()
                item_with_analysis['analysis'] = analysis
                news_with_analysis.append(item_with_analysis)

            # 先保存JSON，确保数据不丢失
            output_file = args.output or 'latest.json'
            advice_result = advisor.analyze(news) if advisor else None
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'news': news_with_analysis,
                    'advice': advice_result
                }, f, ensure_ascii=False, indent=2)
            safe_print(f'\n[+] 已保存到 {output_file}')

            if not args.no_advice:
                safe_print(f'\n{"="*70}')
                safe_print('快讯详情 + 个股分析')
                safe_print(f'{"="*70}')

                for i, item in enumerate(news, 1):
                    analysis = single_analyses[i-1]  # 使用已计算的分析结果

                    # 按SKILL.md格式输出：【1】时间 -> 标题 -> 内容 -> 情绪 | 板块 -> 板块影响 -> 信号/风险
                    safe_print(f'\n【{i}】{item["time"]}')
                    safe_print(f'【标题】{item["title"]}')
                    # 内容可能包含特殊字符，使用try-except处理
                    content = item["content"]
                    if len(content) > 200:
                        safe_print(f'【内容】{content[:200]}...')
                    else:
                        safe_print(f'【内容】{content}')

                    # 情绪和板块
                    sentiment = analysis.get('sentiment', '中性')
                    sectors = analysis.get('sectors', [])
                    if sectors:
                        safe_print(f'【情绪】{sentiment} | 【板块】{"/".join(sectors)}')
                    else:
                        safe_print(f'【情绪】{sentiment}')

                    # 板块影响
                    if analysis.get('sector_impacts'):
                        impact_parts = []
                        for imp in analysis['sector_impacts']:
                            reason_str = ' '.join(imp.get('reasons', [])) if imp.get('reasons') else ''
                            if reason_str:
                                impact_parts.append(f'{imp["sector"]}: {imp["direction"]}（{reason_str}）')
                            else:
                                impact_parts.append(f'{imp["sector"]}: {imp["direction"]}')
                        safe_print(f'【板块影响】' + ' '.join(impact_parts))

                    # 信号
                    if analysis.get('signals'):
                        safe_print(f'【信号】{"/".join(analysis["signals"])}')

                    # 风险
                    if analysis.get('risks'):
                        safe_print(f'【风险】{"/".join(analysis["risks"])}')

                safe_print(f'\n{"="*70}')
                safe_print('综合分析报告')
                safe_print(f'{"="*70}')

                safe_print(f'\n{advice_result["summary"]}')
                safe_print('')
                safe_print(f'市场情绪: {advice_result["stats"]["positive"]}条看多 vs {advice_result["stats"]["negative"]}条看空')

                safe_print('')
                safe_print('【市场趋势】')
                for trend in advice_result['trends']:
                    safe_print(f'  - {trend}')

                safe_print('')
                safe_print('【热门机会】')
                for opp in advice_result['opportunities']:
                    safe_print(f'  - [{opp["sector"]}] {opp["title"]}')

                safe_print('')
                safe_print('【风险提示】')
                for risk in advice_result['risks']:
                    safe_print(f'  - [{risk["alert"]}] {risk["title"]}')

                safe_print('')
                safe_print('【投资建议】')
                safe_print(f'  {advice_result["recommendation"]}')
            else:
                # 不带分析时只显示列表
                safe_print(f'\n快讯列表:')
                for i, item in enumerate(news[:20], 1):
                    safe_print(f'{i}. [{item["time"]}] {item["title"]}')

                if len(news) > 20:
                    safe_print(f'... 还有 {len(news) - 20} 条')
        else:
            print('\n[-] 没有获取到数据')

    elif args.source == 'jin10':
        print('[*] 金十爬虫尚未实现')
        print('[!] 金十免费版只有约5条，需要VIP才能获取更多')


if __name__ == '__main__':
    main()
