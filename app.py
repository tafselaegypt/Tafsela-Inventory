import base64
import io
import time
from PIL import Image
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# دالة مساعدة لمعرفة الحرف الأبجدي للعمود (A, B, C...) أوتوماتيكياً
def get_col_letter(col_idx):
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Tafsela Inventory Management System", layout="wide"
)

# 2. تعديل الـ CSS الشامل
st.markdown(
    """
<style>
    h1, h1 span, h1 div { font-size: 48px !important; color: white !important; font-weight: bold !important; line-height: 1.1 !important; margin: 0 !important; }
    h2, h3, h4, h5, h6 { color: #5ce1d6 !important; }
    label, p, .st-emotion-cache-1wivap2, .st-emotion-cache-1y4p8pa { color: white !important; font-size: 20px !important; font-weight: bold !important; }
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span { color: #5ce1d6 !important; font-size: 18px !important; }
    input, textarea, .stNumberInput input { font-size: 18px !important; }
    .stSelectbox div[data-baseweb="select"] > div { font-size: 18px !important; }
    div[role="listbox"] ul li, ul[data-baseweb="menu"] li { font-size: 18px !important; padding: 12px !important; }
    .stButton button, .stButton button p { font-size: 18px !important; font-weight: bold !important; }

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

    raw_data = worksheet.get_all_values()
    
    if len(raw_data) > 0:
        headers_row = raw_data[0]
        # تنظيف العناوين لضمان المطابقة
        clean_headers = [str(h).strip() if str(h).strip() != "" else f"Unnamed_{i}" for i, h in enumerate(headers_row)]
        
        df = pd.DataFrame(raw_data[1:], columns=clean_headers)
        
        numeric_cols = ["Item_ID", "Quantity", "Purchase_Price", "Selling_Price", "Shipping_Cost"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        clean_headers = []
        df = pd.DataFrame()

    col1, col2 = st.columns([3, 1])

    with col1:
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
        if not display_df.empty and "Item_Name" in display_df.columns and search_term:
            display_df = display_df[display_df["Item_Name"].astype(str).str.contains(search_term, case=False, na=False)]

        if not display_df.empty and "Item_Name" in display_df.columns:
            html_table = (
                '<div style="width: 100%; overflow-x: auto;">'
                '<table style="width:100%; min-width: 1000px; text-align:center; border-collapse:'
                ' collapse; font-size: 16px; margin-top: 15px;">'
            )
            
            has_colors_col = "Colors" in display_df.columns
            
            headers = [
                "Item ID", "Item Name", "Image", "Quantity", "Purchase Price", 
                "Selling Price", "Purchase Location", "Shipping Cost"
            ]
            if has_colors_col:
                headers.append("Colors")
            headers.append("Notes")

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
                    row.get("Purchase_Location", ""), row.get("Shipping_Cost", "")
                ]
                
                if has_colors_col:
                    cols_data.append(row.get("Colors", ""))
                    
                cols_data.append(row.get("Notes", ""))

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
                if loc and str(loc).strip() != "" and loc not in base_locations and loc != "أخرى (إضافة جديد)...":
                    base_locations.append(loc)
        
        base_locations.append("أخرى (إضافة جديد)...")
        
        tab_add, tab_edit = st.tabs(["➕ Add New", "✏️ Edit Existing"])

        # ====== تبويب الإضافة ======
        with tab_add:
            selected_loc_add = st.selectbox("Purchase Location", base_locations, key="add_loc_select")
            new_loc_add = ""
            if selected_loc_add == "أخرى (إضافة جديد)...":
                new_loc_add = st.text_input("Enter New Purchase Location", key="add_new_loc")
                
            has_colors = st.checkbox("هل يوجد ألوان؟ (Has Colors?)", key="add_has_colors")
            item_colors = ""
            if has_colors:
                 item_colors = st.text_input("Available Colors (e.g., Red, Blue, Black)", key="add_colors")

            with st.form("add_item_form"):
                item_name = st.text_input("Item Name")
                uploaded_image = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
                quantity = st.number_input("Quantity", min_value=0, step=1)
                purchase_price = st.number_input("Purchase Price", min_value=0.0, step=1.0)
                selling_price = st.number_input("Selling Price", min_value=0.0, step=1.0)
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
                        
                        # تجميع البيانات الجديدة في قاموس (Dictionary)
                        new_row_dict = {
                            "Item_ID": next_id,
                            "Item_Name": item_name,
                            "Image_URL": image_data_string,
                            "Quantity": quantity,
                            "Purchase_Price": purchase_price,
                            "Selling_Price": selling_price,
                            "Purchase_Location": final_loc_add,
                            "Shipping_Cost": shipping_cost,
                            "Colors": item_colors,
                            "Notes": notes
                        }

                        # الخوارزمية الذكية: ترتيب البيانات بناءً على ترتيب الأعمدة الفعلي في جوجل شيت
                        new_row = []
                        for h in clean_headers:
                            if h in new_row_dict:
                                new_row.append(new_row_dict[h])
                            else:
                                new_row.append("") # لو في عمود غريب، هنسيبه فاضي عشان منبوظش الشيت
                        
                        # الكتابة في أول صف فاضي بدقة
                        next_row = len(raw_data) + 1
                        worksheet.update(values=[new_row], range_name=f"A{next_row}")
                        
                        st.success("Added Successfully! Refreshing...")
                        time.sleep(1)
                        st.rerun()

        # ====== تبويب التعديل والحذف ======
        with tab_edit:
            if not df.empty and "Item_Name" in df.columns:
                item_names_list = df["Item_Name"].dropna().astype(str).tolist()
                item_names_list = [name for name in item_names_list if str(name).strip() != ""]
                
                if item_names_list:
                    selected_edit_name = st.selectbox("Select Item to Edit", item_names_list)
                    current_row = df[df["Item_Name"].astype(str) == str(selected_edit_name)].iloc[0]
                    hidden_edit_id = str(current_row.get("Item_ID", ""))

                    c_name = str(current_row.get("Item_Name", ""))
                    c_qty = int(current_row.get("Quantity", 0))
                    c_pprice = float(current_row.get("Purchase_Price", 0.0))
                    c_sprice = float(current_row.get("Selling_Price", 0.0))
                    c_loc = str(current_row.get("Purchase_Location", ""))
                    c_ship = float(current_row.get("Shipping_Cost", 0.0))
                    c_colors = str(current_row.get("Colors", "")) if "Colors" in current_row else ""
                    c_notes = str(current_row.get("Notes", ""))
                    
                    loc_index = base_locations.index(c_loc) if c_loc in base_locations else 0

                    selected_loc_edit = st.selectbox("Purchase Location", base_locations, index=loc_index, key="edit_loc_select")
                    new_loc_edit = ""
                    if selected_loc_edit == "أخرى (إضافة جديد)...":
                        new_loc_edit = st.text_input("Enter New Purchase Location", key="edit_new_loc")
                        
                    edit_has_colors = st.checkbox("هل يوجد ألوان؟ (Has Colors?)", value=bool(c_colors.strip()), key="edit_has_colors")
                    new_colors = ""
                    if edit_has_colors:
                         new_colors = st.text_input("Available Colors", value=c_colors, key="edit_colors")

                    with st.form("edit_item_form"):
                        st.write(f"Editing/Deleting: **{c_name}**")
                        new_name = st.text_input("Item Name", value=c_name)
                        new_image = st.file_uploader("Upload New Image (Leave empty to keep old image)", type=["jpg", "jpeg", "png"])
                        new_quantity = st.number_input("Quantity", min_value=0, step=1, value=c_qty)
                        new_purchase_price = st.number_input("Purchase Price", min_value=0.0, step=1.0, value=c_pprice)
                        new_selling_price = st.number_input("Selling Price", min_value=0.0, step=1.0, value=c_sprice)
                        new_shipping_cost = st.number_input("Shipping Cost", min_value=0.0, step=1.0, value=c_ship)
                        new_notes = st.text_area("Notes", value=c_notes)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            submitted_edit = st.form_submit_button("✏️ Update Item")
                        with col_btn2:
                            submitted_delete = st.form_submit_button("🗑️ Delete Item")

                    # تحديد مكان الـ ID بذكاء عشان الحذف والتعديل ميضربش
                    cell = None
                    if "Item_ID" in clean_headers:
                        col_idx = clean_headers.index("Item_ID") + 1
                        cell = worksheet.find(hidden_edit_id, in_column=col_idx)
                    else:
                        cell = worksheet.find(hidden_edit_id, in_column=1)

                    if submitted_edit:
                        if new_name == "":
                            st.error("Please enter the Item Name!")
                        else:
                            final_loc_edit = new_loc_edit if selected_loc_edit == "أخرى (إضافة جديد)..." and new_loc_edit else selected_loc_edit
                            if cell:
                                row_num = cell.row
                                img_data_new = get_image_base64(new_image) if new_image else df.loc[df["Item_ID"].astype(str) == hidden_edit_id, "Image_URL"].values[0]
                                
                                updated_row_dict = {
                                    "Item_ID": hidden_edit_id,
                                    "Item_Name": new_name,
                                    "Image_URL": img_data_new,
                                    "Quantity": new_quantity,
                                    "Purchase_Price": new_purchase_price,
                                    "Selling_Price": new_selling_price,
                                    "Purchase_Location": final_loc_edit,
                                    "Shipping_Cost": new_shipping_cost,
                                    "Colors": new_colors,
                                    "Notes": new_notes
                                }
                                
                                # الخوارزمية الذكية للتعديل (تحافظ على الأعمدة القديمة لو موجودة)
                                updated_row = []
                                for h in clean_headers:
                                    if h in updated_row_dict:
                                        updated_row.append(updated_row_dict[h])
                                    else:
                                        val = current_row.get(h, "")
                                        existing_val = "" if pd.isna(val) else str(val)
                                        updated_row.append(existing_val)

                                worksheet.update(values=[updated_row], range_name=f"A{row_num}")
                                st.success("Updated Successfully! Refreshing...")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Error: Could not locate this item in the sheet.")
                            
                    if submitted_delete:
                        if cell:
                            worksheet.delete_row(cell.row)
                            remaining_records = worksheet.get_all_values()
                            
                            # إعادة ترتيب الـ IDs بذكاء في العمود الصح
                            if len(remaining_records) > 1 and "Item_ID" in clean_headers:
                                new_ids = [[i] for i in range(1, len(remaining_records))]
                                col_letter = get_col_letter(clean_headers.index("Item_ID") + 1)
                                worksheet.update(values=new_ids, range_name=f"{col_letter}2:{col_letter}{len(remaining_records)}")
                                
                            st.success("Deleted Successfully and IDs Re-sequenced! Refreshing...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Error: Could not locate this item in the sheet.")
                else:
                    st.info("لا توجد منتجات مسجلة بأسمائها للتعديل أو الحذف.")
            else:
                st.info("No items available to edit or delete.")

except Exception as e:
    st.error(f"Connection Error: {e}")
