import requests
import json

API_KEY = "你的 Helius API KEY"  # 填你的key
URL = f"https://rpc.helius.xyz/?api-key={API_KEY}"

methods = [
    {"method": "getHealth", "params": []},
    {"method": "getSlot", "params": []},
    {"method": "getVersion", "params": []},
    {"method": "getBlockHeight", "params": []},
    {"method": "getBalance", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    {"method": "getAccountInfo", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    {"method": "getSignaturesForAddress", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    {"method": "getTransaction", "params": ["5ac1DgzMLz9Qw1UJAVPLQzErnkdzjgvCKTEnMeT7tG28s82QzJKhAb6AGbnGAs4aFVwRGsAtHDg6B4LbHEFSYPUC"]},
    {"method": "searchTransactions", "params": {"query": {"tokenTransfers": {"mint": "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"}}, "limit": 2}},
]

for i, item in enumerate(methods):
    method = item["method"]
    params = item["params"]
    # searchTransactions 特例需要 list 包一层
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
        resp = requests.post(URL, json=payload, timeout=15)
        print(f"状态码: {resp.status_code}")
        try:
            data = resp.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print("非标准JSON返回：", resp.text)
    except Exception as e:
        print(f"请求异常：{e}")
