# Đề tài 4: kết quả nghiên cứu và đánh giá khả năng công bố

**Mốc tài liệu: 26/09/2026.** Báo cáo này cập nhật và thay thế các giả thuyết về tính mới/kết quả trong hai báo cáo định hướng ban đầu. Toàn bộ dữ liệu do dự án tự tìm từ nguồn công khai; không có dữ liệu riêng của thầy và không có thử nghiệm với sinh viên mới.

## 1. Quyết định khoa học

Nên giữ hướng đề tài 4 về hệ thống thích ứng cho học lập trình, nhưng câu hỏi bài báo phải hẹp và đo được: **những lần nộp lại giúp mô hình biết thêm điều gì về kết quả ở bài kế tiếp, sau khi kiểm soát cách đặt mục tiêu dự báo, và thông tin đó có ích cho một quyết định cụ thể không?**

Tôi không chọn câu chuyện “ghép Knowledge Tracing với PPO rồi gọi là khuyến nghị thông minh”. Dữ liệu hiện có không cho biết kết quả phản thực nếu cùng người học được giao một bài khác. Chúng cũng không có cơ chế phân bài và propensity đủ để mặc nhiên nhận diện giá trị nhân quả của một policy mới. Vì vậy, bài hiện thực hiện một **nghiên cứu dự báo và đánh giá ứng dụng hồi cứu**; không gọi kết quả đó là chứng minh cải thiện học tập.

Đã viết bản thảo tiếng Anh theo cấu trúc nghiên cứu: abstract, câu hỏi nghiên cứu, related work, estimand, phương pháp, dữ liệu và protocol, kết quả, ứng dụng, giới hạn, kết luận, tài liệu tham khảo và khai báo sử dụng AI. Bản nguồn là [manuscript.tex](manuscript.tex). Đây là bản nội dung trung lập, chưa gắn logo hay thông tin xuất bản của một tạp chí.

## 2. Khoảng trống nào còn bảo vệ được?

Rà soát mới làm hẹp đáng kể ý tưởng ban đầu. Không được tuyên bố:

- Người đầu tiên phân biệt sửa được bài hiện tại với kiến thức có thể dùng cho bài khác: Code-DKT đã bàn trực tiếp và đã minh họa dự báo cùng bài tương lai.
- Người đầu tiên gộp repeated attempts hoặc thay đổi tần suất cập nhật: GRATE và Pu & Becker đã có các hướng liên quan.
- Người đầu tiên dùng hành vi để kiểm tra độ tin cậy mastery hoặc dùng permutation controls: các nghiên cứu L@S 2026 và CE-KT đã đi vào vấn đề này.
- Người đầu tiên dùng cùng mô hình/cùng target tương lai, proper scores và bootstrap theo người học: artifact BKT công khai **22/09/2026** đã mô tả thiết kế rất gần.
- Người đầu tiên chỉ ra dự báo tốt chưa chắc dạy tốt: LEOPARD và REM đã đặt vấn đề từ trước.

Nguồn gần nhất được đối chiếu trong [gap audit](../research/literature/gap_audit.md) và [kiểm tra bổ sung](../research/literature/supplementary_gap_audit.md). Nguồn chỉ xem được abstract/metadata được ghi rõ; không coi dataset/notebook artifact là bài đã peer review. Rà soát có mục tiêu không phải bảo đảm đã tìm hết mọi bài đến ngày chốt.

Phần thực nghiệm hiện có bảo vệ được là **đo ảnh hưởng của việc căn chỉnh nhiệm vụ dự báo trên log lập trình, kiểm tra lại trên người học mới và nền tảng khác, rồi đo một ứng dụng cảnh báo bằng quy tắc khóa trước**. Đây là đóng góp kiểm toán thực nghiệm có giới hạn, chưa tự động đạt ngưỡng phương pháp mới mạnh.

