import requests
import streamlit as st

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
TOKEN_MINT = "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"

url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

# JSON-RPC 请求体
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "searchTransactions",
    "params": {
        "query": {
            "tokenTransfers": {
                "mint": TOKEN_MINT
            }
        },
        "limit": 10
    }
}

st.title("Helius searchTransactions JSON-RPC 测试")
if st.button("测试Helius API"):
    st.write("正在请求API...")
    resp = requests.post(url, json=payload)
    st.write(f"状态码: {resp.status_code}")
    try:
        st.json(resp.json())
    except Exception as e:
        st.write(resp.text)
