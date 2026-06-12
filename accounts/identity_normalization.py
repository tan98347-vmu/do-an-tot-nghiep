# file accounts/identity_normalization.py dùng để chuẩn hóa các giá trị nhận dạng như tên người dùng, mã nhân viên, v.v. Nó bao gồm các hàm để loại bỏ dấu, chuẩn hóa chuỗi cho mục đích tra cứu và xây dựng chữ viết tắt từ tên đầy đủ. Các biểu thức chính quy được sử dụng để loại bỏ các ký tự không mong muốn và chuẩn hóa khoảng trắng trong các giá trị đầu vào.
from __future__ import annotations

import re
import unicodedata

_SPACE_RE = re.compile(r"\s+")
_LOOKUP_RE = re.compile(r"[^a-z0-9\s]+")
_EMPLOYEE_CODE_RE = re.compile(r"[^a-z0-9._\-/]+")

# def strip_accents khác với def normalize_lookup_value ở chỗ strip_accents chỉ tập trung vào việc loại bỏ dấu và ký tự kết hợp từ một chuỗi, trong khi normalize_lookup_value thực hiện nhiều bước chuẩn hóa hơn, bao gồm cả việc loại bỏ dấu, chuyển đổi thành chữ thường, loại bỏ các ký tự không mong muốn và chuẩn hóa khoảng trắng. strip_accents chỉ là một phần của quá trình chuẩn hóa được thực hiện trong normalize_lookup_value để đảm bảo rằng các giá trị nhận dạng được chuẩn hóa một cách nhất quán cho mục đích tra cứu.
# dấu và kí tự kết hợp là các ký tự đặc biệt được sử dụng trong nhiều ngôn ngữ để biểu thị các âm thanh hoặc ý nghĩa khác nhau. Ví dụ, trong tiếng Việt, các dấu như dấu sắc (´), dấu huyền (`), dấu hỏi (?), v.v. được sử dụng để thay đổi cách phát âm của các nguyên âm. Các ký tự kết hợp có thể là các ký tự như dấu chấm, dấu gạch ngang, v.v. được sử dụng để phân tách hoặc kết hợp các phần của một chuỗi. Việc loại bỏ dấu và ký tự kết hợp giúp chuẩn hóa các giá trị nhận dạng bằng cách loại bỏ các ký tự đặc biệt và dấu trong các ngôn ngữ khác nhau, giúp dễ dàng tra cứu và so sánh các giá trị này trong cơ sở dữ liệu hoặc khi làm việc với chúng trong mã nguồn.


# def strip_accents để loại bỏ dấu và ký tự kết hợp từ một chuỗi, giúp chuẩn hóa các giá trị nhận dạng bằng cách loại bỏ các ký tự đặc biệt và dấu trong các ngôn ngữ khác nhau. Nó sử dụng unicodedata.normalize để phân tách các ký tự có dấu thành các ký tự cơ bản và các ký tự kết hợp, sau đó loại bỏ các ký tự kết hợp để trả về một chuỗi đã được chuẩn hóa.
# vd: "Nguyễn Văn A" sẽ được chuẩn hóa thành "nguyen van a" sau khi loại bỏ dấu và chuẩn hóa cho mục đích tra cứu.
def strip_accents(value: str) -> str:
# normalize với NFKD để phân tách các ký tự có dấu thành các ký tự cơ bản và các ký tự kết hợp, sau đó loại bỏ các ký tự kết hợp để trả về một chuỗi đã được chuẩn hóa.
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))

