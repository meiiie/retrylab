# Đề 4: đối chiếu yêu cầu gốc và hướng triển khai

Ngày rà soát: 26/09/2026. Đây là bản kiểm toán phạm vi và đặc tả công việc cần làm tiếp; những phần ghi “cần làm” chưa được triển khai hoặc thực nghiệm trong lượt rà soát này.

## 1. Kết luận và quyết định đề xuất

Đề 4 yêu cầu một hệ thống **chọn bài tập lập trình tiếp theo cho từng người học**, dựa trên mô hình người học và học tăng cường. Công việc hiện có chủ yếu kiểm tra chất lượng dự báo kết quả của **một bài tiếp theo đã được chỉ định trong log**, kèm ứng dụng sàng lọc nguy cơ hồi cứu. Hai nhiệm vụ có liên hệ, nhưng không đồng nhất.

Nên giữ đề 4, đưa dự báo về đúng vai trò thành phần mô hình người học, rồi hoàn thiện chính sách chọn bài và phép đánh giá chính sách. Không cần bỏ dữ liệu, checkpoint hoặc thí nghiệm đã làm. Không được gọi phần hiện có là hệ khuyến nghị học tăng cường đã hoàn chỉnh.

## 2. Nguồn gốc đã kiểm tra

- PDF người dùng chỉ định: `E:/Downloads/Danh sách đề tài mon AAI.pdf`, 11 trang.
- SHA-256: `483430db87efd9221f1736f3dadb230e02b6cdb8cbfe13eff620a20f6c3aef5c`.
- Đã trích đọc toàn bộ tài liệu và kiểm tra ảnh đầy đủ trang 7–8. Có một bản tên Unicode khác trong Downloads, có cùng hash.
- Đúng mục cần theo: **Đề tài 4 trong phần “Dữ liệu thầy đã có”**, trang 7–8. Đề tài 4 ở phần đầu, trang 2, là định tuyến tàu biển và không phải lựa chọn của dự án.
- Theo đính chính trực tiếp của người dùng, **thầy không cung cấp dữ liệu**. Nhãn mục trong PDF không thay thế thông tin này.

Nguyên văn tiêu đề:

> ĐỀ TÀI 4: Hệ khuyến nghị bài tập lập trình cá nhân hóa (Adaptive Programming Recommendation) dựa trên mô hình hóa Cognitive State của sinh viên và Học tăng cường

Nguyên văn ý tưởng cốt lõi:

> Mỗi sinh viên có tốc độ học khác nhau. Nếu giao bài tập quá khó họ sẽ nản, quá dễ họ sẽ chán. Đề tài này xây dựng một tác tử thông minh (Intelligent Agent) tự động chọn bài tập tiếp theo có độ khó tối ưu bám sát "vùng phát triển gần nhất" của từng sinh viên.

Ba mục trong phần **“Phương pháp luận & Kỹ thuật đề xuất”**:

1. **Mô hình hóa nhận thức:** dùng các thuật toán như DKT hoặc cây định danh rút gọn dựa trên Entropy để chẩn đoán kỹ năng yếu/mạnh; ví dụ mảng động, con trỏ, vòng lặp.
2. **Khung quyết định tuần tự MDP:** trạng thái là mức hiểu kiến thức; hành động là đề xuất bài cụ thể; phần thưởng là mức cải thiện điểm số và thời gian giải bài.
3. **Học chính sách:** huấn luyện tác tử bằng Q-learning hoặc PPO.

Trang 8 có tên bài báo gợi ý về khuyến nghị lộ trình lập trình bằng mạng theo dõi tri thức và học tăng cường, cùng mô tả giá trị khoa học mong muốn. Đây là định hướng, không phải bằng chứng tính mới hoặc bảo đảm công bố.

Tài liệu ghi kỹ thuật **đề xuất**, không nói phải dùng đồng thời DKT, cây quyết định, Q-learning và PPO. Tuy nhiên, nếu giữ nguyên phạm vi và tên đề 4, không thể bỏ thành phần chọn bài và học chính sách rồi chỉ trình bày bộ dự báo. PDF không cung cấp rubric chấm điểm chi tiết, số bài tối thiểu, ngưỡng accuracy hoặc yêu cầu công bố Q1/Q2/A*.

## 3. Phần người dùng bổ sung

