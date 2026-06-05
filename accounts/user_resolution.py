from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import User

from accounts.identity_normalization import (
    build_initials,
    normalize_employee_code,
    normalize_lookup_value,
)
from accounts.models import Company


def user_public_username(user: User) -> str:
    membership = getattr(user, "company_membership", None)
    local_username = str(getattr(membership, "local_username", "") or "").strip()
    return local_username or user.username


def user_display_name(user: User) -> str:
    full_name = str(user.get_full_name() or "").strip()
    return full_name or user_public_username(user)


def user_alias_values(user: User) -> list[str]:
    aliases = getattr(user, "aliases", None)
    if aliases is None:
        return []
    return [alias.alias for alias in aliases.all() if str(alias.alias or "").strip()]


def _user_title(user: User) -> str:
    profile = getattr(user, "profile", None)
    return str(getattr(profile, "chuc_danh", "") or "").strip()


def _user_employee_code(user: User) -> str:
    profile = getattr(user, "profile", None)
    return str(getattr(profile, "ma_nhan_vien", "") or "").strip()


def _user_department_name(user: User) -> str:
    memberships = getattr(user, "department_memberships", None)
    if memberships is None:
        return ""
    active_memberships = memberships.all()
    for membership in active_memberships:
        if getattr(membership, "is_active", True) and getattr(membership, "department", None):
            return str(membership.department.name or "").strip()
    return ""


def build_recipient_candidate_snapshot(user: User, *, match_reason: str, score: int) -> dict:
    aliases = user_alias_values(user)
    return {
        "user_id": user.id,
        "display_name": user_display_name(user),
        "username": user_public_username(user),
        "employee_code": _user_employee_code(user),
        "title": _user_title(user),
        "department": _user_department_name(user),
        "aliases": aliases,
        "match_reason": match_reason,
        "confidence": round(min(max(score, 0), 100) / 100, 2),
        "_score": score,
    }


def _score_candidate(
    user: User,
    *,
    normalized_query: str,
    employee_code_query: str,
    initials_query: str,
    department_hint: str,
    title_hint: str,
) -> tuple[int, str]:
    display_name = user_display_name(user)
    normalized_name = normalize_lookup_value(display_name)
    username = user_public_username(user)
    normalized_username = normalize_lookup_value(username)
    employee_code = _user_employee_code(user)
    normalized_employee_code = normalize_employee_code(employee_code)
    aliases = user_alias_values(user)
    normalized_aliases = [normalize_lookup_value(alias) for alias in aliases]
    name_initials = build_initials(display_name)

    score = 0
    reason = ""

    if employee_code_query and employee_code_query == normalized_employee_code:
        score, reason = 100, "exact_employee_code"
    elif normalized_query and normalized_query in normalized_aliases:
        score, reason = 96, "exact_alias"
    elif normalized_query and normalized_query == normalized_username:
        score, reason = 92, "exact_username"
    elif normalized_query and normalized_query == normalized_name:
        score, reason = 88, "exact_full_name"
    elif initials_query and initials_query == name_initials:
        score, reason = 76, "initials"
    elif normalized_query and any(normalized_query in alias for alias in normalized_aliases):
        score, reason = 72, "partial_alias"
    elif normalized_query and normalized_query in normalized_username:
        score, reason = 68, "partial_username"
    elif normalized_query and normalized_query in normalized_name:
        score, reason = 64, "partial_full_name"
    elif normalized_query and all(token in normalized_name for token in normalized_query.split()):
        score, reason = 60, "tokenized_full_name"

    if score <= 0:
        return 0, ""

    department = normalize_lookup_value(_user_department_name(user))
    title = normalize_lookup_value(_user_title(user))
    if department_hint and department_hint in department:
        score += 4
    if title_hint and title_hint in title:
        score += 3
    return min(score, 100), reason


def search_recipient_candidates(
    query: str,
    *,
    company: Optional[Company],
    actor: Optional[User] = None,
    limit: int = 5,
    department_hint: str = "",
    title_hint: str = "",
    exclude_self: bool = True,
) -> list[dict]:
    normalized_query = normalize_lookup_value(query)
    employee_code_query = normalize_employee_code(query)
    initials_query = build_initials(query)
    if not normalized_query and not employee_code_query:
        return []

    normalized_department_hint = normalize_lookup_value(department_hint)
    normalized_title_hint = normalize_lookup_value(title_hint)

    users = User.objects.filter(is_active=True)
    if company is not None:
        users = users.filter(
            company_membership__company=company,
            company_membership__is_active=True,
        )
    users = users.select_related("profile", "company_membership").prefetch_related(
        "aliases",
        "department_memberships__department",
    )

    candidates: list[dict] = []
    for user in users.distinct():
        if exclude_self and actor is not None and user.id == actor.id:
            continue
        score, reason = _score_candidate(
            user,
            normalized_query=normalized_query,
            employee_code_query=employee_code_query,
            initials_query=initials_query,
            department_hint=normalized_department_hint,
            title_hint=normalized_title_hint,
        )
        if score <= 0:
            continue
        candidates.append(
            build_recipient_candidate_snapshot(user, match_reason=reason, score=score)
        )

    candidates.sort(
        key=lambda item: (
            -int(item.get("_score", 0)),
            str(item.get("display_name", "")).lower(),
            str(item.get("username", "")).lower(),
        )
    )
    trimmed = candidates[: max(1, limit)]
    for item in trimmed:
        item.pop("_score", None)
    return trimmed


