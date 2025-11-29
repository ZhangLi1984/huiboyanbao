#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import re
import os
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# ===== 全局配置 =====
OUTPUT_DIR = "研报数据"
MAX_RETRIES = 3  # 最大重试次数

# ===== 抓取任务配置 =====
# 格式: (任务名称, ID/类型, 抓取函数类型, 开始页, 结束页)
# 函数类型: 'microns' (普通列表), 'rightmore' (表格列表), 'elitelist' (精选列表)
TASKS = [
    # --- 核心研报 ---
    ("公司调研", 1, 'microns', 1, 3),
    ("行业分析", 2, 'microns', 1, 3),
    ("投资策略", 4, 'microns', 1, 3),
    ("宏观经济", 13, 'microns', 1, 3),
    
    # --- 热门与精选 ---
    ("最新买入", 4, 'rightmore', 1, 3),
    ("今日热门", 0, 'rightmore', 1, 3),
    ("精选研报", 0, 'elitelist', 1, 3),
    
    # --- 其他分类 (根据导航栏) ---
    ("债券研究", 16, 'microns', 1, 2),
    ("晨会早刊", 14, 'microns', 1, 2),
    ("机构资讯", 5, 'microns', 1, 2),
    ("新股研究", 21, 'microns', 1, 2),
    ("并购重组", 22, 'microns', 1, 2),
    ("港美研究", 9, 'microns', 1, 2),
    ("金融工程", 18, 'microns', 1, 2),
    ("投资组合", 19, 'microns', 1, 2),
    ("融资融券", 20, 'microns', 1, 2),
    ("期货研究", 8, 'microns', 1, 2),
    ("股指期货", 15, 'microns', 1, 2),
    ("期权研究", 23, 'microns', 1, 2),
    ("基金频道", 6, 'microns', 1, 2),
]

# ===== 辅助函数 =====
def init_driver():
    """初始化浏览器驱动"""
    print("正在启动浏览器驱动...")
    options = uc.ChromeOptions()
    # options.add_argument('--headless')  # 调试时可注释此行以显示浏览器界面
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    
    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
    except Exception as e:
        print(f"驱动初始化自动匹配失败，尝试使用兼容模式: {e}")
        # 如果自动匹配失败，通常是因为版本不一致，这里可以尝试指定版本或忽略
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=130) # 请根据实际Chrome版本调整
    
    driver.implicitly_wait(10)
    return driver

def save_data(data, prefix="研报数据"):
    """保存数据到CSV"""
    if not data:
        print(f"[{prefix}] 没有数据需要保存。")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    df = pd.DataFrame(data)
    
    # 去重
    df = df.drop_duplicates(subset=['分类', '研报标题'])
    
    # 文件名生成
    today = datetime.now()
    
    # 计算本周的开始日期（周一）和结束日期（周日）
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # 格式化日期为字符串
    week_str = f"{start_of_week.strftime('%Y%m%d')}-{end_of_week.strftime('%Y%m%d')}"
    
    timestamp = today.strftime("%Y%m%d_%H%M")
    filename = os.path.join(OUTPUT_DIR, f"{prefix}_第{today.isocalendar()[1]}周_{week_str}_{timestamp}.csv")
    
    try:
        # 保存带有时间戳和周次的版本
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ 数据已保存至: {filename} (共 {len(df)} 条)")
        
        # 同时保存一个当前最新版本的文件（方便其他程序引用）
        latest_file = os.path.join(OUTPUT_DIR, f"{prefix}_最新数据.csv")
        
        # 如果文件已存在，先删除
        if os.path.exists(latest_file):
            try:
                os.remove(latest_file)
                print(f"🗑️ 已删除旧版本: {latest_file}")
            except Exception as e:
                print(f"⚠️ 删除旧版本失败 (可能文件被占用): {e}")

        df.to_csv(latest_file, index=False, encoding='utf-8-sig')
        print(f"✅ 最新数据已保存至: {latest_file}")
        
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")

