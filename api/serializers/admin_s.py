"""
Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
Vai tro backend: File `api/serializers/admin_s.py` giu hoac ho tro luong backend cho cau hinh du an, anh xa route, thong ke dashboard, quan tri du lieu nen va API chung toan he thong.
Vai tro cua no trong frontend: Cac man `/dashboard`, `/admin`, `/admin/ai-config`, `/admin/backup`, badge thong bao va shell dieu huong doc hoac chiu tac dong tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`.
Tac dung: Giu cho cac man dieu phoi cap he thong co cung nguon cau hinh, cung route va cung so lieu nen khi frontend khoi chay.
"""

from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.models import UserGroup, UserGroupMembership, Department, GlobalAIConfig

class DepartmentSerializer(serializers.ModelSerializer):
    

    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Lop `DepartmentSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/admin_s.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `DepartmentSerializer`.
    """
    class Meta:
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/admin_s.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi cua `DepartmentSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = Department
        fields = ('id', 'name', 'code', 'description')

class UserGroupSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Lop `UserGroupSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/admin_s.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `UserGroupSerializer`.
    """
    member_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    template_count = serializers.SerializerMethodField()
    pending_template_assignment_count = serializers.SerializerMethodField()

    

    class Meta:
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/admin_s.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi cua `UserGroupSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = UserGroup
        fields = (
            'id', 'name', 'description', 'member_count',
            'document_count', 'template_count', 'pending_template_assignment_count',
            'created_at',
        )

    

    def get_member_count(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_member_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_document_count`, `get_template_count`, `get_pending_template_assignment_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.memberships.count()

    

    def get_document_count(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_document_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_member_count`, `get_template_count`, `get_pending_template_assignment_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.documents.count()

    

    def get_template_count(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_template_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_member_count`, `get_document_count`, `get_pending_template_assignment_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.templates.count()

    

    def get_pending_template_assignment_count(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_pending_template_assignment_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_member_count`, `get_document_count`, `get_template_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.pending_template_assignments.count()

class UserGroupDetailSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Lop `UserGroupDetailSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/admin_s.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `UserGroupDetailSerializer`.
    """
    member_count = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    template_count = serializers.SerializerMethodField()
    pending_template_assignment_count = serializers.SerializerMethodField()

    

    class Meta:
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/admin_s.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi cua `UserGroupDetailSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = UserGroup
        fields = (
            'id', 'name', 'description', 'member_count', 'members',
            'document_count', 'template_count', 'pending_template_assignment_count',
            'created_at',
        )

    

    def get_member_count(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_member_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_members`, `get_document_count`, `get_template_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.memberships.count()

    

    def get_members(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_members` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_member_count`, `get_document_count`, `get_template_count` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return [
            {
                'user_id': m.user.id,
                'username': m.user.username,
                'full_name': f'{m.user.first_name} {m.user.last_name}'.strip() or m.user.username,
                'role': m.role,
            }
            for m in obj.memberships.select_related('user').all()
        ]

    

    def get_document_count(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_document_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_member_count`, `get_members`, `get_template_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.documents.count()

    

    def get_template_count(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_template_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_member_count`, `get_members`, `get_document_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.templates.count()

    

    def get_pending_template_assignment_count(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_pending_template_assignment_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/admin_s.py` trong lop `UserGroupDetailSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_member_count`, `get_members`, `get_document_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.pending_template_assignments.count()

class UserAdminSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Lop `UserAdminSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/admin_s.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `UserAdminSerializer`.
    """
    chuc_danh = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    

    class Meta:
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/admin_s.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi cua `UserAdminSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'is_staff', 'is_superuser', 'is_active', 'chuc_danh', 'groups', 'date_joined')

    

    def get_chuc_danh(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_chuc_danh` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/admin_s.py` trong lop `UserAdminSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_groups` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        try:
            return obj.profile.chuc_danh
        except Exception:
            return ''

    

    def get_groups(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_groups` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/admin_s.py` trong lop `UserAdminSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `get_chuc_danh` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return [
            {'id': m.group.id, 'name': m.group.name, 'role': m.role}
            for m in obj.group_memberships.select_related('group').all()
        ]

class GlobalAIConfigSerializer(serializers.ModelSerializer):
    

    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Lop `GlobalAIConfigSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/admin_s.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `GlobalAIConfigSerializer`.
    """
    def validate_ai_model(self, value):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `validate_ai_model` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/admin_s.py` trong lop `GlobalAIConfigSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `validate_ocr_model`, `validate_ai_search_engine`, `validate_ai_max_results` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        value = str(value or '').strip()
        if not value:
            raise serializers.ValidationError('ai_model khong duoc de trong.')
        return value

    

    def validate_chat_ai_model(self, value):
        value = str(value or '').strip()
        return value

    def validate_ocr_model(self, value):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `validate_ocr_model` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/admin_s.py` trong lop `GlobalAIConfigSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `validate_ai_model`, `validate_ai_search_engine`, `validate_ai_max_results` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        value = str(value or '').strip()
        if not value:
            raise serializers.ValidationError('ocr_model khong duoc de trong.')
        return value

    def validate_image_ocr_model(self, value):
        value = str(value or '').strip()
        if not value:
            raise serializers.ValidationError('image_ocr_model khong duoc de trong.')
        return value

    

    def validate_ai_search_engine(self, value):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `validate_ai_search_engine` xu ly phan tim kiem hoac loc du lieu theo cau hoi dau vao cua serializer trong file `api/serializers/admin_s.py` trong lop `GlobalAIConfigSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc tim kiem hoac loc du lieu theo cau hoi dau vao nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `validate_ai_model`, `validate_ocr_model`, `validate_ai_max_results` trong cung lop.
        Tac dung: Giu cho qua trinh tim kiem hoac loc du lieu theo cau hoi dau vao dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        value = str(value or '').strip().lower()
        if value in {'', 'thuvienphapluat', 'tvpl', 'bing', 'duckduckgo'}:
            return 'thuvienphapluat'
        raise serializers.ValidationError('ai_search_engine chi ho tro thuvienphapluat.')

    

    def validate_ai_max_results(self, value):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `validate_ai_max_results` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/admin_s.py` trong lop `GlobalAIConfigSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `validate_ai_model`, `validate_ocr_model`, `validate_ai_search_engine` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        value = int(value)
        if value < 1 or value > 20:
            raise serializers.ValidationError('ai_max_results phai nam trong khoang 1-20.')
        return value

    

    def validate_ai_internet_results(self, value):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `validate_ai_internet_results` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/admin_s.py` trong lop `GlobalAIConfigSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Phoi hop truc tiep voi cac method nhu `validate_ai_model`, `validate_ocr_model`, `validate_ai_search_engine` trong cung lop.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        value = int(value)
        if value < 0 or value > 20:
            raise serializers.ValidationError('ai_internet_results phai nam trong khoang 0-20.')
        return value

    

    class Meta:
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/admin_s.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi cua `GlobalAIConfigSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = GlobalAIConfig
        fields = (
            'ai_model',
            'chat_ai_model',
            'ocr_model',
            'image_ocr_model',
            'ai_temperature',
            'ai_max_results',
            'ai_internet_results',
            'ai_search_engine',
            'embedding_model',
            'company_context',
            'updated_at',
        )
        read_only_fields = ('updated_at',)
