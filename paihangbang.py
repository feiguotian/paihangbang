import streamlit as st
import requests
import time
import pandas as pd

API_KEY = "f71ab4f1-900c-43a7-8ea2-9b4a440b008e"
url = f"https://rpc.helius.xyz/?api-key={API_KEY}"

st.title("Solana Token Swap 盈利榜单（基础RPC版）")
st.info("仅用 getSlot/getBlock 基础接口，抓取近10分钟指定Token的交易排行。")

# 参数输入
token_mint = st.text_input(
    "请输入目标Token的Mint地址：",
    value="So11111111111111111111111111111111111111112",  # 默认SOL
)
minute_range = st.selectbox("分析时间范围：", ["5分钟", "10分钟", "1小时"], index=1)
range_map = {"5分钟": 5, "10分钟": 10, "1小时": 60}
minutes = range_map[minute_range]

if st.button("开始抓取分析"):
    with st.spinner("查询区块高度/slot..."):
        slot_resp = requests.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []
        }, timeout=15)
        current_slot = slot_resp.json()["result"]

        # 估算slot间隔，solana约400ms一个slot，10分钟=1500slot，5分钟=750slot，1小时约9000slot
        slots_per_min = int(60 / 0.4)  # 150 slot/min
        total_slots = slots_per_min * minutes
        start_slot = current_slot - total_slots

        st.write(f"当前slot高度: {current_slot}，目标区间: {start_slot} ~ {current_slot}（共 {total_slots} slot）")
    
    all_swaps = []
    error_count = 0

    # 只抓部分slot，防止超量
    st.info("开始遍历slot，可能需几分钟……")
    progress = st.progress(0)
    for idx, slot in enumerate(range(start_slot, current_slot)):
        # 查询block
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

            # 遍历所有交易，提取含token的swap
            for tx in block["transactions"]:
                # 解析token转账
                meta = tx.get("meta", {})
                inner_instructions = meta.get("innerInstructions", [])
                if not inner_instructions:
                    continue
                for inner in inner_instructions:
                    for inst in inner.get("instructions", []):
                        # token转账一般是Program 0xTokenkeg...，data有Transfer、Swap等
                        if inst.get("programId") == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                            if "data" in inst and inst.get("parsed"):
                                info = inst["parsed"]["info"]
                                if info.get("mint") == token_mint:
                                    all_swaps.append({
                                        "slot": slot,
                                        "source": info.get("source"),
                                        "dest": info.get("destination"),
                                        "amount": int(info.get("amount")),
                                        "type": info.get("type"),
                                        "tx": tx["transaction"]["signatures"][0],
                                    })
        except Exception as e:
            error_count += 1
            continue
        progress.progress((idx + 1) / total_slots)
    progress.empty()
    st.success(f"区块遍历完成，抓到Token交易 {len(all_swaps)} 条，异常Slot {error_count} 个。")

    if not all_swaps:
        st.warning("未抓到任何token转账，请检查token mint是否正确，或缩小时间范围。")
        st.stop()

    # 聚合每个钱包的买卖情况
    df = pd.DataFrame(all_swaps)
    df["盈利"] = df.apply(lambda row: row["amount"] if row["type"] == "transfer" else -row["amount"], axis=1)
    buy = df.groupby("dest")["盈利"].sum().reset_index().rename(columns={"dest": "钱包", "盈利": "净买入"})
    sell = df.groupby("source")["盈利"].sum().reset_index().rename(columns={"source": "钱包", "盈利": "净卖出"})
    rank = buy.merge(sell, how="outer", on="钱包").fillna(0)
    rank["盈利"] = rank["净买入"] - rank["净卖出"]
    rank = rank.sort_values("盈利", ascending=False).reset_index(drop=True)

    st.write("### Top 钱包盈利排行")
    st.dataframe(rank[["钱包", "盈利", "净买入", "净卖出"]].head(20))

    csv = rank.to_csv(index=False)
    st.download_button("导出排行CSV", data=csv, file_name="token_rank.csv")

    st.write("---")
    st.write("全部原始token交易明细：")
    st.dataframe(df)
    raw_csv = df.to_csv(index=False)
    st.download_button("导出全部交易明细", data=raw_csv, file_name="token_swaps.csv")
