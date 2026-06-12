"""
Thuoc chuc nang nao: Khoi dong app AI engine cho tro ly AI, chat, RAG va sinh van ban.
Vai tro backend: File nay dang ky app `ai_engine` voi Django va xac dinh thoi diem nap signal lien quan den cleanup file audio va cac side effect backend khac cua nhom AI.
Vai tro cua no trong frontend: Frontend chat/assistant/voice hoat dong on dinh vi app AI duoc khoi tao day du truoc khi cac API session, audio va tro ly nhan request.
Moi lien he voi nhung ham / source khac: Duoc nap tu `INSTALLED_APPS` trong `my_tennis_club.settings`; `ready()` tiep tuc import `ai_engine.signals`, noi voi `ChatAudioAttachment` trong `ai_engine.models`.
Tac dung: Dat diem khoi dong trung tam cho toan bo backend AI.
"""

from django.apps import AppConfig

# class AiEngineConfig là cấu hình khởi động của app ai_engine: khai báo tên app cho Django và cung cấp hook ready() để nạp signal đúng thời điểm.
# vd: khi Django nạp INSTALLED_APPS, app này được khởi tạo trước khi các API chat/assistant/audio nhận request.
class AiEngineConfig(AppConfig):
    """
    Thuoc chuc nang nao: Cau hinh khoi dong cho app nghiep vu AI.
    Vai tro backend: Lop nay gom metadata cua app `ai_engine` va cung cap hook `ready()` de backend AI co the dang ky signal dung thoi diem.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep, nhung danh sach session AI, file audio va cac luong tro ly phu thuoc vao viec app nay khoi tao dung.
    Moi lien he voi nhung ham / source khac: Django tao instance lop nay khi nap app; `ready()` phia duoi noi voi `ai_engine.signals`.
    Tac dung: Dinh nghia vo boc khoi dong ro rang cho module AI.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_engine'
    verbose_name = 'AI Engine'

    

    # def ready để nạp module signals của app sau khi Django khởi tạo xong, nhờ đó receiver dọn file audio (post_delete của ChatAudioAttachment) được đăng ký vào vòng đời model.
    # vd: ngay khi server khởi động, import .signals chạy nên xóa 1 bản ghi audio sẽ tự kéo theo xóa file .webm/.wav tương ứng.
    def ready(self):
        """
        Thuoc chuc nang nao: Nap signal phuc vu app AI.
        Vai tro backend: Ham nay import `ai_engine.signals` sau khi app registry san sang, de receiver cleanup file audio duoc dang ky vao vong doi model.
        Vai tro cua no trong frontend: Frontend huong loi gian tiep vi khi xoa audio tren man tro ly giong noi, tep vat ly cung duoc don dep dung luc.
        Moi lien he voi nhung ham / source khac: Import module `signals` trong cung app; receiver trong do lang nghe `post_delete` cua `ChatAudioAttachment`.
        Tac dung: Bao dam cac side effect cleanup cua app AI duoc kich hoat.
        """
        from . import signals
