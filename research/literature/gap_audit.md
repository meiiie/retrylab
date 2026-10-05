# Kiểm toán khoảng trống nghiên cứu: cập nhật dự báo từ các lần sửa bài

Ngày chốt tài liệu: **26/09/2026**. Đây là kiểm toán có mục tiêu của tám công trình gần nhất về mặt câu hỏi nghiên cứu, không phải systematic review toàn ngành hay chứng minh quyền ưu tiên. Các số trang bên dưới là **trang PDF đếm từ 1** của bản lưu trong `papers/`, không nhất thiết là số trang trong kỷ yếu. Tác giả, DOI, trạng thái công bố, phiên bản, nguồn và SHA-256 nằm trong `sources.json`; trích dẫn dùng được nằm trong `references.bib`.

**Kết luận:** ý tưởng rộng “phân biệt sửa được bài hiện tại với học được kiến thức”, “dự báo đúng chưa bảo đảm policy tốt”, “đánh giá qua nhiều simulator”, và cả minh họa dự báo cùng một bài tương lai qua nhiều lịch sử đều đã có tiền lệ. Phần có thể phát triển thành đóng góp là **kiểm toán có hệ thống giá trị dự báo của một khối retries đối với cùng outcome bài khác, rồi kiểm tra quyết định nhạy đến đâu với cập nhật ấy**. Mức đóng góp hiện mới là giả thuyết nghiên cứu; chưa có cơ sở hứa Q1/Q2/A* hoặc gọi phương pháp là SOTA.

## 1. Ma trận công trình gần nhất

