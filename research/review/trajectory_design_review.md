# Phản biện thiết kế trajectory experiment trước outcomes mới

Ngày 26/09/2026. Đây là yêu cầu phương pháp cho một nhánh mới, chưa phải protocol được khóa hay kết quả đã chạy. Nguồn mới CodeBench 2016-2 đã được kiểm tra schema, chưa đánh giá performance ở thời điểm ghi phần thiết kế. Những holdouts 2016-1 đã được dùng trong các phân tích trước phải được coi là đã tiêu thụ.

## Câu hỏi đo được

Tại H1, sau một episode có ít nhất ba submission snapshots, liệu **code trung gian** có cải thiện dự báo outcome của bài mới kế tiếp ngoài lịch sử, outcome/time/count summaries và code đầu/cuối? Tất cả models nhận cùng target J và dự báo cùng Y_J. Đây là nested-input experiment tại cùng một thời điểm; không phải một H0→H1 comparison và không là hiệu ứng của việc buộc sinh viên sửa code.

Primary contrast là paired held-out NLL của M2 trừ M1. Brier, calibration và M0→M1 là secondary. Phải giữ khả năng kết luận âm hoặc không rõ. Không gọi đây là phép ước lượng population conditional mutual information từ finite-model losses.

## Inputs và các lời giải thích cạnh tranh

| Arm | Thông tin | Lý do cần |
|---|---|---|
| M0 | Pre-episode history; source item và target item ID/difficulty; submission count; first/final/intermediate verdict, numeric-grade, ERROR/missing summaries; elapsed time/gap summaries | Code không được hưởng lợi đơn thuần vì tiết lộ nguồn bài, số retry, kết quả cuối hoặc stopping/time |
| M1 | M0 + representations của code đầu/cuối, endpoint structural metrics và endpoint-diff descriptors | Code quality/endpoint representation phải là đối chứng trước khi gọi lợi ích của quá trình |
| M2 | M1 + strictly intermediate snapshot representations và path features đã chọn trước | Thông tin path thực sự có thể không khôi phục được chỉ từ endpoints |

Endpoint diff là hàm tất định của full first/final code. Nếu chỉ thêm diff, mọi gain là gain của cách biểu diễn/tính toán, không phải thêm raw information. Vì vậy diff thuộc M1. M2 phải có code từ những snapshots nằm giữa hai đầu; yêu cầu ít nhất ba snapshots cho cả ba arms, không thay eligible set giữa models.

M0 là một representation của nuisance variables, không phải toàn bộ raw outcome/time sequence. Không nói đã loại mọi confounding hay đã condition trên tất cả feedback nếu chỉ dùng summaries. Tương tự, first/final AST counts chưa tương đương full endpoint code. Một M1 quá yếu có thể khiến M2 được lợi vì bổ sung code-quality proxy, không phải path mechanism.

Nên có train-only sparse token/code representation cùng structural features ở M1; common tokenizer/vocabulary/IDF chỉ fit training users. M2 dùng cùng representation cho intermediate snapshots để so sánh có ý nghĩa. Tiền xử lý code là parsing text, không thực thi submission. Normalization phải nói rõ xử lý comments, identifiers và parse failures. Đừng coi AST parse failure là code không có thông tin; giữ cờ missing/parseability và common coverage.

Một feature family nhỏ, cố định, có thể gồm intermediate token-vector average, intermediate structural extrema/mean và độ dài đường thay đổi đã chuẩn hóa theo số chuyển tiếp. Đây chỉ là ví dụ trước protocol: owner phải khóa danh sách thực tế trước outcomes, và audit xem path features có dùng future/target code không. Không xem thêm nhiều tập feature rồi gọi một tập tốt nhất là confirmatory.

**Dữ kiện kiểm toán cần giữ:** nguồn 2016-1 có 2.416 cặp submission kề nhau với cùng CODE text nhưng numeric grade khác. Text equality không bảo đảm cùng execution/input/grading context, tính quyết định của chương trình hoặc record alignment; chưa xác định được cơ chế từ con số này. Raw checks phải kiểm tra mapping CODE–GRADE của các trường hợp đổi grade, không chỉ các ví dụ code đổi. Không gọi same-code resubmission là ground-truth no-learning control: người học có thể suy nghĩ/nhận feedback dù chưa đổi code. Token/AST equality cũng không là chứng nhận semantic equivalence. Target nghiên cứu vẫn là operational outcome.

## Training và split

