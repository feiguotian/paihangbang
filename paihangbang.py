import requests
import streamlit as st
from datetime import datetime, timedelta

TOKEN_MINT = "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"

st.title("Birdeye Token Swap 历史测试")

now = int(datetime.utcnow().timestamp())
week_ago = int((datetime.utcnow() - timedelta(days=7)).timestamp())

url = "https://public-api.birdeye.so/defi/txs/token/seek_by_time"
body = {
    "token_address": TOKEN_MINT,
    "from": week_ago,
    "to": now,
    "page": 1,
    "limit": 100
}
headers = {"accept": "application/json", "content-type": "application/json"}

if st.button("测试Birdeye接口"):
    resp = requests.post(url, headers=headers, json=body)
    st.write(f"状态码: {resp.status_code}")
    try:
        st.json(resp.json())
    except Exception as e:
        st.write(resp.text)
