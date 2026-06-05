# Chức năng web liên quan: Tạo mẫu văn bản, Mẫu dùng chung, Mẫu phòng ban của tôi, Mẫu riêng của tôi, Mẫu yêu thích và Tất cả mẫu (Admin).
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho danh sách mẫu, chi tiết mẫu, form tạo mẫu, bulk upload và preview biến, để các flow ở các tab Mẫu dùng chung, Mẫu phòng ban, Mẫu riêng, Mẫu yêu thích, màn chi tiết mẫu, form tạo mẫu và bulk upload không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Tạo mẫu văn bản, Mẫu dùng chung, Mẫu phòng ban của tôi, Mẫu riêng của tôi, Mẫu yêu thích và Tất cả mẫu (Admin) thay đổi đúng theo kết quả nghiệp vụ.

default_app_config = 'document_templates.runtime_app.DocumentTemplatesRuntimeConfig'
