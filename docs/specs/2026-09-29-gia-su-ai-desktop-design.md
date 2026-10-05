# Thiết kế: RetryLab — Gia sư AI lập trình (bản desktop cho demo đề tài 4)

Ngày: 29/09/2026. Trạng thái: **chờ duyệt**. Hướng đã chọn: "Gia sư AI + thuyết trình".

## 1. Mục tiêu và phạm vi

**Mục tiêu:** một ứng dụng mở trong cửa sổ riêng như phần mềm, kể trọn câu chuyện đề 4 trên dữ liệu thật: *mô hình trạng thái nhận thức → bài toán MDP → chính sách học tăng cường → gợi ý bài → đánh giá*. Người thuyết trình demo trôi chảy trong 7–8 phút; sinh viên vẫn dùng được phần luyện Python thật.

**Tiêu chí thành công**
1. Bấm đúp một biểu tượng → cửa sổ app mở (không thanh địa chỉ/tab) trong ≤ 30 giây, không cần mạng.
2. Với một học viên thật (ẩn danh), thấy được: lịch sử, bản đồ kỹ năng DKT, luật ID3 giải thích, gợi ý của DQN/PPO kèm lý do và 5 ứng viên, lựa chọn của 14 chính sách.
3. Chạy được phiên học 10 bước, xem từng bước hoặc tự chạy, tự quyết định Đúng/Sai nếu muốn; biểu đồ "tracker báo" và "tiến bộ thật" cập nhật từng bước; đối chứng âm cho thấy tiến bộ ảo.
4. Bảng thuyết trình 8 bước tự mở đúng màn hình và trạng thái, có lời gợi ý.
5. Trang Luyện Python: viết code, chạy 8 test thật, xem mức thành thạo thay đổi và bài gợi ý tiếp theo kèm lý do.
6. Mọi số liệu lấy từ hai run đã khóa; nhãn "mô phỏng" rõ ràng; không tuyên bố hiệu quả với người học thật.

**Ngoài phạm vi (lần này):** mở rộng ngân hàng bài Python (giữ 12 bài), huấn luyện lại mô hình, tài khoản/nhiều người dùng, triển khai lên mạng, đóng gói thành .exe độc lập.

## 2. Kịch bản demo (bảng thuyết trình 8 bước)

| Bước | Màn hình | App tự làm | Ý chính để nói |
|---|---|---|---|
| 1 | Tổng quan | Hiện chuỗi Dữ liệu → Mô hình → MDP → Chính sách → Đánh giá, cùng số liệu chính | Bài toán và dữ liệu thật (4.634 người học, 562.912 lần nộp đầu) |
| 2 | Học viên | Chọn học viên mẫu, hiện lịch sử và bản đồ kỹ năng DKT | Trạng thái nhận thức là gì, DKT ước lượng ra sao |
| 3 | Học viên | Mở luật ID3 cho bài được gợi ý | Cây định danh dựa trên entropy giải thích dự báo bằng luật đọc được |
| 4 | Học viên | Hiện gợi ý của PPO (thế giới AFM), 5 ứng viên, bảng 14 chính sách | MDP: trạng thái, hành động, phần thưởng; tác tử chọn bài thế nào |
| 5 | Phiên học | Chạy 10 bước trong thế giới AFM-B (có học) | Vòng lặp gợi ý → làm bài → cập nhật; tiến bộ thật khiêm tốn |
| 6 | Phiên học | PPO thưởng DKT trong IRT-B (không học) | Tracker báo +25 điểm trong khi thật = 0 → tiến bộ ảo |
| 7 | Đánh giá | Bản đồ nhiệt 14 chính sách × 9 thế giới, H1–H4 | Kết quả toàn tập và các giả thuyết đăng ký trước |
| 8 | Luyện Python | Mở bài gợi ý, cho xem chạy test và cập nhật mô hình | Ứng dụng cho sinh viên; giới hạn và hướng tiếp theo |

Người dùng bấm Tiếp/Lùi, đóng bảng bất cứ lúc nào và thao tác tự do; bảng không khóa giao diện.

## 3. Kiến trúc

```
RetryLab.cmd ──► app/desktop.py ──► khởi động/tái dùng Flask (127.0.0.1:8773)
                                  └► mở Edge/Chrome ở chế độ --app (cửa sổ riêng); không có thì mở trình duyệt mặc định
Flask server.py
  ├─ /            ► giao diện mới (một trang, điều hướng bằng #)
  ├─ /classic     ► giao diện cũ giữ nguyên (mục "Lưu trữ")
  ├─ /api/v3/...  ► realdata_engine.py (+ hàm mới: phiên học từng bước, giải thích, luật ID3)
  └─ /api/...     ► engine.py cũ (được bảo vệ, không sửa), chỉ nạp khi /classic cần tới
Trình duyệt (trong cửa sổ app)
  ├─ static/studio/*.js   ► khung app, 6 màn hình, biểu đồ SVG, bảng thuyết trình
  └─ tái dùng: curriculum.js, adaptive.js, practice-store.js, python-runner.js, python-worker.js, grader.py
```