| Ràng buộc hoặc mong muốn | Hệ quả triển khai |
|---|---|
| Tự tìm toàn bộ dữ liệu | Kiểm toán nguồn, quyền sử dụng, schema và tính phù hợp trước khi chọn phương pháp |
| Không thử nghiệm trên sinh viên thật | Dùng log thật cho dự báo và mô phỏng được kiểm soát cho chính sách; giới hạn kết luận tương ứng |
| Có hướng nghiên cứu thực sự và bài báo | Phải có câu hỏi có thể bác bỏ, đối chứng, thực nghiệm và kiểm tra prior art; ghép mô hình không tự tạo tính mới |
| Có app để dùng và demo | Một luồng hoàn chỉnh: làm bài, nhận phản hồi, cập nhật hồ sơ, hệ thống chọn bài tiếp theo, lưu lý do |
| UX/UI rõ ràng, code sạch | Giao diện sinh viên tập trung vào hành động học; số liệu và phương pháp chi tiết ở khu nghiên cứu |
| Xem xét nghiên cứu đến 26/09/2026 | Ghi ngày, nguồn và phạm vi truy tìm; không coi một tìm kiếm có mục tiêu là đã bao phủ toàn bộ SOTA |

## 4. Hiện có gì, còn thiếu gì?

| Thành phần | Bằng chứng hiện có | Đánh giá so với đề 4 |
|---|---|---|
| Dữ liệu lịch sử lập trình | ACcoding và CodeBench đã tải, kiểm toán, có protocol và kết quả | Có nền tảng; các nguồn thiếu những trường khác nhau |
| Mô hình dự báo | Logistic và GRU học từ lịch sử để dự báo accepted/non-accepted | Đã có; là thành phần người học, chưa phải bộ chọn bài |
| Hồ sơ kỹ năng có tên | GRU có trạng thái ẩn; logistic có đặc trưng lịch sử | Chưa có bằng chứng cho phép gắn các chiều thành “vòng lặp”, “con trỏ” hoặc % thành thạo |
| Lựa chọn giữa nhiều bài khả dụng | Phép H0/H1 giữ cùng một bài đích lấy từ log | Chưa đánh giá lựa chọn bài thay thế |
| MDP/POMDP cho học tập | Có tài liệu thiết kế và toy model kiểm tra reward | Chưa có môi trường thực nghiệm đầy đủ gắn với hệ khuyến nghị trong app |
| Tác tử học chính sách | Toy model dùng quy hoạch động với động lực biết trước | Chưa có policy Q-learning/PPO đã huấn luyện và triển khai cho luồng học |
| App luyện tập | 8 bài Python tự biên soạn, chấm thật, lưu nhật ký | Có luồng luyện tập, nhưng chưa dùng model nghiên cứu để chọn bài |
| Gợi ý bài trong app | `recommendNext()` dùng `authored-rule-v1`: số lần thử và việc mở gợi ý | Đây là quy tắc lập trình sẵn, chưa phải policy học tăng cường |
| Đánh giá | Dự báo trên log, bootstrap theo người, sàng lọc nguy cơ hồi cứu | Có bằng chứng dự báo; chưa có bằng chứng chất lượng chọn bài hoặc hiệu quả học |

Các vị trí đã đối chiếu: `app/engine.py`, `app/static/js/curriculum.js:288`, `research/confirmation/confirmatory_study.py:98`, `research/sequential/run_gru.py:55`, `research/diagnostics/README.md`, `research/review/offline_application_evaluation.md`.

Thí nghiệm xác nhận chính có 69.825 cặp từ 1.500 người; logistic FIRST giảm NLL từ 0,581115 xuống 0,579549 sau khi quan sát thêm các lần nộp lại. Đây là kết quả nhỏ về dự báo. Nó không trả lời “giao bài nào tốt hơn?”. Toàn bộ kết quả cũ cần giữ nguyên phạm vi này.

## 5. Hệ thống đích phải có hai thành phần học được

### A. Mô hình người học

Nhận lịch sử có thứ tự, thông tin bài và phản hồi; tạo biểu diễn người học và dự báo có kiểm định. Với kỹ năng có tên, cần một ánh xạ bài–kỹ năng có căn cứ và một nhiệm vụ đánh giá tương ứng. DKT/GRU không tự cung cấp nhãn kỹ năng có thể giải thích.

Khi chưa có lịch sử, dùng prior và bài chẩn đoán phù hợp. Thiếu dữ liệu phải được thể hiện; không mặc định người mới yếu và không hiển thị độ chính xác cá nhân hóa chưa được kiểm chứng. Khi có bài mới ngoài train, cần cơ chế dùng nội dung/metadata đã được đánh giá hoặc fallback công khai; không ánh xạ tùy tiện mã bài.

