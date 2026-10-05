# Thông tin từ đường sửa code: kiểm tra khoảng trống có mục tiêu

Chốt tài liệu ngày **26-09-2026**. Câu hỏi hẹp: sau khi biết lịch sử trước episode, bài sẽ dự báo, số lần thử, kết quả đầu/cuối, thời gian và các kết quả trung gian, các **snapshot code trung gian** có giúp dự báo lần trả lời đầu của bài khác kế tiếp không?

**Trong các toàn văn được kiểm tra, chưa thấy một thí nghiệm đáp ứng đồng thời toàn bộ điều kiện này. Đây là một phép thử thực nghiệm có ý nghĩa, nhưng chưa phải bằng chứng về novelty toàn ngành.** Các thành phần riêng lẻ—code giúp dự báo bài mới, code-edit embeddings, first-attempt evaluation, timing/edit-distance features, trajectory ablations—đều đã có. Đóng góp khả dĩ phải nằm ở một phát hiện về thông tin còn lại của đường sửa code sau đối chứng mạnh, không nằm ở việc ghép các thành phần.

## Bằng chứng gần nhất

Trang là chỉ số một-based trong PDF cục bộ; riêng HELP-DKT dùng bản publisher. Không dùng tóm tắt của bên thứ ba làm bằng chứng phương pháp.

