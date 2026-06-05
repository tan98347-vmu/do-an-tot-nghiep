"""
Thuoc chuc nang nao: Signal hau xu ly cho tai nguyen AI, hien tai tap trung vao file audio cua tro ly.
Vai tro backend: File nay dang ky receiver de khi ban ghi `ChatAudioAttachment` bi xoa thi tep audio tuong ung trong storage cung duoc xoa theo, tranh ro rac file.
Vai tro cua no trong frontend: Khi nguoi dung xoa ban ghi audio tren giao dien tro ly giong noi, frontend thay ket qua day du vi ca metadata lan tep vat ly deu bien mat.
Moi lien he voi nhung ham / source khac: Duoc import boi `ai_engine.apps.AiEngineConfig.ready`; nghe su kien `post_delete` cho `ChatAudioAttachment` trong `ai_engine.models`.
Tac dung: Dong bo trang thai database va file storage cho tinh nang audio AI.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import ChatAudioAttachment

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