| Công trình và trạng thái đã kiểm chứng | Bằng chứng trực tiếp đã đọc | Phần đã có tiền lệ / giới hạn cho đề xuất |
|---|---|---|
| **Shi, Chi, Barnes, Price — Code-DKT (EDM 2022)**. [Kỷ yếu chính thức](https://educationaldatamining.org/edm2022/proceedings/2022.EDM-long-papers.5/index.html), DOI `10.5281/zenodo.6853105`. | §5.1.3, p7: first/all attempts và kiến thức tổng quát so với tiến gần lời giải. §5.2 Case C/Fig8, p9: cùng target problem 5 được dự báo sau các lịch sử khác nhau. | Không được nhận “first fixed future probe” hoặc “first repair/knowledge distinction”. Khác biệt có thể là audit định lượng trên nhiều khối retries, thay vì một minh họa. |
| **Heickal & Lan — Learning Code-Edit Embeddings to Model Student Debugging Behavior (AIED 2025)**. [Chương Springer](https://doi.org/10.1007/978-3-031-98465-5_12); online 20/07/2025. | [Bản tác giả](https://people.umass.edu/~andrewlan/papers/25aied-codeedit.pdf), §2.1 p3, §3.1–4 pp4–5: embedding chênh code; gợi ý code bước tiếp theo theo test-case mask mong muốn. | Code-edit embedding và personalized debugging support đã có. Outcome chính là code được sinh, không phải audit cập nhật trên cùng một bài tương lai khác. |
| **Kim & Kim — Ensuring Reliability in Programming Knowledge Tracing (2026)**. [arXiv v1 06/05/2026](https://arxiv.org/abs/2605.04727v1). Metadata tác giả ghi accepted ITS 2026, to appear LNCS. | §3.1–3.3 pp5–6; §4 p7; §6.1 p9: chiều softmax, thứ tự timestamp, tuning baseline. | Audit leakage và baseline fairness đã có. “Causal validity” ở đây là biên thông tin theo thời gian, không phải nhận dạng tác động giao bài. Chưa xác minh DOI kỷ yếu. |
| **Patel et al. — A Dataset for Modeling Iterative Problem-Solving / CodeInsight (2026)**. [arXiv v1 01/09/2026](https://arxiv.org/abs/2609.00940v1); metadata ghi EMNLP 2026 Findings. | Fig2 p4; Appendix C p18: calibration tuần 1–3, dự báo tuần sau; 55/15/30% train/validation/test theo người. Code có NLL/Brier và nhiều cutoff tuần. | Benchmark iterative programming, future-week prediction và proper scores đều đã có. Không được gọi các thành phần ấy là mới. Final ACL proceedings record chưa xác minh; dataset có điều kiện xin phép, chưa được dùng trong nghiên cứu này. |
| **Ozyurt, Almaci, Feuerriegel, Sachan — ExRec (NeurIPS 2025)**. [Kỷ yếu](https://proceedings.neurips.cc/paper_files/paper/2025/hash/13707aad517ddd6c09ea02e0f55e1e7a-Abstract-Conference.html), DOI `10.52202/085713-0440`. | §4.3–4.4, pp5–6, Eq14–19; §4.4.1 p7, Eq23. Reward là **signed difference**, được đối chiếu với code. | Chuỗi KT → state/reward → RL không mới. Không được gán reward clipped-positive của ví dụ tự xây cho ExRec. Chi tiết kiểm toán riêng ở mục 2. |
| **Doroudi, Aleven, Brunskill — Robust Evaluation Matrix (L@S 2017)**. [DOI](https://doi.org/10.1145/3051457.3051463); [PDF tác giả](https://www.cs.cmu.edu/~shayand/papers/L@S2017.pdf). | pp3–4: predictive fit và policy ranking; REM đánh giá policy trong nhiều student models. Kết luận p9 nêu giới hạn của giá trị policy ước lượng. | Cross-simulator evaluation đã có gần một thập kỷ. Không đổi tên REM thành đóng góp mới; mở rộng phải chỉ rõ yếu tố lập trình/retries và diagnostic nào mới. |
| **Cheng et al. — UniER (2026)**. [arXiv v1 16/05/2026](https://arxiv.org/abs/2605.16750v1); chưa xác minh venue phản biện. | §3.1 p5, Eq7: WCG dùng chênh lệch KT trước/sau simulated path; §3.3 p6 và §4.3 p8: benchmark/label-noise experiments. | Metric “knowledge gain” từ KT và robustness benchmark đã có. Chưa kiểm toán trọn đường chạy code để khẳng định mọi kết quả thực hiện Eq7 giống nhau. |
| **González-Brenes & Huang — Your Model Is Predictive—but Is It Useful? (EDM 2015)**. [PDF chính thức](https://www.educationaldatamining.org/EDM2015/uploads/papers/paper_113.pdf). | §3 pp2–5; §4–5 pp5–8: LEOPARD/TEAL/WHITE; phân biệt dự báo với effort/outcomes của tutoring qua log và dữ liệu giả. | “Prediction ≠ educational utility” không mới. Cần vượt một lời cảnh báo khái niệm bằng phép kiểm định có thể tái lập và phát hiện cụ thể. |

Về metadata: bản arXiv của code-edit dùng **Embedding** số ít, tên chương công bố dùng **Embeddings**. Các anchor dùng bản tác giả 7 trang, không gán trực tiếp sang pagination 91–98 của chương. Bản Code-DKT có mâu thuẫn cỡ mẫu giữa abstract và methods; không lấy con số trong abstract làm sự thật mặc định. Ledger giữ các bất nhất này thay vì tự sửa nguồn.

## 2. ExRec thực sự tối ưu điều gì?

Eq19, p6 định nghĩa

\[
r_t=\hat y^c_{t+1}-\hat y^c_t.
\]

Eq23 lấy kỳ vọng cả hai nhánh đúng/sai. KC calibration ở Eq14–17 đưa dự báo theo KC gần trung bình dự báo theo câu hỏi, đồng thời giữ loss dự báo response thật. Đây không phải bằng chứng độc lập rằng chênh lệch state đo tác động nhân quả của việc luyện tập. [Nguồn chính](https://proceedings.neurips.cc/paper_files/paper/2025/file/13707aad517ddd6c09ea02e0f55e1e7a-Paper-Conference.pdf).

Đã kiểm tra tĩnh `cluster_vector_env.py` ở commit `234955079f936de876c476bebd4b51468694356d`: L264 đo state trước; L274 lấy Bernoulli response; L275 cập nhật; L277 đo state sau; L284 trừ trực tiếp. Không có `max(0, delta)` trên nhánh reward này. [Permalink L264–288](https://github.com/oezyurty/ExRec/blob/234955079f936de876c476bebd4b51468694356d/exercise_recommender/envs/cluster_vector_env.py#L264-L288).

**Hệ quả cho lập luận của chúng ta:** ví dụ posterior tăng do thêm bằng chứng chỉ chỉ ra khác biệt khái niệm giữa belief update và biến đổi năng lực. Nó không tự chứng minh signed-delta reward có bias dương, ExRec sai, hoặc tất cả hệ thống KT-RL vô hiệu. Muốn phê bình một công trình cụ thể phải tái hiện đúng reward, target, transition và protocol của công trình ấy. Clip trong PPO objective, gradient hoặc nhiễu action cũng không đồng nghĩa clip reward.

## 3. Estimand hẹp mà dữ liệu thực cho phép

Đặt `i` là một khối liên tiếp làm cùng bài; `H0` kết thúc sau lần nộp đầu, `H1` sau lần nộp cuối của khối; `j ≠ i` là bài khác ở tương lai với outcome lần đầu được quan sát `Yj`. Với **cùng mô hình đã đóng băng**:

\[
p_0=f(j,H_0),\quad p_1=f(j,H_1),\quad
\Delta L=L(Y_j,p_1)-L(Y_j,p_0).
\]

`ΔL < 0` nghĩa là cập nhật cho dự báo tốt hơn trên target đã chọn. Đơn vị này khác so sánh AUC của hai tập retry/first-attempt khác nhau. Tuy nhiên phép dùng cùng target không tự mới; novelty khả dĩ nằm ở **population-level retry-block audit**, các đối chứng để cô lập nguồn thông tin, và mối nối sang độ nhạy của quyết định.

`p1 − p0` là thay đổi dự báo, `ΔL` là thay đổi chất lượng dự báo; chúng khác đơn vị. Không được gọi chênh xác suất là phần trăm kiến thức, hoặc kết luận “inflation” chỉ vì chênh xác suất lớn hơn chênh Brier. Một cập nhật làm posterior tăng có thể hoàn toàn hợp lý khi dữ liệu mới cho thấy năng lực đã có từ trước. Một cập nhật làm loss xấu ở vài cá nhân cũng không bác bỏ mô hình: outcome nhị phân có nhiễu.

Về lý thuyết, nếu hai dự báo là conditional probabilities đúng của **cùng random variable** trên hai sigma-field lồng nhau, cùng quần thể và cùng cơ chế quan sát, tính martingale và expected improvement của proper scoring là chuẩn xác suất quen thuộc. Đây không phải định lý mới. Trong log thực, ta không biết oracle conditional probabilities, và lọc theo việc có bài `j` tương lai có thể thay quần thể; không áp dụng định lý ấy một cách máy móc để gắn nhãn mọi tăng loss trong subgroup là bất hợp lý.

Protocol hiện tại cho **observational forecast validation trong nhóm có future probe được quan sát**. Nó chưa đo `Y(do(practice i)) − Y(do(other action))`. Tên “transfer” nếu dùng phải được định nghĩa là chuyển thông tin dự báo sang bài khác, không phải tác động chuyển giao học tập nhân quả.

## 4. Ba điểm dễ làm sai kết luận nhất

1. **Selection và định nghĩa cơ hội học.** Người tiếp tục sang bài `j`, người dừng sau AC, người bỏ cuộc và người quay lại bài cũ khác nhau. Danh tính `j` được biết sau khi đọc log; nó chưa là candidate mà policy biết chọn ở `H0`. Giữ cả khối chưa AC, báo coverage/censoring, phân tích strata đã định trước; không tuyên bố rằng việc này đã giải quyết confounding. Thay missing outcome bằng 0 sẽ đổi câu hỏi và có thể tạo kết quả giả.
2. **Thông tin dùng để cập nhật và leakage.** Tăng số lần nộp, thời gian, final verdict, trạng thái gần lời giải và nội dung code đều cùng thay đổi. Cần đối chứng counts/time, last-response, first/last/all-retries, code-aware có cùng budget; không dùng code/score của chính target chưa xảy ra. Split theo người, kiểm tra timestamp ties/rejudging và cohort độc lập. Không so hai mô hình vừa refit rồi gọi chênh dự báo là tác động riêng của retries.
3. **Đánh đồng dự báo với quyết định.** Log có outcome của bài đã làm; thường không có outcome của toàn bộ bài có thể giao hay propensity đủ rõ. Vì vậy một mô hình làm `ΔL` tốt hơn chưa chứng minh policy tốt hơn. Mô phỏng tạo outcome cho action chưa thấy nhưng thêm giả định; không biến missing counterfactual thành quan sát thật. Không có logged propensity không đồng nghĩa mọi OPE đều bất khả thi, song estimated propensity vẫn cần đủ covariates, overlap và mô hình/giả định phù hợp.

## 5. Cầu nối từ audit sang recommendation

Thiết kế có ba lớp bằng chứng, mỗi lớp giữ đúng phạm vi của mình:

| Lớp | Thực nghiệm | Điều được kết luận |
|---|---|---|
| Log thật, target cố định | Paired Brier/NLL, calibration, update direction và độ lớn, khoảng theo người, cohort độc lập. | Chất lượng cập nhật dự báo trên outcome và quần thể đã quan sát. |
| Quyết định giả lập trên prefix thật | Giữ cố định candidate set, scoring rule, ngân sách và tie-breaking; chỉ đổi cách cập nhật state. Báo top-1/top-k disagreement, xác suất vượt ngưỡng, dependence vào độ dài retries. | Độ nhạy hành động. Chưa biết action nào tốt hơn trong đời thật. |
| Thế giới kiểm soát độc lập | Sinh latent learning và item-local repair riêng; response noise, forgetting, stopping và policy coverage được điều khiển. Đo return/regret bằng latent transition hoặc held-out assessment của generator, không bằng chính reward của agent. | Proxy hoặc policy thất bại/thành công dưới cơ chế đã nêu; kiểm tra quan hệ giữa audit và regret trong các thế giới đó. |

REM là khung đối chiếu nền cho lớp cuối. Chỉ dùng nhiều random seed của cùng simulator không đủ kiểm tra sai loại mô hình. Cần cơ chế khác nhau và một số thế giới giữ predictive fit tương đương nhưng khác action effects. Tất cả simulator cùng đồng ý vẫn không bảo đảm ngoài đời đúng; phải ghi rõ lớp thế giới đã xét.

Không cần PPO để thực hiện phép nối này. Một policy chọn bài theo threshold/difficulty, greedy expected signed gain, cùng random/curriculum baselines là đối chứng dễ diễn giải. Chỉ thêm RL khi chứng minh được horizon dài hoặc quan hệ prerequisite làm thay đổi kết luận nghiên cứu; tên thuật toán không tạo novelty.

## 6. Bài viết khả thi và điều kiện đủ sức công bố

Tên làm việc trung tính: **Do Retry-Induced Prediction Updates Transfer? A Fixed-Probe Audit of Programming Student Models**. Tên này đặt câu hỏi, không tuyên bố đã phát hiện “repair masquerading as learning”. Kết quả exploratory trong báo cáo dữ liệu hiện cho thấy một số proper scores **cải thiện nhỏ** sau retries; chúng chưa hỗ trợ câu chuyện chỉ toàn failure.

Đóng góp dự kiến có thể viết ở mức:

> We study the predictive validity of retry-induced state updates using paired forecasts of the same subsequently observed, previously unseen-to-the-student programming problem. We connect these diagnostics to recommendation sensitivity and controlled-ground-truth policy evaluation, while separating predictive evidence from causal learning effects.

Đây là mô tả thiết kế, không phải kết luận ưu tiên hay kết quả đã hoàn tất. Bộ bằng chứng tối thiểu để thành research paper có chiều sâu:

- Hai nguồn log độc lập: CodeBench cho code/process, ACcoding cho quy mô và portability của outcome-only audit; không gán feature code cho ACcoding khi không có full source.
- Ít nhất một KT tuần tự mạnh, baseline đơn giản được tune công bằng, và ablation thêm code/process thực sự đúng biên thông tin. Không xem mô hình lớn nhất mặc định là baseline đúng.
- Paired audit trên test/cohort chưa xem, uncertainty có cả biến thiên split/fit khi phù hợp; báo effect size và coverage. Một bootstrap conditional trên một fitted model không bao trùm mọi bất định nghiên cứu.
- Kết quả có cơ chế: có điều kiện nào khiến retries hữu ích hoặc gây cập nhật sai, và điều này tác động quyết định ra sao trong thế giới có ground truth? Phân tích heterogeneity phải có validation, không tìm subgroup sau khi xem test rồi gọi là hypothesis xác nhận.
- Nếu đề xuất phương pháp “sửa” cập nhật, phải cải thiện proper score/decision criterion trên test độc lập và đánh đổi được trình bày; ép state tăng đơn điệu không mặc nhiên đúng.

**Thí nghiệm kế tiếp cụ thể sau pilot:** khóa trước một cohort mới; dùng frozen DKT và baseline counts/time, lập cùng các cặp `(H0,H1,j,Yj)`; so full retries với first+last và counts-matched history, mỗi phương án có baseline huấn luyện tương ứng. Báo paired score theo nhóm khối kết thúc AC/chưa AC, độ dài khối và độ tương tự bài, đồng thời giữ tiêu chí tổng thể đã định trước. Trong nhánh cố định mô hình, mask history phải được báo như stress test vì có thể tạo input ngoài phân phối; nhánh retrain-matched kiểm tra tính công bằng. Sau đó kiểm tra liệu các trạng thái có audit kém có tạo decision instability và simulated regret cao hơn hay không. Nếu không, báo điều đó thay vì dựng failure narrative.

Nếu chỉ có “dùng Brier thay AUC”, một case study hoặc synthetic counterexample dựa trên clipping không tồn tại trong baseline, novelty yếu. Nếu kết quả ổn định across cohorts/models cho thấy một failure có cơ chế, phạm vi áp dụng rõ, artifact tái lập và cách khắc phục được xác nhận, bài có cơ sở mạnh hơn. Venue/ranking cụ thể phải chọn theo kết quả cuối, không theo tên mục tiêu ban đầu.

## 7. Những gì đã và chưa kiểm chứng

Đã lưu 9 PDF cho 8 công trình (code-edit có hai phiên bản), extract text, checksum; đọc các phần liên quan; đọc metadata chính thức hoặc tác giả; kiểm tra tĩnh các file code liên quan ở commit trước cutoff. Không chạy code từ các repository, không tuyên bố tái lập kết quả của họ, không tải dữ liệu sinh viên từ các kho đó.

`code_manifest.json` ghi các file đã lấy. CodeInsight `student_split.py` xác nhận split 55/15/30%; `metrics.py` đã có Brier/log likelihood. UniER đã xem README và một helper tính promotion, **chưa** trace toàn bộ WCG evaluation dispatcher. Repository code-edit chỉ kiểm tra README/schema trong vòng này. Với Reliability PKT chưa xác minh một repository riêng. Acceptance/publication chưa có proceedings record được đánh dấu rõ trong BibTeX thay vì suy đoán DOI.

Các PDF/code lưu để kiểm toán nội bộ và tái đối chiếu; trước khi phát hành repository của nghiên cứu, nên phát hành manifest/URL và script tái tải, không mặc nhiên đóng gói toàn bộ bản sao nguồn bên thứ ba. Phần tải nguồn là read-only đối với bên cung cấp, không liên hệ tác giả hay chấp nhận điều khoản dữ liệu thay người dùng.