| Nguồn gốc đã đọc | Overlap thực sự | Điều chưa thấy trong phần phương pháp/thí nghiệm đã đọc |
|---|---|---|
| **[Code-DKT, EDM2022](https://educationaldatamining.org/edm2022/proceedings/2022.EDM-long-papers.5/index.html)**. §3.1–3.2 p4; §4.2/Table2 p6; §5.1.3 p7; §5.2/Fig8 p9. | Chuỗi code/correctness cải thiện dự báo **first attempt ở bài khác**; paper đặt trực tiếp câu hỏi general knowledge hay closeness-to-current-solution. Baseline DKT nhận cùng chuỗi problem/correctness, do đó count và intermediate outcomes **đã có ngầm trong input**. | Không tách endpoint code khỏi intermediate path; không thấy elapsed-time/endpoint-matched ablation. Training dùng next-attempt losses trên mọi bước; first attempts là evaluation slice. CaseC cùng future problem là một ví dụ sau các bài nguồn một-attempt, không phải revision-path experiment. Đây là prior gần nhất cho cross-problem predictive value. |
| **[Learning Code-Edit Embeddings to Model Student Debugging Behavior, AIED2025](https://doi.org/10.1007/978-3-031-98465-5_12)**. Author manuscript §2–2.1 pp2–3; §3.1 p4; results p5. | Biểu diễn actual consecutive edits, supervision bằng before/after test masks; sinh code bước sau có desired mask. | Target là sửa **cùng bài**, không phải first response của bài khác. Test masks ở đây dùng để học/điều kiện sinh, không tương đương giữ nguyên outcome summaries để đo giá trị gia tăng của đường sửa code. Không được tuyên bố code-edit representation là mới. |
| **[A Dataset for Modeling Iterative Problem-Solving / CodeInsight, 2026](https://arxiv.org/abs/2609.00940v1)**. App.C.4–C.10 pp19–22; App.D.2–D.5 p25; D.7/Table8 p29. | Có code-aware prediction, metrics theo attempt, persona gồm timing/edit-distance/count và prior trajectories; có NoPersona/NoTrajectory/NoRAG ablations. First-attempt generation có thể dùng các trajectory của bài trước. | Không thấy nested comparison giữ endpoint code và mọi behavioral inputs, chỉ thêm/bỏ intermediate code. NoTrajectory bỏ đồng thời code summaries và outcome/action history của bài target, nên không cô lập path increment. Phải trích nguồn này khi đề xuất timing/edit/count controls. |
| **[srcML-DKT, EDM2025 author paper](https://learninganalytics.upenn.edu/ryanbaker/EDM2025-srcml-DKT-proceedings-v01.pdf)**. §3.4 p4; §4.1 pp4–5; §4.2 pp5–6. | Code-DKT variant giữ thông tin code không parse được; so first/all attempts; minh họa consecutive changes. | Không thấy nuisance-matched endpoint-versus-intermediate ablation. Cải thiện first-attempt prediction không tự chỉ ra revision process hữu ích ngoài endpoint quality. Paper cũng làm rõ rủi ro loại syntax-error submissions khỏi code analysis. |
| **[HELP-DKT, Scientific Reports2022](https://doi.org/10.1038/s41598-022-07956-0)**. Task definitions pp7–8; Implementation p8. | TaskA dùng các code vectors của challenge trước để dự báo challenge kế; TaskB dự báo attempt sau cùng challenge. Đây là cross-challenge trajectory prior từ 2022. | TaskA gán nhãn theo ngưỡng `try_num=3`, không phải target first-response correctness. Không thấy full nuisance/endpoints/path nested contrast. Việc đào tạo đúng một target cross-challenge cũng không tự là mới. |
| **[Open-ended Knowledge Tracing for Programming Exercises, CSEDM workshop2022](https://zenodo.org/records/7157118)**. §2.4 p3; §3–3.2 p4. | Có all-submission và first-only settings; first-only training nhắm các bài khác. | First-only setting bỏ later attempts, nên không đo nội dung revisions; all-submission setting đổi tập targets. Các ablations tập trung representation/alignment/pretraining/generation. |
| **[Revision-Aware Success Prediction from Multi-Attempt Programming Trajectories, 2026 preprint](https://arxiv.org/abs/2608.26169v1)**. §III.C–F pp3–4; §IV.C–E p5; §VII pp12–13. | So current snapshot, consecutive pairs và ba snapshots; kiểm tra horizon availability. Đã đặt câu hỏi liệu thêm revision history có hữu ích; không có lợi ích nhất quán giữa các settings. | Các targets vẫn là acceptance của **cùng problem**, ở current/next/within-three attempts. Regimes có tập eligible khác nhau; không giữ toàn bộ nuisance và endpoints. Không có next-different-problem first-response test. Không được lấy kết quả của paper này làm bằng chứng revisions nói chung vô ích. |

Nguồn cuối có metadata không đồng nhất về tháng: identifier là `2608.26169`, nhưng trang arXiv lúc kiểm tra ghi v1 **21-07-2026 01:06:31 UTC**; một số index ghi tháng 8. Cả hai trước cutoff. Báo đúng ngày do primary history cung cấp, không suy ra ngày từ identifier; chưa xác minh venue peer-reviewed.

Một tín hiệu gần nữa là **SETR-PKT: Programming Knowledge Tracing via Strategy Evolution Graph and Time-Aware Retrieval**, có trong [official WISE2026 program](https://conferences.sigappfr.org/wise2026/program-2/) (#815): abstract nói đến consecutive-code strategy graphs và time-aware retrieval. Chưa tìm được fulltext/DOI/ngày công bố abstract. Hội nghị [diễn ra 1–5-11-2026](https://conferences.sigappfr.org/wise2026/), sau cutoff. Vì vậy chỉ ghi là **announcement nhìn thấy khi rà soát**, không dùng như một paper đã xuất bản trước cutoff hay suy đoán rằng nó có/không có đúng controls đang đề xuất.

## Phải tách endpoint representation khỏi thông tin của đường đi

Ký hiệu (Z) gồm nuisance information và target problem (J); (C_1,C_n) là source code ở đầu/cuối episode; (R=(C_2,\ldots,C_{n-1})) là intermediate path; (Y_J) là outcome first response ở bài khác kế tiếp. Các inputs đều phải có trước thời điểm dự báo H1, còn (J) được dùng theo task definition đã khóa.

Nếu một feature chỉ là `diff(C1,Cn)`, nó là hàm xác định của hai endpoint. Khi conditioning trên **full raw endpoints**, có:

\[
I(Y_J;\operatorname{diff}(C_1,C_n)\mid Z,C_1,C_n)=0.
\]

Một predictor hữu hạn vẫn có thể tốt hơn khi nhận thêm diff, vì nó đọc representation này dễ hơn. Điều đó chứng minh **giá trị biểu diễn đối với model class**, không chứng minh có thông tin mới ngoài endpoints. Tương tự, token/AST embeddings có mất thông tin: thêm một feature từ endpoints có thể bổ sung thông tin so với embeddings đã nén, nhưng không so với raw code đầy đủ. Cần nói rõ cấp độ nào đang được kiểm định.

Thí nghiệm có ý nghĩa nên tách ba tầng trên **cùng eligible cohort và cùng target labels**:

| Tầng | Input thêm vào | Câu hỏi thực nghiệm |
|---|---|---|
| M0 | (Z): history trước episode; identity/difficulty của source/target; retry count; first/final outcomes; elapsed time; intermediate outcome summaries; missingness/availability flags thích hợp. | Coarse behavioral evidence dự báo được bao nhiêu? |
| M1 | M0 + endpoint code representations. Bao gồm endpoint-diff control, nếu tính được đáng tin cậy. | Chất lượng/nội dung code đầu-cuối có thêm predictive value ngoài coarse behavior không? |
| M2 | M1 + intermediate snapshots hoặc path descriptors thật sự không suy ra từ endpoints. | Phần code path quan sát thêm có lợi ích vượt endpoint representation không? |

M1–M0 là một extension/replication của code-aware prediction. **M2–M1** mới gần với câu hỏi về thông tin của revision process. Hai model phải được retrain với inputs của mình, cùng training target là first response bài khác; chỉ xóa/shuffle input của model đã fit không đủ cho primary contrast. M2 không được có encoder/training budget tốt hơn một cách không kiểm soát khiến không thể phân biệt path information với capacity.

Một endpoint baseline quá yếu vẫn không đủ: ưu tiên cùng code encoder/feature extractor cho endpoints và intermediate states, một endpoint-diff hoặc endpoint-interaction variant, và một baseline outcome-sequence có order/count rõ ràng. Không cần sáng tạo kiến trúc lớn chỉ để tạo câu hỏi nghiên cứu này.

## Kiểm định và controls có giá trị

Primary estimand có thể là average held-out log-loss reduction của M2 so M1, paired theo cùng row và uncertainty theo learner. Đây là **finite-model predictive risk contrast**, không phải estimator được chứng minh của conditional mutual information, cũng không phải learning effect. Brier và calibration có thể giúp giải thích kết quả; tránh chọn metric thắng sau khi mở holdout.

Các kiểm tra phân biệt cơ chế phải được khóa trước khi xem outcome holdout:

- **Same-code resubmission:** đánh dấu raw-identical code, token-identical code và parsing failure riêng. Token equality không đồng nghĩa program semantic equivalence; chuẩn hóa không cẩn thận có thể xóa nội dung quan trọng. Resubmit code giống nhau cũng không đồng nghĩa learner không học: feedback, suy nghĩ và bối cảnh chưa quan sát vẫn có thể thay đổi.
- **Endpoint-only và path-order controls:** endpoint diff nằm trong M1; unordered intermediate summaries so với ordered path giúp phân biệt nội dung được quan sát và thứ tự. Sự khác biệt giữa models vẫn là predictive evidence trong thiết kế, không causal decomposition của cognition.
- **Nuisance balance:** báo support/coverage theo retry count, outcomes và elapsed time. Matching/stratification phải đủ mẫu; không quảng bá approximate matching như giữ hoàn toàn mọi yếu tố. Có thể dùng nuisance-adjusted nested models làm primary và strata như sensitivity, thay vì tuyên bố causal-matched study.
- **Target independence:** phải kiểm tra bài target thực sự khác và là first observed submission trong phạm vi lịch sử đủ quan sát. Không đưa future target code, outcome, final snapshot hoặc aggregate statistic có future leakage vào input. Similarity/KC grouping phải định nghĩa trước khi xem target outcomes.
- **Population:** số snapshots tối thiểu 3 là điều kiện cần để có intermediate code, chưa bảo đảm có intermediate content khác endpoints. Báo tỷ lệ bị loại do thiếu/tie timestamps, snapshots lặp, ambiguous pairing, syntax errors và không có future probe. Không ngoại suy sang mọi người học từ tập những người tiếp tục làm bài.

## Quyết định nghiên cứu

**Đáng chạy như một phép thử cơ chế được giới hạn trước**, nếu audit dữ liệu xác nhận mapping timestamp–submission–source code. Bản rà soát này không chứng nhận mapping hay tính khả thi trên CodeBench; đó là một gate riêng. Fresh-semester protocol và holdout theo người học giúp chống lựa chọn kết quả, nhưng không tự tạo novelty.

Positive M2–M1 có sức thuyết phục hơn nếu ổn định qua một representation control mạnh, một split/cohort độc lập, và một contrast định trước về quan hệ source–target. Khi đó phát biểu bảo vệ được là **intermediate revision evidence cải thiện forecast của bài mới ngoài các inputs được kiểm soát trong model families đã thử**. Không gọi đây là chứng minh học do sửa code, đo latent mastery, conditional MI của raw code, hay recommendation superiority.

Nếu M2–M1 không đạt ngưỡng thực tiễn đã khóa, kết luận phù hợp là chưa có incremental predictive benefit trong dữ liệu/thiết kế đó; không mở thêm nhiều features/subgroups cho đến khi tìm được significance. Negative result có thể hữu ích cùng phân tích endpoints/coverage, nhưng không đủ để hứa hẹn Q1/Q2/A*.

## Lưu vết tìm kiếm và truy cập

Agent-Reach/Exa và primary web được dùng cho các truy vấn giới hạn: `"programming knowledge tracing" "code changes" "first attempt"`; `"knowledge tracing" "code edit" "ablation"`; programming KT + identical-code resubmission/next-problem prediction; `"code revisions" "first attempts" prediction`; và các title cụ thể nêu trên. Fulltext Code-DKT, Code-Edit, OKT và CodeInsight có thêm một lượt đọc độc lập. Đã đọc thêm srcML-DKT, HELP-DKT, Error-DKT2024 và revision-aware2026; Error-DKT xác nhận code/error-feature ablations và first-attempt evaluation nhưng không tạo một direct match cho phép thử hẹp.

Không tìm thấy nghiên cứu đúng toàn bộ điều kiện qua các truy vấn này **không** có nghĩa chưa tồn tại. Không audit toàn bộ source code của các papers cho negative claims. Không gọi các code snapshots do người học nộp là đo lường trực tiếp quá trình suy nghĩ.

Các PDF mới được lưu ở `papers/revision_aware_2026.pdf`, `papers/srcml_dkt_2025.pdf`, `papers/help_dkt_2022.pdf`, `papers/error_dkt_2024.pdf`; URL và SHA-256 trong `download_manifest.json`. Không tái phân phối toàn văn trong source-only package. Sau kiểm tra metadata, bốn nguồn được yêu cầu cho revision branch—revision-aware2026, srcML-DKT2025, HELP-DKT2022 và OKT workshop2022—đã được thêm vào `references.bib`, `revision_sources.json` và `sources.json`; bibliography có 17 entries. Error-DKT chỉ là nguồn sàng lọc trong lượt này. Không thêm SETR-PKT vào bibliography như paper đã xuất bản.
