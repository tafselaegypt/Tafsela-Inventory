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

# 2. تعديل الـ CSS لتنسيق الواجهة
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
        font-size: 24px !important;
    }
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {
        color: #5ce1d6 !important;
    }
    input, textarea, select {
        font-size: 24px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 3. عرض اللوجو والعنوان في المنتصف تماماً جنب بعض
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
  # الاتصال الآمن والمباشر باستخدام st.secrets
  secret_dict = {
      "type": st.secrets["type"],
      "project_id": st.secrets["project_id"],
      "private_key_id": st.secrets["private_key_id"],
      "private_key": st.secrets["private_key"],
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
    st.markdown(
        '<div style="color: white; font-size: 30px; font-weight: bold;'
        ' margin-bottom: 15px;">📋 Available Inventory</div>',
        unsafe_allow_html=True,
    )

    if not df.empty:
      html_table = (
          '<table style="width:100%; text-align:center; border-collapse:'
          ' collapse; font-size: 24px;">'
      )
      headers = [
          "Item ID",
          "Item Name",
          "Image",
          "Quantity",
          "Purchase Price",
          "Selling Price",
          "Purchase Location",
          "Shipping Cost",
          "Notes",
      ]

      html_table += "<tr>"
      for h in headers:
        html_table += (
            f'<th style="color: #5ce1d6; border-bottom: 2px solid #5ce1d6;'
            f' padding: 12px; text-align: center;">{h}</th>'
        )
      html_table += "</tr>"

      for _, row in df.iterrows():
        html_table += "<tr>"
        cols_data = [
            row.get("Item_ID", ""),
            row.get("Item_Name", ""),
            row.get("Image_URL", ""),
            row.get("Quantity", ""),
            row.get("Purchase_Price", ""),
            row.get("Selling_Price", ""),
            row.get("Purchase_Location", ""),
            row.get("Shipping_Cost", ""),
            row.get("Notes", ""),
        ]

        for i, val in enumerate(cols_data):
          if i == 2 and str(val).startswith("data:image"):
            html_table += (
                f'<td style="border-bottom: 1px solid #333; padding: 12px;'
                f' text-align: center;"><img src="{val}" width="80"'
                ' style="border-radius: 5px; display: block; margin: 0'
                ' auto;"></td>'
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
      st.info("No items found in the inventory.")

  with col2:
    locations_list = ["Techno Print Cairo", "Supplier A", "Factory B", "Other"]
    tab_add, tab_edit = st.tabs(["➕ Add New", "✏️ Edit Existing"])

    with tab_add:
      with st.form("add_item_form"):
        item_id = st.text_input("Item ID")
        item_name = st.text_input("Item Name")
        uploaded_image = st.file_uploader(
            "Upload Image", type=["jpg", "jpeg", "png"]
        )
        quantity = st.number_input("Quantity", min_value=0, step=1)
        purchase_price = st.number_input(
            "Purchase Price", min_value=0.0, step=1.0
        )
        selling_price = st.number_input("Selling Price", min_value=0.0, step=1.0)
        purchase_loc = st.selectbox("Purchase Location", locations_list)
        shipping_cost = st.number_input("Shipping Cost", min_value=0.0, step=1.0)
        notes = st.text_area("Notes")

        submitted_add = st.form_submit_button("Add to Inventory")
        if submitted_add:
          if item_name == "" or item_id == "":
            st.error("Please enter both Item ID and Name!")
          else:
            image_data_string = (
                get_image_base64(uploaded_image) if uploaded_image else ""
            )
            new_row = [
                item_id,
                item_name,
                image_data_string,
                quantity,
                purchase_price,
                selling_price,
                purchase_loc,
                shipping_cost,
                notes,
            ]
            worksheet.append_row(new_row)
            st.success("Added Successfully! Please refresh the page.")

    with tab_edit:
      if not df.empty and "Item_ID" in df.columns:
        item_ids_list = df["Item_ID"].astype(str).tolist()
        selected_edit_id = st.selectbox("Select Item ID to Edit", item_ids_list)
        current_row = df[df["Item_ID"].astype(str) == str(selected_edit_id)].iloc[
            0
        ]

        c_name = str(current_row.get("Item_Name", ""))
        c_qty = (
            int(current_row.get("Quantity", 0))
            if pd.notna(current_row.get("Quantity"))
            else 0
        )
        c_pprice = (
            float(current_row.get("Purchase_Price", 0.0))
            if pd.notna(current_row.get("Purchase_Price"))
            else 0.0
        )
        c_sprice = (
            float(current_row.get("Selling_Price", 0.0))
            if pd.notna(current_row.get("Selling_Price"))
            else 0.0
        )
        c_loc = str(current_row.get("Purchase_Location", "Other"))
        c_ship = (
            float(current_row.get("Shipping_Cost", 0.0))
            if pd.notna(current_row.get("Shipping_Cost"))
            else 0.0
        )
        c_notes = str(current_row.get("Notes", ""))
        loc_index = (
            locations_list.index(c_loc) if c_loc in locations_list else 0
        )

        with st.form("edit_item_form"):
          st.write("Edit the details below:")
          new_name = st.text_input("Item Name", value=c_name)
          new_image = st.file_uploader(
              "Upload New Image (Leave empty to keep old image)",
              type=["jpg", "jpeg", "png"],
          )
          new_quantity = st.number_input(
              "Quantity", min_value=0, step=1, value=c_qty
          )
          new_purchase_price = st.number_input(
              "Purchase Price", min_value=0.0, step=1.0, value=c_pprice
          )
          new_selling_price = st.number_input(
              "Selling Price", min_value=0.0, step=1.0, value=c_sprice
          )
          new_purchase_loc = st.selectbox(
              "Purchase Location", locations_list, index=loc_index
          )
          new_shipping_cost = st.number_input(
              "Shipping Cost", min_value=0.0, step=1.0, value=c_ship
          )
          new_notes = st.text_area("Notes", value=c_notes)

          submitted_edit = st.form_submit_button("Update Item")
          if submitted_edit:
            if new_name == "":
              st.error("Please enter the Item Name!")
            else:
              cell = worksheet.find(str(selected_edit_id), in_column=1)
              if cell:
                row_num = cell.row
                img_data_new = (
                    get_image_base64(new_image)
                    if new_image
                    else df.loc[
                        df["Item_ID"].astype(str) == str(selected_edit_id),
                        "Image_URL",
                    ].values[0]
                )
                updated_row = [[
                    selected_edit_id,
                    new_name,
                    img_data_new,
                    new_quantity,
                    new_purchase_price,
                    new_selling_price,
                    new_purchase_loc,
                    new_shipping_cost,
                    new_notes,
                ]]
                worksheet.update(
                    values=updated_row, range_name=f"A{row_num}:I{row_num}"
                )
                st.success("Updated Successfully! Please refresh the page.")
              else:
                st.error("Item ID not found in the sheet.")
      else:
        st.info("No items available to edit.")

except Exception as e:
  st.error(f"Connection Error: {e}")
