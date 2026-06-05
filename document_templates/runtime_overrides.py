"""
Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
Vai tro backend: File `document_templates/runtime_overrides.py` giu hoac ho tro luong backend cho CRUD mau, duyet mau, version mau, import DOCX/URL, bulk upload va preview noi dung mau.
Vai tro cua no trong frontend: Cac man `/templates`, `/templates/create`, man chi tiet mau va man bulk upload lay du lieu hoac chiu tac dong gian tiep tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`.
Tac dung: Giu cho du lieu mau, quyen thao tac va preview cua nhom man Mau van ban luon dong nhat giua API, storage va chi so tim kiem.
"""

import re
import os
from functools import wraps

def _patch_render_as_docx(DocumentTemplate):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_patch_render_as_docx` xu ly phan ha tang hoac wiring cua file `document_templates/runtime_overrides.py`, cu the la render noi dung dau ra de tra ve hoac luu tru.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep ham nay; no huong tac dong gian tiep vi route, cau hinh hoac hook nen can buoc render noi dung dau ra de tra ve hoac luu tru truoc khi phuc vu request.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Thuong duoc cac ham public nhu `apply_runtime_overrides` goi lai.
    Tac dung: Giu cho lop ha tang van hanh on dinh bang cach chot rieng buoc render noi dung dau ra de tra ve hoac luu tru.
    """
    current_render = getattr(DocumentTemplate, "render_as_docx", None)
    if current_render is not None and getattr(current_render, "_codex_runtime_patch", False):
        return

    from document_templates.utils import (
        create_docx_from_html,
        create_docx_from_text,
        render_docx_from_template,
    )

    

    def _render_as_docx(self, variables_dict=None, *, allow_content_fallback=True):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `_render_as_docx` xu ly phan ha tang hoac wiring cua file `document_templates/runtime_overrides.py`, cu the la render noi dung dau ra de tra ve hoac luu tru.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep ham nay; no huong tac dong gian tiep vi route, cau hinh hoac hook nen can buoc render noi dung dau ra de tra ve hoac luu tru truoc khi phuc vu request.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Thuong duoc cac ham public nhu `apply_runtime_overrides` goi lai.
        Tac dung: Giu cho lop ha tang van hanh on dinh bang cach chot rieng buoc render noi dung dau ra de tra ve hoac luu tru.
        """
        variables_dict = variables_dict or {}
        docx_source_name = ""
        if getattr(self, "docx_file", None) is not None:
            docx_source_name = getattr(self.docx_file, "name", "") or ""
        docx_source_path = getattr(self.docx_file, "path", "") if docx_source_name else ""
        has_docx_source = bool(docx_source_path) and os.path.exists(docx_source_path)

        if self.source_type == self.SOURCE_DOCX and has_docx_source:
            return render_docx_from_template(docx_source_path, variables_dict)
        if self.source_type == self.SOURCE_DOCX and not allow_content_fallback:
            raise ValueError("Mau DOCX nay khong con file DOCX goc de xuat dung dinh dang.")

        if self.content and str(self.content).strip():
            rendered_content = self.render(variables_dict)
            looks_like_html = bool(re.search(r"<[a-zA-Z][^>]*>", rendered_content))
            if looks_like_html:
                try:
                    return create_docx_from_html(rendered_content)
                except Exception:
                    pass
            rendered_text = re.sub(r"<[^>]+>", "", rendered_content)
            return create_docx_from_text(rendered_text)

        return create_docx_from_text(self.render(variables_dict))

    _render_as_docx._codex_runtime_patch = True
    DocumentTemplate.render_as_docx = _render_as_docx

def _patch_template_save(DocumentTemplate):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_patch_template_save` xu ly phan ha tang hoac wiring cua file `document_templates/runtime_overrides.py`, cu the la xu ly du lieu hoac thao tac lien quan toi mau van ban.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep ham nay; no huong tac dong gian tiep vi route, cau hinh hoac hook nen can buoc xu ly du lieu hoac thao tac lien quan toi mau van ban truoc khi phuc vu request.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Thuong duoc cac ham public nhu `apply_runtime_overrides` goi lai.
    Tac dung: Giu cho lop ha tang van hanh on dinh bang cach chot rieng buoc xu ly du lieu hoac thao tac lien quan toi mau van ban.
    """
    current_save = getattr(DocumentTemplate, "save", None)
    if current_save is None or getattr(current_save, "_codex_runtime_patch", False):
        return

    

    @wraps(current_save)
    def save(self, *args, **kwargs):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `save` xu ly phan ha tang hoac wiring cua file `document_templates/runtime_overrides.py`, cu the la luu va chuan hoa du lieu truoc hoac sau khi ghi vao database.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep ham nay; no huong tac dong gian tiep vi route, cau hinh hoac hook nen can buoc luu va chuan hoa du lieu truoc hoac sau khi ghi vao database truoc khi phuc vu request.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_patch_render_as_docx`, `_patch_template_save`, `_patch_document_save_default_private` trong module nay.
        Tac dung: Giu cho lop ha tang van hanh on dinh bang cach chot rieng buoc luu va chuan hoa du lieu truoc hoac sau khi ghi vao database.
        """
        content = getattr(self, "content", None)
        previous_content = None

        if getattr(self, "pk", None):
            try:
                previous_content = (
                    DocumentTemplate.objects.filter(pk=self.pk)
                    .values_list("content", flat=True)
                    .first()
                )
            except Exception:
                previous_content = None

        if (
            isinstance(content, str)
            and content.strip()
            and isinstance(previous_content, str)
            and previous_content.strip()
        ):
            old_len = len(previous_content.strip())
            new_len = len(content.strip())
            if old_len >= 4000 and new_len < (old_len * 0.6) and (old_len - new_len) >= 1200:
                self.content = previous_content
                content = previous_content

        return current_save(self, *args, **kwargs)

    save._codex_runtime_patch = True
    DocumentTemplate.save = save

