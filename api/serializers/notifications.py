"""
Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
Vai tro backend: File `api/serializers/notifications.py` giu hoac ho tro luong backend cho cau hinh du an, anh xa route, thong ke dashboard, quan tri du lieu nen va API chung toan he thong.
Vai tro cua no trong frontend: Cac man `/dashboard`, `/admin`, `/admin/ai-config`, `/admin/backup`, badge thong bao va shell dieu huong doc hoac chiu tac dong tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`.
Tac dung: Giu cho cac man dieu phoi cap he thong co cung nguon cau hinh, cung route va cung so lieu nen khi frontend khoi chay.
"""

from rest_framework import serializers

from document_templates.models import TemplateReviewNotification


# class AggregateNotificationItemSerializer là serializer định nghĩa dữ liệu vào/ra (AggregateNotificationItem).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class AggregateNotificationItemSerializer(serializers.Serializer):
    source_type = serializers.CharField()
    source_id = serializers.CharField()
    category = serializers.CharField()
    title = serializers.CharField()
    summary = serializers.CharField()
    status = serializers.CharField()
    is_read = serializers.BooleanField()
    supports_read = serializers.BooleanField()
    counts_as_unread = serializers.BooleanField()
    is_actionable = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    deeplink = serializers.CharField()
    action_label = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True)
    actor_name = serializers.CharField(required=False, allow_blank=True)


# class AggregateNotificationReadSerializer là serializer định nghĩa dữ liệu vào/ra (AggregateNotificationRead).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class AggregateNotificationReadSerializer(serializers.Serializer):
    source_type = serializers.CharField()
    source_id = serializers.CharField()

# class TemplateReviewNotificationSerializer là serializer định nghĩa dữ liệu vào/ra (TemplateReviewNotification).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class TemplateReviewNotificationSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Lop `TemplateReviewNotificationSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/notifications.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `TemplateReviewNotificationSerializer`.
    """
    template_id = serializers.IntegerField(source='template.pk', read_only=True)
    template_title = serializers.CharField(source='template.title', read_only=True)
    actor_name = serializers.SerializerMethodField()

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/notifications.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong pham vi cua `TemplateReviewNotificationSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = TemplateReviewNotification
        fields = (
            'id',
            'template_id',
            'template_title',
            'action',
            'actor_name',
            'comment',
            'is_read',
            'read_at',
            'created_at',
        )

    

    # def get_actor_name để lấy actor name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_actor_name(self, obj):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `get_actor_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/notifications.py` trong lop `TemplateReviewNotificationSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/dashboard.py`, `api/views/admin_v.py`, `api/views/notifications.py`. Nam trong lop `TemplateReviewNotificationSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        if not obj.actor:
            return ''
        return obj.actor.get_full_name() or obj.actor.username
