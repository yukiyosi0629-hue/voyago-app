import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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
DRIVE_FOLDER_ID = "1aOyupGCVBxKFx4G58LjfzTH4KwCesx7E"

# ====================
# 設定
# ====================
st.set_page_config(
    page_title="VOYAGO",
    page_icon="icon.png", 
    layout="wide"
)

# CSS（文字サイズ調整）
st.markdown(
    """
    <style>
    .streamlit-expanderHeader p {
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True
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
# データベース接続
# ====================
@st.cache_resource
def get_services():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    if os.path.exists('secret.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'secret.json', scope
        )
    elif "gcp_service_account" in st.secrets:
        try:
            key_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in key_dict:
                pk = key_dict["private_key"]
                key_dict["private_key"] = pk.replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                key_dict, scope
            )
        except Exception as e:
            st.error(f"認証エラー:
