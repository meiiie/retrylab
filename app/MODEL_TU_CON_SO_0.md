# Từ mô hình đến huấn luyện, đánh giá và ứng dụng

Tài liệu này giải thích mô hình dự báo lịch sử ACcoding. Learner filter và policy của luồng 12 bài Python mới được giải thích riêng trong `../paper/DE_4_BAO_CAO_VA_DEMO.md` và `../research/catalog_policy/README.md`.

Tài liệu giải thích hệ thống đã triển khai, đối chiếu trực tiếp `research/confirmation/confirmatory_study.py`, `research/confirmation/METHODS.md`, `research/sequential/run_gru.py`, `research/sequential/README.md` và các artifact cuối trong `research/sequential/validation_converged/`. Không thay đổi hoặc huấn luyện lại mô hình.

## 1. Model là gì?

Model là một cách tính có các con số bên trong được học từ dữ liệu. Những con số đó gọi là tham số hoặc trọng số. Sau huấn luyện, ta giữ chúng lại để tính dự báo cho đầu vào mới.

Trong dự án này, đầu vào là lịch sử các lần nộp bài và mã bài cần dự báo. Đầu ra là xác suất chương trình được hệ thống chấm chấp nhận. Trong phép đánh giá chính, đích là lần nộp đầu tiên quan sát được của bài tiếp theo.

Ví dụ minh họa: sau khi thấy một người nộp bài A chưa qua, sửa rồi qua, mô hình được hỏi về bài B và có thể trả về 0,60. Nghĩa là mô hình ước lượng cơ hội lần nộp đó được chấp nhận là 60%. Con số này không phải điểm học tập, phần trăm kiến thức, độ chính xác tổng thể của mô hình hoặc lời bảo đảm chắc chắn.

## 2. Dữ liệu dùng để học

Nhánh mô hình trong app dùng log ACcoding công khai. Mỗi bản ghi cho biết người học, mã bài, thứ tự/thời điểm và phán quyết của một lần nộp. Phán quyết AC được chuyển thành nhãn 1; các kết quả đã có phán quyết khác AC thành 0. Bản ghi đang đợi/đang chấm bị loại. Mã người học dùng để gom đúng lịch sử và chia tập; không có embedding danh tính người học trong GRU này.

Các nhóm cuối đã dùng:

| Vai trò | Người học | Dùng làm gì? |
|---|---:|---|
| Train | 1.054 | Học trọng số từ 295.788 lần nộp; có 2.624 mã bài trong từ vựng |
| Validation | 212 | Chọn checkpoint GRU, mức cập nhật logistic và quy tắc sàng lọc |
| Exploratory test cũ | 234 | Đã được xem trong thăm dò; không dùng lại như bằng chứng xác nhận nguyên vẹn |
| Confirmation mới | 1.500 người khác toàn bộ pilot | Đánh giá sau khi khóa mô hình; 420.076 lần nộp, tạo 69.825 cặp đủ điều kiện |

Train/validation/exploratory thuộc nhóm pilot 1.500 người. Confirmation là 1.500 người khác. Số người validation đóng góp cặp H0/H1 là 211, tạo 10.734 cặp; điều đó không mâu thuẫn với 212 người được chia vào validation ban đầu.

Đầu vào không phải toàn văn sách, bài báo hoặc lời giải Python của người đang demo. Bài báo nghiên cứu giúp chọn phương pháp; log nộp bài cung cấp mẫu để học trọng số. Nhánh ACcoding không dùng mã nguồn hay văn bản đề bài để suy luận.

## 3. Hai họ mô hình

### Hồi quy logistic: nhìn bản tóm tắt

Trước mỗi dự báo, lịch sử được tóm thành bảy đặc trưng:

1. Ước lượng độ khó bài đích dưới dạng logit, học từ dữ liệu train.
2. Số lượt đã quan sát, biến đổi log1p.
3. Tỷ lệ được chấp nhận trong lịch sử, có làm trơn.
4. Kết quả lần nộp gần nhất.
5. Tỷ lệ được chấp nhận ở tối đa năm lượt gần nhất.
6. Tỷ lệ được chấp nhận ở tối đa hai mươi lượt gần nhất.
7. Số bài khác nhau đã quan sát, biến đổi log1p.

