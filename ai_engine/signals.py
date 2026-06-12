"""
 ai_engine/signals.py:1 chuyên dọn file audio vật lý khi bản ghi ChatAudioAttachment bị xóa khỏi database.

  Nó thuộc chức năng:

  - Giọng nói AI tại /chat/voice.
  - Thư viện audio tại /chat/audio.
  - File ghi âm được đính kèm vào phiên trợ lý.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import ChatAudioAttachment

# def _delete_chat_audio_file là receiver chạy sau khi xóa bản ghi ChatAudioAttachment (post_delete); nó tìm và xóa luôn tệp audio vật lý trong storage để tránh file mồ côi khi metadata đã bị xóa.
# vd: xóa ChatAudioAttachment #12 (audio_file=chat_audio/abc.webm) -> receiver xóa luôn file abc.webm trong storage.
@receiver(post_delete, sender=ChatAudioAttachment)
def _delete_chat_audio_file(sender, instance, **kwargs):
    """
    Thuoc chuc nang nao: Cleanup tep audio sau khi xoa ban ghi audio tro ly.
    Vai tro backend: Receiver nay doc `audio_file` tu instance vua bi xoa, kiem tra tep co ton tai tren storage hay khong, roi xoa tep vat ly neu co.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep, nhung khi user xoa audio trong lich su tro ly thi se khong con gap tinh trang ban ghi da mat ma file van ton tai.
    Moi lien he voi nhung ham / source khac: Duoc Django signal framework goi sau `post_delete(ChatAudioAttachment)`; phu thuoc vao field `audio_file` trong `ai_engine.models.ChatAudioAttachment`.
    Tac dung: Ngan ro rac storage do file audio mo côi sau khi xoa du lieu.
    """
    file_field = getattr(instance, 'audio_file', None)
    if not file_field:
        return
    try:
        storage = file_field.storage
        name = file_field.name
        if name and storage.exists(name):
            storage.delete(name)
    except Exception:
        pass
