import os
import random
import time
import dotenv
from database import insert_email_code, check_email_code_limit
import logging
import smtplib
from email.mime.text import MIMEText
from email.header import Header

dotenv.load_dotenv()
logger = logging.getLogger(__name__)


def get_random_6():
    return ''.join(random.choice('0123456789') for _ in range(6))


def send_email(to):
    """发送邮件验证码 - 修复 QQ 邮箱 550 错误"""

    # 校验环境变量
    account = os.getenv('EMAIL_ACCOUNT')
    password = os.getenv('EMAIL_PASSWORD')
    if not account or not password:
        logger.error("未配置邮箱账号或授权码")
        return {"code": 500, "message": "系统邮件服务未配置"}

    # 检查发送频率限制
    if check_email_code_limit(to):
        return {"code": 429, "message": "发送过于频繁，请1分钟后再试"}

    code = get_random_6()
    expire_time = int(time.time()) + 60 * 10  # 10分钟有效

    # 存储验证码
    insert_result = insert_email_code(to, code, expire_time)
    if insert_result != "success":
        return {"code": 500, "message": "验证码存储失败"}

    # 【修复】构建邮件内容 - 简化，避免被识别为垃圾邮件
    body = f"您的验证码是：{code}，10分钟内有效。"
    msg = MIMEText(body, 'plain', 'utf-8')

    # 【修复】直接用字符串拼接，不要 formataddr + Header 编码！
    msg['From'] = f"SmartFarm <{account}>"
    msg['To'] = to  # 收件人直接写地址
    msg['Subject'] = Header("登录验证码", "utf-8")  # 主题可以编码

    try:
        server = smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=10)
        server.login(account, password)
        server.sendmail(account, [to], msg.as_string())
        server.quit()

        logger.info(f"验证码发送成功 | 目标: {to} | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return {"code": 200, "message": "验证码已发送"}

    except smtplib.SMTPException as e:
        error_msg = str(e)
        logger.error(f"邮件发送失败 | 目标: {to} | 错误: {error_msg}")

        # 判断是否为 QQ 邮箱 550 错误
        if "550" in error_msg:
            return {"code": 500, "message": "邮件被拦截，请检查邮箱垃圾箱或联系管理员"}
        return {"code": 500, "message": "邮件发送失败，请稍后重试"}
    except Exception as e:
        logger.error(f"邮件发送异常 | 目标: {to} | 错误: {str(e)}")
        return {"code": 500, "message": "邮件服务繁忙，请稍后再试"}