# Đề 4 với dữ liệu tự tìm: quyết định và triển khai nghiên cứu

Mốc nghiên cứu: **26/09/2026**. Cập nhật sau khi người dùng xác nhận thầy không cung cấp dataset. Dự án phải tự tìm toàn bộ dữ liệu; không có thử nghiệm trên sinh viên thật; mục tiêu là bài báo nghiên cứu.

**Trạng thái:** tài liệu này lưu khảo sát dữ liệu và các pilot ban đầu. Bộ thực nghiệm mở rộng, bản thảo và đánh giá tính mới hiện hành nằm trong [báo cáo nghiên cứu](paper/BAO_CAO_NGHIEN_CUU.md). Mô phỏng ban đầu chỉ là kiểm tra diễn giải, không phải đánh giá policy đã học hay bằng chứng khuyến nghị cải thiện học tập; không gán reward bị cắt phần âm của toy cho ExRec gốc.

## 1. Quyết định đã thay đổi như thế nào

Giữ hướng đề 4, nhưng loại bỏ giả định dữ liệu nội bộ sẵn có. Nền tảng triển khai là **log lập trình có thể tải và kiểm toán trực tiếp**, kèm mô phỏng có ground truth để kiểm tra tính đúng đắn của mục tiêu mà policy tối ưu.

Tên nghiên cứu làm việc:

> **Auditing Student-Model Updates for Offline Programming Exercise Recommendation.**

Phần “optimizing” chỉ đưa vào tên cuối nếu thực nghiệm chứng minh cơ chế khắc phục có lợi ích rõ. Một bài đo lường và đánh giá có phát hiện quan trọng cũng là nghiên cứu thật; không cần gắn một kiến trúc lớn trước khi xác minh failure mode.

Tên trung tính này phù hợp với kết quả pilot: thông tin nộp lại có ích cho dự báo trong các phép thử đã chạy. Chưa có căn cứ đặt kết luận “repair bị nhầm thành learning” vào tên bài như một phát hiện đã được xác nhận. Giả thuyết sai lệch reward/quyết định vẫn được kiểm tra, cùng khả năng nó không xuất hiện.

Câu hỏi chính: **reward hoặc mô hình người học nào nhầm thành công sửa bài với việc học, sự nhầm lẫn ấy ảnh hưởng lựa chọn bài ra sao, và kiểm tra nào nhận ra được điều đó?**

Tính mới chưa được chứng nhận. Code-DKT đã bàn về general knowledge so với closeness-to-solution; REM đã đánh giá nhiều simulator; các nghiên cứu 2026 đã có uncertainty và multi-state KT. Đóng góp phải nằm ở đặc tả, bằng chứng mới về sai lệch quyết định và biện pháp xử lý có đối chứng, không phải chỉ đổi tên các module.

## 2. Kết quả tìm và kiểm tra truy cập dữ liệu

| Nguồn | Truy cập thực tế | Vai trò phù hợp | Giới hạn đã biết |
|---|---|---|---|
| **CodeBench 1.81, học kỳ 2016-1** | Đã tải file chính thức `174,487,574` byte | Nguồn chính cho quá trình làm bài: code, execution, IDE events, bài tập/thi, thời gian | Trang nguồn chưa thấy giấy phép chuẩn rõ ràng; không mặc định có đề bài đầy đủ hoặc KC tags. Audit archive được lưu riêng |
| **ACcoding, Zenodo record 11395043** | Đã tải `96,056,846` byte; đối chiếu MD5 của Zenodo | Nguồn lớn để kiểm tra lịch sử người học qua nhiều bài, verdicts, thời gian, tags/difficulty nếu hợp lệ | Không có toàn bộ source code; không thay thế được CodeBench cho code-edit modeling. Record title là v2.0.0; API không khai báo version riêng |
| **CodeInsight** | HF công khai card nhưng `gated=manual`; endpoint đọc dữ liệu trả 401 khi không được cấp quyền | Nguồn đối chiếu rất sát nếu có quyền trong tương lai | Phải có chấp thuận theo giấy phép khoa; không nằm trên đường triển khai bắt buộc |
| **FalconCode** | Bản gốc theo yêu cầu; bản HF cũng gated | Mở rộng sang Python với rich metadata | Chưa có quyền/file dữ liệu; không tính là dataset đã sở hữu |
| **CodeWorkout/CSEDM** | Bản gốc DataShop cần tài khoản/điều kiện sử dụng | Benchmark quen thuộc cho KT | Bản processed từ repo tác giả không tự chứng minh quyền tái phân phối hay giữ đầy đủ attempts |
| **ASSISTments: A Bandit You Can Trust** | Đã đọc metadata, schema và data terms công khai; chưa tải log người học | Nguồn bổ trợ về logging policy trong giáo dục | Action là video hỗ trợ toán; chưa xác minh được propensity đầy đủ từ schema |
| **RoboMission 2019-12** | README và link Drive của tác giả được xác minh; chưa tải log | Ứng viên về chương trình MiniCode và edit/execution events | Chưa xác minh giấy phép riêng của dữ liệu; không có propensity/candidate set trong schema |

