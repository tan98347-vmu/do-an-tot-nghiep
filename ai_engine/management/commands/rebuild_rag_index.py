"""
Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
Vai tro backend: File `ai_engine/management/commands/rebuild_rag_index.py` giu hoac ho tro luong backend cho chat, RAG, OCR, prefill ho so, sinh van ban, luu session va quan ly tri thuc AI.
Vai tro cua no trong frontend: Cac man `/chat`, `/rag`, `/ai-doc`, `/guest` va cac dialog AI phu tro phu thuoc vao ket qua ma file nay sinh ra.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`.
Tac dung: Bao dam prompt, ket qua AI, session hoi thoai, du lieu trich xuat va chi muc RAG phuc vu dung ngu canh cua nguoi dung hien tai.
"""

from django.core.management.base import BaseCommand, CommandError

from accounts.models import Company
from ai_engine.rag_index import (
    document_index_stats,
    rebuild_document_index,
    rebuild_template_index,
    template_index_stats,
)

# class Command là lệnh quản trị 'rebuild_rag_index' để xem thống kê hoặc dựng lại chỉ mục vector RAG cho mẫu văn bản và tài liệu.
# vd: python manage.py rebuild_rag_index --scope templates --company-code VNNET.
class Command(BaseCommand):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `Command` la diem vao cua lenh van hanh backend trong file `ai_engine/management/commands/rebuild_rag_index.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay, nhung du lieu ma cac man nav dang doc co the duoc lam moi hoac sua boi lenh nay.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Cho phep tac vu nen hoac thao tac van hanh cap nhat du lieu phu tro ma khong phai cham tay vao database ngoai quy trinh ung dung.
    """
    help = 'Rebuild or inspect the RAG vector index for templates and documents.'

    

    # def add_arguments để khai báo tham số dòng lệnh: --scope (all/templates/documents), --dry-run (chỉ in thống kê), --company-id / --company-code (giới hạn theo một công ty).
    # vd: thêm cờ --dry-run để chỉ xem thống kê mà không dựng lại chỉ mục.
    def add_arguments(self, parser):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `add_arguments` la ham nghiep vu chinh trong file `ai_engine/management/commands/rebuild_rag_index.py` trong lop `Command`, chiu trach nhiem khai bao tham so dong lenh cho lenh van hanh trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can khai bao tham so dong lenh cho lenh van hanh roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `handle` trong cung lop.
        Tac dung: Don buoc khai bao tham so dong lenh cho lenh van hanh xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        parser.add_argument(
            '--scope',
            choices=['all', 'templates', 'documents'],
            default='all',
            help='Choose which collections to inspect or rebuild.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only print current live/stale/missing statistics.',
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Limit the operation to a single company id.',
        )
        parser.add_argument(
            '--company-code',
            help='Limit the operation to a single company code.',
        )

    

    # def handle để thực thi lệnh: in thống kê live/stale/missing của chỉ mục; nếu --dry-run thì dừng, ngược lại dựng lại chỉ mục template và/hoặc document theo scope và công ty đã chọn.
    # vd: --dry-run -> in 'live/stale/missing' rồi dừng; không có cờ -> xóa và đánh chỉ mục lại.
    def handle(self, *args, **options):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `handle` la ham nghiep vu chinh trong file `ai_engine/management/commands/rebuild_rag_index.py` trong lop `Command`, chiu trach nhiem thuc thi tac vu chinh cua lenh van hanh trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc thi tac vu chinh cua lenh van hanh roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `add_arguments` trong cung lop.
        Tac dung: Don buoc thuc thi tac vu chinh cua lenh van hanh xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        scope = options['scope']
        dry_run = bool(options['dry_run'])
        company_id = options.get('company_id')
        company_code = (options.get('company_code') or '').strip().lower()

        if company_id and company_code:
            raise CommandError('Chi duoc dung mot trong hai tham so --company-id hoac --company-code.')
        if company_code:
            company = Company.objects.filter(code__iexact=company_code).first()
            if company is None:
                raise CommandError(f'Khong tim thay cong ty co code "{company_code}".')
            company_id = company.pk

        stats_payload = {}
        if scope in {'all', 'templates'}:
            stats_payload['templates'] = template_index_stats(company_id=company_id)
        if scope in {'all', 'documents'}:
            stats_payload['documents'] = document_index_stats(company_id=company_id)

        for label, stats in stats_payload.items():
            self.stdout.write(
                '[{label}] rows={rows} indexed_objects={indexed} live_objects={live} '
                'stale_objects={stale} missing_objects={missing}'.format(
                    label=label,
                    rows=stats['total_rows'],
                    indexed=stats['indexed_objects'],
                    live=stats['live_objects'],
                    stale=stats['stale_objects'],
                    missing=stats['missing_objects'],
                )
            )
            if stats['stale_ids']:
                self.stdout.write(f'[{label}] stale_ids={stats["stale_ids"]}')
            if stats['missing_ids']:
                self.stdout.write(f'[{label}] missing_ids={stats["missing_ids"]}')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run only, no rebuild executed.'))
            return

        if scope in {'all', 'templates'}:
            result = rebuild_template_index(company_id=company_id)
            self.stdout.write(
                self.style.SUCCESS(
                    '[templates] rebuilt | deleted_rows={deleted} | indexed_objects={objects} | indexed_chunks={chunks}'.format(
                        deleted=result['deleted_rows'],
                        objects=result['indexed_objects'],
                        chunks=result['indexed_chunks'],
                    )
                )
            )

        if scope in {'all', 'documents'}:
            result = rebuild_document_index(company_id=company_id)
            self.stdout.write(
                self.style.SUCCESS(
                    '[documents] rebuilt | deleted_rows={deleted} | indexed_objects={objects} | indexed_chunks={chunks}'.format(
                        deleted=result['deleted_rows'],
                        objects=result['indexed_objects'],
                        chunks=result['indexed_chunks'],
                    )
                )
            )
