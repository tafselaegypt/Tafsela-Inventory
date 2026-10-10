import base64
import io
import time
import datetime
import hashlib
from PIL import Image
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import WorksheetNotFound
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
        image.thumbnail((300, 300)) # كبرت الحجم شوية عشان تفاصيل الفاتورة تبان
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

# ==========================================
# Page Config & Session State
# ==========================================
st.set_page_config(page_title="Tafsela ERP System", layout="wide", initial_sidebar_state="expanded")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'app_mode' not in st.session_state: st.session_state.app_mode = "📊 لوحة الإحصائيات (Dashboard)"

# CSS
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
# Database Connection
# ==========================================
try:
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
    sh = gc.open("My_Inventory")

    try: ws_users = sh.worksheet("Users")
    except WorksheetNotFound:
        ws_users = sh.add_worksheet(title="Users", rows=100, cols=4)
        ws_users.append_row(["Email", "Password", "Status", "Role"])
        
    if not ws_users.get_all_values():
        ws_users.append_row(["Email", "Password", "Status", "Role"])

except Exception as e:
    st.error(f"Database Connection Error: {e}")
    st.stop()

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
                        raw_users = ws_users.get_all_values()
                        df_users, _ = load_data_safe(raw_users)
                        if not df_users.empty and 'Email' in df_users.columns and l_email in df_users['Email'].values:
                            user_row = df_users[df_users['Email'] == l_email].iloc[0]
                            if str(user_row['Password']) == hash_password(l_pass):
                                if user_row['Status'] == 'Approved':
                                    st.session_state.logged_in = True
                                    st.session_state.user_email = l_email
                                    st.session_state.is_admin = (user_row['Role'] == 'Admin')
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
                        raw_users = ws_users.get_all_values()
                        df_users, _ = load_data_safe(raw_users)
                        existing_emails = df_users['Email'].tolist() if not df_users.empty and 'Email' in df_users.columns else []
                        
                        if r_email in existing_emails: st.error("Email already registered!")
                        else:
                            if r_email.lower().strip() == "nadineali2006@gmail.com":
                                status, role = "Approved", "Admin"
                                st.success("Admin recognized. Approved automatically!")
                            else:
                                status, role = "Pending", "User"
                                st.success("Registration successful. Waiting for Admin approval.")
                            ws_users.append_row([r_email, hash_password(r_pass), status, role])
                            time.sleep(2); st.rerun()
                    else: st.error("Please fill all fields correctly and ensure passwords match.")

