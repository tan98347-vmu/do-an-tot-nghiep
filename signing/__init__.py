
# Chức năng web liên quan: Yêu cầu ký, PDF đã ký, Hòm thư và Ủy quyền ký số.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho đề xuất ký, nhiệm vụ ký, PDF đã ký, xác minh chữ ký và ủy quyền ký số, để các flow ở màn Yêu cầu ký, chi tiết ký, PDF đã ký, dialog đề xuất ký, dialog chọn người ký và màn Ủy quyền ký số không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Yêu cầu ký, PDF đã ký, Hòm thư và Ủy quyền ký số thay đổi đúng theo kết quả nghiệp vụ.
