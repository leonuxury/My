from smtplib import SMTP_SSL
from email.mime.text import MIMEText

SMTP_HOST = 'smtp.gmail.com'
USER = 'leonuxury@gmail.com'
PASSWORD = 'LJlj11!!'
TO = '1005411336@qq.com'
with SMTP_SSL(host=SMTP_HOST) as smtp:
    smtp.login(user=USER, password=PASSWORD)

    msg = MIMEText(f'请关注：，当前处于盈利状态。', _charset="utf8")
    msg["Subject"] = f'请关注 ，当前处于盈利状态。'
    msg['From'] = USER  # 发送者
    msg['To'] = TO  # 接收者

    smtp.sendmail(from_addr=USER,
                  to_addrs=[TO],
                  msg=msg.as_string())
