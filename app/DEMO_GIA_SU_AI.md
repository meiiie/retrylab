# Demo RetryLab — Gia sư AI (giao diện mới, 29/09/2026)

Kịch bản cho giao diện chính mở bằng `RetryLab.cmd`. Mọi số liệu dưới đây đọc từ hai run đã khóa `accoding-learner-v3` và `accoding-policy-v3`; ứng dụng kiểm tra hash của cả hai run trước khi hiển thị. Chính sách chọn bài chỉ được đánh giá trong mô phỏng, chưa thử với sinh viên thật. Hướng dẫn cũ ([DEMO_READY.md](DEMO_READY.md)) mô tả giao diện trước đây, nay ở `/classic`.

## 1. Chuẩn bị (10–15 phút trước)

1. Bấm đúp `app/check_demo.cmd` và đợi `DEMO CHECK PASSED`. Lệnh này kiểm tra hash, mở hoặc tái sử dụng máy chủ, rồi diễn tập trong một trình duyệt riêng, không đụng tới tiến độ luyện tập của bạn.
2. Bấm đúp `RetryLab.cmd` ở thư mục gốc (hoặc lối tắt RetryLab trên Desktop). Ứng dụng mở trong cửa sổ riêng tại `http://127.0.0.1:8773/`. Đợi cuối thanh bên hiện **● Mô hình sẵn sàng**; lần khởi động đầu mất khoảng 20–40 giây.
3. Nhấn F11 để toàn màn hình. Giao diện được kiểm tra ở 1440×900; cửa sổ hẹp hơn vẫn dùng được, các cột tự xếp chồng.
4. Mở thử **Mô hình → Bản thảo tiếng Việt (PDF)** để chắc tệp PDF mở được.
5. Lần luyện Python trong buổi demo được ghi vào tiến độ luyện tập của trình duyệt này, như một lần luyện bình thường. Muốn tách riêng, chạy `.\RetryLab.cmd --browser chrome` để dùng trình duyệt khác. Không xóa dữ liệu trình duyệt.

## 2. Kịch bản 8 phút

Bấm **Thuyết trình** ở thanh bên (hoặc **Bắt đầu thuyết trình** trên Tổng quan). Mỗi bước tự chuyển màn hình (kể cả đúng tab ở màn Học viên), viền xanh đánh dấu vùng cần nói và lời gợi ý hiện ở một góc không che vùng đó. Dùng **Tiếp** / **Lùi** hoặc phím → / ←; Esc để đóng. Trong lúc đóng khung thuyết trình, mọi nút vẫn bấm được.

| Bước | Màn hình | Ý chính | Số cần nhớ |
|---|---|---|---|
| 1 | Tổng quan | Đề tài 4: hệ gợi ý bài tập lập trình thích ứng. Chuỗi năm khâu: dữ liệu → mô hình người học → luật ID3 → chính sách chọn bài (MDP, DQN/PPO) → đánh giá. | 4.634 học viên, 562.912 lần nộp đầu, 3.882 bài trên ACcoding (lập trình C) |
| 2 | Học viên L035 · kỹ năng | DKT dự báo xác suất làm đúng từng bài. Mức kỹ năng được so với trung bình 60 học viên mẫu, vì bài vòng lặp vốn khó hơn nên con số thô luôn thấp. | Học viên kiểm tra (926 người) chưa dùng khi huấn luyện |
| 3 | Học viên · cây ID3 | Cây quyết định theo entropy và information gain biến dự báo thành luật đọc được, hữu ích cho giảng viên. | AUC: DKT 0,775; ID3 0,763 |
| 4 | Học viên · gợi ý | MDP: trạng thái là ước lượng kiến thức trên 109 bài; hành động là bài tiếp theo; phần thưởng là tiến bộ ở 16 bài kiểm tra cuối trừ λ × số lần nộp thêm. Xem vì sao PPO chọn bài này và 5 lựa chọn hàng đầu. | λ = 0,05; phiên 10 bước, không lặp bài |
| 5 | Phiên học · AFM-B, PPO-AFM | Vòng gợi ý → làm bài → cập nhật trong 10 bước. Trong thế giới có học thật, tiến bộ thật khiêm tốn. | L035: tiến bộ thật +3,7 điểm; tracker báo +14,6 |
| 6 | Phiên học · IRT-B, PPO-KT | Đối chứng âm: thế giới không có học, tiến bộ thật luôn bằng 0, nhưng tracker vẫn báo tăng mạnh. Đó là **tiến bộ ảo**, phát hiện chính. | L035: thật 0,0; tracker +31,4 (trôi +32,3). Toàn bộ 926 lần: PPO-KT +25,7 [25,1; 26,4] |
| 7 | Đánh giá | Ma trận 14 chính sách × 9 thế giới và bốn giả thuyết đăng ký trước. Xếp hạng trong bộ mô phỏng huấn luyện gần trùng với xếp hạng tiến bộ ảo. | Spearman 0,96; PPO-KT: +28,6 trong DKT-A nhưng thật 0 trong IRT-B |
| 8 | Luyện tập (Python, C) | Phần dành cho người học: code Python thật chạy ngay trong ứng dụng, mô hình cập nhật và gợi ý bài tiếp theo. Kết thúc bằng phạm vi trung thực và hướng tiếp theo. | 12 bài, 96 test; mô hình phần này học từ người học mô phỏng |

