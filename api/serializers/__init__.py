# Chức năng web liên quan: các chức năng quản trị và nghiệp vụ đang hiển thị trên web.
# Vai trò backend trong luồng: Tệp này chốt contract JSON cho nghiệp vụ backend đang phục vụ các chức năng web hiện hành; mọi bảng, card, badge, dialog và form ở các màn web đang hiển thị chức năng nghiệp vụ hiện hành đều đọc hoặc submit dữ liệu theo cấu trúc tại đây.
# Đầu vào/đầu ra chính: Nhận model hoặc payload trung gian, ánh xạ thành field mà web dùng cho bảng, card, detail, quyền nút, timeline, badge trạng thái và dữ liệu submit ngược về backend.
# Người dùng sẽ thấy trên web: Web ở các chức năng các chức năng quản trị và nghiệp vụ đang hiển thị trên web nhận đúng field, đúng nhãn trạng thái, đúng cờ quyền và đúng dữ liệu submit để render nhất quán.
