"""
Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
Vai tro backend: File `api/serializers/documents.py` giu hoac ho tro luong backend cho danh sach van ban, chi tiet van ban, version, chia se, luu tru, preview PDF, hom thu va xoa mem.
Vai tro cua no trong frontend: Cac man `/documents`, `/mailbox`, `/trash` va badge phe duyet doc ket qua do file nay cung cap hoac gian tiep lam thay doi.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`.
Tac dung: Bao dam vong doi van ban tu luc tao, chia se, xu ly hom thu toi luc phuc hoi hoac xoa vinh vien khong bi lech trang thai.
"""

import json
import re

from rest_framework import serializers
from accounts.peer_permissions import get_peer_permission_level, max_peer_permission_level
from accounts.permissions import can_delete_document, can_edit_document
from accounts.tenancy import get_user_company
from documents.edit_lock_state import get_document_edit_lock_state
from documents.models import (
    Document,
    DocumentVersion,
    DocumentFavorite,
    DocumentMailboxEntry,
    DocumentMailboxThread,
    DOC_STATUS_CHOICES,
)
from signing.assistant_quick_sign import (
    build_quick_sign_plan_payload,
    get_latest_quick_sign_plan,
    refresh_quick_sign_plan,
)


def _coerce_list_payload(raw_value):
    if raw_value in (None, '', []):
        return []
    if isinstance(raw_value, str):
        raw_text = raw_value.strip()
        if not raw_text:
            return []
        try:
            return _coerce_list_payload(json.loads(raw_text))
        except Exception:
            return [item.strip() for item in raw_text.split(',') if item.strip()]
    if isinstance(raw_value, dict):
        ordered_items = sorted(
            raw_value.items(),
            key=lambda item: (
                0 if str(item[0]).isdigit() else 1,
                int(str(item[0])) if str(item[0]).isdigit() else str(item[0]),
            ),
        )
        flattened = []
        for _, item_value in ordered_items:
            flattened.extend(_coerce_list_payload(item_value))
        return flattened
    if isinstance(raw_value, (list, tuple, set)):
        flattened = []
        for item in raw_value:
            flattened.extend(_coerce_list_payload(item))
        return flattened
    return [raw_value]


def _normalize_document_tags(raw_tags):
    normalized = []
    seen = set()
    for raw_tag in raw_tags or []:
        tag = ' '.join(str(raw_tag or '').strip().split())
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
    return normalized


def _document_permission_for_user(user, document) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if document.owner_id == user.id:
        return 'owner'
    if user.is_superuser:
        return 'delete'

    base_level = 'view'
    if can_delete_document(user, document):
        base_level = 'delete'
    elif can_edit_document(user, document):
        base_level = 'edit'

    peer_level = get_peer_permission_level(user, document)
    return max_peer_permission_level(base_level, peer_level) or base_level

class DocumentVersionSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentVersionSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/documents.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DocumentVersionSerializer`.
    """
    created_by_name = serializers.SerializerMethodField()

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/documents.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentVersionSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = DocumentVersion
        fields = ('id', 'version_number', 'content', 'change_note',
                  'variables_used', 'created_by_name', 'created_at', 'is_hidden',
                  'output_file')

    

    def get_created_by_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_created_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentVersionSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong lop `DocumentVersionSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return ''

class DocumentListSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentListSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/documents.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DocumentListSerializer`.
    """
    owner_name = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source='owner.id', read_only=True)
    group_id = serializers.SerializerMethodField()
    template_title = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    my_permission = serializers.SerializerMethodField()
    signing_status = serializers.SerializerMethodField()
    can_forward_now = serializers.SerializerMethodField()
    peer_share_status = serializers.CharField(read_only=True)
    peer_audience_count = serializers.SerializerMethodField()
    is_peer_shared_to_me = serializers.SerializerMethodField()

    def get_peer_audience_count(self, obj):
        return obj.audience_members.count() if hasattr(obj, 'audience_members') else 0

    def get_is_peer_shared_to_me(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        u = getattr(request, 'user', None) if request else None
        if not u or not u.is_authenticated or obj.owner_id == u.pk:
            return False
        return obj.audience_members.filter(user=u).exists()

    def get_my_permission(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        user = getattr(request, 'user', None) if request else None
        return _document_permission_for_user(user, obj)


    class Meta:
        model = Document
        fields = ('id', 'title', 'doc_number', 'status', 'status_display', 'visibility',
                  'share_status', 'owner_id', 'owner_name', 'group_id', 'group_name',
                  'template_title', 'department_name', 'category_name', 'notes', 'tags', 'source_type', 'is_archived',
                  'version_number', 'version_count',
                  'is_favorite', 'can_edit', 'can_delete', 'my_permission', 'signing_status', 'can_forward_now',
                  'peer_share_status', 'peer_audience_count', 'is_peer_shared_to_me',
                  'created_at', 'updated_at')

    

    def get_owner_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_owner_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_group_id`, `get_template_title`, `get_status_display` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.owner.get_full_name() or obj.owner.username

    

    def get_group_id(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_group_id` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_status_display` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.group_id

    

    def get_template_title(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_template_title` xu ly phan xu ly du lieu hoac thao tac lien quan toi mau van ban cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly du lieu hoac thao tac lien quan toi mau van ban nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_group_id`, `get_status_display` trong cung lop.
        Tac dung: Giu cho qua trinh xu ly du lieu hoac thao tac lien quan toi mau van ban dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.template.title if obj.template else None

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None

    

    def get_status_display(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_status_display` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_group_id`, `get_template_title` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.get_status_display()

    

    def get_version_count(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_version_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_group_id`, `get_template_title` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.versions.count()

    

    def get_is_favorite(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_is_favorite` xu ly phan danh dau hoac bo danh dau yeu thich cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc danh dau hoac bo danh dau yeu thich nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_group_id`, `get_template_title` trong cung lop.
        Tac dung: Giu cho qua trinh danh dau hoac bo danh dau yeu thich dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return DocumentFavorite.objects.filter(user=request.user, document=obj).exists()
        return False

    

    def get_can_edit(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_can_edit` xu ly phan chinh sua du lieu theo input vua gui len cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc chinh sua du lieu theo input vua gui len nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_group_id`, `get_template_title` trong cung lop.
        Tac dung: Giu cho qua trinh chinh sua du lieu theo input vua gui len dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_edit_document(request.user, obj)
        return False

    

    def get_can_delete(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_can_delete` xu ly phan xoa hoac don du lieu khong con hieu luc cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xoa hoac don du lieu khong con hieu luc nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_group_id`, `get_template_title` trong cung lop.
        Tac dung: Giu cho qua trinh xoa hoac don du lieu khong con hieu luc dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_delete_document(request.user, obj)
        return False

    

    def get_signing_status(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_signing_status` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_group_id`, `get_template_title` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return 'signed' if obj.signed_pdf_records.filter(
            source_version_number=obj.version_number,
            verification_status='safe',
        ).exists() else 'unsigned'

    

    def get_can_forward_now(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_can_forward_now` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_group_id`, `get_template_title` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return self.get_signing_status(obj) == 'signed'

class DocumentDetailSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentDetailSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/documents.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DocumentDetailSerializer`.
    """
    owner_name = serializers.SerializerMethodField()
    template_title = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    has_file = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    my_permission = serializers.SerializerMethodField()
    mailbox_thread_count = serializers.SerializerMethodField()
    signing_status = serializers.SerializerMethodField()
    can_forward_now = serializers.SerializerMethodField()
    assistant_action = serializers.SerializerMethodField()
    can_manual_edit = serializers.SerializerMethodField()
    can_resume_manual_edit = serializers.SerializerMethodField()
    manual_edit_active = serializers.SerializerMethodField()
    manual_edit_session_id = serializers.SerializerMethodField()
    manual_edit_session_status = serializers.SerializerMethodField()
    manual_edit_lock_message = serializers.SerializerMethodField()
    manual_edit_locked_by_name = serializers.SerializerMethodField()
    prompt_id = serializers.SerializerMethodField()
    prompt_title = serializers.SerializerMethodField()
    applied_prompt = serializers.SerializerMethodField()
    applied_user_rules = serializers.SerializerMethodField()
    applied_prompt_snapshot = serializers.JSONField(read_only=True)
    peer_share_status = serializers.CharField(read_only=True)
    peer_share_approver_note = serializers.CharField(read_only=True)
    peer_audience_count = serializers.SerializerMethodField()
    is_peer_shared_to_me = serializers.SerializerMethodField()

    def get_peer_audience_count(self, obj):
        return obj.audience_members.count() if hasattr(obj, 'audience_members') else 0

    def get_is_peer_shared_to_me(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        u = getattr(request, 'user', None) if request else None
        if not u or not u.is_authenticated or obj.owner_id == u.pk:
            return False
        return obj.audience_members.filter(user=u).exists()

    def get_my_permission(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        user = getattr(request, 'user', None) if request else None
        return _document_permission_for_user(user, obj)


    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/documents.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentDetailSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = Document
        fields = ('id', 'title', 'content', 'doc_number', 'status', 'visibility',
                  'share_status', 'owner', 'owner_name', 'template', 'template_title',
                  'department', 'department_name', 'category', 'category_name',
                  'notes', 'tags', 'is_archived', 'archived_at',
                  'has_file', 'group', 'source_type', 'version_number', 'version_count',
                  'group_name',
                  'is_favorite', 'can_edit', 'can_delete', 'my_permission', 'mailbox_thread_count',
                  'signing_status', 'can_forward_now', 'assistant_action',
                  'can_manual_edit', 'can_resume_manual_edit',
                  'manual_edit_active', 'manual_edit_session_id',
                  'manual_edit_session_status', 'manual_edit_lock_message',
                  'manual_edit_locked_by_name',
                  'prompt_id', 'prompt_title', 'applied_prompt', 'applied_user_rules', 'applied_prompt_snapshot',
                  'peer_share_status', 'peer_share_approver_note',
                  'peer_audience_count', 'is_peer_shared_to_me',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'owner', 'doc_number', 'is_archived', 'archived_at', 'created_at', 'updated_at')

    def _lock_state(self, obj):
        cache = getattr(self, '_manual_edit_lock_cache', None)
        if cache is None:
            cache = {}
            self._manual_edit_lock_cache = cache
        cached = cache.get(obj.pk)
        if cached is not None:
            return cached
        request = self.context.get('request')
        state = get_document_edit_lock_state(obj, user=getattr(request, 'user', None))
        cache[obj.pk] = state
        return state

    

    def get_owner_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_owner_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_template_title`, `get_has_file`, `get_version_count` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.owner.get_full_name() or obj.owner.username

    def get_prompt_id(self, obj):
        return obj.prompt_id

    def get_prompt_title(self, obj):
        return obj.prompt.title if obj.prompt else None

    def get_applied_prompt(self, obj):
        if obj.prompt_id and obj.prompt:
            return {
                'id': obj.prompt_id,
                'title': obj.prompt.title,
            }
        snapshot = obj.applied_prompt_snapshot or {}
        if isinstance(snapshot, dict) and snapshot.get('prompt_id'):
            return {
                'id': snapshot.get('prompt_id'),
                'title': snapshot.get('title'),
            }
        return None

    def get_applied_user_rules(self, obj):
        snap = obj.applied_prompt_snapshot or {}
        if isinstance(snap, dict):
            return (snap.get('raw_user_text') or '').strip()
        return ''

    def get_template_title(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_template_title` xu ly phan xu ly du lieu hoac thao tac lien quan toi mau van ban cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly du lieu hoac thao tac lien quan toi mau van ban nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_has_file`, `get_version_count` trong cung lop.
        Tac dung: Giu cho qua trinh xu ly du lieu hoac thao tac lien quan toi mau van ban dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.template.title if obj.template else None

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None

    

    def get_has_file(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_has_file` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_version_count` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return bool(obj.output_file)

    

    def get_version_count(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_version_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_has_file` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.versions.count()

    

    def get_is_favorite(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_is_favorite` xu ly phan danh dau hoac bo danh dau yeu thich cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc danh dau hoac bo danh dau yeu thich nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_has_file` trong cung lop.
        Tac dung: Giu cho qua trinh danh dau hoac bo danh dau yeu thich dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return DocumentFavorite.objects.filter(user=request.user, document=obj).exists()
        return False

    

    def get_can_edit(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_can_edit` xu ly phan chinh sua du lieu theo input vua gui len cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc chinh sua du lieu theo input vua gui len nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_has_file` trong cung lop.
        Tac dung: Giu cho qua trinh chinh sua du lieu theo input vua gui len dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_edit_document(request.user, obj)
        return False

    

    def get_can_delete(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_can_delete` xu ly phan xoa hoac don du lieu khong con hieu luc cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xoa hoac don du lieu khong con hieu luc nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_has_file` trong cung lop.
        Tac dung: Giu cho qua trinh xoa hoac don du lieu khong con hieu luc dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_delete_document(request.user, obj)
        return False

    

    def get_mailbox_thread_count(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_mailbox_thread_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_has_file` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.mailbox_threads.count()

    

    def get_signing_status(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_signing_status` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_has_file` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return 'signed' if obj.signed_pdf_records.filter(
            source_version_number=obj.version_number,
            verification_status='safe',
        ).exists() else 'unsigned'

    

    def get_can_forward_now(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_can_forward_now` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_template_title`, `get_has_file` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return self.get_signing_status(obj) == 'signed'

    def get_assistant_action(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None
        plan = get_latest_quick_sign_plan(obj, user)
        if plan is None:
            return None
        try:
            plan = refresh_quick_sign_plan(plan, user)
        except Exception:
            pass
        return build_quick_sign_plan_payload(plan)

    def get_can_manual_edit(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not obj.output_file or not user or not user.is_authenticated:
            return False
        lock_state = self._lock_state(obj)
        if not lock_state.is_locked:
            return can_edit_document(user, obj)
        return lock_state.code == 'manual_edit_active' and lock_state.can_resume_manual_edit

    def get_can_resume_manual_edit(self, obj):
        return self._lock_state(obj).can_resume_manual_edit

    def get_manual_edit_active(self, obj):
        return self._lock_state(obj).manual_edit_active

    def get_manual_edit_session_id(self, obj):
        return self._lock_state(obj).manual_edit_session_id

    def get_manual_edit_session_status(self, obj):
        return self._lock_state(obj).manual_edit_session_status

    def get_manual_edit_lock_message(self, obj):
        return self._lock_state(obj).detail

    def get_manual_edit_locked_by_name(self, obj):
        return self._lock_state(obj).manual_edit_locked_by_name

class DocumentWriteSerializer(serializers.ModelSerializer):
    

    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentWriteSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/documents.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DocumentWriteSerializer`.
    """
    def to_internal_value(self, data):
        original = data
        if hasattr(data, 'copy'):
            data = data.copy()

        def _set_field_value(target, field_name, value):
            if hasattr(target, 'setlist') and isinstance(value, list):
                target.setlist(field_name, value)
            else:
                target[field_name] = value

        bracketed_tags = []
        if hasattr(original, 'keys'):
            for key in original.keys():
                match = re.fullmatch(r'tags\[(\d+)\]', str(key))
                if not match:
                    continue
                if hasattr(original, 'getlist'):
                    values = original.getlist(key)
                else:
                    raw_value = original.get(key)
                    values = raw_value if isinstance(raw_value, list) else [raw_value]
                for value in values:
                    bracketed_tags.append((int(match.group(1)), value))
        if bracketed_tags and 'tags' not in data:
            ordered_values = [value for _, value in sorted(bracketed_tags, key=lambda item: item[0])]
            _set_field_value(data, 'tags', ordered_values)

        raw_tags = None
        if hasattr(data, 'getlist') and 'tags' in data:
            tag_list = data.getlist('tags')
            if len(tag_list) > 1:
                raw_tags = tag_list
            elif tag_list:
                raw_tags = tag_list[0]
        elif isinstance(data, dict):
            raw_tags = data.get('tags')

        if raw_tags is not None:
            _set_field_value(data, 'tags', _coerce_list_payload(raw_tags))
        return super().to_internal_value(data)

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/documents.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentWriteSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = Document
        fields = ('title', 'content', 'department', 'category', 'notes', 'status', 'tags')

    def validate(self, attrs):
        request = self.context.get('request')
        company = get_user_company(getattr(request, 'user', None))
        department = attrs.get('department', getattr(self.instance, 'department', None))
        category = attrs.get('category', getattr(self.instance, 'category', None))
        if company is not None:
            if department is not None and getattr(department, 'company_id', None) not in {None, company.id}:
                raise serializers.ValidationError({'department': 'Phong ban khong thuoc cong ty hien tai.'})
            if category is not None and getattr(category, 'company_id', None) not in {None, company.id}:
                raise serializers.ValidationError({'category': 'Danh muc khong thuoc cong ty hien tai.'})
        attrs['tags'] = _normalize_document_tags(attrs.get('tags', getattr(self.instance, 'tags', [])))
        return attrs

    

    def update(self, instance, validated_data):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `update` xu ly phan cap nhat du lieu hien co cua serializer trong file `api/serializers/documents.py` trong lop `DocumentWriteSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc cap nhat du lieu hien co nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong lop `DocumentWriteSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh cap nhat du lieu hien co dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class DocumentMailboxEntrySerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentMailboxEntrySerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/documents.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DocumentMailboxEntrySerializer`.
    """
    forwarded_by_name = serializers.SerializerMethodField()
    forwarded_to_name = serializers.SerializerMethodField()
    signed_pdf_id = serializers.IntegerField(source='signed_pdf.id', read_only=True, allow_null=True)
    actioned_by_name = serializers.SerializerMethodField()

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/documents.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentMailboxEntrySerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = DocumentMailboxEntry
        fields = (
            'id',
            'parent_entry',
            'forwarded_by',
            'forwarded_by_name',
            'forwarded_to',
            'forwarded_to_name',
            'signed_pdf_id',
            'status',
            'note',
            'action_reason',
            'actioned_by',
            'actioned_by_name',
            'actioned_at',
            'created_at',
            'updated_at',
        )

    

    def get_forwarded_by_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_forwarded_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentMailboxEntrySerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_forwarded_to_name`, `get_actioned_by_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.forwarded_by.get_full_name() or obj.forwarded_by.username

    

    def get_forwarded_to_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_forwarded_to_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentMailboxEntrySerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_forwarded_by_name`, `get_actioned_by_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.forwarded_to.get_full_name() or obj.forwarded_to.username

    

    def get_actioned_by_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_actioned_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentMailboxEntrySerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_forwarded_by_name`, `get_forwarded_to_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if obj.actioned_by_id:
            return obj.actioned_by.get_full_name() or obj.actioned_by.username
        return ''

class DocumentMailboxThreadSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentMailboxThreadSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/documents.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DocumentMailboxThreadSerializer`.
    """
    document_title = serializers.CharField(source='document.title', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    source_signed_pdf_id = serializers.IntegerField(source='source_signed_pdf.id', read_only=True, allow_null=True)
    last_action_by_name = serializers.SerializerMethodField()
    latest_sender_name = serializers.SerializerMethodField()
    latest_terminal_actor_name = serializers.SerializerMethodField()
    branch_count = serializers.SerializerMethodField()
    entries = DocumentMailboxEntrySerializer(many=True, read_only=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/documents.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentMailboxThreadSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = DocumentMailboxThread
        fields = (
            'id',
            'document',
            'document_title',
            'created_by',
            'created_by_name',
            'source_version_number',
            'source_signed_pdf_id',
            'status',
            'last_action_by',
            'last_action_by_name',
            'last_action_at',
            'last_action_summary',
            'last_action_reason',
            'latest_sender_name',
            'latest_terminal_actor_name',
            'branch_count',
            'created_at',
            'updated_at',
            'entries',
        )

    

    def get_created_by_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_created_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentMailboxThreadSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_last_action_by_name`, `get_latest_sender_name`, `get_latest_terminal_actor_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.created_by.get_full_name() or obj.created_by.username

    

    def get_last_action_by_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_last_action_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentMailboxThreadSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_created_by_name`, `get_latest_sender_name`, `get_latest_terminal_actor_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if obj.last_action_by_id:
            return obj.last_action_by.get_full_name() or obj.last_action_by.username
        return ''

    

    def get_latest_sender_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_latest_sender_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentMailboxThreadSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_created_by_name`, `get_last_action_by_name`, `get_latest_terminal_actor_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        latest_entry = obj.entries.order_by('-created_at').select_related('forwarded_by').first()
        if latest_entry is None:
            return ''
        return latest_entry.forwarded_by.get_full_name() or latest_entry.forwarded_by.username

    

    def get_latest_terminal_actor_name(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_latest_terminal_actor_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/documents.py` trong lop `DocumentMailboxThreadSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_created_by_name`, `get_last_action_by_name`, `get_latest_sender_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if obj.status not in {'completed', 'rejected'} or obj.last_action_by_id is None:
            return ''
        return obj.last_action_by.get_full_name() or obj.last_action_by.username

    

    def get_branch_count(self, obj):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_branch_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/documents.py` trong lop `DocumentMailboxThreadSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_created_by_name`, `get_last_action_by_name`, `get_latest_sender_name` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.entries.count()
