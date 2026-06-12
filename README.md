# AI Document Manager

AI Document Manager là nền tảng web hỗ trợ doanh nghiệp quản lý, soạn thảo, chia sẻ, phê duyệt và ký số văn bản trên một hệ thống tập trung. Dự án kết hợp Flutter Web, Django REST Framework, PostgreSQL, AI/Ollama và Collabora để tạo thành một quy trình xử lý tài liệu đầy đủ từ tạo mẫu đến phát hành văn bản.

Hệ thống được thiết kế cho các tổ chức cần chuẩn hóa biểu mẫu, kiểm soát phân quyền nội bộ, tự động hóa thao tác soạn thảo lặp lại và lưu vết toàn bộ quá trình xử lý văn bản.

## Điểm nổi bật

- Quản lý tài liệu, mẫu biểu, prompt, người dùng, phòng ban, nhóm và công ty theo mô hình nhiều đơn vị.
- Tạo văn bản từ mẫu, chỉnh sửa thủ công qua trình duyệt, xem trước, lưu phiên bản và quản lý vòng đời tài liệu.
- Tích hợp AI để hỏi đáp tài liệu, tóm tắt, tạo nội dung, kiểm tra tuân thủ và xử lý tác vụ nền có theo dõi tiến trình.
- Hỗ trợ chia sẻ tài nguyên theo người dùng, nhóm, phòng ban, công ty và cấp quyền chi tiết.
- Quản lý quy trình ký số, đề xuất ký, PDF đã ký, hộp thư văn bản và quick-sign từ trợ lý AI.
- Hỗ trợ backup theo công ty và các command quản trị dữ liệu.

## Kiến trúc tổng quan

```text
Người dùng
  -> Flutter Web
  -> Django REST API
  -> PostgreSQL
  -> AI/Ollama, OCR, RAG
  -> Collabora/CODE khi cần chỉnh sửa DOCX
```

Các thành phần chính:

- `flutter_frontend/`: giao diện người dùng Flutter Web.
- `api/`: REST API, serializers, views và service layer cho frontend.
- `accounts/`: tài khoản, công ty, phòng ban, tenancy, vai trò và phân quyền.
- `documents/`: tài liệu, mailbox, preview, tóm tắt, chỉnh sửa thủ công.
- `document_templates/`: mẫu văn bản, biến đầu vào, chia sẻ và quản lý mẫu.
- `prompts/`: prompt nghiệp vụ, composer, phân quyền và lịch sử sử dụng.
- `ai_engine/`: ChatAI, RAG, OCR, kiểm tra tuân thủ và xử lý nội dung bằng AI.
- `ai_tasks/`: tác vụ AI bất đồng bộ, tiến trình và thông báo kết quả.
- `signing/`: ký số, PKI, signing proposal, signed PDF và quick-sign.
- `sharing/`: chia sẻ tài nguyên và quản lý audience permission.
- `company_backups/`: xuất, sao lưu và khôi phục dữ liệu theo công ty.
- `word_worker_agent/`: client worker tùy chọn cho môi trường tích hợp Microsoft Word.
- `my_tennis_club/`: cấu hình Django, route gốc, ASGI/WSGI và management commands.

## Công nghệ sử dụng

- Frontend: Flutter Web, Riverpod, GoRouter, Dio.
- Backend: Django, Django REST Framework, Simple JWT, CORS Headers.
- Database: PostgreSQL, `pgvector`.
- AI/OCR: Ollama hoặc AI service tương thích, LangChain, OCR model cấu hình bằng biến môi trường.
- Tài liệu: `python-docx`, `mammoth`, `PyMuPDF`, `pdfplumber`, `html2docx`, Collabora/CODE.
- Ký số: `cryptography`, `pyHanko`, PKI nội bộ hoặc cấu hình remote HSM.
- Vận hành: Waitress, nginx, APScheduler, management commands.

## Yêu cầu môi trường

