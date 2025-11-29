#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import logging
from datetime import datetime, timedelta

# --- 配置 ---
# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 任务1配置：清理旧文件夹
TARGET_DIR_FOLDERS = "Gemini发送内容"
DAYS_TO_KEEP = 10

# 任务2配置：清理旧研报数据
TARGET_DIR_REPORTS = "研报数据"
MAX_REPORT_FILES = 50  # 保留最新的文件数量

def clean_old_subfolders():
    """
    任务1: 扫描指定目录，并删除创建时间早于指定天数的子文件夹。
    子文件夹的名称必须是 'YYYY-MM-DD' 格式。
    """
    logging.info("-" * 30)
    logging.info(f"任务1: 开始清理 '{TARGET_DIR_FOLDERS}' 目录下的旧文件夹...")
    
    if not os.path.isdir(TARGET_DIR_FOLDERS):
        logging.warning(f"目录 '{TARGET_DIR_FOLDERS}' 不存在，跳过此任务。")
        return

    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=DAYS_TO_KEEP)
    logging.info(f"截止日期: {cutoff_date.strftime('%Y-%m-%d')} (在此之前的文件夹将被删除)")

    deleted_count = 0
    kept_count = 0

    for item_name in os.listdir(TARGET_DIR_FOLDERS):
        item_path = os.path.join(TARGET_DIR_FOLDERS, item_name)

        if os.path.isdir(item_path):
            try:
                # 尝试将文件夹名称解析为日期
                folder_date = datetime.strptime(item_name, '%Y-%m-%d')

                if folder_date < cutoff_date:
                    logging.info(f"正在删除旧文件夹: {item_path}")
                    shutil.rmtree(item_path)
                    deleted_count += 1
                else:
                    # logging.info(f"保留近期文件夹: {item_name}") # 减少刷屏
                    kept_count += 1
            except ValueError:
                logging.warning(f"跳过格式不正确的文件夹: {item_name}")
            except Exception as e:
                logging.error(f"删除文件夹 {item_path} 时发生错误: {e}")

    logging.info(f"任务1完成: 删除 {deleted_count} 个，保留 {kept_count} 个。")

def clean_old_report_data():
    """
    任务2: 清理研报数据目录。
    规则:
    1. 总是保留包含 '最新数据.csv' 的文件。
    2. 其余 .csv 文件按修改时间排序，只保留最新的 50 个。
    """
    logging.info("-" * 30)
    logging.info(f"任务2: 开始清理 '{TARGET_DIR_REPORTS}' 目录下的旧研报...")

    if not os.path.isdir(TARGET_DIR_REPORTS):
        logging.warning(f"目录 '{TARGET_DIR_REPORTS}' 不存在，跳过此任务。")
        return

    all_files = []
    
    # 扫描目录
    for f in os.listdir(TARGET_DIR_REPORTS):
        file_path = os.path.join(TARGET_DIR_REPORTS, f)
        
        # 只处理文件，且是csv
        if os.path.isfile(file_path) and f.endswith(".csv"):
            # 规则: 总是保留“最新数据”文件
            if "最新数据" in f:
                logging.info(f"永久保留: {f}")
                continue
            
            all_files.append(file_path)

    # 检查文件数量
    if len(all_files) <= MAX_REPORT_FILES:
        logging.info(f"当前历史文件数量 ({len(all_files)}) 未超过限制 ({MAX_REPORT_FILES})，无需清理。")
        return

    # 按修改时间倒序排序 (最新的在最前)
    all_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    # 分离保留和删除列表
    files_to_keep = all_files[:MAX_REPORT_FILES]
    files_to_delete = all_files[MAX_REPORT_FILES:]

    logging.info(f"发现 {len(all_files)} 个历史文件，将删除最旧的 {len(files_to_delete)} 个。")

    deleted_count = 0
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            logging.info(f"已删除归档: {os.path.basename(file_path)}")
            deleted_count += 1
        except Exception as e:
            logging.error(f"删除文件 {os.path.basename(file_path)} 失败: {e}")

    logging.info(f"任务2完成: 已清理 {deleted_count} 个旧文件。")

def main():
    logging.info("=== 开始执行清理脚本 ===")
    clean_old_subfolders()
    clean_old_report_data()
    logging.info("=== 所有清理任务结束 ===")

if __name__ == "__main__":
    main()
