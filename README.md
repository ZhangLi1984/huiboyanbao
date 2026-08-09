

# 研报爬虫与AI分析系统

这个项目包含两个主要功能：
1. 爬取研报数据
2. 使用Google Gemini AI模型分析研报数据并通过方糖推送摘要

## 功能介绍

### 慧博研报爬虫
- 爬取投研资讯网的研报数据
- 爬取最新买入研报数据
- 爬取热门研报数据（今日热门、本周热门、本月热门）
- 爬取行业分析和投资策略研报数据
- 数据去重并保存为CSV文件

### 研报AI分析
- 使用Google Gemini模型分析研报数据
- 识别核心投资主题
- 构建高成长潜力模拟投资组合
- 通过方糖推送分析结果

## 本地运行

### 安装依赖
```bash
pip install pandas beautifulsoup4 undetected-chromedriver selenium google-generativeai requests akshare yfinance pytz
```

### 设置环境变量
```bash
# Linux/Mac
export GEMINI_API_KEY="你的Gemini API密钥"
export FANGTANG_KEY="你的方糖推送密钥"

# Windows
set GEMINI_API_KEY=你的Gemini API密钥
set FANGTANG_KEY=你的方糖推送密钥
```

### 爬取研报数据
```bash
python 慧博研报爬虫整合版.py
```

### 运行AI分析并推送
```bash
python AKShareSummer.py
```
