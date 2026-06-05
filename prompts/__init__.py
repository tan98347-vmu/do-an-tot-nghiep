# Chức năng web liên quan: Cấu hình AI.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho cấu hình AI, prompt và ngữ cảnh dùng chung cho web, để các flow ở màn Cấu hình AI, các form chỉnh model/context và những luồng AI đọc cấu hình này không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Cấu hình AI thay đổi đúng theo kết quả nghiệp vụ.
