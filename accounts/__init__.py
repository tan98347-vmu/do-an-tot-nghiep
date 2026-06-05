# Chức năng web liên quan: Hồ sơ cá nhân và Tài khoản, phòng ban và nhóm.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho hồ sơ cá nhân, tài khoản, phòng ban, nhóm và phân quyền truy cập, để các flow ở màn Hồ sơ cá nhân, màn đăng nhập/đăng ký và các dialog quản trị tài khoản, phòng ban, nhóm không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Hồ sơ cá nhân và Tài khoản, phòng ban và nhóm thay đổi đúng theo kết quả nghiệp vụ.
