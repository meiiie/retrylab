# Kết quả lần đầu và quyết định tiếp theo

Run: `policy-controlled-v1`, hoàn tất ngày 26/09/2026; các tệp nguồn, protocol, checkpoint và kết quả nằm trong `research/runs/policy-controlled-v1/`. Đã kiểm tra checksum sau thực thi. Toàn bộ dữ liệu trong nhánh này là mô phỏng.

## Những gì đã chạy

- 3 seed độc lập để sinh log fit và train policy.
- Mỗi seed: 400 lịch sử fit mô hình người học, 100 lịch sử validation; 8 lượt/lịch sử.
- 2 mô hình người học: bỏ qua và có xét hiệu ứng quen bài khi làm lại. Tham số được fit bằng grid search NLL trên train.
- 6 bảng Q được huấn luyện, mỗi bảng 4.000 episode × 8 hành động. Tổng 192.000 bước policy training.
- Đánh giá 6 chính sách × 5 môi trường × 3 seed fit × 400 episode: 36.000 rollout, nhưng các chính sách dùng chung người học mô phỏng cho so sánh cặp. Không phải 36.000 người độc lập.
- Reward terminal dựa trên điểm probe mô phỏng quan sát được. Đánh giá dùng kỳ vọng thành công trên probe chưa luyện, không thưởng cho việc chỉ quen bài cũ.

## Kết quả phải giữ, kể cả không thuận giả thuyết

Mô hình có xét quen bài giảm validation NLL ở cả ba seed:

| Seed | Không xét quen bài | Có xét quen bài |
|---|---:|---:|
| 11 | 0,649784 | 0,632629 |
| 29 | 0,637517 | 0,627936 |
| 47 | 0,647226 | 0,623876 |

Nhưng trong môi trường `transfer_and_repair`, mức tăng kỳ vọng probe trung bình là:

| Chính sách | Probe gain |
|---|---:|
| Củng cố kỹ năng ước lượng yếu nhất | 0,174806 |
| Ngẫu nhiên có ràng buộc | 0,156333 |
| Lộ trình cố định | 0,155750 |
| Q-learning với mô hình không xét quen bài | 0,153611 |
| Q-learning với mô hình có xét quen bài | 0,151667 |
| Nhắm xác suất qua bài khoảng 0,7 | 0,126583 |

Đây là thứ tự các trung bình mô tả, chưa có kiểm định để kết luận ưu thế thống kê. Nó không xác nhận rằng cách xử lý retry hiện tại làm policy tốt hơn. Cũng chưa cho biết nguyên nhân là ngân sách train, phần thưởng thưa, biểu diễn trạng thái hay sai số model; cần thí nghiệm tách các giải thích này.

Trong môi trường không có học, tất cả policy có probe gain đúng 0 dù tỷ lệ qua bài luyện khoảng 42,9%–55,6%. Kết quả này là kiểm tra hành vi simulator đúng đặc tả, không phải phát hiện mới về sinh viên.

Không có fallback state chưa gặp trong tập đánh giá này; điều đó chỉ nói về các trạng thái rời rạc và cohort mô phỏng đã thử, không chứng minh phủ toàn bộ không gian trạng thái.

## Quyết định nghiên cứu

Giữ baseline kỹ năng yếu làm đối chứng mạnh. Chưa nâng Q-learning này thành policy mặc định của app và chưa tuyên bố một cải tiến phương pháp. Thí nghiệm này chứng minh có pipeline học/chạy/đánh giá policy, không hoàn thành tính mới hoặc hiệu quả giáo dục của đề 4.

Các kết quả v1 đã được xem. Nếu thay biểu diễn state, reward hoặc ngân sách sau khi đọc chúng, đó là phát triển/thăm dò trên v1. Thiết kế xác nhận mới phải giữ riêng các seed/cohort và cơ chế môi trường chưa dùng để chọn phương pháp; không đổi protocol v1 thành một kế hoạch khác.

Hai bước cần ưu tiên tiếp: (1) kiểm toán ngân hàng bài có nội dung và lịch sử ghép nối để chuẩn bị model–app tương thích; (2) tái lập/adapt một baseline KT+RL công bố, có ablation state/reward và learning curves được xác định trước. Không chỉ tăng độ phức tạp vì kết quả đầu chưa tốt.
