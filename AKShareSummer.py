import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import os
import numpy as np
import logging
import json
import pytz
import google.generativeai as genai
from google.generativeai import types
import traceback
import akshare as ak

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 配置参数
# Use environment variable for API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATA_DIR = "国际市场数据"  # 数据保存目录

# 创建数据目录
os.makedirs(DATA_DIR, exist_ok=True)

# 配置 Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logging.warning("警告: 未找到 GEMINI_API_KEY 环境变量。将无法生成 AI 分析报告。")

# 获取中国时间
def get_china_time():
    """获取中国时间"""
    china_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(china_tz)

# 格式化日期
def format_date(dt):
    """格式化日期为YYYY-MM-DD"""
    return dt.strftime('%Y-%m-%d')

# 获取中国国债收益率数据
def get_china_bond_yield():
    """获取中国10年期国债收益率数据"""
    try:
        logging.info("正在获取中国国债收益率数据...")
        # 使用AKShare获取中国国债收益率，指定起始日期为一年前
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        bond_data = ak.bond_zh_us_rate(start_date=start_date)
        
        # 打印获取到的数据结构
        print("获取到的国债数据结构:")
        print(bond_data.columns)
        print(bond_data.head())
        
        if bond_data.empty:
            logging.warning("未获取到国债收益率数据")
            return create_default_bond_data()
        
        # 检查是否有中国国债收益率10年列
        if '中国国债收益率10年' not in bond_data.columns:
            logging.warning("未找到'中国国债收益率10年'列，检查可用列")
            print("可用列:", bond_data.columns.tolist())
            return create_default_bond_data()
        
        # 创建新的DataFrame，只保留日期和中国国债收益率10年
        china_10y = pd.DataFrame({
            '日期': bond_data['日期'],
            '数值': bond_data['中国国债收益率10年']
        })
        
        # 删除NaN值
        china_10y = china_10y.dropna(subset=['数值'])
        
        if china_10y.empty:
            logging.warning("过滤NaN后数据为空")
            return create_default_bond_data()
            
        # 重命名列并设置索引
        china_10y.rename(columns={'日期': 'date', '数值': 'China_10Y_Treasury_Yield'}, inplace=True)
        china_10y['date'] = pd.to_datetime(china_10y['date'])
        china_10y.set_index('date', inplace=True)
        
        # 打印处理后的数据
        print("处理后的中国国债收益率数据:")
        print(china_10y.head())
        print(f"数据行数: {len(china_10y)}")
        
        logging.info("成功获取中国国债收益率数据")
        return china_10y
    except Exception as e:
        logging.error(f"获取中国国债收益率数据失败: {str(e)}")
        logging.error(traceback.format_exc())
        return create_default_bond_data()

def create_default_bond_data():
    """创建默认的中国国债收益率数据"""
    logging.info("创建默认的中国国债收益率数据")
    today = datetime.now()
    # 创建过去一年的每日数据
    dates = pd.date_range(end=today, periods=365, freq='D')
    china_10y = pd.DataFrame({
        'date': dates,
        'China_10Y_Treasury_Yield': [2.5] * len(dates)  # 使用2.5%作为默认值
    })
    china_10y.set_index('date', inplace=True)
    return china_10y

