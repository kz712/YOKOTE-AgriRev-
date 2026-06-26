import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from datetime import datetime

# ページ基本設定
st.set_page_config(
    page_title="YOKOTE AgriRev 出荷カレンダー",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 全体のフォント・デザイン調整
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans JP", sans-serif;
    }
    .main .block-container { padding-top: 2rem; }
    h1 { color: #1E3A8A; font-size: 20pt; font-weight: bold; margin-bottom: 20px; }
    h2 { color: #1E40AF; font-size: 14pt; margin-top: 25px; margin-bottom: 10px; }
    .fc-event-title { font-weight: bold; font-size: 9pt !important; }
    </style>
""", unsafe_allow_html=True)

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
        
        df['出荷開始日'] = pd.to_datetime(df['出荷開始予定日'], errors='coerce').dt.date
        df['出荷終了日_元データ'] = pd.to_datetime(df['出荷終了予定日'], errors='coerce').dt.date
        
        df = df.dropna(subset=['出荷開始日', '出荷終了日_元データ'])
        df['出荷予定ケース数'] = pd.to_numeric(df['出荷予定ケース数'], errors='coerce').fillna(0)
        
        # カレンダーで最終日までしっかり色付けするための処理
        df['出荷終了日_カレンダー用'] = pd.to_datetime(df['出荷終了日_元データ']) + pd.Timedelta(days=1)
        
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return pd.DataFrame()

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT8-Wda-QgU2r6VAcpAdZB6oqft1qV0dYk18_SorDMHPNF5BrMsmjkY3T3v-I1i2R1D7A5yy6RL87_w/pub?gid=878960407&single=true&output=csv"

df = load_data(CSV_URL)

# --- 2. サイドバー（フィルター・システム操作） ---
st.sidebar.title("メニュー")
st.sidebar.markdown("---")
st.sidebar.header("🔍 表示条件で絞り込み")

if not df.empty:
    all_producers = ["すべて"] + sorted(df['生産者'].unique().tolist())
    selected_producer = st.sidebar.selectbox("生産者を選択", all_producers)
    
    all_varieties = ["すべて"] + sorted(df['品種'].unique().tolist())
    selected_variety = st.sidebar.selectbox("品種を選択", all_varieties)
    
    filtered_df = df.copy()
    if selected_producer != "すべて":
        filtered_df = filtered_df[filtered_df['生産者'] == selected_producer]
    if selected_variety != "すべて":
        filtered_df = filtered_df[filtered_df['品種'] == selected_variety]

    if st.sidebar.button("最新の情報に更新", use_container_width=True):
        st.cache_data.clear()
        st.toast("スプレッドシートから最新データを取得しました！", icon="🔄")

    # --- 3. メイン画面の構築 ---
    st.title("📦 YOKOTE AgriRev 出荷予定カレンダー")
    st.markdown("左上の「**＞**」ボタンから、生産者や品種での絞り込みが可能です。")

    main_tab1, main_tab2 = st.tabs(["📅 月間カレンダー", "📊 出荷データ明細・集計"])

    # --- 【タブ1】月間カレンダー表示 ---
    with main_tab1:
        colors = ["#1E40AF", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#14B8A6", "#F97316", "#64748B"]
        unique_varieties = sorted(filtered_df['品種'].unique().tolist())
        variety_color_map = {v: colors[i % len(colors)] for i, v in enumerate(unique_varieties)}

        calendar_events = []
        for idx, row in filtered_df.iterrows():
            event_title = f"{row['生産者']} : {row['品種']} ({int(row['出荷予定ケース数']):,}c)"
            calendar_events.append({
                "title": event_title,
                "start": row['出荷開始日'].isoformat(),
                "end": row['出荷終了日_カレンダー用'].strftime('%Y-%m-%dT%H:%M:%S'),
                "backgroundColor": variety_color_map.get(row['品種'], "#3182ce"),
                "borderColor": variety_color_map.get(row['品種'], "#3182ce"),
                "allDay": True
            })

        # 🌟 変更点：出荷開始日から終了日までの「すべての期間」から、存在する月を重複なく確実に抽出
        months_set = set()
        for idx, row in filtered_df.iterrows():
            # 各データの開始月と終了月を両方リストに追加
            months_set.add(row['出荷開始日'].strftime('%Y-%m'))
            months_set.add(row['出荷終了日_元データ'].strftime('%Y-%m'))
        all_months = sorted(list(months_set))

        if all_months:
            st.markdown("### 🗓️ 表示する月を選択")
            month_tabs = st.tabs([f"{m.split('-')[1]}月 ({m.split('-')[0]}年)" for m in all_months])
            
            for i, m_tab in enumerate(month_tabs):
                with m_tab:
                    target_month = all_months[i]
                    initial_date_str = f"{target_month}-01"
                    
                    calendar_options = {
                        "initialView": "dayGridMonth",
                        "initialDate": initial_date_str,
                        "headerToolbar": {
                            "left": "",       
                            "center": "title",
                            "right": ""
                        },
                        "locale": "ja",       
                        "firstDay": 0,        
                        "height": 650,        
                        "editable": False,
                        "selectable": False
                    }
                    
                    calendar(
                        events=calendar_events,
                        options=calendar_options,
                        key=f"calendar_{target_month}"
                    )
        else:
            st.warning("カレンダーに表示可能な有効な日付データがありません。")

    # --- 【タブ2】出荷データ明細・集計サマリー ---
    with main_tab2:
        st.subheader("📊 現在の集計サマリー")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="登録総出荷件数", value=f"{len(filtered_df)} 件")
        with col2:
            st.metric(label="合計出荷予定ケース数", value=f"{int(filtered_df['出荷予定ケース数'].sum()):,} ケース")
        with col3:
            st.metric(label="現在の稼働生産者数", value=f"{filtered_df['生産者'].nunique()} 名")
            
        st.subheader("📋 出荷予定データ明細（一覧）")
        display_df = filtered_df[['生産者', '品種', '出荷開始予定日', '出荷終了予定日', '出荷予定ケース数']].sort_values(by='出荷開始予定日')
        st.dataframe(display_df, use_container_width=True, hide_index=True)

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
