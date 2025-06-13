import streamlit as st
import requests

# 固定 KEY 变量（你可以随时替换为你的新key）
API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.title("Helius API KEY 功能检测与可视化")

st.info("当前测试的是基础Solana RPC方法。后续所有开发/检测结果都将显示在本页面画布。")

# 提供几个可选方法供选择（你也可以继续扩展）
method_options = {
    "getVersion（节点版本）": {
        "method": "getVersion",
        "params": []
    },
    "getSlot（当前区块高度）": {
        "method": "getSlot",
        "params": []
    },
    "getHealth（节点健康状态）": {
        "method": "getHealth",
        "params": []
    },
    "getBalance（钱包余额）": {
        "method": "getBalance",
        "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]
    },
    "getAccountInfo（账户信息）": {
        "method": "getAccountInfo",
        "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]
    },
    "searchTransactions（高级-测试权限）": {
        "method": "searchTransactions",
        "params": [{
            "query": {
                "tokenTransfers": {
                    "mint": "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"
                }
            },
            "limit": 2
        }]
    }
}

sel_method = st.selectbox("请选择要检测的API方法：", list(method_options.keys()))

if st.button("运行检测"):
    st.write(f"正在请求 `{sel_method}` ...")
    m = method_options[sel_method]
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": m["method"],
        "params": m["params"]
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        st.write(f"状态码: {resp.status_code}")
        try:
            st.json(resp.json())
        except Exception:
            st.write("非标准JSON返回：", resp.text)
    except Exception as e:
        st.error(f"请求失败: {e}")

st.write("---")
st.info("选择不同方法测试，能返回数据说明你有该方法权限。返回报错/未找到/401说明权限不够。后续所有开发/数据分析都在本页画布上继续。")
