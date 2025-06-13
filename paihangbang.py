import streamlit as st
import requests
import pandas as pd
import time

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.set_page_config(page_title="SOL兑换币种排行榜", layout="wide")
st.title("SOL兑换币种排行榜（wSOL抓取，时间窗口自定义）")
st.info("采集真实wSOL转账统计，展示指定秒数窗口内所有和SOL（wSOL）发生兑换的token账户，按兑换SOL量排行（前10名）。\n\n:orange[⚠ 时间窗口支持自定义，单位为秒。采集和运行过程已收纳在右侧边栏。]")

# 侧边栏
with st.sidebar:
    st.header("运行进度 / 状态")
    status = st.empty()
    progress = st.progress(0, text="等待开始...")

# 时间窗口输入
second_range = st.number_input("请输入采集时间窗口（秒）", min_value=1, max_value=600, value=3, step=1)
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
            status.info(f"当前slot高度: {current_slot}，目标区间: {start_slot} ~ {current_slot}（{total_slots} slot，{second_range}秒）")

    all_swaps = []
    error_count = 0
    swaps_found = 0
    t0 = time.time()

    for idx, slot in enumerate(range(start_slot, current_slot)):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getParsedBlock",  # 关键！用 getParsedBlock 可直接获得 parsed innerInstructions
            "params": [slot, {"maxSupportedTransactionVersion": 0}]
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            res = r.json()
            block = res.get("result")
            if not block or "transactions" not in block:
                continue
            for tx in block["transactions"]:
                meta = tx.get("meta", {})
                if "innerInstructions" not in meta:
                    continue
                for inner in meta["innerInstructions"]:
                    for ix in inner.get("instructions", []):
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
                                "amount_wsol": amount / 1e9
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
        st.warning("本区块时间段未发现wSOL转账。")
        st.stop()

    df = pd.DataFrame(all_swaps)
    agg = df.groupby("wsol_account_dest")["amount_wsol"].sum().reset_index()
    agg = agg.sort_values("amount_wsol", ascending=False).head(10)
    agg = agg.rename(columns={"wsol_account_dest": "Token账户地址", "amount_wsol": "累计兑换SOL数量"})

    st.write("### 与SOL兑换币种（Token账户地址）排行")
    st.dataframe(agg.style.format({"累计兑换SOL数量": "{:.6f}"}), use_container_width=True, hide_index=True)

    csv = agg.to_csv(index=False)
    st.download_button("导出排行CSV", data=csv, file_name="sol_top10_tokens.csv")

    st.write("全部原始wSOL转账明细（仅前100条预览）")
    st.dataframe(df.head(100).style.format({"amount_wsol": "{:.6f}"}), use_container_width=True, hide_index=True)
    raw_csv = df.to_csv(index=False)
    st.download_button("导出全部原始明细", data=raw_csv, file_name="sol_swap_raw.csv")
