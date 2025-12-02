import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials # ← 新しい認証ライブラリ
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import datetime
import time
from geopy.geocoders import Nominatim
import os
import altair as alt
import urllib.parse

# ====================
# 🛑 フォルダID
# ====================
DRIVE_FOLDER_ID = "1Tv342SterGVXuOwiH-aKyO4tOW6OPjgp"

# ====================
# 設定
# ====================
st.set_page_config(
    page_title="VOYAGO",
    page_icon="icon.png", 
    layout="wide"
)

# ====================
# リスト定義
# ====================
PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県",
    "山形県", "福島県", "茨城県", "栃木県", "群馬県",
    "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県",
    "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県",
    "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
    "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県",
    "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県",
    "鹿児島県", "沖縄県"
]

GENRES = [
    "テーマパーク", "動物園・水族館", "神社・仏閣",
    "城・史跡", "美術館・博物館", "公園・庭園",
    "山・高原", "海・ビーチ", "温泉・スパ",
    "夜景・タワー", "買い物", "道の駅",
    "キャンプ", "グルメ", "その他"
]

TAGS = [
    "雨の日", "晴れの日", "デート", "子連れ",
    "静か", "賑やか", "コスパ良", "贅沢",
    "景色良", "アクセス良", "アクセス悪", "アクティブ",
    "大人向け"
]

# ====================
# データベース接続（最新方式）
# ====================
@st.cache_resource
def get_services():
    # スコープも最新のものに変更
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    if os.path.exists('secret.json'):
        creds = Credentials.from_service_account_file(
            'secret.json', scopes=scopes
        )
    elif "gcp_service_account" in st.secrets:
        try:
            key_dict = dict(st.secrets["gcp_service_account"])
            # 改行コードの修正
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
            creds = Credentials.from_service_account_info(
                key_dict, scopes=scopes
            )
        except Exception as e:
            st.error(f"認証エラー: {e}")
            st.stop()
    else:
        st.error("鍵が見つかりません。")
        st.stop()

    gspread_client = gspread.authorize(creds)
    sheet = gspread_client.open("travel_db")
    drive_service = build('drive', 'v3', credentials=creds)
    return sheet, drive_service

try:
    sheet_file, drive_service = get_services()
    vote_sheet = sheet_file.sheet1
    
    try:
        photo_sheet = sheet_file.worksheet("photos")
    except:
        photo_sheet = sheet_file.add_worksheet(
            title="photos", rows="100", cols="3"
        )
        photo_sheet.append_row(["観光地", "画像URL", "投稿日時"])

    try:
        master_sheet = sheet_file.worksheet("spots_master")
    except:
        master_sheet = sheet_file.add_worksheet(
            title="spots_master", rows="100", cols="3"
        )
        master_sheet.append_row(["観光地", "都道府県", "ジャンル"])

except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# ====================
# データ読み込み
# ====================
master_records = master_sheet.get_all_records()
if master_records:
    df_master = pd.DataFrame(master_records)
else:
    cols = ["観光地", "都道府県", "ジャンル"]
    df_master = pd.DataFrame(columns=cols)

vote_records = vote_sheet.get_all_records()
if vote_records:
    df_vote = pd.DataFrame(vote_records)
else:
    cols = ["観光地", "特徴", "投票数"]
    df_vote = pd.DataFrame(columns=cols)

photo_records = photo_sheet.get_all_records()
if photo_records:
    df_photo = pd.DataFrame(photo_records)
else:
    cols = ["観光地", "画像URL"]
    df_photo = pd.DataFrame(columns=cols)


# ====================
# サイドバー
# ====================
with st.sidebar:
    st.title("🔍 VOYAGO Menu")
    
    st.caption("▼ 観光地を探す")
    search_mode = st.radio(
        "モード",
        ["都道府県", "ジャンル", "キーワード"]
    )
    filtered_spots = []

    if search_mode == "都道府県":
        p_list = df_master["都道府県"].unique().tolist()
        available_prefs = sorted(p_list)
        
        if available_prefs:
            selected_pref = st.selectbox("県を選択", available_prefs)
            mask = df_master["都道府県"] == selected_pref
            filtered_spots = df_master[mask]["観光地"].tolist()
        else:
            st.warning("データなし")

    elif search_mode == "ジャンル":
        g_list = df_master["ジャンル"].unique().tolist()
        available_genres = sorted(g_list)
        
        if available_genres:
            selected_genre = st.selectbox(
                "ジャンル選択", available_genres
            )
            mask = df_master["ジャンル"] == selected_genre
            filtered_spots = df_master[mask]["観光地"].tolist()
        else:
            st.warning("データなし")

    else:
        keyword = st.text_input("キーワード")
        if keyword:
            mask = df_master["観光地"].str.contains(
                keyword, na=False
            )
            filtered_spots = df_master[mask]["観光地"].tolist()

    st.markdown("---")
    
    st.caption("▼ 場所を追加")
    with st.expander("➕ 登録フォーム"):
        with st.form("reg_form"):
            new_name = st.text_input("名前")
            new_pref = st.selectbox("県", PREFECTURES)
            new_genre = st.selectbox("ジャンル", GENRES)
            
            if st.form_submit_button("登録"):
                if new_name and new_pref and new_genre:
                    existing = df_master["観光地"].tolist()
                    if new_name in existing:
                        st.error("登録済み")
                    else:
                        master_sheet.append_row(
                            [new_name, new_pref, new_genre]
                        )
                        st.success("完了！")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("未入力あり")


