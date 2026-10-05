# Biên bản kiểm tra RetryLab

**Biên bản lịch sử trước tích hợp policy.** Kiểm tra bản 12 bài/Double DQN mới ở `TOPIC4_VALIDATION.md`; không dùng số 8 bài hoặc quy tắc cũ bên dưới để mô tả phiên bản hiện tại.

Ngày kiểm tra: 26/09/2026. Đây là kiểm tra vận hành của app bổ sung sau thí nghiệm; không phải thử nghiệm người dùng hoặc phép kiểm chứng hiệu quả giáo dục mới.

## Phiên bản thiết kế lại: luồng sinh viên

Playwright/Chromium chạy Python thật bằng Pyodide 314.0.7 trên localhost, không giả lập kết quả bộ kiểm tra:

- Trang mặc định mở vào luyện tập; 8 bài đều có đề, ví dụ, khung hàm và phản hồi. Không tải API nghiên cứu để hiển thị trang luyện tập.
- Tám lời giải tham chiếu đi qua **64 trường hợp kiểm tra**; bài sai cho thấy đầu vào, đầu ra thực tế và đầu ra cần có. Lỗi khởi tạo giá trị lớn nhất bằng 0 bị phát hiện ở danh sách toàn số âm/rỗng.
- Kiểm tra lỗi cú pháp và vị trí dòng, sai tên hàm, nhầm `print` với `return`, vòng lặp quá 2,5 giây và chạy lại thành công sau lỗi.
- Dừng trong lúc khởi động Python hoặc đang chạy không được ghi là một lần chấm. Chuyển bài giữa lúc chạy không làm kết quả cũ ghi đè hoặc tắt worker của bài mới.
- Kiểm tra bản nháp sau tải lại, đánh dấu kết quả cũ khi sửa mã, hoàn tác đặt lại mã, Ctrl + Enter, Tab và xuất nhật ký với namespace riêng.
- Tiến độ 8/8 và các bản ghi xuất khớp thao tác thử nghiệm. Đã kiểm tra hai nhánh chọn bài củng cố/vận dụng và trạng thái hoàn tất bộ bài.
- Các màn hình luyện tập, viết mã, tiến độ và cổng nghiên cứu không tràn chiều ngang toàn trang ở **390 px và 768 px**; mã dài có vùng cuộn riêng.
- Không có yêu cầu ra ngoài localhost và không có POST mã người học trong luồng luyện tập đã kiểm tra. Không có lỗi JavaScript hoặc console trong lần chạy ghi nhận.

Chi tiết: `test_outputs/practice_browser_report.json`; mã: `tests/practice_browser_check.py`. Ảnh `v2-home-desktop.png`, `v2-exercise-feedback.png`, `v2-exercise-passed.png` và `v2-mobile-*.png` đã được tạo để rà soát bố cục.

Kiểm tra bổ sung `tests/practice_recovery_check.py` xác nhận: một lần đúng có mở gợi ý chuyển sang bài củng cố; nội dung `print` hiển thị được; nút Back và skip link giữ đúng trang; bản lưu hỏng được phục hồi; trình duyệt chặn lưu vẫn chạy được bài và báo rõ chưa lưu. Biên bản: `test_outputs/practice_recovery_report.json`.

Kiểm tra này xác nhận hành vi phần mềm trên Chromium của máy hiện tại. **64 test không phải 64 người học hoặc một thực nghiệm hiệu quả học tập**. Chưa thực hiện nghiên cứu khả dụng với sinh viên thật hoặc kiểm tra trên mọi trình duyệt.

## Tính đúng của dữ liệu và suy luận