# def normalize_lookup_value để chuẩn hóa một giá trị đầu vào cho mục đích tra cứu bằng cách loại bỏ dấu, chuyển đổi thành chữ thường, loại bỏ các ký tự không mong muốn và chuẩn hóa khoảng trắng. Nó sử dụng hàm strip_accents để loại bỏ dấu và ký tự kết hợp, sau đó sử dụng các biểu thức chính quy để loại bỏ các ký tự không phải là chữ cái, số hoặc khoảng trắng, và cuối cùng chuẩn hóa khoảng trắng thành một khoảng trắng duy nhất. Kết quả trả về là một chuỗi đã được chuẩn hóa sẵn sàng cho việc tra cứu.
# vd: "Nguyễn Văn A" sẽ được chuẩn hóa thành "nguyen van a" sau khi loại bỏ dấu, chuyển đổi thành chữ thường và loại bỏ các ký tự không mong muốn, giúp dễ dàng tra cứu trong cơ sở dữ liệu hoặc so sánh với các giá trị khác đã được chuẩn hóa.
# __LOOKUP_RE được sử dụng để loại bỏ các ký tự không phải là chữ cái, số hoặc khoảng trắng, giúp chuẩn hóa các giá trị nhận dạng bằng cách loại bỏ các ký tự đặc biệt và dấu trong các ngôn ngữ khác nhau. __SPACE_RE được sử dụng để chuẩn hóa khoảng trắng thành một khoảng trắng duy nhất, giúp đảm bảo rằng các giá trị nhận dạng được chuẩn hóa một cách nhất quán cho mục đích tra cứu.
# __SPACE_RE được sử dụng để chuẩn hóa khoảng trắng thành một khoảng trắng duy nhất, giúp đảm bảo rằng các giá trị nhận dạng được chuẩn hóa một cách nhất quán cho mục đích tra cứu. Điều này có nghĩa là nếu có nhiều khoảng trắng liên tiếp trong chuỗi đầu vào, chúng sẽ được thay thế bằng một khoảng trắng duy nhất trong kết quả trả về, giúp tránh các vấn đề liên quan đến việc so sánh hoặc tra cứu các giá trị nhận dạng có chứa nhiều khoảng trắng.
def normalize_lookup_value(value: str) -> str:
    text = strip_accents(str(value or "")).lower().strip()
    text = _LOOKUP_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()

# def normalize_employee_code để chuẩn hóa mã nhân viên bằng cách loại bỏ dấu, chuyển đổi thành chữ thường và loại bỏ các ký tự không mong muốn. Nó sử dụng hàm strip_accents để loại bỏ dấu và ký tự kết hợp, sau đó sử dụng biểu thức chính quy để loại bỏ các ký tự không phải là chữ cái, số, dấu chấm, dấu gạch ngang hoặc dấu gạch chéo. Kết quả trả về là một chuỗi đã được chuẩn hóa sẵn sàng cho việc tra cứu hoặc so sánh với các mã nhân viên khác đã được chuẩn hóa.
# vd: "NV001" sẽ được chuẩn hóa thành "nv001" sau khi loại bỏ dấu, chuyển đổi thành chữ thường và loại bỏ các ký tự không mong muốn.
# __EMPLOYEE_CODE_RE được sử dụng để loại bỏ các ký tự không phải là chữ cái, số, dấu chấm, dấu gạch ngang hoặc dấu gạch chéo, giúp chuẩn hóa mã nhân viên bằng cách loại bỏ các ký tự đặc biệt và dấu trong các ngôn ngữ khác nhau. Điều này đảm bảo rằng mã nhân viên được chuẩn hóa một cách nhất quán cho mục đích tra cứu hoặc so sánh với các mã nhân viên khác đã được chuẩn hóa.
def normalize_employee_code(value: str) -> str:
    text = strip_accents(str(value or "")).lower().strip()
    return _EMPLOYEE_CODE_RE.sub("", text)

# def build_initials để xây dựng chữ viết tắt từ một giá trị đầu vào bằng cách chuẩn hóa giá trị đó và lấy chữ cái đầu tiên của mỗi từ. Nó sử dụng hàm normalize_lookup_value để chuẩn hóa giá trị đầu vào, sau đó tách chuỗi đã được chuẩn hóa thành các token (từ) và lấy chữ cái đầu tiên của mỗi token để tạo thành một chuỗi chữ viết tắt. Kết quả trả về là một chuỗi chứa các chữ cái đầu tiên của mỗi từ trong giá trị đầu vào đã được chuẩn hóa.
# vd: "Nguyễn Văn A" sẽ được chuẩn hóa thành "nguyen van a" và sau đó xây dựng chữ viết tắt thành "nva" bằng cách lấy chữ cái đầu tiên của mỗi từ trong tên đã được chuẩn hóa.
# return "".join(token[0] for token in tokens if token) để tạo thành một chuỗi chữ viết tắt bằng cách lấy chữ cái đầu tiên của mỗi token (từ) trong danh sách tokens, chỉ bao gồm các token không rỗng. Điều này đảm bảo rằng nếu có bất kỳ token nào là chuỗi rỗng (ví dụ: do có nhiều khoảng trắng liên tiếp), chúng sẽ bị bỏ qua và không ảnh hưởng đến kết quả cuối cùng của chữ viết tắt.
def build_initials(value: str) -> str:
    tokens = normalize_lookup_value(value).split()
    return "".join(token[0] for token in tokens if token)
