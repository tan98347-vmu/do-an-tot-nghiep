"""
Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
Vai tro backend: File `api/serializers/templates.py` giu hoac ho tro luong backend cho CRUD mau, duyet mau, version mau, import DOCX/URL, bulk upload va preview noi dung mau.
Vai tro cua no trong frontend: Cac man `/templates`, `/templates/create`, man chi tiet mau va man bulk upload lay du lieu hoac chiu tac dong gian tiep tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`.
Tac dung: Giu cho du lieu mau, quyen thao tac va preview cua nhom man Mau van ban luon dong nhat giua API, storage va chi so tim kiem.
"""

from rest_framework import serializers
from accounts.permissions import can_delete_template, can_edit_template, can_use_template
from accounts.peer_permissions import get_peer_permission_level, max_peer_permission_level
from accounts.tenancy import get_user_company
from document_templates.models import (
    DocumentTemplate, TemplateCategory, TemplateVersion,
    TemplateAudienceMember, TemplatePermission, TemplateFavorite, TemplateApprovalLog
)
from document_templates.status_rules import _auto_status


def _template_permission_for_user(user, template) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if template.owner_id == user.id:
        return 'owner'
    if user.is_superuser:
        return 'delete'

    base_level = 'view'
    if can_delete_template(user, template):
        base_level = 'delete'
    elif can_edit_template(user, template):
        base_level = 'edit'

    peer_level = get_peer_permission_level(user, template)
    return max_peer_permission_level(base_level, peer_level) or base_level

