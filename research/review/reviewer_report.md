# Phản biện phương pháp — cập nhật sau nghiên cứu xác nhận

Ngày: 26/09/2026. Phạm vi đọc: hai báo cáo ở thư mục gốc, pilot/fixed probe, ACcoding confirmation, CodeBench, screening audit, mã temporal sensitivity và recurrent baseline. Kết quả của các nhánh chưa hoàn thành được ghi riêng. Đây là bản phản biện, không phải bản thảo bài báo và không phải xác nhận trước về khả năng được nhận ở Q1/Q2/A*.

## 1. Phán quyết hiện tại

**Các kết quả hiện có chưa đủ cho một bài báo thực nghiệm mạnh.** Chúng chứng minh pipeline khai thác dữ liệu chạy được, có kiểm soát biên thông tin, và một số thông tin từ các lượt nộp thêm giúp dự báo kết quả ở bài tiếp theo. Chưa chứng minh một failure mode quan trọng của phương pháp công bố, một cơ chế sửa mới, hay lợi ích của khuyến nghị bài tập.

Hướng vẫn đáng tiếp tục. Câu hỏi có triển vọng là: **Khi nào cập nhật mô hình từ nhiều lượt nộp cải thiện dự báo một outcome bài mới, các kết luận đó phụ thuộc định nghĩa nhiệm vụ dự báo ra sao, và sự khác biệt có đủ lớn để thay đổi các quyết định được xác định trước hay không?** Câu hỏi này cho phép kết quả âm; không mặc định rằng retry là nhiễu hay học giả.

Phát biểu mạnh nhất hiện có thể bảo vệ: trên cohort xác nhận ACcoding gồm người học hoạt động đủ nhiều, với protocol khóa trước kết quả, thông tin thêm trong các episode nhiều lượt giúp cải thiện nhỏ dự báo cùng outcome tương lai; lợi ích còn tồn tại ở đối chứng huấn luyện cùng paired target và adapted GRU. CodeBench chưa xác nhận rõ lợi ích của các readout first-attempt. Screening logistic chưa cho lift rõ; GRU có một số gains nhỏ theo threshold đã khóa, cần đọc workload và recall cùng nhau. Mọi từ như “causal learning”, “safe recommendation”, “optimal exercise”, “SOTA” hoặc “đầu tiên” đều chưa được hỗ trợ.

## 2. Những đóng góp không được tính mới chỉ bằng cách đặt tên