# ===== 1. Microns 样式爬虫 (适用于大多数分类) =====
def scrape_microns_style_page(driver, category_name, category_id, start_page, end_page, url_prefix="microns"):
    all_reports = []
    # 构建URL模板，支持 microns_1_1.html 或 freport_11_1.html
    base_url = f"https://www.hibor.com.cn/{url_prefix}_{category_id}_{{page_num}}.html"

    for page_num in range(start_page, end_page + 1):
        url = base_url.format(page_num=page_num)
        print(f"正在抓取 [{category_name}] 第 {page_num} 页: {url}")

        for attempt in range(MAX_RETRIES):
            try:
                driver.get(url)
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "tableList")))
                time.sleep(1) # 等待DOM完全稳定

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                table = soup.find('table', id='tableList')
                
                if not table:
                    print(f"  - 未找到数据表格")
                    break

                rows = table.find_all('tr', recursive=False)
                if not rows: rows = table.find_all('tr') # 兼容性处理

                page_count = 0
                # 慧博列表结构：标题行 -> 摘要行 -> 元数据行 -> 空行 (4行一组)
                for i in range(0, len(rows), 4):
                    if i + 2 >= len(rows): break
                    
                    try:
                        title_row = rows[i]
                        summary_row = rows[i+1]
                        meta_row = rows[i+2]

                        # 标题
                        title_link = title_row.select_one('.tab_lta a') or title_row.find('a', href=re.compile(r'/data/'))
                        full_title = title_link.get_text(strip=True) if title_link else "N/A"
                        # [已修改] 不再保存链接
                        # link = f"https://www.hibor.com.cn{title_link['href']}" if title_link else "N/A"

                        # 摘要
                        summary = "N/A"
                        summary_cell = summary_row.find('td')
                        if summary_cell:
                            for tag in summary_cell.find_all('a'): tag.decompose() # 移除[详细]
                            summary = summary_cell.get_text(strip=True)

                        # 元数据
                        author, rating, report_date, pages, sharer = ('N/A',) * 5
                        meta_cell = meta_row.find('td')
                        if meta_cell:
                            text_content = meta_cell.get_text(" ", strip=True) # 使用空格分隔
                            
                            # 简单的正则提取
                            if '作者：' in text_content:
                                author = text_content.split('作者：')[1].split(' ')[0]
                            if '评级：' in text_content:
                                try: rating = meta_cell.find('label').get_text(strip=True)
                                except: pass
                            
                            date_match = re.search(r'\d{4}-\d{2}-\d{2}', text_content)
                            if date_match: report_date = date_match.group(0)
                            
                            pages_match = re.search(r'页数：(\d+)', text_content)
                            if pages_match: pages = pages_match.group(1)

                        all_reports.append({
                            "分类": category_name,
                            "研报标题": full_title,
                            "摘要": summary,
                            "作者": author,
                            "评级": rating,
                            "页数": pages,
                            "日期": report_date,
                            # "链接": link,  # [已移除] 节省Token
                            "页码": page_num,
                            "抓取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        page_count += 1
                    except Exception:
                        continue
                
                print(f"  - 成功抓取 {page_count} 条")
                break # 成功则跳出重试循环

            except Exception as e:
                print(f"  - 尝试 {attempt+1}/{MAX_RETRIES} 失败: {e}")
                time.sleep(2)
    
    return all_reports

# ===== 2. Rightmore 样式爬虫 (最新买入、热门) =====
def scrape_rightmore_style_page(driver, category_name, category_id, start_page, end_page):
    all_reports = []
    # 支持 rightmore_0.html (第1页) 和 rightmore_0_2.html (第2页) 的逻辑
    # 慧博逻辑：第1页通常是 rightmore_X.html 或 rightmore_X_1.html，翻页是 rightmore_X_page.html
    
    for page_num in range(start_page, end_page + 1):
        if page_num == 1:
            # 尝试标准首页格式，部分分类可能是 _1.html
            url = f"https://www.hibor.com.cn/rightmore_{category_id}_{page_num}.html"
        else:
            url = f"https://www.hibor.com.cn/rightmore_{category_id}_{page_num}.html"
            
        print(f"正在抓取 [{category_name}] 第 {page_num} 页: {url}")

        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "rightmore-result")))
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table', class_='rightmore-result')
            
            if not table: continue
            
            rows = table.find_all('tr')
            page_count = 0
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 4: continue # 跳过表头
                
                try:
                    # 结构通常为: 图标 | 标题 | 类型 | 评级 | 时间
                    # 索引:      0    1     2     3     4
                    title_tag = cells[1].find('a')
                    if not title_tag: continue
                    
                    full_title = title_tag.get('title') or title_tag.get_text(strip=True)
                    # [已修改] 不再保存链接
                    # link = f"https://www.hibor.com.cn{title_tag['href']}"
                    
                    rpt_type = cells[2].get_text(strip=True)
                    rating = cells[3].get_text(strip=True)
                    pub_date = cells[4].get_text(strip=True)
                    
                    all_reports.append({
                        "分类": category_name,
                        "研报标题": full_title,
                        "子类型": rpt_type,
                        "评级": rating,
                        "日期": pub_date,
                        # "链接": link, # [已移除] 节省Token
                        "页码": page_num,
                        "抓取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    page_count += 1
                except: continue
                
            print(f"  - 成功抓取 {page_count} 条")
            
        except Exception as e:
            print(f"  - 抓取失败: {e}")
            
    return all_reports

# ===== 3. Elitelist 样式爬虫 (精选研报) =====
def scrape_elitelist_style_page(driver, category_name, category_id, start_page, end_page):
    all_reports = []
    # 结构: elitelist_{page}_0.html
    base_url = f"https://www.hibor.com.cn/elitelist_{{page_num}}_0.html"
    
    for page_num in range(start_page, end_page + 1):
        url = base_url.format(page_num=page_num)
        print(f"正在抓取 [{category_name}] 第 {page_num} 页: {url}")
        
        try:
            driver.get(url)
            # 等待 trContent 加载
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "trContent")))
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # 查找所有包含研报的行
            rows = soup.find_all('tr', class_='trContent')
            
            page_count = 0
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 6: continue
                    
                    # 索引: 0图标, 1标题, 2类型, 3作者, 4页数, 5时间
                    title_tag = cells[1].find('a')
                    full_title = title_tag.get('title') if title_tag else cells[1].get_text(strip=True)
                    # [已修改] 不再保存链接
                    # link = f"https://www.hibor.com.cn{title_tag['href']}" if title_tag else ""
                    
                    rpt_type = cells[2].get_text(strip=True)
                    author = cells[3].get_text(strip=True)
                    pages = cells[4].get_text(strip=True).replace("页", "")
                    pub_date = cells[5].get_text(strip=True)
                    
                    all_reports.append({
                        "分类": category_name,
                        "研报标题": full_title,
                        "子类型": rpt_type,
                        "作者": author,
                        "页数": pages,
                        "日期": pub_date,
                        # "链接": link, # [已移除] 节省Token
                        "页码": page_num,
                        "抓取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    page_count += 1
                except: continue
                
            print(f"  - 成功抓取 {page_count} 条")
            
        except Exception as e:
            print(f"  - 抓取失败: {e}")
            
    return all_reports

# ===== 主程序 =====
def main():
    driver = None
    all_data = []
    
    try:
        driver = init_driver()
        print(f"\n🚀 开始执行抓取任务，共 {len(TASKS)} 个任务队列...")
        
        for task in TASKS:
            name, cat_id, method, start, end = task
            task_data = []
            
            print(f"\n>>> 正在处理任务: {name} (页码 {start}-{end})")
            
            if method == 'microns':
                task_data = scrape_microns_style_page(driver, name, cat_id, start, end)
            elif method == 'freport':
                task_data = scrape_microns_style_page(driver, name, cat_id, start, end, url_prefix="freport")
            elif method == 'rightmore':
                task_data = scrape_rightmore_style_page(driver, name, cat_id, start, end)
            elif method == 'elitelist':
                task_data = scrape_elitelist_style_page(driver, name, cat_id, start, end)
            
            if task_data:
                all_data.extend(task_data)
                # 可选：每抓完一个分类就保存一次，防止意外中断
                # save_data(task_data, f"分项_{name}") 
            
            time.sleep(1) # 任务间隙暂停

        # 最终保存
        print("\n🏁 所有任务完成，正在保存汇总数据...")
        save_data(all_data, "慧博研报")

    except Exception as e:
        print(f"❌ 主程序发生错误: {e}")
    finally:
        if driver:
            print("正在关闭浏览器...")
            driver.quit()

if __name__ == "__main__":
    main()
