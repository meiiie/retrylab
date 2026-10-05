# Kịch bản demo RetryLab trong 7 phút

Kịch bản này dành cho nhánh dự báo ACcoding đã khóa. Để demo toàn bộ đề 4 (model → policy → bài Python), dùng `../paper/DE_4_BAO_CAO_VA_DEMO.md`, mục 6.

Các hồ sơ và kết quả dưới đây đã được đối chiếu lại bằng API suy luận thật. Dùng **GRU · lần nộp đầu** xuyên suốt các ví dụ để không đổi mô hình nhằm lấy kết quả đẹp. Bốn hồ sơ thuộc R00001–R00004, được chọn và sắp lại sau khi đã biết kết quả để minh họa bốn tình huống. Chúng không phải mẫu ngẫu nhiên hoặc phép đánh giá mới.

## Chuẩn bị trước khi trình bày

1. Mở `http://127.0.0.1:8773/#learn`. Nếu máy chủ chưa chạy, bấm đúp `app/start.cmd` và đợi app sẵn sàng.
2. Tập thử phần Python để runtime và trình duyệt hoạt động ổn định. Không cần GPU hoặc kết nối tới dịch vụ chạy code từ xa.
3. Giữ một bản lời giải hiện tại của bạn nếu định thay bằng mã sai để diễn thử; có thể dùng cửa sổ duyệt riêng cho demo.
4. Chuẩn bị ba địa chỉ: `/#exercise/count-positive`, `/#replay`, `/#evidence` trên cùng máy chủ.
5. Kiểm tra trước mã hồ sơ và mô hình. Mỗi khi đổi hồ sơ, kết quả bài đích được ẩn lại, nhưng lựa chọn mô hình có thể được giữ.
6. Nếu chỉ có 3 phút, demo sửa code, R00001 và kết quả toàn tập. Nếu có 7 phút, làm đủ kịch bản bên dưới. Không dành thời gian đi qua tất cả các nút.

## 0:00–0:30 — Nói rõ hai phần

“Em sẽ trình bày hai việc. Phần luyện tập cho thấy người dùng có thể viết code, nhận phản hồi và tiếp tục làm bài. Phần nghiên cứu kiểm tra xem thêm thông tin từ các lần nộp lại có giúp dự báo bài tiếp theo tốt hơn hay không. Hai phần hiện dùng dữ liệu riêng.”

## 0:30–1:40 — Tình huống 1: có lỗi thật và sửa được lỗi

Mở bài **Đếm số dương** và nhập mã cố ý sai:

```python
def dem_so_duong(numbers):
    dem = 0
    for so in numbers:
        if so >= 0:
            dem += 1
    return dem
```

Bấm **Chạy kiểm tra**. Kết quả dự kiến **5/8**. Trường hợp `[-1, 2, 2, 0, 5]` trả về `4`, trong khi đề yêu cầu `3`. Mở chi tiết test; `[0]` cũng sai vì hàm trả `1` thay vì `0`.

Nói: “Em cố ý tính nhầm số 0 là số dương. App cho thấy đầu vào gây lỗi và kết quả cần trả về để người dùng có thể sửa.”

Chỉ sửa `so >= 0` thành `so > 0`, bấm chạy lại. Kết quả **8/8**. Mở các test để chỉ ra danh sách rỗng `[]` trả `0`, toàn số âm trả `0`, số dương lặp lại vẫn được đếm từng lần.

Nói: “Đây là kiểm tra kết quả chạy của chương trình. Nó chưa xác nhận người viết đã thành thạo hoặc đã học được nhờ app.”

Có thể chỉ vào bài tiếp theo và đọc lý do gợi ý. Không hứa một tên bài cố định nếu trình duyệt đã lưu tiến độ cũ.

## 1:40–4:40 — Bốn tình huống dự báo

Mở **Nghiên cứu → Xem một trường hợp**. Chọn **GRU · lần nộp đầu**.

Lặp cùng một thao tác cho từng hồ sơ:

1. Mở **Đổi hồ sơ hoặc tìm một trường hợp khác**, nhập mã hồ sơ, bấm vào kết quả.
2. Đọc xác suất ở lần nộp đầu của bài hiện tại. Đây là dự báo cho lần nộp đầu của **bài tiếp theo cố định**.
3. Bấm **Xem sau các lần sửa**. So sánh dự báo mới cho cùng bài đích.
4. Bấm **Mở kết quả thực tế**. Dành một câu để giải thích.

| Thứ tự | Hồ sơ | Bài hiện tại → bài đích | Xác suất AC H0 → H1 | Kết quả thật ở lần nộp đầu bài đích | Câu nên nói |
|---|---|---|---|---|---|
| 1 | **R00004** | #7800 → #10179 | **87,4% → 89,4%** | **AC**, được chấp nhận | “Ở ví dụ này, mô hình tăng xác suất thành công và bài tiếp theo thực sự được chấp nhận. Dự báo sau phù hợp hơn với kết quả.” |
| 2 | **R00001** | #9927 → #9954 | **33,4% → 29,6%** | **TLE**, quá thời gian | “Mô hình hạ xác suất thành công. Bài tiếp theo thực sự chưa được chấp nhận. Vì vậy cập nhật hữu ích không nhất thiết làm đường dự báo đi lên.” |
| 3 | **R00002** | #9777 → #9792 | **80,0% → 80,0%** khi làm tròn | **PE**, chưa được chấp nhận | “Mô hình nghiêng nhiều về thành công nhưng kết quả thực tế khác đi. Xác suất 80% không phải lời bảo đảm, và mô hình có thể dự báo kém ở từng hồ sơ.” |
| 4 | **R00003** | #10218 → #10213 | **50,2% → 45,9%** | **AC**, được chấp nhận | “Lần cập nhật này hạ xác suất thành công nhưng bài tiếp theo lại thành công. Trên hồ sơ này, điểm phạt dự báo tăng. Thêm dữ liệu không đảm bảo mọi dự đoán đều tốt hơn.” |

Lưu ý quan trọng:

- R00002 chỉ thay đổi rất nhỏ: 79,9609% → 79,9905%, tức +0,0296 điểm phần trăm. Hai xác suất cùng hiển thị 80,0% do làm tròn; không mô tả là tăng mạnh.
- Ở R00001, chuỗi A là WA → WA → WA → WA → WA → AC. Bài A đã qua ở lần cuối không bảo đảm bài B qua ngay lần đầu. Đường dự báo có thể tăng ở bước cuối nhưng H1 vẫn thấp hơn H0.
- R00003 minh họa một cập nhật làm NLL của chính trường hợp đó xấu đi. Nó không chứng minh mô hình có xác suất 45,9% là “luôn sai” hoặc bị lỗi phần mềm.
- Các xác suất nói về kết quả chấm bài. Không gọi chúng là phần trăm kiến thức hoặc năng lực của người học.
- Bài đích là bài tiếp theo đã quan sát trong log, không phải một bài do AI lựa chọn và đã chứng minh tối ưu.

## 4:40–6:10 — Quay về kết quả toàn tập

Bấm **Xem kết quả toàn tập** hoặc mở **Kết quả toàn tập** trong thanh điều hướng nghiên cứu.

1. Chọn **GRU · lần nộp đầu**.
2. Chọn **Khoảng 30% hồ sơ trên validation**.
3. Chỉ hai thẻ đầu:
   - Phát hiện thất bại: **44,58% → 45,27%**.
   - Hồ sơ cần xem xét: **30,71% → 30,81%**.

Nói: “Bốn hồ sơ vừa rồi chỉ giúp giải thích. Kết luận chung dựa trên 69.825 cặp của 1.500 người học. Ở cấu hình này, hệ thống phát hiện thêm một ít trường hợp thất bại và cần xem xét thêm một ít hồ sơ. Đây là lợi ích nhỏ, có đánh đổi, và không đúng đồng loạt cho mọi mô hình hoặc ngưỡng.”

