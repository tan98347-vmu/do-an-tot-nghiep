
# Chức năng web liên quan: Trợ lý AI, Hỏi đáp tài liệu và Sinh văn bản từ mẫu.
# Vai trò backend trong luồng: Tệp này chạy tác vụ nền hoặc lệnh vận hành cho trợ lý AI, RAG, OCR/prefill và sinh văn bản từ mẫu; kết quả của nó thường làm mới hoặc sửa dữ liệu mà màn Trợ lý AI, Hỏi đáp tài liệu, kết quả RAG và luồng Sinh văn bản từ mẫu đang đọc.
# Đầu vào/đầu ra chính: Nhận tham số CLI, chạy job nền và cập nhật dữ liệu hoặc cấu hình mà các màn web sẽ đọc lại sau đó.
# Người dùng sẽ thấy trên web: Sau khi tác vụ chạy xong, dữ liệu nền mà các chức năng Trợ lý AI, Hỏi đáp tài liệu và Sinh văn bản từ mẫu đang dùng sẽ được làm mới hoặc sửa về trạng thái đúng.