1. Source mới phải được kiểm tra schema/chronology trước performance. Giữ checksum và định nghĩa CODE/SUBMITION/TEST/grade; xác minh timestamp cùng snapshot, không chỉ dựa vào tên thư mục.
2. Loại toàn bộ 471 IDs từng xuất hiện trong archive 2016-1 khỏi evaluation mới, nếu ID có semantics toàn cục đã xác minh. Train trên partition của source mới được phép để có item support; đây là fresh held-out students trong nguồn mới, không phải zero-shot transfer từ model 2016-1.
3. Giữ cùng eligible training/evaluation pairs, outcome definition, target identity và history boundary cho M0/M1/M2. Source grade/ERROR chỉ dùng khi có sẵn trước query; target code/grade tuyệt đối không dùng.
4. Cùng model family, cùng training rows, cùng validation tuning budget và tiêu chí chọn. Scale/impute/vocabulary/difficulty đều train-only; train difficulty cross-fit theo người nếu áp dụng target encoding. Không chọn model thắng bằng test.
5. Nếu mục tiêu loại lời giải thích calibration đơn giản, khóa cùng calibration procedure cho mọi arm bằng validation labels. Báo raw và calibrated losses, phân biệt primary đã khóa. Không tự điều chỉnh calibration riêng cho model yếu sau khi thấy test.
6. Cluster bootstrap theo held-out student cho primary paired difference, cùng resamples giữa arms; report equal-student sensitivity. CI có điều kiện trên pipeline/split đã fit, không gồm toàn bộ uncertainty do training/cohort/model search.

## Mức hiệu ứng và quyết định nghiên cứu

Đề xuất trước outcomes: δ = 0,005 nats mỗi target là một **ngưỡng thực dụng do người phân tích đặt cho dự báo**, không là educational utility. Owner cần chấp nhận/khóa hoặc thay bằng lý do độc lập trước results.

- Upper bound của 95% CI < 0: hỗ trợ cải thiện dự báo theo primary estimand.
- Upper bound < −δ: hỗ trợ cải thiện ít nhất bằng ngưỡng đã chọn.
- CI cắt 0: chưa rõ dấu; không kết luận zero effect.
- Lower bound > −δ: không phù hợp một cải thiện lớn ít nhất δ trong sampling view đã dùng; không chứng minh code trung gian vô ích trong mọi mô hình.

Một positive result chỉ hỗ trợ incremental predictive value của code trung gian **so với các input/representation controls đã xác định**. Để nói mechanism hoặc transfer competence cần thêm đánh giá; để nói exercise recommendation tốt hơn cần action-value evidence riêng.

## Tính mới còn phải bảo vệ

Code-DKT đã có first-attempt prediction từ full code/correctness history; CodeInsight có trajectory-related ablations; nghiên cứu code-edit và revision-aware success đã có các biểu diễn quá trình. Thay domain hoặc thêm intermediate code chưa đủ. Khác biệt có thể kiểm chứng của nhánh này là cùng future target, cùng eligible pairs, cùng H1, kiểm soát endpoint và feedback/count/time representations. Chưa được gọi tổ hợp này là đầu tiên vì tìm kiếm literature hữu hạn.

Nếu metadata không đủ đảm bảo snapshot timing hoặc fresh source có quá ít eligible targets/held-out students, phải báo feasibility failure trước fitting. Nếu M2 không cải thiện, không được bổ sung subgroup/feature/model vô hạn trên cùng test để cứu câu chuyện. Kết quả đó là thông tin quyết định hướng nghiên cứu.

## Điều chỉnh theo schema trước performance và kiểm tra module

Archive 2016-2 có 172 IDs, 38.881 SUBMITION và 87.299 TEST. Mỗi SUBMITION có đúng một CODE section không rỗng; 27.993 có numeric grade, 10.888 missing grade đều có ERROR. Không phát hiện timestamp lùi trong file theo audit. Những thống kê này phục vụ schema/coverage; không phải predictive performance.

Để tránh fit mô hình sparse trên một tập quá nhỏ, thiết kế đã chuyển sang pooling **chỉ 329 người train gốc của 2016-1** với 79 người train mới. Các 471 IDs cũ đều bị loại khỏi validation/test mới; old holdouts không đưa vào training. Giữ 208 validation targets và 274 test targets theo eligibility hiện tại, với item-support exclusions lần lượt 6/7. Test nhỏ vẫn hạn chế precision dù training được tăng; không dùng kết quả không rõ để nói intermediate path vô ích.

