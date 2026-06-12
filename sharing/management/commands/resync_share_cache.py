"""Dong bo lai cache legacy (visibility + status) tu ShareGrant.

Sua du lieu cu bi lech: cac mau/prompt da duoc chia se nhom (co ShareGrant active)
nhung truong `status` legacy van ket o 'pending_leader'/'draft' -> bi an khoi tab
"Mau phong ban". Nguyen nhan cu: finish trinh sua thu cong goi _auto_status lam reset
status. Sau khi vap loi da duoc va, chay lenh nay 1 lan de chua du lieu ton dong.

Cach dung:
    python manage.py resync_share_cache            # ap dung
    python manage.py resync_share_cache --dry-run  # chi liet ke, khong ghi
"""

from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from sharing.constants import APPROVAL_ACTIVE, SCOPE_COLLEAGUES, SCOPE_EVERYONE, SCOPE_GROUP
from sharing.models import ShareGrant
from sharing.services import _sync_legacy_visibility_cache
from sharing.signals import _APPROVAL_STATUS_MODELS


_SHARED_SCOPES = (SCOPE_GROUP, SCOPE_COLLEAGUES, SCOPE_EVERYONE)


class Command(BaseCommand):
    help = 'Dong bo lai visibility/status legacy tu ShareGrant (sua du lieu chia se cu bi lech).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Chi liet ke, khong ghi.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Lay danh sach (content_type, object_id) co grant chia se ACTIVE.
        pairs = (
            ShareGrant.objects.filter(
                approval_status=APPROVAL_ACTIVE,
                scope__in=_SHARED_SCOPES,
            )
            .values_list('content_type_id', 'object_id')
            .distinct()
        )

        by_ct: dict[int, set[int]] = {}
        for ct_id, obj_id in pairs:
            by_ct.setdefault(ct_id, set()).add(obj_id)

        total = 0
        changed = 0
        for ct_id, obj_ids in by_ct.items():
            ct = ContentType.objects.get_for_id(ct_id)
            model_cls = ct.model_class()
            if model_cls is None:
                continue
            for resource in model_cls.objects.filter(pk__in=obj_ids):
                total += 1
                before = (
                    getattr(resource, 'visibility', None),
                    getattr(resource, 'status', None),
                )
                if dry_run:
                    # Chi model co status kieu DUYET (template/prompt) moi duoc promote
                    # status -> approved. Document.status (draft/final) KHONG bi dung toi.
                    model_key = f'{ct.app_label}.{model_cls.__name__}'
                    status_now = getattr(resource, 'status', None)
                    if model_key in _APPROVAL_STATUS_MODELS and status_now not in (None, 'approved'):
                        changed += 1
                        self.stdout.write(
                            f'[DRY] {ct.app_label}.{ct.model} #{resource.pk} '
                            f'visibility={before[0]} status={status_now} -> approved'
                        )
                    continue
                _sync_legacy_visibility_cache(resource)
                resource.refresh_from_db()
                after = (
                    getattr(resource, 'visibility', None),
                    getattr(resource, 'status', None),
                )
                if after != before:
                    changed += 1
                    self.stdout.write(
                        f'{ct.app_label}.{ct.model} #{resource.pk}: '
                        f'{before} -> {after}'
                    )

        self.stdout.write(self.style.SUCCESS(
            f'Hoan tat resync_share_cache. resources={total} changed={changed} dry_run={dry_run}'
        ))
