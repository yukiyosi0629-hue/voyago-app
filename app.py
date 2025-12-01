# (前略... ライブラリインポート部分は同じ)

# ====================
# データベース接続（エラー詳細表示版）
# ====================
@st.cache_resource
def get_services():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # パソコンの場合
    if os.path.exists('secret.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'secret.json', scope
        )
    # クラウドの場合
    elif "gcp_service_account" in st.secrets:
        try:
            # Secretsから文字列を取得
            json_str = st.secrets["gcp_service_account"]["json_content"]
            # JSONとして読み込む
            key_dict = json.loads(json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                key_dict, scope
            )
        except Exception as e:
            # ★ここで本当のエラーを表示します
            st.error(f"Secrets読み込みエラー: {e}")
            st.stop()
    else:
        st.error("鍵が見つかりません。")
        st.stop()

    gspread_client = gspread.authorize(creds)
    sheet = gspread_client.open("travel_db")
    drive_service = build('drive', 'v3', credentials=creds)
    return sheet, drive_service

# (以下略... 他の部分は変更なし)
