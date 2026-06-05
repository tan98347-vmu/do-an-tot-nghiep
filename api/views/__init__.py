# Chức năng web liên quan: các chức năng quản trị và nghiệp vụ đang hiển thị trên web.
# Vai trò backend trong luồng: Tệp này là lớp nhận request trực tiếp từ web cho nghiệp vụ backend đang phục vụ các chức năng web hiện hành; nó quyết định API nào cấp dữ liệu, nhận action và trả lỗi về cho các màn web đang hiển thị chức năng nghiệp vụ hiện hành.
# Đầu vào/đầu ra chính: Nhận request, query params hoặc body từ client, áp quyền, lọc dữ liệu theo đúng ngữ cảnh người dùng rồi trả JSON hoặc HTTP status để web dựng list, detail, form, preview hoặc thông báo lỗi.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng các chức năng quản trị và nghiệp vụ đang hiển thị trên web thay đổi đúng theo kết quả nghiệp vụ.
