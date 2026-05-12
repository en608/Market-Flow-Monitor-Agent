"""
ETF监控系统 - Agent 大脑层
基于 OpenAI API 实现智能分析 Agent
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Callable

from dotenv import load_dotenv
import openai

# 加载环境变量（指定 .env 文件路径）
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from tools import (
    get_etf_realtime_data,
    get_etf_technical_indicators,
    get_future_index_data
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TOOL_FUNCTIONS = {
    "get_etf_realtime_data": get_etf_realtime_data,
    "get_etf_technical_indicators": get_etf_technical_indicators,
    "get_future_index_data": get_future_index_data
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_etf_realtime_data",
            "description": "获取ETF实时行情数据，包括当前价格、涨跌幅、成交量、成交额等",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "ETF代码，如 '510500'（中证500ETF）",
                        "default": "510500"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_etf_technical_indicators",
            "description": "获取ETF技术指标数据，包括K线、MACD、均线等",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "ETF代码，如 '510500'（中证500ETF）",
                        "default": "510500"
                    },
                    "freq": {
                        "type": "string",
                        "description": "K线周期，如 'D'（日线）、'W'（周线）、'M'（月线）",
                        "default": "D"
                    },
                    "count": {
                        "type": "integer",
                        "description": "获取数据条数",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_future_index_data",
            "description": "获取股指期货数据（目前新浪API暂不支持，可选akshare）",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "期货合约代码：'IC'（中证500）、'IF'（沪深300）、'IH'（上证50）",
                        "default": "IC"
                    }
                },
                "required": []
            }
        }
    }
]


SYSTEM_PROMPTS = {
    "08:00 盘前展望": """你是一位资深的量化金融分析师，专注于**大盘资金流向分析**和ETF投资策略。

当前时间：08:00 盘前展望

**核心任务**：基于前一日市场数据，分析大盘资金流向趋势，为今日操作提供参考。

请执行以下分析：
- 分析北向资金、主力资金的整体动向
- 调用 `get_etf_technical_indicators` 分析中证500ETF前一日技术面（MACD、成交量等）
- 评估市场情绪指标
- 结合股指期货基差情况（如IC合约）判断市场预期
- 预测今日大盘资金流向趋势

请生成一份专业的 Markdown 格式分析报告，包含：
1. **【08:00 盘前资金流向展望】** - 标题
2. **市场概览** - 最新指数点位与涨跌幅
3. **资金流向分析** - 北向资金、主力资金动向解读
4. **ETF技术面** - 中证500ETF技术指标分析
5. **市场情绪** - 综合情绪指标评估
6. **今日展望** - 资金流向预测与操作建议

请确保报告专业、严谨，数据驱动，逻辑清晰。""",

    "14:30 尾盘大盘资金异动": """你是一位资深的量化金融分析师，专注于**大盘资金流向分析**和ETF投资策略。

当前时间：14:30 尾盘监控

**核心任务**：实时监控尾盘资金异动，识别主力资金动向和潜在的市场机会或风险。

请执行以下分析：
- 调用 `get_etf_realtime_data` 获取 ETF 实时行情数据
- 重点分析尾盘主力资金流向（净流入/净流出）
- 关注北向资金尾盘动向
- 识别是否出现异常资金异动（大单流入/流出）
- 判断资金流向对市场的影响

请生成一份专业的 Markdown 格式分析报告，包含：
1. **【14:30 尾盘资金异动监控】** - 标题
2. **实时行情** - 当前ETF价格、涨跌幅、成交量
3. **主力资金流向** - 尾盘资金净流入/流出分析
4. **北向资金动态** - 外资动向解读
5. **异动识别** - 是否出现异常资金流动
6. **市场影响** - 资金动向对市场的潜在影响
7. **操作建议** - 基于资金流向的操作建议

请确保报告专业、严谨，数据驱动，逻辑清晰。""",

    "18:00 全天大盘资金流向复盘": """你是一位资深的量化金融分析师，专注于**大盘资金流向分析**和ETF投资策略。

当前时间：18:00 全天复盘

**核心任务**：全面复盘今日大盘资金流向，分析北向资金、主力资金的整体动态，评估市场情绪。

请执行以下分析：
- 调用 `get_etf_technical_indicators` 分析日线技术指标
- 调用 `get_etf_realtime_data` 获取最新行情
- 分析全天北向资金净流入/流出情况
- 评估主力资金动向和板块资金流向
- 判断市场情绪变化
- 总结今日资金流向特点并给出明日展望

请生成一份专业的 Markdown 格式分析报告，包含：
1. **【18:00 全天资金流向复盘】** - 标题
2. **今日行情回顾** - 大盘走势与关键点位
3. **北向资金分析** - 全天外资动向
4. **主力资金流向** - 板块资金分布与热点
5. **ETF表现** - 中证500ETF技术面与资金关系
6. **市场情绪评估** - 综合情绪指标分析
7. **明日展望** - 资金流向预测与策略建议

请确保报告专业、严谨，数据驱动，逻辑清晰。""",

    "手动测试运行": """你是一位资深的量化金融分析师，专注于**大盘资金流向分析**和ETF投资策略。

