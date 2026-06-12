from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CompanyUserMembership, UserAlias, UserProfile

'''
 accounts/signals.py dùng để tự động đồng bộ dữ liệu liên quan đến tài khoản sau khi User hoặc CompanyUserMembership được lưu.

  Nó hoạt động theo cơ chế event:

  Model được save
  → Django phát post_save signal
  → hàm receiver tự động chạy
'''
# CompanyUserMembership để đồng bộ công ty của UserProfile khi có sự thay đổi về thành viên công ty của người dùng. Khi một CompanyUserMembership được lưu, hàm sync_profile_company sẽ được gọi để đảm bảo rằng công ty trong UserProfile của người dùng được cập nhật đúng với công ty trong CompanyUserMembership. Điều này giúp duy trì tính nhất quán giữa thông tin thành viên công ty và hồ sơ người dùng trong hệ thống.
# User để tự động tạo UserProfile khi một User mới được tạo và đồng bộ công ty của UserProfile khi có sự thay đổi về công ty của người dùng. Khi một User được lưu, hàm create_user_profile sẽ được gọi nếu User mới được tạo để tự động tạo một UserProfile liên kết với User đó. Sau đó, hàm save_user_profile sẽ được gọi để đồng bộ công ty của UserProfile dựa trên thông tin thành viên công ty của người dùng, đảm bảo rằng công ty trong UserProfile luôn phản ánh đúng công ty mà người dùng đang thuộc về.
def _sync_alias_company(user: User, company) -> None:
    aliases = UserAlias.objects.filter(user=user)
    if company is None:
        aliases.exclude(company__isnull=True).update(company=None)
        return
    aliases.exclude(company=company).update(company=company)

# def _ensure_signing_credential để đảm bảo rằng một người dùng có thông tin đăng ký ký số (signing credential) cần thiết để thực hiện các hoạt động liên quan đến ký số. Khi một User mới được tạo, hàm _ensure_signing_credential sẽ được gọi để kiểm tra và tạo thông tin đăng ký ký số cho người dùng đó nếu cần thiết. Điều này giúp đảm bảo rằng tất cả người dùng trong hệ thống đều có khả năng thực hiện các hoạt động liên quan đến ký số một cách an toàn và hiệu quả.
def _ensure_signing_credential(user: User) -> None:
    try:
        from signing.internal_pki import ensure_user_signing_credential

        ensure_user_signing_credential(user)
    except Exception:
        pass

# def create_user_profile để tự động tạo UserProfile khi một User mới được tạo. Khi một User được lưu và nếu đó là một User mới (created=True), hàm create_user_profile sẽ được gọi để tạo một UserProfile liên kết với User đó. Điều này đảm bảo rằng mỗi người dùng trong hệ thống đều có một hồ sơ người dùng (UserProfile) tương ứng, giúp quản lý thông tin liên quan đến người dùng một cách hiệu quả hơn.
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return
    UserProfile.objects.get_or_create(user=instance)
    _ensure_signing_credential(instance)

# def save_user_profile để đồng bộ công ty của UserProfile khi có sự thay đổi về thành viên công ty của người dùng. Khi một User được lưu, hàm save_user_profile sẽ được gọi để đảm bảo rằng công ty trong UserProfile của người dùng được cập nhật đúng với công ty trong CompanyUserMembership. Điều này giúp duy trì tính nhất quán giữa thông tin thành viên công ty và hồ sơ người dùng trong hệ thống.
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    profile, _ = UserProfile.objects.get_or_create(user=instance)
    membership = getattr(instance, 'company_membership', None)
    membership_company = getattr(membership, 'company', None)
    if membership_company and profile.company_id != membership_company.id:
        profile.company = membership_company
        profile.save(update_fields=['company'])
    elif membership_company is None and profile.company_id is not None:
        profile.company = None
        profile.save(update_fields=['company'])
    _sync_alias_company(instance, membership_company)

# def sync_profile_company để đồng bộ công ty của UserProfile khi có sự thay đổi về thành viên công ty của người dùng. Khi một CompanyUserMembership được lưu, hàm sync_profile_company sẽ được gọi để đảm bảo rằng công ty trong UserProfile của người dùng được cập nhật đúng với công ty trong CompanyUserMembership. Điều này giúp duy trì tính nhất quán giữa thông tin thành viên công ty và hồ sơ người dùng trong hệ thống.
@receiver(post_save, sender=CompanyUserMembership)
def sync_profile_company(sender, instance, **kwargs):
    profile, _ = UserProfile.objects.get_or_create(user=instance.user)
    if profile.company_id != instance.company_id:
        profile.company = instance.company
        profile.save(update_fields=['company'])
    _sync_alias_company(instance.user, instance.company)
