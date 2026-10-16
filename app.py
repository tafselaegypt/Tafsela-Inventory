import base64
import io
import time
import datetime
import hashlib
from PIL import Image
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# ==========================================
# Helper Functions
# ==========================================
def get_col_letter(col_idx):
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

def hash_password(password):
    return hashlib.sha256(str(password).encode('utf-8')).hexdigest()

def get_image_base64(uploaded_file):
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        image.thumbnail((300, 300))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=75)
        return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    return ""

def load_data_safe(raw_values):
    if not raw_values or len(raw_values) == 0:
        return pd.DataFrame(), []
    headers = [str(h).strip() if str(h).strip() != "" else f"Unnamed_{i}" for i, h in enumerate(raw_values[0])]
    safe_data = []
    for row in raw_values[1:]:
        if len(row) < len(headers):
            safe_data.append(row + [""] * (len(headers) - len(row)))
        else:
            safe_data.append(row[:len(headers)])
    return pd.DataFrame(safe_data, columns=headers), headers

def ensure_worksheet(sh, title, default_headers):
    try:
        return sh.worksheet(title)
    except:
        ws = sh.add_worksheet(title=title, rows=1000, cols=max(10, len(default_headers)+2))
        ws.append_row(default_headers)
        return ws

# ==========================================
# Page Config & Session State
# ==========================================
st.set_page_config(page_title="Tafsela ERP System", layout="wide", initial_sidebar_state="expanded")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'app_mode' not in st.session_state: st.session_state.app_mode = "📦 المخزون الأساسي (الخامات)"
if 'dismissed_alerts' not in st.session_state: st.session_state.dismissed_alerts = []