Một câu hỏi cụ thể hơn đã được kiểm tra là liệu **đường đi qua các bản mã trung gian** có ích sau khi mô hình đã nhận số lần thử, thời gian, kết quả đầu/cuối/trung gian và mã nguồn đầu/cuối. Diff chỉ giữa hai endpoint là hàm của chính hai endpoint; thêm nó có thể giúp cách biểu diễn, nhưng không tạo thông tin mới nếu đã biết đầy đủ endpoint. Phép thử đúng phải tách hai việc này. Kết quả trên holdout học kỳ mới hiện chưa rõ; không tuyên bố đã tìm được một cơ chế hay phương pháp mới thành công.

## 3. Dữ liệu đã tải, đo và kiểm toán

| Nguồn | Dữ liệu thực đọc được | Giới hạn quyết định thiết kế |
|---|---|---|
| ACcoding, Zenodo v2.0.0 | 2.181.602 submissions; 9.866 user IDs; 4.301 problem IDs; khoảng 98% C; timestamp 2024–2025 | Không có full source code hoặc per-test outcomes. Mô tả trang và thời gian thật trong archive không hoàn toàn khớp; báo cả hai. |
| CodeBench UFAM, 2016-1, release 1.81 | 471 user IDs; 535 lượt ghi danh; 9 lớp; 235 bài; 153.931 SUBMITION và 167.791 TEST | Có mã trong execution records. Numeric grade thiếu khi có ERROR; first submission có thể đã có TEST trước đó. |
| CodeBench UFAM, 2016-2, release 1.81 | 172 user IDs; 5 lớp; 38.881 SUBMITION và 87.299 TEST; tháng 10/2016 đến 02/2017 | Mỗi submission có một CODE không rỗng. Loại 38 ID trùng nguồn cũ khỏi mọi partition của cohort mới; không mặc định ID khác là hai con người khác nhau. |

