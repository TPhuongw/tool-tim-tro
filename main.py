import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# --- 1. CẤU HÌNH ---
GEMINI_API_KEY = "AIzaSyDhDa6TXgqVBLuvhWn6qD7gPfonn4Yru_U" 
SHEET_NAME = "danhsachtro" 
CREDENTIALS_FILE = "credentials.json"

# --- 2. THIẾT LẬP KẾT NỐI ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(CURRENT_DIR, CREDENTIALS_FILE)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

@st.cache_resource
def connect_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if not os.path.exists(CREDENTIALS_PATH):
        st.error(f"❌ Lỗi: Không tìm thấy file '{CREDENTIALS_FILE}'")
        st.stop()
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)
    return client

# --- 3. HÀM XỬ LÝ AI ---
def parse_rental_ad(ad_text):
    prompt = f"""
    Bạn là trợ lý lọc tin trọ. Trích xuất thông tin thành JSON phẳng.
    
    YÊU CẦU ĐẶC BIỆT:
    1. ĐỊA CHỈ: Chỉ lấy số nhà, đường, phường, quận. Cắt bỏ các đoạn "gần trường A", "cách chợ B".
    2. GIÁ ĐIỆN: Nếu thấy "giá dân", "giá nhà nước" -> ghi nguyên văn cụm từ đó. Nếu có giá số -> ghi số (VD: 4k/số).

    Các trường cần lấy (key json):
    - gia_thue: Giá phòng.
    - dia_chi: Địa chỉ ngắn gọn.
    - dien_tich: Diện tích.
    - noi_that: Nội thất tóm tắt.
    - phi_dien: Giá điện.
    - phi_dich_vu: Phí khác (Nước, mạng, rác...).
    - luu_y: Lưu ý (chung chủ, cọc...).
    - uu_diem: Điểm cộng.

    Nội dung tin:
    ---
    {ad_text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        return json.loads(text)
    except Exception as e:
        return None

# --- 4. HÀM GHI SHEET (CẬP NHẬT CỘT K, L) ---
def save_to_sheet(data, link, client):
    try:
        sheet = client.open(SHEET_NAME).sheet1
        existing_data = sheet.get_all_values()
        
        stt = len(existing_data) if existing_data else 1
        
        # Sắp xếp dữ liệu theo đúng thứ tự cột mới
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
            "Chưa xem",  # Cột K: Mặc định điền là "Chưa xem"
            ""           # Cột L: Chấm điểm (để trống cho bạn tự điền)
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Lỗi ghi Sheet: {e}")
        return False

def reset_header(client):
    """Hàm tạo lại tiêu đề bảng với 12 cột"""
    try:
        sheet = client.open(SHEET_NAME).sheet1
        sheet.clear()
        # Danh sách tiêu đề mới
        header = [
            "STT", "Giá thuê", "Địa chỉ", "Diện tích", "Nội thất", 
            "Tiền Điện", "Phí Dịch Vụ", "Lưu ý", "Ưu điểm", "Link bài viết",
            "Trạng thái", "Chấm điểm (Thang 10)"
        ]
        sheet.append_row(header)
        return True
    except Exception as e:
        st.error(f"Lỗi tạo tiêu đề: {e}")
        return False

# --- 5. GIAO DIỆN WEB ---
st.set_page_config(page_title="Tool Tìm Trọ V4", page_icon="🏠")
st.title("🏠 Trợ Lý Tìm Trọ (V4)")

with st.expander(""):
    st.warning("")
    if st.button(""):
        client = connect_google_sheet()
        if reset_header(client):
            st.success("Đã cập nhật bảng thành công! Hãy vào Google Sheet cài đặt Dropdown nhé.")

with st.form("main_form"):
    link_input = st.text_input("🔗 Link bài viết:")
    text_input = st.text_area("📝 Nội dung tin:", height=150)
    submitted = st.form_submit_button("🚀 Lưu vào Sheet", type="primary")

if submitted:
    if not text_input:
        st.warning("Chưa có nội dung!")
    else:
        with st.spinner("Đang xử lý..."):
            data = parse_rental_ad(text_input)
            if data:
                st.success("Xong!")
                st.dataframe([data])
                client = connect_google_sheet()
                save_to_sheet(data, link_input, client)
                st.toast("Đã lưu tin mới!", icon="🎉")