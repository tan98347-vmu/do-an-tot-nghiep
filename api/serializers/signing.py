"""
Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
Vai tro backend: File `api/serializers/signing.py` giu hoac ho tro luong backend cho de xuat ky, packet ky, nhiem vu ky, xac minh PDF, PKI noi bo va quyen uy quyen.
Vai tro cua no trong frontend: Cac man `/signing/tasks`, `/signed-pdfs`, `/signing/access` va mot phan thao tac o `/mailbox` phu thuoc truc tiep hoac gian tiep vao file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`.
Tac dung: Giu cho quy trinh ky nhieu buoc, trang thai chu ky va kiem tra toan ven PDF nhat quan giua nguoi de xuat, nguoi ky va man tra cuu.
"""

from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import DepartmentMembership, UserGroupMembership
from signing.models import (
    DepartmentDelegation,
    PdfSignatureRecord,
    SignedPdfDocument,
    SigningProposal,
    SigningTask,
    VERIFY_STATUS_INTERNAL_APPROVAL,
)

# def _user_full_name để user full name (trong serializer).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _user_full_name(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_user_full_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Duoc dat o cap module de cac phan khac cua file co the goi lai.
    Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
    """
    return user.get_full_name() or user.username

# class SigningCandidateSerializer là serializer định nghĩa dữ liệu vào/ra (SigningCandidate).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class SigningCandidateSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningCandidateSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `SigningCandidateSerializer`.
    """
    full_name = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    managed_departments = serializers.SerializerMethodField()
    departments = serializers.SerializerMethodField()

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/signing.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi cua `SigningCandidateSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = User
        fields = ('id', 'username', 'full_name', 'title', 'groups', 'managed_departments', 'departments')

    

    # def get_full_name để lấy full name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_full_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_full_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningCandidateSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_title`, `get_groups`, `get_managed_departments` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return _user_full_name(obj)

    

    # def get_title để lấy title (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_title(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_title` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningCandidateSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_full_name`, `get_groups`, `get_managed_departments` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        try:
            return (obj.profile.chuc_danh or '').strip()
        except Exception:
            return ''

    

    # def get_groups để lấy groups (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_groups(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_groups` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningCandidateSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_full_name`, `get_title`, `get_managed_departments` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        memberships = UserGroupMembership.objects.filter(user=obj).select_related('group')
        return [
            {
                'id': membership.group_id,
                'name': membership.group.name,
                'role': membership.role,
            }
            for membership in memberships
        ]

    

    # def get_managed_departments để lấy managed departments (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_managed_departments(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_managed_departments` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningCandidateSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_full_name`, `get_title`, `get_groups` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return list(obj.managed_departments.values('id', 'name', 'code'))

    

    # def get_departments để lấy departments (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_departments(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_departments` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningCandidateSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_full_name`, `get_title`, `get_groups` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        memberships = DepartmentMembership.objects.filter(user=obj, is_active=True).select_related('department')
        return [
            {
                'id': membership.department_id,
                'name': membership.department.name,
                'code': membership.department.code,
            }
            for membership in memberships
        ]

# class SigningProposalSignerInputSerializer là serializer định nghĩa dữ liệu vào/ra (SigningProposalSignerInput).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class SigningProposalSignerInputSerializer(serializers.Serializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningProposalSignerInputSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `SigningProposalSignerInputSerializer`.
    """
    user_id = serializers.IntegerField()
    display_role = serializers.CharField(max_length=200)
    step_no = serializers.IntegerField(min_value=1, required=False, default=1)
    required = serializers.BooleanField(required=False, default=True)
    group_context = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')

# class SigningProposalCreateSerializer là serializer định nghĩa dữ liệu vào/ra (SigningProposalCreate).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class SigningProposalCreateSerializer(serializers.Serializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningProposalCreateSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `SigningProposalCreateSerializer`.
    """
    proposal_note = serializers.CharField(required=False, allow_blank=True, default='')
    signers = SigningProposalSignerInputSerializer(many=True)

