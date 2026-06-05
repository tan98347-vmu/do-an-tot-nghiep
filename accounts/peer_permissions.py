"""
Module legacy `peer_permissions` - hien tai chi la **alias** sang sharing.services.

Ly do giu lai: nhieu noi trong codebase con import:
  - PeerPermissionLevel (template/document/prompt audience_member.permission_level)
  - peer_can(user, obj, required)
  - normalize_peer_permission_level / max_peer_permission_level
  - log_peer_permission_change

Tu khi co `sharing.services`, peer_can() chi delegate sang `sharing.services.can()`.
Khi cleanup phase 4, file nay co the bo hoan toan va doi nhung noi con import
PeerPermissionLevel sang `sharing.constants`.
"""

from __future__ import annotations

import logging

from django.db import models


logger = logging.getLogger(__name__)


class PeerPermissionLevel(models.TextChoices):
    """Giu nguyen vi audience_member.permission_level dang dung TextChoices nay."""

    VIEW = 'view', 'Chi xem'
    EDIT = 'edit', 'Xem & sua'
    DELETE = 'delete', 'Toan quyen'


# Re-export ladder ordering tu sharing.constants de tuong thich nguoc
from sharing.constants import (  # noqa: E402
    PERMISSION_ORDER,
    normalize_permission as _normalize_perm,
)


def normalize_peer_permission_level(level) -> str | None:
    return _normalize_perm(level)


def max_peer_permission_level(*levels) -> str | None:
    winner = None
    winner_order = -1
    for level in levels:
        normalized = _normalize_perm(level)
        if normalized is None:
            continue
        rank = PERMISSION_ORDER[normalized]
        if rank > winner_order:
            winner = normalized
            winner_order = rank
    return winner


def get_peer_permission_level(user, obj) -> str | None:
    """Tra ve permission level cao nhat ma user duoc cap tren obj (None neu khong co).

    Delegate sang sharing.services.user_permission_for nhung loai bo owner-bypass
    (vi caller cu phan biet owner vs grantee).
    """
    from sharing.services import get_effective_grants

    grants = get_effective_grants(user, obj)
    return max_peer_permission_level(*(g.permission_level for g in grants))


def peer_can(user, obj, required: str) -> bool:
    """Alias cua sharing.services.can()."""
    from sharing.services import can as _can

    return _can(user, obj, required)


def log_peer_permission_change(
    *,
    entity_name: str,
    entity_id: int,
    actor_id: int | None,
    target_user_id: int,
    old_level: str | None,
    new_level: str | None,
) -> None:
    logger.info(
        'peer_permission_changed | entity=%s | entity_id=%s | actor_id=%s | target_user_id=%s | old=%s | new=%s',
        entity_name,
        entity_id,
        actor_id,
        target_user_id,
        old_level,
        new_level,
    )