Ở bước 8, nếu còn thời gian, làm thật một bài. Với người chưa có lịch sử, bài được gợi ý đầu tiên là **Tìm số lớn nhất**; nếu trình duyệt của bạn gợi ý bài khác, mở thẳng `#/practice/maximum`. Dán lời giải mắc lỗi quen thuộc (khởi tạo bằng 0):

```python
def so_lon_nhat(numbers):
    best = 0
    for x in numbers:
        if x > best:
            best = x
    return best
```

Bấm **Chạy kiểm tra** (Ctrl + Enter): qua 5/8 test; bảng kết quả chỉ ra danh sách rỗng và danh sách toàn số âm. Sửa lại:

```python
def so_lon_nhat(numbers):
    if not numbers:
        return None
    best = numbers[0]
    for x in numbers[1:]:
        if x > best:
            best = x
    return best
```

Qua 8/8 test, mục **Mô hình đã cập nhật** cho thấy niềm tin về kỹ năng thay đổi thế nào, và ứng dụng gợi ý bài kế tiếp kèm lý do. Nói rõ: qua test không đồng nghĩa đã thành thạo; các con số là ước lượng của mô hình.

**Luyện C** (nút **C** ở đầu màn Luyện tập, hoặc `#/practice-c/c-sum-positive`). Bài "Tổng số dương": dán lời giải quên bỏ số âm —

```c
int tong_duong(int a[], int n) {
    int tong = 0;
    for (int i = 0; i < n; i++) {
        tong += a[i];
    }
    return tong;
}
```

— một số test sai; sửa dòng cộng thành `if (a[i] > 0) tong += a[i];` là đạt 8/8. Muốn cho thấy lỗi chạy, đổi điều kiện vòng lặp thành `i <= n`: trình thông dịch báo truy cập ngoài mảng và chỉ đúng test. Nói rõ: bài C tự soạn, nhãn kỹ năng theo nhóm ACcoding nhưng chưa kiểm chứng chuyển giao; bài gợi ý chọn bằng quy tắc vùng phát triển gần (~65%), không phải mô hình học. Mã chạy bằng trình thông dịch JSCPP ngay trong ứng dụng, chậm hơn C thật.

**Bản 3 phút:** bước 1 → bước 6 → bước 8.

## 3. Câu hỏi thường gặp

- **Dữ liệu là C, sao phần luyện lại là Python?** Bộ 12 bài Python do nhóm tự soạn, không chung mã bài với ACcoding. Mô hình gợi ý ở phần này được huấn luyện trên người học mô phỏng của chính bộ bài đó; mô hình ACcoding không được gán cho bài Python. Nay đã có thêm 13 bài C (nút **C**), gắn theo nhóm kỹ năng ACcoding nhưng chưa kiểm chứng chuyển giao, gợi ý bằng quy tắc minh bạch.
- **Sao không thử với sinh viên thật?** Đề tài không có dữ liệu của giảng viên và không có kế hoạch can thiệp. Kết quả tiến bộ ảo cho thấy vì sao không nên tin con số của bộ mô phỏng khi chưa kiểm chứng độc lập.
- **RL có tốt hơn quy tắc đơn giản không?** Trong AFM-B, PPO-AFM đạt +3,14 điểm, gần oracle một bước (+3,48) và cao hơn chọn ngẫu nhiên (+1,72). Khoảng cách nhỏ; tác tử học từ phần thưởng DKT có số rất đẹp trong mô phỏng của chính nó nhưng không giữ được ở thế giới khác.
- **Tiến bộ ảo đến từ đâu?** Tiến bộ tracker báo = trôi (tracker tự kỳ vọng học lên sau mỗi bài) + bất ngờ (phản ứng với kết quả thật). Ở IRT-B phần trôi chiếm gần hết.
- **Có rò rỉ dữ liệu không?** Học viên được chia A/B/T theo người; mô hình chỉ fit trên A hoặc B, mọi phép đánh giá bắt đầu từ lịch sử của 926 học viên T.

## 4. Nếu có sự cố

- Thanh trạng thái báo lỗi hoặc không hiện **Mô hình sẵn sàng** sau 1 phút: đóng cửa sổ, bấm lại `RetryLab.cmd`; nếu vẫn lỗi, chạy `app/check_demo.cmd` và đọc thông báo.
- Python chạy chậm lần đầu: runtime Pyodide nạp khoảng vài giây; đợi nút chạy được bật lại, không bấm liên tục.
- Cần giao diện cũ: **Lưu trữ (giao diện cũ)** ở cuối thanh bên, hoặc `http://127.0.0.1:8773/classic`.
- Ảnh chụp dự phòng của từng màn hình ở `app/test_outputs/studio/`.

## 5. Những gì demo này không chứng minh

- Không chứng minh hiệu quả học tập với người thật; mọi kết quả chính sách đến từ mô phỏng.
- Mức kỹ năng, xác suất dự báo, số test qua và tiến bộ là bốn đại lượng khác nhau; không dùng cái này thay cái kia.
- Thế giới ZPD là giả định lý thuyết, không được fit từ dữ liệu.