- Code-DKT đã đánh giá first attempts và trực tiếp phân biệt kiến thức dùng cho bài khác với việc gần giải xong bài hiện tại. First-versus-retry protocol không phải đóng góp mới tự thân. [Bài gốc](https://arxiv.org/abs/2206.03545)
- Zhang, Meng và Lin (L@S 2026), *Augmenting Knowledge Tracing With Self-Regulated Learning Indicators for Reliable Skill-Mastery Estimation*, đã khảo sát việc vượt ngưỡng mastery cùng dấu hiệu như rapid guessing/repeated attempts và liên hệ với performance drop/recovery sau đó trên ASSISTments 2009–2010. Đây là đối thủ gần trực tiếp cho tuyên bố chung về độ tin cậy của mastery/readiness sau retries. **Mới kiểm chứng abstract và metadata, chưa đọc được full text:** không suy ra họ dùng cùng paired estimand, cùng code-trace protocol hoặc cùng estimator. Tính mới phải được đối chiếu full text trước submission. [DOI bài gốc](https://doi.org/10.1145/3774398.3811597), [hồ sơ HKU](https://hub.hku.hk/handle/10722/375606)
- Artifact công khai *Step-level evidence integration in bayesian knowledge tracing: A controlled within-model ablation study*, phát hành 22/09/2026, so sánh cách tích hợp scaffold evidence bằng BKT với cùng tham số, trạng thái ban đầu và target bài gốc tiếp theo cùng skill; có learner bootstrap và phân biệt AUC với proper scores. Đây là prior art trực tiếp cho một audit within-model/fixed-future-target nói chung. **Đã đọc mô tả artifact, chưa notebook; chưa xác nhận là bài đã peer review.** Không khẳng định identical protocol với programming submissions, nhưng không còn căn cứ gọi matched future-target evaluation tự thân là mới. [Artifact gốc, DOI 10.17632/tnzghkdgfw.1](https://data.mendeley.com/datasets/tnzghkdgfw/1)
- Phân rã nhiều trạng thái, multi-scale/phase-aware KT và uncertainty-aware recommendation đã có các đối thủ gần. PAKT 2026 là một ví dụ; cần đối chiếu giả định và nhiệm vụ, không chỉ tên module. [PAKT](https://arxiv.org/html/2607.13103v1)
- CE-KT (preprint tháng 8/2026) đã dùng process-conditioned evidence, đối chứng permuted context/random proxy và đánh giá proper scores; GRATE (UMAP 2021) đã gộp attempts và kiểm tra state fluctuation trong programming; Pu–Becker (AIED 2022) đã xét all/first responses và repeated-attempt batches. Không nhận process gating, episode compression hoặc permutation control là novelty độc lập. Đường dẫn, vị trí trang và mức đọc từng nguồn nằm trong [kiểm tra literature bổ sung](../literature/supplementary_gap_audit.md).
- Reward flow, estimated logging policy và offline difficulty recommendation đã được nghiên cứu trước mốc ngày yêu cầu; tác giả cũng phân biệt proxy thành công phù hợp độ khó với learning gain. [Girard và cộng sự, 2026](https://arxiv.org/html/2606.23015v1)
- Posterior là martingale đối với một đại lượng cố định; proper score giảm khi thêm thông tin dưới mô hình Bayes đúng; positive clipping làm đổi mục tiêu. Đó là các hệ quả chuẩn dùng làm nền tảng chẩn đoán, không phải định lý mới.
- Shrinkage một hệ số, phase-specific calibration hoặc hai đầu dự báo phù hợp hai thời điểm là các đối chứng cần thiết. Chưa có căn cứ gọi chúng là thuật toán KT mới.
- Mô phỏng nhiều họ môi trường là kiểm tra độ bền cần có; không tự là đóng góp mới và không xác nhận môi trường nào mô tả sinh viên thật.

Tính mới khả dĩ phải là một **phát hiện thực nghiệm chưa được mô tả đầy đủ**, được tái lập đa nguồn với cơ chế giải thích có đối chứng, hoặc một protocol/benchmark giải quyết một sai sót thực tiễn đủ lớn. Việc chưa tìm thấy một tiêu đề giống hệt không xác nhận tính mới.

## 3. Các phản biện ưu tiên

| Ưu tiên | Vấn đề | Vì sao ảnh hưởng kết luận | Bằng chứng/đối chứng cần có |
|---|---|---|---|
| P0 | Đánh đồng cập nhật dự báo với tăng năng lực | Hai prefix cùng dự báo một Y tương lai; p0 không phải outcome nếu ngừng luyện | Estimand rõ; không dùng hiệu p làm treatment effect; xem `paired_estimand.md` |
| P0 | Nhiệm vụ/horizon huấn luyện không khớp H0 | Predictor next-submission được hỏi ở giữa episode về bài xảy ra sau nhiều lượt nữa | Paired-target training control dùng cùng Y tại H0/H1, khóa trước test mới |
| P0 | Kể chuyện từ test đã xem | Pilot đã dẫn tới thay đổi mô hình, chỉ tiêu và giả thuyết | Cohort xác nhận chưa xem kết quả, protocol có timestamp và lịch sử sửa; test cũ chỉ exploratory |
| P1 | Điều kiện hóa theo tương lai J và việc tiếp tục học | J, thời điểm dừng, có outcome tiếp theo đều phụ thuộc lịch sử và hành vi | Báo coverage/attrition, tính đúng first exposure; không diễn giải policy value hay hiệu quả luyện thêm |
| P1 | Cohort >=20 bài dùng toàn bộ tương lai | Loại nhiều người bỏ học/ít hoạt động trước khi phân tích | Nêu đúng population; phân tích cohort phổ rộng hoặc eligibility bằng prefix ở nghiên cứu đầy đủ |
| P1 | CodeBench TEST/SUBMITION, GRADE thiếu, snapshot không đồng bộ | Sai parser có thể tạo false failure, false first exposure hoặc future-code leakage | Kiểm kê đầy đủ, unit semantics, strict-time histories; không tự gán missing grade=0 |
| P1 | “Retry” không đồng nghĩa “repair” | ACcoding thiếu code; nộp lại có thể cùng chương trình hoặc sau khi đã AC | Chỉ gọi repeated submission; xác minh code diff trong nguồn có snapshot đúng thời điểm |
| P1 | Khác biệt training calibration giả làm cơ chế cập nhật | Predictor all-attempt và first-only có intercept/phân phối khác | Task-aligned/phase control, calibration-in-the-large, reliability và proper scores; không so hai thang đo khác đơn vị |
| P1 | Snapshot training chứa sự kiện muộn hơn test | Student-disjoint không phải prospective temporal validation | Phát biểu đúng loại generalization; thêm cutoff/cohort holdout thực sự nếu muốn claim triển khai theo thời gian |
| P1 | Thời gian nộp khác thời gian feedback được công bố | ACcoding `created_at` chưa xác minh là verdict-release time; judging có thể bất đồng bộ | Gọi đúng record-order retrospective prefix; không bảo đảm online feedback availability nếu không có release timestamp hoặc kiểm tra latency |
| P1 | Không có action support/counterfactual outcomes | Chỉ biết kết quả bài đã được chọn; không biết kết quả các bài thay thế | Candidate ranking chỉ là sensitivity; policy regret phải được kiểm chứng ở môi trường có ground truth |
| P2 | Tăng AUC nhỏ nhưng thiếu ứng dụng | Statistical detectability không tự chứng minh giá trị sử dụng | Risk-screening workload/miss-rate hoặc quyết định cố định; tránh suy diễn từ AUC |
| P2 | CI có điều kiện trên mô hình/split cố định | Không bao gồm thay đổi train sample, seed hay estimator design | Báo rõ; lặp split/retraining đủ cho claim ổn định, hoặc giới hạn kết luận ở predictor cố định |
| P2 | Nhiều contrasts và subgroups | Một số khoảng 95% không cắt zero có thể xuất hiện khi khảo sát nhiều nhánh | Tách primary đã khóa với secondary/exploratory; các CI hiện tại là nominal/descriptive, không là bảo đảm đồng thời cho toàn bộ bảng |
| P2 | Trọng số theo hàng | Người có nhiều episode ảnh hưởng nhiều hơn | Pair-weighted primary rõ ràng; equal-student sensitivity, student-cluster CI |

## 4. Những gì kiểm tra mã đã xác nhận

### Pilot ACcoding

- Current result/score/code_length/code không nằm trong predictors.
- Item difficulty chỉ từ training students, training features cross-fit theo sinh viên.
- Thay nhãn test hiện tại không làm đổi feature của chính nó, feature quá khứ hoặc feature train trong fixture kiểm tra.
- Time-gap dùng timestamp của query/submission hiện tại: đúng cho submission-time outcome prediction; không được mang nguyên sang exercise-selection-time prediction.
- Các metric tách first, retry, retry trước AC và sau AC; hiệu ứng same-item nhỏ hơn nhiều khi chỉ giữ retry trước AC.

### Fixed future probe

- H0 dùng feature ở ngay trước submission thứ hai của episode i, nên chỉ chứa lịch sử đến sau submission đầu tiên.
- H1 dùng feature ngay trước target j, nên chứa toàn bộ episode i nhưng chưa có nhãn của j.
- Hai query dùng cùng difficulty của j, cùng nhãn Yj và cùng mô hình đã đóng băng; gap bị bỏ ở cả fitting lẫn prediction.
- Target phải mới với người học trong extract và đã có trong training; các trường hợp loại được đếm và kiểm tra tổng attrition.
- Nhánh `--train-first-only` thay đúng cả tập fit scaler và logistic; giữ nguyên test pairs. Đây là sensitivity hợp lệ, nhưng chưa giải quyết hết horizon mismatch.
- Student bootstrap tính tổng paired differences theo người rồi lấy mẫu người; đúng với ước lượng trọng số theo pair.

Chưa phát hiện lỗi biên thông tin quan trọng ở các phiên bản đã đọc. Kết luận này không bao gồm semantic correctness của mọi nguồn dữ liệu hay các thay đổi sau lần audit. Timestamp ties vẫn là quy ước sắp ID chưa xác minh dưới giây.

## 5. Điều kiện tối thiểu trước một submission nghiêm túc

1. **Một primary claim** có thể bị bác bỏ, tương ứng đúng outcome và population. Không ghép một paper KT, một paper causal RL và một hệ thống LLM vào cùng gói.
2. **Xác nhận độc lập khỏi pilot:** protocol khóa trước conditional outcomes; mọi sửa lỗi/deviation ghi rõ. Cohort mới cùng platform chỉ là student replication, không phải external validation.
3. **Nguồn thứ hai có semantics độc lập:** CodeBench được parse đúng, first exposure xét cả TEST lẫn SUBMITION, label missingness được báo, người học split xuyên lớp. Không coi hai nguồn khác ngôn ngữ/platform là một transfer experiment nếu không thiết kế như vậy.
4. **Đối thủ đúng nhiệm vụ:** item/history đơn giản mạnh, first-only, paired-task/phase control, ít nhất một KT mạnh và một baseline code-aware ở nguồn thực sự có code. Cùng input, target, preprocessing và budget so sánh.
5. **Phát hiện vượt “thêm dữ liệu thì đoán tốt hơn”:** một khác biệt quan trọng về cập nhật, calibration hoặc quyết định; phân tích cơ chế loại lời giải thích đơn giản; negative result được chấp nhận.
6. **Ứng dụng kiểm chứng được:** failure screening có nhãn factual hoặc audit decision sensitivity trung thực; nếu claim wrong recommendation/regret thì cần ground-truth simulation hoặc dữ liệu nhận dạng phù hợp.
7. **Nếu dùng simulation:** finite-data learned models/policies, nhiều learning/repair/observation regimes độc lập, môi trường kiểm tra ngoài môi trường dùng chọn mô hình, mô tả giả định rõ. Toy oracle hiện tại chỉ minh họa tồn tại.
8. **Reproducibility:** hashes, parser/schema, protocol, cố định split/seed, counts, missingness/coverage, scripts và aggregate outputs; model configurations thực tế; dataset access/licensing đúng phiên bản.

Không có checklist nào bảo đảm Q1/Q2/A*. Xếp hạng venue là thuộc tính khác với độ đúng của kết luận. Hiện nên mô tả là nghiên cứu đang xác minh giả thuyết, chưa là paper-ready SOTA contribution.

## 6. Trạng thái cập nhật

- Baseline, fixed-probe exploratory, ACcoding confirmation, CodeBench và screening logistic đã đọc mã/kết quả và audit.
- Temporal sensitivity đã đọc mã trước khi chạy và kết quả sau sửa lỗi triển khai có ghi nhận.
- Recurrent baseline đã đọc mã/convergence amendment, sáu fit cuối cùng, confirmation và screening GRU.
- Phần dưới giữ riêng kết quả đã quan sát, kiểm tra mã và nhánh chưa hoàn thành.

## 7. Audit các nhánh bổ sung trước khi đọc kết quả xác nhận

### ACcoding confirmation

Đã đọc `research/confirmation/confirmatory_study.py` cùng protocol và amendments 01–02. Không phát hiện lỗi quan trọng ở các đường dữ liệu đã kiểm tra:

- Cohort mới dùng hàm prefix không tự chia lại bằng hash cũ và được ép toàn bộ thành confirmation; kiểm tra không trùng bất kỳ người nào trong cohort pilot.
- Reference độ khó chỉ từ 1.054 người train ban đầu. Paired training control dùng difficulty của target đã cross-fit, lặp cùng target label cho H0/H1 và trọng số 0,5 cho mỗi phase.
- Scaler/model chỉ fit train; alpha chọn bằng NLL trên validation cũ. Model/reference và các lựa chọn được lưu trước khi hàm evaluate đọc file mới.
- H1 được đối chiếu với query thông thường của cùng frozen model; các contrast dùng cùng bộ bootstrap sinh viên.
- Khuyến nghị nhỏ về tái lập: khóa và kiểm tra hash của evaluator script/helper bên cạnh protocol, model và reference. Đây là tăng cường kiểm chứng phiên bản, không phải phát hiện label leakage.

Phase intercept là đối chứng task alignment. Mean update gần zero của nó không tự là phát hiện “học giả đã được sửa”; calibration ở hai phase có thể tạo tính chất đó theo cách mô hình được fit.

### CodeBench

Đã đọc `research/codebench_experiment/extract_events.py` và `fixed_future_probe.py` trước khi có bảng kết quả. Parser đọc text và dùng `ast.parse`, không thực thi code. GRADE có nhãn số được tách riêng khỏi missing; ERROR-mode là thay đổi outcome có ghi tên. Dữ liệu missing vẫn đi vào history, first submission được xác định trước khi lọc target label.

Strict-prior timestamp batches cùng điều kiện biên i0/i1/j không trùng timestamp làm H0/H1 đúng prefix. Snapshot code trong feature là code của nhóm submission trước, không phải code của target. Mapping `row_id` về prediction target và các phép bootstrap pair-weighted/equal-student-weighted được kiểm tra, chưa thấy lỗi quan trọng.

Giới hạn cần giữ:

- TEST của j có thể xảy ra sau H1 nhưng trước SUBMITION đầu của j. Target vì vậy là first submitted/graded outcome, không phải first execution hoặc một bài đánh giá chưa được tự kiểm thử.
- Training first rows trong những nhóm trùng timestamp còn dùng quy ước source-path/file-order; test boundary exclusion không tự giải quyết training sensitivity đó.
- Prior-code structural features không chứng minh code đã được sửa hoặc hiểu thêm; cần đối chiếu content change nếu claim repair.
- Student bootstrap không xác nhận generalization sang lớp/trường mới; các điều kiện lớp và nhiệm vụ có thể là bối cảnh chung cố định của tập quan sát.

### Recurrent baseline

Đã đọc `research/sequential/run_gru.py` và `protocol.md`. Unidirectional GRU dùng state trước response hiện tại, carry/detach qua cửa sổ TBPTT 128; padding không đổi các trạng thái hợp lệ trước đó. H0/H1 đúng indices và cùng query question. Vocabulary chỉ từ train; checkpoint theo validation first-attempt NLL. Protocol công khai optimizer loss được chuẩn hóa trong từng window, không đồng nhất với target-row weighting toàn tập.

Không phát hiện lỗi cơ bản về recurrent-state/label timing. Đã yêu cầu hai kiểm tra vận hành: chỉ mở confirmation bằng chế độ evaluate-only sau khi cả sáu checkpoint được đóng băng; so hash checkpoint với fit report. Unknown event embeddings là hai index không xuất hiện trong train nên giữ khởi tạo ngẫu nhiên; đây là giới hạn cho lịch sử chứa item chưa thấy, cần công khai hoặc sensitivity riêng, không âm thầm thay mô hình đã khóa. Đây là adapted GRU, không được ghi là tái lập DKT hoặc SOTA.

**Cập nhật trước confirmation:** agent đã giữ nguyên các run 5 epoch như exploratory và viết convergence amendment cho sáu fit mới: tối đa 30 epoch, patience 4 với min-delta 0,0001, giữ checkpoint có validation NLL nhỏ nhất thực tế; unknown event embeddings được đặt zero trước fit. Đã đọc phần code sửa: absolute-best checkpoint và patience-best tách đúng; ràng buộc confirmation chỉ evaluate-only cùng kiểm tra đủ sáu checkpoint hashes nằm trước lúc mở dữ liệu mới. Sửa mô hình này được công khai là amendment sau exploratory, trước confirmation; không được nhập lẫn với run ban đầu.

**Cập nhật integrity confirmation logistic:** một seal riêng lưu hash evaluator, baseline helper và validation lock trước evaluate; code đã kiểm tra các hash này cùng timestamp. Khuyến nghị tái lập ở trên đã được thực hiện mà không đổi thống kê hoặc tham số đã chọn.

## 8. Phản biện sau khi đọc kết quả ACcoding confirmation

Đã đọc trực tiếp `research/confirmation/results.json`. Validation lock có trước lúc mở confirmation cho modeling. Cohort mới gồm 1.500 người, 420.076 submissions; giữ 69.825 paired targets, bao phủ 83,82% episode nhiều lượt và 38,82% first-observed targets. Đây là student-disjoint confirmation trên cùng nguồn, không phải independent-platform validation.

| Predictor cố định | ΔNLL H1−H0 | CI 95%, student bootstrap 1.000 lần | Mean Δp |
|---|---:|---:|---:|
| Train mọi submission | −0,002099 | [−0,003262; −0,000829] | +0,049427 |
| Train first attempts — primary | −0,001566 | [−0,002300; −0,000756] | +0,024789 |
| Paired-target + phase control | −0,001416 | [−0,001842; −0,000971] | −0,000153 |

**Điều được củng cố:** có lợi ích dự báo nhỏ từ các quan sát thêm, và lợi ích còn tồn tại khi huấn luyện phù hợp với paired target. Trường hợp “retries chỉ gây nhiễu” không phù hợp với các kết quả tổng thể này.

**Điều về diễn giải được minh họa rõ:** dấu và độ lớn của mean probability update phụ thuộc readout/task/calibration. Paired-target control giữ lợi ích proper score trong khi mean update gần zero. Không được chuyển +0,0248 hay +0,0494 thành “tăng năng lực 2,48%/4,94%”. Nhưng near-zero của phase control cũng phần nào là hệ quả của fitting theo phase, nên không chứng minh đã tìm được true learning state.

Validation chọn alpha 0,5 cho all-submission, 0,75 cho first-attempt và 1 cho paired-target. Trên confirmation, shrinkage của first-attempt cải thiện NLL thêm −0,000418 so với full update, nominal CI [−0,000614; −0,000236]; paired-target không chọn shrinkage. Đây là một kết quả calibration nhỏ có đối chứng, **không đủ để giới thiệu shrinkage như phương pháp mới hoặc tốt hơn một cách tổng quát**. Không so các proper-score delta và mean-probability delta như cùng đơn vị.

Primary replication contrast đã được hỗ trợ trong population và pipeline đã khóa. Quyết định paper-ready vẫn là **chưa**: chưa xác nhận độ mới, external source không cho một positive replication rõ ở readout first-attempt, lợi ích screening nhỏ và phụ thuộc model/rule, và chưa có empirical policy-value evidence. Recurrent baseline hoàn chỉnh được bổ sung ở phần 13, hỗ trợ hướng predictive update nhưng không giải quyết các khoảng trống trên. Không được kéo dài danh sách thử đến khi tìm được một subgroup gây ấn tượng; các nhánh bổ sung phải ghi rõ exploratory hoặc được khóa trước outcomes.

## 9. CodeBench: hiệu ứng phụ thuộc nhiệm vụ huấn luyện và outcome

Đã đọc `research/codebench_experiment/results.md`, aggregate summary và kiểm tra ngữ nghĩa extraction. Full census có 105.052 SUBMITION với numeric grade và 48.879 không có grade nhưng có ERROR. Numeric grade thiếu không được âm thầm coi là sai; nhánh operational ERROR-failure là một outcome khác, có tên riêng. Có 471 user IDs trong archive, 467 có dated event và 466 có SUBMITION.

| Outcome / predictor | Pairs / test users | ΔNLL H1−H0 [CI 95%, 2.000 student bootstrap] | Mean Δp |
|---|---:|---:|---:|
| Numeric grade / history-all | 1.125 / 61 | −0,044019 [−0,073846; −0,012115] | +0,143429 |
| Numeric grade / history-first | 1.125 / 61 | −0,005277 [−0,016748; +0,006288] | +0,004619 |
| Numeric grade / prior-code-first | 1.125 / 61 | −0,008520 [−0,020518; +0,002683] | +0,007760 |
| ERROR-failure / history-all | 1.665 / 61 | −0,025970 [−0,052860; +0,001490] | +0,173261 |
| ERROR-failure / history-first | 1.665 / 61 | −0,001912 [−0,010907; +0,006398] | −0,001899 |

Đối chứng difficulty-only cho Δ đúng zero như kỳ vọng. Một sensitivity hậu nghiệm loại người có clock rollback giữ nguyên kết luận định tính về CI; phải giữ nhãn post hoc và kết quả chính, không đổi cohort chính sau khi xem outcome. Equal-student weighting đổi dấu mean Δp của numeric/history-first từ +0,004619 thành khoảng −0,001665; cả khoảng bất định đều gồm zero. Đây là minh họa về estimand/weighting, không là bằng chứng mean update thật bằng zero.

Không thể gọi đây là tái lập rõ một lợi ích first-attempt trên platform thứ hai: độ bất định còn lớn và các CI liên quan cắt zero. Cũng không được suy ra hai nguồn có hiệu ứng khác nhau một cách có ý nghĩa chỉ từ một nguồn có CI không cắt zero và nguồn kia có. Cần contrast giữa nguồn hoặc phân tích heterogeneity phù hợp nếu muốn phát biểu đó.

ALL-training tạo mean update và ΔNLL lớn hơn, đồng thời mức NLL H1 vẫn kém first-attempt training. Điều này phù hợp với khả năng khác biệt task alignment/calibration; **chưa nhận dạng nguyên nhân**. Không gọi chênh lệch đó là lượng false learning đã loại bỏ. Prior-code features chưa chứng minh giá trị gia tăng: H1 NLL của code-first không tốt hơn history-first trong các bảng hiện tại, và chưa có contrast cross-model đã khóa để kết luận.

442/1.125 numeric targets và 593/1.665 operational targets có TEST sau H1 nhưng trước SUBMITION đầu. Outcome là lần nộp đầu được quan sát, có thể đã tự kiểm thử; không phải bài đo năng lực hoàn toàn mới/chưa feedback. Hai định nghĩa nhãn giữ hai population khác nhau nên không diễn giải sự thay đổi metric giữa chúng như tác động nhân quả của ERROR.

## 10. Ứng dụng screening: lợi ích proper score chưa chuyển thành lợi ích quyết định rõ

Đã đọc `research/application/risk_screening.py`, protocol, threshold lock và `results_table.md`. Validation-only thresholds được khóa trước confirmation; quy tắc thứ nhất đạt 80% failure recall trên validation, quy tắc thứ hai giới hạn khoảng 30% workload trên validation. Threshold được chuyển nguyên sang confirmation, không đặt lại ngân sách bằng test outcomes. Student bootstrap ghép cặp đúng H0/H1 và có điều kiện trên mô hình cùng threshold cố định.

Ở first-attempt readout, quy tắc 80% recall cho Δworkload −0,016 điểm phần trăm [−0,167; +0,137] và Δfailure recall +0,046 điểm phần trăm [−0,143; +0,237]. Quy tắc 30% workload cho Δrecall +0,183 điểm phần trăm [−0,067; +0,457]. Đây chưa là bằng chứng rõ về lợi ích screening. Paired-target readout cũng không cho lift rõ ở hai quy tắc đó.

All-submission readout giảm workload 0,444 điểm phần trăm ở quy tắc 80% recall, nhưng đồng thời recall giảm 0,358 điểm phần trăm. Không gọi đây là cải thiện hiệu quả nếu chưa có utility/trade-off được xác định trước. Không dùng từ non-inferiority khi chưa định nghĩa margin và thiết kế kiểm định tương ứng.

Kết luận đúng là: **lợi ích proper score nhỏ được xác nhận không tự bảo đảm lợi ích ở các quyết định threshold đã khảo sát**. Đây là kết quả ứng dụng âm/không rõ có giá trị báo cáo; không phải lý do điều chỉnh threshold nhiều lần đến khi có lift. Screening dự báo nhãn factual của bài đã được chọn; nó vẫn không xác nhận tác dụng của trợ giúp hoặc khuyến nghị bài thay thế.

## 11. Temporal sensitivity: kiểm tra trước khi chạy

Đã đọc `research/confirmation/temporal_check.py` trước khi agent chạy. Cutoff lấy từ timestamp covariates của train users ban đầu; train được truncate trước xây feature và reference độ khó. First-observed flag của phần quá khứ được assert bằng full-history designation. Confirmation prefix được tạo trước time filtering, checkpoint times khôi phục từ episode đầy đủ; target ID map đúng sang row và H1 được đối chiếu prediction trực tiếp. Bootstrap vẫn paired theo sinh viên và pair-weighted.

Chưa phát hiện lỗi thời gian/index quan trọng trong đường đã kiểm tra. Quy tắc train ≤ cutoff và H0/H1 ≥ cutoff dùng biên bao gồm; target phải strictly after H1 chỉ loại tie ở biên successor, không tự loại mọi tie nội bộ. Đây là secondary exploratory check sau khi main confirmation đã xem, không phải đợt confirmation mới. Known-item support và temporal filtering đổi population nên không quy sự khác biệt metric với nhánh chính thành tác động thuần của chronological training.

**Kết quả đã đọc:** cutoff 27/10/2025; 103.285 first-attempt training rows trước cutoff; còn 2.291 paired targets từ 516 người confirmation. ΔNLL = −0,003895, nominal CI [−0,007585; −0,000100]; ΔBrier = −0,001845, CI [−0,003636; −0,000017]. Hướng hiệu ứng tương thích kết quả chính nhưng CI gần zero. Known-past-item support loại 11.130 candidate episodes thay vì 251 ở nhánh chính; time filtering giữ 3,89% số pairs đã qua known-past-item support. Kết quả vì vậy hỗ trợ một lát dữ liệu hẹp ở thời gian muộn hơn, không xác nhận generalization ra toàn bộ item bank/cohort tương lai.

Lần chạy đầu dừng trước predictions/metrics do Boolean `pd.NA` ở dòng đầu khi dựng episode boundary. Agent ghi `temporal_repair_01.json`, sửa initial boundary thành True rồi chạy tiếp với đúng cutoff/model/reference đã lưu và kiểm tra hashes. Đã đọc patch và metadata: đây là sửa lỗi triển khai không thay thống kê hoặc lựa chọn mô hình; không che lỗi này khỏi provenance.

### CodeBench: đối chứng paired-task trên partition còn lại

Đã đọc `paired_task_control.py` và `paired_task_results.md`. Nhánh này được chỉ định sau exploratory test nhưng trước đánh giá 74 validation users trước đó chưa dùng đo performance, trong đó 72 người đóng góp eligible pairs. Đây là expanded secondary holdout, không phải external dataset mới hay preregistration độc lập.

Difficulty tính từ split train gốc trước khi đổi partition mask để gom cặp; train features giữ cross-fit. Paired model dùng cùng Y ở hai phase, mỗi snapshot weight 0,5, và chỉ dùng train pairs. Hai model giữ cùng held-out target IDs; H1 khớp direct query; model contrasts/bootstrap ghép cặp theo người. Không phát hiện lỗi quan trọng trong các đường đã đọc.

Numeric outcome giữ 1.342 pairs: ordinary-first ΔNLL +0,002902 [−0,007076; +0,012731]; paired-phase ΔNLL −0,000630 [−0,005191; +0,004365]. ERROR-failure giữ 2.033 pairs: ordinary-first +0,003813 [−0,004577; +0,012206]; paired-phase +0,000609 [−0,002897; +0,004335]. Không có update CI nào cho lợi ích rõ ở holdout này.

Paired-task model có NLL tuyệt đối tốt hơn tại cả H0/H1: numeric contrast −0,008464/−0,011996; ERROR-failure −0,013790/−0,016994, với các nominal CI endpoint không cắt zero. Điều đó củng cố vai trò của task-aligned training; nó **không** chứng minh phase intercept riêng lẻ tạo cải thiện vì hai mô hình còn khác population/dòng huấn luyện. Contrast giữa update improvements cũng có CI cắt zero. Không lấy endpoint improvement làm bằng chứng incremental retry information hoặc chuyển thành latent learning gain.

## 12. Thí nghiệm tiếp theo có thể thay đổi phán quyết khoa học

Thêm nhiều kiến trúc không tự khôi phục novelty của protocol đã có prior art. Một câu hỏi thực chất hơn là: **code revisions có chứa thông tin dự báo bài sau vượt quá số lượt thử, kết quả đầu/cuối, thời gian và chất lượng snapshot cuối hay không?** Cần kiểm tra trực tiếp với Code-DKT và nghiên cứu code-edit đã có; đây là ứng viên nghiên cứu, chưa là claim mới.

Thiết kế tối thiểu đáng cân nhắc trên nguồn có snapshot đúng timestamp:

1. Giữ cùng pairs, future target và task-aligned training. Baseline nhận H0, target J, retry count, elapsed episode time, first/final result cùng tóm tắt outcomes trung gian; thêm đối chứng nhận representation snapshot cuối để không nhầm thông tin chất lượng code cuối với thông tin của quá trình sửa.
2. Predictor mở rộng nhận descriptors đã định trước của code changes, phân biệt identical-code resubmission và thay đổi thực. Mọi snapshot, feature và item relationship phải có trước query boundary; không dùng code/outcome của target.
3. Primary contrast là paired held-out log-loss của predictors được huấn luyện trên đúng input của chúng, với capacity/control và khoảng bootstrap theo người. Chọn practical-effect threshold hoặc operating point trước outcomes. Inference-only scrambling dễ tạo history phi thực nên không được dùng làm chứng cứ duy nhất.
4. Nếu có item content/skill mapping độc lập, kiểm tra prespecified related-vs-unrelated target contrast để phân biệt cơ chế dự kiến. Không suy relatedness từ nhãn thành công của test hoặc tự chọn nhóm có hiệu ứng lớn.

Kết quả dương chỉ xác nhận thông tin dự báo tăng thêm trong revisions, không xác nhận việc sửa code gây học. Kết quả âm phải có khả năng kết thúc cơ chế giả thuyết đó. Nếu thiếu snapshot đáng tin hoặc target assessment đủ độc lập, cần nguồn đo tốt hơn; không tích lũy mô hình trên cùng log để thay thế phần đo lường còn thiếu.

Thiết kế mới cụ thể hơn đã được đề xuất trong `trajectory_design_review.md`: cùng H1, M0 nuisance summaries, M1 thêm endpoints và endpoint-diff control, M2 thêm strictly intermediate code. Đây là một câu hỏi riêng cần source/holdout mới và protocol riêng; không đổi primary claim của các kết quả trước. Literature đối chiếu riêng nằm ở `research/literature/revision_information_gap.md`.

## 13. Recurrent baseline đã hoàn tất

Đã đọc `research/sequential/validation_converged/final_results.md`, checkpoint/confirmation locks và đường evaluate/export cuối. Sáu checkpoints được chọn chỉ bằng validation first-attempt NLL: ALL epochs 13/11/11, FIRST epochs 8/11/11, đều dừng theo convergence amendment. Checkpoint lock lúc 02:44 UTC có trước confirmation-run lock 02:45 UTC. Không chọn seed theo confirmation. Guard/hash checks và core recurrent timing đã đọc trước đó vẫn giữ nguyên; không phát hiện lỗi mới quan trọng.

| Mean-probability ensemble | H0 NLL | H1 NLL | ΔNLL [nominal 95% student CI] | Mean Δp |
|---|---:|---:|---:|---:|
| GRU ALL, seeds 11/29/47 | 0,594697 | 0,588198 | −0,006499 [−0,007939; −0,005156] | +0,016873 |
| GRU FIRST, seeds 11/29/47 | 0,596264 | 0,592048 | −0,004215 [−0,005637; −0,002781] | −0,002783 |

Cả sáu run có paired loss difference âm trên cùng 69.825 pairs/1.500 người; 2.464 pairs có unknown-item history dùng zero unknown embeddings. Ba seed chỉ cho mô tả variability hạn chế, không là estimator đầy đủ của uncertainty training. Ensemble losses được tính sau khi lấy mean probabilities, không đồng nhất với trung bình loss hoặc effect của các seed.

Kết quả củng cố hướng lợi ích dự báo trong một họ model tuần tự khác. **NLL tuyệt đối H1 của GRU vẫn kém logistic first/paired khoảng 0,57955/0,57903.** Không lấy Δ lớn hơn làm chứng minh GRU tốt hơn, không gọi đây là DKT reproduction hoặc SOTA. FIRST có mean probability update âm trong khi proper score cải thiện; đó tiếp tục cho thấy mean Δp và predictive value khác nhau, không xác nhận năng lực người học giảm hay tăng.

Nhánh này vẫn có future-J conditioning, horizon/task transport ở H0, selection theo episode/continuation và full-history cohort eligibility. FIRST chỉ đổi loss targets, không bỏ past retry events khỏi recurrent state. Không có code semantics hoặc policy-learning objective trong baseline này. Phần ứng dụng screening phải được đánh giá riêng bằng threshold đã khóa; direction của NLL không tự bảo đảm lift.

**Screening GRU đã hoàn tất:** tại threshold được chọn cho 30% validation workload, GRU FIRST tăng failure recall 0,694 điểm phần trăm, nominal CI [+0,336; +1,057], đồng thời actual workload tăng 0,102 điểm phần trăm [−0,141; +0,337]. GRU ALL tăng recall 0,350 điểm phần trăm [+0,005; +0,704], workload −0,083 [−0,313; +0,158]. Đây là bằng chứng về gain nhỏ trong các pipeline/rules cụ thể, cần bổ sung vào kết luận logistic ở phần 10; không được tiếp tục viết rằng mọi screening contrast đều không rõ.

CI workload cắt zero không chứng minh hai workloads bằng nhau. Ở quy tắc 80% validation recall, workload giảm khoảng 0,62 điểm phần trăm, nhưng uncertainty/trade-off của recall vẫn phải báo và chưa có non-inferiority margin định trước. Các contrast có điều kiện trên trained models/thresholds và chưa hiệu chỉnh nhiều phép so sánh. H1 của GRU chưa được chứng minh vượt logistic screening controls hoặc cải thiện educational intervention; một within-GRU gain không phải superiority claim.

## 14. Phép thử intermediate CODE trên source mới đã hoàn tất

Thiết kế, audit trước lock và kết quả nằm trong `trajectory_design_review.md`; phán quyết xuyên các nhánh nằm trong `scientific_readiness_addendum.md`. M0/M1/M2 cùng queried H1, cùng next-first-submission target và cùng pairs; đây là cross-model nested-input contrast, không phải thêm một H0→H1 update contrast.

Sau 3.906 training pairs và 208 calibration pairs, test gồm 274 targets/28 người mới trong archive 2016-2. Primary calibrated M2−M1 NLL = −0,001094 [−0,006666; +0,004346]. CI chứa zero và cả ngưỡng cải thiện −0,005 đã khóa. Không có benefit hoặc equivalence conclusion. Equal-student, raw và endpoint-redundant controls đều không xác nhận rõ path gain. Các representations hữu hạn và target là recorded operational grade; không đo latent learning hoặc raw conditional mutual information.

Kết quả này làm phép thử giả thuyết cụ thể và tái lập được, nhưng chưa mang lại cơ chế dương đủ mạnh để thay phán quyết paper-ready. Giữ kết quả không rõ này trong bản thảo, không mở thêm nhánh trên test đã xem. Hướng phù hợp hiện tại là empirical audit có giới hạn; không tuyên bố một revision-aware algorithm mới đạt SOTA.
