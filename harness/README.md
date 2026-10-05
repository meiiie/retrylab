# Harness làm việc cho RetryLab

Harness là bộ hướng dẫn và công cụ giúp tiếp tục đúng đề 4, chạy kiểm tra có chọn lọc và giữ dấu vết thực nghiệm. Không cần API key, dịch vụ bên ngoài hoặc thêm agent để sử dụng.

## Lệnh thường dùng

```powershell
python -X utf8 tools/harness.py doctor
python -X utf8 tools/harness.py status
python -X utf8 tools/harness.py check --suite fast
python -X utf8 tools/harness.py check --suite policy
python -X utf8 tools/harness.py check --suite backend
python -X utf8 tools/harness.py check --suite browser
python -X utf8 tools/harness.py check --suite demo
```

`fast` kiểm tra cấu trúc, bảng yêu cầu, hash lịch sử và các unit test của harness. `policy` dùng fixtures mô phỏng. `backend` cần dữ liệu/checkpoint cục bộ. `browser` cần server ở 127.0.0.1:8773 và Playwright; dùng browser context riêng, không xóa dữ liệu người dùng. Các suite không tự cài dependency, tải dữ liệu hay huấn luyện lại mô hình cũ. Mã thoát khác 0 nghĩa là kiểm tra không đạt; lỗi không bị đổi thành “skip/pass”.

`demo` diễn tập Fibonacci → chọn bài → xuất dấu vết, năm môi trường, lỗi tải model/runtime/results/API và khởi động lại một server riêng. `all` bao gồm cả `demo`. Trước buổi báo cáo, bấm `app/check_demo.cmd` hoặc chạy `python app/demo_check.py` để kiểm tra hash, tự mở/tái sử dụng server và diễn tập nhanh trên Edge nếu có. Xem `app/DEMO_READY.md`; các lần diễn tập lưu thư mục mới trong `app/test_outputs/demo/`, kể cả lần thất bại.

## Thực nghiệm có thể truy lại

Protocol JSON có các trường bắt buộc: `id`, `question`, `data_scope`, `claim_scope`, `primary_metric`, `split`, `selection`, `seeds`, `inputs`, `code`, `output_files`. `inputs` và `code` là danh sách đường dẫn tương đối trong repo. `output_files` tương đối với thư mục run. `split` phải khai báo `test_previously_inspected` dạng boolean. Protocol phải mô tả chính xác, không dùng placeholder.

```powershell
python -X utf8 tools/harness.py run policy-v1 --protocol research/policy/protocol.json -- "{python}" research/policy/benchmark.py --output "{run}"
python -X utf8 tools/harness.py verify-run policy-v1
```

Runner tạo thư mục mới độc quyền, lưu protocol/source, checksum input, môi trường, command và thời điểm bắt đầu **trước khi chạy**. Sau chạy ghi mã thoát, log, hash output và kiểm tra đầu vào/lịch sử có thay đổi không. Thiếu output đã khai báo cũng là lỗi. Không tái sử dụng run ID, kể cả run thất bại. Điều này là khóa cục bộ, không phải đăng ký nghiên cứu công khai hay bằng chứng chống sửa có chủ ý.

## Git và hook

`.gitignore` loại raw data, checkpoint, log, runtime và tài liệu bên thứ ba khỏi các thao tác add thông thường. `.ignore` giảm nhiễu tìm kiếm; không là rào cản quyền đọc. Git chỉ hoạt động cục bộ; không có remote/push tự động.

Hook `pre-commit` chạy kiểm tra nhanh cùng kiểm tra bản staged của tệp được bảo vệ. Nó không sửa tệp, cài package, huấn luyện hoặc tự tạo commit. Cấu hình bằng `git config core.hooksPath .githooks`. Không coi hook là cơ chế bảo mật không thể vượt qua.

## Tiếp tục sau gián đoạn

Đọc `status`, `harness/HANDOFF.md` và đúng tài liệu của mục đang làm. Run còn trạng thái `running` phải được kiểm tra tiến trình/log trước khi kết luận; không dùng lại ID. Giữ run cũ để truy vết và mở run mới khi cần. Một bước có bằng chứng mới được đánh dấu hoàn thành; toàn bộ đề 4 chỉ xong khi các yêu cầu chính sách và tích hợp app cũng có bằng chứng tương ứng.

`harness/protected.json` ghi baseline thực tế trước công việc mới. Không cập nhật hash để “chữa” một check thất bại. Muốn sửa nghiên cứu đã khóa, tạo bản khác và ghi amendment. Nguồn thiết kế và các quyết định được lưu ở `SOURCES.md`.