StandardScaler đưa các đặc trưng về thang đo thuận tiện cho việc fit. Mô hình học một trọng số cho mỗi đặc trưng và một số bù. Tổng có trọng số được đưa qua sigmoid để thành xác suất từ 0 đến 1. Đây là cách tính được học từ dữ liệu, không phải người lập trình tự viết luật rằng “sai ba lần thì chắc chắn yếu”.

Cấu hình thật: scikit-learn, L2 regularization, C=1, max_iter=500, random_state=26092026. Độ khó dùng train; đặc trưng độ khó cho các hàng train dùng student-fold crossfitting để hạn chế tự dùng nhãn của người đó vào đặc trưng.

Ba bản logistic:

- **ALL:** fit trên mọi lần nộp đủ điều kiện trong train, 295.788 hàng.
- **FIRST:** chỉ các lần đầu quan sát ở một bài của từng người tạo mục tiêu loss, 127.005 hàng. Đây là predictor chính của phép xác nhận.
- **PAIRED:** đưa cả H0 và H1 của một cặp vào train, cùng nhãn bài tương lai, thêm chỉ báo phase. Có 49.019 cặp thành 98.038 hàng, mỗi phase trọng số 0,5. Đây là đối chứng giúp kiểm tra ảnh hưởng của cách đặt nhiệm vụ dự báo.

### GRU: đọc chuỗi và giữ một tờ ghi nhớ

Thay vì nhận một bản tóm tắt bảy số, GRU đọc từng sự kiện “mã bài + kết quả”. Một sự kiện đi vào thì tờ ghi nhớ được cập nhật. Khi cần đoán một lần nộp, mô hình dùng tờ ghi nhớ **trước khi xem kết quả của lần nộp đó** và mã bài đang hỏi.

Các thành phần thật:

| Thành phần | Kích thước/cấu hình | Cách hiểu |
|---|---|---|
| Event embedding | 48 số | Biểu diễn học được cho một cặp mã bài/kết quả |
| GRU một chiều, một tầng | Trạng thái 64 số | Cập nhật thông tin tóm tắt chuỗi; không phải 64 kỹ năng có tên |
| Query embedding | 48 số | Biểu diễn học được cho mã bài cần dự báo |
| Decoder | Ghép 64+48=112 số, Linear 112→64, Tanh, Linear 64→1 | Tính mức dự báo từ lịch sử và bài đích |
| Sigmoid | Một xác suất 0–1 | Đưa mức dự báo thành xác suất được chấp nhận |

GRU ở đây có **407.233 tham số** và được khởi tạo, huấn luyện từ đầu. Cách diễn giải “tờ ghi nhớ” là phép ví von cho trạng thái số; chưa có bằng chứng trạng thái đó là phép đo kiến thức thật. Mã bài chưa biết ở train được biểu diễn bằng vector 0 trong bản cuối. Đây là GRU tùy biến có điều kiện theo bài, không phải bản tái lập nguyên xi DKT hoặc mô hình ngôn ngữ sinh câu trả lời.

## 4. Train nghĩa là gì?

Một vòng tập gồm:

1. Đưa lịch sử và mã bài vào mô hình, che kết quả cần đoán.
2. Mô hình tạo xác suất dự báo.
3. Mở nhãn đã có trong dữ liệu train để chấm dự báo.
4. Tính loss: dự báo sai mà quá tự tin bị phạt nặng.
5. Tính cách thay trọng số để giảm loss và cập nhật chúng.
6. Lặp qua nhiều mẫu, nhiều lượt.

Đây là **học có giám sát**: các ví dụ để học đã có nhãn đúng. Loss là binary cross-entropy/log loss; số đo NLL dùng cùng ý tưởng chấm xác suất. Với GRU, backpropagation tính gradient và Adam dùng gradient để chỉnh trọng số. Logistic được thư viện tối ưu bằng solver của nó, không dùng vòng Adam của GRU.

Ví dụ giả định trong hình tương tác dùng một phép logistic chỉ có một tham số để giải thích thao tác cập nhật. Nó không tái hiện một bước huấn luyện thật của mạng GRU 407.233 tham số. Khi nhãn thật là 0, giảm xác suất 0,70 xuống khoảng 0,622 làm điểm phạt của mẫu này giảm từ khoảng 1,204 xuống 0,972. Cải thiện một mẫu không chứng minh khái quát sang mẫu khác.