**Quyết định đã chốt**
- **Cửa sổ desktop bằng chế độ app của Edge** (có sẵn trên Windows 11, không cài thêm gì). Không có Edge thì dùng Chrome, cuối cùng là trình duyệt mặc định. Dùng hồ sơ trình duyệt mặc định nên tiến độ luyện tập đã lưu vẫn còn.
- **JavaScript thuần (ES modules), không thêm framework hay bước build**, biểu đồ vẽ bằng SVG tự viết theo bảng màu đã kiểm tra khả năng phân biệt màu. Chạy offline hoàn toàn, tuân thủ CSP hiện có.
- **Mô hình v3 được "làm nóng" khi server khởi động** (luồng nền) để thao tác đầu tiên không phải chờ; mô hình nghiên cứu cũ chỉ nạp khi mở /classic.

## 4. Màn hình

Khung: thanh điều hướng dọc bên trái (Tổng quan · Học viên · Phiên học · Đánh giá · Luyện Python · Mô hình · Lưu trữ), nút "▶ Thuyết trình" ở cuối thanh. Cửa sổ chuẩn 1440×900; tự co về một cột khi hẹp.

1. **Tổng quan:** tiêu đề đề tài; 4 ô số liệu (người học, lần nộp đầu, AUC dự báo, số chính sách × thế giới); sơ đồ chuỗi 5 khâu, mỗi khâu bấm được để mở màn hình tương ứng; thông điệp chính của nghiên cứu; nút bắt đầu thuyết trình.
2. **Học viên (dữ liệu thật ACcoding):**
   - Cột trái: danh sách 60 học viên mẫu (mã ẩn danh, số bài, tỉ lệ đúng lần đầu), ô tìm kiếm.
   - Giữa: thẻ hồ sơ; *Bản đồ kỹ năng* (10 kỹ năng nền tảng, thanh mức thành thạo DKT); *Dòng thời gian* các bài đã làm (chấm đúng/sai theo kỹ năng, di chuột xem chi tiết; bấm để giả định đảo kết quả).
   - Phải: *Gợi ý tiếp theo* (chọn chính sách; bài được chọn, kỹ năng, độ khó, P(đúng) theo DKT; 5 ứng viên hàng đầu với điểm Q hoặc xác suất; "Vì sao" bằng lời); *Luật ID3* cho bài đó (chuỗi điều kiện → xác suất lá, số mẫu); bảng "14 chính sách chọn gì".
3. **Phiên học (mô phỏng từng bước):** chọn học viên, chính sách, thế giới (tên dễ hiểu kèm mã). Nút Bước tiếp / Tự chạy / Làm lại; chế độ "tôi quyết định Đúng/Sai". Mỗi bước: bài được chọn, kết quả, số lần nộp, phần thưởng MDP của bước (Δ post-test − λ×nộp thêm), độ trôi. Biểu đồ đường: post-test mà tracker báo và post-test thật của thế giới (thế giới DKT/SAKT không có "thật" riêng thì ghi rõ). Thanh kỹ năng cập nhật động. Tổng kết cuối phiên: tiến bộ thật, tracker báo, tiến bộ ảo = chênh lệch, kèm giải thích ngắn. Có nút mẫu "Đối chứng âm: PPO thưởng DKT trong thế giới không học".
4. **Đánh giá:** bản đồ nhiệt 14 chính sách × 9 thế giới (bấm ô để xem tiến bộ, khoảng tin cậy, tiến bộ tracker báo, số lần nộp thêm); 4 thẻ H1–H4 bằng lời thường; biểu đồ độ chính xác dự báo của 7 mô hình; điểm chính và giới hạn.
5. **Luyện Python (sinh viên):**
   - Trang chủ luyện: mức thành thạo 3 kỹ năng (Bayes filter), bài gợi ý kèm lý do (kỹ năng mục tiêu, P(đúng), giá trị Q, nhãn "mô hình học từ mô phỏng"), thư viện 12 bài theo kỹ năng và trạng thái.
   - Không gian làm bài: đề, ví dụ, gợi ý từng bước; ô code (Tab thụt lề, tự thụt dòng sau dấu ":", Ctrl+Enter chạy); kết quả từng test; khi xong có thẻ "Mô hình đã cập nhật" (kỹ năng trước → sau) và bài tiếp theo.
   - Dùng chung kho lưu `retrylab.practice.v1`, nên tiến độ cũ còn nguyên và giao diện cũ vẫn thấy.
