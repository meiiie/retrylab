# Biên bản kiểm thử trước buổi demo — 26/09/2026

**Kết luận: đạt các luồng vận hành và phục hồi liệt kê dưới đây trên máy Windows hiện tại.** Có thể dùng bản này để demo kỹ thuật. Đây là kiểm thử phần mềm, không phải xác nhận tính tối ưu của policy hoặc hiệu quả giáo dục. Không tìm thấy lỗi ứng dụng cần sửa trong các ca đã chạy; phần bổ sung là công cụ kiểm tra, kịch bản và bằng chứng phục hồi.

## Phạm vi đã thực thi

| Nhóm | Kết quả và bằng chứng |
|---|---|
| Hồi quy toàn bộ trước bổ sung suite demo | 40 kiểm tra harness/policy/backend và 4 script trình duyệt đều đạt; 212,315 giây. `.harness/reports/20260926T152931373126/report.json` |
| Bài tập thật | 12 lời giải, 96 test chạy bằng Python trong trình duyệt; lỗi cú pháp, thiếu hàm, print/return, timeout, hủy và đổi bài khi đang chạy đều có kiểm tra |
| Mô hình và nghiên cứu | Parity Python/JavaScript, Q lớn nhất trong tập hợp lệ, giới hạn lịch sử, không sử dụng nhãn tương lai, dự phòng có nhãn, phát lại/log/CSV đều đạt |
| Suite demo bổ sung | Diễn tập đầy đủ và khởi động lại server riêng đều đạt; 101,141 giây. `.harness/reports/20260926T153815799504/report.json` |
| Edge 154.0.4258.37 | Luồng demo, chặn Internet ngoài localhost và bốn nhóm lỗi giả lập đạt; `app/test_outputs/demo/20260926T153557818155-msedge/report.json` |
| Chrome 153.0.8010.53 | Luồng demo và preflight đạt; `app/test_outputs/demo/20260926T153738550288-chrome/report.json` |
| Chromium 151.0.7922.34 | Luồng demo và bốn nhóm lỗi giả lập đạt; `app/test_outputs/demo/20260926T153816331681-chromium/report.json` |
| Nút kiểm tra cho người trình bày | Đã chạy thật `app/check_demo.cmd` qua cmd.exe, mã thoát 0, xuất `DEMO CHECK PASSED`; report `20260926T153611974426-msedge` |
| Khởi động, đóng và mở lại | Server riêng chạy từ thư mục khác; launcher tái sử dụng server; đóng/mở lại và lấy phiên nghiên cứu mới sau reload đều đạt. Hai lần diễn tập: `20260926T153357380490-restart`, `20260926T153853466865-restart` |
| Runtime và artifact | 7 tệp runtime và 4 tệp catalog/model/kết quả/parity khớp SHA-256; 85 tệp nghiên cứu lịch sử giữ nguyên |
| Giao diện | Kiểm tra 390, 768, 1366 và 1440 pixel theo từng bộ; không tràn ngang toàn trang. Đã xem ảnh Fibonacci sai/đúng và bàn thử nghiệm |

Các số phiên bản là kết quả trên máy lúc kiểm tra, không phải khuyến cáo phiên bản mới nhất. `all` của harness hiện bao gồm thêm `demo`; biên bản hồi quy cũ và biên bản demo được giữ riêng, không sửa một lần chạy cũ để giả như đã chạy bộ mới.

## Luồng thuyết trình đã diễn tập

1. Hồ sơ trình duyệt mới, mở bài Fibonacci, lời giải `return n` cho **2/8**, sửa lời giải lặp cho **8/8**.
2. Policy gợi ý bài tiếp theo; nút mở đúng đề đã chọn. Không giả định trước rằng đổi kết quả sẽ luôn đổi tên bài được gợi ý.
3. Tiến độ ghi 1/12; xuất journal có hai quan sát hợp lệ. Bàn thử nghiệm đọc cùng trạng thái và cùng hai quan sát.
4. Bốn ca giả định gồm người mới, đúng ngay, sai–sai–đúng và hai bài cùng kỹ năng. Mọi phép thử giữ nguyên nhật ký thật của context.
5. Bảng đủ bảy chính sách ở cả năm môi trường. Môi trường chỉ nhớ bài cũ có transfer gain bằng 0; giữ nguyên cả kết quả chính sách thua đối chứng.
6. Bài được gợi ý mở được; reload giữ mã; không tự thêm quan sát. Các route và tài liệu cục bộ tải thành công.