Nguồn sơ cấp: [CodeBench](https://codebench.icomp.ufam.edu.br/dataset/), [ACcoding record](https://zenodo.org/records/11395043), [ACcoding data paper](https://www.nature.com/articles/s41597-024-03392-z), [CodeInsight card](https://huggingface.co/datasets/CodeInsightTeam/code_insights_csv), [FalconCode paper](https://doi.org/10.1145/3545945.3569822), [DataShop terms](https://pslcdatashop.web.cmu.edu/Terms), [ASSISTments OSF](https://osf.io/zuwf7/), [RoboMission README](https://raw.githubusercontent.com/adaptive-learning/adaptive-learning-research/master/data/robomission-2019-12/README.md).

File công khai tải được và quyền phân phối lại là hai thuộc tính khác nhau. Báo cáo ghi điều kiện của từng nguồn; hiện chưa có thao tác đăng tải/chia sẻ lại raw data. ACcoding paper 2024 mô tả CC-BY-4.0 cho bản v1, trong khi metadata record v2 hiện ghi `other-open`; không tự chuyển kết luận giấy phép giữa các phiên bản. Các manifest giữ bằng chứng này để kiểm tra trước khi công bố gói dữ liệu hoặc notebook chứa raw records.

## 3. Dữ liệu thực sự chứa gì

**ACcoding** có bảng `out_submissions` với:

`id, lang, result, score, time_cost, memory_cost, code_length, detail, created_at, creator_id, problem_id, contest_id`.

`result` có các giá trị AC, WA, CE, TLE, MLE và những trạng thái khác. Không gộp WT/JG (đang chờ/chấm) thành thất bại đã xác định. Trường `detail` có thể có diagnostics và đoạn trích nhưng không phải kho source code đầy đủ. Schema không cung cấp test inputs/outputs hoặc kết quả từng test.

Bảng problem có difficulty, access level, test settings, thời điểm cập nhật; bảng tags có nhãn và liên kết có trọng số. Vì metadata difficulty/tag có thể là snapshot cập nhật sau tương tác, sử dụng chúng như feature online phải được audit theo thời gian; baseline ban đầu có thể ước lượng item difficulty từ training để tránh giả định ngầm.

Kiểm kê trực tiếp archive ACcoding hiện tại thu được **2.181.602 submissions, 9.866 người học có submission và 4.301 bài có submission**. Trong đó **2.137.950 submissions dùng C, khoảng 98,0%**. Khoảng thời gian thực trong bảng là **02/01/2024–30/12/2025**. Metadata mô tả “as of May 12, 2025” không khớp ngày lớn nhất; báo cáo giữ cả hai bằng chứng và dùng khoảng thời gian quan sát được cho thí nghiệm. Không lấy số 4.046.652 submissions của paper bản cũ làm quy mô của archive này.

Đã tạo cohort tái lập gồm **1.500 người học, 424.311 submissions, 2.768 bài**: chọn bằng SHA-256 cố định từ 7.634 người học có ít nhất 20 bài khác nhau, rồi giữ toàn bộ lịch sử của họ. Cohort này ưu tiên người học hoạt động đủ nhiều, nên chưa đại diện cho người ít hoạt động hoặc bỏ học sớm. `submissions_cohort.csv` có 20.596.768 byte; manifest và hash lưu trong `research/accoding/`.

**CodeBench** tổ chức theo học kỳ, lớp, người học, bài đánh giá và bài lập trình. Có các thư mục code, CodeMirror events, executions, grades và assignment descriptors. Phải kiểm tra file thật để xác định bản code nào tương ứng thời điểm nào. Code cuối bài không được dùng để dự báo một quyết định trước đó. Snapshot hoặc quá trình tái dựng code từ events cần được kiểm tra, đặc biệt khi IDE log không đầy đủ.

Kiểm kê toàn archive học kỳ 2016-1 xác nhận **471 user ID duy nhất, 535 lượt ghi danh người–lớp, 9 lớp và 235 ID bài tập**; có **29.991 tệp code `.py`**, cùng số tệp execution và editor log. Execution log chứa **321.722 sự kiện có timestamp**, gồm 167.791 TEST và 153.931 SUBMITION (giữ nguyên cách viết của nguồn). Có 136 assessment descriptors: 75 homework, 61 exam. Ba assessment mẫu ghi Python 3.

Ba chi tiết ảnh hưởng trực tiếp protocol: (1) timestamp chạy từ **25/05/2016 đến 02/10/2017**, vượt nhãn học kỳ; (2) phải split theo user ID, không theo lượt ghi danh; (3) **48.879 sự kiện SUBMITION, khoảng 31,75%, chưa có trường GRADE được parse**, nên không được tự gán chúng bằng 0. Trang giới thiệu ghi 30.140 code và 322.500 sự kiện, khác archive đo trực tiếp; nguyên nhân chưa được xác định. Hash, inventory, parser và các định nghĩa đếm đã lưu để kiểm chứng.

Chưa có căn cứ coi bất kỳ nguồn chính nào có randomized next-exercise assignment và propensity chính xác. Chúng hỗ trợ nghiên cứu dự báo và mô hình hóa, cùng kiểm tra độ bền trong mô phỏng; causal OPE phải là nhánh có điều kiện riêng.

## 4. Phân công bằng chứng giữa các nguồn

### Nhánh thực nghiệm chính: CodeBench

Đo mức liên hệ giữa lịch sử sửa bài và outcome tương lai ở bài khác. Bắt đầu một học kỳ để kiểm tra parser; thiết kế cuối cần nhiều học kỳ/lớp. Có thể so homework và exam nếu semantics của trường dữ liệu được xác minh, nhưng điểm thi quan sát vẫn chịu selection và confounding.

CodeBench cung cấp quá trình lập trình Python; ACcoding có log chủ yếu bằng C. Vì vậy đề tài vẫn có dữ liệu C sát danh sách gốc, nhưng phân tích biểu diễn code hiện dựa vào Python. Không gộp lợi ích của ngôn ngữ, cách chấm và khác biệt trường/lớp thành một kết luận chuyển miền duy nhất. Chuyển encoder giữa C/Python đòi hỏi dữ liệu có source code tương ứng và là nhánh riêng.

### Nhánh kiểm tra tính tổng quát: ACcoding

Dùng lịch sử submission và trạng thái lỗi để kiểm tra hiện tượng first-attempt so với retries ở quy mô lớn. Không gọi đây là tái lập đầy đủ một mô hình code-aware nếu source code không tồn tại. So các phương pháp trên cùng phần thông tin chung, rồi báo riêng giá trị gia tăng của code trong nguồn có code.

Trong ACcoding, “nộp lại” chưa chứng minh code đã được sửa: có thể nộp lại cùng chương trình hoặc đổi điều kiện khác. Để đo repair theo nội dung chương trình, phải đối chiếu snapshot/diff trong CodeBench; verdict và code length không thay thế được bằng chứng đó.

### Nhánh ground truth: thế giới được kiểm soát

Cho phép thay đổi độc lập knowledge transition, local repair, observation noise và selection policy. Đây là nơi xác định được policy nào thực sự kém theo mục tiêu đã đặt. Trên log không có phản thực thật, chênh lệch giữa evaluator chỉ được gọi là bất đồng, không mặc nhiên là sai thứ hạng.

## 5. Thí nghiệm chẩn đoán đã chạy

Đã tạo và chạy `research/diagnostics/reward_audit.py`, xuất CSV/JSON cho **45 tổ hợp**: 5 cấu hình thế giới × 3 prior × 3 objective; mỗi lượt quyết định có horizon 4. Mọi nhánh được liệt kê, dùng số thực và cache belief làm tròn 12 chữ số; không dùng Monte Carlo.

Các thước đo khác nhau:

- Số lần trả lời thành công.
- Tổng thay đổi posterior có dấu.
- Tổng phần tăng dương của posterior.

Với prior 0.4, thế giới không có học vẫn cho positive-only posterior return xấp xỉ **0.348** sau bốn bước, trong khi expected true mastery gain bằng **0**. Ở thế giới sửa bài mà không học, policy tối ưu thành công đạt expected success rate **0.87**; một evaluator được cố tình đặc tả sai báo gain khoảng **0.486**, dù true gain vẫn bằng 0.

Đây là các phản ví dụ được xây có chủ đích. Policy trong code dùng thông tin oracle; evaluator sai chỉ chấm lại trajectory. Không diễn giải chúng thành bằng chứng một policy học được đã khai thác simulator, hoặc một phương pháp công bố mắc đúng lỗi này. Muốn có kết quả bài báo phải huấn luyện các model/policy từ dữ liệu hữu hạn, so baseline thực và kiểm tra ngoài họ môi trường tối ưu.

Kiểm tra độc lập bằng liệt kê latent-state trajectories khớp evaluator trên cả 45 tổ hợp, sai lệch số học tối đa khoảng `1.33e-15`. Kết quả này xác minh triển khai toy experiment, không xác nhận tính đúng của mô hình giáo dục ngoài đời.

## 6. Protocol thực nghiệm trên log thật

Đơn vị dự báo là một submission sắp xảy ra. Chỉ dùng lịch sử trước timestamp của nó. Không dùng result, code_length hoặc source code của chính submission target để làm feature cho bài toán lựa chọn bài trước khi người học trả lời.

**Bài mới đối với sinh viên** và **bài chưa xuất hiện trong training** là hai điều kiện khác nhau. Khi thiếu đề bài hoặc mô tả nội dung, target chính khả thi là bài mới đối với sinh viên nhưng có lịch sử trong training; không tuyên bố content-based cold-item generalization. Bài chưa thấy được báo riêng với backoff và độ phủ.

Pilot ban đầu dùng split theo người học, history-only baseline và baseline thêm tín hiệu cùng bài. Item difficulty được fit từ training; features theo người học được cập nhật theo prefix trong split tương ứng. Outcomes được báo riêng cho first encounter và repeat attempt. Không lấy chênh lệch AUC giữa hai nhóm khác phân phối làm chứng minh nhân quả hoặc proof of learning.

Thiết kế đầy đủ phải có:

1. Student-disjoint và temporal/cohort holdout, với phương pháp chọn cohort định trước.
2. History-only, first-attempt-only, counts/time, last response, code-aware và capacity-matched baselines.
3. AUC khi hai lớp đều có; Brier/NLL/calibration; confidence intervals theo sinh viên.
4. Missingness, duplicate/rejudging/timestamp ties, người học quay lại bài cũ, language switching và contest context.
5. Các ablation tách lợi ích của thêm thông tin khỏi lợi ích kiến trúc.
6. Một test set chưa dùng để điều chỉnh câu chuyện giả thuyết sau pilot.

Pilot là phép kiểm tra khả năng khai thác dữ liệu và pipeline. Nếu baseline đơn giản cho kết quả tốt, đó là chuẩn đối chứng cần vượt; không phải bằng chứng đã đạt SOTA hay lý do loại phương pháp mạnh khỏi nghiên cứu.

### 6.1. Pilot ACcoding đã chạy xong

Đã fit ba logistic regression cố định, không tìm siêu tham số: chỉ độ khó bài, độ khó + lịch sử người học, và thêm lịch sử cùng bài. Split SHA-256 theo người học cho **1.054 train / 212 validation / 234 test**; validation được giữ lại, chưa dùng để chọn mô hình. Test có **64.371 submissions**. Độ khó bài dựa trên first attempts của training users, cross-fit theo người trong train; 139 test submissions thuộc bài chưa thấy trong train được dùng backoff. Không dùng kết quả, điểm hay code của submission hiện tại làm feature.

| Nhóm test | Số lượt | AUC: chỉ độ khó | AUC: lịch sử | AUC: thêm cùng bài | Chênh AUC thêm cùng bài; khoảng bootstrap 95% |
|---|---:|---:|---:|---:|---:|
| Toàn bộ | 64.371 | 0,7073 | 0,7286 | 0,7333 | +0,00470 [0,00393; 0,00536] |
| Bài lần đầu được quan sát ở người học | 27.868 | 0,7570 | 0,7687 | 0,7698 | +0,00117 [0,00074; 0,00169] |
| Nộp lại | 36.503 | 0,6301 | 0,6603 | 0,6697 | +0,00939 [0,00787; 0,01080] |
| Nộp lại trước lần AC đầu tiên | 33.187 | 0,6256 | 0,6471 | 0,6490 | +0,00191 [0,00146; 0,00257] |

Log loss toàn bộ giảm từ **0,59612 xuống 0,59311**, Brier giảm từ **0,20424 xuống 0,20288**. Khoảng trên dùng 100 lần paired bootstrap theo sinh viên, là kết quả thăm dò và chưa điều chỉnh nhiều phép so sánh. Chúng có điều kiện trên mô hình đã fit và một split cố định, không gồm bất định do huấn luyện lại hoặc chọn cohort. Điểm dự báo vẫn có trọng số theo lượt nộp, không phải mỗi người trọng số bằng nhau.

**Kết luận đúng mức:** dữ liệu và pipeline chạy được; lịch sử cùng bài cho lợi ích dự báo nhỏ; mức tăng trên nhóm nộp lại giảm khi loại lượt sau AC. Chưa có bằng chứng từ pilot này về learning gain giả, sai thứ hạng policy hoặc ưu thế phương pháp mới. Ở first-attempt, các feature cùng bài đều là giá trị mặc định; chênh lệch nhỏ đến từ việc fit lại hệ số chung, không phải bằng chứng tín hiệu cùng bài đã chuyển sang bài mới.

Baseline này dự báo kết quả chấm tại thời điểm submission và biết khoảng cách thời gian đến submission đó. Nó không phải policy lựa chọn bài ở thời điểm trước đó. Non-AC gồm cả một số loại lỗi thực thi/hệ thống nên target là kết quả chấm vận hành, không phải nhãn năng lực chuẩn. Có 205 cặp kề nhau cùng giây, tương ứng 392 dòng thuộc nhóm trùng thời gian; sắp theo ID chỉ là quy ước chưa xác minh thứ tự dưới giây. Đánh giá đầy đủ cần sensitivity loại nhóm trùng thời gian hoặc cập nhật cả nhóm cùng lúc.

Script, phiên bản môi trường, coefficients, mọi metric và confidence intervals: `research/pilot/first_vs_retry.py`, `metrics.csv`, `pilot_summary.json`, `README.md`. Đã kiểm tra prefix invariance trên dữ liệu giả: thay nhãn hiện tại không làm thay feature của chính nó hoặc các feature trước nó; nhãn test không làm thay feature train.

### 6.2. Kiểm định cùng một outcome tương lai

Đã chạy thí nghiệm giữ cố định một bài tương lai `j`, dự báo nó từ `H0` sau lần nộp đầu và `H1` sau lần nộp cuối của một đoạn liên tục làm bài `i`. Chỉ nhận `j != i` và first observed attempt của người học trên `j`. Mô hình đã fit được đóng băng; loại feature thời gian target khỏi cả training và hai dự báo. So paired NLL/Brier trên **chính cùng outcome**, thay vì lấy AUC hai nhóm khác nhau làm chứng cứ transfer.

Phải giữ cả đoạn kết thúc AC lẫn chưa AC, báo số episode không có outcome tiếp theo, và thừa nhận chọn mẫu theo người tiếp tục học. Danh tính bài `j` được điều kiện hóa sau khi quan sát log; đây chưa phải một bài kiểm tra policy biết chọn bài đúng. Nếu dự báo sau retries tốt hơn, kết quả chống lại cách kể đơn giản rằng retries chỉ gây nhiễu; nếu tệ hơn, kết quả chỉ ra vấn đề cập nhật dự báo trên outcome này, chưa chứng minh người học không học.

Trong 12.793 episode có ít nhất hai submissions, loại 117 không có episode tiếp theo quan sát được, 1.703 có bài tiếp theo đã gặp trước đó và 23 có bài chưa xuất hiện trong train. Còn **10.950 cặp cùng outcome của 233 người học**, bao phủ 85,59% episode nhiều lượt và 39,29% first-attempt targets ở test. Có 2.473 episode kết thúc chưa AC; chúng vẫn được giữ. Censoring và item-selection bias chưa được giải quyết bởi việc báo coverage.

Hai mô hình có cùng bảy feature và cấu hình logistic, đều đóng băng; khác tập dòng dùng huấn luyện. Cả hai được báo, không chọn mô hình chỉ vì hướng kết quả thuận lợi.

| Tập huấn luyện | NLL trước → sau | ΔNLL; bootstrap 95% | Brier trước → sau | ΔBrier; bootstrap 95% |
|---|---:|---:|---:|---:|
| Mọi submission train, 295.788 dòng | 0,58881 → 0,58566 | −0,00315 [−0,00655; +0,00021] | 0,20192 → 0,20026 | −0,00166 [−0,00325; −0,00017] |
| Chỉ first attempts train, 127.005 dòng | 0,58015 → 0,57764 | −0,00251 [−0,00457; −0,00034] | 0,19857 → 0,19738 | −0,00120 [−0,00213; −0,00031] |

Delta là sau trừ trước; âm nghĩa là dự báo tốt hơn. Bootstrap 100 lần theo người, có điều kiện trên mô hình cố định; kết quả exploratory, chưa hiệu chỉnh nhiều phép so sánh. Với mô hình huấn luyện trên mọi lượt, khoảng ΔNLL chứa 0; với mô hình first-attempt, hai proper scores cải thiện nhỏ theo các khoảng này.

Xác suất dự đoán trung bình tăng lần lượt **0,05041 và 0,02520**. Đây là cập nhật dự báo phụ thuộc cách huấn luyện, **không phải mức tăng tri thức 5,04% hay 2,52%**. Kết quả hiện tại cho thấy thông tin từ nộp lại có thể hữu ích cho outcome bài khác; chưa chứng minh failure mode hoặc hiệu quả policy. Không gắn nhãn mô hình sai chỉ vì posterior thay đổi nhiều hơn mức thay đổi của proper score: hai đại lượng khác đơn vị và mục đích.

Đã kiểm tra cùng difficulty đích, nhãn/time tương lai không làm đổi feature, thêm sự kiện tương lai không làm đổi cặp cũ, và dự báo H1 khớp chính xác dự báo thông thường của mô hình tại target. Có rà soát độc lập biên thông tin. Kết quả đầy đủ: `research/fixed_probe/summary.json`, `first_attempt_summary.json`, hai CSV tổng hợp và script; không xuất dự báo định danh từng người.

Tập test của pilot đã được xem trong quá trình nghiên cứu và phải được coi là exploratory. Đánh giá xác nhận cuối cần khóa protocol trước khi mở cohort/học kỳ độc lập khác; không dùng lại các số này như một test chưa từng được xem.

## 7. Những phát biểu được và chưa được phép

| Bằng chứng | Phát biểu hợp lệ | Phát biểu chưa được hỗ trợ |
|---|---|---|
| File thực + checksum + schema | Có dữ liệu để tái lập bước xử lý | Đã có toàn bộ dữ liệu cần cho mọi mô hình |
| Held-out prediction | Dự báo outcome quan sát được tốt hơn theo protocol | Giao bài này gây tăng kiến thức |
| Null/synthetic worlds | Failure mode tồn tại dưới giả định cụ thể | Sinh viên thật có cùng transition |
| Cross-simulator comparison | Policy nhạy hoặc bền trong tập evaluator đã chọn | Policy chắc chắn tốt hơn ngoài đời |
| OPE có support và assumptions | Giá trị ước lượng có điều kiện và uncertainty | Propensity estimate tự khử mọi confounding |

## 8. Các mốc nghiên cứu tiếp theo

Mốc dữ liệu, parser, baseline dự báo ACcoding và kiểm tra reward trong thế giới kiểm soát đã hoàn tất ở quy mô pilot. Bài báo đầu nên tập trung vào **kiểm định cập nhật trạng thái và độ nhạy quyết định**, trước khi nhận thêm nhiệm vụ xây một họ robust RL.

Chuỗi bằng chứng cần hoàn thành là: **retry evidence → cập nhật dự báo cùng bài tương lai → thay đổi action của một recommender cụ thể → thay đổi return**. Hai bước đầu kiểm tra được trên log; thay đổi action chỉ chứng minh độ nhạy quyết định. Bước cuối cần thế giới ground truth hoặc thiết kế can thiệp đủ điều kiện để gọi quyết định tốt/xấu. Không suy trực tiếp từ tăng AUC sang cải thiện khuyến nghị.

Sau pilot: tái lập đúng một objective/recommender gần nhất, ưu tiên ExRec vì sát KT + recommendation, kiểm tra công thức reward thật; chọn tập bài khả dụng và ngân sách chung; huấn luyện policy thật từ dữ liệu hữu hạn trong thế giới đã biết; đo regret dưới repair/learning và model misspecification. Chỉ sau khi xác minh failure mode mới đánh giá cách khắc phục bằng objective, tách trạng thái hoặc ràng buộc uncertainty. Kiểm tra nhiều lớp/học kỳ, ablation và ngoài họ simulator là phần bắt buộc để nâng kết quả vượt mức minh họa.

Nếu kết quả không xác nhận failure mode trên benchmark thật, phải đổi giả thuyết hoặc thu hẹp kết luận. Không giữ một câu chuyện “repair gây học giả” chỉ vì toy example chứng minh nó có thể xảy ra.

## 9. Vị trí các kết quả tái lập

- `research/codebench/`: mã kiểm toán, inventory và manifest của archive chính thức.
- `research/accoding/`: schema, mã kiểm toán, manifest và thống kê cohort.
- `research/assistments_bandit/`: nguồn bổ trợ, schema và điều kiện dùng; không phải empirical log dataset đã tải.
- `research/diagnostics/`: toy-world script, assumptions, CSV và kết quả kiểm tra reward.
- `research/pilot/`: pilot dự báo ACcoding đã chạy hoàn tất, kèm số liệu và bootstrap.
- `research/fixed_probe/`: kiểm định dự báo cùng outcome trước/sau episode sửa bài.
- `data/raw/`: archive gốc; `data/processed/`: bảng phục vụ thí nghiệm. Chưa đăng tải lại dữ liệu.

Không có kết quả huấn luyện mô hình lớn hay so sánh SOTA hoàn chỉnh trong báo cáo này. Giá trị của bước triển khai hiện tại là biến hướng nghiên cứu thành nguồn dữ liệu kiểm tra được, protocol có thể chạy và giả thuyết có thể bác bỏ.