### B. Chính sách chọn bài

Nhận trạng thái ước lượng, mục tiêu học, ngân hàng bài khả dụng và ràng buộc; trả về bài tiếp theo. Đầu ra là **một hành động**, thay vì chỉ là một xác suất.

Năng lực thật không quan sát trực tiếp. Cách hình thức hóa phù hợp là POMDP hoặc MDP trên biểu diễn lịch sử/belief, có nêu giả định. Việc đặt tên một vector là “state” không chứng minh nó chứa đầy đủ thông tin cần thiết.

| Yếu tố | Đặc tả đề xuất |
|---|---|
| Quan sát | Mã bài, kết quả chấm, chuỗi lần thử; thời gian, test, code hoặc hint chỉ dùng nếu nguồn có và thời điểm sẵn có được xác minh |
| Trạng thái cho policy | Biểu diễn lịch sử, bài đã gặp, thông tin còn thiếu và mục tiêu; không đồng nhất với năng lực thật |
| Hành động | Chọn một bài trong tập hợp đủ điều kiện; việc ôn lại phải là một lựa chọn được đặc tả riêng |
| Chuyển trạng thái | Người học làm bài, phát sinh quan sát; mô hình cập nhật biểu diễn bằng lịch sử mới |
| Mục tiêu | Tiến bộ trên bài đánh giá độc lập sau một ngân sách luyện tập; có thể tính chi phí thời gian khi dữ liệu cho phép |
| Giới hạn | Tiên quyết kỹ năng, bài đã làm, giới hạn lặp lại, ngân sách, và hỗ trợ dữ liệu cho bài ứng viên |

Không lấy mức tăng xác suất của chính một câu hỏi cố định làm bằng chứng trực tiếp rằng người học vừa học thêm. Không tối ưu “càng dễ qua càng tốt” rồi gọi đó là tối ưu học tập. Một ngưỡng xác suất như 70% là lựa chọn thiết kế cần kiểm tra, không phải định nghĩa đã được xác nhận của vùng phát triển gần nhất.

## 6. Dữ liệu và ngân hàng bài là điểm phải giải quyết trước

ACcoding hiện không có toàn văn đề, full code hoặc kết quả từng test. Vì vậy không thể lấy mã bài trong ACcoding rồi gắn tùy ý với 8 bài Python trong app. CodeBench có lịch sử code và thực thi, nhưng kiểm toán hiện chưa xác nhận đầy đủ đề bài, nhãn kỹ năng chuyên gia và propensity chọn bài.

Ngân hàng dùng để demo phải có đề, lời giải tham chiếu, test, kỹ năng, điều kiện tiên quyết và ID ổn định. Bộ model/policy phục vụ ngân hàng này phải được huấn luyện hoặc chuyển giao theo một cơ chế được kiểm tra trên chính các đầu vào tương thích.

Thứ tự lựa chọn:

1. Kiểm toán nguồn có ngân hàng bài và log đủ ghép nối; có nội dung/metadata sử dụng được cho việc học và demo. Đây là hướng ưu tiên.
2. Nếu demo dùng ngân hàng tự biên soạn, cần model dựa trên kỹ năng/nội dung có đánh giá chuyển giao, hoặc dùng môi trường mô phỏng minh bạch. Gắn nhãn nguồn dự báo và phạm vi chứng minh tương ứng.
3. Không tạo “dữ liệu sinh viên thật” bằng việc sinh chương trình giả, không coi vài lần người dùng thử app là tập huấn luyện đủ cho hiệu quả giáo dục.

## 7. Hướng nghiên cứu cần kiểm tra

Câu hỏi định hướng:

> Khi người học sửa và nộp lại nhiều lần, cách cập nhật mô hình người học ảnh hưởng thế nào đến chính sách chọn bài; chính sách có còn hữu ích khi mô hình người học dự báo sai hoặc nhầm thành công tại bài cũ với khả năng làm bài khác?

Đây là câu hỏi cần thực nghiệm, chưa phải “khe hở chưa ai làm”. Các nghiên cứu trước đã xét KT, repeated attempts và đánh giá policy qua nhiều student models. Không tuyên bố việc ghép KT + RL, tách sửa lỗi/hiểu biết hoặc dùng nhiều simulator là đóng góp đầu tiên.

Các giả thuyết có thể bác bỏ:

1. Cải thiện chất lượng dự báo không bảo đảm thứ hạng policy tốt hơn theo mục tiêu đánh giá độc lập.
2. Biểu diễn episode sửa bài khác nhau có thể làm thay đổi lựa chọn bài, nhưng tác động phụ thuộc cơ chế học và lỗi mô hình.
3. Một chính sách có cơ chế xử lý độ bất định hoặc hạn chế hành động thiếu hỗ trợ có thể bền hơn; cần so với calibration, aggregation và quy tắc đơn giản để biết phần mới có cần thiết không.

Các thí nghiệm cũ phục vụ điểm khởi đầu về dự báo. Chúng không xác nhận trước các giả thuyết về policy.

## 8. Thực nghiệm đúng với điều kiện không có sinh viên thật

### Tầng 1: dự báo trên log thật

Giữ kết quả cũ như bằng chứng đã có; nếu đổi nhiệm vụ hoặc mô hình, mở một protocol mới. Dùng các chỉ số xác suất như NLL/Brier/calibration, thêm AUC khi thích hợp. Chia người học và thời gian phù hợp với phát biểu; báo coverage và uncertainty.

Các tập test đã xem kết quả không được gọi lại là holdout nguyên vẹn cho giả thuyết mới. Nếu dùng lại để phát triển thì phải ghi là thăm dò, và tìm tập xác nhận mới trước khi đưa ra kết luận xác nhận.

### Tầng 2: học và đánh giá policy trong mô phỏng

- Huấn luyện policy thật từ dữ liệu/tương tác hữu hạn, có checkpoint và log. Khởi đầu bằng họ Q-learning phù hợp hành động rời rạc, như DQN; PPO là đối chứng hoặc phương án khác nếu thiết kế môi trường phù hợp. Không cần thêm thuật toán chỉ để có nhiều tên.
- So với chọn ngẫu nhiên có ràng buộc, lộ trình cố định, quy tắc kỹ năng yếu, quy tắc độ khó và phương pháp KT+RL gần nhất đã tái lập hoặc thích nghi có ghi rõ.
- Giữ cùng tập ứng viên, ngân sách và giao thức đánh giá. Không cho một phương pháp dùng metadata hoặc outcome tương lai mà đối chứng không có.
- Dùng các cơ chế riêng: chỉ sửa được bài hiện tại; học có khả năng chuyển sang bài khác; quên theo thời gian; phản hồi nhiễu. Giữ lại cả một họ/cơ chế môi trường khác cho đánh giá.
- Đo mục tiêu độc lập: bài kiểm tra/probe không được luyện trực tiếp, kỹ năng ẩn khi simulator cung cấp, regret khi oracle xác định được, chi phí thời gian và mức lặp bài. Metric trong simulator phải được ghi là mô phỏng.
- Báo nhiều seed và độ biến thiên do dữ liệu/fit. Đánh giá bằng môi trường độc lập với mô hình mà policy tối ưu; không chỉ cho policy tự chấm bằng cùng mô hình sinh reward.

Không lấy bài mà người học thực tế chọn trong log làm nhãn “bài tốt nhất”. Không coi NDCG bắt chước lựa chọn lịch sử hoặc AUC dự báo là bằng chứng learning gain. Đánh giá off-policy từ log cần kiểm toán giả định, tập hành động và support; dữ liệu hiện có chưa tự đáp ứng các điều kiện đó.

### Tầng 3: app chạy toàn bộ luồng

Kiểm chứng phần mềm bằng kịch bản người mới, qua ngay, sai nhiều lần, cần gợi ý, bỏ dở, quay lại bài cũ và bài ngoài phân phối. Yêu cầu kiểm tra:

1. Mỗi quan sát cập nhật đúng hồ sơ người đang học, không dùng kết quả tương lai.
2. Policy thực sự chấm các bài ứng viên và chọn bài đủ điều kiện; có thể truy lại model/policy version, tập ứng viên, điểm và lý do.
3. Đổi lịch sử có thể đổi quyết định khi hợp lý; không cưỡng bức hai lịch sử phải luôn chọn hai bài khác nhau.
4. Chấm code và dự báo là hai chức năng phân biệt rõ. Phần trăm dự báo không được hiển thị như điểm hay phần trăm kỹ năng thật.
5. Nếu thiếu dữ liệu hoặc bài nằm ngoài phạm vi model, app dùng fallback minh bạch và vẫn cho người dùng tiếp tục học.

Tầng 3 chứng minh hệ thống hoạt động. Tầng 1 chứng minh dự báo trong dữ liệu quan sát. Tầng 2 chứng minh giá trị policy trong những môi trường thử nghiệm. Chưa tầng nào tự chứng minh sinh viên thật học tốt hơn nhờ hệ thống.