6. **Mô hình:** sơ đồ MDP (trạng thái 230 chiều, hành động 109 bài, phần thưởng), danh sách mô hình và độ chính xác, cách huấn luyện DQN/PPO, 9 thế giới, phạm vi và giới hạn; liên kết tới bản thảo PDF.
7. **Lưu trữ:** mở giao diện cũ (/classic) với các công cụ nghiên cứu trước đây.

## 5. API mới (chỉ đọc, dữ liệu từ run đã khóa)

| Phương thức | Đường dẫn | Trả về |
|---|---|---|
| GET | `/api/v3/learners` | Thêm tóm tắt: số bài, tỉ lệ đúng, kỹ năng yếu nhất, dự báo post-test |
| GET | `/api/v3/learners/<id>/explain?policy=` | Bài được chọn, 5 ứng viên với điểm của chính sách (Q của DQN, xác suất của PPO, tiêu chí của luật), đường đi ID3 và xác suất lá |
| POST | `/api/v3/session` | `{learner_id, world, policy, forced: [0/1/null ≤10]}` → 10 bước: bài, kết quả, P(đúng) của tracker và thế giới, số lần nộp, phần thưởng, độ trôi, post-test tracker/thế giới sau bước, mức kỹ năng sau bước; tổng kết tiến bộ thật/báo cáo/độ trôi/bất ngờ |

Các endpoint cũ giữ nguyên cho /classic. POST vẫn cần token phiên như hiện tại; chỉ phục vụ localhost.

**Tính đúng:** phiên học dựng lại từng bước bằng chính các lớp của nghiên cứu (world, tracker, policy) với cùng seed nên **khớp tuyệt đối** với `run_episodes` khi không ép kết quả (kiểm bằng test). Ép Đúng/Sai được thực hiện bằng số ngẫu nhiên 0/1 đưa vào đúng hàm của thế giới, không sửa mã nghiên cứu. Đặc trưng ID3 được tính lại giống hệt `tree_features` (kiểm bằng test).

## 6. Xử lý lỗi và tính trung thực

- Thiếu run v3 hoặc sai mã băm → các màn hình dữ liệu thật hiện lý do cụ thể; Luyện Python vẫn chạy.
- Python trong trình duyệt không khởi động → thông báo và nút thử lại; code không bao giờ gửi lên server.
- Lỗi API → thông báo ngắn tại chỗ, không làm trắng màn hình.
- Nhãn cố định: "kết quả phiên học là mô phỏng", "mô hình luyện Python học từ người học mô phỏng", "mã học viên là ẩn danh cục bộ"; không hiển thị mã người học gốc.

## 7. Bảo toàn

- Không sửa `engine.py` (tệp được bảo vệ), các run nghiên cứu, bản thảo.
- Không xóa hay đặt lại tiến độ luyện tập; kiểm thử dùng ngữ cảnh trình duyệt tạm.
- Giao diện cũ giữ ở `/classic`; các test cũ chạy lại trên đường dẫn đó.

## 8. Kiểm thử và nghiệm thu

- **Backend (unittest):** phiên học khớp `run_episodes`; ép kết quả được tôn trọng; tổng phần thưởng = tiến bộ thật − λ × nộp thêm; tiến bộ tracker = tổng độ trôi + tổng bất ngờ; đặc trưng và xác suất ID3 khớp mã nghiên cứu; điểm ứng viên sắp xếp đúng và bài được chọn trùng hành động của chính sách; JSON không có NaN; đầu vào sai → 400; POST thiếu token → 403.
- **Trình duyệt (Playwright, ngữ cảnh tạm):** mở từng màn hình không có lỗi console; chọn học viên cập nhật bản đồ kỹ năng; phiên học vẽ đủ 10 bước và tổng kết; đối chứng âm cho tiến bộ thật = 0; bảng thuyết trình đi hết 8 bước; Luyện Python: mở bài gợi ý, nhập lời giải đúng, qua 8/8 test, thấy thẻ cập nhật và bài tiếp theo; /classic vẫn mở được.
- **Khởi chạy:** `desktop.py --dry-run` tìm đúng trình duyệt và tham số; tái dùng server đang chạy, không mở trùng.
- **Harness:** thêm test mới vào các bộ `backend` và `browser`, bộ `fast`/`policy`/`demo` vẫn đạt.