def download_gold_training_data(years=1, output_filename="gold_training_data_macro_enhanced.csv"):
    """
    Downloads a comprehensive financial dataset centered around gold, enhanced with key
    macroeconomic indicators, more commodities, and Chinese A-Share market data from Yahoo Finance.
    It then cleans the data, calculates percentage changes, computes the basis, and saves it to a CSV file.

    Args:
        years (int): The number of years of historical data to download.
        output_filename (str): The filename for the output CSV.
    """
    print("Executing financial data download script (Macro, Commodity & A-Shares Enhanced)...")

    # --- 1. Define Tickers to Download ---
    # This list uses ETFs as proxies for key macro indicators for more reliable data.
    tickers_to_download = {
        # --- Core Gold Assets ---
        'GC=F': 'GOLD_spot_price',         # 黄金现货价格 (通过近月期货代理)
        'MGC=F': 'GOLD_near_month_future', # 黄金近月期货 (微型合约，连续性好)

        # --- Other Precious & Industrial Metals ---
        'SI=F': 'SILVER_future',           # 白银期货
        'PL=F': 'PLATINUM_future',         # 铂金期货
        'HG=F': 'COPPER_future',           # 铜期货
        
        # --- NEW: Added More Industrial Metals & Materials (新增更多工业金属与原料) ---
        'ALI=F': 'ALUMINUM_future',        # 铝期货

        # --- Agricultural & Energy Commodity Futures ---
        'CL=F': 'OIL_price',               # 原油期货
        'NG=F': 'NATURAL_GAS_future',      # 天然气期货
        'ZC=F': 'CORN_future',             # 玉米期货
        'ZS=F': 'SOYBEANS_future',         # 大豆期货
        'ZW=F': 'WHEAT_future',            # 小麦期货
        'LE=F': 'LIVE_CATTLE_future',      # 活牛期货
        'HE=F': 'LEAN_HOGS_future',        # 瘦肉猪期货

        # --- Cryptocurrencies ---
        'BTC-USD': 'BTC_price',            # 比特币价格
        'ETH-USD': 'ETH_price',            # 以太币价格

        # --- US Market Sentiment & Volatility ---
        '^GSPC': 'SP500_close',            # 标普500指数
        '^IXIC': 'NASDAQ_close',           # 纳斯达克综合指数
        '^VIX': 'VIX_close',               # 波动率指数 (恐慌指数)

        # --- Chinese A-Share Market Indices ---
        '000001.SS': 'Shanghai_Composite_Index', # 上证综合指数
        '399001.SZ': 'Shenzhen_Component_Index', # 深证成份股指数
        '000300.SS': 'CSI_300_Index',            # 沪深300指数

        # --- Key Global Macro Indicators ---
        'DX-Y.NYB': 'US_Dollar_Index',         # 美元指数 (DXY)
        'CNY=X': 'USD_CNY_exchange_rate',  # 新增: 美元兑人民币汇率
        '^TNX': 'US_10Y_Treasury_Yield',   # 美国10年期国债收益率
        'TLT': 'Long_Term_Treasury_ETF',   # 20+年期美国国债ETF (代表长期利率和避险情绪)
        'HYG': 'High_Yield_Bond_ETF',      # 高收益公司债券ETF (代表市场风险偏好)
        'DBC': 'Commodity_Index_ETF',      # 综合商品指数ETF (代表通胀预期)
    }

    # --- 2. Set Date Range ---
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    print(f"Data download period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # --- 3. Execute Download ---
    print("\nDownloading data from Yahoo Finance, please wait...")
    try:
        full_data = yf.download(
            tickers=list(tickers_to_download.keys()),
            start=start_date,
            end=end_date,
            interval="1d",
            progress=True,
            threads=True
        )

        if full_data.empty:
            print("Error: No data was downloaded. Please check your network connection or ticker symbols.")
            return None

        # Use the 'Close' column for pricing data.
        data = full_data['Close']
        print("Data download successful!")

    except Exception as e:
        print(f"An error occurred during download: {e}")
        return None

    # --- 4. Data Cleaning and Processing ---
    print("\nPerforming data cleaning and processing...")
    main_df = data.rename(columns=tickers_to_download)
    main_df.sort_index(inplace=True)

    initial_cols = set(main_df.columns)
    main_df.dropna(axis=1, how='all', inplace=True)
    removed_cols = initial_cols - set(main_df.columns)
    if removed_cols:
        print(f"Warning: The following columns were removed for being completely empty: {list(removed_cols)}")

    main_df.ffill(inplace=True)
    main_df.bfill(inplace=True)
    print("Data cleaning complete.")

    # --- 5. Calculate Derivative Indicators ---
    print("Calculating gold near-month basis...")
    if 'GOLD_spot_price' in main_df.columns and 'GOLD_near_month_future' in main_df.columns:
        main_df['GOLD_basis_spot_vs_near'] = main_df['GOLD_spot_price'] - main_df['GOLD_near_month_future']
        print("Successfully calculated 'GOLD_basis_spot_vs_near' column.")
    else:
        print("Warning: Could not calculate basis, as Gold Spot or Near-Month Future data is missing.")
    
    # --- 6. Add China 10Y Treasury Yield data ---
    print("Adding China 10Y Treasury Yield data...")
    china_bond_data = get_china_bond_yield()
    if china_bond_data is not None and not china_bond_data.empty:
        # 确保索引格式一致
        main_df.index = pd.to_datetime(main_df.index)
        china_bond_data.index = pd.to_datetime(china_bond_data.index)
        
        print(f"主数据框索引范围: {main_df.index.min()} 到 {main_df.index.max()}")
        print(f"中国国债数据索引范围: {china_bond_data.index.min()} 到 {china_bond_data.index.max()}")
        
        # 确保中国国债数据的索引在主数据框的索引范围内
        filtered_china_data = china_bond_data[
            (china_bond_data.index >= main_df.index.min()) & 
            (china_bond_data.index <= main_df.index.max())
        ]
        
        if filtered_china_data.empty:
            print("警告: 过滤后的中国国债数据为空，尝试重采样数据")
            # 重采样中国国债数据以匹配主数据框的日期
            resampled_china_data = china_bond_data.resample('D').ffill()
            filtered_china_data = resampled_china_data[
                (resampled_china_data.index >= main_df.index.min()) & 
                (resampled_china_data.index <= main_df.index.max())
            ]
        
        # 合并数据
        if not filtered_china_data.empty:
            print(f"合并前主数据框形状: {main_df.shape}")
            
            # 使用reindex确保索引完全匹配
            aligned_china_data = filtered_china_data.reindex(main_df.index, method='ffill')
            main_df['China_10Y_Treasury_Yield'] = aligned_china_data['China_10Y_Treasury_Yield']
            
            print(f"合并后主数据框形状: {main_df.shape}")
            print(f"China_10Y_Treasury_Yield 列非空值数量: {main_df['China_10Y_Treasury_Yield'].count()}")
            print(f"China_10Y_Treasury_Yield 示例数据: {main_df['China_10Y_Treasury_Yield'].head()}")
        else:
            print("警告: 无法找到匹配的中国国债收益率数据，使用默认值")
            main_df['China_10Y_Treasury_Yield'] = 2.5  # 使用默认值
        
        print("Successfully added China 10Y Treasury Yield data.")
    else:
        print("Warning: Could not add China 10Y Treasury Yield data, using default value.")
        main_df['China_10Y_Treasury_Yield'] = 2.5  # 使用默认值

    # 填充可能的NaN值
    main_df.fillna(method='ffill', inplace=True)
    main_df.fillna(method='bfill', inplace=True)
    
    # 确保China_10Y_Treasury_Yield列存在
    if 'China_10Y_Treasury_Yield' not in main_df.columns:
        print("警告: 在最终数据中未找到China_10Y_Treasury_Yield列，创建默认值")
        main_df['China_10Y_Treasury_Yield'] = 2.5  # 使用默认值
    
    print("Final data processing complete!")

    # --- 7. Save to File ---
    try:
        output_path = os.path.join(os.getcwd(), output_filename)
        main_df.to_csv(output_path)
        print(f"\nSuccess! The integrated data has been saved to: {output_path}")
        print(f"Data dimensions (Rows, Columns): {main_df.shape}")
        print("Data preview (last 5 rows):")
        print(main_df.tail())
        
        return main_df

    except Exception as e:
        print(f"\nAn error occurred while saving the file: {e}")
        return None

def prepare_market_data_for_analysis(df):
    """
    Prepares market data for AI analysis by extracting the most recent values.
    """
    if df is None or df.empty:
        return None
    
    latest_data = df.iloc[-1].to_dict()
    
    market_data = {
        "latest_date": df.index[-1].strftime('%Y-%m-%d'),
        "latest_values": {k: v for k, v in latest_data.items() if not k.endswith('_pct_change')}
    }
    
    return market_data

def generate_market_summary(market_data):
    """使用Gemini生成市场总结分析"""
    if not GEMINI_API_KEY:
        return "错误：未配置Gemini API KEY，无法生成市场分析。请设置 `GEMINI_API_KEY` 环境变量。"
    
    try:
        # Using a valid, current model name.
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        prompt = f"""
# 角色
你是一位顶尖的、专注于A股市场的宏观策略分析师。你的分析必须结合全球视野和本土洞察，最终为A股投资者提供清晰、可执行的观点。

# 任务
基于以下全球及中国本土的市场数据，撰写一份聚焦于A股的市场策略分析报告。

# 分析框架 (A股视角优先)
1.  **市场情绪诊断 (双重视角)**:
    * **A股本土情绪**: 中国市场指数表现如何？反映出当前A股场内投资者的恐慌或乐观程度？
    * **全球宏观情绪**: `VIX`和`美元指数(DXY)`表现如何？全球市场是"Risk-On"还是"Risk-Off"？
    * **情绪背离分析**: **关键点**！本土情绪与全球情绪是否存在背离？例如，若全球恐慌但A股平稳，意味着什么？若全球乐观但A股低迷，又是什么原因？这种背离对A股的短期走势有何指示意义？

2.  **核心市场表现与归因**:
    * **A股核心指数 (`上证指数`, `深证成指`)**: 点评其表现，核心驱动力是来自政策面、资金面还是基本面？
    * **美股与港股 (`纳斯达克`, `标普500`)**: 它们对A股的科技股和中概股有何映射和传导影响？

3.  **关键要素分析**:
    * **人民币汇率 (`美元/人民币`)**: 汇率水平对北向资金流和国内流动性预期有何影响？
    * **关键大宗商品 (`原油`, `铜`)**: 它们的价格水平反映了怎样的全球和中国经济复苏预期？对A股相关板块（如资源、化工）有何影响？
    * **中美利差 (`中美10年期国债收益率`)**: 利差水平如何影响A股的估值逻辑和外资流向？

4.  **核心结论与策略展望**:
    * **一句话总结**: 当前市场环境对A股投资者是"机会大于风险"还是"风险大于机会"？
    * **短期展望**: 对未来1-3个月A股市场的核心走势给出预判。
    * **关注方向**: 简要提示短期内值得关注的板块或逻辑。

# 数据
```json
{json.dumps(market_data, ensure_ascii=False, indent=2)}
```

# 输出要求
- **A股为本**: 所有分析最终都要落回到对A股市场的影响上。
- **突出背离**: 重点分析本土情绪与全球情绪的差异。
- **专业精炼**: 使用专业术语，直击要点。
- **结论明确**: 在报告结尾给出清晰的、有倾向性的观点。
- **总字数控制在1000字以内。**
- **输出格式**: Markdown格式，使用适当的标题层级和列表。
"""

 
        
        logging.info("正在使用Gemini AI生成市场分析...")
        response = model.generate_content(
            prompt,
        )
        
        if response and hasattr(response, 'text'):
            logging.info("成功生成市场分析")
            return response.text
        else:
            logging.error("生成分析失败: 响应格式异常")
            logging.debug(f"Full API response: {response}")
            return "生成分析失败: 响应格式异常"
    
    except Exception as e:
        logging.error(f"生成分析失败: {str(e)}")
        logging.error(traceback.format_exc())
        return f"生成分析失败: {str(e)}"

def save_market_analysis(analysis_text, df):
    """保存市场分析到MD文件，并附上最近一个月的数据（按时间降序）。"""
    try:
        today = get_china_time().strftime('%Y-%m-%d')
        filename = f"market_analysis_{today}.md"
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # 写入AI生成的分析
            f.write(analysis_text)
            f.write("\n\n---\n\n")
            f.write("## 最近一个月全部数据 (按时间降序排列)\n\n")

            # 截取最近一个月的数据
            if not df.empty:
                # 检查数据框中的列
                print(f"数据框中的所有列: {df.columns.tolist()}")
                print(f"China_10Y_Treasury_Yield 是否存在: {'China_10Y_Treasury_Yield' in df.columns}")
                
                last_date = df.index[-1]
                one_month_ago = last_date - pd.DateOffset(months=1)
                # 使用 .copy() 来避免 SettingWithCopyWarning
                last_month_df = df[df.index >= one_month_ago].copy()

                # 按用户要求，将数据按日期降序排列
                last_month_df.sort_index(ascending=False, inplace=True)

                # 所有列都是要显示的列
                display_columns = df.columns.tolist()
                print(f"将要显示的列: {display_columns}")
                
                # 确保重要列排在前面
                priority_columns = ['China_10Y_Treasury_Yield', 'US_10Y_Treasury_Yield', 'Shanghai_Composite_Index', 
                                   'CSI_300_Index', 'Shenzhen_Component_Index', 'GOLD_spot_price', 'OIL_price']
                
                # 重新排序列，优先显示重要列
                ordered_columns = []
                for col in priority_columns:
                    if col in display_columns:
                        ordered_columns.append(col)
                        display_columns.remove(col)
                
                # 添加剩余的列
                ordered_columns.extend(display_columns)
                print(f"最终排序后的列: {ordered_columns}")
                
                # 将数据转换为Markdown格式并写入文件
                if not last_month_df.empty and ordered_columns:
                    # 检查China_10Y_Treasury_Yield是否在最终列表中
                    if 'China_10Y_Treasury_Yield' not in ordered_columns and 'China_10Y_Treasury_Yield' in last_month_df.columns:
                        print("警告: China_10Y_Treasury_Yield不在最终列表中，但存在于数据框中")
                        ordered_columns.insert(0, 'China_10Y_Treasury_Yield')
                    
                    # 将索引（日期）格式化为字符串，避免时区信息
                    last_month_df.index = last_month_df.index.strftime('%Y-%m-%d')
                    
                    # 确保所有列都在数据框中
                    valid_columns = [col for col in ordered_columns if col in last_month_df.columns]
                    print(f"最终有效的列: {valid_columns}")
                    
                    # 转换为Markdown
                    markdown_table = last_month_df[valid_columns].to_markdown()
                    f.write(markdown_table)
        
        logging.info(f"市场分析及数据已保存到: {filepath}")
        return filepath
    except Exception as e:
        logging.error(f"保存市场分析及数据失败: {str(e)}")
        logging.error(traceback.format_exc())
        return None

def run_market_analysis():
    """运行完整的市场数据分析流程"""
    logging.info("开始下载最近1年的市场数据...")
    df = download_gold_training_data(years=1)
    
    if df is None:
        logging.error("数据下载失败，无法继续分析")
        return
    
    logging.info("准备数据用于AI分析...")
    market_data = prepare_market_data_for_analysis(df)
    
    if market_data is None:
        logging.error("数据准备失败，无法继续分析")
        return
    
    try:
        today = get_china_time().strftime('%Y-%m-%d')
        json_filename = f"global_market_data_{today}.json"
        json_filepath = os.path.join(DATA_DIR, "global_market_data_latest.json")
        
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(market_data, f, ensure_ascii=False, indent=2)
        
        dated_json_filepath = os.path.join(DATA_DIR, json_filename)
        with open(dated_json_filepath, 'w', encoding='utf-8') as f:
            json.dump(market_data, f, ensure_ascii=False, indent=2)
            
        logging.info(f"市场数据已保存到: {json_filepath} 和 {dated_json_filepath}")
    except Exception as e:
        logging.error(f"保存市场数据JSON失败: {str(e)}")
    
    logging.info("使用Gemini AI生成市场分析...")
    analysis = generate_market_summary(market_data)
    
    if analysis and "生成分析失败" not in analysis:
        # 将df传递给保存函数
        saved_path = save_market_analysis(analysis, df)
        if saved_path:
            logging.info(f"完整分析流程已完成，分析报告保存在: {saved_path}")
        else:
            logging.error("保存分析报告失败")
    else:
        logging.error("生成分析失败，无法保存报告")

if __name__ == '__main__':
    run_market_analysis()