class TemplateCategorySerializer(serializers.ModelSerializer):
    

    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateCategorySerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/templates.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `TemplateCategorySerializer`.
    """
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/templates.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi cua `TemplateCategorySerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = TemplateCategory
        fields = ('id', 'name', 'description')

class TemplateListSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateListSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/templates.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `TemplateListSerializer`.
    """
    owner_name = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source='owner.id', read_only=True)
    group_id = serializers.SerializerMethodField()
    variable_count = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    can_use = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    my_permission = serializers.SerializerMethodField()
    is_limited_group_share = serializers.SerializerMethodField()
    audience_count = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    last_review_action = serializers.SerializerMethodField()
    last_review_at = serializers.SerializerMethodField()
    last_review_actor_name = serializers.SerializerMethodField()
    has_docx_source = serializers.SerializerMethodField()
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
        return _template_permission_for_user(user, obj)


    class Meta:
        model = DocumentTemplate
        fields = ('id', 'title', 'description', 'status', 'visibility', 'version',
                  'owner_id', 'owner_name', 'group_id', 'variable_count',
                  'category_name', 'is_favorite', 'can_use', 'can_edit', 'can_delete', 'my_permission',
                  'is_limited_group_share', 'audience_count', 'tags',
                  'has_docx_source',
                  'effective_date', 'end_date', 'approved_by_name',
                  'last_review_action', 'last_review_at', 'last_review_actor_name',
                  'peer_share_status', 'peer_audience_count', 'is_peer_shared_to_me',
                  'created_at', 'updated_at')

    

    def get_owner_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_owner_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_variable_count`, `get_category_name`, `get_group_id` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.owner.get_full_name() or obj.owner.username

    

    def get_variable_count(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_variable_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_category_name`, `get_group_id` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return len(obj.get_variables())

    

    def get_category_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_category_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_group_id` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.category.name if obj.category else None

    

    def get_group_id(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_group_id` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.group_id  

    

    def get_is_favorite(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_is_favorite` xu ly phan danh dau hoac bo danh dau yeu thich cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc danh dau hoac bo danh dau yeu thich nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh danh dau hoac bo danh dau yeu thich dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return TemplateFavorite.objects.filter(user=request.user, template=obj).exists()
        return False

    

    def get_can_use(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_can_use` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_use_template(request.user, obj)
        return False

    

    def get_can_edit(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_can_edit` xu ly phan chinh sua du lieu theo input vua gui len cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc chinh sua du lieu theo input vua gui len nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh chinh sua du lieu theo input vua gui len dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_edit_template(request.user, obj)
        return False

    

    def get_can_delete(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_can_delete` xu ly phan xoa hoac don du lieu khong con hieu luc cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xoa hoac don du lieu khong con hieu luc nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh xoa hoac don du lieu khong con hieu luc dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_delete_template(request.user, obj)
        return False

    

    def get_is_limited_group_share(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_is_limited_group_share` xu ly phan khoi tao hoac xu ly quy trinh chia se du lieu cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc khoi tao hoac xu ly quy trinh chia se du lieu nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh khoi tao hoac xu ly quy trinh chia se du lieu dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.visibility == DocumentTemplate.VISIBILITY_GROUP and obj.audience_members.exists()

    

    def get_audience_count(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_audience_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.audience_members.count()

    

    def get_has_docx_source(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_has_docx_source` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return bool(getattr(obj.docx_file, 'name', '') if getattr(obj, 'docx_file', None) else '')

    

    def _latest_review_log(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `_latest_review_log` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.approval_logs.select_related('actor').order_by('-created_at').first()

    

    def get_approved_by_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_approved_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if not obj.approved_by:
            return None
        return obj.approved_by.get_full_name() or obj.approved_by.username

    

    def get_last_review_action(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_last_review_action` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        latest = self._latest_review_log(obj)
        return latest.action if latest else None

    

    def get_last_review_at(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_last_review_at` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        latest = self._latest_review_log(obj)
        return latest.created_at if latest else None

    

    def get_last_review_actor_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_last_review_actor_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateListSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variable_count`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        latest = self._latest_review_log(obj)
        if not latest or not latest.actor:
            return None
        return latest.actor.get_full_name() or latest.actor.username

class TemplateDetailSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateDetailSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/templates.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `TemplateDetailSerializer`.
    """
    owner_name = serializers.SerializerMethodField()
    variables = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    can_use = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    my_permission = serializers.SerializerMethodField()
    is_limited_group_share = serializers.SerializerMethodField()
    audience_count = serializers.SerializerMethodField()
    audience_user_ids = serializers.SerializerMethodField()
    audience_users = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    last_review_action = serializers.SerializerMethodField()
    last_review_at = serializers.SerializerMethodField()
    last_review_actor_name = serializers.SerializerMethodField()
    has_docx_source = serializers.SerializerMethodField()
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
        return _template_permission_for_user(user, obj)


    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/templates.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi cua `TemplateDetailSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = DocumentTemplate
        fields = ('id', 'title', 'description', 'content', 'source_type', 'status',
                  'visibility', 'version', 'owner', 'owner_name', 'variables',
                  'category', 'category_name', 'department', 'department_name',
                  'notes', 'tags', 'effective_date', 'end_date', 'approved_by', 'approved_by_name', 'approved_at',
                  'approver_note', 'group', 'is_favorite', 'can_use', 'can_edit', 'can_delete', 'my_permission',
                  'is_limited_group_share', 'audience_count', 'audience_user_ids', 'audience_users',
                  'has_docx_source',
                  'last_review_action', 'last_review_at', 'last_review_actor_name',
                  'peer_share_status', 'peer_share_approver_note',
                  'peer_audience_count', 'is_peer_shared_to_me',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'owner', 'status', 'version', 'approved_by', 'approved_at', 'created_at', 'updated_at')

    

    def get_owner_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_owner_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_variables`, `get_category_name`, `get_department_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.owner.get_full_name() or obj.owner.username

    

    def get_variables(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_variables` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_category_name`, `get_department_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return sorted(obj.get_variables())

    

    def get_category_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_category_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_department_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.category.name if obj.category else None

    

    def get_department_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_department_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return str(obj.department) if obj.department else None

    

    def get_is_favorite(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_is_favorite` xu ly phan danh dau hoac bo danh dau yeu thich cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc danh dau hoac bo danh dau yeu thich nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh danh dau hoac bo danh dau yeu thich dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return TemplateFavorite.objects.filter(user=request.user, template=obj).exists()
        return False

    

    def get_can_use(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_can_use` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_use_template(request.user, obj)
        return False

    

    def get_can_edit(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_can_edit` xu ly phan chinh sua du lieu theo input vua gui len cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc chinh sua du lieu theo input vua gui len nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh chinh sua du lieu theo input vua gui len dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_edit_template(request.user, obj)
        return False

    

    def get_can_delete(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_can_delete` xu ly phan xoa hoac don du lieu khong con hieu luc cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xoa hoac don du lieu khong con hieu luc nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh xoa hoac don du lieu khong con hieu luc dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return can_delete_template(request.user, obj)
        return False

    

    def get_is_limited_group_share(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_is_limited_group_share` xu ly phan khoi tao hoac xu ly quy trinh chia se du lieu cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc khoi tao hoac xu ly quy trinh chia se du lieu nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh khoi tao hoac xu ly quy trinh chia se du lieu dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.visibility == DocumentTemplate.VISIBILITY_GROUP and obj.audience_members.exists()

    

    def get_audience_count(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_audience_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.audience_members.count()

    

    def get_audience_user_ids(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_audience_user_ids` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return list(obj.audience_members.values_list('user_id', flat=True))

    

    def get_audience_users(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_audience_users` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return [
            {
                'id': membership.user_id,
                'username': membership.user.username,
                'full_name': membership.user.get_full_name() or membership.user.username,
            }
            for membership in obj.audience_members.select_related('user').order_by('user__username')
        ]

    

    def get_has_docx_source(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_has_docx_source` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return bool(getattr(obj.docx_file, 'name', '') if getattr(obj, 'docx_file', None) else '')

    

    def _latest_review_log(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `_latest_review_log` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.approval_logs.select_related('actor').order_by('-created_at').first()

    

    def get_approved_by_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_approved_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if not obj.approved_by:
            return None
        return obj.approved_by.get_full_name() or obj.approved_by.username

    

    def get_last_review_action(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_last_review_action` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        latest = self._latest_review_log(obj)
        return latest.action if latest else None

    

    def get_last_review_at(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_last_review_at` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        latest = self._latest_review_log(obj)
        return latest.created_at if latest else None

    

    def get_last_review_actor_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_last_review_actor_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_variables`, `get_category_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        latest = self._latest_review_log(obj)
        if not latest or not latest.actor:
            return None
        return latest.actor.get_full_name() or latest.actor.username

class TemplateWriteSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateWriteSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/templates.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `TemplateWriteSerializer`.
    """
    source_type = serializers.ChoiceField(
        choices=DocumentTemplate.SOURCE_CHOICES,
        required=False,
        write_only=True,
    )
    change_note = serializers.CharField(required=False, allow_blank=True, write_only=True)
    audience_user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        write_only=True,
    )

    

    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/templates.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi cua `TemplateWriteSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = DocumentTemplate
        fields = ('title', 'description', 'content', 'category', 'department',
                  'notes', 'tags', 'effective_date', 'end_date', 'visibility',
                  'group', 'source_type', 'change_note', 'audience_user_ids')

    

    def to_internal_value(self, data):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `to_internal_value` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `_normalize_tags`, `_apply_auto_approval_metadata`, `validate` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        import json as _json
        import re as _re

        original = data
        if hasattr(data, 'copy'):
            data = data.copy()

        

        def _set_field_value(target, field_name, value):
            """
            Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
            Vai tro backend: Ham `_set_field_value` xu ly phan chuan bi hoac dong bo truong du lieu lien quan cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
            Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc chuan bi hoac dong bo truong du lieu lien quan nay.
            Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Duoc dat o cap module de cac phan khac cua file co the goi lai.
            Tac dung: Giu cho qua trinh chuan bi hoac dong bo truong du lieu lien quan dien ra ngay tai serializer thay vi dan trai sang view hoac client.
            """
            if hasattr(target, 'setlist') and isinstance(value, list):
                target.setlist(field_name, value)
            else:
                target[field_name] = value

        

        def _coerce_list_payload(raw_value):
            """
            Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
            Vai tro backend: Ham `_coerce_list_payload` xu ly phan tra danh sach du lieu theo bo loc hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
            Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc tra danh sach du lieu theo bo loc hien tai nay.
            Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Duoc dat o cap module de cac phan khac cua file co the goi lai.
            Tac dung: Giu cho qua trinh tra danh sach du lieu theo bo loc hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
            """
            if raw_value in (None, '', []):
                return []

            if isinstance(raw_value, str):
                raw_text = raw_value.strip()
                if not raw_text:
                    return []
                try:
                    return _coerce_list_payload(_json.loads(raw_text))
                except Exception:
                    return [
                        item.strip()
                        for item in raw_text.split(',')
                        if item.strip()
                    ]

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

        bracketed_audience = []
        if hasattr(original, 'keys'):
            for key in original.keys():
                match = _re.fullmatch(r'audience_user_ids\[(\d+)\]', str(key))
                if not match:
                    continue
                if hasattr(original, 'getlist'):
                    values = original.getlist(key)
                else:
                    raw_value = original.get(key)
                    values = raw_value if isinstance(raw_value, list) else [raw_value]
                for value in values:
                    bracketed_audience.append((int(match.group(1)), value))
        if bracketed_audience and 'audience_user_ids' not in data:
            ordered_values = [value for _, value in sorted(bracketed_audience, key=lambda item: item[0])]
            _set_field_value(data, 'audience_user_ids', ordered_values)

        raw_audience = None
        if hasattr(data, 'getlist') and 'audience_user_ids' in data:
            audience_list = data.getlist('audience_user_ids')
            if len(audience_list) > 1:
                raw_audience = audience_list
            elif audience_list:
                raw_audience = audience_list[0]
        elif isinstance(data, dict):
            raw_audience = data.get('audience_user_ids')

        if raw_audience is not None:
            _set_field_value(data, 'audience_user_ids', _coerce_list_payload(raw_audience))

        bracketed_tags = []
        if hasattr(original, 'keys'):
            for key in original.keys():
                match = _re.fullmatch(r'tags\[(\d+)\]', str(key))
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

    

    def _normalize_tags(self, raw_tags):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `_normalize_tags` xu ly phan chuan hoa du lieu dau vao hoac du lieu trung gian cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc chuan hoa du lieu dau vao hoac du lieu trung gian nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `to_internal_value`, `_apply_auto_approval_metadata`, `validate` trong cung lop.
        Tac dung: Giu cho qua trinh chuan hoa du lieu dau vao hoac du lieu trung gian dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
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

    

    def _apply_auto_approval_metadata(self, template, actor):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `_apply_auto_approval_metadata` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `to_internal_value`, `_normalize_tags`, `validate` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        from accounts.permissions import is_leader_of
        from django.utils import timezone

        if template.status != 'approved':
            return
        if template.visibility == DocumentTemplate.VISIBILITY_PRIVATE:
            return
        if actor.is_superuser or (template.visibility == DocumentTemplate.VISIBILITY_GROUP and template.group and is_leader_of(actor, template.group)):
            template.approved_by = actor
            template.approved_at = timezone.now()
            template.approver_note = template.approver_note or ''

    

    def validate(self, attrs):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `validate` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `to_internal_value`, `_normalize_tags`, `_apply_auto_approval_metadata` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        from accounts.models import UserGroupMembership
        request = self.context.get('request')
        company = get_user_company(getattr(request, 'user', None))
        docx_file = request.FILES.get('docx_file') if request else None
        effective_date = attrs.get('effective_date', getattr(self.instance, 'effective_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        source_type = attrs.get('source_type', getattr(self.instance, 'source_type', DocumentTemplate.SOURCE_MANUAL))
        department = attrs.get('department', getattr(self.instance, 'department', None))
        category = attrs.get('category', getattr(self.instance, 'category', None))
        group = attrs.get('group', getattr(self.instance, 'group', None))

        if company is not None:
            if department is not None and getattr(department, 'company_id', None) not in {None, company.id}:
                raise serializers.ValidationError({'department': 'Phong ban khong thuoc cong ty hien tai.'})
            if category is not None and getattr(category, 'company_id', None) not in {None, company.id}:
                raise serializers.ValidationError({'category': 'Danh muc khong thuoc cong ty hien tai.'})
            if group is not None and getattr(group, 'company_id', None) not in {None, company.id}:
                raise serializers.ValidationError({'group': 'Nhom khong thuoc cong ty hien tai.'})

        attrs['tags'] = self._normalize_tags(attrs.get('tags', getattr(self.instance, 'tags', [])))
        if effective_date and end_date and end_date < effective_date:
            raise serializers.ValidationError({
                'end_date': 'Ngay het han khong duoc som hon ngay hieu luc.',
            })

        if source_type == DocumentTemplate.SOURCE_DOCX:
            if self.instance is None and not docx_file:
                raise serializers.ValidationError({
                    'docx_file': 'Mau DOCX phai kem file DOCX goc khi tao moi.',
                })
            switching_to_docx = (
                self.instance is not None
                and attrs.get('source_type') == DocumentTemplate.SOURCE_DOCX
                and getattr(self.instance, 'source_type', None) != DocumentTemplate.SOURCE_DOCX
            )
            if switching_to_docx and not docx_file and not getattr(self.instance, 'docx_file', None):
                raise serializers.ValidationError({
                    'docx_file': 'Can file DOCX goc khi chuyen mau sang che do DOCX.',
                })

        visibility = attrs.get('visibility', getattr(self.instance, 'visibility', DocumentTemplate.VISIBILITY_PRIVATE))
        group = attrs.get('group', getattr(self.instance, 'group', None))
        audience_user_ids = attrs.get('audience_user_ids', serializers.empty)
        if visibility == DocumentTemplate.VISIBILITY_GROUP and not group:
            raise serializers.ValidationError({'group': 'Vui lòng chọn nhóm/phòng ban khi chia sẻ theo phòng ban.'})
        if visibility != DocumentTemplate.VISIBILITY_GROUP:
            attrs['group'] = None
            attrs['audience_user_ids'] = []
            return attrs
        if audience_user_ids is serializers.empty:
            return attrs
        normalized_ids = list(dict.fromkeys(int(user_id) for user_id in audience_user_ids))
        if not normalized_ids:
            attrs['audience_user_ids'] = []
            return attrs
        valid_ids = set(
            UserGroupMembership.objects.filter(
                group=group,
                user_id__in=normalized_ids,
            ).values_list('user_id', flat=True)
        )
        if len(valid_ids) != len(normalized_ids):
            raise serializers.ValidationError({
                'audience_user_ids': 'Chi duoc chon nguoi nam trong nhom duoc chia se.',
            })
        attrs['audience_user_ids'] = normalized_ids
        return attrs

    

    def _sync_template_audience(self, template, audience_user_ids):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `_sync_template_audience` xu ly phan xu ly du lieu hoac thao tac lien quan toi mau van ban cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly du lieu hoac thao tac lien quan toi mau van ban nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `to_internal_value`, `_normalize_tags`, `_apply_auto_approval_metadata` trong cung lop.
        Tac dung: Giu cho qua trinh xu ly du lieu hoac thao tac lien quan toi mau van ban dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        template.audience_members.exclude(user_id__in=audience_user_ids).delete()
        existing_ids = set(template.audience_members.values_list('user_id', flat=True))
        TemplateAudienceMember.objects.bulk_create(
            [
                TemplateAudienceMember(template=template, user_id=user_id)
                for user_id in audience_user_ids
                if user_id not in existing_ids
            ],
            ignore_conflicts=True,
        )

    

    def create(self, validated_data):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `create` xu ly phan tao moi ban ghi hoac khoi tao mot luong xu ly cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc tao moi ban ghi hoac khoi tao mot luong xu ly nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `to_internal_value`, `_normalize_tags`, `_apply_auto_approval_metadata` trong cung lop.
        Tac dung: Giu cho qua trinh tao moi ban ghi hoac khoi tao mot luong xu ly dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        user = self.context['request'].user
        validated_data.pop('change_note', None)
        audience_user_ids = validated_data.pop('audience_user_ids', [])
        source_type = validated_data.pop('source_type', None)
        visibility = validated_data.get('visibility', DocumentTemplate.VISIBILITY_PRIVATE)
        target_group = validated_data.get('group')
        request = self.context['request']
        docx_file = request.FILES.get('docx_file') or self.initial_data.get('docx_file')
        if docx_file:
            source_type = DocumentTemplate.SOURCE_DOCX
        else:
            source_type = source_type or DocumentTemplate.SOURCE_MANUAL
        status = _auto_status(source_type, visibility, user, target_group)
        company = get_user_company(user)
        category = validated_data.get('category')
        if category is not None and getattr(category, 'company_id', None) is None and company is not None:
            category.company = company
            category.save(update_fields=['company'])
        template = DocumentTemplate.objects.create(
            owner=user,
            company=company,
            source_type=source_type,
            status=status,
            **validated_data
        )
        self._apply_auto_approval_metadata(template, user)
        if docx_file:
            template.docx_file.save(docx_file.name, docx_file, save=False)
        if visibility == DocumentTemplate.VISIBILITY_GROUP and audience_user_ids:
            self._sync_template_audience(template, audience_user_ids)
        template.save()
        return template

    

    def update(self, instance, validated_data):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `update` xu ly phan cap nhat du lieu hien co cua serializer trong file `api/serializers/templates.py` trong lop `TemplateWriteSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc cap nhat du lieu hien co nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `to_internal_value`, `_normalize_tags`, `_apply_auto_approval_metadata` trong cung lop.
        Tac dung: Giu cho qua trinh cap nhat du lieu hien co dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        from document_templates.versioning import create_template_version_snapshot

        audience_user_ids = validated_data.pop('audience_user_ids', serializers.empty)
        source_type = validated_data.pop('source_type', instance.source_type)
        change_note = validated_data.pop('change_note', '')
        
        create_template_version_snapshot(
            instance,
            created_by=self.context['request'].user,
            change_note=change_note,
        )
        
        try:
            parts = instance.version.split('.')
            major = parts[0]
            minor = int(parts[1]) + 1 if len(parts) > 1 else 1
            instance.version = f'{major}.{minor}'
        except Exception:
            pass
        visibility = validated_data.get('visibility', instance.visibility)
        target_group = validated_data.get('group', instance.group)
        request = self.context['request']
        company = get_user_company(request.user)
        docx_file = request.FILES.get('docx_file') or self.initial_data.get('docx_file')
        if docx_file:
            source_type = DocumentTemplate.SOURCE_DOCX
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if instance.company_id is None:
            instance.company = company
        instance.source_type = source_type
        instance.status = _auto_status(source_type, visibility, self.context['request'].user, target_group)
        if instance.status != 'approved':
            instance.approved_by = None
            instance.approved_at = None
            instance.approver_note = ''
        else:
            self._apply_auto_approval_metadata(instance, self.context['request'].user)
        instance.save()
        if instance.visibility != DocumentTemplate.VISIBILITY_GROUP:
            instance.audience_members.all().delete()
        elif audience_user_ids is not serializers.empty:
            self._sync_template_audience(instance, audience_user_ids)
        return instance

class TemplateVersionSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateVersionSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/templates.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `TemplateVersionSerializer`.
    """
    created_by_name = serializers.SerializerMethodField()

    

    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/templates.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong pham vi cua `TemplateVersionSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = TemplateVersion
        fields = ('id', 'version_number', 'content', 'change_note', 'created_by_name', 'created_at', 'is_hidden')

    

    def get_created_by_name(self, obj):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_created_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/templates.py` trong lop `TemplateVersionSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`, `accounts.models`. Nam trong lop `TemplateVersionSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.created_by.username if obj.created_by else None
