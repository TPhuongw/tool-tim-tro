import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# --- CẤU HÌNH ---
SHEET_NAME = "danhsachtro" 

# --- XỬ LÝ KẾT NỐI ---
@st.cache_resource
def get_credentials():
    if "gcp_service_account" in st.secrets:
        return st.secrets["gcp_service_account"]
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "credentials.json")
    if os.path.exists(json_path):
        return json_path
    return None

@st.cache_resource
def connect_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_source = get_credentials()
    
    if not creds_source:
        st.error("❌ Lỗi: Không tìm thấy Key (Secrets hoặc file json).")
        st.stop()
        
    if isinstance(creds_source, dict):
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_source, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_source, scope)
        
    client = gspread.authorize(creds)
    return client

# Cấu hình AI
# Cấu hình AI
# Chỉ lấy Key từ Secrets (Két sắt), không điền trực tiếp ở đây
if "gemini_api_key" in st.secrets:
    api_key = st.secrets["gemini_api_key"]
else:
    # Nếu dòng này đang chứa key thật, hãy xóa nó đi và để trống hoặc để chuỗi giả
    api_key = "KEY_DU_PHONG_DA_XOA"
genai.configure(api_key=api_key)
# Dùng bản 1.5 Flash cho ổn định trên Cloud
model = genai.GenerativeModel('gemini-2.5-flash')

# --- HÀM XỬ LÝ AI (ĐÃ SỬA LỖI ĐỌC TIN) ---
def parse_rental_ad(ad_text):
    prompt = f"""
    Trích xuất thông tin trọ thành JSON phẳng.
    1. ĐỊA CHỈ: Chỉ lấy số nhà, đường, phường, quận. Cắt bỏ "gần trường", "cách chợ".
    2. GIÁ ĐIỆN: Nếu thấy "giá dân" -> ghi "Giá dân".
    
    JSON keys: gia_thue, dia_chi, dien_tich, noi_that, phi_dien, phi_dich_vu, luu_y, uu_diem.
    Nội dung:
    ---
    {ad_text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # --- BƯỚC QUAN TRỌNG: LÀM SẠCH JSON ---
        # AI thường trả về ```json ở đầu và ``` ở cuối, phải cắt bỏ đi mới đọc được
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"): # Phòng trường hợp nó chỉ có ```
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip() # Cắt khoảng trắng thừa lần nữa
        # ---------------------------------------

        return json.loads(text)
    except Exception as e:
        # In lỗi chi tiết ra màn hình để debug
        st.error(f"⚠️ Lỗi chi tiết từ Google: {e}")
        st.write("Dữ liệu AI trả về (bị lỗi):", response.text if 'response' in locals() else "Không có phản hồi")
        return None

# --- HÀM GHI SHEET ---
def save_to_sheet(data, link, client):
    try:
        sheet = client.open(SHEET_NAME).sheet1
        existing_data = sheet.get_all_values()
        stt = len(existing_data) if existing_data else 1
        
        row = [
            stt,
            data.get("gia_thue", ""),
            data.get("dia_chi", ""),
            data.get("dien_tich", ""),
            data.get("noi_that", ""),
            data.get("phi_dien", ""),
            data.get("phi_dich_vu", ""),
            data.get("luu_y", ""),
            data.get("uu_diem", ""),
            link,
            "Chưa xem", ""
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Lỗi ghi Sheet: {e}")
        return False

# --- GIAO DIỆN ---
st.set_page_config(page_title="Tool Tìm Trọ Cloud", page_icon="☁️")
st.title("☁️ Trợ Lý Tìm Trọ (Online)")

with st.form("main_form"):
    link_input = st.text_input("🔗 Link bài viết:")
    text_input = st.text_area("📝 Nội dung tin:", height=150)
    submitted = st.form_submit_button("🚀 Lưu vào Sheet", type="primary")

if submitted:
    if not text_input:
        st.warning("Chưa có nội dung!")
    else:
        with st.spinner("Đang xử lý trên Cloud..."):
            data = parse_rental_ad(text_input)
            if data:
                st.success("Xong!")
                # st.dataframe([data]) 
                client = connect_google_sheet()
                save_to_sheet(data, link_input, client)
                st.toast("Đã lưu!", icon="🎉")
            else:
                st.error("Không đọc được tin. Hãy xem lỗi chi tiết bên trên!")


