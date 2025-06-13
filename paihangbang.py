import streamlit as st
import requests
import pandas as pd
import time

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.set_page_config(page_title="近3秒SOL兑换币种排行榜", layout="wide")
st.title("近3秒SOL兑换币种排行榜（Raydium wSOL 测试版）")
st.info("统计近3秒内所有和SOL（wSOL）发生兑换的token账户，按兑换SOL量排行（前10名）。采集真实wSOL转账。\n\n:orange[⚠ 时间窗口后期可改，这里为3秒，仅便于调试。]")

# 时间窗口设为3秒（后期可调整）
second_range = 3  # 时间窗口
slots_per_sec = int(1 / 0.4)  # Solana约2.5 slot/秒
# 取整保证不漏
if slots_per_sec < 1:
    slots_per_sec = 1

total_slots = slots_per_sec * second_range

WSOL_MINT = "So11111111111111111111111111111111111111112"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

if st.button("开始抓取分析"):
    status = st.empty()
    progress = st.progress(0, text="初始化…")
    with st.spinner("查询当前slot高度..."):
        slot_resp = requests.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []
        }, timeout=15)
        current_slot = slot_resp.json()["result"]
        start_slot = current_slot - total_slots
        status.info(f"当前slot高度: {current_slot}，目标区间: {start_slot} ~ {current_slot}（约 {total_slots} slot，窗口{second_range}秒，后期可调）")

    all_swaps = []
    error_count = 0
    swaps_found = 0
    t0 = time.time()
    for idx, slot in enumerate(range(start_slot, current_slot)):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBlock",
            "params": [slot, {"maxSupportedTransactionVersion": 0, "transactionDetails": "full", "rewards": False}]
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
        # 进度和状态实时显示
        if (idx + 1) % 2 == 0 or idx == total_slots - 1:
            elapsed = time.time() - t0
            progress.progress((idx + 1) / total_slots, text=f"已遍历slot：{slot}，累计wSOL转账：{swaps_found}，耗时：{elapsed:.1f}s")
            status.info(f"已遍历slot：{slot}（{idx+1}/{total_slots}），累计wSOL转账：{swaps_found}，错误区块：{error_count}")
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

    st.write("### 近3秒与SOL兑换币种（Token账户地址）排行 :orange[(窗口后期可调)]")
    st.dataframe(agg.style.format({"累计兑换SOL数量": "{:.6f}"}), use_container_width=True, hide_index=True)

    csv = agg.to_csv(index=False)
    st.download_button("导出排行CSV", data=csv, file_name="sol_top10_tokens.csv")

    st.write(":green[全部原始wSOL转账明细（仅前100条预览）]:")
    st.dataframe(df.head(100).style.format({"amount_wsol": "{:.6f}"}), use_container_width=True, hide_index=True)
    raw_csv = df.to_csv(index=False)
    st.download_button("导出全部原始明细", data=raw_csv, file_name="sol_swap_raw.csv")
