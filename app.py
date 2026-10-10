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
# دوال مساعدة
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
        image.thumbnail((200, 200))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=70)
        return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    return ""

# ==========================================
# إعدادات الصفحة وتهيئة الذاكرة (Session State)
# ==========================================
st.set_page_config(page_title="Tafsela ERP System", layout="wide", initial_sidebar_state="expanded")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = "🏠 الصفحة الرئيسية (Home)"

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
    .stRadio div { font-size: 20px !important; font-weight: bold !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# الاتصال بقاعدة البيانات (جوجل شيت)
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

    # التأكد من وجود شيت المستخدمين (Users) وحل مشكلة الإيرور
    try:
        ws_users = sh.worksheet("Users")
    except WorksheetNotFound:
        ws_users = sh.add_worksheet(title="Users", rows=100, cols=4)
        ws_users.append_row(["Email", "Password", "Status", "Role"])
        
    # التأكد إن العناوين موجودة لو الشيت كان فاضي
    if not ws_users.get_all_values():
        ws_users.append_row(["Email", "Password", "Status", "Role"])

except Exception as e:
    st.error(f"حدث خطأ في الاتصال بقاعدة البيانات: {e}")
    st.stop()

# ==========================================
# نظام تسجيل الدخول (Authentication)
# ==========================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logi.png", use_container_width=True)
        except: st.write("📦 Tafsela Logo")
        st.markdown("<h2 style='text-align: center;'>بوابة الدخول - Tafsela System</h2>", unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["🔐 تسجيل الدخول", "📝 إنشاء حساب جديد"])
        
        with tab_login:
            with st.form("login_form"):
                l_email = st.text_input("البريد الإلكتروني (Email)")
                l_pass = st.text_input("كلمة المرور (Password)", type="password")
                if st.form_submit_button("دخول (Login)"):
                    if l_email and l_pass:
                        users_data = ws_users.get_all_records()
                        df_users = pd.DataFrame(users_data)
                        if not df_users.empty and l_email in df_users['Email'].values:
                            user_row = df_users[df_users['Email'] == l_email].iloc[0]
                            if str(user_row['Password']) == hash_password(l_pass):
                                if user_row['Status'] == 'Approved':
                                    st.session_state.logged_in = True
                                    st.session_state.user_email = l_email
                                    st.session_state.is_admin = (user_row['Role'] == 'Admin')
                                    st.success("تم تسجيل الدخول بنجاح! جاري التوجيه...")
                                    time.sleep(1); st.rerun()
                                else:
                                    st.warning("حسابك قيد المراجعة (Pending). في انتظار موافقة الإدارة.")
                            else:
                                st.error("كلمة المرور غير صحيحة!")
                        else:
                            st.error("البريد الإلكتروني غير مسجل لدينا.")
                    else:
                        st.error("يرجى إدخال البريد الإلكتروني وكلمة المرور.")

        with tab_register:
            with st.form("register_form"):
                r_email = st.text_input("البريد الإلكتروني (Email)")
                r_pass = st.text_input("كلمة المرور (Password)", type="password")
                r_pass2 = st.text_input("تأكيد كلمة المرور", type="password")
                if st.form_submit_button("إنشاء حساب (Register)"):
                    if r_email and r_pass and r_pass == r_pass2:
                        users_data = ws_users.get_all_values()
                        existing_emails = [row[0] for row in users_data[1:]] if len(users_data) > 1 else []
                        
                        if r_email in existing_emails:
                            st.error("هذا البريد الإلكتروني مسجل بالفعل!")
                        else:
                            if r_email.lower().strip() == "nadineali2006@gmail.com":
                                status, role = "Approved", "Admin"
                                st.success("تم التعرف عليك كمدير النظام. تم الموافقة أوتوماتيكياً!")
                            else:
                                status, role = "Pending", "User"
                                st.success("تم إرسال طلبك بنجاح. يرجى انتظار موافقة الإدارة (Admin).")
                                
                            ws_users.append_row([r_email, hash_password(r_pass), status, role])
                            time.sleep(2); st.rerun()
                    else:
                        st.error("تأكد من ملء جميع الخانات وتطابق كلمة المرور.")

# ==========================================
# التطبيق الرئيسي (بعد تسجيل الدخول)
# ==========================================
else:
    with st.sidebar:
        try: st.image("logi.png", use_container_width=True)
        except: st.write("📦")
        st.markdown(f"<p style='text-align: center; font-size:14px; color:#aaa;'>مرحباً: {st.session_state.user_email}</p><hr>", unsafe_allow_html=True)
        
        menu_options = ["🏠 الصفحة الرئيسية (Home)", "📦 المخزون والموردين", "🛍️ المنتجات والمبيعات", "📊 لوحة الإحصائيات (Dashboard)"]
        if st.session_state.is_admin:
            menu_options.append("⚙️ لوحة الإدارة (Admin Panel)")
            
        st.radio("القائمة الرئيسية:", menu_options, key="app_mode")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 تسجيل الخروج (Logout)"):
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.session_state.is_admin = False
            st.rerun()

    # تحميل داتا المخزون الأساسية
    worksheet = sh.sheet1
    raw_data = worksheet.get_all_values()
    if len(raw_data) > 0:
        clean_headers = [str(h).strip() if str(h).strip() != "" else f"Unnamed_{i}" for i, h in enumerate(raw_data[0])]
        if "Supplier_Name" not in clean_headers: clean_headers.append("Supplier_Name")
        if "Services_Cost" not in clean_headers: clean_headers.append("Services_Cost")
        df = pd.DataFrame(raw_data[1:], columns=clean_headers[:len(raw_data[1][0])] if len(raw_data)>1 else clean_headers)
        for col in ["Supplier_Name", "Services_Cost"]:
            if col not in df.columns: df[col] = ""
        for col in ["Item_ID", "Quantity", "Purchase_Price", "Selling_Price", "Shipping_Cost", "Services_Cost"]: 
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        clean_headers = ["Item_ID", "Item_Name", "Image_URL", "Quantity", "Purchase_Price", "Selling_Price", "Purchase_Location", "Shipping_Cost", "Supplier_Name", "Services_Cost", "Colors", "Notes"]
        df = pd.DataFrame(columns=clean_headers)

    # ------------------------------------------
    # الصفحة الرئيسية (Home Page)
    # ------------------------------------------
    if st.session_state.app_mode == "🏠 الصفحة الرئيسية (Home)":
        st.markdown("<br><br>", unsafe_allow_html=True)
        col_img1, col_img2, col_img3 = st.columns([1, 1, 1])
        with col_img2:
            try: st.image("logi.png", use_container_width=True)
            except: st.write("📦")
        
        st.markdown("<h1 style='text-align: center; color: white;'>Tafsela Management System</h1><br>", unsafe_allow_html=True)
        
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        with col_nav2:
            nav_options = [opt for opt in menu_options if opt != "🏠 الصفحة الرئيسية (Home)"]
            selected_nav = st.selectbox("إلى أين تريد الذهاب؟ (Where to?)", nav_options)
            if st.button("انتقال 🚀 (Go)", use_container_width=True):
                st.session_state.app_mode = selected_nav
                st.rerun()

    # ------------------------------------------
    # لوحة الإدارة للمدير (Admin Panel)
    # ------------------------------------------
    elif st.session_state.app_mode == "⚙️ لوحة الإدارة (Admin Panel)" and st.session_state.is_admin:
        st.markdown("<h1>⚙️ إدارة المستخدمين (Admin Panel)</h1><hr>", unsafe_allow_html=True)
        
        users_raw = ws_users.get_all_values()
        if len(users_raw) > 1:
            df_u = pd.DataFrame(users_raw[1:], columns=users_raw[0])
            pending_users = df_u[df_u['Status'] == 'Pending']
            
            if not pending_users.empty:
                st.warning(f"يوجد عدد ({len(pending_users)}) طلب تسجيل قيد الانتظار.")
                for _, row in pending_users.iterrows():
                    st.write(f"📧 البريد: **{row['Email']}**")
                    if st.button(f"✅ الموافقة (Approve)", key=f"app_{row['Email']}"):
                        cell = ws_users.find(row['Email'], in_column=1)
                        if cell:
                            ws_users.update_cell(cell.row, 3, "Approved") 
                            st.success(f"تمت الموافقة على {row['Email']} بنجاح!")
                            time.sleep(1); st.rerun()
                    st.markdown("<hr>", unsafe_allow_html=True)
            else:
                st.success("لا توجد طلبات معلقة. جميع المستخدمين نشطين.")
            
            st.markdown("### 👥 جميع المستخدمين المسجلين:")
            st.dataframe(df_u[['Email', 'Status', 'Role']], use_container_width=True)
        else:
            st.info("لا يوجد مستخدمين مسجلين حتى الآن.")

    # ------------------------------------------
    # إدارة المخزون والموردين (Inventory)
    # ------------------------------------------
    elif st.session_state.app_mode == "📦 المخزون والموردين":
        st.markdown("<h1>📦 إدارة المخزون والموردين (Inventory)</h1><hr>", unsafe_allow_html=True)
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
                    p_price = row.get("Purchase_Price", 0)
                    s_cost = row.get("Services_Cost", 0)
                    t_cost = float(p_price) + float(s_cost) 
                    
                    cols_data = [
                        row.get("Item_ID", ""), row.get("Item_Name", ""), row.get("Image_URL", ""),
                        row.get("Quantity", ""), p_price, row.get("Selling_Price", ""),
                        row.get("Supplier_Name", ""), s_cost, f'<span style="color:#ffcc00; font-weight:bold;">{t_cost}</span>'
                    ]
                    for i, val in enumerate(cols_data):
                        if i == 2 and str(val).startswith("data:image"):
                            html_table += f'<td style="border-bottom: 1px solid #333; padding: 12px;"><img src="{val}" width="50" style="border-radius: 5px;"></td>'
                        else:
                            html_table += f'<td style="color: white; border-bottom: 1px solid #333; padding: 12px;">{val}</td>'
                    html_table += "</tr>"
                html_table += "</table></div>"
                st.markdown(html_table, unsafe_allow_html=True)
            else: st.info("No items found.")

        with col2:
            tab_add, tab_edit = st.tabs(["➕ Add Item", "✏️ Edit Item"])
            base_suppliers = ["محمود بلاستيك", "مكتبة الفنون", "مورد أونلاين"]
            if not df.empty and "Supplier_Name" in df.columns:
                sup_list = df["Supplier_Name"].dropna().astype(str).unique().tolist()
                for s in sup_list:
                    if s and s.strip() != "" and s not in base_suppliers and s != "مورد جديد...": base_suppliers.append(s)
            base_suppliers.append("مورد جديد...")

            with tab_add:
                with st.form("add_inv_form", clear_on_submit=True):
                    i_name = st.text_input("اسم الخامة")
                    i_img = st.file_uploader("صورة", type=["jpg", "png"])
                    i_qty = st.number_input("الكمية", min_value=0, step=1)
                    
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                    sup_sel = st.selectbox("المورد (Supplier)", base_suppliers)
                    new_sup = st.text_input("اسم المورد الجديد") if sup_sel == "مورد جديد..." else ""
                    
                    p_price = st.number_input("سعر الشراء الأساسي", min_value=0.0, step=1.0)
                    serv_cost = st.number_input("تكلفة إكسسوارات/خدمات إضافية", min_value=0.0, step=1.0)
                    s_price = st.number_input("سعر البيع المتوقع", min_value=0.0, step=1.0)
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                    
                    colors = st.text_input("الألوان المتاحة")
                    notes = st.text_area("ملاحظات")

                    if st.form_submit_button("إضافة للمخزن"):
                        if i_name == "": st.error("أدخل اسم الخامة!")
                        else:
                            f_sup = new_sup if sup_sel == "مورد جديد..." and new_sup else sup_sel
                            img_str = get_image_base64(i_img) if i_img else ""
                            new_row_dict = {
                                "Item_ID": len(df) + 1 if not df.empty else 1, "Item_Name": i_name, "Image_URL": img_str,
                                "Quantity": i_qty, "Purchase_Price": p_price, "Selling_Price": s_price,
                                "Supplier_Name": f_sup, "Services_Cost": serv_cost, "Colors": colors, "Notes": notes
                            }
                            new_row = [new_row_dict.get(h, "") for h in clean_headers]
                            worksheet.update(values=[new_row], range_name=f"A{len(raw_data) + 1}")
                            st.success("تم الإضافة!"); time.sleep(1); st.rerun()

            with tab_edit:
                if not df.empty and "Item_Name" in df.columns:
                    names_list = [n for n in df["Item_Name"].dropna().astype(str).tolist() if str(n).strip() != ""]
                    if names_list:
                        sel_name = st.selectbox("اختر للتعديل", names_list)
                        c_row = df[df["Item_Name"].astype(str) == str(sel_name)].iloc[0]
                        hid_id = str(c_row.get("Item_ID", ""))
                        c_sup = str(c_row.get("Supplier_Name", ""))
                        sup_idx = base_suppliers.index(c_sup) if c_sup in base_suppliers else 0

                        with st.form("edit_inv_form", clear_on_submit=True):
                            e_name = st.text_input("اسم الخامة", value=str(c_row.get("Item_Name", "")))
                            e_img = st.file_uploader("صورة جديدة", type=["jpg", "png"])
                            e_qty = st.number_input("الكمية", min_value=0, step=1, value=int(c_row.get("Quantity", 0)))
                            
                            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                            e_sup_sel = st.selectbox("المورد", base_suppliers, index=sup_idx)
                            e_new_sup = st.text_input("اسم المورد الجديد") if e_sup_sel == "مورد جديد..." else ""
                            
                            e_pprice = st.number_input("سعر الشراء", min_value=0.0, step=1.0, value=float(c_row.get("Purchase_Price", 0.0)))
                            e_scost = st.number_input("إكسسوارات/خدمات", min_value=0.0, step=1.0, value=float(c_row.get("Services_Cost", 0.0)))
                            e_sprice = st.number_input("سعر البيع", min_value=0.0, step=1.0, value=float(c_row.get("Selling_Price", 0.0)))
                            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

                            e_colors = st.text_input("الألوان", value=str(c_row.get("Colors", "")))
                            e_notes = st.text_area("ملاحظات", value=str(c_row.get("Notes", "")))

                            c_b1, c_b2 = st.columns(2)
                            with c_b1: sub_e = st.form_submit_button("✏️ تحديث")
                            with c_b2: sub_d = st.form_submit_button("🗑️ حذف")

                        cell = worksheet.find(hid_id, in_column=clean_headers.index("Item_ID")+1) if "Item_ID" in clean_headers else worksheet.find(hid_id, in_column=1)

                        if sub_e and cell:
                            f_sup = e_new_sup if e_sup_sel == "مورد جديد..." else e_sup_sel
                            img_n = get_image_base64(e_img) if e_img else c_row.get("Image_URL", "")
                            up_dict = {
                                "Item_ID": hid_id, "Item_Name": e_name, "Image_URL": img_n, "Quantity": e_qty,
                                "Purchase_Price": e_pprice, "Selling_Price": e_sprice, "Supplier_Name": f_sup,
                                "Services_Cost": e_scost, "Colors": e_colors, "Notes": e_notes
                            }
                            up_row = [up_dict.get(h, str(c_row.get(h, ""))) for h in clean_headers]
                            worksheet.update(values=[up_row], range_name=f"A{cell.row}")
                            st.success("تم التحديث!"); time.sleep(1); st.rerun()

                        if sub_d and cell:
                            worksheet.delete_row(cell.row)
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
        if len(raw_p) > 0:
            c_head_p = [str(h).strip() if str(h).strip() != "" else f"Unnamed_{i}" for i, h in enumerate(raw_p[0])]
            df_p = pd.DataFrame(raw_p[1:], columns=c_head_p)
            for c in ["Product_ID", "Quantity", "Cost_Price", "Selling_Price", "Profit"]: 
                if c in df_p.columns: df_p[c] = pd.to_numeric(df_p[c], errors='coerce').fillna(0)
        else: df_p = pd.DataFrame()

        cp1, cp2 = st.columns([3, 1])
        with cp1:
            st.markdown("### 🏷️ المنتجات المعروضة والمباعة")
            if not df_p.empty:
                st.dataframe(df_p[["Product_Name", "Quantity", "Cost_Price", "Selling_Price", "Profit", "Is_Sold", "Customer_Name"]], use_container_width=True)
            else: st.info("لا توجد منتجات.")

        with cp2:
            st.markdown("<div style='background-color:#2a2a3f; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
            is_from_inv = st.checkbox("🔗 سحب خامات من المخزن؟", key="add_p_is_inv")
            used_qty = {}
            if is_from_inv and not df.empty:
                inv_opts = [f"[{r['Item_ID']}] {r['Item_Name']} (متاح: {r['Quantity']})" for _, r in df.iterrows() if str(r['Item_Name']).strip() != ""]
                sel_inv = st.multiselect("اختر الخامات:", inv_opts)
                for item in sel_inv:
                    used_qty[item] = st.number_input(f"سحب من {item.split(']')[1].split('(')[0]}:", min_value=1, step=1)
            st.markdown("</div><br>", unsafe_allow_html=True)

            is_sold = st.checkbox("هل تم البيع؟", key="add_p_sold")
            with st.form("add_p_form", clear_on_submit=True):
                p_name = st.text_input("اسم المنتج")
                p_cost = st.number_input("التكلفة", min_value=0.0, step=1.0)
                p_sell = st.number_input("سعر البيع", min_value=0.0, step=1.0)
                p_date = st.date_input("تاريخ البيع", value=None)
                p_cust = st.text_input("اسم العميل")
                if st.form_submit_button("إضافة"):
                    if p_name:
                        profit = float(p_sell) - float(p_cost)
                        p_dict = {
                            "Product_ID": len(df_p)+1, "Product_Name": p_name, "Cost_Price": p_cost, "Selling_Price": p_sell, "Profit": profit,
                            "Is_Sold": "نعم" if is_sold else "لا", "Sale_Date": str(p_date) if is_sold and p_date else "", "Customer_Name": p_cust if is_sold else ""
                        }
                        n_row = [p_dict.get(h, "") for h in c_head_p]
                        ws_prod.update(values=[n_row], range_name=f"A{len(raw_p)+1}")
                        
                        if is_from_inv and used_qty:
                            id_idx = clean_headers.index("Item_ID")+1 if "Item_ID" in clean_headers else 1
                            q_idx = clean_headers.index("Quantity")+1 if "Quantity" in clean_headers else 4
                            for itm, q in used_qty.items():
                                i_id = itm.split("]")[0].replace("[", "").strip()
                                c_inv = worksheet.find(i_id, in_column=id_idx)
                                if c_inv:
                                    curr = int(worksheet.cell(c_inv.row, q_idx).value or 0)
                                    worksheet.update(values=[[max(0, curr - q)]], range_name=f"{get_col_letter(q_idx)}{c_inv.row}")
                        st.success("تم!"); time.sleep(1); st.rerun()

    # ------------------------------------------
    # لوحة الإحصائيات (Dashboard)
    # ------------------------------------------
    elif st.session_state.app_mode == "📊 لوحة الإحصائيات (Dashboard)":
        st.markdown("<h1>📊 إحصائيات وأداء البيزنس</h1><hr>", unsafe_allow_html=True)
        
        try: ws_prod = sh.worksheet("Products"); raw_p = ws_prod.get_all_values()
        except: raw_p = []

        if len(raw_p) > 1:
            df_p = pd.DataFrame(raw_p[1:], columns=[str(h).strip() for h in raw_p[0]])
            df_p["Profit"] = pd.to_numeric(df_p["Profit"], errors='coerce').fillna(0)
            df_p["Selling_Price"] = pd.to_numeric(df_p["Selling_Price"], errors='coerce').fillna(0)
            
            total_sales = df_p[df_p["Is_Sold"] == "نعم"]["Selling_Price"].sum()
            total_profit = df_p[df_p["Is_Sold"] == "نعم"]["Profit"].sum()
            total_items_sold = len(df_p[df_p["Is_Sold"] == "نعم"])
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>💰 إجمالي المبيعات</h3><h2 style='color:#5ce1d6;'>{total_sales} ج.م</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>📈 صافي الأرباح</h3><h2 style='color:#00ff00;'>{total_profit} ج.م</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='background-color:#2a2a3f; padding:20px; border-radius:10px; text-align:center;'><h3>🛍️ منتجات مباعة</h3><h2 style='color:#ffcc00;'>{total_items_sold} قطعة</h2></div>", unsafe_allow_html=True)
            
            st.markdown("<br><hr>", unsafe_allow_html=True)
            
        st.markdown("<h3>⚠️ تنبيهات نواقص المخزن (أقل من 5 قطع)</h3>", unsafe_allow_html=True)
        if not df.empty:
            low_stock = df[df["Quantity"] < 5]
            if not low_stock.empty:
                for _, row in low_stock.iterrows():
                    st.error(f"🚨 الخامة: **{row['Item_Name']}** - متبقي منها **{row['Quantity']}** قطع فقط! (المورد: {row.get('Supplier_Name', 'غير مسجل')})")
            else:
                st.success("✅ المخزن ممتلئ ولا توجد نواقص خطيرة حالياً.")