def build_recipient_clarification_prompt(candidates: list[dict]) -> str:
    labels = []
    for candidate in candidates[:3]:
        username = str(candidate.get("username", "") or "").strip()
        display_name = str(candidate.get("display_name", "") or "").strip()
        employee_code = str(candidate.get("employee_code", "") or "").strip()
        extra = []
        if username:
            extra.append(f"@{username}")
        if employee_code:
            extra.append(employee_code)
        if extra:
            labels.append(f"{display_name} ({', '.join(extra)})")
        else:
            labels.append(display_name)
    if not labels:
        return "Toi can ban noi ro nguoi nhan can xu ly."
    return "Toi thay nhieu nguoi phu hop: " + "; ".join(labels) + ". Ban muon gui cho ai?"


def resolve_recipient_query(
    query: str,
    *,
    company: Optional[Company],
    actor: Optional[User] = None,
    limit: int = 5,
    department_hint: str = "",
    title_hint: str = "",
) -> dict:
    candidates = search_recipient_candidates(
        query,
        company=company,
        actor=actor,
        limit=limit,
        department_hint=department_hint,
        title_hint=title_hint,
    )
    if not candidates:
        return {
            "status": "not_found",
            "recipient": None,
            "candidates": [],
            "clarification_prompt": "",
            "message": "Toi chua tim thay nguoi nhan phu hop trong cong ty hien tai.",
        }

    if len(candidates) == 1:
        return {
            "status": "resolved",
            "recipient": candidates[0],
            "candidates": candidates,
            "clarification_prompt": "",
            "message": "Da xac dinh duoc nguoi nhan.",
        }

    top = candidates[0]
    top_confidence = float(top.get("confidence", 0))
    next_confidence = float(candidates[1].get("confidence", 0))
    if top_confidence >= 0.9 and (top_confidence - next_confidence) >= 0.08:
        return {
            "status": "resolved",
            "recipient": top,
            "candidates": candidates,
            "clarification_prompt": "",
            "message": "Da xac dinh duoc nguoi nhan.",
        }

    ambiguous_candidates = candidates[:3]
    return {
        "status": "ambiguous",
        "recipient": None,
        "candidates": ambiguous_candidates,
        "clarification_prompt": build_recipient_clarification_prompt(ambiguous_candidates),
        "message": "Can ban lam ro nguoi nhan truoc khi toi tiep tuc.",
    }


def resolve_choice_from_candidates(choice_text: str, candidates: list[dict]) -> dict:
    normalized_choice = normalize_lookup_value(choice_text)
    employee_code_choice = normalize_employee_code(choice_text)
    if not normalized_choice and not employee_code_choice:
        return {
            "status": "not_found",
            "recipient": None,
            "candidates": candidates,
            "clarification_prompt": build_recipient_clarification_prompt(candidates),
        }

    scored_matches: list[tuple[int, dict]] = []
    for candidate in candidates:
        score = 0
        display_name = normalize_lookup_value(candidate.get("display_name", ""))
        username = normalize_lookup_value(candidate.get("username", ""))
        employee_code = normalize_employee_code(candidate.get("employee_code", ""))
        aliases = [normalize_lookup_value(alias) for alias in candidate.get("aliases", [])]
        department = normalize_lookup_value(candidate.get("department", ""))
        title = normalize_lookup_value(candidate.get("title", ""))

        if employee_code_choice and employee_code_choice == employee_code:
            score = 100
        elif normalized_choice and normalized_choice in aliases:
            score = 96
        elif normalized_choice and normalized_choice == username:
            score = 92
        elif normalized_choice and normalized_choice == display_name:
            score = 88
        elif normalized_choice and normalized_choice in department:
            score = 74
        elif normalized_choice and normalized_choice in title:
            score = 72
        elif normalized_choice and normalized_choice in display_name:
            score = 68

        if score > 0:
            scored_matches.append((score, candidate))

    if not scored_matches:
        return {
            "status": "not_found",
            "recipient": None,
            "candidates": candidates,
            "clarification_prompt": build_recipient_clarification_prompt(candidates),
        }

    scored_matches.sort(key=lambda item: (-item[0], str(item[1].get("display_name", "")).lower()))
    if len(scored_matches) == 1 or scored_matches[0][0] > scored_matches[1][0]:
        return {
            "status": "resolved",
            "recipient": scored_matches[0][1],
            "candidates": candidates,
            "clarification_prompt": "",
        }

    return {
        "status": "ambiguous",
        "recipient": None,
        "candidates": [match[1] for match in scored_matches[:3]],
        "clarification_prompt": build_recipient_clarification_prompt(
            [match[1] for match in scored_matches[:3]]
        ),
    }


def get_company_recipient_by_id(company: Optional[Company], user_id: int) -> Optional[User]:
    queryset = User.objects.filter(id=user_id, is_active=True)
    if company is not None:
        queryset = queryset.filter(
            company_membership__company=company,
            company_membership__is_active=True,
        )
    return queryset.select_related("profile", "company_membership").prefetch_related(
        "aliases",
        "department_memberships__department",
    ).first()