# class ProposalSignerSerializer là serializer định nghĩa dữ liệu vào/ra (ProposalSigner).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class ProposalSignerSerializer(serializers.Serializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `ProposalSignerSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `ProposalSignerSerializer`.
    """
    id = serializers.IntegerField(source='pk')
    signer_user_id = serializers.IntegerField(source='signer_user.id')
    signer_name = serializers.SerializerMethodField()
    signer_username = serializers.CharField(source='signer_user.username')
    display_role = serializers.CharField()
    group_context = serializers.CharField()
    step_no = serializers.IntegerField()
    required = serializers.BooleanField()
    sort_order = serializers.IntegerField()

    

    # def get_signer_name để lấy signer name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_signer_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_signer_name` xu ly phan xu ly chung thu, khoa hoac ngu canh ky so cua serializer trong file `api/serializers/signing.py` trong lop `ProposalSignerSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly chung thu, khoa hoac ngu canh ky so nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong lop `ProposalSignerSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh xu ly chung thu, khoa hoac ngu canh ky so dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return _user_full_name(obj.signer_user)

# class SigningProposalSerializer là serializer định nghĩa dữ liệu vào/ra (SigningProposal).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class SigningProposalSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningProposalSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `SigningProposalSerializer`.
    """
    document_id = serializers.IntegerField(source='document.id', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)
    document_owner_name = serializers.SerializerMethodField()
    proposed_by_name = serializers.SerializerMethodField()
    hr_reviewed_by_name = serializers.SerializerMethodField()
    signers = ProposalSignerSerializer(many=True, read_only=True)
    packet_id = serializers.SerializerMethodField()
    current_user_task_id = serializers.SerializerMethodField()

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/signing.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi cua `SigningProposalSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = SigningProposal
        fields = (
            'id',
            'document_id',
            'document_title',
            'document_owner_name',
            'source_version_number',
            'status',
            'proposal_note',
            'review_note',
            'proposed_by_name',
            'hr_reviewed_by_name',
            'hr_reviewed_at',
            'invalidated_reason',
            'packet_id',
            'current_user_task_id',
            'created_at',
            'updated_at',
            'signers',
        )

    

    # def get_document_owner_name để lấy document owner name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_document_owner_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_document_owner_name` xu ly phan xu ly du lieu hoac thao tac lien quan toi van ban cua serializer trong file `api/serializers/signing.py` trong lop `SigningProposalSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly du lieu hoac thao tac lien quan toi van ban nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_proposed_by_name`, `get_hr_reviewed_by_name`, `get_packet_id` trong cung lop.
        Tac dung: Giu cho qua trinh xu ly du lieu hoac thao tac lien quan toi van ban dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return _user_full_name(obj.document.owner)

    

    # def get_proposed_by_name để lấy proposed by name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_proposed_by_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_proposed_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningProposalSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_document_owner_name`, `get_hr_reviewed_by_name`, `get_packet_id` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return _user_full_name(obj.proposed_by)

    

    # def get_hr_reviewed_by_name để lấy hr reviewed by name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_hr_reviewed_by_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_hr_reviewed_by_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningProposalSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_document_owner_name`, `get_proposed_by_name`, `get_packet_id` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if obj.hr_reviewed_by_id:
            return _user_full_name(obj.hr_reviewed_by)
        return ''

    

    # def get_packet_id để lấy packet id (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_packet_id(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_packet_id` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningProposalSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_document_owner_name`, `get_proposed_by_name`, `get_hr_reviewed_by_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        packet = getattr(obj, 'packet', None)
        return packet.pk if packet else None

    

    # def get_current_user_task_id để lấy current user task id (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_current_user_task_id(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_current_user_task_id` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningProposalSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_document_owner_name`, `get_proposed_by_name`, `get_hr_reviewed_by_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        packet = getattr(obj, 'packet', None)
        if request is None or packet is None or not request.user.is_authenticated:
            return None
        task = packet.tasks.filter(signer_user=request.user).order_by('step_no', 'sort_order', 'id').first()
        return task.pk if task else None

