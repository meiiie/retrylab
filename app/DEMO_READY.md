# Vận hành và diễn tập đề 4

Hướng dẫn dành cho **máy Windows và workspace đang được kiểm thử**. Gói `retrylab_source.zip` chỉ là nguồn, không phải bản cài đặt đầy đủ để chuyển sang máy khác. Giữ nguyên cả workspace, Python, thư viện và runtime cục bộ nếu dùng máy này để trình bày. Kết quả kiểm tra kỹ thuật không chứng minh hiệu quả giáo dục.

## Trước buổi trình bày 15 phút

1. Cắm sạc, mở đúng workspace. Bấm đúp **`app/check_demo.cmd`**. Lệnh này kiểm tra hash runtime/model, mở hoặc tái sử dụng máy chủ, rồi thực hành tự động trong một trình duyệt riêng. Không xóa bài làm cá nhân, không huấn luyện lại, không cần GPU.
2. Đợi dòng **`DEMO CHECK PASSED`**. Nếu có `NOT READY`, đọc lỗi và đường dẫn `REPORT`; không coi việc mở được trang chủ là đã kiểm thử thành công.
3. Bấm đúp **`app/start.cmd`** để mở app. Lần mở đầu cần đợi nạp dữ liệu; không bấm liên tục. Cửa sổ launcher kết thúc không đồng nghĩa server đã tắt.
4. Chuẩn bị ba tab: `http://127.0.0.1:8773/#exercise/fibonacci`, `http://127.0.0.1:8773/#policy`, và PDF `output/pdf/retrylab-de4-bao-cao.pdf`.
5. Để diễn tập một người mới, mở cửa sổ InPrivate/Ẩn danh riêng, rồi nhập URL trên. Đóng cửa sổ riêng khi xong; giữ nguyên cửa sổ chứa bài làm cá nhân. Không bấm xóa dữ liệu trình duyệt.

Luôn dùng **`127.0.0.1:8773`**. `localhost`, cổng khác, trình duyệt khác và cửa sổ riêng có kho lưu bài riêng; đổi địa chỉ có thể khiến tiến độ trông như biến mất.

PDF cần trình bày là **`retrylab-de4-bao-cao.pdf`**. Các tài liệu trong trang **Phương pháp** của nhánh phát lại ACcoding là báo cáo dự báo lịch sử, không phải bản báo cáo chính sách mới. [Biên bản kiểm thử](DEMO_VALIDATION.md) ghi cụ thể trình duyệt, phép thử và ảnh dự phòng.

## Kịch bản 8 phút

**Phút 0–1 — nói rõ ba việc khác nhau.** Bộ chấm chạy code để biết đúng bao nhiêu test. Mô hình cập nhật ước lượng từ lịch sử đã biết. Chính sách học tăng cường chọn bài tiếp theo. Chúng ta chứng minh chuỗi này vận hành; thực nghiệm chính sách hiện là mô phỏng.

**Phút 1–3 — làm thật bài Fibonacci.** Mở `#exercise/fibonacci`, nhập lời giải cố ý sai:

```python
def fibonacci(n):
    return n
```

Bấm **Chạy kiểm tra**, đợi nút chạy được bật lại; xem test sai. Thay bằng lời giải đúng:

```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```

Chạy lại, chỉ vào **8/8**, gợi ý và nhãn chính sách. Bấm **Làm bài tiếp theo**: đề và khung hàm phải đổi sang đúng bài đã được gợi ý. Không hứa trước một tên bài vì gợi ý phụ thuộc lịch sử. Nếu mô hình gợi ý sửa tiếp bài hiện tại thì nút sẽ đưa con trỏ về ô mã.