- Tái dựng đủ **69.825 cặp**, khớp tập mã cặp và nhãn với cả năm tệp dự báo theo mô hình. Đây là kiểm tra toàn bộ coverage; không đồng nghĩa đã chạy lại suy luận từng cặp của tất cả mô hình trong phiên kiểm thử app.
- Đối chiếu suy luận lại trên **20 hồ sơ**: hai đầu danh sách, 16 hồ sơ theo seed cố định 8773, chuỗi dài nhất (135 lần nộp) và hồ sơ có lịch sử trước chuỗi dài nhất. Cả năm mô hình đạt ở H0/H1.
- Sai số tuyệt đối lớn nhất trên các hồ sơ kiểm tra: Logistic ALL **1,67×10⁻¹⁶**; Logistic FIRST **1,39×10⁻¹⁶**; Logistic PAIRED **1,67×10⁻¹⁶**; GRU ALL **5,96×10⁻⁸**; GRU FIRST **3,97×10⁻⁸**. Dung sai chặn hiển thị lần lượt `1e-12` và `2e-6`.
- App tiếp tục kiểm tra H0/H1 với dự báo gốc khi người dùng mở mỗi hồ sơ mới; không giới hạn kiểm tra này vào 20 ví dụ trên.
- Đặc trưng lịch sử logistic đối chiếu với hàm trong nghiên cứu gốc; thay nhãn tương lai không thay đổi dự báo.
- Chạy giả lập với chuỗi gốc tái hiện đúng dự báo. Thay đầu vào làm thay dự báo của cả logistic và GRU; không gọi mô hình giả hoặc số ngẫu nhiên.
- Mô hình PAIRED không nội suy phase cho bước giữa chuỗi.
- **20 tổ hợp** mô hình × giai đoạn × quy tắc được kiểm tra số hồ sơ đánh dấu, số thất bại phát hiện, recall và workload: khớp tuyệt đối với kết quả nghiên cứu.
- Dữ liệu/checkpoint/ngưỡng/tệp dự báo được kiểm tra hash với khóa gốc. Từ vựng GRU được ghi nhận hash và kiểm tra gián tiếp qua đối chiếu dự báo; không diễn đạt hash mới ghi nhận như một khóa đã tồn tại trước nghiên cứu.

Chi tiết: `test_outputs/model_parity.json`; kiểm tra tự động: `tests/test_engine.py` (**15 test đạt**).

## Kiểm tra khu nghiên cứu sau thiết kế lại bằng Chromium

Đã dùng Playwright để kiểm tra luồng thật trên trình duyệt:

1. Nạp hồ sơ và checkpoint; không yêu cầu endpoint kết quả bài đích trước khi bấm mở.
2. Xuất JSON trước khi mở kết quả: nhãn bài đích bị bỏ khỏi tệp xuất.
3. Đổi mô hình, phát lại đến H1, chọn phase trung gian, mở kết quả và hiển thị NLL.
4. Thay đầu vào, chạy suy luận, thêm lần nộp, cảnh báo kết quả cũ sau khi chỉnh và khôi phục chuỗi.
5. Đối chiếu số trên màn hình với **45,27% recall**, **30,81% workload** của GRU FIRST ở quy tắc validation 30%; đổi sang quy tắc recall 80%.
6. Thử ngưỡng 0% và 100%; xuất đúng 20 dòng số liệu tổng hợp.
7. Tìm và chuyển hồ sơ; nhãn bài đích trở về trạng thái ẩn.
8. Bốn màn hình không tràn chiều ngang toàn trang ở chiều rộng 390 px. Bảng rộng có cuộn riêng.

**Không có lỗi JavaScript hoặc lỗi console** trong luồng kiểm tra. Đã xem trực quan ảnh desktop và mobile; chỉnh kích thước biểu đồ mobile và bảo đảm không ẩn hồ sơ khỏi danh sách khi màn hình hẹp.

Biên bản máy đọc: `test_outputs/browser_report.json`. Ảnh: `test_outputs/01-replay-initial.png` đến `08-mobile-evidence.png`.

## Đo phản hồi API nghiên cứu cục bộ (phép đo trước thiết kế lại)

Máy kiểm tra: Intel Core i5-10300H, 4 nhân / 8 luồng; suy luận CPU. Trên 12 mã hồ sơ cố định chưa có trong bộ nhớ đệm replay của máy chủ lúc đo:

- Trung vị thời gian yêu cầu HTTP: **102,25 ms**.
- Phân vị 95% trên 12 phép đo: **152,33 ms**.
- Khởi động nạp artifact và mô hình trong lần đo riêng: khoảng **8,9 giây**.

Các thời gian này là đo API replay, không phải thời gian khởi động hoặc thực thi Python trong trình duyệt. Đây là phép đo nhỏ trên máy hiện tại, không phải benchmark tải lớn, bảo đảm độ trễ hoặc so sánh thuật toán. Cache, độ dài lịch sử và cấu hình máy làm thay đổi thời gian. Dữ liệu đo nằm trong `test_outputs/latency.json`.

## Ranh giới kết luận

App cho thấy pipeline có thể vận hành, cho phép kiểm tra và tái hiện các số đo. Nó không biến kết quả hồi cứu thành bằng chứng nhân quả, không xác lập chất lượng chọn bài tập và không thay thế thử nghiệm với người học. Phần giả lập không được đưa vào các kết quả nghiên cứu đã khóa. Bản thảo, checkpoint và gói nghiên cứu trước đó được giữ nguyên.
