import os

'''
accounts/storage_paths.py dùng để tạo đường dẫn lưu file an toàn và tách biệt theo từng công ty.

  Tên file thực tế là storage_paths.py, có chữ s.

  File: accounts/storage_paths.py:1

  ## Mục Tiêu

  Mọi file media nên được lưu theo cấu trúc:

  companies/<company-slug>/<khu-vực>/<tên-file>

  Ví dụ:

  companies/cong-ty-a/avatars/avatar.png
  companies/cong-ty-a/documents/report.docx
  companies/cong-ty-b/documents/report.docx

  Hai công ty có file cùng tên nhưng không ghi đè nhau.
'''
# def company_storage_slug để tạo một slug an toàn cho công ty dựa trên các thuộc tính của công ty như slug, code hoặc name. Nếu công ty là None, nó sẽ trả về 'default-company'. Nếu có một thuộc tính nào đó có giá trị, nó sẽ được sử dụng để tạo slug bằng cách thay thế các ký tự gạch chéo ngược (\) và gạch chéo (/) bằng dấu gạch ngang (-). Nếu không có thuộc tính nào có giá trị, nó sẽ trả về 'default-company'. Kết quả của hàm này là một chuỗi slug an toàn được sử dụng để tổ chức các file media theo công ty trong hệ thống lưu trữ.
# vd: nếu công ty có slug là 'cong-ty-a', code là 'CTA' và name là 'Công ty A', thì company_storage_slug sẽ trả về 'cong-ty-a' vì slug có giá trị. Nếu công ty có slug là None, code là 'CTA' và name là 'Công ty A', thì company_storage_slug sẽ trả về 'CTA' vì slug là None nhưng code có giá trị. Nếu công ty có slug là None, code là None và name là 'Công ty A', thì company_storage_slug sẽ trả về 'Công ty A' vì slug và code đều là None nhưng name có giá trị. Nếu công ty có slug là None, code là None và name là None, thì company_storage_slug sẽ trả về 'default-company' vì tất cả các thuộc tính đều là None.
def company_storage_slug(company):
    if company is None:
        return 'default-company'
    slug = getattr(company, 'slug', '') or getattr(company, 'code', '') or getattr(company, 'name', '')
    slug = str(slug or '').strip().replace('\\', '-').replace('/', '-')
    return slug or 'default-company'

# def safe_storage_filename để tạo một tên file an toàn bằng cách lấy phần tên file từ đường dẫn gốc và thay thế các ký tự gạch chéo ngược (\) và gạch chéo (/) bằng dấu gạch dưới (_). Nếu tên file sau khi xử lý là rỗng, nó sẽ trả về 'file.bin' làm tên mặc định. Kết quả của hàm này là một chuỗi tên file đã được làm sạch và an toàn để sử dụng trong hệ thống lưu trữ, giúp tránh các vấn đề liên quan đến định dạng đường dẫn hoặc tên file không hợp lệ.
# Vi du: dau vao co thu muc cha se duoc rut gon thanh ten file; ten rong se dung "file.bin".
def safe_storage_filename(filename):
    raw_name = os.path.basename(str(filename or '').strip())
    if not raw_name:
        return 'file.bin'
    return raw_name.replace('\\', '_').replace('/', '_')

# def company_media_path để tạo đường dẫn lưu trữ cho một file media liên quan đến một công ty cụ thể, bao gồm phần tiền tố dựa trên công ty và khu vực lưu trữ, cùng với tên file đã được làm sạch. Nó sử dụng hàm company_storage_slug để tạo phần slug an toàn cho công ty và hàm safe_storage_filename để đảm bảo rằng tên file là an toàn. Kết quả của hàm này là một chuỗi đường dẫn lưu trữ được tổ chức theo cấu trúc 'companies/<company-slug>/<section>/<parts...>/<safe-filename>', giúp đảm bảo rằng các file media được lưu trữ một cách an toàn và có tổ chức theo công ty trong hệ thống lưu trữ.
# vd: nếu company có slug là 'cong-ty-a', section là 'documents', filename là 'report.docx' và parts là ['2024', 'Q1'], thì company_media_path sẽ trả về 'companies/cong-ty-a/documents/2024/Q1/report.docx' sau khi tạo phần slug an toàn cho công ty, đảm bảo tên file an toàn và tổ chức đường dẫn lưu trữ theo cấu trúc đã định, giúp dễ dàng quản lý và truy cập các file media liên quan đến công ty trong hệ thống lưu trữ.
def company_media_path(*, company, section, filename, parts=None):
    safe_name = safe_storage_filename(filename)
    base_parts = ['companies', company_storage_slug(company)]
    if section:
        base_parts.append(str(section).strip('/'))
    for part in parts or []:
        if part in (None, ''):
            continue
        base_parts.append(str(part).strip('/'))
    base_parts.append(safe_name)
    return '/'.join(base_parts)
