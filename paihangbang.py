import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ====== 配置区 ======
HELIUS_API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"   # ←替换为你的helius api key
TOKEN_MINT = "So11111111111111111111111111111111111111112"   # ←替换为你要分析的Token Mint地址

# ====== Streamlit 页面 ======
st.title("Solana 新币盈利钱包排行工具（前30名）")

st.write("""
- 输入Token Mint地址，自动分析7天内Swap记录，输出前30名盈利钱包。
- 支持导出CSV，所有数据本地处理。
""")

token_input = st.text_input("Token Mint地址", value=TOKEN_MINT)
submit = st.button("开始分析")

if submit:
    with st.spinner("正在拉取和分析数据，请稍候..."):

        # 获取token上线时间（这里只做演示，实际建议用solscan查block时间或项目方发布）
        token_start_time = datetime.utcnow() - timedelta(days=7)
        start_timestamp = int(token_start_time.timestamp())
        end_timestamp = int(datetime.utcnow().timestamp())

        # HELIUS API: 交易历史接口（举例，实际请用官方文档查swap相关endpoint，下面仅为演示）
        url = f"https://api.helius.xyz/v0/addresses/{token_input}/transactions?api-key={HELIUS_API_KEY}&limit=1000"

        response = requests.get(url)
        if response.status_code != 200:
            st.error("API拉取失败，请检查API KEY和Token地址")
            st.stop()
        txs = response.json()

        # 这里只是演示：假设API已经返回swap明细，每个包含
        # wallet, side（buy/sell）, amount_in, amount_out, time等
        # 实际你要根据helius返回格式写自己的数据解析（可发API返回给我帮你解析）

        # =========== 数据解析演示 =============
        # 假数据格式 [{'wallet':'xxx', 'side':'buy', 'amount':100, 'time':...}]
        # 假设你已从API解析为下表：
        df = pd.DataFrame(txs)  # 真实脚本你要解析成标准DataFrame

        if df.empty or 'wallet' not in df.columns:
            st.warning("数据为空或格式不符，请检查API返回/数据解析代码")
            st.stop()

        # 统计每个钱包的买入卖出
        profit_df = df.pivot_table(
            index='wallet',
            values='amount',
            columns='side',
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        profit_df['profit'] = profit_df.get('sell', 0) - profit_df.get('buy', 0)
        profit_df = profit_df.sort_values('profit', ascending=False)

        # 前30名
        top30 = profit_df.head(30)
        st.subheader("前30名盈利钱包")
        st.dataframe(top30)

        # 导出CSV
        csv = top30.to_csv(index=False)
        st.download_button(
            "导出为CSV",
            data=csv,
            file_name="solana_wallet_profit_top30.csv",
            mime="text/csv"
        )
