import streamlit as st
import requests

st.title("Birdeye Token Swap API 测试（只查10条）")

TOKEN_MINT = "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"
API_KEY = "c11020fe7a6d4fea8f3c118b3565ac39"  # 换成你自己的Key更稳妥

url = f"https://public-api.birdeye.so/defi/txs/token/seek_by_time?offset=0&limit=10&tx_type=swap&token_address={TOKEN_MINT}"
headers = {
    "accept": "application/json",
    "x-chain": "solana",
    "X-API-KEY": API_KEY
}

if st.button("测试Birdeye API"):
    st.write("正在请求API...")
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        st.write(f"状态码: {resp.status_code}")
        if resp.status_code == 200:
            st.json(resp.json())
        else:
            st.write(resp.text)
    except Exception as e:
        st.error(f"请求失败: {e}")