# CSS Styling
st.markdown(
    """
<style>
    h1, h1 span, h1 div { font-size: 45px !important; color: white !important; font-weight: bold !important; line-height: 1.1 !important; margin: 0 !important; }
    h2, h3, h4, h5, h6 { color: #5ce1d6 !important; }
    label, p, .st-emotion-cache-1wivap2, .st-emotion-cache-1y4p8pa { color: white !important; font-size: 20px !important; font-weight: bold !important; }
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span { color: #5ce1d6 !important; font-size: 18px !important; }
    input, textarea, .stNumberInput input { font-size: 18px !important; }
    .stSelectbox div[data-baseweb="select"] > div { font-size: 18px !important; }
    div[role="listbox"] ul li, ul[data-baseweb="menu"] li { font-size: 18px !important; padding: 12px !important; }
    .stButton button, .stButton button p { font-size: 18px !important; font-weight: bold !important; }
    [data-testid="stSidebar"] { background-color: #1e1e2f; }
    .stRadio div { font-size: 18px !important; font-weight: bold !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# Database Connection & Caching
# ==========================================
@st.cache_resource(show_spinner=False)
def init_connection():
    raw_key = st.secrets["private_key"]
    clean_key = raw_key.replace("\\n", "\n").strip()
    secret_dict = {
        "type": st.secrets["type"], "project_id": st.secrets["project_id"], "private_key_id": st.secrets["private_key_id"],
        "private_key": clean_key, "client_email": st.secrets["client_email"], "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"], "token_uri": st.secrets["token_uri"], "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"],
    }
    credentials = Credentials.from_service_account_info(secret_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    gc = gspread.authorize(credentials)
    return gc.open("My_Inventory")

try:
    sh = init_connection()
except Exception as e:
    st.error(f"Database Connection Error: {e}")
    st.stop()

@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_data():
    worksheets = {ws.title: ws for ws in sh.worksheets()}
    def get_or_create(title, headers):
        if title in worksheets:
            return worksheets[title].get_all_values()
        else:
            new_ws = sh.add_worksheet(title=title, rows=1000, cols=max(10, len(headers)+2))
            new_ws.append_row(headers)
            return new_ws.get_all_values()

    return {
        "users": get_or_create("Users", ["Email", "Password", "Status", "Role"]),
        "inventory": sh.get_worksheet(0).get_all_values(),
        "supplies": get_or_create("Supplies", ["Supply_ID", "Supply_Name", "Image_URL", "Quantity", "Cost_Price", "Supplier_Name", "Min_Threshold", "Notes"]),
        "invoices": get_or_create("Invoices", ["Invoice_ID", "Date", "Supplier_Location", "Total_Amount", "Image_URL", "Notes"]),
        "products": get_or_create("Products", ["Product_ID", "Product_Name", "Image_URL", "Quantity", "Display_Location", "Cost_Price", "Selling_Price", "Profit", "Is_Sold", "Sale_Date", "Customer_Name", "Notes"])
    }

all_data = fetch_all_data()

# ==========================================
# Authentication (Login / Register) 
# ==========================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logi.png", use_container_width=True)
        except: st.write("📦 Tafsela Logo")
        st.markdown("<h2 style='text-align: center;'>Tafsela System - Gateway</h2>", unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab_login:
            with st.form("login_form"):
                l_email = st.text_input("Email")
                l_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    if l_email and l_pass:
                        df_users, _ = load_data_safe(all_data["users"])
                        if not df_users.empty and 'Email' in df_users.columns and l_email in df_users['Email'].values:
                            user_row = df_users[df_users['Email'] == l_email].iloc[0]
                            if str(user_row['Password']) == hash_password(l_pass):
                                if user_row['Status'] == 'Approved':
                                    st.session_state.logged_in = True
                                    st.session_state.user_email = l_email
                                    st.session_state.is_admin = (user_row['Role'] == 'Admin')
                                    st.session_state.dismissed_alerts = [] 
                                    st.success("Login successful! Redirecting...")
                                    time.sleep(1); st.rerun()
                                else: st.warning("Account Pending. Please wait for Admin approval.")
                            else: st.error("Incorrect Password!")
                        else: st.error("Email not registered.")
                    else: st.error("Please enter Email and Password.")

        with tab_register:
            with st.form("register_form"):
                r_email = st.text_input("Email")
                r_pass = st.text_input("Password", type="password")
                r_pass2 = st.text_input("Confirm Password", type="password")
                if st.form_submit_button("Register"):
                    if r_email and r_pass and r_pass == r_pass2:
                        df_users, _ = load_data_safe(all_data["users"])
                        existing_emails = df_users['Email'].tolist() if not df_users.empty and 'Email' in df_users.columns else []
                        
                        if r_email in existing_emails: st.error("Email already registered!")
                        else:
                            if r_email.lower().strip() == "nadineali2006@gmail.com":
                                status, role = "Approved", "Admin"
                                st.success("Admin recognized. Approved automatically!")
                            else:
                                status, role = "Pending", "User"
                                st.success("Registration successful. Waiting for Admin approval.")
                            sh.worksheet("Users").append_row([r_email, hash_password(r_pass), status, role])
                            st.cache_data.clear()
                            time.sleep(2); st.rerun()
                    else: st.error("Please fill all fields correctly and ensure passwords match.")

# ==========================================
# Main Application (After Login)
# ==========================================
else:
    # --- Auto-Fix Headers in Google Sheets ---
    # تحديث الكود للتركيز على Purchase_Location كعمود المورد
    inv_raw = all_data["inventory"]
    if inv_raw and len(inv_raw) > 0:
        inv_headers = [str(h).strip() for h in inv_raw[0]]
        missing_inv = [h for h in ["Purchase_Location", "Services_Cost", "Min_Threshold"] if h not in inv_headers]
        if missing_inv:
            new_inv_headers = inv_headers + missing_inv
            sh.get_worksheet(0).update(values=[new_inv_headers], range_name="A1")
            st.cache_data.clear()
            st.rerun()

    sup_raw = all_data["supplies"]
    if sup_raw and len(sup_raw) > 0:
        sup_headers = [str(h).strip() for h in sup_raw[0]]
        if "Min_Threshold" not in sup_headers:
            new_sup_headers = sup_headers + ["Min_Threshold"]
            sh.worksheet("Supplies").update(values=[new_sup_headers], range_name="A1")
            st.cache_data.clear()
            st.rerun()

    with st.sidebar:
        try: st.image("logi.png", use_container_width=True)
        except: st.write("📦")
        st.markdown(f"<p style='text-align: center; font-size:14px; color:#aaa;'>Welcome: {st.session_state.user_email}</p><hr>", unsafe_allow_html=True)
        
        menu_options = [
            "📦 المخزون الأساسي (الخامات)", 
            "📊 لوحة الإحصائيات (Dashboard)", 
            "🛒 مستلزمات وإضافات (تغليف)", 
            "🛍️ المنتجات والمبيعات",
            "🧾 أرشيف فواتير المشتريات" 
        ]
        if st.session_state.is_admin: menu_options.append("⚙️ Admin Panel")
            
        st.radio("Main Menu:", menu_options, key="app_mode")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.session_state.is_admin = False
            st.session_state.dismissed_alerts = []
            st.rerun()

    # --- تجهيز الداتا من الذاكرة ---
    df, clean_headers = load_data_safe(all_data["inventory"])
    if not df.empty:
        df["Min_Threshold"] = pd.to_numeric(df.get("Min_Threshold", 5), errors='coerce').fillna(5)
        for col in ["Item_ID", "Quantity", "Purchase_Price", "Selling_Price", "Shipping_Cost", "Services_Cost"]: 
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df_supplies, head_supplies = load_data_safe(all_data["supplies"])
    if not df_supplies.empty:
        df_supplies["Min_Threshold"] = pd.to_numeric(df_supplies.get("Min_Threshold", 10), errors='coerce').fillna(10)
        for col in ["Supply_ID", "Quantity", "Cost_Price"]:
            if col in df_supplies.columns: df_supplies[col] = pd.to_numeric(df_supplies[col], errors='coerce').fillna(0)

    df_invoices, head_invoices = load_data_safe(all_data["invoices"])
    if not df_invoices.empty:
        for col in ["Invoice_ID", "Total_Amount"]:
            if col in df_invoices.columns: df_invoices[col] = pd.to_numeric(df_invoices[col], errors='coerce').fillna(0)

    # ------------------------------------------
    # إدارة المخزون (الخامات الأساسية)
    # ------------------------------------------
    if st.session_state.app_mode == "📦 المخزون الأساسي (الخامات)":
        st.markdown("<h1>📦 الخامات والمخزون الأساسي</h1><hr>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])

        with col1:
            h_col, s_col, b_col = st.columns([2, 1.5, 0.5], vertical_alignment="center")
            with h_col: st.markdown('<div style="color: white; font-size: 24px; font-weight: bold;">📋 الخامات المتاحة</div>', unsafe_allow_html=True)
            with s_col: search_term = st.text_input("Search", label_visibility="collapsed", placeholder="🔍 ابحث...", key="inv_s")
            with b_col: st.button("Search", use_container_width=True, key="inv_b")

            display_df = df.copy()
            if not display_df.empty and "Item_Name" in display_df.columns and search_term:
                display_df = display_df[display_df["Item_Name"].astype(str).str.contains(search_term, case=False, na=False)]

            if not display_df.empty and "Item_Name" in display_df.columns:
                html_table = '<div style="width: 100%; overflow-x: auto;"><table style="width:100%; min-width: 1200px; text-align:center; border-collapse: collapse; font-size: 16px; margin-top: 15px;">'
                headers = ["ID", "Name", "Image", "Qty", "Cost", "Sell Price", "Supplier", "Min Alert", "Total Cost"]
                html_table += "<tr>" + "".join([f'<th style="color: #5ce1d6; border-bottom: 2px solid #5ce1d6; padding: 12px;">{h}</th>' for h in headers]) + "</tr>"

                for _, row in display_df.iterrows():
                    html_table += "<tr>"
                    p_price, s_cost = row.get("Purchase_Price", 0), row.get("Services_Cost", 0)
                    min_t = row.get("Min_Threshold", 5)
                    # تم ربط عمود Supplier بالداتا الموجودة في Purchase_Location
                    cols_data = [
                        row.get("Item_ID", ""), row.get("Item_Name", ""), row.get("Image_URL", ""),
                        row.get("Quantity", ""), p_price, row.get("Selling_Price", ""),
                        row.get("Purchase_Location", ""), min_t, f'<span style="color:#ffcc00; font-weight:bold;">{float(p_price) + float(s_cost)}</span>'
                    ]
                    for i, val in enumerate(cols_data):
                        if i == 2 and str(val).startswith("data:image"):
                            html_table += f'<td style="border-bottom: 1px solid #333; padding: 12px;"><img src="{val}" width="50" style="border-radius: 5px;"></td>'
                        else: html_table += f'<td style="color: white; border-bottom: 1px solid #333; padding: 12px;">{val}</td>'
                    html_table += "</tr>"
                html_table += "</table></div>"
                st.markdown(html_table, unsafe_allow_html=True)
            else: st.info("No items found.")

        with col2:
            tab_add, tab_edit = st.tabs(["➕ Add Item", "✏️ Edit Item"])
            
            # مسح البيانات الوهمية تماماً وسحب الأسماء من الداتا فقط
            base_suppliers = []
            if not df.empty and "Purchase_Location" in df.columns:
                for s in df["Purchase_Location"].dropna().astype(str).unique():
                    if s and s.strip() != "" and s not in base_suppliers and s != "مورد جديد...": base_suppliers.append(s)
            base_suppliers.append("مورد جديد...")

            with tab_add:
                with st.form("add_inv_form", clear_on_submit=True):
                    i_name = st.text_input("اسم الخامة")
                    i_img = st.file_uploader("صورة", type=["jpg", "png"])
                    i_qty = st.number_input("الكمية", min_value=0, step=1)
                    sup_sel = st.selectbox("المورد (Supplier)", base_suppliers)
                    new_sup = st.text_input("اسم المورد الجديد") if sup_sel == "مورد جديد..." else ""
                    p_price = st.number_input("سعر الشراء الأساسي", min_value=0.0, step=1.0)
                    serv_cost = st.number_input("تكلفة خدمات إضافية", min_value=0.0, step=1.0)
                    s_price = st.number_input("سعر البيع المتوقع", min_value=0.0, step=1.0)
                    m_thresh = st.number_input("الحد الأدنى للتنبيه", min_value=0, step=1, value=5)
                    colors, notes = st.text_input("الألوان"), st.text_area("ملاحظات")
                    if st.form_submit_button("إضافة للمخزن"):
                        if i_name:
                            new_row_dict = {
                                "Item_ID": len(df) + 1 if not df.empty else 1, "Item_Name": i_name, "Image_URL": get_image_base64(i_img),
                                "Quantity": i_qty, "Purchase_Price": p_price, "Selling_Price": s_price,
                                "Purchase_Location": new_sup if sup_sel == "مورد جديد..." else sup_sel, 
                                "Services_Cost": serv_cost, "Min_Threshold": m_thresh, "Colors": colors, "Notes": notes
                            }
                            sh.get_worksheet(0).update(values=[[new_row_dict.get(h, "") for h in clean_headers]], range_name=f"A{len(all_data['inventory']) + 1}")
                            st.cache_data.clear()
                            st.success("تم الإضافة بنجاح!"); time.sleep(1); st.rerun()

            with tab_edit:
                if not df.empty and "Item_Name" in df.columns:
                    names_list = [n for n in df["Item_Name"].dropna().astype(str).tolist() if str(n).strip() != ""]
                    if names_list:
                        sel_name = st.selectbox("اختر للتعديل", names_list)
                        c_row = df[df["Item_Name"].astype(str) == str(sel_name)].iloc[0]
                        hid_id, c_sup = str(c_row.get("Item_ID", "")), str(c_row.get("Purchase_Location", ""))
                        sup_idx = base_suppliers.index(c_sup) if c_sup in base_suppliers else 0

                        with st.form("edit_inv_form", clear_on_submit=True):
                            e_name = st.text_input("اسم الخامة", value=str(c_row.get("Item_Name", "")))
                            e_img = st.file_uploader("صورة جديدة", type=["jpg", "png"])
                            e_qty = st.number_input("الكمية", min_value=0, step=1, value=int(c_row.get("Quantity", 0)))
                            e_sup_sel = st.selectbox("المورد", base_suppliers, index=sup_idx)
                            e_new_sup = st.text_input("اسم المورد الجديد") if e_sup_sel == "مورد جديد..." else ""
                            e_pprice = st.number_input("سعر الشراء", min_value=0.0, step=1.0, value=float(c_row.get("Purchase_Price", 0.0)))
                            e_scost = st.number_input("خدمات", min_value=0.0, step=1.0, value=float(c_row.get("Services_Cost", 0.0)))
                            e_sprice = st.number_input("سعر البيع", min_value=0.0, step=1.0, value=float(c_row.get("Selling_Price", 0.0)))
                            e_m_thresh = st.number_input("الحد الأدنى للتنبيه", min_value=0, step=1, value=int(c_row.get("Min_Threshold", 5)))
                            e_colors, e_notes = st.text_input("الألوان", value=str(c_row.get("Colors", ""))), st.text_area("ملاحظات", value=str(c_row.get("Notes", "")))
                            
                            c_b1, c_b2 = st.columns(2)
                            with c_b1: sub_e = st.form_submit_button("✏️ تحديث")
                            with c_b2: sub_d = st.form_submit_button("🗑️ حذف")

                        ws_inv = sh.get_worksheet(0)
                        cell = ws_inv.find(hid_id, in_column=clean_headers.index("Item_ID")+1) if "Item_ID" in clean_headers else ws_inv.find(hid_id, in_column=1)

                        if sub_e and cell:
                            up_dict = {
                                "Item_ID": hid_id, "Item_Name": e_name, "Image_URL": get_image_base64(e_img) if e_img else c_row.get("Image_URL", ""), 
                                "Quantity": e_qty, "Purchase_Price": e_pprice, "Selling_Price": e_sprice, 
                                "Purchase_Location": e_new_sup if e_sup_sel == "مورد جديد..." else e_sup_sel,
                                "Services_Cost": e_scost, "Min_Threshold": e_m_thresh, "Colors": e_colors, "Notes": e_notes
                            }
                            ws_inv.update(values=[[up_dict.get(h, str(c_row.get(h, ""))) for h in clean_headers]], range_name=f"A{cell.row}")
                            st.cache_data.clear()
                            st.success("تم التحديث!"); time.sleep(1); st.rerun()

                        if sub_d and cell:
                            ws_inv.delete_row(cell.row)
                            st.cache_data.clear()
                            st.success("تم الحذف!"); time.sleep(1); st.rerun()

    # ------------------------------------------
    # لوحة الإحصائيات (Dashboard)
    # ------------------------------------------
    elif st.session_state.app_mode == "📊 لوحة الإحصائيات (Dashboard)":
        st.markdown("<h1>📊 إحصائيات وأداء البيزنس</h1><hr>", unsafe_allow_html=True)
        df_p, _ = load_data_safe(all_data["products"])

        total_sales, total_profit, total_items_sold, total_expenses = 0, 0, 0, 0

        if not df_p.empty and "Is_Sold" in df_p.columns:
            df_p["Profit"] = pd.to_numeric(df_p.get("Profit", 0), errors='coerce').fillna(0)
            df_p["Selling_Price"] = pd.to_numeric(df_p.get("Selling_Price", 0), errors='coerce').fillna(0)
            total_sales = df_p[df_p["Is_Sold"] == "نعم"]["Selling_Price"].sum()
            total_profit = df_p[df_p["Is_Sold"] == "نعم"]["Profit"].sum()
            total_items_sold = len(df_p[df_p["Is_Sold"] == "نعم"])
            
        if not df_invoices.empty and "Total_Amount" in df_invoices.columns:
            total_expenses = df_invoices["Total_Amount"].sum()
            
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>💰 المبيعات</h3><h2 style='color:#5ce1d6;'>{total_sales} ج.م</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>📈 الأرباح</h3><h2 style='color:#00ff00;'>{total_profit} ج.م</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>💸 المصروفات</h3><h2 style='color:#ff4d4d;'>{total_expenses} ج.م</h2></div>", unsafe_allow_html=True)
        c4.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>🛍️ المنتجات</h3><h2 style='color:#ffcc00;'>{total_items_sold} قطعة</h2></div>", unsafe_allow_html=True)
        st.markdown("<br><hr>", unsafe_allow_html=True)
            
        st.markdown("<h3>⚠️ تنبيهات نواقص المخزن</h3>", unsafe_allow_html=True)
        
        total_alerts = 0
        displayed_alerts = 0

        if not df.empty:
            low_stock = df[df["Quantity"] <= df["Min_Threshold"]]
            for _, row in low_stock.iterrows():
                total_alerts += 1
                alert_key = f"inv_{row.get('Item_ID', _)}"
                if alert_key not in st.session_state.dismissed_alerts:
                    displayed_alerts += 1
                    col_alert, col_btn = st.columns([5, 1])
                    with col_alert:
                        st.error(f"🚨 خامة أساسية: **{row['Item_Name']}** - متبقي منها **{row['Quantity']}** قطع فقط! (الحد الأدنى: {int(row.get('Min_Threshold', 5))})")
                    with col_btn:
                        if st.button("❌ إخفاء", key=f"dismiss_{alert_key}"):
                            st.session_state.dismissed_alerts.append(alert_key)
                            st.rerun()
        
        if not df_supplies.empty:
            low_sup = df_supplies[df_supplies["Quantity"] <= df_supplies["Min_Threshold"]]
            for _, row in low_sup.iterrows():
                total_alerts += 1
                alert_key = f"sup_{row.get('Supply_ID', _)}"
                if alert_key not in st.session_state.dismissed_alerts:
                    displayed_alerts += 1
                    col_alert, col_btn = st.columns([5, 1])
                    with col_alert:
                        st.warning(f"⚠️ مستلزم إضافي: **{row['Supply_Name']}** - متبقي منها **{row['Quantity']}** فقط! (الحد الأدنى: {int(row.get('Min_Threshold', 10))})")
                    with col_btn:
                        if st.button("❌ إخفاء", key=f"dismiss_{alert_key}"):
                            st.session_state.dismissed_alerts.append(alert_key)
                            st.rerun()

        if total_alerts == 0:
            st.success("✅ المخزن ممتلئ (خامات ومستلزمات) ولا توجد أي نواقص.")
        elif displayed_alerts == 0 and total_alerts > 0:
            st.info(f"⚠️ يوجد عدد ({total_alerts}) تنبيهات للنواقص في المخزن، ولكن قمتِ بإخفائها مؤقتاً.")
            if st.button("🔄 إظهار التنبيهات المخفية"):
                st.session_state.dismissed_alerts = []
                st.rerun()

    # ------------------------------------------
    # أرشيف فواتير المشتريات (Invoices)
    # ------------------------------------------
    elif st.session_state.app_mode == "🧾 أرشيف فواتير المشتريات":
        st.markdown("<h1>🧾 أرشيف فواتير المشتريات</h1><hr>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown("### 🗂️ الفواتير المسجلة")
            if not df_invoices.empty:
                html_inv = '<div style="width: 100%; overflow-x: auto;"><table style="width:100%; min-width: 900px; text-align:center; border-collapse: collapse; font-size: 16px; margin-top: 15px;">'
                headers = ["ID", "التاريخ", "مكان الشراء (المورد)", "المبلغ الإجمالي", "صورة الفاتورة", "ملاحظات"]
                html_inv += "<tr>" + "".join([f'<th style="color: #5ce1d6; border-bottom: 2px solid #5ce1d6; padding: 12px;">{h}</th>' for h in headers]) + "</tr>"

                for _, row in df_invoices.iterrows():
                    html_inv += "<tr>"
                    cols_data = [
                        row.get("Invoice_ID", ""), row.get("Date", ""), row.get("Supplier_Location", ""),
                        row.get("Total_Amount", ""), row.get("Image_URL", ""), row.get("Notes", "")
                    ]
                    for i, val in enumerate(cols_data):
                        if i == 4 and str(val).startswith("data:image"):
                            html_inv += f'<td style="border-bottom: 1px solid #333; padding: 12px;"><img src="{val}" width="80" style="border-radius: 5px;"></td>'
                        else: html_inv += f'<td style="color: white; border-bottom: 1px solid #333; padding: 12px;">{val}</td>'
                    html_inv += "</tr>"
                html_inv += "</table></div>"
                st.markdown(html_inv, unsafe_allow_html=True)
            else: st.info("لا توجد فواتير مسجلة في الأرشيف.")

        with col2:
            ti_add, ti_edit = st.tabs(["➕ إضافة فاتورة", "✏️ تعديل/حذف"])
            with ti_add:
                with st.form("add_inv_doc_form", clear_on_submit=True):
                    inv_date = st.date_input("تاريخ الفاتورة", value=datetime.date.today())
                    inv_loc = st.text_input("مكان الشراء (اسم المكان/المورد)")
                    inv_amt = st.number_input("إجمالي الفاتورة (للحسابات)", min_value=0.0, step=1.0)
                    inv_img = st.file_uploader("رفع صورة الفاتورة (مهم)", type=["jpg", "png", "jpeg"])
                    inv_notes = st.text_area("تفاصيل / ملاحظات")
                    
                    if st.form_submit_button("💾 حفظ الفاتورة في الأرشيف"):
                        if inv_loc:
                            new_inv_dict = {
                                "Invoice_ID": len(df_invoices) + 1 if not df_invoices.empty else 1,
                                "Date": str(inv_date), "Supplier_Location": inv_loc, "Total_Amount": inv_amt,
                                "Image_URL": get_image_base64(inv_img) if inv_img else "", "Notes": inv_notes
                            }
                            sh.worksheet("Invoices").update(values=[[new_inv_dict.get(h, "") for h in head_invoices]], range_name=f"A{len(all_data['invoices']) + 1}")
                            st.cache_data.clear()
                            st.success("تم أرشفة الفاتورة بنجاح!"); time.sleep(1); st.rerun()
                        else: st.error("يرجى إدخال مكان الشراء على الأقل.")
                        
            with ti_edit:
                if not df_invoices.empty and "Supplier_Location" in df_invoices.columns:
                    inv_list = [f"[{r['Invoice_ID']}] {r['Supplier_Location']} - {r['Date']}" for _, r in df_invoices.iterrows() if str(r['Supplier_Location']).strip() != ""]
                    if inv_list:
                        sel_inv = st.selectbox("اختر الفاتورة:", inv_list)
                        inv_id_to_edit = sel_inv.split("]")[0].replace("[", "").strip()
                        c_inv_row = df_invoices[df_invoices["Invoice_ID"].astype(str) == inv_id_to_edit].iloc[0]
                        
                        try: saved_date = datetime.datetime.strptime(str(c_inv_row.get("Date", "")), "%Y-%m-%d").date()
                        except: saved_date = datetime.date.today()

                        with st.form("edit_inv_doc_form", clear_on_submit=True):
                            e_inv_date = st.date_input("تاريخ الفاتورة", value=saved_date)
                            e_inv_loc = st.text_input("مكان الشراء", value=str(c_inv_row.get("Supplier_Location", "")))
                            e_inv_amt = st.number_input("إجمالي الفاتورة", min_value=0.0, step=1.0, value=float(c_inv_row.get("Total_Amount", 0.0)))
                            e_inv_img = st.file_uploader("صورة جديدة (اتركه فارغاً للاحتفاظ بالقديمة)", type=["jpg", "png", "jpeg"])
                            e_inv_notes = st.text_area("ملاحظات", value=str(c_inv_row.get("Notes", "")))
                            
                            c_ie1, c_ie2 = st.columns(2)
                            with c_ie1: sub_ie_e = st.form_submit_button("✏️ تحديث الفاتورة")
                            with c_ie2: sub_ie_d = st.form_submit_button("🗑️ حذف الفاتورة")
                            
                        ws_invs = sh.worksheet("Invoices")
                        cell_inv = ws_invs.find(inv_id_to_edit, in_column=head_invoices.index("Invoice_ID")+1) if "Invoice_ID" in head_invoices else ws_invs.find(inv_id_to_edit, in_column=1)
                        
                        if sub_ie_e and cell_inv:
                            up_inv_dict = {
                                "Invoice_ID": inv_id_to_edit, "Date": str(e_inv_date), "Supplier_Location": e_inv_loc,
                                "Total_Amount": e_inv_amt, "Image_URL": get_image_base64(e_inv_img) if e_inv_img else str(c_inv_row.get("Image_URL", "")),
                                "Notes": e_inv_notes
                            }
                            ws_invs.update(values=[[up_inv_dict.get(h, str(c_inv_row.get(h, ""))) for h in head_invoices]], range_name=f"A{cell_inv.row}")
                            st.cache_data.clear()
                            st.success("تم تحديث بيانات الفاتورة!"); time.sleep(1); st.rerun()
                            
                        if sub_ie_d and cell_inv:
                            ws_invs.delete_row(cell_inv.row)
                            st.cache_data.clear()
                            st.success("
