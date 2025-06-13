import requests
import json

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
URL = f"https://rpc.helius.xyz/?api-key={API_KEY}"

methods_to_test = [
    # 基础Solana RPC方法
    {"method": "getHealth", "params": []},
    {"method": "getSlot", "params": []},
    {"method": "getBlockHeight", "params": []},
    {"method": "getVersion", "params": []},
    # 账户/交易相关
    {"method": "getBalance", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    {"method": "getAccountInfo", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    {"method": "getSignaturesForAddress", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    # 高级/付费特性
    {"method": "searchTransactions", "params": {"query": {"tokenTransfers": {"mint": "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"}}, "limit": 2}},
]

for i, item in enumerate(methods_to_test):
    method = item["method"]
    params = item["params"]
    # searchTransactions需要params是字典，否则是list
    if method == "searchTransactions":
        rpc_params = [params]
    else:
        rpc_params = params
    payload = {
        "jsonrpc": "2.0",
        "id": i + 1,
        "method": method,
        "params": rpc_params
    }
    print(f"\n--- 正在测试 {method} ---")
    try:
        resp = requests.post(URL, json=payload, timeout=20)
        print(f"状态码: {resp.status_code}")
        try:
            data = resp.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print("无法解析为JSON，原始文本：")
            print(resp.text)
    except Exception as e:
        print(f"请求异常：{e}")
