import streamlit as st
import requests
import pandas as pd
import time

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.set_page_config(page_title="SOL兑换币种排行榜", layout="wide")
st.title("SOL兑换币种排行榜（wSOL与其它token合约地址配对，DEX自选）")
st.info("采集真实wSOL与其它Token发生兑换的数据，展示指定秒数窗口内所有和SOL（wSOL）组成交易对发生过swap的token mint合约地址和名称，并统计兑换SOL量排行。\n\n:orange[⚠ 时间窗口单位秒，采集进度和详细过程收纳在右侧边栏。]")

# 支持的DEX及其主程序ID（可以随时补充）
DEX_PROGRAMS = {
    "Raydium": "RVKd61ztZW9BXdtYq9R93uR7KkS5qX8ymBoBB9i5ALv",
    "Orca": "9WwGKNMezQd5cQyxqDLuK7p2TLWa3pLk7e8kQ4JkYvPj",
    "Phoenix": "8YbDUs6rL3CBPLhJdxx8vGS5CSpEoVVc3x5drPLp8hU5",
    "Lifinity": "6bSRvF6h6KRnSTuohkZgV4MePMRCrmkCeKPCXZpFzx9f"
}

DEX_LIST = list(DEX_PROGRAMS.keys())
DEX_LIST.insert(0, "所有DEX")

def dex_id_selected(choice):
    if choice == "所有DEX":
        return set(DEX_PROGRAMS.values())
    return {DEX_PROGRAMS[choice]}

# Token mint名称符号查询（solscan，可缓存！）
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

# 侧边栏：进度、状态
with st.sidebar:
    st.header("运行进度 / 状态")
    status = st.empty()
    progress = st.progress(0, text="等待开始...")

# 参数输入
second_range = st.number_input("请输入采集时间窗口（秒）", min_value=1, max_value=600, value=60, step=1)
dex_choice = st.selectbox("请选择要分析的DEX", DEX_LIST)
selected_program_ids = dex_id_selected(dex_choice)

slots_per_sec = int(1 / 0.4)  # Solana约2.5 slot/秒
if slots_per_sec < 1:
    slots_per_sec = 1
total_slots = slots_per_sec * second_range

WSOL_MINT = "So11111111111111111111111111111111111111112"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

if st.button("开始抓取分析"):
    with st.spinner("查询当前slot高度..."):
        slot_resp = requests.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []
        }, timeout=15)
        current_slot = slot_resp.json()["result"]
        start_slot = current_slot - total_slots
        with st.sidebar:
            status.info(f"当前slot高度: {current_slot}，目标区间: {start_slot} ~ {current_slot}（{total_slots} slot，{second_range}秒）\n目标DEX: {dex_choice}")

    swap_pairs = []  # 记录wSOL<->token配对及数量
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
            r = requests.post(url, json=payload, timeout=10)
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
                    # 只关心本次与wSOL配对的所有token
                    for t in token_out:
                        # 记录一对
                        swap_pairs.append({
                            "slot": slot,
                            "blockTime": block.get("blockTime", None),
                            "token_mint": t["mint"],
                            "token_amount": t["amount"] / (10 ** 6),  # 大部分token 6位，后续可查meta自动处理
                            "sol_amount": w["amount"] / 1e9,
                            "txid": tx["transaction"]["signatures"][0]
                        })
        except Exception:
            error_count += 1
            continue
        # 进度
        if (idx + 1) % 2 == 0 or idx == total_slots - 1:
            elapsed = time.time() - t0
            with st.sidebar:
                progress.progress((idx + 1) / total_slots, text=f"已遍历slot：{slot}，累计swap：{len(swap_pairs)}，耗时：{elapsed:.1f}s")
                status.info(f"已遍历slot：{slot}（{idx+1}/{total_slots}），累计swap：{len(swap_pairs)}，错误区块：{error_count}")

    with st.sidebar:
        progress.empty()
        elapsed = time.time() - t0
        st.success(f"遍历完毕，抓到swap {len(swap_pairs)} 条，异常Slot {error_count} 个。总耗时 {elapsed:.2f} 秒。")

    if not swap_pairs:
        st.warning("本区块时间段未发现wSOL相关swap。\n（如需进一步定位，请尝试扩大时间窗口或更换DEX）")
        st.stop()

    df = pd.DataFrame(swap_pairs)
    # 统计Token合约地址种类数
    token_count = df["token_mint"].nunique() if not df.empty else 0

    # 按token_mint聚合sol兑换量
    agg = df.groupby("token_mint")["sol_amount"].sum().reset_index()
    agg = agg.sort_values("sol_amount", ascending=False).head(10)
    agg["名称"] = agg["token_mint"].apply(lambda x: get_token_meta(x)[0])
    agg["符号"] = agg["token_mint"].apply(lambda x: get_token_meta(x)[1])
    agg = agg[["token_mint", "名称", "符号", "sol_amount"]]
    agg = agg.rename(columns={"token_mint": "Token合约地址", "sol_amount": "累计兑换SOL数量"})
    st.write(f"### 与SOL兑换币种排行 | 抓到Token种类数：:orange[**{token_count}**]（按配对token合约地址统计）")
    st.dataframe(agg.style.format({"累计兑换SOL数量": "{:.6f}"}), use_container_width=True, hide_index=True)

    csv = agg.to_csv(index=False)
    st.download_button("导出排行CSV", data=csv, file_name="sol_top10_tokens.csv")

    st.write(f"全部原始swap明细（仅前100条预览，Token种类数：:orange[**{token_count}**]）")
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)
    raw_csv = df.to_csv(index=False)
    st.download_button("导出全部原始明细", data=raw_csv, file_name="sol_swap_raw.csv")
