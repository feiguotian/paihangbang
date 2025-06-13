import streamlit as st
import requests
import pandas as pd
import time

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.set_page_config(page_title="SOL兑换币种排行榜", layout="wide")
st.title("SOL兑换币种排行榜（wSOL抓取，DEX自选）")
st.info("采集真实wSOL转账统计，展示指定秒数窗口内与SOL（wSOL）发生兑换的所有token账户，按兑换SOL量排行（前10名），支持自选DEX或全DEX。\n\n:orange[⚠ 时间窗口单位秒，采集进度和详细过程收纳在右侧边栏。]")

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

    all_swaps = []
    error_count = 0
    swaps_found = 0
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
                for inner in meta["innerInstructions"]:
                    for ix in inner.get("instructions", []):
                        # 判断是否目标DEX（支持全部或单选）
                        prog_idx = ix.get("programIdIndex")
                        if prog_idx is not None and len(account_keys) > prog_idx:
                            program_id = account_keys[prog_idx]
                            if program_id not in selected_program_ids:
                                continue
                        # 只统计Token Program的transfer
                        if ix.get("programId") != TOKEN_PROGRAM_ID:
                            continue
                        parsed = ix.get("parsed")
                        if not parsed:
                            continue
                        info = parsed.get("info", {})
                        if info.get("mint") == WSOL_MINT and parsed.get("type") == "transfer":
                            source = info.get("source")
                            dest = info.get("destination")
                            amount = int(info.get("amount", 0))
                            all_swaps.append({
                                "slot": slot,
                                "blockTime": block.get("blockTime", None),
                                "wsol_account_source": source,
                                "wsol_account_dest": dest,
                                "amount_wsol": amount / 1e9,
                                "dex_program_id": program_id
                            })
                            swaps_found += 1
        except Exception:
            error_count += 1
            continue
        # 进度状态写入sidebar
        if (idx + 1) % 2 == 0 or idx == total_slots - 1:
            elapsed = time.time() - t0
            with st.sidebar:
                progress.progress((idx + 1) / total_slots, text=f"已遍历slot：{slot}，累计wSOL转账：{swaps_found}，耗时：{elapsed:.1f}s")
                status.info(f"已遍历slot：{slot}（{idx+1}/{total_slots}），累计wSOL转账：{swaps_found}，错误区块：{error_count}")

    with st.sidebar:
        progress.empty()
        elapsed = time.time() - t0
        st.success(f"遍历完毕，抓到wSOL转账 {len(all_swaps)} 条，异常Slot {error_count} 个。总耗时 {elapsed:.2f} 秒。")

    if not all_swaps:
        st.warning("本区块时间段未发现wSOL转账。\n（如需进一步定位，请尝试扩大时间窗口或更换DEX）")
        st.stop()

    df = pd.DataFrame(all_swaps)
    # 统计Token账户种类数
    token_count = df["wsol_account_dest"].nunique() if not df.empty else 0
    st.write(f"### 与SOL兑换币种（Token账户地址）排行    |    本轮抓到Token种类数：:orange[**{token_count}**] （按wSOL转账唯一目标地址数统计）")
    agg = df.groupby("wsol_account_dest")["amount_wsol"].sum().reset_index()
    agg = agg.sort_values("amount_wsol", ascending=False).head(10)
    agg = agg.rename(columns={"wsol_account_dest": "Token账户地址", "amount_wsol": "累计兑换SOL数量"})
    st.dataframe(agg.style.format({"累计兑换SOL数量": "{:.6f}"}), use_container_width=True, hide_index=True)

    csv = agg.to_csv(index=False)
    st.download_button("导出排行CSV", data=csv, file_name="sol_top10_tokens.csv")

    st.write(f"全部原始wSOL转账明细（仅前100条预览，Token种类数：:orange[**{token_count}**]）")
    st.dataframe(df.head(100).style.format({"amount_wsol": "{:.6f}"}), use_container_width=True, hide_index=True)
    raw_csv = df.to_csv(index=False)
    st.download_button("导出全部原始明细", data=raw_csv, file_name="sol_swap_raw.csv")