Nguồn gốc: [ACcoding chính thức](https://doi.org/10.5281/zenodo.11395043), [CodeBench chính thức](https://codebench.icomp.ufam.edu.br/dataset/). Không mặc định “download được” đồng nghĩa quyền phát tán lại raw data. Các nguồn gated như CodeInsight không được tính là dataset đã sở hữu.

ACcoding ban đầu có 1.500 người được chia train/validation/exploratory test; kết quả exploratory đã được xem nên không gọi lại là test nguyên vẹn. Sau đó khóa thêm **1.500 người khác**, loại toàn bộ người pilot trước khi chọn, thu được 420.076 submissions. Các tham số, alpha và ngưỡng ứng dụng đều được khóa trước khi chấm cohort mới.

CodeBench chia toàn cục theo user ID, kể cả người học xuất hiện ở nhiều lớp: 329 train, 74 ban đầu dành validation, 63 test. Phép so sánh paired-target bổ sung dùng 74 người chưa được dùng để xem performance trước đó; không trộn kết quả này với test 63 người cũ.

## 4. Đo đúng đại lượng

Một cặp đo gồm cùng người học và cùng kết quả đầu tiên quan sát được của bài kế tiếp:

1. **H0:** lịch sử đến sau lần nộp đầu của bài hiện tại.
2. **H1:** lịch sử đến sau lần nộp cuối của cùng episode.
3. Cả hai dự báo **cùng Y của cùng bài tương lai J**.

Biết J ở đây là điều kiện hồi cứu từ log, không phải hệ thống đã chọn được bài tốt nhất. Episode phải có bài kế tiếp quan sát được, nên continuation/selection vẫn là giới hạn.

Metric chính là **ΔNLL = NLL(H1) − NLL(H0)**; âm nghĩa là dự báo tốt hơn. Báo thêm Brier, calibration, mean Δp, số người/cặp, coverage và khoảng bootstrap theo người. Không coi hàng chục nghìn cặp là hàng chục nghìn người độc lập.

Một thay đổi xác suất trung bình không bằng learning gain. Với dự báo Bayes đúng cho **cùng một biến kết quả tương lai**, kỳ vọng cập nhật bằng 0 do luật kỳ vọng lặp, kể cả khi người học thực sự học trong khoảng đó. Loss vẫn có thể giảm khi thêm thông tin. Kết quả này không áp dụng nguyên xi cho hai biến năng lực tiềm ẩn ở hai thời điểm khác nhau. Có kiểm tra số học chính xác 9 trường hợp; đây là minh họa nền tảng, không phải lý thuyết mới của bài.

## 5. Kết quả chính đã thực chạy

### Xác nhận trên ACcoding: lợi ích nhỏ, có bằng chứng

69.825 cặp từ 1.500 người mới, cùng target cho mọi mô hình:

| Nhiệm vụ huấn luyện logistic | NLL H0 | NLL H1 | ΔNLL và khoảng 95% theo người học |
|---|---:|---:|---|
| Mọi submission | 0,589148 | 0,587049 | −0,002099 [−0,003262; −0,000829] |
| Chỉ first attempt — phép thử chính | 0,581115 | 0,579549 | **−0,001566 [−0,002300; −0,000756]** |
| Cùng future target, hai phase | 0,580450 | 0,579035 | −0,001416 [−0,001842; −0,000971] |

Mô hình paired-target có mean Δp gần 0, nhưng proper losses vẫn tốt lên. Phase calibration có thể tạo một phần hành vi này một cách cơ học; không diễn giải thành “đã loại bỏ learning giả”.

Alpha nội suy được chọn chỉ trên validation: 0,5 / 0,75 / 1 tương ứng ba mô hình. Với first-attempt, alpha 0,75 giảm thêm NLL 0,000418 so với full update. Đây là baseline hiệu chỉnh đơn giản, không phải thuật toán mới. Calibration không cải thiện đồng đều với mọi mô hình.

Chi tiết và mọi phân tầng đã định trước: [confirmation RESULTS](../research/confirmation/RESULTS.md), [methods](../research/confirmation/METHODS.md).

### CodeBench: chưa xác lập được lợi ích cập nhật ổn định

Test ban đầu có 1.125 cặp numeric-grade và 1.665 cặp operational-error. Mô hình first-attempt có ΔNLL tương ứng −0,005277 và −0,001912; cả hai khoảng đều chứa 0. Mô hình huấn luyện mọi submission trông tốt hơn trong numeric-grade task, nhưng điều đó phụ thuộc cách chọn nhãn và nhiệm vụ fit.

Phép thử paired-target trên holdout mới có 1.342 cặp numeric và 2.033 cặp operational từ 72 người đóng góp. Paired-target làm NLL tuyệt đối tốt hơn ở cả H0 lẫn H1, song **tất cả khoảng thay đổi H1−H0 vẫn chứa 0**. Điều này hỗ trợ việc căn chỉnh task như một control cần thiết, chưa chứng minh retry cung cấp ích lợi gia tăng đáng tin trên nguồn này. Khoảng chứa 0 cũng không chứng minh hiệu ứng bằng 0 hoặc khác ACcoding.

Chi tiết: [thí nghiệm CodeBench](../research/codebench_experiment/results.md), [control trên holdout mới](../research/codebench_experiment/paired_task_results.md).

### Kiểm tra theo lịch: đúng hướng nhưng coverage hẹp

Control chỉ fit sự kiện trước cutoff **27/10/2025 08:45:57** và chấm sau cutoff còn 2.291 cặp, 516 người. ΔNLL = −0,003895 [−0,007585; −0,000100]. Chỉ **2,75% toàn bộ episode nhiều lượt** còn đáp ứng điều kiện. Đây là kết quả thăm dò trên lát cắt muộn, bài đã có hỗ trợ quá khứ; không gọi là bằng chứng triển khai prospective rộng.

Timestamp là thời điểm tạo submission; không có timestamp công bố verdict nên chưa xác minh mọi phản hồi trước đó đã sẵn có tức thì cho một hệ thống online. [Temporal results](../research/confirmation/temporal_RESULTS.md).

### Mô hình chuỗi: kết quả giữ được qua ba seed

GRU đã hội tụ theo early stopping trên validation, gồm hai cách chọn training labels × ba seed. Ensemble lấy trung bình xác suất của cả ba seed, không chọn seed tốt nhất trên test:

| GRU | NLL H0 → H1 | ΔNLL [95%] | Mean Δp |
|---|---|---|---:|
| Fit mọi submission | 0,594697 → 0,588198 | −0,006499 [−0,007939; −0,005156] | +0,016873 |
| Fit nhãn first-attempt | 0,596264 → 0,592048 | −0,004215 [−0,005637; −0,002781] | −0,002783 |

Cả sáu seed riêng đều giảm NLL với khoảng dưới 0. Tuy nhiên, hai ensemble có dấu mean Δp ngược nhau. Đây là bằng chứng thực cho việc đánh giá trên outcome thay vì coi xác suất đi lên mới là một cập nhật tốt. Mức giảm loss lớn hơn cũng không có nghĩa mô hình cuối tốt hơn: NLL H1 của GRU vẫn cao hơn logistic first-attempt/paired-target trong thí nghiệm này. Không gọi GRU tùy biến này là bản tái lập chính xác DKT hay một baseline SOTA đã được đánh bại. [Kết quả đầy đủ](../research/sequential/validation_converged/final_results.md).

### Thông tin mã trung gian

Phép thử riêng dùng cùng thời điểm cuối episode H1, cùng target và cùng cohort cho M0 → M1 endpoint code → M2 intermediate path. Nó đã chạy một lần sau khi khóa protocol; không gộp vào phép so sánh H0→H1 vì hai estimand khác nhau.

Protocol cố định sử dụng 3.906 cặp train từ 380 người đóng góp: 3.177 cặp thuộc nhóm train cũ và 729 cặp thuộc train học kỳ mới. Validation mới có 208 cặp/20 người; test mới 274 cặp/28 người. Mỗi episode có ít nhất ba snapshots; target chỉ được giữ nếu lần nộp đầu quan sát được có numeric grade; không lấy một lượt nộp lại có grade để thay thế lần đầu thiếu grade. M0 nhận history/feedback/time/count và source/target identity; M1 thêm mã đầu/cuối; M2 thêm mã thực sự nằm giữa. Cả bốn arms, gồm một control lặp thông tin endpoint, có cùng cách fit và calibration. Đây là thí nghiệm trên tập test nhỏ, cùng lớp với train, nên không hứa hẹn độ chính xác thống kê cao hoặc khái quát sang lớp mới.

| Arm | NLL chưa calibration | NLL sau calibration trên validation |
|---|---:|---:|
| M0: history/feedback/count/time | 0,623534 | 0,626371 |
| M1: M0 + mã đầu/cuối | 0,625941 | 0,627958 |
| M2: M1 + mã trung gian | 0,633867 | 0,626864 |
| M1 + token block suy ra từ endpoint | 0,630323 | 0,629748 |

**Phép thử chính M2−M1:** ΔNLL sau calibration = **−0,001094 [−0,006666; +0,004346]**. Khoảng chứa cả 0 và mức cải thiện −0,005 nats đã định trước. Vì vậy chưa xác lập được lợi ích, nhưng cũng chưa loại được lợi ích cỡ đó. Khi mỗi người học có trọng số ngang nhau, point estimate đổi thành +0,000693, khoảng vẫn chứa 0. Các đối chứng raw/calibrated và endpoint-redundant cũng chưa làm rõ dấu hiệu ứng. M0 có point NLL thấp nhất, nhưng bảng không chứng minh nó vượt các arm còn lại về mặt thống kê.

Có 211/274 target được TEST sau H1 trước lần SUBMITION đầu. CODE là snapshot ghi kèm event; kiểm tra hash không tự chứng minh grader đã thực thi đúng snapshot đó hoặc feedback có sẵn ngay ở timestamp. Đây không phải phép đo khả năng làm một bài hoàn toàn chưa được thử. Kết quả được giữ như một phép thử chưa phân định được câu hỏi, không thêm feature/subgroup để cứu giả thuyết. [Protocol, source và kết quả](../research/revision_information/README.md), [bảng kết quả đầy đủ](../research/revision_information/results.md).

## 6. Ứng dụng thực nghiệm đã đo được là gì?

Ứng dụng là **cảnh báo nguy cơ không thành công ở bài kế tiếp quan sát được**, phục vụ một hàng đợi hỗ trợ giả định. Quy tắc chọn ngưỡng trên validation được khóa trước confirmation: (a) đạt ít nhất 80% failure recall; (b) top 30% risk trên validation. Quy tắc thứ hai không cưỡng bức workload confirmation đúng 30%.

Với logistic first-attempt ở quy tắc (a), workload thay đổi −0,016 điểm phần trăm [−0,167; +0,137], recall +0,046 điểm [−0,143; +0,237]. **Lỗi xác suất tốt hơn chưa tạo cải thiện quyết định rõ ràng ở ngưỡng này.** Với all-submission, workload giảm nhưng recall cũng giảm; phải gọi là trade-off. Quy tắc (b) chưa có bằng chứng tăng recall ở cả ba logistic.

Đây là phép đo ứng dụng thật trên log có outcome, với code và uncertainty, nhưng **không có can thiệp hỗ trợ thực tế, không đo learning gain, không thử policy chọn bài**. Không sử dụng sinh viên mô phỏng như bằng chứng thay thế về hiệu quả trên người. [Application protocol và kết quả](../research/application/README.md).

**GRU có một kết quả ứng dụng tích cực ở mức nhỏ:** theo ngưỡng workload 30% đã chọn trên validation, ensemble FIRST tăng failure recall từ 44,58% lên 45,27%, tức **+0,694 điểm phần trăm [0,336; 1,057]**. Workload thực tăng từ 30,71% lên 30,81%; khoảng thay đổi là [−0,141; +0,337] điểm. PPV tăng 77,27% → 78,21%. Khoảng workload chứa 0 không chứng minh workload bằng nhau; không được gọi đây là kiểm định noninferiority. Đây là kết quả thứ cấp với khoảng danh nghĩa chưa chỉnh đa so sánh. GRU ALL có recall tăng nhỏ hơn +0,350 điểm [0,005; 0,704]. Toàn bộ năm predictor dùng đúng cùng các cặp và nhãn; [bảng trade-off đầy đủ](../research/application/results_table.md).

[Biểu đồ thay đổi workload và recall](../research/application/figures/screening_changes.png) thể hiện đủ năm mô hình ở cả hai quy tắc, với khoảng bootstrap và mốc 0. Đồ thị đi kèm [mã dựng lại và manifest](../research/application/figures/figure_manifest.json), chỉ đọc aggregate outputs đã lưu.

## 7. Đánh giá Q1/Q2/A*

Q1/Q2 thuộc hệ xếp hạng tạp chí theo năm và ngành; A* ở đây là hội nghị ICORE. Chúng không chuyển đổi trực tiếp. Các số đã kiểm chứng trong lần tra cứu là **SJR 2024**, không gọi là JCR/Q1 năm 2026.

| Nơi xuất bản | Thông tin đã kiểm chứng | Đánh giá phù hợp |
|---|---|---|
| IJAIED | Q1 theo SJR 2024; chuyển sang Elsevier từ 01/01/2026 | Mục tiêu định hướng nếu bài tạo insight về student modelling và AI giáo dục đủ mạnh. |
| ACM TOCE | Q1 theo SJR 2024 | Phù hợp nếu kết quả thực sự giải thích cách học/làm bài lập trình, không chỉ chênh lệch metric. |
| IEEE TLT | Q1 theo SJR 2024 | Cần đóng góp công nghệ/phương pháp đáng kể và bằng chứng ứng dụng thuyết phục hơn. |
| AIED / LAK / RecSys | A theo ICORE 2026 | Các cộng đồng liên quan, nhưng mỗi nơi đòi trọng tâm riêng. |
| AAAI | A* theo ICORE 2026 | Chưa có cơ sở chọn làm mục tiêu nộp cho đóng góp hiện tại. |
| JEDM / EDM | JEDM Q3 SJR 2024; EDM B ICORE 2026 | Độ phù hợp chuyên môn đáng cân nhắc cho kiểm toán/replication chặt chẽ; không quảng bá nhầm là Q1/Q2. |

Nguồn và quy định từng venue: [venue strategy](../research/venues/venue_strategy.md). IJAIED yêu cầu abstract ≤250 từ, 1–7 keywords, double anonymized. TOCE dùng author–year từ tháng 05/2026. Chưa có tên tác giả, affiliation, CRediT, funding hoặc ethics approval được xác nhận; không tự điền cho đủ form.

**Đánh giá cuối của đợt nghiên cứu này:** đã có nghiên cứu và bản thảo đầy đủ với kết quả thật; chưa đủ cơ sở gọi là một bài SOTA hoặc sẵn sàng nộp A*. Tôi chọn **IJAIED làm đích ưu tiên có điều kiện**, TOCE là phương án theo trọng tâm computing education. Hướng Q1 không phải lời hứa nhận bài. Tính mới bị prior art làm hẹp, lợi ích ứng dụng nhỏ và phép thử mã trung gian chưa rõ là những vấn đề nội dung; đổi template, thêm GPU hoặc thêm mô hình không tự giải quyết. [Đánh giá khoa học sau toàn bộ thí nghiệm](../research/review/scientific_readiness_addendum.md).

Muốn nâng từ bản nghiên cứu này lên một submission mạnh, phần cần được xác lập là một phát hiện có thể lặp lại vượt các lời giải thích về nhiệm vụ dự báo, endpoint quality, calibration và selection; hoặc một thiết kế đo lường có giá trị hơn trên assessment đủ độc lập. Đó là một vòng nghiên cứu mới, cần hypothesis và dữ liệu/holdout mới. Không coi test đã xem là nguồn để tiếp tục tìm điểm thắng. Bản hiện tại có thể làm cơ sở thảo luận khoa học với thầy và đánh giá phản biện, không nên quảng bá như đã đạt chuẩn chấp nhận Q1.

## 8. Tái lập và việc đã/không thực hiện

Các thư mục nghiên cứu giữ protocol nội bộ có timestamp/hash, mã xử lý và fit, model-selection logs, aggregate metrics, learner bootstrap, khóa ngưỡng ứng dụng, và nguồn tài liệu có trạng thái truy cập. Internal lock giúp kiểm tra thứ tự thao tác; không tự biến nghiên cứu thành preregistered study bên ngoài.

[Hướng dẫn tái lập](../research/reproducibility/README.md) ghi môi trường thực đã dùng và thứ tự chạy. Bản thảo có 22 tài liệu tham khảo đã kiểm tra chéo; abstract dưới 250 từ. PDF được dựng từ đúng nội dung nguồn bằng renderer cục bộ và kiểm tra các trang. Trình biên dịch LaTeX tích hợp báo lỗi môi trường “Unable to find standard directories for platform”, nên không ghi rằng `.tex` đã được biên dịch thành công bằng công cụ đó. Nguồn `.tex` được giữ nguyên để chỉnh sửa và biên dịch ở môi trường phù hợp.

Các kiểm tra gồm: không dùng target outcome để dựng prefix, giữ cùng target cho H0/H1, cross-fitting item difficulty, chia theo người qua nhiều lớp, xử lý tie/clock reversal, invariance khi đổi tương lai, kiểm tra GRU full/chunk state, số học bootstrap và kiểm tra identity. Không thực thi mã nguồn sinh viên.

Không mua GPU, không liên hệ người học/tác giả, không nộp bài hay công khai raw data. Không gán ethics exemption hoặc giấy phép chung không tồn tại. Người đứng tên bài cần kiểm tra và chịu trách nhiệm khoa học; bản thảo khai báo rõ phần hỗ trợ của AI và chưa giả định bước xác minh cuối của tác giả con người đã hoàn tất.
