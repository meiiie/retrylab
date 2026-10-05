# Hiểu và thuyết trình RetryLab

Đối chiếu với mã nguồn, kết quả nghiên cứu và hồ sơ R00001 của máy chủ ngày 26/09/2026. Đây là tài liệu giải thích, không bổ sung một thí nghiệm mới.

## 1. Một câu cần nhớ

**Quan sát thêm những lần sinh viên sửa bài có giúp AI dự báo kết quả lần nộp đầu tiên của bài tiếp theo tốt hơn không?**

“Kết quả” ở đây là chương trình được hệ thống chấm chấp nhận hay chưa. Một lần không được chấp nhận có thể do sai kết quả, lỗi chạy, quá thời gian… nên không được tự suy ra rằng sinh viên không hiểu kiến thức.

## 2. Câu chuyện đơn giản

An đang làm bài A. An nộp một lần, nhận kết quả, sửa và nộp tiếp.

Ta cho một người dự đoán quan sát hai lần:

1. Sau lần nộp đầu của A, người đó đoán An có vượt qua bài B ngay lần nộp đầu không. Gọi đây là H0.
2. Sau khi xem thêm các lần nộp lại của A, người đó đoán lại **vẫn chính bài B ấy**. Gọi đây là H1.
3. Mở kết quả thật của B để chấm hai dự đoán.
4. Làm tương tự trên nhiều hồ sơ, rồi xem dự đoán trước hay sau nhận ít điểm phạt hơn.

Mô hình vẫn giữ nguyên trọng số; lịch sử đầu vào được bổ sung. Trong nghiên cứu, bài B được lấy từ lịch sử đã xảy ra và được cung cấp cho cả H0/H1. Hệ thống chưa chọn B như một quyết định khuyến nghị đã được kiểm chứng. H0/H1 là tên hai mốc quan sát trong nghiên cứu này.

Tại sao giữ nguyên B? Nếu đoán bài dễ ở lần đầu và bài khó ở lần sau, ta không biết thay đổi đến từ thông tin mới hay do đổi bài.

## 3. AI thực sự làm gì?

Mô hình học từ log công khai của những người học thuộc tập huấn luyện. Đầu vào gồm lịch sử bài và các kết quả nộp; nhóm logistic dùng các đặc trưng lịch sử, nhóm GRU xử lý chuỗi sự kiện. Mô hình trả một xác suất được chấp nhận ở lần nộp đầu của bài đích.

Mô hình không đọc hiểu đoạn Python bạn vừa viết trong khu Luyện tập. Nghiên cứu ACcoding không có mã nguồn để làm việc đó. App hiện có hai luồng riêng:

| Phần | Hoạt động thực tế | Bằng chứng tạo ra |
|---|---|---|
| Luyện tập | Chạy mã Python thật trên 8 test mỗi bài, phản hồi lỗi, lưu nháp và chọn bài bằng quy tắc | Luồng làm bài và bộ kiểm tra thực thi được |
| Nghiên cứu | Nạp mô hình đã huấn luyện, dự báo từ log cũ, đối chiếu kết quả đã xảy ra | Khả năng dự báo và tái hiện phép đo nghiên cứu |

Hai phần chưa được nối thành một gia sư AI đã được đánh giá. Nhật ký bạn vừa làm không tự nhập vào số liệu 69.825 cặp. Gợi ý trong khu Luyện tập ưu tiên bài củng cố khi có từ ba lần thử hoặc đã mở gợi ý; đó là quy tắc viết sẵn.

## 4. Đã đo được gì?

Thử nghiệm xác nhận dùng 69.825 cặp dự báo của 1.500 người học khác nhóm pilot. Một người có thể đóng góp nhiều cặp; 69.825 không phải số sinh viên. Đây là log đã tồn tại, không phải 1.500 người vừa dùng app mới.

Mô hình và các lựa chọn đánh giá được khóa trước khi xem kết quả nhóm xác nhận. Hai dự báo của từng cặp hướng đến cùng một kết quả thật. Khoảng bất định được ước lượng bằng cách lấy mẫu lại theo người học, giữ các cặp của cùng người đi cùng nhau.

Kết quả chính với Logistic FIRST: điểm phạt dự báo NLL giảm từ **0,581115 xuống 0,579549**; chênh lệch **−0,001566**, CI95% **[−0,002300; −0,000756]**. Đây là bằng chứng về lợi ích dự báo nhỏ trong điều kiện đã khảo sát. Không gọi là tỷ lệ chính xác tăng 0,1566%.

Một kết quả ứng dụng thứ cấp với GRU FIRST, dùng quy tắc khoảng 30% hồ sơ trên tập validation:

- Trong các trường hợp thực tế thất bại, tỷ lệ phát hiện được tăng **44,58% → 45,27%**.
- Trong toàn bộ hồ sơ, tỷ lệ đưa vào nhóm cần xem xét tăng **30,71% → 30,81%**.
- Chênh lệch recall theo số chưa làm tròn là **+0,694 điểm phần trăm**, CI95% **[0,336; 1,057]**.

