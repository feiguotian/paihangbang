import requests
import streamlit as st

API_KEY = "你的helius_api_key"   # 换成你自己的
TOKEN_MINT = "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"

st.title("Helius API 拉取测试")

if st.button("测试API"):
    url = f"https://api.helius.xyz/v1/search/transactions?api-key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {
        "query": {
            "tokenTransfers": {
                "mint": TOKEN_MINT
            }
        },
        "limit": 5,
        "before": None
    }
    r = requests.post(url, headers=headers, json=body)
    st.write(f"状态码: {r.status_code}")
    try:
        data = r.json()
        st.json(data)
    except Exception as e:
        st.write("不是标准json格式返回！")
        st.write(r.text)
