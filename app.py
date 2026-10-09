import base64
import io
from PIL import Image
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Tafsela Inventory Management System", layout="wide"
)

# 2. تعديل الـ CSS لتكبير الخطوط وتنسيق الأزرار
st.markdown(
    """
<style>
    h1, h1 span, h1 div {
        font-size: 60px !important;
        color: white !important; 
        font-weight: bold !important;
        line-height: 1.1 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    h2, h3, h4, h5, h6 {
        color: #5ce1d6 !important; 
    }
    label, p, .st-emotion-cache-1wivap2 {
        color: white !important; 
        font-size: 26px !important; 
        font-weight: bold !important;
    }
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {
        color: #5ce1d6 !important;
        font-size: 22px !important; 
    }
    input, textarea, select, .stSelectbox div {
        font-size: 24px !important; 
    }
    .stNumberInput input {
        font-size: 24px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 3. عرض اللوجو والعنوان
col_left, col_logo, col_title, col_right = st.columns(
    [1, 1.2, 5.8, 1], vertical_alignment="center"
)

with col_logo:
    try:
        st.image("logi.png", use_container_width=True)
    except Exception:
        st.write("📦")

with col_title:
    st.markdown(
        "<h1>Tafsela Inventory Management System</h1>", unsafe_allow_html=True
    )

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_image_base64(uploaded_file):
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.thumbnail((200, 200))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    return ""

try:
    # قراءة المفتاح السري وتنظيفه
    raw_key = st.secrets["private_key"]
    clean_key = raw_key.replace("\\n", "\n").strip()

    secret_dict = {
        "type": st.secrets["type"],
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        "private_key": clean_key,
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"],
        "token_uri": st.secrets["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"],
    }
    
    credentials = Credentials.from_service_account_info(
        secret_dict, scopes=scopes
    )
    gc = gspread.authorize(credentials)
    sh = gc.open("My_Inventory")
    worksheet = sh.sheet1

    data = worksheet.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()

    col1, col2 = st.columns([3, 1])

    with col1:
        # ترتيب العنوان ومربع البحث وزر البحث جنب بعض
        header_col, search_input_col, search_btn_col = st.columns([2, 1.5, 0.5], vertical_alignment="center")
        
        with header_col:
            st.markdown(
                '<div style="color: white; font-size: 30px; font-weight: bold;">📋 Available Inventory</div>',
                unsafe_allow_html=True,
            )
        with search_input_col:
            # مربع إدخال البحث
            search_term = st.text_input("Search", label_visibility="collapsed", placeholder="🔍 ابحث باسم المنتج...")
        with search_btn_col:
            # زر البحث
            search_btn = st.button("Search", use_container_width=True)

        # فلترة البيانات بناءً على كلمة البحث
        display_df = df.copy()
        if not display_df.empty and search_term:
            # فلترة تتجاهل حالة الأحرف (كابيتال/سمول)
            display_df = display_df[display_df["Item_Name"].astype(str).str.contains(search_term, case=False, na=False)]

        if not display_df.empty:
            html_table = (
                '<table style="width:100%; text-align:center; border-collapse:'
                ' collapse; font-size: 24px; margin-top: 15px;">'
            )
            headers = [
                "Item ID", "Item Name", "Image", "Quantity", "Purchase Price", 
                "Selling Price", "Purchase Location", "Shipping Cost", "Notes"
            ]