def _patch_document_save_default_private():
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `_patch_document_save_default_private` xu ly phan ha tang hoac wiring cua file `document_templates/runtime_overrides.py`, cu the la xu ly du lieu hoac thao tac lien quan toi van ban.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep ham nay; no huong tac dong gian tiep vi route, cau hinh hoac hook nen can buoc xu ly du lieu hoac thao tac lien quan toi van ban truoc khi phuc vu request.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Thuong duoc cac ham public nhu `apply_runtime_overrides` goi lai.
    Tac dung: Giu cho lop ha tang van hanh on dinh bang cach chot rieng buoc xu ly du lieu hoac thao tac lien quan toi van ban.
    """
    try:
        from documents.models import Document
    except Exception:
        return

    current_save = getattr(Document, "save", None)
    if current_save is None or getattr(current_save, "_codex_runtime_patch", False):
        return

    

    @wraps(current_save)
    def save(self, *args, **kwargs):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `save` xu ly phan ha tang hoac wiring cua file `document_templates/runtime_overrides.py`, cu the la luu va chuan hoa du lieu truoc hoac sau khi ghi vao database.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep ham nay; no huong tac dong gian tiep vi route, cau hinh hoac hook nen can buoc luu va chuan hoa du lieu truoc hoac sau khi ghi vao database truoc khi phuc vu request.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_patch_render_as_docx`, `_patch_template_save`, `_patch_document_save_default_private` trong module nay.
        Tac dung: Giu cho lop ha tang van hanh on dinh bang cach chot rieng buoc luu va chuan hoa du lieu truoc hoac sau khi ghi vao database.
        """
        if getattr(self, "_state", None) is not None and getattr(self._state, "adding", False):
            visibility = getattr(self, "visibility", None)
            if isinstance(visibility, str) and visibility.lower() == "public":
                self.visibility = "private"
        return current_save(self, *args, **kwargs)

    save._codex_runtime_patch = True
    Document.save = save

def apply_runtime_overrides():
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Ham `apply_runtime_overrides` xu ly phan ha tang hoac wiring cua file `document_templates/runtime_overrides.py`, cu the la thuc hien phan xu ly chuyen trach cua symbol hien tai.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep ham nay; no huong tac dong gian tiep vi route, cau hinh hoac hook nen can buoc thuc hien phan xu ly chuyen trach cua symbol hien tai truoc khi phuc vu request.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Dung cung cap voi cac ham `_patch_render_as_docx`, `_patch_template_save`, `_patch_document_save_default_private` trong module nay.
    Tac dung: Giu cho lop ha tang van hanh on dinh bang cach chot rieng buoc thuc hien phan xu ly chuyen trach cua symbol hien tai.
    """
    from document_templates.models import DocumentTemplate

    _patch_render_as_docx(DocumentTemplate)
    _patch_template_save(DocumentTemplate)
    _patch_document_save_default_private()
