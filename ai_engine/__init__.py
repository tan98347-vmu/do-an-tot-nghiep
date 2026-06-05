# Chức năng web liên quan: Trợ lý AI, Hỏi đáp tài liệu và Sinh văn bản từ mẫu.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho trợ lý AI, RAG, OCR/prefill và sinh văn bản từ mẫu, để các flow ở màn Trợ lý AI, Hỏi đáp tài liệu, kết quả RAG và luồng Sinh văn bản từ mẫu không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Trợ lý AI, Hỏi đáp tài liệu và Sinh văn bản từ mẫu thay đổi đúng theo kết quả nghiệp vụ.
