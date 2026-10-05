# Bàn giao bản đề 4 tích hợp — 26/09/2026

## Trạng thái giao cho người dùng

Đã kiểm thử vận hành tiếp theo theo yêu cầu người dùng: đọc `app/DEMO_VALIDATION.md` và `harness/demo_validation.json`; dùng `app/check_demo.cmd` trước buổi báo cáo. Suite `demo` đã thêm vào harness. Không đổi model, kết quả nghiên cứu hoặc lịch sử cá nhân. Kiểm thử phần mềm đạt không thay thế các bằng chứng khoa học còn thiếu phía dưới.

Prototype kỹ thuật đã khép kín: 12 bài Python/96 test → learner filter → Double DQN → chọn bài trong app → kết quả mô phỏng → báo cáo/bản thảo. Mở `http://127.0.0.1:8773/#policy`; hướng dẫn đầy đủ ở `paper/DE_4_BAO_CAO_VA_DEMO.md`. Không xóa localStorage người dùng. Run/test dùng browser context riêng.

Điều chưa được chứng minh: hiệu quả học của sinh viên thật, simulator-to-human transfer, chất lượng nhãn kỹ năng do chuyên gia, hội tụ policy tối ưu, vượt ExRec/UniER, tính mới hoặc hạng venue. Workboard giữ mục publication-validation là planned. Đây không phải tác vụ bí mật đang chạy hay lời hứa sẽ tự tiếp tục sau turn.

## Thực nghiệm mới

`catalog-policy-v2`: 9 mạng 28–64–64–12, mỗi mạng 24.000 transition, 3 seed, 7 policy × 5 world × 300 learner × 3 fit = 31.500 rollout. Mỗi world chỉ có 300 learner khác nhau, ghép cặp qua policy/fit. Chạy 482 giây, exit 0; verify-run đạt, không changed inputs. Source/protocol và tất cả output/checkpoint nằm trong run.

Filter aware giảm NLL validation ở cả 3 seed; nominal policy gain aware/probe 17,91 đpt, naive 18,85, weakest 19,16. Kết quả không hỗ trợ thắng baseline. Deployed member aware/probe seed 101 khóa trước evaluation cho demo, không phải best-test selection. Giữ số âm và giới hạn CI điều kiện trên ba fit.

## Mã và dữ liệu quan trọng

- Nguồn catalog duy nhất: `app/static/data/catalog-v2.json`. Không chỉnh tùy tiện sau train; SHA model sẽ phát hiện mismatch. Nếu thay nội dung/test/skill, version mới và fit/evaluate mới hoặc giữ artifact cũ với nhãn riêng.
- `research/catalog_policy/core.py`, `train.py`, `protocol.json`: nguồn thực nghiệm v2. Đừng ghi đè run; evaluation v2 nay đã inspected. `tests/test_catalog_policy.py` đã snapshot trước run; test 96 lời giải được thêm sau, không coi là preregistered design.
- `adaptive.js`: filter + mạng Q trong browser. `policy-lab.js`: dữ liệu demo giả định không ghi vào practice. `practice.js`: cập nhật model sau kết quả graded, lưu decision trace tối đa 200, xuất theo yêu cầu.
- Identical code một bài chỉ tính một quan sát. Chỉ passed/failed hợp lệ dùng cho model. Lỗi/dừng/timeout không chấm như năng lực. Fallback công khai sau 12 quan sát, quá ba lượt/bài, làm lại bài đã đạt, hết ứng viên hoặc model/catalog lỗi.
- Trọng số mô phỏng và summary được copy có verify-run qua `deploy.py`; manifest checksum công khai tại `app/static/data/policy-manifest-v2.json`.

## Kiểm tra và tài liệu

Suite policy 14 checks; backend 15; browser 4 scripts và 96 browser Python cases; harness 11. `app/TOPIC4_VALIDATION.md` và `harness/topic4_validation.json` dẫn đến evidence. Follow-up storage recovery được chạy sau khi bổ sung sanitize decision history; chưa chỉnh engine lịch sử.

`paper/topic4_policy.tex` đã được mở trong editor. Native compiler trả `Unable to find standard directories for platform`; không có English PDF compile thành công. PDF Việt `output/pdf/retrylab-de4-bao-cao.pdf` được tạo bằng ReportLab từ Markdown; 5 trang, font Việt nhúng, kiểm tra text và visual. `paper/topic4_render_status.json` phân biệt hai kết quả này.

Các tài liệu cũ như `app/DEMO_7_PHUT.md` mô tả nhánh forecast trước tích hợp; người dùng mới nên dùng báo cáo v2. Nghiên cứu/manuscript cũ và 85 hash được bảo vệ không bị sửa. Chưa tạo commit, push, nộp paper hoặc mua compute.