## 9. Ví dụ Fibonacci cho bản hoàn chỉnh

Đây là hành vi mong muốn, không phải tính năng đã có của RetryLab.

1. Người mới làm một số bài khởi đầu để có thông tin; nếu chưa đủ thì hồ sơ ghi rõ chưa đủ dữ liệu.
2. Làm Fibonacci; hệ thống ghi kết quả và quá trình, không chỉ kết quả cuối.
3. Từ nhiều bằng chứng, mô hình ước lượng những kỹ năng cần củng cố. Một lần sai Fibonacci không tự chứng minh yếu đệ quy: bài có thể giải bằng vòng lặp, đệ quy hoặc cách khác.
4. Policy chọn giữa bài củng cố, bài vận dụng khác và bài ôn lại theo mục tiêu, tiên quyết và ngân sách. App giải thích ngắn gọn dựa trên thông tin thật đã dùng.
5. Sau chuỗi luyện tập, dùng bài khác để đánh giá khả năng vận dụng. Nếu quay lại Fibonacci, ghi đây là ôn lại; không trộn kết quả với nhãn lần đầu gặp bài.

## 10. Thứ tự làm tiếp và tiêu chí hoàn thành

| Mốc | Sản phẩm cần có | Điều kiện được coi là xong |
|---|---|---|
| 1. Chốt bài toán và nguồn | Đặc tả mục tiêu học, schema, ngân hàng bài, ánh xạ ID/kỹ năng | Nêu được dữ liệu nào có thật và đủ để nối model với app |
| 2. Mô hình người học | Model, protocol, calibration và xử lý thiếu lịch sử | Chấm trên đúng nhiệm vụ, tách test, không gắn nhãn năng lực vô căn cứ |
| 3. Môi trường và reward | Đặc tả state/action/transition/objective; các họ simulator | Phân biệt học thật trong mô phỏng với chỉ sửa/nhớ bài, có evaluator độc lập |
| 4. Chính sách | Baselines và policy RL được train, checkpoints, seeds | Chọn được bài hợp lệ và so sánh công bằng theo mục tiêu đã khóa |
| 5. Tích hợp app | Một luồng làm bài–cập nhật–chọn bài, trace quyết định | Model/policy tương thích ngân hàng bài; demo các trường hợp thật rõ |
| 6. Báo cáo/bài báo | Kết quả, ablation, uncertainty, giới hạn và tái lập | Phát biểu đúng cấp bằng chứng; không dùng kỳ vọng làm kết quả |

Tên làm việc đề xuất:

> Hệ khuyến nghị bài tập lập trình cá nhân hóa dựa trên lịch sử sửa bài và học tăng cường: đánh giá độ tin cậy của quyết định trong điều kiện dữ liệu hạn chế.

Tên này mô tả mục tiêu tiếp theo, không đổi tên kết quả đã hoàn tất thành nghiên cứu RL. Bản thảo cũ vẫn là nghiên cứu dự báo/sàng lọc cho đến khi có thực nghiệm mới. Chỉ thêm PPO/DQN không tự đủ tạo một bài báo Q1/Q2/A*.

## 11. Nguồn nghiên cứu đối chiếu trong lượt rà soát

- [ExRec, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/13707aad517ddd6c09ea02e0f55e1e7a-Abstract-Conference.html): trang proceedings đã được đọc lại; bản full text lưu trong `research/literature/papers/exrec_2025.txt` được đối chiếu các phần kiến trúc/MDP. Có chuỗi KC, KT và RL cho exercise recommendation. Bối cảnh là toán, không coi kết quả của tác giả là kết quả lập trình của dự án.
- [Code-DKT, EDM 2022](https://arxiv.org/abs/2206.03545): nguồn sơ cấp đã đọc lại; mô hình dùng code cho dự báo hiệu suất lập trình, minh họa vai trò student model, không tự là hệ chọn bài.
- Các kiểm toán đã có: `research/literature/gap_audit.md`, `research/literature/supplementary_gap_audit.md`, `research/review/offline_application_evaluation.md`. Đọc cùng nguồn gốc và mức truy cập ghi trong từng tệp.

Đây là rà soát yêu cầu gốc và đối chiếu có mục tiêu, không phải một lần tái lập toàn bộ SOTA đến 26/09/2026. Không thay đổi PDF của thầy, app, checkpoint, số liệu hoặc bản thảo đã khóa trong lượt này.
