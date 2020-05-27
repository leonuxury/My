import tushare as ts
import pandas as pd
import sqlite3
import time
from smtplib import SMTP_SSL
from email.mime.text import MIMEText

ts.set_token('397a9a945c62a0b0526178fe7657dd32fc45a7b02b133ab6ce4e3e08')
pro = ts.pro_api()


class Stock:
    def __init__(self, ts_code, name, symbol='', cost=0.0, amount=0):
        # 如果未提供symbol，那么从ts_code获取。
        self.ts_code = ts_code
        self.name = name
        self.symbol = symbol if symbol else ts_code.split('.')[0]
        self.cost = cost
        self.amount = amount

    def __str__(self):
        return f'ts_code: {self.ts_code}, name: {self.name}'

    def GetStockRealPrice(self):  # 在线获取实时价格。
        stock_real_price = 0
        try:
            stock_real_price = float(ts.get_realtime_quotes(self.symbol)['price'][0])
        except Exception as e:
            print(e)
        return stock_real_price

    def GetStockMaxMin(self, time_span, con):  # 获取一段时间内最高、最低值。
        # 从数据库读取，不涉及到网络超时。
        stock_history = pd.read_sql(f'''SELECT max(high), min(low) FROM 
                                    (select high, low from stock_daily 
                                    where ts_code = "{self.ts_code}" 
                                    limit {time_span})''', con)
        stock_max = stock_history.iloc[0, 0] if stock_history.iloc[0, 0] else 0
        stock_min = stock_history.iloc[0, 1] if stock_history.iloc[0, 1] else 0

        return stock_max, stock_min

    def UpdateData(self, con):
        stock_daily = pro.daily(ts_code=self.ts_code, start_date='20180101',
                                fields='ts_code, trade_date, high, low')
        stock_daily.to_sql('stock_daily', con,
                           if_exists='append', index=False)
        print(f'{self} - 历史记录已写入。')

    def UpdateDataAdjfactor(self, con):
        stock_daily = ts.pro_bar(ts_code=self.ts_code, adj='qfq',
                                 start_date='20180101')
        try:
            stock_daily.to_sql('stock_daily', con,
                               if_exists='append', index=False)
            print(f'{self} - 历史记录已写入。')
        except Exception as e:
            print(e)

    def IsValuable(self, time_span, con):
        # 该股票是否有价值，因为不能只关注便宜的股票，还要关注涨幅空间。
        is_valuable = False
        stock_max, stock_min = self.GetStockMaxMin(time_span, con)
        real_price = self.GetStockRealPrice()
        if (real_price != 0  # 为0时，获取实时价格失败。
                and real_price <= stock_min * 1.01  # %1以内。
                and (stock_max - real_price) > 3  # 有一定的涨幅空间。
                and not self.IsST()):  # 并且不是ST股票。
            is_valuable = True
            print(f'关注 {self} 当前：{real_price} 最高：{stock_max} 最低：{stock_min}')
        return is_valuable

    def IsST(self):
        return 'ST' in self.name

    def HowMuchProfit(self):
        real_price = self.GetStockRealPrice()
        profit = (real_price - self.cost) * self.amount  # 有可能赚，有可能赔。
        print(f'{self.name} 当前：{real_price} 成本：{self.cost} 数量：{self.amount} 盈利：{round(profit, 3)}。')
        return profit

    def SendEmail(self):
        with SMTP_SSL(host='smtp.hotmail.com') as smtp:
            smtp.login(user='li_jing_ok@hotmail.com', password='LJlj11!!')

            msg = MIMEText(f'请关注：{self.name} {self.ts_code}，当前处于盈利状态。', _charset="utf8")
            msg["Subject"] = f'请关注 {self.name}，当前处于盈利状态。'
            msg['From'] = 'li_jing_ok@hotmail.com'  # 发送者
            msg['To'] = '1005411336@qq.com'  # 接收者

            smtp.sendmail(from_addr="li_jing_ok@hotmail.com",
                          to_addrs=['1005411336@qq.com'],
                          msg=msg.as_string())


class Me:
    def __init__(self, name):
        self.con = sqlite3.connect('stock.db')
        self.name = name

    def __del__(self):
        self.con.close()

    def UpdateStockList(self):  # 更新股票列表，一般很少变化，不用更新太频繁。
        c = self.con.cursor()
        c.execute('DROP TABLE stock_list')  # 删除之前的表。
        c.close()  # 关闭游标。
        # 获取所有的股票列表。
        stock_list = pro.stock_basic(exchange='', list_status='L')
        stock_list.to_excel('stock_list.xlsx', index=False)  # excel方便看
        # 保存在数据库中。添加index列。
        stock_list.to_sql('stock_list', self.con, if_exists='replace',
                          index=False)

    def UpdateStockData(self):  # 更新股票历史交易记录。从20180101开始的。
        c = self.con.cursor()
        c.execute('DROP TABLE stock_daily')  # 删除之前的表。
        c.close()  # 关闭。

        stock_list = self.GetStockList()
        for stock in stock_list:  # 遍历
            if not stock.IsST():  # 不是ST的才更新。
                stock.UpdateDataAdjfactor(self.con)

    def GetStockList(self):
        tmp = pd.read_sql('select ts_code, symbol, name from stock_list',
                          self.con)
        stock_list = []
        for row in tmp.itertuples():  # 遍历
            ts_code = row[1]
            name = row[3]
            symbol = row[2]
            stock = Stock(ts_code, name, symbol)
            stock_list.append(stock)
        return stock_list

    def Select(self, time_span):  # 选择最近time_span内
        stock_list = self.GetStockList()
        for stock in stock_list:  # 遍历每一个股票，选择接近%3最低点的股票。
            if not stock.IsST():
                stock.IsValuable(time_span, self.con)

    @staticmethod
    def KeepEyesOn():  # 已购买股票。
        stocks = [Stock('000039.SZ', '中集集团', cost=7.34, amount=100),
                  # Stock('600717.SH', '天津港', cost=5.44, amount=100),
                  # Stock('603885.SH', '吉祥航空', cost=9.35, amount=100),
                  # Stock('601919.SH', '中远海控', cost=3.4, amount=100),
                  # Stock('600018.SH', '上港集团', cost=4.1, amount=100),
                  ]

        while True:
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f'--------开始：{t}---------')
            for stock in stocks:
                if stock.HowMuchProfit() - 5 > 1:  # 5元是税费。
                    print(f'--可以交易：{stock}')
                    try:  # 有可能邮件发送失败。
                        stock.SendEmail()
                    except Exception as e:
                        print(f'邮件发送失败：{e}。')
            stock.SendEmail()
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f'--------结束：{t}---------')
            time.sleep(60)  # 一分钟后再循环


TIME_SPAN = 30 * 12
lj = Me('李敬')
# lj.UpdateStockList()
# lj.UpdateStockData()
# lj.Select(TIME_SPAN)
Me.KeepEyesOn()
