import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ページ基本設定
st.set_page_config(
    page_title="出荷予定ガントチャートシステム",
    layout="wide",
    initial_sidebar_state="expanded"
)

# デザインの微調整
st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; }
    h1 { color: #1E3A8A; font-size: 22pt; font-weight: bold; margin-bottom: 20px; }
    h2 { color: #1E40AF; font-size: 15pt; margin-top: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 生産者グループ 出荷予定タイムライン")
st.markdown("Googleフォームから集計された出荷予定データをガントチャート形式でリアルタイムに表示します。")

# --- 1. データ読み込み関数 ---
@st.cache_data(ttl=300)  # 5分間キャッシュ
def load_data(source_url_or_path):
    try:
        df = pd.read_csv(source_url_or_path)
        
        # カラム名の前後の不要な空白を削除
        df.columns = df.columns.str.strip()
        
        # 変更後の設問名に合わせた日付型への変換
        df['出荷開始日'] = pd.to_datetime(df['出荷開始予定日'])
        df['出荷終了日'] = pd.to_datetime(df['出荷終了予定日'])
        
        # 出荷ケース数を数値型に変換（エラーは0に置換）
        df['出荷予定ケース数'] = pd.to_numeric(df['出荷予定ケース数'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました。設定を確認してください: {e}")
        return pd.DataFrame()

# --- 【本番運用時の設定】 ---
# スプレッドシートの「ウェブに公開」から取得したCSVのURLをここに貼り付けます
# CSV_URL = "https://docs.google.com/spreadsheets/d/e/YOUR_ID/pub?output=csv"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT8-Wda-QgU2r6VAcpAdZB6oqft1qV0dYk18_SorDMHPNF5BrMsmjkY3T3v-I1i2R1D7A5yy6RL87_w/pub?gid=878960407&single=true&output=csv"

# デモ用データのカラム名も新しい設問名に更新して上書き（検証用）
import os
if not os.path.exists("app_src"):
    os.makedirs("app_src")
demo_data = pd.DataFrame({
    "タイムスタンプ": ["2026/06/20 10:00:00", "2026/06/21 11:30:00", "2026/06/22 09:15:00", "2026/06/23 14:00:00"],
    "生産者": ["田中農園", "鈴木ファーム", "佐藤ファーム", "田中農園"],
    "品種": ["羅皇", "金色羅皇", "羅皇", "マダーボール"],
    "出荷開始予定日": ["2026-07-05", "2026-07-10", "2026-07-01", "2026-07-15"],
    "出荷終了予定日": ["2026-07-20", "2026-07-25", "2026-07-15", "2026-07-30"],
    "出荷予定ケース数": [500, 300, 400, 200]
})
demo_data.to_csv("app_src/demo_shipping_data.csv", index=False)

df = load_data(CSV_URL)

if not df.empty:
    # --- 2. サイドバー（新設問名に対応） ---
    st.sidebar.header("🔍 表示条件で絞り込み")
    
    # 生産者で絞り込み
    all_producers = ["すべて"] + sorted(df['生産者'].unique().tolist())
    selected_producer = st.sidebar.selectbox("生産者を選択", all_producers)
    
    # 品種で絞り込み
    all_varieties = ["すべて"] + sorted(df['品種'].unique().tolist())
    selected_variety = st.sidebar.selectbox("品種を選択", all_varieties)
    
    # フィルタリング
    filtered_df = df.copy()
    if selected_producer != "すべて":
        filtered_df = filtered_df[filtered_df['生産者'] == selected_producer]
    if selected_variety != "すべて":
        filtered_df = filtered_df[filtered_df['品種'] == selected_variety]

    # --- 3. 集計サマリー（新設問名に対応） ---
    st.subheader("📊 現在の集計サマリー")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="登録総出荷件数", value=f"{len(filtered_df)} 件")
    with col2:
        st.metric(label="合計出荷予定ケース数", value=f"{int(filtered_df['出荷予定ケース数'].sum()):,} ケース")
    with col3:
        st.metric(label="現在の稼働生産者数", value=f"{filtered_df['生産者'].nunique()} 名")

    # --- 4. ガントチャート（新設問名に対応） ---
    st.subheader("📅 出荷スケジュール（ガントチャート）")
    
    if not filtered_df.empty:
        fig = px.timeline(
            filtered_df, 
            start="出荷開始日", 
            end="出荷終了日", 
            y="生産者",  # 縦軸を「生産者」に
            color="品種", 
            text="品種",  
            hover_data={   
                "出荷予定ケース数": ":,d", 
                "出荷開始予定日": True, 
                "出荷終了予定日": True,
                "生産者": False
            },
            labels={"品種": "栽培品種"},
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        
        fig.update_yaxes(autorange="reversed")  
        fig.update_layout(
            xaxis_title="日付",
            yaxis_title="生産者名",
            height=450,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=dict(size=12)
        )
        fig.update_traces(textposition='inside', insidetextanchor='center')
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("条件に一致する出荷予定データがありません。")

    # --- 5. 明細データ一覧テーブル ---
    st.subheader("📋 出荷予定データ明細（一覧）")
    display_df = filtered_df[['生産者', '品種', '出荷開始予定日', '出荷終了予定日', '出荷予定ケース数']].sort_values(by='出荷開始予定日')
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.info("表示するデータがありません。Googleフォームからの回答を待機しています。")