- Python 3.10 trở lên.
- PostgreSQL đã tạo database cho hệ thống.
- Flutter SDK 3.x cho frontend.
- Ollama hoặc AI endpoint tương thích nếu dùng các tính năng AI.
- Tesseract OCR nếu dùng OCR local.
- LibreOffice hoặc Collabora/CODE nếu cần preview/chỉnh sửa DOCX.

## Cấu hình

Tạo file `.env` từ `.env.example` và điền giá trị thật cho môi trường đang chạy:

```powershell
Copy-Item .env.example .env
```

Các nhóm cấu hình quan trọng:

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
- `OLLAMA_BASE_URL`, `DEFAULT_AI_MODEL`, `DEFAULT_EMBEDDING_MODEL`, `OCR_MODEL`, `IMAGE_OCR_MODEL`.
- `BACKUP_ENCRYPTION_MASTER_KEY`, `BACKUP_ENCRYPTION_REQUIRED`, signer key path cho backup.
- `MANUAL_EDIT_PROVIDER`, `COLLABORA_PUBLIC_URL`, `MANUAL_EDIT_WOPI_SRC_BASE_URL`.
- Các cấu hình signing, remote HSM và LibreOffice nếu dùng trong production.

Không commit `.env`, database local, log, cache, runtime output, file backup hoặc credential.

## Chạy backend

Cài dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Chạy migration và khởi tạo dữ liệu cần thiết:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Chạy server phát triển:

```powershell
python manage.py runserver 127.0.0.1:8000
```

Một số management command hữu ích có trong repo:

```powershell
python manage.py seed_default_company
python manage.py seed_platform_admin
python manage.py seed_default_prompts
python manage.py cleanup_ai_tasks
```

## Chạy frontend

```powershell
cd flutter_frontend
flutter pub get
flutter run -d chrome
```

Khi build bản web:

```powershell
cd flutter_frontend
flutter build web
```

Nếu frontend gọi API khác origin, cần cấu hình CORS/CSRF ở backend và cấu hình base URL trong phần frontend tương ứng với môi trường triển khai.

## Tích hợp chỉnh sửa tài liệu

Hệ thống hỗ trợ Collabora/CODE để chỉnh sửa DOCX qua trình duyệt và WOPI endpoint. Các biến `MANUAL_EDIT_PROVIDER`, `COLLABORA_PUBLIC_URL` và `MANUAL_EDIT_WOPI_SRC_BASE_URL` cần được điều chỉnh theo môi trường local hoặc production.

## Kiểm thử

Backend:

```powershell
python -m unittest discover tests
python manage.py test
```

Frontend:

```powershell
cd flutter_frontend
flutter test
```

Tùy phạm vi thay đổi, nên chạy thêm các test theo module như `accounts`, `documents`, `signing`, `sharing` và các test Flutter liên quan màn hình vừa sửa.

## Quy tắc repository

- Commit code nguồn, migration, cấu hình mẫu và script vận hành cần thiết.
- Không commit `.env`, `db.sqlite3`, `.sqlite3`, `media/`, `staticfiles/`, `.codex-*`, runtime output, backup, log hoặc file sinh ra khi test.
- Không công khai cấu hình triển khai riêng, `word_ai/` hoặc `word_addin/`.
- Không đưa các file báo cáo, roadmap, ghi chú cá nhân hoặc Markdown không phục vụ vận hành vào commit release.
- Nếu cần tài liệu vận hành công khai, đặt trong `docs/` với nội dung rõ mục đích sử dụng.

## Trạng thái sản phẩm

Dự án đang ở giai đoạn hệ thống ứng dụng hoàn chỉnh cho đồ án/sản phẩm nội bộ, tập trung vào quản trị tài liệu doanh nghiệp, tự động hóa bằng AI, chia sẻ nội bộ, ký số và tích hợp Word. Khi triển khai thực tế, cần rà soát bảo mật, phân quyền, khóa mã hóa backup, cấu hình domain, HTTPS, database production và chính sách lưu trữ file.