### Các tham số huấn luyện GRU thật

- PyTorch; môi trường ghi nhận chạy CPU, hai luồng CPU, không phải đã thuê GPU Kaggle.
- Adam learning rate 0,001; gradient clipping với ngưỡng norm 5.
- Mỗi batch tối đa 32 người học, ghép theo độ dài chuỗi.
- Chia tính toán thành cửa sổ 128 sự kiện; trạng thái được mang sang cửa sổ sau, còn gradient bị ngắt tại biên. Không xóa lịch sử chỉ vì quá 128 lượt.
- Tối đa 30 epoch; một epoch là một lượt qua tập train. Kiểm tra validation sau mỗi epoch.
- Dừng sớm khi bốn epoch không cải thiện validation đủ 0,0001; giữ checkpoint có validation first-attempt NLL thấp nhất quan sát được.
- Ba lần khởi tạo: seed 11, 29, 47. Mỗi mode ALL/FIRST có ba mạng riêng. Các ensemble lấy trung bình ba xác suất, không chỉ chọn seed đẹp nhất.
- Không dropout, không class weighting, Adam weight decay bằng 0 trong bản này.

Ví dụ thật: GRU FIRST seed 11 được giữ ở epoch 8 và dừng sau epoch 12. Toàn bộ checkpoint cuối được lưu ở `research/sequential/validation_converged/`; các bản thăm dò năm epoch trước đó không được dùng thay cho bản cuối.

**ALL và FIRST khác ở mục tiêu bị chấm lỗi lúc train. Cả hai GRU vẫn đọc mọi sự kiện lịch sử trước đó.** FIRST không có nghĩa bỏ các lần nộp lại khỏi trí nhớ.

## 5. Vì sao app có năm tên mô hình?

Ba bản logistic + hai ensemble GRU = năm cấu hình hiển thị. Hai ensemble tương ứng sáu checkpoint GRU thật, vì mỗi ensemble là trung bình của ba seed. Năm lựa chọn không phải năm thuật toán mới do dự án phát minh.

Phần nghiên cứu chính của dự án là kiểm tra giá trị của thông tin nộp lại và cách đặt mục tiêu dự báo. GRU là kiểm tra bổ sung bằng một họ mô hình khác, không tự động là mô hình tốt nhất chỉ vì là mạng nơ-ron.

## 6. Train khác dùng mô hình như thế nào?

| Train | Khi dùng trong app |
|---|---|
| Đọc ví dụ, đoán, mở nhãn, tính loss, thay trọng số | Nạp trọng số đã lưu, đọc lịch sử, tính dự báo |
| Có vòng tối ưu | Không fit lại khi bấm nút |
| Được dùng nhãn train sau khi dự báo để tính loss | Kết quả bài đích không được đưa vào đầu vào dự báo |

Khi thêm một lần nộp vào lịch sử, GRU có thể có trạng thái mới và logistic có đặc trưng mới; xác suất vì thế thay đổi. **Trọng số vẫn giữ nguyên.** Phân biệt “cập nhật thông tin về lịch sử đang xem” với “huấn luyện lại cách tính của mô hình”.

## 7. Kiểm tra khoa học đang hỏi điều gì?

Sau khi train xong, khóa mô hình. Với mỗi chuỗi sửa bài A, dự báo **cùng kết quả lần nộp đầu của bài B** tại hai mốc:

- **H0:** biết lịch sử đến sau lần nộp đầu của A.
- **H1:** biết thêm các lần nộp lại của A đến cuối chuỗi.

Danh tính B được lấy hồi cứu từ log và cung cấp cho cả hai dự báo. Mô hình không được xem nhãn B khi suy luận. Giữ cùng B giúp không lẫn “thêm thông tin” với “đổi độ khó vì đổi bài”.

Đối chiếu cả hai xác suất với cùng nhãn thật, tính NLL/Brier rồi tổng hợp. Dự báo tăng hay giảm chưa tự nói tốt/xấu: nếu kết quả là chưa qua, xác suất thành công thấp hơn có thể phù hợp hơn. Các phép lấy mẫu lại theo người học giữ phụ thuộc giữa nhiều hồ sơ của cùng một người.

