# Tệp này dùng để: duy trì logic trong tệp test_cam.py.
# Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
# Vai trò trong hệ thống: Đây là một thành phần của hệ thống.
# Tác dụng khi hệ thống vận hành: giữ cho luồng nghiệp vụ thuộc `test_cam.py` chạy ổn định trong runtime.

import ollama
from google.colab import files
import os

print("👇 Hãy chọn 1 bức ảnh (CCCD, Hợp đồng, Bảng biểu) từ máy tính:")
uploaded = files.upload()

# Lấy đường dẫn file ảnh vừa tải
image_path = list(uploaded.keys())[0]
print(f"✅ Đã tải lên ảnh: {image_path}")
print("🚀 Đang dùng GLM-OCR để đọc ảnh (Chạy 100% Local bằng VRAM GPU)...")

# Gọi mô hình qua thư viện python
try:
    response = ollama.chat(
        model='glm-ocr',
        messages=[{
            'role': 'user',
            'content': 'Bạn là hệ thống bóc tách dữ liệu OCR. Hãy trích xuất toàn bộ văn bản trong bức ảnh này, giữ nguyên định dạng bảng biểu nếu có. KHÔNG giải thích gì thêm.',
            'images': [image_path]
        }]
    )

    print("\n" + "="*50)
    print("🟢 KẾT QUẢ TỪ GLM-OCR (OLLAMA):")
    print("="*50)
    print(response['message']['content'])
    print("="*50)

# Chặn lỗi ở biên xử lý để hệ thống còn cơ hội ghi log và trả phản hồi lỗi kiểm soát được.

except Exception as e:
    print(f"❌ Có lỗi xảy ra: {e}")