## Các tình huống sự cố đã kiểm tra

- **Không có Internet ngoài localhost:** dùng browser context mới, chặn mọi request ra ngoài. Không phát sinh request bên ngoài trong kịch bản. Không có CDN/API key/GPU trong luồng demo này. Server localhost vẫn cần chạy.
- **Model trả 503:** Python vẫn chấm thật, gợi ý ghi rõ dự phòng. Khôi phục tài nguyên rồi mở bàn thử nghiệm dùng lại model được.
- **Bộ chấm Python trả 503:** hiện lỗi, giữ nguyên mã, không ghi thêm lần chấm vào lịch sử; chạy lại sau khi khôi phục đạt 8/8.
- **Bảng kết quả hoặc API nghiên cứu trả 503:** hiện lỗi và phục hồi khi mở lại trang sau khi tài nguyên đã có.
- **Máy chủ tắt thật:** nút suy luận được bật lại sau lỗi; mở máy chủ lại, trang cũ yêu cầu reload vì token đã đổi. Reload khôi phục suy luận và giữ bản nháp. Chỉ dừng các PID do bài kiểm tra tạo, không đụng server 8773 hoặc hồ sơ người dùng.
- **Bản nháp, storage, hủy code:** các kiểm tra hồi quy gồm lưu qua reload, hoàn tác reset, kho lưu bị chặn/hỏng và hủy lúc Python đang khởi động.

Bốn lần nạp server trong hai buổi diễn tập mất **16,432–28,163 giây**, dưới hạn 90 giây của launcher. Đây là số đo trên máy này; nên mở ứng dụng trước buổi báo cáo. Thời gian ở `first_python_run` bắt đầu khi bấm chạy, sau bước chuẩn bị Python của trang, không phải toàn bộ thời gian khởi động runtime.

## Lần kiểm tra thất bại được giữ lại

`app/test_outputs/demo/20260926T153238123999-msedge/report.json` ghi `passed: false`: test chờ `networkidle` khi cố ý làm bộ chấm tải thất bại. Worker kết thúc nhưng trạng thái chờ mạng của trình duyệt không kết thúc trước hạn. Script được sửa để trong riêng ca lỗi này chờ ô mã dùng được và phản hồi lỗi cụ thể, rồi vẫn kiểm tra mã còn nguyên, không thêm quan sát và chạy lại thành công. Edge và Chromium đều đã chạy lại đạt. Không bỏ assertion chức năng, không ghi đè biên bản thất bại.

## Tài liệu giao cho người trình bày

- `app/check_demo.cmd`: kiểm tra trước buổi báo cáo; tự mở/reuse server, xác minh hash và diễn tập bằng context riêng.
- `app/DEMO_READY.md`: kịch bản 8 phút, lời giải, địa chỉ, thao tác khôi phục và lưu ý về kho dữ liệu theo trình duyệt/địa chỉ.
- `harness/demo_validation.json`: chỉ mục máy đọc được, SHA-256 của bằng chứng và nguồn hiện tại.
- Ảnh dự phòng đã xem: `app/test_outputs/demo/20260926T153611974426-msedge/01-fibonacci-wrong.png`, `02-fibonacci-correct.png`, `03-policy.png`. Đây là ảnh từ buổi diễn tập, không phải bằng chứng sinh viên thật.

Phạm vi không bao gồm máy khác chưa cài đặt, triển khai Internet cho nhiều người, mọi chương trình Python có thể có hoặc sự cố phần cứng của ngày trình bày. Dữ liệu cá nhân và tiến trình của người dùng được giữ nguyên. Bộ nguồn ZIP không thay thế cả workspace và các artifact nghiên cứu cần để khởi động app.
