# Biên bản tích hợp đề 4 — 26/09/2026

**Kiểm thử vận hành mới hơn:** xem [DEMO_VALIDATION.md](DEMO_VALIDATION.md), [hướng dẫn demo](DEMO_READY.md) và `harness/demo_validation.json`. Biên bản phía dưới giữ lại lần kiểm tra tích hợp ban đầu.

Bản này thêm catalog v2, filter và policy Double DQN đã huấn luyện, điều khiển gợi ý trong luồng làm bài; giữ nguyên engine và các kết quả ACcoding đã khóa. Không xóa tiến độ/bản nháp của người dùng. Các bài cũ giữ nguyên ID và test; bổ sung bốn bài mới.

## Kiểm tra đã chạy

- `catalog-policy-v2`: hoàn tất, exit 0, không có đầu vào/historical artifact thay đổi giữa run, không thiếu output. `verify-run` đạt. Protocol được khóa trước evaluation v2; v1 là bằng chứng đã được xem.
- 14 kiểm tra policy: 6 v1, 7 invariants v2, 1 kiểm tra tất cả lời giải tham chiếu. Kiểm tra chia seed, không dùng nhãn tương lai cho dự báo trước đó, action mask, familiarity và null control.
- 15 kiểm tra backend lịch sử đạt; 11 kiểm tra harness đạt. Các kiểm tra hash vẫn xác nhận 85 artifact lịch sử nguyên vẹn.
- Lời giải tham chiếu của cả 12 bài vượt 96 test bằng CPython. Cả 12 cũng vượt test trong Pyodide trên browser thực.
- Suite browser gồm 4 script đã đạt: replay lịch sử; luồng sinh viên; hồi phục lỗi/storage; policy lab. Báo cáo harness: `.harness/reports/20260926T150038246720/report.json`, tổng 347 giây trên máy đang dùng.
- Kiểm tra Python/JavaScript trên năm prefix: sai khác tối đa belief/prediction bằng 0 ở fixtures; Q tối đa khoảng 8,06e-8, nhỏ hơn dung sai 2e-6. Đây là parity số học, không phải xác nhận hiệu chuẩn với con người.
- Kiểm tra policy: chọn Q cao nhất trong tập hợp lệ; bỏ bài đã đạt; lặp mã không tạo bằng chứng mới; ngoài support có nhãn fallback; hash khác chặn suy luận; thử giả định không sửa localStorage cá nhân.
- Luồng sinh viên: sửa lỗi, sai tên hàm, print thay return, timeout, dừng khi khởi động, đổi bài khi đang chạy, giữ bản nháp, hoàn tác, xuất journal, recovery khi storage hỏng/bị chặn.
- Giao diện desktop, 768px và 390px không tràn ngang toàn trang. Bảng chi tiết dùng cuộn trong vùng riêng. Không có lỗi JavaScript ở các luồng đã kiểm tra; không có POST mã/lịch sử hoặc request ra ngoài trong luồng sinh viên.

Kiểm tra dùng browser context mới, không tác động dữ liệu trình duyệt người dùng. Các export kiểm thử trong `app/test_outputs/` là QA giả lập, không phải log sinh viên tuyển vào nghiên cứu.

## Tệp chứng cứ

`app/test_outputs/{practice_browser_report,practice_recovery_report,policy_browser_report,browser_report}.json`; public model/catalog/results checksums tại `static/data/policy-manifest-v2.json`; provenance gốc tại `research/runs/catalog-policy-v2/record.json`.

Nguyên tắc đọc: tests đạt chứng minh các hành vi đã kiểm tra. Không chứng minh mọi input, chương trình hay môi trường đều đúng. Bộ test hữu hạn không phải hệ thống thi chống gian lận. Dữ liệu mô phỏng không chứng minh người học thật tiến bộ.

## Giới hạn còn công khai

Không có dữ liệu người thật khớp 12 bài, nhãn kỹ năng chuyên gia, phân tích mã trong learner model, forgetting theo ngày, hiệu quả học tập hoặc thực nghiệm đối chứng ExRec/UniER. Policy aware/probe không thắng weakest-skill ở môi trường chính. Phiên bản triển khai là lựa chọn demo khóa trước evaluation, không phải khuyến nghị tốt nhất đã chứng minh.

Bản thảo tiếng Anh được mở trong editor nhưng native compiler báo `Unable to find standard directories for platform`. Nguồn giữ nguyên để tiếp tục chỉnh sửa. PDF tiếng Việt được dựng từ Markdown bằng ReportLab và kiểm tra riêng; không gọi nó là PDF compile từ bản thảo tiếng Anh.
