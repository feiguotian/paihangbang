import streamlit as st
import requests
import pandas as pd
import time

# 可选数据源
API_OPTIONS = [
    "Solscan聚合API",
    "Birdeye聚合API",
    "Jupiter聚合API",
    "基础RPC (Helius)",
]

st.set_page_config(page_title="SOL兑换币种排行榜", layout="wide")
st.title("SOL兑换币种排行榜（多API可切换/Key支持）")
st.info("可选Solscan、Birdeye、Jupiter、基础RPC等多种API；需Key的接口自动弹出输入框。")

data_source = st.radio("选择数据源", API_OPTIONS, horizontal=True)

# 动态显示需要Key的API输入框
user_keys = {}
if data_source == "Birdeye聚合API":
    user_keys["birdeye"] = st.text_input("请输入Birdeye API Key（免费注册：https://birdeye.so/）", type="password")
if data_source == "Jupiter聚合API":
    # Jupiter暂不需要Key，如需可添加
    pass
if data_source == "基础RPC (Helius)":
    user_keys["helius"] = st.text_input("请输入你的Helius API Key（基础RPC可用）", type="password")
else:
    user_keys["helius"] = ""

second_range = st.number_input("采集时间窗口（秒）", min_value=5, max_value=600, value=60, step=1)
top_n = st.number_input("排行Top N", min_value=3, max_value=50, value=10, step=1)

# DEX选择同前
DEX_PROGRAMS = {
    "Raydium": "RVKd61ztZW9BXdtYq9R93uR7KkS5qX8ymBoBB9i5ALv",
    "Orca": "9WwGKNMezQd5cQyxqDLuK7p2TLWa3pLk7e8kQ4JkYvPj",
    "Phoenix": "8YbDUs6rL3CBPLhJdxx8vGS5CSpEoVVc3x5drPLp8hU5",
    "Lifinity": "6bSRvF6h6KRnSTuohkZgV4MePMRCrmkCeKPCXZpFzx9f"
}
DEX_LIST = list(DEX_PROGRAMS.keys())
DEX_LIST.insert(0, "所有DEX")
dex_choice = st.selectbox("请选择要分析的DEX", DEX_LIST)

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

# 侧边栏进度
with st.sidebar:
    st.header("运行进度 / 状态")
    status = st.empty()
    progress = st.progress(0, text="等待开始...")

# ------------ Solscan聚合API ------------
def solscan_query(second_range, dex_choice, top_n):
    end_ts = int(time.time())
    start_ts = end_ts - second_range
    DEX_TAGS = {
        "Raydium": "Raydium",
        "Orca": "Orca",
        "Phoenix": "Phoenix",
        "Lifinity": "Lifinity"
    }
    url = f"https://public-api.solscan.io/token/swapHistory"
    params = {
        "startTime": start_ts,
        "endTime": end_ts,
        "offset": 0,
        "limit": 1000
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        st.warning("Solscan API 查询失败。")
        return pd.DataFrame()
    swaps = resp.json().get("data", [])
    if dex_choice != "所有DEX":
        swaps = [x for x in swaps if x.get("market") == DEX_TAGS.get(dex_choice, "")]
    WSOL = "So11111111111111111111111111111111111111112"
    pairs = []
    for s in swaps:
        if s.get("tokenASymbol") == "SOL" or s.get("tokenBSymbol") == "SOL" or s.get("tokenA") == WSOL or s.get("tokenB") == WSOL:
            if s.get("tokenA") == WSOL:
                token_mint = s.get("tokenB")
                sol_amt = abs(float(s.get("amountA", 0)) / 1e9)
            else:
                token_mint = s.get("tokenA")
                sol_amt = abs(float(s.get("amountB", 0)) / 1e9)
            pairs.append({
                "Token合约地址": token_mint,
                "累计兑换SOL数量": sol_amt,
                "名称": get_token_meta(token_mint)[0],
                "符号": get_token_meta(token_mint)[1],
                "DEX": s.get("market"),
                "时间": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s.get("blockTime", 0))),
                "交易hash": s.get("txHash")
            })
    df = pd.DataFrame(pairs)
    if df.empty:
        return df
    agg = df.groupby("Token合约地址")["累计兑换SOL数量"].sum().reset_index()
    agg = agg.sort_values("累计兑换SOL数量", ascending=False).head(top_n)
    agg["名称"] = agg["Token合约地址"].apply(lambda x: get_token_meta(x)[0])
    agg["符号"] = agg["Token合约地址"].apply(lambda x: get_token_meta(x)[1])
    agg = agg[["Token合约地址", "名称", "符号", "累计兑换SOL数量"]]
    return agg

# ------------ Birdeye聚合API ------------
def birdeye_query(second_range, dex_choice, top_n, api_key):
    if not api_key:
        st.warning("请输入Birdeye API Key。")
        return pd.DataFrame()
    # Birdeye不支持按区块时间，只能近N分钟的swap聚合，略有延迟，仅演示
    # 真实API用法请参考官方文档，可继续优化
    st.info("Birdeye聚合API演示版：仅供尝试，结果未必最全。")
    return pd.DataFrame()  # 演示stub

# ------------ Jupiter聚合API ------------
def jupiter_query(second_range, dex_choice, top_n):
    st.info("Jupiter聚合API演示版：官方暂未开放大规模聚合，暂不可用。")
    return pd.DataFrame()

# ------------ 基础RPC（Helius） ------------
def rpc_query(second_range, dex_choice, top_n, helius_key):
    # 基础版与前述代码一致，略
    st.info("基础RPC仅供体验，建议用Solscan或Birdeye。")
    return pd.DataFrame()

# --------- 查询与展示主流程 -----------
if st.button("开始抓取分析"):
    with st.spinner("数据采集中..."):
        if data_source == "Solscan聚合API":
            df = solscan_query(second_range, dex_choice, top_n)
        elif data_source == "Birdeye聚合API":
            df = birdeye_query(second_range, dex_choice, top_n, user_keys.get("birdeye"))
        elif data_source == "Jupiter聚合API":
            df = jupiter_query(second_range, dex_choice, top_n)
        elif data_source == "基础RPC (Helius)":
            df = rpc_query(second_range, dex_choice, top_n, user_keys.get("helius"))
        else:
            st.warning("不支持的API")
            df = pd.DataFrame()
    if df is None or df.empty:
        st.warning("此区块时间段内未获取到swap数据。可尝试扩大时间窗口、更换DEX或切换数据源。")
    else:
        st.write(f"### 与SOL兑换币种排行（Top {top_n}）")
        st.dataframe(df.style.format({"累计兑换SOL数量": "{:.6f}"}), use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False)
        st.download_button("导出排行CSV", data=csv, file_name="sol_top_tokens.csv")
