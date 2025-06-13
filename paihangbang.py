import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ====== 配置 ======
TOKEN_MINT = "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"  # 你要分析的Token
API_KEY = "你的Birdeye API KEY"  # <<<<<< 换成你自己的

# ====== Streamlit UI ======
st.title("Solana 新币盈利钱包排行工具（前30名）")
st.write("""
输入Token Mint地址，自动分析7天内Swap记录，输出前30名盈利钱包。
支持导出CSV，所有数据本地处理。
""")

token_input = st.text_input("Token Mint地址", value=TOKEN_MINT)
run = st.button("开始分析")

if run:
    with st.spinner("正在抓取数据..."):

        now = int(datetime.utcnow().timestamp())
        week_ago = int((datetime.utcnow() - timedelta(days=7)).timestamp())

        # 分页抓取
        all_records = []
        offset = 0
        page_size = 100

        while True:
            url = (
                "https://public-api.birdeye.so/defi/txs/token/seek_by_time"
                f"?offset={offset}&limit={page_size}"
                f"&tx_type=swap&token_address={token_input}"
                f"&from={week_ago}&to={now}"
            )
            headers = {
                "accept": "application/json",
                "x-chain": "solana",
                "X-API-KEY": API_KEY
            }
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                st.error(f"API错误: {resp.status_code}")
                st.stop()
            data = resp.json()
            tx_list = data.get("data", [])
            if not tx_list:
                break
            all_records.extend(tx_list)
            if len(tx_list) < page_size or len(all_records) >= 2000:
                # 超过2000条数据就不再往后翻（可自行增大或减少，避免超时）
                break
            offset += page_size

        st.success(f"共抓取 {len(all_records)} 条swap交易记录。")

        if not all_records:
            st.warning("没有拉取到任何交易记录，请检查Token是否有效或近期有无活跃。")
            st.stop()

        # ====== 数据聚合处理 ======
        # 结构示例：https://docs.birdeye.so/reference/get_defi_txs_token_seek_by_time
        df = pd.DataFrame(all_records)
        # from_address：卖方，to_address：买方，in_amount/out_amount等字段需具体分析
        # 我们按钱包的净流入量聚合（实际复杂策略可继续优化）

        # 以from_address为卖，to_address为买，token流向to_address
        df['buy_wallet'] = df['to_address']
        df['sell_wallet'] = df['from_address']
        df['amount'] = pd.to_numeric(df['in_amount'], errors='coerce').fillna(0)

        buy_df = df.groupby('buy_wallet')['amount'].sum().reset_index().rename(columns={'buy_wallet': 'wallet', 'amount': 'buy_amount'})
        sell_df = df.groupby('sell_wallet')['amount'].sum().reset_index().rename(columns={'sell_wallet': 'wallet', 'amount': 'sell_amount'})

        profit_df = pd.merge(buy_df, sell_df, on='wallet', how='outer').fillna(0)
        profit_df['profit'] = profit_df['sell_amount'] - profit_df['buy_amount']
        profit_df = profit_df.sort_values('profit', ascending=False)

        # 取前30名
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