Đây là mức tăng nhỏ và phải đọc cùng chi phí xem xét. Kết quả là phân tích thứ cấp, khoảng danh nghĩa chưa chỉnh cho nhiều so sánh. Không suy ra mọi mô hình hoặc mọi cách đặt ngưỡng đều được cải thiện. Mức giảm loss của GRU lớn hơn không chứng minh GRU tốt hơn logistic; không có kết luận đánh bại SOTA ở đây.

## 5. Cách đọc màn hình Bằng chứng

| Nhãn trên màn hình | Câu giải thích ngắn |
|---|---|
| Phát hiện thất bại | Trong những trường hợp thật sự thất bại, hệ thống đánh dấu trước được bao nhiêu phần? |
| Hồ sơ cần xem xét | Trong tất cả hồ sơ, bao nhiêu phần bị đưa vào danh sách cần xem xét? |
| Thất bại trong nhóm đánh dấu | Trong các hồ sơ bị đánh dấu, bao nhiêu phần sau đó thực sự thất bại? |
| Sai số dự báo · NLL | Điểm phạt cho dự báo; đoán sai mà quá tự tin bị phạt nặng. Nhỏ hơn là tốt hơn. Đây không phải phần trăm. |
| Δ | Giá trị sau trừ giá trị trước. Tăng recall thường tốt; giảm NLL thường tốt; workload thể hiện chi phí. |
| CI95% | Khoảng thể hiện bất định của ước lượng chênh lệch theo phép lấy mẫu lại đã dùng. Không phải khoảng điểm hoặc năng lực của một sinh viên. |

Vì sao hai tỷ lệ đầu khác nhau? Chúng có mẫu số khác nhau: một tỷ lệ tính trên nhóm thất bại, một tỷ lệ tính trên tất cả hồ sơ.

Nếu quy recall về 1.000 trường hợp thật sự thất bại, 44,58% và 45,27% tương đương khoảng 446 và 453 trường hợp được nhận ra. Đây chỉ là quy đổi minh họa tỷ lệ, không phải quy mô mẫu thực của thí nghiệm.

Đồ thị NLL: phía âm biểu thị lỗi giảm; khoảng cắt qua 0 cho thấy phép ước lượng còn bao gồm cả hai hướng. Đồ thị hiệu chỉnh: nếu dự báo nguy cơ 30% cho nhiều hồ sơ tương tự, ta muốn tỷ lệ thất bại quan sát của nhóm ấy gần 30%.

Thanh kéo ngưỡng bên dưới là thăm dò một ngưỡng chung. Nó khác các ngưỡng H0/H1 đã khóa trên validation của bảng phía trên. Khi thuyết trình lần đầu, giữ thanh kéo mặc định và không dùng nó để tìm một con số đẹp.

## 6. Kịch bản trình bày 5 phút

### 0:00–0:40 — Nêu câu hỏi

“Một sinh viên có thể sửa nhiều lần để qua một bài. Em muốn biết các lần sửa đó giúp hệ thống dự báo bài tiếp theo tốt hơn đến đâu. Em cho mô hình đoán trước và sau khi nhận thêm lịch sử, rồi đối chiếu cùng một kết quả thật.”

### 0:40–1:20 — Minh họa người học

Mở Luyện tập → Chỉ cộng số dương. Chạy khung hàm có `return 0` để thấy một trường hợp sai, sau đó sửa và chạy lại. Chỉ thao tác trên bản nháp dùng cho trình bày; không cần xóa tiến độ đã có.

“Đây là giao diện thực hành. Bộ kiểm tra chạy Python thật và chỉ ra đầu vào gây sai. Việc vượt các test chứng minh chương trình xử lý được các trường hợp đó. Phần chọn bài tiếp hiện dùng quy tắc, chưa dùng mô hình nghiên cứu để đánh giá người đang ngồi trước app.”

### 1:20–2:40 — Minh họa AI nghiên cứu

1. Mở **Nghiên cứu → Xem một trường hợp** (hoặc `/#replay`).
2. Mở **Đổi hồ sơ hoặc tìm một trường hợp khác**, tìm và chọn **R00001**. Chọn **GRU · lần nộp đầu**.
3. Đặt thanh quan sát về lần 1 nếu cần. Xác suất được chấp nhận ở bài #9954 là khoảng **33,4%**.
4. Bấm **Xem sau các lần sửa**. Sau sáu lần nộp của bài #9927, dự báo cho cùng bài #9954 còn khoảng **29,6%**.
5. Bấm **Mở kết quả thực tế**. Lần nộp đầu bài #9954 nhận **TLE**, tức quá thời gian và chưa được chấp nhận.

“Trong hồ sơ này, lần nộp cuối của bài đang làm đã được chấp nhận, nhưng bài tiếp theo vẫn chưa qua ngay lần đầu. Mô hình hạ dự báo xác suất thành công; cập nhật đó phù hợp hơn với kết quả quan sát. Vì thế, đường xác suất tăng không phải tiêu chí duy nhất để nói mô hình tốt hơn.”