Nếu thầy hỏi phép đo chính, chuyển **Logistic · lần nộp đầu**, chỉ NLL **0,5811 → 0,5795**, Δ **−0,001566** với CI95% **[−0,002300; −0,000756]**. NLL là điểm phạt dự báo; thấp hơn tốt hơn, không phải phần trăm chính xác hoặc điểm học tập.

Không dùng thanh kéo ngưỡng để tìm mức tạo ra con số đẹp trong lúc báo cáo. Thanh đó là thăm dò ngưỡng chung, khác quy tắc đã khóa ở bảng phía trên.

## 6:10–7:00 — Kết thúc đúng phạm vi

“App thực thi được luồng làm bài và tái hiện được dự báo của nghiên cứu. Các kết quả ủng hộ giá trị dự báo nhỏ của việc cập nhật lịch sử nộp bài, đồng thời cho thấy có những trường hợp cập nhật kém đi. Em chưa chứng minh người học dùng app sẽ học tốt hơn, hoặc chính sách gợi ý chọn được bài tốt nhất. Để kết luận những điều đó cần một đánh giá giáo dục riêng.”

Nếu được hỏi tại sao cố ý trình bày ví dụ dự báo kém: “Vì kết quả trung bình không có nghĩa mọi trường hợp đều cải thiện. Em muốn chỉ rõ hệ thống làm được gì và còn hạn chế gì.”

## Nhánh demo bổ sung: quy tắc gợi ý bài tiếp theo

Chỉ dùng khi có thời gian hoặc thầy hỏi về khả năng thích ứng. Chuẩn bị **hai phiên duyệt mới độc lập**, không có bài đã hoàn thành. Nếu dùng chế độ riêng tư, kết thúc toàn bộ phiên thứ nhất trước khi bắt đầu phiên thứ hai; không coi hai tab trong cùng phiên là hai bộ tiến độ riêng.

| Tình huống | Thao tác trên bài Chỉ cộng số dương | Bài tiếp theo khi tiến độ còn mới |
|---|---|---|
| Giải nhanh | Qua test trong 1–2 lần chạy, không mở gợi ý | **Tổng các số chẵn** |
| Cần củng cố | Mở một gợi ý trước khi qua test, hoặc có tổng cộng ít nhất 3 lần kiểm tra rồi mới qua | **Đếm số dương** |

Nói rõ: “Đây là quy tắc thiết kế để minh họa luồng thích ứng. Nó chưa được học từ mô hình nghiên cứu và chưa được kiểm chứng là nâng kết quả học tập.” Nếu các bài ưu tiên đã hoàn thành, app chuyển sang một bài chưa hoàn thành khác; lịch sử cũ có thể làm tên bài khác bảng này.

## Nhánh demo bổ sung: thay đầu vào, giữ mô hình

Trong hồ sơ đã chọn, mở **So sánh mô hình và xuất số liệu → Thử sửa chuỗi này**. Đổi một kết quả đầu vào, bấm chạy suy luận, quan sát xác suất thay đổi, rồi khôi phục.

Nói: “Đây là phản ứng tính toán của mô hình với một chuỗi giả định. Chuỗi mới không có kết quả tương lai thực tế để đối chiếu. Em không diễn giải nó thành bằng chứng sửa như thế sẽ khiến người học giỏi hơn.”

## Đối chiếu

- `app/test_outputs/demo_case_verification.json`: bốn hồ sơ, toàn bộ chuỗi xác suất, phán quyết bài đích và kết quả đối chiếu dự báo gốc.
- `app/test_outputs/demo_practice_verification.json`: mã sai/đúng và các test đếm số dương. Kiểm tra trực tiếp bằng cùng bộ chấm Python; các luồng trình duyệt đã có biên bản riêng trong `VALIDATION.md`.
- `app/HUONG_DAN_THUYET_TRINH.md`: phần giải thích khái niệm và câu trả lời khi thầy hỏi.

Tài liệu này không thay đổi mô hình, dữ liệu, ngưỡng, số liệu nghiên cứu hoặc tiến độ trên trình duyệt của bạn.