# ====================
# メイン画面
# ====================
st.markdown(
    "# VOYAGO <small>(ボヤゴ)</small>",
    unsafe_allow_html=True
)
st.markdown("##### みんなで作る観光マップ")

with st.expander("❓ VOYAGOについて"):
    st.markdown(
        """
        <small style="color:gray;">
        みんなの投票と写真で作る、新しい観光地マップです。<br>
        <b>📝 タグ評価</b>： 特徴をボタンで投票<br>
        <b>📸 アルバム</b>： リアルな写真を共有<br>
        <b>🗺️ 登録</b>： 隠れた名所を自由に登録
        </small>
        """,
        unsafe_allow_html=True
    )

st.write("---")

if len(filtered_spots) > 0:
    spot_name = st.selectbox(
        "📍 観光地を選択してください",
        filtered_spots
    )
    
    # Googleマップ
    encoded_name = urllib.parse.quote(spot_name)
    gmap_url = f"https://www.google.com/maps/search/?api=1&query={encoded_name}"
    
    st.markdown(
        f"""
        <a href="{gmap_url}" target="_blank" style="
            display: inline-block;
            background-color: #4285F4;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
            margin-bottom: 10px;
        ">📍 Googleマップで見る</a>
        """,
        unsafe_allow_html=True
    )

    # 住所
    try:
        ua = f"voyago_{int(time.time())}"
        geolocator = Nominatim(user_agent=ua, timeout=5)
        location = geolocator.geocode(spot_name)
        if location:
            st.caption(f"住所目安: {location.address}")
    except:
        pass
    
    st.write("---")

    col_main, col_side = st.columns([2, 1])

    # === 左側 ===
    with col_main:
        # 写真一覧
        mask = df_photo["観光地"] == spot_name
        imgs = df_photo[mask]["画像URL"].tolist()
        
        if imgs:
            cols = st.columns(3)
            for i, url in enumerate(imgs):
                with cols[i % 3]:
                    st.image(
                        url, use_container_width=True
                    )
        else:
            st.info("写真なし")

        # 投稿フォーム
        with st.expander("📸 写真を追加する"):
            tab1, tab2 = st.tabs(["📁 アップロード", "🔗 URL貼り付け"])
            
            with tab1:
                up_file = st.file_uploader(
                    "画像選択", type=['png', 'jpg', 'jpeg']
                )
                if up_file and st.button("アップロード"):
                    with st.spinner("送信中..."):
                        fname = f"{spot_name}_{up_file.name}"
                        meta = {
                            'name': fname,
                            'parents': [DRIVE_FOLDER_ID]
                        }
                        media = MediaIoBaseUpload(
                            up_file, mimetype=up_file.type
                        )
                        f = drive_service.files().create(
                            body=meta,
                            media_body=media,
                            fields='id, webContentLink'
                        ).execute()
                        
                        now = datetime.datetime.now().strftime(
                            '%Y-%m-%d %H:%M'
                        )
                        photo_sheet.append_row([
                            spot_name,
                            f.get('webContentLink'),
                            now
                        ])
                        st.success("完了！")
                        st.rerun()

            with tab2:
                img_url_input = st.text_input("URL入力")
                if img_url_input and st.button("登録"):
                    now = datetime.datetime.now().strftime(
                        '%Y-%m-%d %H:%M'
                    )
                    photo_sheet.append_row([
                        spot_name,
                        img_url_input,
                        now
                    ])
                    st.success("完了！")
                    st.rerun()

    # === 右側 ===
    with col_side:
        st.subheader("📊 評価")
        mask_v = df_vote["観光地"] == spot_name
        current_data = df_vote[mask_v]
        
        if not current_data.empty:
            c = alt.Chart(current_data).mark_bar().encode(
                x=alt.X('特徴', axis=alt.Axis(labelAngle=0)),
                y='投票数',
                tooltip=['特徴', '投票数']
            )
            st.altair_chart(c, use_container_width=True)
        else:
            st.info("投票なし")
        
        st.write("👍 特徴に投票")
        
        if 'voted_history' not in st.session_state:
            st.session_state.voted_history = []

        b_cols = st.columns(2)
        
        for i, tag in enumerate(TAGS):
            with b_cols[i % 2]:
                v_key = f"{spot_name}_{tag}"
                has_voted = v_key in st.session_state.voted_history
                
                if st.button(tag, key=v_key, disabled=has_voted):
                    mask_tag = (df_vote["観光地"] == spot_name) & \
                               (df_vote["特徴"] == tag)
                    existing = df_vote[mask_tag]
                    
                    if not existing.empty:
                        r_idx = existing.index[0] + 2
                        vote_sheet.update_cell(
                            r_idx, 3,
                            int(existing.iloc[0]["投票数"] + 1)
                        )
                    else:
                        vote_sheet.append_row(
                            [spot_name, tag, 1]
                        )
                    
                    st.session_state.voted_history.append(v_key)
                    st.rerun()

else:
    st.info("👈 左側のメニューから検索するか、新規登録してください。")
    try:
        st.image("icon.png", width=100)
    except:
        pass