Đây là hồ sơ đầu trong thứ tự cố định, không phải bằng chứng toàn tập. Không kết luận hiệu quả chung từ một trường hợp.

### 2:40–4:10 — Chỉ vào bằng chứng toàn tập

Bấm **Xem kết quả toàn tập**. Chọn **GRU · lần nộp đầu** và **Khoảng 30% hồ sơ trên validation**. Giải thích hai tỷ lệ đầu: 44,58% → 45,27% phát hiện thất bại; 30,71% → 30,81% hồ sơ cần xem xét. Nói rõ lợi ích nhỏ.

Nếu cần trình bày phép đo chính của bài báo, chuyển sang **Logistic · lần nộp đầu** và chỉ thẻ NLL: 0,5811 → 0,5795. Nhắc đây là điểm phạt dự báo, không phải điểm học tập.

“Một hồ sơ giúp nhìn thấy cách hệ thống vận hành. Kết luận được dựa trên nhiều hồ sơ và khoảng bất định. Quy tắc đánh dấu đã chọn trên tập validation trước khi chấm nhóm xác nhận.”

### 4:10–5:00 — Kết luận đúng phạm vi

“Kết quả ủng hộ rằng các lần nộp lại có thêm thông tin dự báo, với lợi ích nhỏ trong dữ liệu và mô hình đã khảo sát. App tái hiện được dự báo và cung cấp một luồng luyện tập có thể chạy. Hiện chưa có thí nghiệm cho thấy người học dùng app sẽ học tốt hơn hoặc bài gợi ý là bài tốt nhất. Đây là hệ thống thực nghiệm và nghiên cứu dự báo; phần đánh giá tác dụng giáo dục còn là bước tiếp theo.”

## 7. Các câu hỏi dễ bị hỏi

**AI ở đâu?** Ở các mô hình logistic và GRU đã học từ log, suy luận trong khu Nghiên cứu. Bộ test Python là chương trình kiểm tra kết quả; gợi ý bài trong khu Luyện tập hiện là quy tắc.

**Sao làm đúng một bài chưa đủ chứng minh đã học được?** Người học có thể nhớ hoặc sao chép lời giải. Cần thêm đánh giá độc lập để biết có tự giải được bài mới hay không. Dán lời giải có sẵn và qua 8 test chỉ chứng minh mã đó qua bộ kiểm tra.

**Vậy đóng góp nghiên cứu là gì?** Đo giá trị thông tin của các lần nộp lại khi giữ cùng mục tiêu dự báo, kiểm tra ảnh hưởng của cách đặt nhiệm vụ huấn luyện và đo lợi ích/cost của một quy tắc sàng lọc hồi cứu. Không tuyên bố đây là mô hình kiến trúc mới.

**69.825 người đã dùng app?** Không. Đó là 69.825 cặp dự báo trên log của 1.500 người học; một người đóng góp nhiều cặp. App được xây sau thí nghiệm.

**Qua 64 test có chứng minh AI dạy tốt?** Không. 64 là số trường hợp kiểm tra phần mềm cho tám lời giải tham chiếu. Đây không phải số người tham gia hoặc số phép đo learning gain.

**Có chứng minh hệ thống chọn bài tốt nhất?** Chưa. Bài đích của nghiên cứu là bài quan sát được trong lịch sử. Không có kết quả cho mọi bài khác mà cùng người học có thể được giao ở thời điểm đó.

**Chưa có sinh viên thật thử thì thuyết trình thế nào?** Gọi đúng là đánh giá hồi cứu trên log công khai và kiểm tra vận hành phần mềm. Báo kết quả, bất định và giới hạn. Không đặt tên cho nó là thử nghiệm can thiệp hoặc thành công giáo dục đã được xác nhận.

**Đã đạt Q1 hoặc SOTA chưa?** Chưa có cơ sở tuyên bố. Mức mới, độ mạnh của phát hiện và khả năng công bố cần được đánh giá riêng; giao diện và số lượng bài thử không quyết định thứ hạng công bố.

## Nguồn để đối chiếu

- `research/confirmation/RESULTS.md`: phép đo chính, mô hình logistic và khoảng bootstrap.
- `research/sequential/validation_converged/final_results.md`: mô hình GRU đã khóa và kết quả.
- `research/application/results_table.md`: toàn bộ các đánh đổi sàng lọc, không chỉ một kết quả tích cực.
- `paper/BAO_CAO_NGHIEN_CUU.md`: đóng góp, giới hạn và mức sẵn sàng công bố.
- `app/README.md`, `app/VALIDATION.md`, `app/static/js/curriculum.js`: cách dùng, kiểm tra app và quy tắc chọn bài.
- Hồ sơ minh họa được đối chiếu tại `/api/cases/R00001` và `/api/cases/R00001/outcome`; việc đọc endpoint không thay đổi trạng thái trình bày trên giao diện của người dùng.
