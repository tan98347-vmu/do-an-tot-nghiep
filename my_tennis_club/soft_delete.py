"""
Thuoc chuc nang nao: Ha tang soft-delete dung chung cho cac model backend co cot `is_deleted`.
Vai tro backend: File nay cung cap manager loc san nhung ban ghi da bi danh dau xoa mem, de service va API co the tiep tuc luu lich su du lieu nhung khong vo tinh tra ve ban ghi da an.
Vai tro cua no trong frontend: Frontend khong goi truc tiep module nay, nhung danh sach tai lieu, mau, thong bao hay ban ghi quan tri se chi nhan du lieu dang hoat dong neu model cua chung su dung manager nay.
Moi lien he voi nhung ham / source khac: Duoc gan vao model qua thuoc tinh manager; cac queryset sinh ra tu viewset, serializer hoac helper quyen se duoc huong loi tu bo loc mac dinh trong `get_queryset`.
Tac dung: Tap trung quy tac an ban ghi bi xoa mem vao mot cho duy nhat thay vi lap lai dieu kien `is_deleted=False` o nhieu API.
"""

from django.db import models

class ActiveOnlyManager(models.Manager):
    """
    Thuoc chuc nang nao: Soft-delete va truy van mac dinh cho model can an ban ghi da xoa.
    Vai tro backend: Manager nay ghi de cach tao queryset mac dinh de chi tra ve du lieu con hieu luc, giup cac model dung chung co hanh vi dong nhat khi truy van.
    Vai tro cua no trong frontend: Moi man danh sach o frontend se nhan du lieu "sach" hon vi nhung ban ghi da xoa mem khong con xuat hien trong cac API su dung manager nay.
    Moi lien he voi nhung ham / source khac: Cac model trong backend co the gan `objects = ActiveOnlyManager()`; moi truy van tiep theo tu serializer, permission helper hay view se chay qua `get_queryset`.
    Tac dung: Bien quy tac loc ban ghi song thanh hanh vi mac dinh cua model.
    """
    def get_queryset(self):
        """
        Thuoc chuc nang nao: Soft-delete va truy van mac dinh cho model can an ban ghi da xoa.
        Vai tro backend: Ham nay chen them dieu kien `is_deleted=False` vao queryset goc cua Django manager, de moi truy van mac dinh deu bo qua ban ghi da danh dau xoa mem.
        Vai tro cua no trong frontend: Frontend thay doi gian tiep qua viec danh sach va bo loc tren giao dien khong hien lai du lieu da "xoa" du du lieu goc van con trong database.
        Moi lien he voi nhung ham / source khac: Duoc goi tu co che truy van cua `models.Manager`; cac view, serializer, admin query va permission helper su dung manager nay deu nhan queryset da loc.
        Tac dung: Bien viec loc ban ghi con hieu luc thanh hanh vi tu dong o lop truy van.
        """
        return super().get_queryset().filter(is_deleted=False)
