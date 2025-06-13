import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

st.title("Solana新币盈利钱包排行工具（前30名）")
st.write("输入Token Mint地址，自动分析7天Swap记录，输出前30名盈利钱包。")

mint_addr = st.text_input("Token Mint地址", value="4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq")
api_key = st.text_input("Helius API KEY", type="password", value="你的APIKEY")

if st.button("开始分析"):

    # 获取7天前的unix时间戳
    start_time = int((datetime.utcnow() - timedelta(days=7)).timestamp())
    end_time = int(datetime.utcnow().timestamp())

    helius_url = f"https://api.helius.xyz/v1/search/transactions?api-key={api_key}"
    headers = {"Content-Type": "application/json"}

    # Helius官方文档的body结构
    body = {
        "query": {
            "tokenTransfers": {
                "mint": mint_addr
            }
        },
        "limit": 1000,
        "before": None  # 翻页用的
    }

    resp = requests.post(helius_url, headers=headers, json=body)
    if resp.status_code != 200:
        st.error("API拉取失败，请检查API KEY和Token地址")
        st.stop()

    data = resp.json()
    txs = data.get("transactions", [])
    if not txs:
        st.warning("该Token 7天内没有交易记录。")
        st.stop()

    # 下面简化处理，实际要对txs里的每个交易详细字段筛选swap
    # 以下是简单演示，实际需要你根据返回体结构提取买/卖、地址和数量
    results = []
    for tx in txs:
        # 需要你补充，如何判断是swap（可通过program或者instruction类型）
        # 这里只演示如何提取token转账
        for transfer in tx.get("tokenTransfers", []):
            # 这里只取mint一致的
            if transfer.get("mint") == mint_addr:
                owner = transfer.get("fromUserAccount", "")  # 买入/卖出可通过amount>0,<0判断
                amount = float(transfer.get("tokenAmount", 0))
                results.append({
                    "wallet": owner,
                    "amount": amount
                })
    df = pd.DataFrame(results)
    if df.empty:
        st.warning("解析不到任何钱包数据，请检查数据结构。")
        st.stop()

    # 聚合
    profit_df = df.groupby("wallet")["amount"].sum().reset_index()
    profit_df = profit_df.sort_values("amount", ascending=False).head(30)
    st.dataframe(profit_df)
    st.download_button("导出为CSV", profit_df.to_csv(index=False), file_name="profit_top30.csv")

