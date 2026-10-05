# Phán quyết khoa học sau toàn bộ các nhánh đã khóa

Ngày 26/09/2026. Phạm vi: ACcoding pilot/confirmation/temporal; CodeBench 2016-1 probes và paired-task control; adapted GRU và screening; CodeBench 2016-2 intermediate-code experiment. Đây là nhận xét độc lập về bằng chứng, không là cam kết acceptance hay bản thảo của tác giả.

**Có một chương trình nghiên cứu tái lập và một working manuscript trung thực. Chưa có bằng chứng đủ mạnh để tự nhận SOTA hoặc một đóng góp phương pháp lớn sẵn sàng Q1/Q2/A*.** Một empirical audit có thể có giá trị; khả năng công bố còn phụ thuộc độ mới chính xác, phạm vi venue, diễn giải, chất lượng đo lường và kiểm chứng của tác giả con người.

## Những phát biểu hiện có thể bảo vệ

- Trên selected active-user population ACcoding, thêm recorded submissions cải thiện modest paired future-outcome prediction ở logistic, paired-target logistic và adapted GRU. Đây là student-disjoint confirmation trên cùng platform/period, không là causal transfer-learning effect.
- Mean probability revision thay đổi đáng kể theo training task/readout/calibration, thậm chí khác dấu khi proper loss cùng cải thiện. Không thể coi dấu/độ lớn của mean Δp như lượng kiến thức tăng/giảm. Đối chứng phase có một phần tính chất này do cách fit; không là thuật toán đo true mastery.
- CodeBench first-attempt và paired-task update effects còn bất định. Paired-task training cải thiện absolute forecasts trên holdout riêng; nó không xác nhận incremental evidence gain hay tác động của phase intercept riêng lẻ.
- Ở quy tắc screening validation-30%-workload, adapted GRU FIRST tăng recall 0,694 điểm phần trăm [0,336; 1,057], với actual workload tăng 0,102 điểm phần trăm [−0,141; 0,337]. Đây là gain nhỏ theo rule/pipeline cụ thể; workload không được giữ đúng bằng nhau. Không xác nhận tutor intervention hoặc exercise policy hiệu quả hơn.
- Phép thử intermediate CODE mới chưa kết luận được: calibrated M2−M1 NLL −0,001094 [−0,006666; +0,004346], 274 targets/28 người. CI chứa cả zero và ngưỡng −0,005. Không xác nhận lợi ích, không chứng minh không có lợi ích, không chứng minh revisions không tạo học.

## Điều kết quả không giải quyết

Prior art đã có repeated-attempt aggregation, first-attempt/code-aware forecasting, fixed-future-target evidence evaluation, behavior-aware KT, và mastery-boundary reliability checks. Các nguồn gần đã được đọc ở nhiều mức truy cập và phân biệt rõ full text/abstract/metadata. Chưa thấy exact conjunction của nhánh M0/M1/M2 qua targeted search không bảo đảm chưa có nghiên cứu tương tự.

Các logs chỉ có outcome của trajectory thực tế. Future item J, việc tiếp tục học, grade observability, source-end stopping và eligible cohort đều có chọn mẫu. Các dự báo không tạo counterfactual outcome cho bài không được chọn. Thời gian ghi submission/CODE chưa xác minh đồng nhất với thời gian feedback sẵn sàng hoặc snapshot thực sự được grader chạy. Identical text hoặc AST không là no-learning control hay bảo đảm cùng execution outcome.

Bootstrap hiện có điều kiện trên pipeline, training split và tập lớp/platform quan sát. Nó không bao gồm đầy đủ training/cohort uncertainty, class dependence hoặc external population shift. Nhánh mới 28 người đủ để chạy một kiểm tra có thể bác bỏ, nhưng độ bất định thực tế chưa giải quyết câu hỏi cơ chế. Không chữa điều này bằng diễn giải CI cắt zero thành equivalence.

## Khuyến nghị đối với bản thảo

1. Đặt claim chính ở **empirical validity audit** với modest predictive benefit và task-alignment controls; giữ nhánh code-path inconclusive như một phép thử có giới hạn. Không đổi title/abstract thành thuật toán intermediate-code mới sau kết quả này.
2. Phân biệt ba tasks: early-versus-late readout; cross-model task-aligned fitting; H1-only nested code-input experiment. Các delta có estimand khác nhau, không gộp thành một average effect hoặc một bảng xếp hạng SOTA.
3. Báo point losses và operating points, không chỉ favorable deltas. GRU có within-model gains nhưng H1 NLL không vượt simple logistic; M0 có point NLL tốt trong code-path experiment nhưng không có superiority conclusion.
4. Giữ provenance của pilot-consumed holdout, amendments, secondary temporal/CodeBench analyses, pre-metric repairs và prior-art discovery. Local timestamp/hash locks hỗ trợ audit, không đồng nghĩa external preregistration.
5. Bước tiếp theo trước submission là human-author verification, targeted prior-art comparison và một câu hỏi bài báo thống nhất. Nếu muốn một positive revision mechanism claim, cần dữ liệu/assessment và test độc lập mới với precision phù hợp; không thêm nhánh trên holdout đã mở.

## Trạng thái rà soát

Đã đọc trực tiếp mã và aggregate outputs của các nhánh nêu trên, kiểm tra timing/feature lineage, training-only transforms, task/label definitions và paired bootstrap. Một lỗi TEST boundary tiềm tàng được phát hiện và sửa trước lock của nhánh code-path. Chưa phát hiện lỗi quan trọng còn lại trong các đường đã đọc. Đây không là chứng nhận mọi dòng code hoặc mọi record nguồn; không thực hiện một external rerun toàn bộ archive-to-results.

Đã đọc lần cuối `paper/manuscript.tex` và `paper/BAO_CAO_NGHIEN_CUU.md` sau khi tích hợp nhánh 2016-2. Các con số, ba estimand riêng, kết quả chưa phân định được của code-path, giới hạn prior art, feedback availability và trade-off screening được diễn giải nhất quán với bằng chứng. Không thấy TODO/TBD/FIXME hay kết quả đang chờ. Đã đề nghị chỉnh hai chi tiết mô tả: semester là biến nhị phân số, chỉ source/target item dùng one-hot; NLL là phép thử chính còn Brier là thước đo bổ sung. Cách gọi tỷ lệ hash là tỷ lệ danh nghĩa thay cho xác suất phân nhóm cũng chính xác hơn.

Sau những chỉnh sửa câu chữ đó, không có vấn đề khoa học trọng yếu còn lại trong phạm vi đã đọc ngăn việc đóng băng working manuscript. Đây là xác nhận tính nhất quán nội dung với bằng chứng hiện có, không phải chứng nhận khả năng được nhận bài, tính mới tuyệt đối, phê duyệt đạo đức hay một lần tái lập độc lập toàn bộ dữ liệu. Scientific readiness và implementation correctness là hai đánh giá khác nhau: code có thể đúng trong khi phát hiện vẫn nhỏ, bất định hoặc chưa đủ mới.
