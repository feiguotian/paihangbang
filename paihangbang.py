import streamlit as st
import requests
import pandas as pd

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.title("近10分钟SOL兑换币种排行榜（基础RPC）")
st.info("扫描近10分钟区块，列出所有与SOL兑换的币种（按兑换SOL量排名）。仅支持主流DEX。")

top_n = st.slider("显示前N名（按兑换SOL量）", min_value=3, max_value=30, value=10)

minute_range = 10
slots_per_min = int(60 / 0.4)  # 150 slot/min
total_slots = slots_per_min * minute_range

DEX_PROGRAMS = {
    "Raydium V4": "RVKd61ztZW9BXdtYq9R93uR7KkS5qX8ymBoBB9i5ALv",
    "Orca V2": "9WwGKNMezQd5cQyxqDLuK7p2TLWa3pLk7e8kQ4JkYvPj",
    "Phoenix": "8YbDUs6rL3CBPLhJdxx8vGS5CSpEoVVc3x5drPLp8hU5",
    # 你可以根据实际补充其他主流DEX
}

SOL_MINT = "So11111111111111111111111111111111111111112"  # SOL的mint

if st.button("开始抓取分析"):
    with st.spinner("查询slot..."):
        slot_resp = requests.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []
        }, timeout=15)
        current_slot = slot_resp.json()["result"]
        start_slot = current_slot - total_slots
        st.write(f"当前slot高度: {current_slot}，目标区间: {start_slot} ~ {current_slot}（约 {total_slots} slot）")

    all_swaps = []
    error_count = 0
    progress = st.progress(0)
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

                # 只处理主流DEX
                for ix in ixns:
                    prog_idx = ix["programIdIndex"]
                    program_id = account_keys[prog_idx]
                    if program_id not in DEX_PROGRAMS.values():
                        continue

                    # 处理swap指令，只筛含有SOL参与的
                    # 尝试识别input/output的mint信息
                    # 这里只能靠已知Swap协议的账户结构，主流Raydium/Orca通常SOL的账户直接为 "111111..."
                    # 下面是简易的swap解码（深度解析需用Serum/Orca特定ABI）

                    # Raydium V4
                    if program_id == DEX_PROGRAMS["Raydium V4"]:
                        acc = ix["accounts"]
                        # acc通常第1,2为in/out账户，第3为池子
                        if len(acc) > 2:
                            try:
                                # 在Raydium Swap: acc[0]=user_source_token, acc[1]=user_dest_token
                                source = account_keys[acc[0]]
                                dest = account_keys[acc[1]]
                                # 如果任何一端是SOL原生账户（"11111111111111111111111111111111"），就记为和SOL兑换
                                if source == "11111111111111111111111111111111" or dest == "11111111111111111111111111111111":
                                    # 解析sol的增减
                                    sol_change = 0
                                    if source == "11111111111111111111111111111111":
                                        # 用户用SOL换其他token，SOL支出
                                        sol_change = pre_balances[0] - post_balances[0]
                                        swapped_mint = dest
                                    else:
                                        # 用户卖token换回SOL，SOL收入
                                        sol_change = post_balances[0] - pre_balances[0]
                                        swapped_mint = source
                                    # 由于结构限制，mint只能粗略用目标token账户地址映射，有时需要on-chain再查一次
                                    all_swaps.append({
                                        "slot": slot,
                                        "block": block.get("blockTime", None),
                                        "dex": "Raydium",
                                        "swapped_token": swapped_mint,
                                        "sol_amount": abs(sol_change) / 1e9  # lamports to SOL
                                    })
                            except Exception as e:
                                continue

                    # Orca/其他主流DEX，结构大同小异，可补充
                    # 你可以用类似的逻辑扩展

        except Exception as e:
            error_count += 1
            continue
        if (idx + 1) % 100 == 0:
            progress.progress((idx + 1) / total_slots)
    progress.empty()

    st.success(f"遍历完毕，抓到与SOL兑换相关Swap记录 {len(all_swaps)} 条，异常Slot {error_count} 个。")

    if not all_swaps:
        st.warning("本区块时间段未发现和SOL兑换的swap。")
        st.stop()

    # 聚合币种排行（swapped_token这里只能拿到account address，需要进一步补充为mint）
    df = pd.DataFrame(all_swaps)
    # 你可以用account address->mint的映射进一步美化结果
    agg = df.groupby("swapped_token")["sol_amount"].sum().reset_index()
    agg = agg.sort_values("sol_amount", ascending=False).head(top_n)
    agg = agg.rename(columns={"swapped_token": "Token账户/地址", "sol_amount": "累计兑换SOL数量"})

    st.write(f"### Top {top_n} 币种与SOL兑换排行榜")
    st.dataframe(agg)

    csv = agg.to_csv(index=False)
    st.download_button("导出排行CSV", data=csv, file_name="sol_top_tokens.csv")

    st.write("---")
    st.write("原始swap明细")
    st.dataframe(df)
    raw_csv = df.to_csv(index=False)
    st.download_button("导出全部原始明细", data=raw_csv, file_name="sol_swap_raw.csv")
