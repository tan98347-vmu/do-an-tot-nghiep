from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CompanyUserMembership, UserAlias, UserProfile


def _sync_alias_company(user: User, company) -> None:
    aliases = UserAlias.objects.filter(user=user)
    if company is None:
        aliases.exclude(company__isnull=True).update(company=None)
        return
    aliases.exclude(company=company).update(company=company)


def _ensure_signing_credential(user: User) -> None:
    try:
        from signing.internal_pki import ensure_user_signing_credential

        ensure_user_signing_credential(user)
    except Exception:
        pass


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return
    UserProfile.objects.get_or_create(user=instance)
    _ensure_signing_credential(instance)


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


@receiver(post_save, sender=CompanyUserMembership)
def sync_profile_company(sender, instance, **kwargs):
    profile, _ = UserProfile.objects.get_or_create(user=instance.user)
    if profile.company_id != instance.company_id:
        profile.company = instance.company
        profile.save(update_fields=['company'])
    _sync_alias_company(instance.user, instance.company)
