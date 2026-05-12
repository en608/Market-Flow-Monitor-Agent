"""
ETF监控系统工具层
提供金融数据获取的工具函数，基于新浪财经API获取实时数据
"""

import logging
import json
import re
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SINA_HQ_URL = "https://hq.sinajs.cn/list={}"
SINA_HEADERS = {
    'Referer': 'https://finance.sina.com.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def get_sina_etf_data(symbol: str) -> Optional[Dict[str, Any]]:
    """使用新浪财经API获取ETF实时数据"""
    try:
        full_symbol = f"sh{symbol}" if not symbol.startswith('sh') and not symbol.startswith('sz') else symbol
        url = SINA_HQ_URL.format(full_symbol)

        response = requests.get(url, headers=SINA_HEADERS, timeout=10)
        response.encoding = 'gbk'

        if response.status_code != 200:
            logger.error(f"新浪API请求失败，状态码: {response.status_code}")
            return None

        text = response.text.strip()

        if 'hq_str' not in text:
            logger.error(f"新浪API返回数据格式错误: {text[:200]}")
            return None

        match = re.search(r'"([^"]+)"', text)
        if not match:
            logger.error(f"无法解析新浪API数据: {text[:200]}")
            return None

        data_str = match.group(1)
        parts = data_str.split(',')

        if len(parts) < 32:
            logger.error(f"新浪API数据字段不足: {data_str[:200]}")
            return None

        return {
            'name': parts[0],
            'open': float(parts[1]) if parts[1] else 0,
            'close_prev': float(parts[2]) if parts[2] else 0,
            'current': float(parts[3]) if parts[3] else 0,
            'high': float(parts[4]) if parts[4] else 0,
            'low': float(parts[5]) if parts[5] else 0,
            'buy': float(parts[6]) if parts[6] else 0,
            'sell': float(parts[7]) if parts[7] else 0,
            'volume': int(parts[8]) if parts[8] else 0,
            'amount': float(parts[9]) if parts[9] else 0,
            'date': parts[30] if len(parts) > 30 else '',
            'time': parts[31] if len(parts) > 31 else ''
        }

    except Exception as e:
        logger.error(f"获取新浪ETF数据失败: {str(e)}", exc_info=True)
        return None


def get_etf_realtime_data(symbol: str = "510500") -> Dict[str, Any]:
    """获取ETF实时数据"""
    try:
        logger.info(f"正在获取ETF实时数据: {symbol}")

        raw_data = get_sina_etf_data(symbol)

        if raw_data is None:
            return {"code": symbol, "error": f"无法获取ETF {symbol} 的实时数据"}

        current_price = raw_data['current']
        close_prev = raw_data['close_prev']

        change_pct = 0
        if close_prev > 0:
            change_pct = round((current_price - close_prev) / close_prev * 100, 2)

        turnover = round(raw_data['amount'] / 10000, 2) if raw_data['amount'] > 0 else 0

        data = {
            "code": symbol,
            "name": raw_data['name'],
            "price": current_price,
            "change": change_pct,
            "volume": raw_data['volume'],
            "turnover": turnover,
            "open": raw_data['open'],
            "high": raw_data['high'],
            "low": raw_data['low'],
            "update_time": f"{raw_data['date']} {raw_data['time']}"
        }

        logger.info(f"成功获取ETF {symbol} 实时数据: 价格={current_price}, 涨跌幅={change_pct}%")
        return data

    except Exception as e:
        logger.error(f"获取ETF实时数据失败: {str(e)}", exc_info=True)
        return {"code": symbol, "error": f"获取ETF实时数据失败: {str(e)}"}


def get_etf_historical_data(symbol: str, count: int = 60) -> Optional[pd.DataFrame]:
    """获取ETF历史K线数据"""
    try:
        full_symbol = f"sh{symbol}" if not symbol.startswith('sh') and not symbol.startswith('sz') else symbol

        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            'symbol': full_symbol,
            'scale': 240,
            'ma': 'no',
            'datalen': min(count, 250)
        }

        response = requests.get(url, params=params, headers=SINA_HEADERS, timeout=10)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            logger.error(f"获取历史数据失败，状态码: {response.status_code}")
            return None

        data = response.json()

        if not data:
            logger.error("历史数据为空")
            return None

        df = pd.DataFrame(data)
        
        df = df.rename(columns={'day': 'date'})

        # 转换数据类型
        for col in ['open', 'close', 'high', 'low']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)

        df = df.tail(count).reset_index(drop=True)
        return df

    except Exception as e:
        logger.error(f"获取ETF历史数据失败: {str(e)}", exc_info=True)
        return None