**Phút 3–5 — giải thích lịch sử.** Mở `#policy`, chọn **Fibonacci · đúng ngay lần đầu**, rồi **Fibonacci · sai → sai → đúng**. Cả hai cùng có kết quả cuối đúng, nhưng lịch sử khác nhau nên trạng thái mô hình có thể khác. Đây là lịch sử giả định, không ghi vào bài làm cá nhân. Mở **Điểm Q, dự báo và bài bị loại**: bài được chọn phải có Q cao nhất trong các bài hợp lệ. Q không phải phần trăm; phần trăm không phải số test đúng.

**Phút 5–7 — trình bày phép đo.** Chọn môi trường **Chỉ nhớ bài cũ · không học thêm**: đúng nhiều bài luyện vẫn có thể có tiến bộ chuyển giao bằng 0. Quay lại **Giống cơ chế huấn luyện**: báo cáo cả kết quả chính sách thua đối chứng kỹ năng yếu nhất. Không nói đã đạt SOTA hoặc đã cải thiện năng lực người thật.

**Phút 7–8 — xuất dấu vết.** Bấm **Xuất dấu vết** trong bàn thử nghiệm; đó là JSON giả định nếu đang chọn ca mẫu. Muốn xuất bài làm thật, vào **Tiến độ → Xuất nhật ký**. Hai tệp có nguồn dữ liệu khác nhau. Kết thúc bằng giới hạn và hướng kiểm chứng tiếp.

## Nếu có sự cố trong buổi demo

| Tình huống | Cách xử lý đã đưa vào diễn tập |
|---|---|
| Mất Internet, nhưng máy chủ cục bộ vẫn chạy | Runtime, model và dữ liệu được phục vụ tại máy. Tiếp tục dùng URL cục bộ; không cần Kaggle, CDN hoặc API ngoài. Không tắt server. |
| Không mở được `127.0.0.1:8773` | Chạy lại `app/start.cmd`, đợi sẵn sàng, rồi tải lại tab. Xem `app/runtime/server-error.log` nếu launcher báo lỗi. |
| Máy chủ vừa khởi động lại, phần nghiên cứu yêu cầu tải lại trang | Tải lại tab để lấy phiên nghiên cứu mới. Bản nháp lưu ở cùng trình duyệt/địa chỉ vẫn còn. |
| Code chạy mãi | Bấm **Dừng chạy**, sửa code rồi chạy lại. Vòng lặp vượt giới hạn bị dừng tự động; thời gian khởi động Python là bước riêng. |
| Python chưa tải được | Đợi nút chạy bật lại, bấm chạy lại; nếu cần thì tải lại trang. Giữ bản nháp, không xóa dữ liệu. |
| Hiện “quy tắc dự phòng” | Đọc lý do. Có thể do lịch sử ngoài phạm vi hoặc model không tải được. Không gọi đó là quyết định RL; dùng ca giả định trong `#policy` để trình bày nhánh mô hình khi model hoạt động. |
| Nhật ký quá nhiều hoặc Fibonacci đã làm đúng trước đây | Dùng cửa sổ riêng cho luồng người mới; hoặc chọn ca giả định trong bàn thử nghiệm. Không sửa/xóa nhật ký cũ để tạo kết quả thuận lợi. |
| Không xử lý kịp sự cố | Mở PDF và ảnh diễn tập trong `app/test_outputs/demo/<lần-chạy>/`. Nói rõ đây là ảnh từ lần chạy đã kiểm tra, không giả làm demo trực tiếp. |

## Chạy lại kiểm tra bằng terminal

```powershell
python -X utf8 app/demo_check.py
python -X utf8 app/demo_check.py --channel chrome --faults
python -X utf8 tools/harness.py check --suite all
python -X utf8 app/tests/launch_recovery_check.py
```

Lệnh `--faults` cố ý làm một số tài nguyên tạm trả lỗi trong trình duyệt thử nghiệm. Lệnh cuối khởi động/tắt **server riêng trên cổng riêng**, không dừng server của bạn. Mỗi lần diễn tập lưu biên bản mới, kể cả lần thất bại. Trước khi dùng máy khác hoặc thay dependency/model, chạy lại kiểm tra trên đúng máy đó.
