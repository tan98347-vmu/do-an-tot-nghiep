# Chức năng web liên quan: các chức năng quản trị và nghiệp vụ đang hiển thị trên web.
# Vai trò backend trong luồng: Tệp này chốt contract JSON cho nghiệp vụ backend đang phục vụ các chức năng web hiện hành; mọi bảng, card, badge, dialog và form ở các màn web đang hiển thị chức năng nghiệp vụ hiện hành đều đọc hoặc submit dữ liệu theo cấu trúc tại đây.
# Đầu vào/đầu ra chính: Nhận model hoặc payload trung gian, ánh xạ thành field mà web dùng cho bảng, card, detail, quyền nút, timeline, badge trạng thái và dữ liệu submit ngược về backend.
# Người dùng sẽ thấy trên web: Web ở các chức năng các chức năng quản trị và nghiệp vụ đang hiển thị trên web nhận đúng field, đúng nhãn trạng thái, đúng cờ quyền và đúng dữ liệu submit để render nhất quán.
'''
Trong Django REST Framework, các file trong api/serializers/ đóng vai trò lớp chuyển đổi và kiểm tra dữ liệu tại biên API. Chúng khác với model, view và service ở trách nhiệm.

  Flutter
     ↕ JSON
  Serializer
     ↕ Python object
  View
     ↕
  Service
     ↕
  Model + Database

  ## Serializer là gì?

  Serializer chuyển đổi hai chiều:

  Model/Python object → JSON trả cho Flutter
  JSON từ Flutter → dữ liệu Python đã kiểm tra

  Ví dụ TemplateManualEditSessionSerializer chuyển đối tượng session thành:

  {
    "id": 12,
    "template": 5,
    "status": "active",
    "editor_url": "https://.../cool.html?...",
    "is_active": true
  }

  Flutter không hiểu trực tiếp Django model, QuerySet, datetime hay FileField, nên cần serializer.

  ## Serializer khác model

  Model như:

  class TemplateManualEditSession(models.Model):
      status = models.CharField(...)
      expires_at = models.DateTimeField(...)

  Model có trách nhiệm:

  - Định nghĩa bảng database.
  - Định nghĩa cột và quan hệ.
  - Lưu, đọc, cập nhật bản ghi.
  - Ràng buộc dữ liệu ở mức database/model.

  Serializer:

  class TemplateManualEditSessionSerializer(serializers.ModelSerializer):
      editor_url = serializers.SerializerMethodField()

  Có trách nhiệm:

  - Chọn trường nào được trả ra API.
  - Chuyển model thành JSON.
  - Ẩn dữ liệu nhạy cảm như access_token.
  - Thêm trường phục vụ UI như editor_url.
  - Kiểm tra dữ liệu client gửi vào.

  Serializer không tạo bảng database.

  ## Serializer khác view

  View nhận HTTP request:

  def template_manual_edit_session_finish(request, session_id):

  Nó chịu trách nhiệm:

  - Xác thực user.
  - Đọc URL parameter.
  - Chọn HTTP method.
  - Gọi serializer kiểm tra request.
  - Gọi service xử lý.
  - Trả Response và HTTP status.

  Ví dụ:

  serializer = TemplateManualEditFinishSerializer(data=request.data)
  serializer.is_valid(raise_exception=True)

  finish_template_manual_edit_session(
      change_note=serializer.validated_data['change_note']
  )

  Serializer kiểm tra change_note; view điều phối request.

  ## Serializer khác service

  Service chứa nghiệp vụ thật:

  finish_template_manual_edit_session()

  Nó thực hiện:

  - Đọc working copy.
  - Tạo snapshot phiên bản cũ.
  - Tăng version.
  - Thay file DOCX chính.
  - Đóng session.
  - Xóa file tạm.

  Serializer không nên thực hiện các nghiệp vụ nhiều bước như vậy. Nó chỉ chuẩn hóa đầu vào và đầu ra API.
'''