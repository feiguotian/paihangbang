import requests
import json

API_KEY = "你的 Helius API KEY"   # 换成你的key
URL = f"https://rpc.helius.xyz/?api-key={API_KEY}"

methods = [
    {"method": "getHealth", "params": []},
    {"method": "getSlot", "params": []},
    {"method": "getVersion", "params": []},
    {"method": "getBlockHeight", "params": []},
    {"method": "getBalance", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    {"method": "getAccountInfo", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    {"method": "getSignaturesForAddress", "params": ["4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"]},
    # 高级
    {"method": "searchTransactions", "params": {"query": {"tokenTransfers": {"mint": "4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"}}, "limit": 2}},
]

def do_test(method, params):
    if method == "searchTransactions":
        rpc_params = [params]
    else:
        rpc_params = params
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": rpc_params
    }
    try:
        resp = requests.post(URL, json=payload, timeout=15)
        print(f"\n>>> 测试方法: {method} | 状态码: {resp.status_code}")
        try:
            data = resp.json()
            if "error" in data:
                print("  错误:", data["error"].get("message", data["error"]))
            else:
                # 只打印关键信息
                print("  成功返回：", json.dumps(data.get("result", data), ensure_ascii=False, indent=2)[:500], "...")
        except Exception:
            print("  非标准JSON：", resp.text[:200])
    except Exception as e:
        print("  请求异常：", e)

if __name__ == "__main__":
    print("=== Helius Key功能检测 ===")
    for m in methods:
        do_test(m["method"], m["params"])
    print("=== 检测结束 ===")
