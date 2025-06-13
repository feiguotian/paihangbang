import streamlit as st
import requests
import pandas as pd
import time

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
RPC_URL = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.set_page_config(page_title="SOL兑换币种排行榜", layout="wide")
st.title("SOL兑换币种排行榜（数据源可选：Solscan/基础RPC）")
st.info(\"\"\"可选用Solscan聚合API或基础RPC分析近N秒内和SOL发生兑换的所有token合约地址、名称、累计兑换SOL排行。
主界面可切换数据源、选择DEX、设定时间窗口。表格中包含token合约、名称、符号、兑换总量，可导出。\"\"\")

# 支持的DEX及主程序ID
DEX_PROGRAMS = {
    "Raydium": "RVKd61ztZW9BXdtYq9R93uR7KkS5qX8ymBoBB9i5ALv",
    "Orca": "9WwGKNMezQd5cQyxqDLuK7p2TLWa3pLk7e8kQ4JkYvPj",
    "Phoenix": "8YbDUs6rL3CBPLhJdxx8vGS5CSpEoVVc3x5drPLp8hU5",
    "Lifinity": "6bSRvF6h6KRnSTuohkZgV4MePMRCrmkCeKPCXZpFzx9f"
}
DEX_LIST = list(DEX_PROGRAMS.keys())
DEX_LIST.insert(0, "所有DEX")

# Token名称符号（Solscan API，可缓存）
@st.cache_data(show_spinner=False, ttl=3600)
def get_token_meta(mint):
    url = f"https://public-api.solscan.io/token/meta?tokenAddress={mint}"
    try:
        resp = requests.get(url, timeout=10)
        j = resp.json()
        symbol = j.get("symbol") or ""
        name = j.get("name") or ""
        return name, symbol
    except Exception:
        return "", ""

# --------- UI输入区域 ----------
data_source = st.radio("选择数据源", ["Solscan聚合API", "基础RPC"], horizontal=True)
second_range = st.number_input("采集时间窗口（秒）", min_value=5, max_value=600, value=60, step=1)
dex_choice = st.selectbox("请选择要分析的DEX", DEX_LIST)
top_n = st.number_input("排行Top N", min_value=3, max_value=50, value=10, step=1)

# 侧边栏进度
with st.sidebar:
    st.header("运行进度 / 状态")
    status = st.empty()
    progress = st.progress(0, text="等待开始...")

# ------------------- SOLSCAN 聚合API -------------------
def solscan_query(second_range, dex_choice, top_n):
    end_ts = int(time.time())
    start_ts = end_ts - second_range
    DEX_TAGS = {
        "Raydium": "Raydium",
        "Orca": "Orca",
        "Phoenix": "Phoenix",
        "Lifinity": "Lifinity"
    }
    # solscan docs: https://public-api.solscan.io/docs/#/token/get_apiTokenSwapHistory
    url = f"https://public-api.solscan.io/token/swapHistory"
    params = {
        "startTime": start_ts,
        "endTime": end_ts,
        "offset": 0,
        "limit": 1000  # 1k足够小窗口
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        st.warning("Solscan API 查询失败。")
        return pd.DataFrame()
    swaps = resp.json().get("data", [])
    # DEX筛选
    if dex_choice != "所有DEX":
        swaps = [x for x in swaps if x.get("market") == DEX_TAGS.get(dex_choice, "")]
    # 只抓wSOL相关
    WSOL = "So11111111111111111111111111111111111111112"
    pairs = []
    for s in swaps:
        if s.get("tokenASymbol") == "SOL" or s.get("tokenBSymbol") == "SOL" or s.get("tokenA") == WSOL or s.get("tokenB") == WSOL:
            # 统一以tokenB为目标token
            if s.get("tokenA") == WSOL:
                token_mint = s.get("tokenB")
                sol_amt = abs(float(s.get("amountA", 0)) / 1e9)
            else:
                token_mint = s.get("tokenA")
                sol_amt = abs(float(s.get("amountB", 0)) / 1e9)
            pairs.append({
                "时间": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s.get("blockTime", 0))),
                "Token合约地址": token_mint,
                "累计兑换SOL数量": sol_amt,
                "交易hash": s.get("txHash"),
                "DEX": s.get("market")
            })
    df = pd.DataFrame(pairs)
    if df.empty:
        return df
    # 聚合
    agg = df.groupby("Token合约地址")["累计兑换SOL数量"].sum().reset_index()
    agg = agg.sort_values("累计兑换SOL数量", ascending=False).head(top_n)
    agg["名称"] = agg["Token合约地址"].apply(lambda x: get_token_meta(x)[0])
    agg["符号"] = agg["Token合约地址"].apply(lambda x: get_token_meta(x)[1])
    agg = agg[["Token合约地址", "名称", "符号", "累计兑换SOL数量"]]
    return agg

