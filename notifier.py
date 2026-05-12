"""
ETF监控系统 - 微信推送模块
基于 WxPusher 实现消息推送功能
"""

import logging
import json
import os
from typing import Optional

import requests
from dotenv import load_dotenv

# 先配置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 加载环境变量（指定 .env 文件路径）
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

WXPUSHER_API_URL = "https://wxpusher.zjiecode.com/api/send/message"


def send_wechat_notification(content: str, title: str = "ETF监控通知") -> bool:
    """
    发送微信通知消息

    Args:
        content: 消息内容（支持 Markdown 格式）
        title: 消息标题，默认为"ETF监控通知"

    Returns:
        bool: 推送是否成功
    """
    try:
        # 从环境变量获取配置
        app_token = os.getenv("WXPUSHER_APP_TOKEN")
        uids = os.getenv("WXPUSHER_UID")

        if not app_token or not uids:
            logger.error("WXPUSHER_APP_TOKEN 或 WXPUSHER_UID 未配置")
            return False

        # 构建请求参数
        payload = {
            "appToken": app_token,
            "content": content,
            "summary": title,
            "contentType": 3,  # 3 = Markdown 格式
            "uids": [uids]
        }

        logger.info(f"准备发送微信通知，标题: {title}")

        # 发送请求
        response = requests.post(
            WXPUSHER_API_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        if result.get("code") == 1000:
            # 检查每个用户的发送状态
            success_count = 0
            fail_count = 0
            fail_reasons = []
            
            if isinstance(result.get("data"), list):
                for item in result["data"]:
                    if item.get("code") == 1000:
                        success_count += 1
                    else:
                        fail_count += 1
                        fail_reasons.append(item.get("status", "未知错误"))
            
            if success_count > 0:
                logger.info(f"微信推送发送成功，成功 {success_count} 人，失败 {fail_count} 人")
                return True
            else:
                logger.error(f"微信推送发送失败: {'; '.join(fail_reasons)}")
                return False
        else:
            logger.error(f"微信推送发送失败: {result.get('msg', '未知错误')}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"发送微信通知时发生网络错误: {str(e)}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"发送微信通知时发生未知错误: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    """模块测试：发送连接成功消息"""
    print("=" * 60)
    print("微信推送模块测试")
    print("=" * 60)

    test_content = """## 中证500ETF 监控系统

**系统状态**: 连接成功

**服务信息**:
- 数据源: 新浪财经API
- Agent模型: gpt-4o-mini
- 监控时段: 08:00 / 14:30 / 18:00

**今日提醒**: 系统已准备就绪，将按时推送分析报告。
"""

    test_title = "中证500ETF 监控系统连接成功"

    print(f"测试标题: {test_title}")
    print(f"测试内容长度: {len(test_content)} 字符")
    print()

    success = send_wechat_notification(test_content, test_title)

    if success:
        print("微信通知发送成功！")
    else:
        print("微信通知发送失败！")
        print("\n常见问题排查:")
        print("1. 请确保已关注 'WxPusher' 公众号")
        print("2. 请检查 .env 文件中的 UID 是否正确")
        print("3. 如果提示'未订阅应用'，请访问以下链接订阅:")
        print("   https://wxpusher.zjiecode.com/demo/scan?appToken=YOUR_APP_TOKEN")
        print("   (请在 .env 文件中查看 APP_TOKEN)")
        print("4. 如果还是收不到消息，请检查 WxPusher 后台的消息状态")