当前时间：手动测试运行

**核心任务**：执行完整的ETF分析流程，验证系统功能正常。

请执行以下分析：
- 调用相关工具获取ETF数据
- 分析资金流向和技术指标
- 生成测试报告验证系统功能

请生成一份专业的 Markdown 格式分析报告，包含：
1. **【测试运行报告】** - 标题
2. **系统状态** - 各模块运行状态
3. **数据获取** - 工具调用结果
4. **分析结果** - ETF分析摘要
5. **系统验证** - 功能完整性检查

请确保报告专业、严谨，数据驱动，逻辑清晰。"""
}


class EtfAnalysisAgent:
    """ETF分析Agent类"""

    def __init__(self):
        """初始化Agent"""
        logger.info("正在初始化ETF分析Agent...")

        # 从环境变量读取配置
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE")
        model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")

        if not api_key:
            raise ValueError("OPENAI_API_KEY 未配置")
        
        if not base_url:
            raise ValueError("OPENAI_API_BASE 未配置")

        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60,
            max_retries=2
        )

        self.model = model_name
        self.temperature = 0.2

        logger.info(f"LLM初始化完成 (model={self.model}, temperature={self.temperature})")

    def _call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具函数"""
        logger.info(f"正在调用工具: {tool_name}, 参数: {tool_args}")

        try:
            if tool_name not in TOOL_FUNCTIONS:
                return {"error": f"未找到工具: {tool_name}"}

            func = TOOL_FUNCTIONS[tool_name]
            result = func(**tool_args)
            logger.info(f"工具 {tool_name} 返回: {str(result)[:200]}...")
            return result

        except Exception as e:
            logger.error(f"工具调用失败: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量执行工具调用"""
        results = []
        for call in tool_calls:
            tool_name = call['function']['name']
            tool_args = json.loads(call['function']['arguments']) if isinstance(call['function']['arguments'], str) else call['function']['arguments']
            result = self._call_tool(tool_name, tool_args)
            results.append({
                "tool_call_id": call['id'],
                "tool_name": tool_name,
                "result": result
            })
        return results

    def _build_messages(self, system_prompt: str, user_input: str, tool_results: List[Dict[str, Any]] = None, assistant_message=None) -> List[Dict[str, Any]]:
        """构建消息列表"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        if assistant_message:
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in (assistant_message.tool_calls or [])
                ]
            })

        if tool_results:
            for res in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": res['tool_call_id'],
                    "content": json.dumps(res['result'], ensure_ascii=False, indent=2)
                })

        return messages

    def run_analysis(self, run_time: str) -> str:
        """
        运行ETF分析（带工具调用）

        Args:
            run_time: 盘口时间，格式如 "早盘 08:00"、"尾盘 14:30"、"收盘 18:00"

        Returns:
            Markdown格式的分析报告
        """
        logger.info(f"=" * 60)
        logger.info(f"开始ETF分析，盘口时间: {run_time}")
        logger.info(f"=" * 60)

        system_prompt = SYSTEM_PROMPTS.get(run_time, SYSTEM_PROMPTS["手动测试运行"])
        user_input = f"请帮我执行{run_time}的ETF分析，代码为510500（中证500ETF南方）"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"第 {iteration} 轮对话...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                tools=TOOL_DEFINITIONS if iteration == 1 else None,
                tool_choice="auto" if iteration == 1 else None
            )

            assistant_message = response.choices[0].message
            logger.info(f"助手响应: {assistant_message.content[:200] if assistant_message.content else 'No content'}")

            if not assistant_message.tool_calls:
                logger.info("Agent分析完成，无更多工具调用")
                return assistant_message.content or "分析完成，但未返回报告内容"

            tool_calls = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in assistant_message.tool_calls
            ]

            logger.info(f"需要调用 {len(tool_calls)} 个工具")
            tool_results = self._execute_tools(tool_calls)

            for res in tool_results:
                logger.info(f"工具 {res['tool_name']} 执行完成")

            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })

            for res in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": res['tool_call_id'],
                    "content": json.dumps(res['result'], ensure_ascii=False, indent=2)
                })

        return "分析已达到最大迭代次数，请检查工具调用是否正常"


def run_analysis(run_time: str) -> str:
    """
    主函数：运行ETF分析

    Args:
        run_time: 盘口时间，格式如 "早盘 08:00"、"尾盘 14:30"、"收盘 18:00"

    Returns:
        Markdown格式的分析报告
    """
    agent = EtfAnalysisAgent()
    return agent.run_analysis(run_time)


if __name__ == "__main__":
    print("=" * 60)
    print("ETF监控系统 - Agent测试")
    print("=" * 60)

    agent = EtfAnalysisAgent()

    test_times = ["早盘 08:00", "尾盘 14:30", "收盘 18:00"]

    for time_slot in test_times:
        print(f"\n{'=' * 60}")
        print(f"测试盘口时间: {time_slot}")
        print(f"{'=' * 60}\n")

        report = agent.run_analysis(time_slot)
        print(report)
        print()