def calculate_macd(df, short=12, long=26, signal=9):
    """计算MACD指标"""
    df['EMA12'] = df['close'].ewm(span=short, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=long, adjust=False).mean()
    df['DIFF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = df['DIFF'].ewm(span=signal, adjust=False).mean()
    df['MACD'] = 2 * (df['DIFF'] - df['DEA'])
    return df


def calculate_ma(df, periods=[5, 10, 20, 60]):
    """计算均线指标"""
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period).mean()
    return df


def get_etf_technical_indicators(symbol: str = "510500", freq: str = "D", count: int = 60) -> Dict[str, Any]:
    """获取ETF技术指标数据"""
    try:
        logger.info(f"正在获取ETF技术指标: {symbol}, 频率: {freq}, 条数: {count}")

        df = get_etf_historical_data(symbol, count)

        if df is None or df.empty:
            return {"code": symbol, "error": f"无法获取ETF {symbol} 的历史数据"}

        df = calculate_macd(df)
        df = calculate_ma(df)

        result = {
            "code": symbol,
            "freq": freq,
            "kline_data": [],
            "macd": [],
            "ma": []
        }

        for _, row in df.tail(min(10, count)).iterrows():
            result["kline_data"].append({
                "date": row['date'],
                "open": float(row['open']),
                "close": float(row['close']),
                "high": float(row['high']),
                "low": float(row['low']),
                "volume": int(row['volume'])
            })

        for _, row in df.tail(min(10, count)).iterrows():
            result["macd"].append({
                "date": row['date'],
                "dif": float(row['DIFF']),
                "dea": float(row['DEA']),
                "macd": float(row['MACD'])
            })

        for _, row in df.tail(min(10, count)).iterrows():
            ma_data = {"date": row['date']}
            for ma_col in ['MA5', 'MA10', 'MA20', 'MA60']:
                if ma_col in df.columns:
                    ma_data[ma_col] = float(row[ma_col]) if pd.notna(row[ma_col]) else None
            result["ma"].append(ma_data)

        logger.info(f"成功获取ETF {symbol} 技术指标")
        return result

    except Exception as e:
        logger.error(f"获取ETF技术指标失败: {str(e)}", exc_info=True)
        return {"code": symbol, "error": f"获取ETF技术指标失败: {str(e)}"}


def get_future_index_data(symbol: str = "IC") -> Dict[str, Any]:
    """获取股指期货数据

    注意：由于新浪财经API暂不支持股指期货数据，此功能返回提示信息
    如需真实期货数据，可考虑使用akshare或其他数据源
    """
    try:
        logger.info(f"正在获取股指期货数据: {symbol}")

        symbol_map = {
            "IC": ("IC0", "中证500股指期货"),
            "IF": ("IF0", "沪深300股指期货"),
            "IH": ("IH0", "上证50股指期货")
        }

        if symbol not in symbol_map:
            symbol = "IC"

        future_symbol, future_name = symbol_map[symbol]
        raw_data = get_sina_etf_data(future_symbol)

        if raw_data is None or raw_data.get('current', 0) == 0:
            return {
                "symbol": symbol,
                "name": future_name,
                "price": None,
                "change": None,
                "volume": None,
                "update_time": None,
                "note": "股指期货数据暂不可用（新浪API限制），如需真实数据请配置akshare"
            }

        current_price = raw_data['current']
        close_prev = raw_data['close_prev']

        change_pct = 0
        if close_prev > 0:
            change_pct = round((current_price - close_prev) / close_prev * 100, 2)

        result = {
            "symbol": symbol,
            "name": future_name,
            "price": current_price,
            "change": change_pct,
            "volume": raw_data['volume'],
            "update_time": f"{raw_data['date']} {raw_data['time']}"
        }

        logger.info(f"成功获取股指期货 {symbol} 数据: 价格={current_price}")
        return result

    except Exception as e:
        logger.error(f"获取股指期货数据失败: {str(e)}", exc_info=True)
        return {"symbol": symbol, "error": f"获取股指期货数据失败: {str(e)}"}


TOOLS = [
    get_etf_realtime_data,
    get_etf_technical_indicators,
    get_future_index_data
]


if __name__ == "__main__":
    realtime_data = get_etf_realtime_data("510500")
    tech_data = get_etf_technical_indicators("510500", freq="D", count=10)
    future_data = get_future_index_data("IC")

    output = {
        "get_etf_realtime_data": realtime_data,
        "get_etf_technical_indicators": tech_data,
        "get_future_index_data": future_data
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
