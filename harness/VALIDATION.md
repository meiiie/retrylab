# Kiểm chứng harness và lần thực nghiệm đầu

Hoàn tất 26/09/2026. Chi tiết máy đọc được ở `validation.json`; kết quả lần chạy ở `research/runs/policy-controlled-v1/record.json`.

| Phần | Kết quả |
|---|---|
| Harness unit tests | 11/11 đạt, gồm sửa tệp bảo vệ, sửa bản staged, lỗi subprocess, thiếu output, collision metadata, path traversal và completion thiếu bằng chứng |
| Policy unit tests | 6/6 đạt: không học thì không tăng probe, action hợp lệ, không dùng future outcome, history không bị mutate, tái lập Q-learning, fallback minh bạch |
| Backend | 15/15 đạt, gồm parity mô hình đã khóa và ranh giới nhãn tương lai |
| Browser | Cả 3 scripts đạt: nghiên cứu, luyện tập và phục hồi; 64 test Python thật; không lỗi console/page |
| Git hook | Chạy trực tiếp qua `git hook run pre-commit`, đạt |
| Skill | `quick_validate.py` đạt |
| Lịch sử | 85 tệp bảo vệ giữ nguyên hash |
| Experiment | Run ID mới, protocol/source/input/output được lưu và kiểm tra; 6 Q tables, 3 seeds, 5 môi trường |

Lần chạy browser đầu thất bại do app server đang tắt. Log thất bại được giữ lại; đã chạy launcher sẵn có, bổ sung preflight và xác nhận lần chạy lại đạt. Không sửa app hoặc xóa tiến độ trình duyệt người dùng để làm test qua.

Kết quả khoa học mô phỏng được giữ nguyên dù không có lợi thế cho Q-learning; đọc `research/policy/INTERPRETATION.md`. Kiểm chứng phần mềm và pipeline không đồng nghĩa với bằng chứng cải thiện học tập hoặc hoàn thành toàn bộ đề 4.