Namespace item IDs theo semester là cách bảo thủ khi chưa xác minh cùng số ID có cùng nội dung xuyên semester. Source/semester indicator thuộc M0. Cách pooling này là training trên nguồn cũ và một phần nguồn mới, đánh giá người mới ở source mới; không phải zero-shot hoặc strictly prospective transfer. Một số timestamp ở archive 2016-1 kéo sang 2017 nên tên semester không thay cho time cutoff.

Đã đọc static `research/revision_information/model_pipeline.py` trước fitting: transforms chỉ fit train; vocabulary dùng mọi source snapshot trong training episodes; M0 là exact column prefix của M1 và M1 là prefix của M2; chỉ strictly intermediate code được mean-pool cho block mới. Cùng logistic C=1 và cùng validation-only Platt cho mọi arm. Source code được token hóa bằng Python tokenizer có whole-document fallback cho syntax errors, không thực thi. Có guard index/user overlap/nonfinite features. Chưa thấy lỗi quan trọng trong module; caller xây pairs/numeric features vẫn cần audit riêng.

Một secondary control `M1_endpoint_redundant` thêm mean(first,final) token vector vào M1. Nó không thêm thông tin mới và chỉ là partial control cho capacity/regularization geometry, vì không match toàn bộ intermediate numeric block. Giữ primary M2−M1; không chọn contrast thuận lợi sau test. Common numeric clipping chỉ cần ở NLL; Brier/calibration nên dùng raw predicted probabilities. Module này chưa tự bảo đảm chronology hoặc target-label exclusion; đó là trách nhiệm của caller.

**Kiểm tra cuối trước lock/run:** đã đọc `features.py`, `schema_audit.py`, `recover_old_training_code.py`, `protocol.md` và `run_experiment.py`. Phát hiện TEST covariates ban đầu có thể dùng TEST cùng giây nhưng xảy ra sau H1; đã yêu cầu và xác minh sửa thành first-source-time ≤ TEST-time < H1 trước performance. Các biên source/target SUB có unique timestamp; prefix, first-observed designation, item namespaces, source/target cross-fit difficulty, code đầu/cuối/trung gian và target exclusion được kiểm tra nhất quán.

Tập loss training cuối có 3.906 pairs/380 contributors, gồm 3.177 pairs/309 người từ old training và 729 pairs/71 người từ fresh training. Validation có 208 pairs/20 người; test 274 pairs/28 người. Các eligible counts khác designated cohort counts vì phải có episode/probe phù hợp. Runner dùng cùng resampling weights cho mọi contrast và tính pair-weighted/equal-student estimates đúng; không phát hiện lỗi quan trọng trong đường đã đọc. Epsilon 1e-12 chỉ cho log loss. Protocol khóa mọi source/helper/data hash trước chạy; không thêm nhánh sau outcomes.

## Kết quả sau lock và phán quyết

Đã đọc `results.json` độc lập: lock 03:10:41 UTC có trước run 03:10:54 và fit hoàn tất 03:12:14. Primary calibrated M2−M1 NLL = **−0,001094**, 95% paired student CI **[−0,006666; +0,004346]**. Khoảng này chứa cả zero lẫn mức cải thiện −0,005 đã chọn trước. Kết luận là **chưa rõ**: không xác nhận lợi ích, nhưng cũng không loại trừ một lợi ích đạt ngưỡng đó.

Equal-student primary sensitivity = +0,000693 [−0,006256; +0,007408]. Raw M2−M1 = +0,007926 [−0,002876; +0,018107]. Calibrated M2−endpoint-redundant = −0,002884 [−0,009326; +0,003391]. Không lấy một dấu point estimate thuận lợi hay một secondary contrast đơn lẻ để thay primary. M0 có point NLL thấp nhất ở cả raw/calibrated tables; các paired comparisons chưa xác nhận superiority của M0 hoặc kết luận code vô ích.

Phép thử đã được thực hiện đúng câu hỏi hẹp trong các đường đã audit. Nó chưa tạo một positive mechanism finding đủ mạnh để nâng nhận định paper-ready. Giữ toàn bộ kết quả và ngừng mở thêm feature/model/subgroup branches trên holdout này. Kết luận vẫn giới hạn bởi 28 người test, shared-class context không được resample, finite lossy representations, grade-observability selection và availability assumptions của recorded snapshots/feedback.