Kết quả chính Logistic FIRST: NLL H0 0,581115 → H1 0,579549; Δ −0,001566, CI95% [−0,002300; −0,000756]. Đây là cải thiện dự báo nhỏ trên quần thể/điều kiện đã khảo sát. Nó không phải mức tăng điểm học tập hoặc tác động nhân quả của việc nộp lại.

Các mô hình chưa được chứng minh vượt SOTA, các khoảng thứ cấp chưa điều chỉnh nhiều so sánh, và đánh giá không đại diện sẵn cho mọi trường/lịch thời gian/người học mới.

## 8. Dùng dự báo để làm gì?

Một hướng ứng dụng đã được đo hồi cứu là đánh dấu hồ sơ có nguy cơ lần nộp đầu bài tiếp theo không được chấp nhận, để hình thành danh sách cần xem xét giả định. Nếu p là xác suất AC, nguy cơ non-AC là 1−p. Ngưỡng đánh dấu được chọn trên validation và giữ cố định khi chấm confirmation.

Ta đo được trong nhóm thất bại thật hệ thống nhận ra bao nhiêu, và phải đánh dấu bao nhiêu hồ sơ. Chưa có giáo viên thực sự hỗ trợ theo danh sách này trong thí nghiệm; không có kết quả về tác dụng của hỗ trợ, học tốt hơn hoặc chọn bài tối ưu.

## 9. Sau cùng mới đến app

Khu Nghiên cứu là giao diện điều khiển và quan sát mô hình đã train. Flask phục vụ API; `engine.py` nạp logistic và GRU, dựng đầu vào lịch sử, suy luận và kiểm tra với dự báo đã lưu. Giao diện hiển thị xác suất, cho mở kết quả thật và đọc các phép đo tổng hợp.

Khu Luyện tập là luồng riêng: tám bài Python tự biên soạn, thực thi bằng Pyodide trong trình duyệt, chấm bằng test, lưu nháp và gợi ý bài theo quy tắc. Các tên hàm `tong_so_duong` hoặc `dem_so_duong` không đi vào GRU để mô hình đọc hiểu code. Hai phần chưa được nối thành một gia sư AI thích ứng đã được đánh giá.

Muốn nối nghiên cứu với người đang làm các bài Python mới, cần dữ liệu và mô hình phù hợp với chính ngân hàng bài đó, rồi đánh giá chính sách hỗ trợ/chọn bài. Không thể mặc nhiên dùng embedding của mã bài ACcoding cho những bài mới không có trong train.

## 10. Một đoạn có thể dùng khi thuyết trình

“Hệ thống của em dùng học có giám sát để dự báo khả năng một lần nộp bài được chấp nhận từ lịch sử nộp bài và mã bài đích. Em dùng hồi quy logistic trên đặc trưng lịch sử và GRU xử lý chuỗi. Mô hình học trên train, lựa chọn trên validation và được khóa trước khi đánh giá trên nhóm người học khác. Thí nghiệm so sánh hai dự báo cho cùng bài tiếp theo: trước và sau khi quan sát thêm các lần nộp lại. App giúp xem và kiểm chứng những dự báo đó; khu luyện Python hiện là một luồng thực hành riêng.”

## Các vị trí mã nguồn quan trọng

- `research/confirmation/confirmatory_study.py`: tạo đặc trưng, fit ba logistic, khóa và đánh giá.
- `research/confirmation/METHODS.md`: định nghĩa estimand, chia nhóm, phép đo và giới hạn.
- `research/sequential/run_gru.py`: lớp `QueryGRU`, hàm `fit`, validation và đánh giá.
- `research/sequential/README.md`: kiến trúc, train và cách diễn giải.
- `research/sequential/validation_converged/summary.json`: môi trường thật và số lượng mẫu.
- `research/sequential/validation_converged/fit_FIRST_seed11.json`: log từng epoch minh họa.
- `app/engine.py`: suy luận bằng các checkpoint đã khóa.
- `app/static/js/curriculum.js`: bài Python và quy tắc gợi ý của phần luyện tập.