# class SigningTaskSerializer là serializer định nghĩa dữ liệu vào/ra (SigningTask).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class SigningTaskSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningTaskSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `SigningTaskSerializer`.
    """
    document_id = serializers.IntegerField(source='packet.document.id', read_only=True)
    document_title = serializers.CharField(source='packet.document.title', read_only=True)
    packet_status = serializers.CharField(source='packet.status', read_only=True)
    packet_id = serializers.IntegerField(source='packet.id', read_only=True)
    signature_mode = serializers.CharField(source='packet.signature_mode', read_only=True)
    signer_name = serializers.SerializerMethodField()
    available_now = serializers.SerializerMethodField()

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/signing.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi cua `SigningTaskSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = SigningTask
        fields = (
            'id',
            'packet_id',
            'document_id',
            'document_title',
            'packet_status',
            'signature_mode',
            'display_role',
            'group_context',
            'step_no',
            'required',
            'signature_field_name',
            'status',
            'signer_name',
            'available_now',
            'notified_at',
            'opened_at',
            'signed_at',
            'rejected_at',
            'rejection_reason',
            'created_at',
        )

    

    # def get_signer_name để lấy signer name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_signer_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_signer_name` xu ly phan xu ly chung thu, khoa hoac ngu canh ky so cua serializer trong file `api/serializers/signing.py` trong lop `SigningTaskSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly chung thu, khoa hoac ngu canh ky so nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_available_now` trong cung lop.
        Tac dung: Giu cho qua trinh xu ly chung thu, khoa hoac ngu canh ky so dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return _user_full_name(obj.signer_user)

    

    # def get_available_now để lấy available now (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_available_now(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_available_now` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SigningTaskSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_signer_name` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.status == 'available' and obj.packet.status == 'active'

# class PdfSignatureRecordSerializer là serializer định nghĩa dữ liệu vào/ra (PdfSignatureRecord).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class PdfSignatureRecordSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `PdfSignatureRecordSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `PdfSignatureRecordSerializer`.
    """
    signer_name = serializers.SerializerMethodField()
    signer_user_id = serializers.IntegerField(source='signer_user.id', read_only=True)
    signer_username = serializers.CharField(source='signer_user.username', read_only=True)
    task_id = serializers.IntegerField(source='task.id', read_only=True)
    display_role = serializers.CharField(source='task.display_role', read_only=True)
    step_no = serializers.IntegerField(source='task.step_no', read_only=True)

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/signing.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi cua `PdfSignatureRecordSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = PdfSignatureRecord
        fields = (
            'task_id',
            'signer_user_id',
            'signer_username',
            'signer_name',
            'display_role',
            'step_no',
            'signature_field_name',
            'certificate_fingerprint',
            'certificate_subject_dn',
            'certificate_serial_number',
            'certificate_issuer_dn',
            'signature_algorithm',
            'digest_algorithm',
            'provider_transaction_id',
            'signed_at',
            'verification_status',
        )

    

    # def get_signer_name để lấy signer name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_signer_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_signer_name` xu ly phan xu ly chung thu, khoa hoac ngu canh ky so cua serializer trong file `api/serializers/signing.py` trong lop `PdfSignatureRecordSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly chung thu, khoa hoac ngu canh ky so nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong lop `PdfSignatureRecordSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh xu ly chung thu, khoa hoac ngu canh ky so dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return _user_full_name(obj.signer_user)

