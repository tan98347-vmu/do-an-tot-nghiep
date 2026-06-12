"""
Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
Vai tro backend: File `api/views/trash.py` giu hoac ho tro luong backend cho danh sach van ban, chi tiet van ban, version, chia se, luu tru, preview PDF, hom thu va xoa mem.
Vai tro cua no trong frontend: Cac man `/documents`, `/mailbox`, `/trash` va badge phe duyet doc ket qua do file nay cung cap hoac gian tiep lam thay doi.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`.
Tac dung: Bao dam vong doi van ban tu luc tao, chia se, xu ly hom thu toi luc phuc hoi hoac xoa vinh vien khong bi lech trang thai.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..trash_services import (
    list_trash_entries,
    permanently_delete_trash_items,
    purge_expired_trash,
    restore_trash_items,
)

# Là gì: `trash_entries` là endpoint REST của nhóm thùng rác, khôi phục và xóa vĩnh viễn văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `trash entries` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình thùng rác sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `purge_expired_trash`, `request.GET.get`, `list_trash_entries` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trash_entries(request):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `trash_entries` la endpoint hoac diem vao REST cua file `api/views/trash.py`, chiu trach nhiem xu ly ban ghi trong thung rac theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xu ly ban ghi trong thung rac tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `trash_restore`, `trash_delete` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xu ly ban ghi trong thung rac tren giao dien.
    """
    purge_expired_trash()
    category = request.GET.get('category') or 'all'
    query = request.GET.get('q') or ''
    payload = list_trash_entries(
        request.user,
        category=category,
        query=query,
    )
    return Response(payload)

# Là gì: `trash_restore` là endpoint REST của nhóm thùng rác, khôi phục và xóa vĩnh viễn văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm khôi phục dữ liệu về trạng thái hoạt động; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình thùng rác sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `purge_expired_trash`, `request.data.get`, `restore_trash_items` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trash_restore(request):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `trash_restore` la endpoint hoac diem vao REST cua file `api/views/trash.py`, chiu trach nhiem khoi phuc du lieu hoac trang thai cu theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can khoi phuc du lieu hoac trang thai cu tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `trash_entries`, `trash_delete` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac khoi phuc du lieu hoac trang thai cu tren giao dien.
    """
    purge_expired_trash()
    items = request.data.get('items')
    if not isinstance(items, list) or not items:
        return Response(
            {'detail': 'Danh sách item cần khôi phục không hợp lệ.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    payload = restore_trash_items(request.user, items)
    return Response(payload)

# Là gì: `trash_delete` là endpoint REST của nhóm thùng rác, khôi phục và xóa vĩnh viễn văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xóa hoặc đánh dấu xóa dữ liệu được chỉ định; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình thùng rác sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `purge_expired_trash`, `request.data.get`, `permanently_delete_trash_items` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trash_delete(request):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Ham `trash_delete` la endpoint hoac diem vao REST cua file `api/views/trash.py`, chiu trach nhiem xoa hoac don du lieu khong con hieu luc theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can xoa hoac don du lieu khong con hieu luc tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Dung cung cap voi cac ham `trash_entries`, `trash_restore` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac xoa hoac don du lieu khong con hieu luc tren giao dien.
    """
    purge_expired_trash()
    items = request.data.get('items')
    if not isinstance(items, list) or not items:
        return Response(
            {'detail': 'Danh sách item cần xóa vĩnh viễn không hợp lệ.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    payload = permanently_delete_trash_items(request.user, items)
    return Response(payload)