# ==========================================
# Main Application (After Login)
# ==========================================
else:
    with st.sidebar:
        try: st.image("logi.png", use_container_width=True)
        except: st.write("📦")
        st.markdown(f"<p style='text-align: center; font-size:14px; color:#aaa;'>Welcome: {st.session_state.user_email}</p><hr>", unsafe_allow_html=True)
        
        menu_options = [
            "📊 لوحة الإحصائيات (Dashboard)", 
            "📦 المخزون الأساسي (الخامات)", 
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
            st.rerun()

    # --- تحميل داتا المخزون الأساسي ---
    worksheet = sh.sheet1
    raw_data = worksheet.get_all_values()
    df, clean_headers = load_data_safe(raw_data)
    if not df.empty:
        if "Supplier_Name" not in clean_headers: clean_headers.append("Supplier_Name")
        if "Services_Cost" not in clean_headers: clean_headers.append("Services_Cost")
        if "Min_Threshold" not in clean_headers: clean_headers.append("Min_Threshold")
        for col in ["Supplier_Name", "Services_Cost"]:
            if col not in df.columns: df[col] = ""
        if "Min_Threshold" not in df.columns: df["Min_Threshold"] = 5
        df["Min_Threshold"] = pd.to_numeric(df["Min_Threshold"], errors='coerce').fillna(5)
        for col in ["Item_ID", "Quantity", "Purchase_Price", "Selling_Price", "Shipping_Cost", "Services_Cost"]: 
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        clean_headers = ["Item_ID", "Item_Name", "Image_URL", "Quantity", "Purchase_Price", "Selling_Price", "Purchase_Location", "Shipping_Cost", "Supplier_Name", "Services_Cost", "Min_Threshold", "Colors", "Notes"]
        df = pd.DataFrame(columns=clean_headers)

    # --- تحميل داتا المستلزمات (Supplies) ---
    try: ws_supplies = sh.worksheet("Supplies")
    except WorksheetNotFound:
        ws_supplies = sh.add_worksheet(title="Supplies", rows=1000, cols=10)
        ws_supplies.append_row(["Supply_ID", "Supply_Name", "Image_URL", "Quantity", "Cost_Price", "Supplier_Name", "Min_Threshold", "Notes"])
        time.sleep(1); st.rerun()
    raw_supplies = ws_supplies.get_all_values()
    df_supplies, head_supplies = load_data_safe(raw_supplies)
    if not df_supplies.empty:
        for col in ["Supply_ID", "Quantity", "Cost_Price", "Min_Threshold"]:
            if col in df_supplies.columns: df_supplies[col] = pd.to_numeric(df_supplies[col], errors='coerce').fillna(0)
    else:
        head_supplies = ["Supply_ID", "Supply_Name", "Image_URL", "Quantity", "Cost_Price", "Supplier_Name", "Min_Threshold", "Notes"]
        df_supplies = pd.DataFrame(columns=head_supplies)

    # --- تحميل داتا الفواتير (Invoices) ---
    try: ws_invoices = sh.worksheet("Invoices")
    except WorksheetNotFound:
        ws_invoices = sh.add_worksheet(title="Invoices", rows=1000, cols=10)
        ws_invoices.append_row(["Invoice_ID", "Date", "Supplier_Location", "Total_Amount", "Image_URL", "Notes"])
        time.sleep(1); st.rerun()
    raw_invoices = ws_invoices.get_all_values()
    df_invoices, head_invoices = load_data_safe(raw_invoices)
    if not df_invoices.empty:
        for col in ["Invoice_ID", "Total_Amount"]:
            if col in df_invoices.columns: df_invoices[col] = pd.to_numeric(df_invoices[col], errors='coerce').fillna(0)
    else:
        head_invoices = ["Invoice_ID", "Date", "Supplier_Location", "Total_Amount", "Image_URL", "Notes"]
        df_invoices = pd.DataFrame(columns=head_invoices)

    # ------------------------------------------
    # لوحة الإحصائيات (Dashboard)
    # ------------------------------------------
    if st.session_state.app_mode == "📊 لوحة الإحصائيات (Dashboard)":
        st.markdown("<h1>📊 إحصائيات وأداء البيزنس</h1><hr>", unsafe_allow_html=True)
        try: ws_prod = sh.worksheet("Products"); raw_p = ws_prod.get_all_values()
        except: raw_p = []

        df_p, _ = load_data_safe(raw_p)

        total_sales = 0
        total_profit = 0
        total_items_sold = 0
        total_expenses = 0

        if not df_p.empty:
            df_p["Profit"] = pd.to_numeric(df_p["Profit"], errors='coerce').fillna(0)
            df_p["Selling_Price"] = pd.to_numeric(df_p["Selling_Price"], errors='coerce').fillna(0)
            total_sales = df_p[df_p["Is_Sold"] == "نعم"]["Selling_Price"].sum()
            total_profit = df_p[df_p["Is_Sold"] == "نعم"]["Profit"].sum()
            total_items_sold = len(df_p[df_p["Is_Sold"] == "نعم"])
            
        if not df_invoices.empty:
            total_expenses = df_invoices["Total_Amount"].sum()
            
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>💰 إجمالي المبيعات</h3><h2 style='color:#5ce1d6;'>{total_sales} ج.م</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>📈 صافي الأرباح</h3><h2 style='color:#00ff00;'>{total_profit} ج.م</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>💸 مصروفات (فواتير)</h3><h2 style='color:#ff4d4d;'>{total_expenses} ج.م</h2></div>", unsafe_allow_html=True)
        c4.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>🛍️ منتجات مباعة</h3><h2 style='color:#ffcc00;'>{total_items_sold} قطعة</h2></div>", unsafe_allow_html=True)
        st.markdown("<br><hr>", unsafe_allow_html=True)
            
        st.markdown("<h3>⚠️ تنبيهات نواقص المخزن</h3>", unsafe_allow_html=True)
        warnings_count = 0
        if not df.empty:
            low_stock = df[df["Quantity"] <= df["Min_Threshold"]]
            for _, row in low_stock.iterrows():
                warnings_count += 1
                st.error(f"🚨 خامة أساسية: **{row['Item_Name']}** - متبقي منها **{row['Quantity']}** قطع فقط! (الحد الأدنى: {int(row['Min_Threshold'])})")
        
        if not df_supplies.empty:
            low_sup = df_supplies[df_supplies["Quantity"] <= df_supplies["Min_Threshold"]]
            for _, row in low_sup.iterrows():
                warnings_count += 1
                st.warning(f"⚠️ مستلزم إضافي: **{row['Supply_Name']}** - متبقي منها **{row['Quantity']}** فقط! (الحد الأدنى: {int(row['Min_Threshold'])})")

        if warnings_count == 0:
            st.success("✅ المخزن ممتلئ (خامات ومستلزمات) ولا توجد نواقص خطيرة حالياً.")

    # ------------------------------------------
    # أرشيف فواتير المشتريات (Invoices - القسم الجديد)
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
                            html_inv += f'<td style="border-bottom: 1px solid #333; padding: 12px;"><img src="{val}" width="80" style="border-radius: 5px; cursor: pointer;"></td>'
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
                    inv_notes = st.text_area("تفاصيل / ملاحظات (أرقام أصناف، ضمان، إلخ)")
                    
                    if st.form_submit_button("💾 حفظ الفاتورة في الأرشيف"):
                        if inv_loc:
                            new_inv_dict = {
                                "Invoice_ID": len(df_invoices) + 1 if not df_invoices.empty else 1,
                                "Date": str(inv_date), "Supplier_Location": inv_loc, "Total_Amount": inv_amt,
                                "Image_URL": get_image_base64(inv_img) if inv_img else "", "Notes": inv_notes
                            }
                            ws_invoices.update(values=[[new_inv_dict.get(h, "") for h in head_invoices]], range_name=f"A{len(raw_invoices) + 1}")
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
                            
                        cell_inv = ws_invoices.find(inv_id_to_edit, in_column=head_invoices.index("Invoice_ID")+1) if "Invoice_ID" in head_invoices else ws_invoices.find(inv_id_to_edit, in_column=1)
                        if sub_ie_e and cell_inv:
                            up_inv_dict = {
                                "Invoice_ID": inv_id_to_edit, "Date": str(e_inv_date), "Supplier_Location": e_inv_loc,
                                "Total_Amount": e_inv_amt, "Image_URL": get_image_base64(e_inv_img) if e_inv_img else str(c_inv_row.get("Image_URL", "")),
                                "Notes": e_inv_notes
                            }
                            ws_invoices.update(values=[[up_inv_dict.get(h, str(c_inv_row.get(h, ""))) for h in head_invoices]], range_name=f"A{cell_inv.row}")
                            st.success("تم تحديث بيانات الفاتورة!"); time.sleep(1); st.rerun()
                            
                        if sub_ie_d and cell_inv:
                            ws_invoices.delete_row(cell_inv.row)
                            st.success("تم حذف الفاتورة!"); time.sleep(1); st.rerun()

    # ------------------------------------------
    # Admin Panel
    # ------------------------------------------
    elif st.session_state.app_mode == "⚙️ Admin Panel" and st.session_state.is_admin:
        st.markdown("<h1>⚙️ Admin Panel</h1><hr>", unsafe_allow_html=True)
        tab_users, tab_thresholds = st.tabs(["👥 User Management", "⚙️ إعدادات النواقص"])
        
        with tab_users:
            users_raw = ws_users.get_all_values()
            df_u, _ = load_data_safe(users_raw)
            if not df_u.empty and 'Status' in df_u.columns:
                pending_users = df_u[df_u['Status'] == 'Pending']
                if not pending_users.empty:
                    st.warning(f"There are ({len(pending_users)}) pending registration requests.")
                    for _, row in pending_users.iterrows():
                        st.write(f"📧 Email: **{row.get('Email', '')}**")
                        if st.button(f"✅ Approve", key=f"app_{row.get('Email', '')}"):
                            cell = ws_users.find(row.get('Email', ''), in_column=1)
                            if cell:
                                ws_users.update_cell(cell.row, 3, "Approved") 
                                st.success(f"Approved {row.get('Email', '')} successfully!")
                                time.sleep(1); st.rerun()
                        st.markdown("<hr>", unsafe_allow_html=True)
                else: st.success("No pending requests. All users are active.")
                st.markdown("### 👥 All Registered Users:")
                st.dataframe(df_u[['Email', 'Status', 'Role']], use_container_width=True)
            else: st.info("No registered users yet.")

        with tab_thresholds:
            st.markdown("### ⚠️ تحديد الحد الأدنى للخامات الأساسية")
            if not df.empty and "Item_Name" in df.columns:
                names_list = [n for n in df["Item_Name"].dropna().astype(str).tolist() if str(n).strip() != ""]
                if names_list:
                    sel_item_th = st.selectbox("اختر الخامة لتعديل الحد الأدنى:", names_list, key="admin_thresh_item")
                    c_row_th = df[df["Item_Name"].astype(str) == str(sel_item_th)].iloc[0]
                    hid_id_th = str(c_row_th.get("Item_ID", ""))
                    with st.form("thresh_form"):
                        new_thresh = st.number_input("الحد الأدنى للتنبيه", min_value=0, step=1, value=int(c_row_th.get("Min_Threshold", 5)))
                        if st.form_submit_button("💾 حفظ الإعدادات"):
                            cell_th = worksheet.find(hid_id_th, in_column=clean_headers.index("Item_ID")+1) if "Item_ID" in clean_headers else worksheet.find(hid_id_th, in_column=1)
                            if cell_th:
                                up_dict_th = c_row_th.to_dict()
                                up_dict_th["Min_Threshold"] = new_thresh
                                worksheet.update(values=[[up_dict_th.get(h, "") for h in clean_headers]], range_name=f"A{cell_th.row}")
                                st.success("تم الحفظ!"); time.sleep(1); st.rerun()
            else: st.info("لا توجد خامات.")

            st.markdown("<hr>### ⚠️ تحديد الحد الأدنى للمستلزمات والإضافات", unsafe_allow_html=True)
            if not df_supplies.empty and "Supply_Name" in df_supplies.columns:
                sup_names_list = [n for n in df_supplies["Supply_Name"].dropna().astype(str).tolist() if str(n).strip() != ""]
                if sup_names_list:
                    sel_sup_th = st.selectbox("اختر المستلزم لتعديل الحد الأدنى:", sup_names_list, key="admin_thresh_sup")
                    c_row_sth = df_supplies[df_supplies["Supply_Name"].astype(str) == str(sel_sup_th)].iloc[0]
                    hid_id_sth = str(c_row_sth.get("Supply_ID", ""))
                    with st.form("thresh_sup_form"):
                        new_s_thresh = st.number_input("الحد الأدنى للتنبيه", min_value=0, step=1, value=int(c_row_sth.get("Min_Threshold", 10)))
                        if st.form_submit_button("💾 حفظ الإعدادات للمستلزم"):
                            cell_sth = ws_supplies.find(hid_id_sth, in_column=head_supplies.index("Supply_ID")+1) if "Supply_ID" in head_supplies else ws_supplies.find(hid_id_sth, in_column=1)
                            if cell_sth:
                                up_dict_sth = c_row_sth.to_dict()
                                up_dict_sth["Min_Threshold"] = new_s_thresh
                                ws_supplies.update(values=[[up_dict_sth.get(h, "") for h in head_supplies]], range_name=f"A{cell_sth.row}")
                                st.success("تم الحفظ!"); time.sleep(1); st.rerun()
            else: st.info("لا توجد مستلزمات.")

    # ------------------------------------------
    # إدارة المخزون (الخامات الأساسية)
    # ------------------------------------------
    elif st.session_state.app_mode == "📦 المخزون الأساسي (الخامات)":
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
                headers = ["ID", "Name", "Image", "Qty", "Cost", "Sell Price", "Supplier", "Services/Acc", "Total Cost"]
                html_table += "<tr>" + "".join([f'<th style="color: #5ce1d6; border-bottom: 2px solid #5ce1d6; padding: 12px;">{h}</th>' for h in headers]) + "</tr>"

                for _, row in display_df.iterrows():
                    html_table += "<tr>"
                    p_price, s_cost = row.get("Purchase_Price", 0), row.get("Services_Cost", 0)
                    cols_data = [
                        row.get("Item_ID", ""), row.get("Item_Name", ""), row.get("Image_URL", ""),
                        row.get("Quantity", ""), p_price, row.get("Selling_Price", ""),
                        row.get("Supplier_Name", ""), s_cost, f'<span style="color:#ffcc00; font-weight:bold;">{float(p_price) + float(s_cost)}</span>'
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
            base_suppliers = ["محمود بلاستيك", "مكتبة الفنون"]
            if not df.empty and "Supplier_Name" in df.columns:
                for s in df["Supplier_Name"].dropna().astype(str).unique():
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
                    colors, notes = st.text_input("الألوان"), st.text_area("ملاحظات")
                    if st.form_submit_button("إضافة للمخزن"):
                        if i_name:
                            new_row_dict = {
                                "Item_ID": len(df) + 1 if not df.empty else 1, "Item_Name": i_name, "Image_URL": get_image_base64(i_img),
                                "Quantity": i_qty, "Purchase_Price": p_price, "Selling_Price": s_price,
                                "Supplier_Name": new_sup if sup_sel == "مورد جديد..." else sup_sel, 
                                "Services_Cost": serv_cost, "Min_Threshold": 5, "Colors": colors, "Notes": notes
                            }
                            worksheet.update(values=[[new_row_dict.get(h, "") for h in clean_headers]], range_name=f"A{len(raw_data) + 1}")
                            st.success("تم الإضافة!"); time.sleep(1); st.rerun()

            with tab_edit:
                if not df.empty and "Item_Name" in df.columns:
                    names_list = [n for n in df["Item_Name"].dropna().astype(str).tolist() if str(n).strip() != ""]
                    if names_list:
                        sel_name = st.selectbox("اختر للتعديل", names_list)
                        c_row = df[df["Item_Name"].astype(str) == str(sel_name)].iloc[0]
                        hid_id, c_sup = str(c_row.get("Item_ID", "")), str(c_row.get("Supplier_Name", ""))
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
                            e_colors, e_notes = st.text_input("الألوان", value=str(c_row.get("Colors", ""))), st.text_area("ملاحظات", value=str(c_row.get("Notes", "")))
                            
                            c_b1, c_b2 = st.columns(2)
                            with c_b1: sub_e = st.form_submit_button("✏️ تحديث")
                            with c_b2: sub_d = st.form_submit_button("🗑️ حذف")

                        cell = worksheet.find(hid_id, in_column=clean_headers.index("Item_ID")+1) if "Item_ID" in clean_headers else worksheet.find(hid_id, in_column=1)

                        if sub_e and cell:
                            up_dict = {
                                "Item_ID": hid_id, "Item_Name": e_name, "Image_URL": get_image_base64(e_img) if e_img else c_row.get("Image_URL", ""), 
                                "Quantity": e_qty, "Purchase_Price": e_pprice, "Selling_Price": e_sprice, 
                                "Supplier_Name": e_new_sup if e_sup_sel == "مورد جديد..." else e_sup_sel,
                                "Services_Cost": e_scost, "Min_Threshold": c_row.get("Min_Threshold", 5), "Colors": e_colors, "Notes": e_notes
                            }
                            worksheet.update(values=[[up_dict.get(h, str(c_row.get(h, ""))) for h in clean_headers]], range_name=f"A{cell.row}")
                            st.success("تم التحديث!"); time.sleep(1); st.rerun()

                        if sub_d and cell:
                            worksheet.delete_row(cell.row)
                            st.success("تم الحذف!"); time.sleep(1); st.rerun()

    # ------------------------------------------
    # إدارة المستلزمات الإضافية (Supplies)
    # ------------------------------------------
    elif st.session_state.app_mode == "🛒 مستلزمات وإضافات (تغليف)":
        st.markdown("<h1>🛒 المستلزمات (تغليف، حبر، دلايات)</h1><hr>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])

        with col1:
            h_col, s_col, b_col = st.columns([2, 1.5, 0.5], vertical_alignment="center")
            with h_col: st.markdown('<div style="color: white; font-size: 24px; font-weight: bold;">📋 المستلزمات المتاحة</div>', unsafe_allow_html=True)
            with s_col: search_sup = st.text_input("Search", label_visibility="collapsed", placeholder="🔍 ابحث...", key="sup_s")
            with b_col: st.button("Search", use_container_width=True, key="sup_b")

            disp_sup = df_supplies.copy()
            if not disp_sup.empty and "Supply_Name" in disp_sup.columns and search_sup:
                disp_sup = disp_sup[disp_sup["Supply_Name"].astype(str).str.contains(search_sup, case=False, na=False)]

            if not disp_sup.empty and "Supply_Name" in disp_sup.columns:
                html_sup = '<div style="width: 100%; overflow-x: auto;"><table style="width:100%; min-width: 1000px; text-align:center; border-collapse: collapse; font-size: 16px; margin-top: 15px;">'
                headers = ["ID", "Name", "Image", "Qty", "Cost", "Supplier", "Notes"]
                html_sup += "<tr>" + "".join([f'<th style="color: #5ce1d6; border-bottom: 2px solid #5ce1d6; padding: 12px;">{h}</th>' for h in headers]) + "</tr>"

                for _, row in disp_sup.iterrows():
                    html_sup += "<tr>"
                    cols_data = [
                        row.get("Supply_ID", ""), row.get("Supply_Name", ""), row.get("Image_URL", ""),
                        row.get("Quantity", ""), row.get("Cost_Price", ""), row.get("Supplier_Name", ""), row.get("Notes", "")
                    ]
                    for i, val in enumerate(cols_data):
                        if i == 2 and str(val).startswith("data:image"):
                            html_sup += f'<td style="border-bottom: 1px solid #333; padding: 12px;"><img src="{val}" width="50" style="border-radius: 5px;"></td>'
                        else: html_sup += f'<td style="color: white; border-bottom: 1px solid #333; padding: 12px;">{val}</td>'
                    html_sup += "</tr>"
                html_sup += "</table></div>"
                st.markdown(html_sup, unsafe_allow_html=True)
            else: st.info("لا توجد مستلزمات.")

        with col2:
            ts_add, ts_edit = st.tabs(["➕ Add Supply", "✏️ Edit Supply"])
            sup_vendors = ["مورد تغليف"]
            if not df_supplies.empty and "Supplier_Name" in df_supplies.columns:
                for s in df_supplies["Supplier_Name"].dropna().astype(str).unique():
                    if s and s.strip() != "" and s not in sup_vendors and s != "مورد جديد...": sup_vendors.append(s)
            sup_vendors.append("مورد جديد...")

            with ts_add:
                with st.form("add_sup_form", clear_on_submit=True):
                    s_name = st.text_input("اسم المستلزم (ورق، أكياس، حبر)")
                    s_img = st.file_uploader("صورة", type=["jpg", "png"], key="s_img")
                    s_qty = st.number_input("الكمية", min_value=0, step=1)
                    s_cost = st.number_input("التكلفة", min_value=0.0, step=1.0)
                    s_vend = st.selectbox("المورد", sup_vendors)
                    s_new_vend = st.text_input("مورد جديد") if s_vend == "مورد جديد..." else ""
                    s_notes = st.text_area("ملاحظات")
                    if st.form_submit_button("إضافة للمستلزمات"):
                        if s_name:
                            new_s_dict = {
                                "Supply_ID": len(df_supplies) + 1 if not df_supplies.empty else 1, "Supply_Name": s_name, 
                                "Image_URL": get_image_base64(s_img), "Quantity": s_qty, "Cost_Price": s_cost, 
                                "Supplier_Name": s_new_vend if s_vend == "مورد جديد..." else s_vend, 
                                "Min_Threshold": 10, "Notes": s_notes
                            }
                            ws_supplies.update(values=[[new_s_dict.get(h, "") for h in head_supplies]], range_name=f"A{len(raw_supplies) + 1}")
                            st.success("تم الإضافة!"); time.sleep(1); st.rerun()

            with ts_edit:
                if not df_supplies.empty and "Supply_Name" in df_supplies.columns:
                    s_names_list = [n for n in df_supplies["Supply_Name"].dropna().astype(str).tolist() if str(n).strip() != ""]
                    if s_names_list:
                        sel_s_name = st.selectbox("اختر للتعديل", s_names_list)
                        c_s_row = df_supplies[df_supplies["Supply_Name"].astype(str) == str(sel_s_name)].iloc[0]
                        hid_s_id = str(c_s_row.get("Supply_ID", ""))
                        
                        with st.form("edit_sup_form", clear_on_submit=True):
                            e_s_name = st.text_input("الاسم", value=str(c_s_row.get("Supply_Name", "")))
                            e_s_img = st.file_uploader("صورة جديدة", type=["jpg", "png"], key="es_img")
                            e_s_qty = st.number_input("الكمية", min_value=0, step=1, value=int(c_s_row.get("Quantity", 0)))
                            e_s_cost = st.number_input("التكلفة", min_value=0.0, step=1.0, value=float(c_s_row.get("Cost_Price", 0.0)))
                            e_s_notes = st.text_area("ملاحظات", value=str(c_s_row.get("Notes", "")))
                            
                            c_s1, c_s2 = st.columns(2)
                            with c_s1: sub_s_e = st.form_submit_button("✏️ تحديث")
                            with c_s2: sub_s_d = st.form_submit_button("🗑️ حذف")

                        cell_s = ws_supplies.find(hid_s_id, in_column=head_supplies.index("Supply_ID")+1) if "Supply_ID" in head_supplies else ws_supplies.find(hid_s_id, in_column=1)

                        if sub_s_e and cell_s:
                            up_s_dict = {
                                "Supply_ID": hid_s_id, "Supply_Name": e_s_name, "Image_URL": get_image_base64(e_s_img) if e_s_img else c_s_row.get("Image_URL", ""), 
                                "Quantity": e_s_qty, "Cost_Price": e_s_cost, "Supplier_Name": c_s_row.get("Supplier_Name", ""),
                                "Min_Threshold": c_s_row.get("Min_Threshold", 10), "Notes": e_s_notes
                            }
                            ws_supplies.update(values=[[up_s_dict.get(h, str(c_s_row.get(h, ""))) for h in head_supplies]], range_name=f"A{cell_s.row}")
                            st.success("تم التحديث!"); time.sleep(1); st.rerun()

                        if sub_s_d and cell_s:
                            ws_supplies.delete_row(cell_s.row)
                            st.success("تم الحذف!"); time.sleep(1); st.rerun()

    # ------------------------------------------
    # المنتجات والمبيعات (Products)
    # ------------------------------------------
    elif st.session_state.app_mode == "🛍️ المنتجات والمبيعات":
        st.markdown("<h1>🛍️ سجل المنتجات والمبيعات</h1><hr>", unsafe_allow_html=True)
        try: ws_prod = sh.worksheet("Products")
        except WorksheetNotFound:
            ws_prod = sh.add_worksheet(title="Products", rows=1000, cols=20)
            ws_prod.append_row(["Product_ID", "Product_Name", "Image_URL", "Quantity", "Display_Location", "Cost_Price", "Selling_Price", "Profit", "Is_Sold", "Sale_Date", "Customer_Name", "Notes"])
            time.sleep(1); st.rerun()

        raw_p = ws_prod.get_all_values()
        df_p, c_head_p = load_data_safe(raw_p)
        
        if not df_p.empty:
            for c in ["Product_ID", "Quantity", "Cost_Price", "Selling_Price", "Profit"]: 
                if c in df_p.columns: df_p[c] = pd.to_numeric(df_p[c], errors='coerce').fillna(0)

        cp1, cp2 = st.columns([3, 1])
        with cp1:
            st.markdown("### 🏷️ المنتجات المعروضة والمباعة")
            if not df_p.empty:
                st.dataframe(df_p[["Product_Name", "Quantity", "Cost_Price", "Selling_Price", "Profit", "Is_Sold", "Customer_Name"]], use_container_width=True)
            else: st.info("لا توجد منتجات.")

        with cp2:
            tab_p_add, tab_p_edit = st.tabs(["➕ إضافة منتج", "✏️ تعديل منتج"])

            with tab_p_add:
                st.markdown("<div style='background-color:#2a2a3f; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                is_from_inv = st.checkbox("🔗 سحب من الخامات/المستلزمات؟", key="add_p_is_inv")
                used_qty = {}
                if is_from_inv:
                    all_opts = []
                    if not df.empty:
                        all_opts += [f"[خامة-{r['Item_ID']}] {r['Item_Name']} (متاح: {r['Quantity']})" for _, r in df.iterrows() if str(r['Item_Name']).strip() != ""]
                    if not df_supplies.empty:
                        all_opts += [f"[تغليف-{r['Supply_ID']}] {r['Supply_Name']} (متاح: {r['Quantity']})" for _, r in df_supplies.iterrows() if str(r['Supply_Name']).strip() != ""]
                    
                    if all_opts:
                        sel_inv = st.multiselect("اختر كل ما تم استهلاكه:", all_opts)
                        for item in sel_inv:
                            used_qty[item] = st.number_input(f"سحب من {item.split(']')[1].split('(')[0]}:", min_value=1, step=1)
                    else: st.warning("لا يوجد شيء في المخازن للسحب منه.")
                st.markdown("</div><br>", unsafe_allow_html=True)

                is_sold = st.checkbox("هل تم البيع؟", key="add_p_sold")
                with st.form("add_p_form", clear_on_submit=True):
                    p_name = st.text_input("اسم المنتج")
                    p_img = st.file_uploader("صورة المنتج", type=["jpg", "jpeg", "png"])
                    p_qty = st.number_input("الكمية", min_value=0, step=1)
                    p_loc = st.text_input("مكان العرض")
                    p_cost = st.number_input("التكلفة", min_value=0.0, step=1.0)
                    p_sell = st.number_input("سعر البيع", min_value=0.0, step=1.0)
                    
                    st.markdown("<small style='color:#ccc;'>بيانات البيع (اختياري)</small>", unsafe_allow_html=True)
                    p_date = st.date_input("تاريخ البيع", value=None)
                    p_cust = st.text_input("اسم العميل")
                    p_notes = st.text_area("ملاحظات")
                    
                    if st.form_submit_button("إضافة المنتج"):
                        if p_name:
                            profit = float(p_sell) - float(p_cost)
                            p_dict = {
                                "Product_ID": len(df_p)+1, "Product_Name": p_name, "Image_URL": get_image_base64(p_img) if p_img else "",
                                "Quantity": p_qty, "Display_Location": p_loc, "Cost_Price": p_cost, "Selling_Price": p_sell, "Profit": profit,
                                "Is_Sold": "نعم" if is_sold else "لا", "Sale_Date": str(p_date) if is_sold and p_date else "", 
                                "Customer_Name": p_cust if is_sold else "", "Notes": p_notes
                            }
                            ws_prod.update(values=[[p_dict.get(h, "") for h in c_head_p]], range_name=f"A{len(raw_p)+1}")
                            
                            if is_from_inv and used_qty:
                                for itm, q in used_qty.items():
                                    if itm.startswith("[خامة-"):
                                        i_id = itm.split("]")[0].replace("[خامة-", "").strip()
                                        id_idx = clean_headers.index("Item_ID")+1 if "Item_ID" in clean_headers else 1
                                        q_idx = clean_headers.index("Quantity")+1 if "Quantity" in clean_headers else 4
                                        c_inv = worksheet.find(i_id, in_column=id_idx)
                                        if c_inv:
                                            curr = int(worksheet.cell(c_inv.row, q_idx).value or 0)
                                            worksheet.update(values=[[max(0, curr - q)]], range_name=f"{get_col_letter(q_idx)}{c_inv.row}")
                                    elif itm.startswith("[تغليف-"):
                                        s_id = itm.split("]")[0].replace("[تغليف-", "").strip()
                                        sid_idx = head_supplies.index("Supply_ID")+1 if "Supply_ID" in head_supplies else 1
                                        sq_idx = head_supplies.index("Quantity")+1 if "Quantity" in head_supplies else 4
                                        c_sup = ws_supplies.find(s_id, in_column=sid_idx)
                                        if c_sup:
                                            curr_s = int(ws_supplies.cell(c_sup.row, sq_idx).value or 0)
                                            ws_supplies.update(values=[[max(0, curr_s - q)]], range_name=f"{get_col_letter(sq_idx)}{c_sup.row}")
                            st.success("تم الإضافة والخصم!"); time.sleep(1); st.rerun()
                        else: st.error("أدخل اسم المنتج!")

            with tab_p_edit:
                if not df_p.empty and "Product_Name" in df_p.columns:
                    p_names_list = [n for n in df_p["Product_Name"].dropna().astype(str).tolist() if str(n).strip() != ""]
                    if p_names_list:
                        sel_p_name = st.selectbox("اختر المنتج لتعديله", p_names_list)
                        c_row_p = df_p[df_p["Product_Name"].astype(str) == str(sel_p_name)].iloc[0]
                        hid_p_id = str(c_row_p.get("Product_ID", ""))
                        
                        edit_p_sold = st.checkbox("هل تم البيع؟", value=(str(c_row_p.get("Is_Sold", "")).strip() == "نعم"), key="edit_p_sold")
                        try:
                            r_date = str(c_row_p.get("Sale_Date", "")).strip()
                            saved_date = datetime.datetime.strptime(r_date, "%Y-%m-%d").date() if r_date and r_date != "None" else None
                        except: saved_date = None

                        with st.form("edit_p_form", clear_on_submit=True):
                            e_p_name = st.text_input("اسم المنتج", value=str(c_row_p.get("Product_Name", "")))
                            e_p_img = st.file_uploader("صورة جديدة", type=["jpg", "png"])
                            e_p_qty = st.number_input("الكمية", min_value=0, step=1, value=int(c_row_p.get("Quantity", 0)))
                            e_p_loc = st.text_input("مكان العرض", value=str(c_row_p.get("Display_Location", "")))
                            e_p_cost = st.number_input("التكلفة", min_value=0.0, step=1.0, value=float(c_row_p.get("Cost_Price", 0.0)))
                            e_p_sell = st.number_input("سعر البيع", min_value=0.0, step=1.0, value=float(c_row_p.get("Selling_Price", 0.0)))
                            e_p_date = st.date_input("تاريخ البيع", value=saved_date)
                            e_p_cust = st.text_input("اسم العميل", value=str(c_row_p.get("Customer_Name", "")))
                            e_p_notes = st.text_area("ملاحظات", value=str(c_row_p.get("Notes", "")))

                            cp_b1, cp_b2 = st.columns(2)
                            with cp_b1: sub_p_e = st.form_submit_button("✏️ تحديث المنتج")
                            with cp_b2: sub_p_d = st.form_submit_button("🗑️ حذف المنتج")

                        cell_p = ws_prod.find(hid_p_id, in_column=c_head_p.index("Product_ID")+1) if "Product_ID" in c_head_p else ws_prod.find(hid_p_id, in_column=1)

                        if sub_p_e and cell_p:
                            profit_n = float(e_p_sell) - float(e_p_cost)
                            up_p_dict = {
                                "Product_ID": hid_p_id, "Product_Name": e_p_name, "Image_URL": get_image_base64(e_p_img) if e_p_img else str(c_row_p.get("Image_URL", "")),
                                "Quantity": e_p_qty, "Display_Location": e_p_loc, "Cost_Price": e_p_cost, "Selling_Price": e_p_sell, "Profit": profit_n,
                                "Is_Sold": "نعم" if edit_p_sold else "لا", "Sale_Date": str(e_p_date) if edit_p_sold and e_p_date else "",
                                "Customer_Name": e_p_cust if edit_p_sold else "", "Notes": e_p_notes
                            }
                            ws_prod.update(values=[[up_p_dict.get(h, str(c_row_p.get(h, ""))) for h in c_head_p]], range_name=f"A{cell_p.row}")
                            st.success("تم التحديث!"); time.sleep(1); st.rerun()

                        if sub_p_d and cell_p:
                            ws_prod.delete_row(cell_p.row)
                            st.success("تم الحذف!"); time.sleep(1); st.rerun()
