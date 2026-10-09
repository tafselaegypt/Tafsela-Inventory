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

# 2. تعديل الـ CSS لتكبير كل الخطوط (العناوين، المدخلات، والقوائم المنسدلة)
st.markdown(
    """
<style>
    /* العناوين الأساسية */
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
    
    /* تكبير خط العناوين (Labels) فوق المربعات */
    label, p, .st-emotion-cache-1wivap2, .st-emotion-cache-1y4p8pa {
        color: white !important; 
        font-size: 26px !important; 
        font-weight: bold !important;
    }
    
    /* تكبير خط تبويبات (Add New / Edit Existing) */
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {
        color: #5ce1d6 !important;
        font-size: 24px !important; 
    }
    
    /* تكبير الكلام المكتوب داخل مربعات النصوص والأرقام */
    input, textarea, .stNumberInput input {
        font-size: 24px !important; 
    }
    
    /* ----- تحديثات قوية للقوائم المنسدلة (Dropdowns) ----- */
    /* تكبير النص داخل المربع قبل ما تفتح القائمة */
    div[data-baseweb="select"] {
        font-size: 30px !important;
    }
    div[data-baseweb="select"] > div {
        font-size: 24px !important;
    }
    
    /* تكبير النصوص داخل القائمة بعد ما تفتح */
    div[role="listbox"] ul li {
        font-size: 24px !important;
        padding: 15px !important; /* تكبير المساحة حول كل اختيار عشان يكون واضح */
    }
    ul[data-baseweb="menu"] li {
        font-size: 24px !important;
    }
    li[role="option"] {
        font-size: 24px !important;
    }
    
    /* تكبير خط الكلام داخل الأزرار (Add, Update, Delete) */
    .stButton button, .stButton button p {
        font-size: 24px !important;
        font-weight: bold !important;
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
                            f' text-align: center;"><img src="{val}" width="80"'
                            ' style="border-radius: 5px; display: block; margin: 0 auto;"></td>'
                        )
                    else:
                        html_table += (
                            f'<td style="color: white; border-bottom: 1px solid #333;'
                            f' padding: 12px; text-align: center;">{val}</td>'
                        )
                html_table += "</tr>"
            html_table += "</table>"

            st.markdown(html_table, unsafe_allow_html=True)
        else:
            if search_term:
                st.warning(f"لا توجد منتجات تطابق كلمة البحث: '{search_term}'")
            else:
                st.info("No items found in the inventory.")

    with col2:
        # بناء قائمة أماكن الشراء الديناميكية
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
                        st.success("Added Successfully! Please refresh the page.")

        # ====== تبويب التعديل والحذف ======
        with tab_edit:
            if not df.empty and "Item_Name" in df.columns:
                item_names_list = df["Item_Name"].dropna().astype(str).tolist()
                item_names_list = [name for name in item_names_list if name.strip() != ""]
                
                if item_names_list:
                    selected_edit_name = st.selectbox("Select Item to Edit", item_names_list)
                    current_row = df[df["Item_Name"].astype(str) == str(selected_edit_name)].iloc[0]
                    hidden_edit_id = str(current_row.get("Item_ID", ""))

                    c_name = str(current_row.get("Item_Name", ""))
                    
                    raw_qty = current_row.get("Quantity", 0)
                    c_qty = int(raw_qty) if pd.notna(raw_qty) and str(raw_qty).strip() != "" else 0
                    
                    raw_pprice = current_row.get("Purchase_Price", 0.0)
                    c_pprice = float(raw_pprice) if pd.notna(raw_pprice) and str(raw_pprice).strip() != "" else 0.0
                    
                    raw_sprice = current_row.get("Selling_Price", 0.0)
                    c_sprice = float(raw_sprice) if pd.notna(raw_sprice) and str(raw_sprice).strip() != "" else 0.0
                    
                    c_loc = str(current_row.get("Purchase_Location", ""))
                    
                    raw_ship = current_row.get("Shipping_Cost", 0.0)
                    c_ship = float(raw_ship) if pd.notna(raw_ship) and str(raw_ship).strip() != "" else 0.0
                    
                    c_notes = str(current_row.get("Notes", ""))
                    
                    loc_index = base_locations.index(c_loc) if c_loc in base_locations else 0

                    with st.form("edit_item_form"):
                        st.write(f"Editing/Deleting: **{c_name}**")
                        new_name = st.text_input("Item Name", value=c_name)
                        new_image = st.file_uploader("Upload New Image (Leave empty to keep old image)", type=["jpg", "jpeg", "png"])
                        new_quantity = st.number_input("Quantity", min_value=0, step=1, value=c_qty)
                        new_purchase_price = st.number_input("Purchase Price", min_value=0.0, step=1.0, value=c_pprice)
                        new_selling_price = st.number_input("Selling Price", min_value=0.0, step=1.0, value=c_sprice)
                        
                        selected_loc_edit = st.selectbox("Purchase Location", base_locations, index=loc_index)
                        new_loc_edit = ""
                        if selected_loc_edit == "أخرى (إضافة جديد)...":
                            new_loc_edit = st.text_input("Enter New Purchase Location")
                            
                        new_shipping_cost = st.number_input("Shipping Cost", min_value=0.0, step=1.0, value=c_ship)
                        new_notes = st.text_area("Notes", value=c_notes)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            submitted_edit = st.form_submit_button("✏️ Update Item")
                        with col_btn2:
                            submitted_delete = st.form_submit_button("🗑️ Delete Item")

                    if submitted_edit:
                        if new_name == "":
                            st.error("Please enter the Item Name!")
                        else:
                            final_loc_edit = new_loc_edit if selected_loc_edit == "أخرى (إضافة جديد)..." and new_loc_edit else selected_loc_edit
                            cell = worksheet.find(hidden_edit_id, in_column=1)
                            if cell:
                                row_num = cell.row
                                img_data_new = get_image_base64(new_image) if new_image else df.loc[df["Item_ID"].astype(str) == hidden_edit_id, "Image_URL"].values[0]
                                
                                updated_row = [[
                                    hidden_edit_id, new_name, img_data_new, new_quantity,
                                    new_purchase_price, new_selling_price, final_loc_edit,
                                    new_shipping_cost, new_notes
                                ]]
                                worksheet.update(values=updated_row, range_name=f"A{row_num}:I{row_num}")
                                st.success("Updated Successfully! Please refresh the page.")
                            else:
                                st.error("Error: Could not locate this item in the sheet.")
                            
                    if submitted_delete:
                        cell = worksheet.find(hidden_edit_id, in_column=1)
                        if cell:
                            worksheet.delete_row(cell.row)
                            
                            remaining_records = worksheet.get_all_values()
                            if len(remaining_records) > 1:
                                new_ids = [[i] for i in range(1, len(remaining_records))]
                                worksheet.update(values=new_ids, range_name=f"A2:A{len(remaining_records)}")
                                
                            st.success("Deleted Successfully and IDs Re-sequenced! Please refresh the page.")
                        else:
                            st.error("Error: Could not locate this item in the sheet.")
                else:
                    st.info("لا توجد منتجات مسجلة بأسمائها للتعديل أو الحذف.")
            else:
                st.info("No items available to edit or delete.")

except Exception as e:
    st.error(f"Connection Error: {e}")