# ------------------- 基础RPC（保留演示/实验用）-------------------
def rpc_query(second_range, dex_choice, top_n):
    slots_per_sec = int(1 / 0.4)  # Solana约2.5 slot/秒
    if slots_per_sec < 1:
        slots_per_sec = 1
    total_slots = slots_per_sec * second_range
    WSOL_MINT = "So11111111111111111111111111111111111111112"
    TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    selected_program_ids = set(DEX_PROGRAMS.values()) if dex_choice == "所有DEX" else {DEX_PROGRAMS[dex_choice]}
    with st.spinner("查询当前slot高度..."):
        slot_resp = requests.post(RPC_URL, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []
        }, timeout=15)
        current_slot = slot_resp.json()["result"]
        start_slot = current_slot - total_slots
        with st.sidebar:
            status.info(f"当前slot高度: {current_slot}，目标区间: {start_slot} ~ {current_slot}（{total_slots} slot，{second_range}秒）\n目标DEX: {dex_choice}")

    swap_pairs = []
    error_count = 0
    t0 = time.time()
    for idx, slot in enumerate(range(start_slot, current_slot)):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getParsedBlock",
            "params": [slot, {"maxSupportedTransactionVersion": 0}]
        }
        try:
            r = requests.post(RPC_URL, json=payload, timeout=10)
            res = r.json()
            block = res.get("result")
            if not block or "transactions" not in block:
                continue
            for tx in block["transactions"]:
                msg = tx["transaction"]["message"]
                account_keys = msg["accountKeys"]
                meta = tx.get("meta", {})
                if "innerInstructions" not in meta:
                    continue
                # 检查该交易是否属于目标DEX
                hit_dex = False
                for ix in msg["instructions"]:
                    prog_idx = ix.get("programIdIndex")
                    if prog_idx is not None and len(account_keys) > prog_idx:
                        program_id = account_keys[prog_idx]
                        if program_id in selected_program_ids:
                            hit_dex = True
                            break
                if not hit_dex:
                    continue
                # 本交易内所有token转账记录
                transfers = []
                for inner in meta["innerInstructions"]:
                    for ix in inner.get("instructions", []):
                        if ix.get("programId") != TOKEN_PROGRAM_ID:
                            continue
                        parsed = ix.get("parsed")
                        if not parsed or parsed.get("type") != "transfer":
                            continue
                        info = parsed.get("info", {})
                        mint = info.get("mint")
                        source = info.get("source")
                        dest = info.get("destination")
                        amount = int(info.get("amount", 0))
                        transfers.append({
                            "mint": mint, "source": source, "dest": dest, "amount": amount
                        })
                # 查找wSOL相关的转账及对应非wSOL配对
                wsol_out = [t for t in transfers if t["mint"] == WSOL_MINT and t["amount"] > 0]
                token_out = [t for t in transfers if t["mint"] != WSOL_MINT and t["amount"] > 0]
                for w in wsol_out:
                    for t in token_out:
                        swap_pairs.append({
                            "token_mint": t["mint"],
                            "sol_amount": w["amount"] / 1e9,
                        })
        except Exception:
            error_count += 1
            continue
        # 进度
        if (idx + 1) % 10 == 0 or idx == total_slots - 1:
            elapsed = time.time() - t0
            with st.sidebar:
                progress.progress((idx + 1) / total_slots, text=f"已遍历slot：{slot}，累计swap：{len(swap_pairs)}，耗时：{elapsed:.1f}s")
                status.info(f"已遍历slot：{slot}（{idx+1}/{total_slots}），累计swap：{len(swap_pairs)}，错误区块：{error_count}")

    with st.sidebar:
        progress.empty()
        elapsed = time.time() - t0
        st.success(f"遍历完毕，抓到swap {len(swap_pairs)} 条，异常Slot {error_count} 个。总耗时 {elapsed:.2f} 秒。")

    if not swap_pairs:
        return pd.DataFrame()
    df = pd.DataFrame(swap_pairs)
    token_count = df["token_mint"].nunique() if not df.empty else 0
    agg = df.groupby("token_mint")["sol_amount"].sum().reset_index()
    agg = agg.sort_values("sol_amount", ascending=False).head(top_n)
    agg["名称"] = agg["token_mint"].apply(lambda x: get_token_meta(x)[0])
    agg["符号"] = agg["token_mint"].apply(lambda x: get_token_meta(x)[1])
    agg = agg.rename(columns={"token_mint": "Token合约地址", "sol_amount": "累计兑换SOL数量"})
    agg = agg[["Token合约地址", "名称", "符号", "累计兑换SOL数量"]]
    return agg

# ------------------- 查询并展示 -------------------
if st.button("开始抓取分析"):
    with st.spinner("数据采集中..."):
        if data_source == "Solscan聚合API":
            df = solscan_query(second_range, dex_choice, top_n)
        else:
            df = rpc_query(second_range, dex_choice, top_n)
    if df is None or df.empty:
        st.warning("此区块时间段内未获取到swap数据。可尝试扩大时间窗口、更换DEX或切换数据源。")
    else:
        st.write(f"### 与SOL兑换币种排行（Top {top_n}）")
        st.dataframe(df.style.format({"累计兑换SOL数量": "{:.6f}"}), use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False)
        st.download_button("导出排行CSV", data=csv, file_name="sol_top_tokens.csv")
