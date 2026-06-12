'''
accounts/record_codes.py dùng để tạo và đọc mã hiển thị của Document và DocumentTemplate.

  File này không làm việc với database trực tiếp. Nó chỉ chuyển đổi giữa:

  Primary key dạng số ↔ mã dễ đọc

  ## Nội Dung File

  import re


  DOCUMENT_RECORD_PREFIX = 'VB'
  TEMPLATE_RECORD_PREFIX = 'MVB'
  RECORD_CODE_WIDTH = 6

  ### Các hằng số

  DOCUMENT_RECORD_PREFIX = 'VB'

  Prefix cho văn bản:

  VB = Văn bản

  TEMPLATE_RECORD_PREFIX = 'MVB'

  Prefix cho mẫu văn bản:

  MVB = Mẫu văn bản

  RECORD_CODE_WIDTH = 6

  Phần số được hiển thị tối thiểu sáu chữ số:

  1    → 000001
  25   → 000025
  1234 → 001234
'''
import re


DOCUMENT_RECORD_PREFIX = 'VB'
TEMPLATE_RECORD_PREFIX = 'MVB'
RECORD_CODE_WIDTH = 6


def format_record_code(prefix, object_id):
    if object_id is None:
        return ''
    return f'{prefix}-{int(object_id):0{RECORD_CODE_WIDTH}d}'


def parse_record_code(value, prefix):
    normalized = re.sub(r'[\s_-]+', '', str(value or '').strip()).upper()
    match = re.fullmatch(rf'{re.escape(prefix)}0*(\d+)', normalized)
    if not match:
        return None
    return int(match.group(1))