# class SignedPdfDocumentSerializer là serializer định nghĩa dữ liệu vào/ra (SignedPdfDocument).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class SignedPdfDocumentSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SignedPdfDocumentSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `SignedPdfDocumentSerializer`.
    """
    owner_name = serializers.SerializerMethodField()
    source_document_id = serializers.IntegerField(source='source_document.id', read_only=True)
    signature_mode = serializers.CharField(read_only=True)
    verification_status = serializers.CharField(read_only=True)
    verification_checked_at = serializers.DateTimeField(read_only=True)
    signature_count = serializers.IntegerField(read_only=True)
    participant_names = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    signing_events = serializers.SerializerMethodField()
    mailbox_thread_count = serializers.SerializerMethodField()
    mailbox_last_status = serializers.SerializerMethodField()
    mailbox_last_summary = serializers.SerializerMethodField()
    mailbox_latest_thread_id = serializers.SerializerMethodField()

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/signing.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi cua `SignedPdfDocumentSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = SignedPdfDocument
        fields = (
            'id',
            'title',
            'owner_name',
            'source_document_id',
            'source_version_number',
            'file_hash',
            'signature_mode',
            'verification_status',
            'verification_checked_at',
            'signature_count',
            'participant_names',
            'participant_count',
            'mailbox_thread_count',
            'mailbox_last_status',
            'mailbox_last_summary',
            'mailbox_latest_thread_id',
            'signing_events',
            'created_at',
        )

    

    # def get_owner_name để lấy owner name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_owner_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_owner_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SignedPdfDocumentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_participant_names`, `get_participant_count`, `get_mailbox_thread_count` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if obj.owner_id:
            return _user_full_name(obj.owner)
        return ''

    

    # def get_participant_names để lấy participant names (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_participant_names(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_participant_names` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SignedPdfDocumentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_participant_count`, `get_mailbox_thread_count` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        seen = []
        for task in obj.packet.tasks.select_related('signer_user').order_by('step_no', 'sort_order', 'id'):
            name = _user_full_name(task.signer_user)
            if name not in seen:
                seen.append(name)
        return seen

    

    # def get_participant_count để lấy participant count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_participant_count(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_participant_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/signing.py` trong lop `SignedPdfDocumentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_participant_names`, `get_mailbox_thread_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.packet.tasks.values('signer_user_id').distinct().count()

    

    # def get_mailbox_thread_count để lấy mailbox thread count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_mailbox_thread_count(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_mailbox_thread_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/signing.py` trong lop `SignedPdfDocumentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_participant_names`, `get_participant_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.mailbox_threads.count()

    

    # def get_mailbox_last_status để lấy mailbox last status (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_mailbox_last_status(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_mailbox_last_status` xu ly phan xu ly luong hom thu hoac diem chuyen tiep tai lieu cua serializer trong file `api/serializers/signing.py` trong lop `SignedPdfDocumentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly luong hom thu hoac diem chuyen tiep tai lieu nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_participant_names`, `get_participant_count` trong cung lop.
        Tac dung: Giu cho qua trinh xu ly luong hom thu hoac diem chuyen tiep tai lieu dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        thread = obj.mailbox_threads.order_by('-updated_at').first()
        return thread.status if thread else ''

    

    # def get_mailbox_last_summary để lấy mailbox last summary (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_mailbox_last_summary(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_mailbox_last_summary` xu ly phan tong hop so lieu tom tat cua serializer trong file `api/serializers/signing.py` trong lop `SignedPdfDocumentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc tong hop so lieu tom tat nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_participant_names`, `get_participant_count` trong cung lop.
        Tac dung: Giu cho qua trinh tong hop so lieu tom tat dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        thread = obj.mailbox_threads.order_by('-updated_at').first()
        return thread.last_action_summary if thread else ''

    

    # def get_mailbox_latest_thread_id để lấy mailbox latest thread id (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_mailbox_latest_thread_id(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_mailbox_latest_thread_id` xu ly phan xu ly luong hom thu hoac diem chuyen tiep tai lieu cua serializer trong file `api/serializers/signing.py` trong lop `SignedPdfDocumentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc xu ly luong hom thu hoac diem chuyen tiep tai lieu nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_participant_names`, `get_participant_count` trong cung lop.
        Tac dung: Giu cho qua trinh xu ly luong hom thu hoac diem chuyen tiep tai lieu dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        thread = obj.mailbox_threads.order_by('-updated_at').first()
        return thread.pk if thread else None

    

    # def get_signing_events để lấy signing events (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_signing_events(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_signing_events` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `SignedPdfDocumentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_owner_name`, `get_participant_names`, `get_participant_count` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if obj.signature_mode == 'pdf_pkcs7':
            records = obj.signature_records.select_related('signer_user', 'task').order_by('signed_at', 'id')
            return PdfSignatureRecordSerializer(records, many=True).data

        events = []
        tasks = obj.packet.tasks.select_related('signer_user').filter(
            status='signed',
            signed_at__isnull=False,
        ).order_by('step_no', 'sort_order', 'id')
        for task in tasks:
            events.append({
                'task_id': task.id,
                'signer_user_id': task.signer_user_id,
                'signer_username': task.signer_user.username,
                'signer_name': _user_full_name(task.signer_user),
                'display_role': task.display_role,
                'step_no': task.step_no,
                'signature_field_name': task.signature_field_name,
                'certificate_fingerprint': '',
                'certificate_subject_dn': '',
                'certificate_serial_number': '',
                'certificate_issuer_dn': '',
                'signature_algorithm': '',
                'digest_algorithm': '',
                'provider_transaction_id': '',
                'verification_status': VERIFY_STATUS_INTERNAL_APPROVAL,
                'signed_at': task.signed_at.isoformat() if task.signed_at else '',
            })
        return events

# class DepartmentDelegationSerializer là serializer định nghĩa dữ liệu vào/ra (DepartmentDelegation).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class DepartmentDelegationSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `DepartmentDelegationSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DepartmentDelegationSerializer`.
    """
    delegate_user_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/signing.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi cua `DepartmentDelegationSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = DepartmentDelegation
        fields = (
            'id',
            'department',
            'department_name',
            'delegate_user',
            'delegate_user_name',
            'permission_type',
            'is_active',
            'created_at',
        )

    

    # def get_delegate_user_name để lấy delegate user name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_delegate_user_name(self, obj):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_delegate_user_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/signing.py` trong lop `DepartmentDelegationSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong lop `DepartmentDelegationSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return _user_full_name(obj.delegate_user)

# class DepartmentDelegationCreateSerializer là serializer định nghĩa dữ liệu vào/ra (DepartmentDelegationCreate).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class DepartmentDelegationCreateSerializer(serializers.Serializer):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `DepartmentDelegationCreateSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/signing.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DepartmentDelegationCreateSerializer`.
    """
    delegate_user_id = serializers.IntegerField()
    permission_type = serializers.ChoiceField(choices=['approve_signing_proposal', 'view_signed_pdf'])
