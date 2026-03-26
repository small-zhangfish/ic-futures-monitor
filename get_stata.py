import akshare as ak
import pandas as pd
import datetime
import calendar
import time
import json
import os
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta

# ===================== 缓存（永不限流） =====================
USE_CACHE = True
CACHE_FILE = "futures_cache.json"
cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# ===================== 合约计算 =====================
def get_ic_contracts(trading_date):
    year = trading_date.year
    month = trading_date.month
    c = calendar.monthcalendar(year, month)
    fridays = [week[4] for week in c if week[4] != 0]
    delivery_day = datetime.date(year, month, fridays[2])

    if trading_date > delivery_day:
        current_date = trading_date + relativedelta(months=1)
    else:
        current_date = trading_date

    cy, cm = current_date.year, current_date.month
    def code(y, m): return f"IC{str(y)[-2:]}{m:02d}"

    current = code(cy, cm)
    next_m = code(cy, cm + 1) if cm < 12 else code(cy + 1, 1)
    q = (cm + 1) // 3 + 1
    q_month = q * 3
    current_q = code(cy, q_month)
    next_q = code(cy, q_month + 3)
    return current, next_m, current_q, next_q

# ===================== 历史价格（带缓存，不限流） =====================
def get_hist_close(contract, trade_date):
    key = f"{contract}_{trade_date}"
    if key in cache:
        return cache[key]
    try:
        time.sleep(1.5)
        df = ak.futures_zh_daily_sina(symbol=contract)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        target = df[df["date"] == trade_date]
        if target.empty:
            return None
        price = float(target["close"].iloc[0])
        cache[key] = price
        save_cache()
        return price
    except:
        return None

# ===================== 单日计算 =====================
def calculate_day(trading_date):
    current, next_m, current_q, next_q = get_ic_contracts(trading_date)
    c_close = get_hist_close(current, trading_date)
    nm_close = get_hist_close(next_m, trading_date)
    cq_close = get_hist_close(current_q, trading_date)
    nq_close = get_hist_close(next_q, trading_date)

    if None in [c_close, nm_close, cq_close, cq_close, nq_close]:
        print(f"❌ {trading_date} 无数据")
        return None

    diff_nm = 1
    curr_m = int(current[-2:])
    cq_m = int(current_q[-2:])
    nq_m = int(next_q[-2:])
    diff_cq = (cq_m - curr_m) % 12
    diff_nq = (nq_m - curr_m) % 12

    basis1 = round((c_close - nm_close) / diff_nm, 2)
    basis2 = round((c_close - cq_close) / diff_cq, 2)
    basis3 = round((c_close - nq_close) / diff_nq, 2)

    print(f"✅ {trading_date} | {current} | 基差1:{basis1} 基差2:{basis2} 基差3:{basis3}")

    return {
        "日期": trading_date.strftime("%Y-%m-%d"),
        "当月合约": current,
        "当月-下月/月差": basis1,
        "当月-当季/月差": basis2,
        "当月-下季/月差": basis3,
    }

# ===================== 绘图函数（你要的图） =====================
def plot_basis_trend(df):
    # 设置字体以确保中文显示正常
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun", "DejaVu Sans", "Arial Unicode MS", "Helvetica", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    plt.figure(figsize=(12, 5))
    plt.plot(df["日期"], df["当月-下月/月差"], marker="o", label="当月-下月/月差", color="#FF4B4B")
    plt.plot(df["日期"], df["当月-当季/月差"], marker="s", label="当月-当季/月差", color="#457B9D")
    plt.plot(df["日期"], df["当月-下季/月差"], marker="^", label="当月-下季/月差", color="#1D3557")

    plt.title("IC期货 基差/月份 趋势图", fontsize=14)
    plt.xlabel("日期")
    plt.ylabel("基差 / 月份")
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("基差趋势图.png", dpi=300)
    plt.close()
    print("✅ 趋势图已保存：基差趋势图.png")

# ===================== 生成HTML页面（用于GitHub Pages） =====================
def generate_html(df):
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IC期货基差监控</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .last-updated {{
            text-align: right;
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: center;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .chart-container {{
            text-align: center;
            margin: 30px 0;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .stats {{ 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #ddd;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>IC期货基差监控</h1>
        <div class="last-updated">最后更新：{(datetime.datetime.now() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')}</div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{df['当月-下月/月差'].iloc[-1]}</div>
                <div class="stat-label">当月-下月/月差</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{df['当月-当季/月差'].iloc[-1]}</div>
                <div class="stat-label">当月-当季/月差</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{df['当月-下季/月差'].iloc[-1]}</div>
                <div class="stat-label">当月-下季/月差</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>基差趋势图</h2>
            <img src="基差趋势图.png" alt="基差趋势图">
        </div>
        
        <h2>最近一周数据</h2>
        <table>
            <tr>
                <th>日期</th>
                <th>当月合约</th>
                <th>当月-下月/月差</th>
                <th>当月-当季/月差</th>
                <th>当月-下季/月差</th>
            </tr>
"""
    
    # 添加最近一周数据
    recent_df = df.tail(7)
    for _, row in recent_df.iterrows():
        html_content += f"""
            <tr>
                <td>{row['日期']}</td>
                <td>{row['当月合约']}</td>
                <td>{row['当月-下月/月差']}</td>
                <td>{row['当月-当季/月差']}</td>
                <td>{row['当月-下季/月差']}</td>
            </tr>
"""
    
    html_content += f"""
        </table>
    </div>
</body>
</html>
"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ HTML页面已生成：index.html")

# ===================== 主抓取（近3个月） =====================
def crawl_and_save():
    print("=" * 70)
    print(f"📊 IC期货基差（不限流+自动绘图）| {datetime.datetime.now()}")

    today = datetime.date.today()
    date_list = [today - datetime.timedelta(days=i) for i in range(89, -1, -1)]

    result = []
    for d in date_list:
        if d.weekday() >= 5:
            print(f"🌤 跳过周末：{d}")
            continue
        year = d.year
        month = d.month
        c = calendar.monthcalendar(year, month)
        fridays = [week[4] for week in c if week[4] != 0]
        delivery_day = datetime.date(year, month, fridays[2])
        if d == delivery_day:
            print(f"⏳ 跳过交割日：{d}")
            continue

        data = calculate_day(d)
        if data:
            result.append(data)

    if not result:
        print("❌ 无有效数据")
        return

    df = pd.DataFrame(result)
    df.to_excel("IC期货基差数据_最终版.xlsx", index=False)
    print(f"\n🎉 Excel 保存完成！")

    # ===================== 自动画图 =====================
    plot_basis_trend(df)
    
    # ===================== 生成HTML页面 =====================
    generate_html(df)

    print("=" * 70)

# ===================== 启动 =====================
if __name__ == "__main__":
    crawl_and_save()