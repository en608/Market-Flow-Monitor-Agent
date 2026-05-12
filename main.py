"""
ETF监控系统 - 主程序入口（GitHub Actions 适配版）
单次运行脚本，根据当前时间智能分发任务
"""

import logging
import os
from datetime import datetime, timezone, timedelta

# 导入自定义模块
from agent import run_analysis
from notifier import send_wechat_notification

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("etf_monitor")


def get_run_time_name() -> str:
    """
    根据当前北京时间判断应该执行哪个时段的分析任务
    
    Returns:
        run_time_name: 运行时段名称
    """
    # 获取当前北京时间 (UTC+8)
    now = datetime.now(timezone(timedelta(hours=8)))
    hour = now.hour
    minute = now.minute
    
    logger.info(f"当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 判断时段（±15分钟范围内认为是该时段）
    if (hour == 8 and minute >= 0 and minute <= 30) or (hour == 7 and minute >= 45):
        return "08:00 盘前展望"
    elif (hour == 14 and minute >= 15 and minute <= 45):
        return "14:30 尾盘大盘资金异动"
    elif (hour == 18 and minute >= 0 and minute <= 30) or (hour == 17 and minute >= 45):
        return "18:00 全天大盘资金流向复盘"
    else:
        return "手动测试运行"


def execute_analysis(run_time_name: str) -> None:
    """
    执行分析任务并推送微信通知
    
    Args:
        run_time_name: 运行时段名称
    """
    logger.info(f"{'='*60}")
    logger.info(f"开始执行任务: {run_time_name}")
    logger.info(f"{'='*60}")

    try:
        # 调用 Agent 分析（重点关注大盘资金流向）
        logger.info("正在调用分析引擎...")
        report = run_analysis(run_time_name)
        
        if not report:
            logger.error("分析引擎返回空结果")
            return

        # 生成标题
        title = f"【{run_time_name}】中证500ETF分析报告"
        
        # 截取报告前200字符作为预览
        report_preview = report[:200] + "..." if len(report) > 200 else report
        logger.info(f"分析报告生成成功，内容预览:\n{report_preview}")

        # 发送微信通知
        logger.info("正在发送微信通知...")
        success = send_wechat_notification(report, title)
        
        if success:
            logger.info("微信通知发送成功")
        else:
            logger.warning("微信通知发送失败")

    except Exception as e:
        logger.error(f"任务执行失败: {str(e)}", exc_info=True)
        # 尝试发送错误通知
        try:
            error_msg = f"## 任务执行失败\n\n**时间**: {run_time_name}\n**错误**: {str(e)[:200]}"
            send_wechat_notification(error_msg, "【告警】ETF监控任务失败")
        except Exception as notify_e:
            logger.error(f"发送错误通知也失败: {str(notify_e)}")

    logger.info(f"{'='*60}")
    logger.info(f"任务执行完成: {run_time_name}")
    logger.info(f"{'='*60}")


def print_welcome():
    """打印启动欢迎语"""
    welcome = """
╔══════════════════════════════════════════════════════════════════╗
║                    ETF监控系统 v1.0                             ║
║            Agent-based ETF Monitoring System (GitHub Actions)   ║
╚══════════════════════════════════════════════════════════════════╝
║  数据源:     新浪财经API                                        ║
║  分析引擎:   GPT-4o-mini                                        ║
║  推送方式:   WxPusher                                          ║
║  分析重心:   大盘资金流向分析                                    ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(welcome)


def main():
    """主程序入口"""
    print_welcome()
    
    # 获取当前时段
    run_time_name = get_run_time_name()
    print(f"\n【当前时段】: {run_time_name}")
    print("-" * 50)
    
    # 执行分析任务
    execute_analysis(run_time_name)


if __name__ == "__main__":
    main()
