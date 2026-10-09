import base64
import io
import time  # <-- ضفنا المكتبة دي عشان تأخير الريفرش ثانية واحدة
from PIL import Image
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Tafsela Inventory Management System", layout="wide"
)

# 2. تعديل الـ CSS الشامل (بحجم خطوط أصغر قليلاً لتكون مريحة كأنك عاملة زووم 80%)
st.markdown(
    """
<style>
    /* ----- الخطوط الأساسية للشاشات الكبيرة ----- */
    h1, h1 span, h1 div { font-size: 48px !important; color: white !important; font-weight: bold !important; line-height: 1.1 !important; margin: 0 !important; }
    h2, h3, h4, h5, h6 { color: #5ce1d6 !important; }
    
    label, p, .st-emotion-cache-1wivap2, .st-emotion-cache-1y4p8pa { color: white !important; font-size: 20px !important; font-weight: bold !important; }
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span { color: #5ce1d6 !important; font-size: 18px !important; }
    input, textarea, .stNumberInput input { font-size: 18px !important; }
    
    /* حل نهائي وجذري للقوائم المنسدلة (Dropdowns) */
    .stSelectbox div[data-baseweb="select"] > div { font-size: 18px !important; }
    div[role="listbox"] ul li, ul[data-baseweb="menu"] li { font-size: 18px !important; padding: 12px !important; }
    
    /* أزرار الحفظ والحذف */
    .stButton button, .stButton button p { font-size: 18px !important; font-weight: bold !important; }

    /* ----- التجاوب (Responsiveness) للشاشات الصغيرة والموبايل ----- */
    @media (max-width: 800px) {
        h1, h1 span, h1 div { font-size: 30px !important; text-align: center !important; }
        label, p, .st-emotion-cache-1wivap2, .st-emotion-cache-1y4p8pa { font-size: 16px !important; }
        input, textarea, .stNumberInput input { font-size: 16px !important; }
        .stSelectbox div[data-baseweb="select"] > div { font-size: 16px !important; }
        div[role="listbox"] ul li, ul[data-baseweb="menu"] li { font-size: 16px !important; padding: 10px !important; }
        .stButton button, .stButton button p { font-size: 16px !important; }
        button[data-baseweb="tab"] p, button[data-baseweb="tab"] span { font-size: 16px !important; }
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
                '<div style="color: white; font-size: 24px; font-weight: bold;">📋 Available Inventory</div>',
                unsafe_allow_html=True,
            )
        with search_input_col:
            search_term = st.text_input("Search", label_visibility="collapsed", placeholder="🔍 ابحث باسم المنتج...")
        with search_btn_col:
            search_btn = st.button("Search", use_container_width=True)

        display_df = df.copy()
        if not display_df.empty and search_term:
            display_df = display_df[display_df["Item_Name"].astype(str).str.contains(search_term, case=False, na=False)]

        if not display_df.empty:
            html_table = (
                '<div style="width: 100%; overflow-x: auto;">'
                '<table style="width:100%; min-width: 1000px; text-align:center; border-collapse:'
                ' collapse; font-size: 16px; margin-top: 15px;">'
            )
            headers = [
                "Item ID", "Item Name", "Image", "Quantity", "Purchase Price", 
                "Selling Price", "Purchase Location", "Shipping Cost", "Notes"
            ]

            html_table += "<tr>"
            for h in headers:
                html_table += (
                    f'<th style="color: #5ce1d6; border-bottom: 2px solid #5ce1d6;'
                    f' padding: 12px; text-align: center;">{h}</th>'
                )
            html_table += "</tr>"

            for _, row in display_df.iterrows():
                html_table += "<tr>"
                cols_data = [
                    row.get("Item_ID", ""), row.get("Item_Name", ""), row.get("Image_URL", ""),
                    row.get("Quantity", ""), row.get("Purchase_Price", ""), row.get("Selling_Price", ""),
                    row.get("Purchase_Location", ""), row.get("Shipping_Cost", ""), row.get("Notes", ""),
                ]

                for i, val in enumerate(cols_data):
                    if i == 2 and str(val).startswith("data:image"):
                        html_table += (
                            f'<td style="border-bottom: 1px solid #333; padding: 12px;'
                            f' text-align: center;"><img src="{val}" width="60"' 
                            ' style="border-radius: 5px; display: block; margin: 0 auto;"></td>'
                        )
                    else:
                        html_table += (
                            f'<td style="color: white; border-bottom: 1px solid #333;'
                            f' padding: 12px; text-align: center;">{val}</td>'
                        )
                html_table += "</tr>"
            html_table += "</table></div>"

            st.markdown(html_table, unsafe_allow_html=True)
        else:
            if search_term:
                st.warning(f"لا توجد منتجات تطابق كلمة البحث: '{search_term}'")
            else:
                st.info("No items found in the inventory.")

    with col2:
        base_locations = ["Techno Print Cairo", "Supplier A", "Factory B"]
        
        if not df.empty and "Purchase_Location" in df.columns:
            sheet_locations = df["Purchase_Location"].dropna().astype(str).unique().tolist()
            for loc in sheet_locations:
                if loc and loc not in base_locations and loc != "أخرى (إضافة جديد)...":
                    base_locations.append(loc)
        
        base_locations.append("أخرى (إضافة جديد)...")
        
        tab_add, tab_edit = st.tabs(["➕ Add New", "✏️ Edit Existing"])

        # ====== تبويب الإضافة ======
        with tab_add:
            with st.form("add_item_form"):
                item_name = st.text_input("Item Name")
                uploaded_image = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
                quantity = st.number_input("Quantity", min_value=0, step=1)
                purchase_price = st.number_input("Purchase Price", min_value=0.0, step=1.0)
                selling_price = st.number_input("Selling Price", min_value=0.0, step=1.0)
                
                selected_loc_add = st.selectbox("Purchase Location", base_locations)
                new_loc_add = ""
                if selected_loc_add == "أخرى (إضافة جديد)...":
                    new_loc_add = st.text_input("Enter New Purchase Location")
                    
                shipping_cost = st.number_input("Shipping Cost", min_value=0.0, step=1.0)
                notes = st.text_area("Notes")

                submitted_add = st.form_submit_button("Add to Inventory")
                if submitted_add:
                    if item_name == "":
                        st.error("Please enter the Item Name!")
                    else:
                        final_loc_add = new_loc_add if selected_loc_add == "أخرى (إضافة جديد)..." and new_loc_add else selected_loc_add
                        image_data_string = get_image_base64(uploaded_image) if uploaded_image else ""
                        
                        next_id = len(df) + 1 if not df.empty else 1
                        
                        new_row = [
                            next_id, item_name, image_data_string, quantity, purchase_price,
                            selling_price, final_loc_add, shipping_cost, notes
                        ]
                        worksheet.append_row(new_row)
                        st.success("Added Successfully! Refreshing...")
                        time.sleep(1) # استراحة ثانية واحدة
                        st.rerun()    # تحديث وتفريغ الخانات أوتوماتيكياً

        # ====== تبويب التعديل والحذف ======
        with tab_edit:
            if not df.empty and "Item_Name" in df.columns:
                item_names_list = df["Item_Name"].dropna().astype(str).tolist()
                item
