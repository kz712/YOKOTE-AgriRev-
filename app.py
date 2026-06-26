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
    h2 { color: #1E40AF; font-size: 15pt; margin-top: 25px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 生産者グループ 出荷予定タイムライン")
st.markdown("Googleフォームから集計された出荷予定データをガントチャート形式でリアルタイムに表示します。")

# --- 1. データ読み込み関数 ---
@st.cache_data(ttl=300)
def load_data(source_url_or_path):
    try:
        df = pd.read_csv(source_url_or_path)
        df.columns = df.columns.str.strip()
        
        required_cols = ['生産者', '品種', '出荷開始予定日', '出荷終了予定日', '出荷予定ケース数']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"⚠️ スプレッドシートに以下の設問名が見つかりません: {missing_cols}")
            return pd.DataFrame()
        
        df['出荷開始日'] = pd.to_datetime(df['出荷開始予定日'], errors='coerce')
        df['出荷終了日'] = pd.to_datetime(df['出荷終了予定日'], errors='coerce')
        df = df.dropna(subset=['出荷開始日', '出荷終了日'])
        df['出荷予定ケース数'] = pd.to_numeric(df['出荷予定ケース数'], errors='coerce').fillna(0)
        
        # バーの中に「品種」と「ケース数」を2行で表示するためのラベル列を作成
        df['バー表示ラベル'] = df.apply(
            lambda row: f"{row['品種']}<br>({int(row['出荷予定ケース数']):,}ケース)", axis=1
        )
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return pd.DataFrame()

# GoogleスプレッドシートのCSV公開URL
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT8-Wda-QgU2r6VAcpAdZB6oqft1qV0dYk18_SorDMHPNF5BrMsmjkY3T3v-I1i2R1D7A5yy6RL87_w/pub?gid=878960407&single=true&output=csv"

# --- 手動更新ボタン ---
st.sidebar.header("🔄 システム操作")
if st.sidebar.button("最新の情報に更新", use_container_width=True):
    st.cache_data.clear()
    st.toast("スプレッドシートから最新データを取得しました！", icon="🔄")

df = load_data(CSV_URL)

if not df.empty:
    # --- 2. サイドバー（フィルター機能） ---
    st.sidebar.header("🔍 表示条件で絞り込み")
    all_producers = ["すべて"] + sorted(df['生産者'].unique().tolist())
    selected_producer = st.sidebar.selectbox("生産者を選択", all_producers)
    
    all_varieties = ["すべて"] + sorted(df['品種'].unique().tolist())
    selected_variety = st.sidebar.selectbox("品種を選択", all_varieties)
    
    filtered_df = df.copy()
    if selected_producer != "すべて":
        filtered_df = filtered_df[filtered_df['生産者'] == selected_producer]
    if selected_variety != "すべて":
        filtered_df = filtered_df[filtered_df['品種'] == selected_variety]

    # --- 3. 集計サマリー（KPI） ---
    st.subheader("📊 現在の集計サマリー")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="登録総出荷件数", value=f"{len(filtered_df)} 件")
    with col2:
        st.metric(label="合計出荷予定ケース数", value=f"{int(filtered_df['出荷予定ケース数'].sum()):,} ケース")
    with col3:
        st.metric(label="現在の稼働生産者数", value=f"{filtered_df['生産者'].nunique()} 名")

    # --- 4. ガントチャート（タイムライン）描画 ---
    st.subheader("📅 出荷スケジュール（ガントチャート）")
    
    if not filtered_df.empty and filtered_df['出荷開始日'].notna().any():
        try:
            filtered_df['出荷開始日'] = pd.to_datetime(filtered_df['出荷開始日'])
            filtered_df['出荷終了日'] = pd.to_datetime(filtered_df['出荷終了日'])

            fig = px.timeline(
                filtered_df, 
                x_start="出荷開始日", 
                x_end="出荷終了日", 
                y="生産者",
                color="品種", 
                text="バー表示ラベル",
                hover_data={   
                    "出荷予定ケース数": ":,d", 
                    "出荷開始予定日": True, 
                    "出荷終了予定日": True,
                    "生産者": False,
                    "バー表示ラベル": False
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
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as plotly_err:
            st.warning("📊 グラフの自動描画に失敗しました。データ形式を確認してください。")
            st.info(f"技術詳細: {plotly_err}")
    else:
        st.warning("条件に一致する有効な出荷予定データがありません。")

    # --- 🌟 改良：2つのデータテーブルを縦並びに配置 ---
    
    # 5. 明細データ一覧テーブル
    st.subheader("📋 出荷予定データ明細（一覧）")
    display_df = filtered_df[['生産者', '品種', '出荷開始予定日', '出荷終了予定日', '出荷予定ケース数']].sort_values(by='出荷開始予定日')
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # 6. 品種毎のケース数合計集計
    st.subheader("📈 品種毎の出荷予定ケース数合計")
    if not filtered_df.empty:
        summary_variety = filtered_df.groupby('品種')['出荷予定ケース数'].sum().reset_index()
        summary_variety = summary_variety.sort_values(by='出荷予定ケース数', ascending=False)
        summary_variety.columns = ['品種', '合計出荷ケース数']
        
        st.dataframe(
            summary_variety,
            column_config={
                "合計出荷ケース数": st.column_config.ProgressColumn(
                    "合計出荷ケース数（ケース）",
                    help="品種ごとの合計予定数量です",
                    format="%d",
                    min_value=0,
                    max_value=int(summary_variety['合計出荷ケース数'].max()) if not summary_variety.empty else 100,
                )
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("集計するデータがありません。")

else:
    st.info("表示するデータがありません。Googleフォームからの回答を待機しています。")
