import streamlit as st
import requests
import pandas as pd
import time

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.set_page_config(page_title="近1分钟SOL兑换币种排行榜", layout="wide")
st.title("近1分钟SOL兑换币种排行榜（Raydium 测试版）")
st.info("仅抓 Raydium DEX，统计近1分钟所有和SOL发生兑换的币种账户，按兑换SOL量排行（前10名）。每步获取过程均实时展示。")

minute_range = 1
slots_per_min = int(60 / 0.4)  # 150 slot/min
total_slots = slots_per_min * minute_range

DEX_PROGRAM_ID = "RVKd61ztZW9BXdtYq9R93uR7KkS5qX8ymBoBB9i5ALv"  # Raydium V4
SOL_SYSTEM_ACCOUNT = "11111111111111111111111111111111"  # SOL原生系统账户

if st.button("开始抓取分析"):
    status = st.empty()
    progress = st.progress(0, text="初始化…")
    with st.spinner("查询当前slot高度..."):
        slot_resp = requests.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []
        }, timeout=15)
        current_slot = slot_resp.json()["result"]
        start_slot = current_slot - total_slots
        status.info(f"当前slot高度: {current_slot}，目标区间: {start_slot} ~ {current_slot}（约 {total_slots} slot）")

    all_swaps = []
    error_count = 0
    swaps_found = 0
    t0 = time.time()
    for idx, slot in enumerate(range(start_slot, current_slot)):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBlock",
            "params": [slot, {"maxSupportedTransactionVersion": 0}]
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            res = r.json()
            block = res.get("result")
            if not block or "transactions" not in block:
                continue
            for tx in block["transactions"]:
                tx_msg = tx["transaction"]["message"]
                account_keys = tx_msg["accountKeys"]
                ixns = tx_msg["instructions"]
                meta = tx.get("meta", {})
                pre_balances = meta.get("preBalances", [])
                post_balances = meta.get("postBalances", [])
                if not (ixns and pre_balances and post_balances):
                    continue
                for ix in ixns:
                    prog_idx = ix["programIdIndex"]
                    program_id = account_keys[prog_idx]
                    if program_id != DEX_PROGRAM_ID:
                        continue
                    acc = ix["accounts"]
                    # acc[0]=user_source_token, acc[1]=user_dest_token
                    if len(acc) > 2:
                        try:
                            source = account_keys[acc[0]]
                            dest = account_keys[acc[1]]
                            # 只抓和SOL相关的兑换
                            if source == SOL_SYSTEM_ACCOUNT or dest == SOL_SYSTEM_ACCOUNT:
                                sol_change = 0
                                swapped_token = dest if source == SOL_SYSTEM_ACCOUNT else source
                                # 估算sol实际变动量
                                if source == SOL_SYSTEM_ACCOUNT:
                                    sol_change = meta["preBalances"][0] - meta["postBalances"][0]
                                else:
                                    sol_change = meta["postBalances"][0] - meta["preBalances"][0]
                                all_swaps.append({
                                    "slot": slot,
                                    "blockTime": block.get("blockTime", None),
                                    "swapped_token_account": swapped_token,
                                    "sol_amount": abs(sol_change) / 1e9  # lamports to SOL
                                })
                                swaps_found += 1
                        except Exception:
                            continue
        except Exception:
            error_count += 1
            continue

        # 实时进度与当前抓取状态
        if (idx + 1) % 10 == 0 or idx == total_slots - 1:
            elapsed = time.time() - t0
            progress.progress((idx + 1) / total_slots, text=f"已遍历slot：{slot}，累计swap：{swaps_found}，耗时：{elapsed:.1f}s")
            status.info(f"已遍历slot：{slot}（{idx+1}/{total_slots}），累计swap：{swaps_found}，错误区块：{error_count}")

    progress.empty()
    elapsed = time.time() - t0
    st.success(f"遍历完毕，抓到与SOL兑换相关Swap记录 {len(all_swaps)} 条，异常Slot {error_count} 个。总耗时 {elapsed:.2f} 秒。")

    if not all_swaps:
        st.warning("本区块时间段未发现和SOL兑换的swap。")
        st.stop()

    df = pd.DataFrame(all_swaps)
    agg = df.groupby("swapped_token_account")["sol_amount"].sum().reset_index()
    agg = agg.sort_values("sol_amount", ascending=False).head(10)
    agg = agg.rename(columns={"swapped_token_account": "Token账户地址", "sol_amount": "累计兑换SOL数量"})

    st.write("### 近1分钟与SOL兑换币种（Token账户地址）排行")
    st.dataframe(agg.style.format({"累计兑换SOL数量": "{:.6f}"}), use_container_width=True, hide_index=True)

    csv = agg.to_csv(index=False)
    st.download_button("导出排行CSV", data=csv, file_name="sol_top10_tokens.csv")

    st.write(":green[全部原始Swap明细（仅前100条预览）]:")
    st.dataframe(df.head(100).style.format({"sol_amount": "{:.6f}"}), use_container_width=True, hide_index=True)
    raw_csv = df.to_csv(index=False)
    st.download_button("导出全部原始明细", data=raw_csv, file_name="sol_swap_raw.csv")
