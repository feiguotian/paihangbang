import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ============ 配置区 ============
API_KEY = "你的helius_api_key"   # 直接写死
DEFAULT_TOKEN_MINT = "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"

# ============ 页面UI ============
st.title("Solana 新币盈利钱包排行工具（前30名）")
st.write("输入Token Mint地址，自动分析7天Swap记录，输出前30名盈利钱包。")

token_mint = st.text_input("Token Mint地址", value=DEFAULT_TOKEN_MINT)
start = st.button("开始分析")

if start:
    # ...其余逻辑和上面完全一样...
    # 下面是API请求部分
    start_time = int((datetime.utcnow() - timedelta(days=7)).timestamp())
    helius_url = f"https://api.helius.xyz/v1/search/transactions?api-key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {
        "query": {
            "tokenTransfers": {
                "mint": token_mint
            }
        },
        "limit": 1000,
        "before": None
    }
    resp = requests.post(helius_url, headers=headers, json=body)
    if resp.status_code != 200:
        st.error("API拉取失败，请检查API KEY和Token地址")
        st.stop()

    data = resp.json()
    # ...后续数据分析与展示同前...
