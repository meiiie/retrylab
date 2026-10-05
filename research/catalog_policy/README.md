# Chính sách khớp ngân hàng bài — v2

Đây là nhánh hoàn thiện **prototype đề 4**: mô hình trạng thái → policy học được → app Python → kiểm chứng. Nó không thay thế nghiên cứu dự báo ACcoding đã khóa.

Ngân hàng duy nhất nằm ở `app/static/data/catalog-v2.json`: 12 bài, 96 test, ba nhãn kỹ năng chính do tác giả gán. `core.py` đọc trực tiếp JSON này. Mô hình triển khai chứa SHA256 của nguyên tệp và thứ tự 12 hành động; trình duyệt từ chối trọng số không khớp. “Khớp ngân hàng” nghĩa là khớp định danh/lược đồ, **không có nghĩa động lực học mô phỏng đã đúng với người thật**.

## Mô hình thực sự làm gì?

1. Bayes filter kiểu BKT đọc cặp `(mã bài, qua toàn bộ test hay chưa)`, ước lượng ba biến kỹ năng và ảnh hưởng của độ quen bài. Fit tham số bằng likelihood trên log mô phỏng. Nhãn kỹ năng và độ khó chưa được chuyên gia/người học xác nhận.
2. Double DQN nhận 28 số, xuất 12 giá trị Q. Mạng 28–64–64–12 có 6.796 tham số. Loại bài đã đạt hoặc đã có ba quan sát; chọn Q lớn nhất trong tập còn lại. Q không phải xác suất.
3. Các reward huấn luyện là điểm thăm dò cuối phiên và chi phí giả định; ablation đổi sang thưởng correctness của bài luyện. Cả hai là thiết kế mô phỏng, không dùng thời gian chạy Python trên trình duyệt làm “thời gian học”.
4. Sau mỗi lần nộp, app suy luận với trọng số giữ nguyên. Chạy lại cùng nguyên mã không tạo quan sát mới. Lỗi cú pháp, lỗi khởi động, dừng chạy và quá thời gian không được dùng làm nhãn kỹ năng. Các lần chạy vẫn có thể được lưu trong nhật ký thao tác.

## Thực nghiệm và lệnh

`protocol.json` là thiết kế khóa trước kết quả v2. v1 đã được xem và đã ảnh hưởng đến thiết kế này; không gọi v2 là xác nhận độc lập toàn bộ giả thuyết phát minh từ v1. Run có namespace seed mới, source snapshot và hash qua harness.

```powershell
python -X utf8 tools/harness.py check --suite policy
python -X utf8 tools/harness.py verify-run catalog-policy-v2
python -X utf8 tools/harness.py run catalog-policy-v2-reproduction --protocol research/catalog_policy/protocol.json -- "{python}" research/catalog_policy/train.py --output "{run}"
```

Không chạy lại vào ID đã tồn tại. NumPy và CPU PyTorch cần có sẵn; không cần GPU/API trả phí. Runtime ghi Python/platform, phiên bản Torch, nguồn và kết quả. Các seed được cố định nhưng không hứa bitwise-identical giữa mọi bản thư viện/nền tảng.

300 log train + 100 log validation cho mỗi trong ba fit. Mỗi chính sách neural học 24.000 transition, 2.000 episode, 5.872 gradient update. Tổng chín mạng = 216.000 transition huấn luyện. Kiểm tra 7 policy × 5 world × 3 fit × 300 learner = 31.500 rollout; chỉ có 1.500 định danh người học mô phỏng khác nhau trong evaluation, ghép cặp giữa policy và fit. Mỗi rollout dài 12 bước.

Khoảng tin cậy lấy mẫu lại người học ghép cặp sau khi trung bình ba fit. Khoảng này có điều kiện trên ba mô hình đã học; báo cáo thêm trung bình từng fit. Không suy ra CI cho quần thể sinh viên thật hoặc cho toàn bộ ngẫu nhiên của huấn luyện.

## App và ranh giới

`deployment.json` cố định là `ddqn_aware`, seed 101, được chọn **trước** kiểm tra vì mục tiêu minh họa cơ chế. Không phải checkpoint thắng benchmark. Bản sao công khai cục bộ nằm trong `app/static/data/policy-v2.json`. Mạng và filter chạy trong JavaScript, không gửi mã/lịch sử lên server. Bài làm chạy bằng Python trong worker riêng. Kiểm tra parity so với Python nằm trong `app/tests/policy_browser_check.py`.

App công khai dùng quy tắc dự phòng khi mô hình không tải được, ngân hàng không khớp, hết ứng viên, sau 12 quan sát hợp lệ hoặc khi lịch sử có hành động ngoài phạm vi huấn luyện (thử lại bài đã đạt/quá ba lượt). Thư viện vẫn cho phép ôn bất kỳ bài nào. Không được giấu fallback trong báo cáo RL.

## Giới hạn nghiên cứu

Simulator không hiểu hoặc chạy mã bài làm. Nó dùng nhãn kỹ năng, độ khó giả định và cơ chế xác suất. Nội dung bài tồn tại để kiểm tra app/cùng không gian hành động; chưa có log người thật ghép vào các bài này. Không dùng 12 bài tự biên soạn thay cho benchmark lớn khi tuyên bố SOTA. Double DQN là thuật toán đã công bố; không phải thuật toán mới của dự án. ExRec/UniER được đối chiếu tài liệu, chưa tái hiện thực nghiệm trong môi trường của họ.

`LITERATURE_AND_DATA.md` ghi căn cứ lựa chọn, `RESULTS.md` ghi kết quả thực chạy, `paper/topic4_policy.tex` là bản thảo riêng. Bài gốc và v1 giữ nguyên.
