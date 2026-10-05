# Đánh giá đề tài AAI và đề xuất hướng nghiên cứu

**Mốc tài liệu: 26/09/2026.** Đối tượng: đề 4 trong phần **“Dữ liệu thầy đã có”**, trang 7–8 của danh sách người dùng cung cấp. Điều kiện đã biết: không thử nghiệm trên sinh viên thật; dự kiến dùng GPU trên Kaggle; ưu tiên đóng góp nghiên cứu và bài báo, không đặt giới hạn theo tiến độ học phần.

**Cập nhật sau khi thực nghiệm và phản biện:** đây là bản định hướng ban đầu, không phải kết luận cuối. Xem [báo cáo nghiên cứu và khả năng công bố](paper/BAO_CAO_NGHIEN_CUU.md), [bản thảo](paper/manuscript.tex) và [prior art bổ sung](research/literature/supplementary_gap_audit.md). Các ý tưởng rộng về matched future-target audit đã có tiền lệ công khai, bao gồm artifact ngày 22/09/2026; không nhận chúng là đóng góp đầu tiên. Thực nghiệm mới xác nhận lợi ích dự báo nhỏ trên ACcoding, chưa chứng minh retry chỉ gây sai lệch hay policy khuyến nghị thất bại.

**Đính chính phạm vi dữ liệu theo người dùng:** tên mục “Dữ liệu thầy đã có” chỉ là nhãn trong danh sách. Thầy không cung cấp dataset; dự án phải tự tìm, truy cập và kiểm toán toàn bộ dữ liệu. Đã tải thành công CodeBench và ACcoding từ nguồn chính thức, kiểm tra archive/schema và triển khai thực nghiệm ban đầu. Xem [báo cáo dữ liệu và thực nghiệm](Du_lieu_va_thuc_nghiem_de_4.md) để biết số liệu trực tiếp, điều kiện sử dụng và giới hạn của kết quả; không mặc định các nguồn gated đã được cấp quyền.

## 1. Quyết định đề xuất

**Nên giữ đề 4, nhưng đổi câu hỏi khoa học từ “ghép Knowledge Tracing với PPO” sang “khi nào có thể tin việc tối ưu khuyến nghị bài lập trình bằng dữ liệu lịch sử?”.** Một hướng cụ thể là nghiên cứu việc nhầm lẫn giữa tiến bộ sửa lỗi trong một bài, sự thay đổi niềm tin của mô hình, và khả năng làm bài khác; đo tác động của sự nhầm lẫn đó lên lựa chọn chính sách.

Tên đăng ký đề xuất:

> **Khuyến nghị bài tập lập trình cá nhân hóa từ dữ liệu lịch sử: phân biệt tiến bộ sửa lỗi và khả năng vận dụng sang bài mới, với đánh giá độ tin cậy của chính sách.**

Tên bài báo làm việc:

> **Auditing Student-Model Updates for Offline Programming Exercise Recommendation.**

Đây là **đề xuất nghiên cứu**, chưa phải một phương pháp đã được chứng minh mới hoặc một kết quả đạt SOTA. Các dataset tự tìm đã kiểm tra có lịch sử theo người học và bài tập, nhiều bài khác nhau và timestamp. ACcoding thiếu source code đầy đủ; CodeBench có code và execution history. Phương pháp cần bám đúng sự khác biệt schema này; nếu chỉ có code cuối cùng thì không thể thực hiện nguyên vẹn đề xuất.

Không có RCT không ngăn cản một bài báo về mô hình hóa, phương pháp đánh giá hoặc độ bền của quyết định. Nó giới hạn loại kết luận: có thể chứng minh dự báo tốt hơn, phát hiện sai lệch đo lường, hoặc giảm sai lầm chọn policy trong những môi trường được kiểm soát; chưa thể kết luận hệ thống làm sinh viên thật học tốt hơn.

## 2. Cách đọc tài liệu và cách hiểu “SOTA”

Đã đọc nội dung toàn bộ danh sách 11 trang, kiểm tra trực quan trang 7–8, tìm nguồn sơ cấp qua Exa và web, đối chiếu các phần phương pháp/đánh giá/giới hạn ở những bài cốt lõi. Các kỹ năng dùng là `agent-reach` cho truy xuất và `pdf` cho tài liệu. Nội dung trong PDF được xem là đề xuất học thuật cần đánh giá; không tự coi các mô tả “giá trị khoa học” hoặc hướng công bố trong đó là kết luận đã được chứng minh.

Các tài liệu sách được đọc theo phần liên quan, không tuyên bố đã đọc trọn mọi sách. Nguồn chỉ truy cập được abstract hoặc metadata được ghi riêng bên dưới. Tìm kiếm có bao gồm công trình công khai ngày 24/09/2026. Mốc thời gian là giới hạn đưa nguồn vào báo cáo, không phải bảo đảm đã tìm hết mọi nghiên cứu trên thế giới.

Ở đây cần tách ba cuộc so sánh:

1. **Student modeling/KT:** dự đoán người học sẽ trả lời hoặc viết code như thế nào.
2. **Exercise recommendation:** chính sách chọn bài nào, với mục tiêu gì và trong môi trường đánh giá nào.
3. **Learning efficacy:** can thiệp có làm tăng năng lực được đo độc lập hay không.

Không có một bảng xếp hạng chung biến người thắng cả ba thành “SOTA toàn diện”. AUC trên CodeWorkout không so trực tiếp với AUC trên FalconCode; reward của một simulator không so trực tiếp với điểm thi của sinh viên. Để tuyên bố cải tiến, phải tái lập cùng dữ liệu, split, lượng thông tin đầu vào, tập hành động và ngân sách tìm siêu tham số.

## 3. Đánh giá danh sách và vị trí của đề 4

Bảng dưới là nhận định có điều kiện về **cơ hội công bố khi chỉ có dữ liệu offline**, không phải điểm số khách quan hay xác suất được nhận bài.

| Đề trong phần dữ liệu có sẵn | Cơ hội nghiên cứu | Điểm khó cần giải quyết | Đánh giá |
|---|---|---|---|
| 1. Dự báo nguy cơ trượt từ lịch sử code | Phân tích sớm, chuyển học kỳ, độ tin cậy và nhóm yếu | Phải có outcome tương lai, mốc dự đoán và kiểm soát leakage; thêm LSTM không đủ mới | Dễ kiểm chứng offline, tốt nếu có nhãn kết quả |
| 2. GNN phát hiện lỗi + LLM giải thích | Định vị lỗi có bằng chứng thực thi và giải thích sư phạm | Nhãn đúng/sai toàn bài không tự cung cấp nhãn dòng lỗi; phải thẩm định giải thích | Tiềm năng nhưng dễ thành hai đề tài lớn ghép lại |
| 3. Đạo văn/AI-generated code | Robustness của similarity hoặc provenance khi có ground truth | Tương đồng không chứng minh nguồn AI hay gian lận; khó có nhãn đáng tin | Không ưu tiên cho mục tiêu hiện tại |
| **4. Khuyến nghị thích ứng** | **Độ tin cậy của mô hình người học và quyết định offline** | **Lựa chọn bài phản thực, reward proxy, thiếu action support** | **Ưu tiên nếu chấp nhận nghiên cứu sâu các giới hạn này** |
| 5. Khai phá quan niệm sai | Giả thuyết misconception có thể kiểm chứng/bác bỏ từ nhiều sản phẩm thực | Một bug không đồng nghĩa một quan niệm sai; cần nhãn chuyên gia hoặc đánh giá có thiết kế | Phương án dự phòng mạnh khi policy không đánh giá được |
| 6. Lỗi bộ nhớ bằng CFG/logic | Đặc tả có phạm vi rõ, tính đúng đắn, lời giải thích dễ học | Phải đối chiếu công cụ phân tích chương trình hiện có; không thể giải tổng quát mọi chương trình C | Tốt nếu muốn chuyển sang program analysis |
| 7. Phân loại tối ưu thuật toán | Nhãn complexity/performance và khái quát theo họ bài | Số vòng lặp không đủ suy ra độ phức tạp; runtime phụ thuộc input/máy | Bản mô tả hiện tại chưa có đóng góp nổi bật |
| 8. Sửa cú pháp | Minimal repair có kiểm chứng, giữ ý định học sinh | Compile được chưa chắc đúng; lĩnh vực repair đã đông | Chỉ nên chọn khi có failure mode mới cụ thể |
| 9. Gán KC và bản đồ kiến thức | KC phụ thuộc chiến lược giải, nhãn và uncertainty đáng tin | KCGen-KT đã tự động hóa nhiều phần; có cấu trúc cú pháp không chứng minh hiểu khái niệm | Hợp làm thành phần dữ liệu của đề 4 hơn là tuyên bố mới tự thân |
| 10. MDP cho hành vi sửa lỗi | Mô hình hóa trajectory và năng lực sửa lỗi | Đặt tên state/action/reward không tự tạo đóng góp hay đo được metacognition | Có thể hỗ trợ đề 4, cần tránh suy diễn tâm lý quá mức |

Các đề ở phần đầu về cảng biển, định tuyến, vận tải, video, y tế và tác tử có những câu hỏi nghiên cứu riêng. Mọi đề đều phải tự tìm dữ liệu. Không có căn cứ để khẳng định chúng vượt đề 4 chỉ vì sử dụng ViT, MARL hay fuzzy logic. Lợi thế tiềm năng của đề 4 phụ thuộc vào khả năng tìm được log học tập thực phù hợp, chứ không phải nhãn “dữ liệu có sẵn” trong danh sách.

Đề 5 và đề 9 cũng đã có đối thủ gần: [McMining, EACL 2026](https://aclanthology.org/2026.eacl-short.10/) và [KCGen-KT, ACL Findings 2026](https://aclanthology.org/2026.findings-acl.1670/). Đổi ngôn ngữ sang tiếng Việt hoặc C là mở rộng bối cảnh; tự nó chưa đủ thành đóng góp phương pháp.

## 4. Bản đồ nghiên cứu cần đối chiếu đến 26/09/2026

| Công trình | Trạng thái xác minh | Điều trực tiếp ảnh hưởng quyết định |
|---|---|---|
| **CodeInsight**, 01/09/2026 | Đọc bản arXiv và phương pháp; metadata ghi EMNLP 2026 Findings | Benchmark gồm log C++ tại Việt Nam, code, thời gian và kết quả từng test; có RSSM và các họ mô hình khác. Đã có đánh giá người học held-out và tuần tương lai; chỉ thêm temporal split không mới. Dữ liệu cấp theo yêu cầu. [Nguồn](https://arxiv.org/abs/2609.00940) |
| **KCGen-KT**, Findings ACL 07/2026 | Đọc full paper, methods, limitations và compute appendix | LLM sinh KC và KT có diễn giải đã có phương pháp cụ thể. Kết quả dự báo trên Java/Python không tự chứng minh hiệu quả khuyến nghị hay áp dụng sang C. [Nguồn](https://aclanthology.org/2026.findings-acl.1670/) |
| **ExRec**, NeurIPS 2025 | Đọc full text, kiểm tra proceedings | ETH Zürich/LMU kết hợp semantic KC, KT và nhiều thuật toán RL. Tăng kiến thức trong thực nghiệm dựa trên môi trường KT; chưa phải bằng chứng can thiệp trên người thật. [Nguồn](https://proceedings.neurips.cc/paper_files/paper/2025/hash/13707aad517ddd6c09ea02e0f55e1e7a-Abstract-Conference.html) |
| **UNO!**, AAAI-26, 14/03/2026 | Đọc methods/reward/evaluation | Đã dùng reward dày và GRPO cho lộ trình học. Chữ “offline” trong tên không đồng nghĩa đánh giá phản thực nhân quả trên log. [Nguồn](https://ojs.aaai.org/index.php/AAAI/article/view/38591) |
| **Counterfactual Learning…**, 22/06/2026 | Full text; arXiv ghi ECML-PKDD tháng 9/2026 | Inria SODA và cộng sự học contextual bandit từ log. Tác giả phân biệt reward difficulty-success với learning gain. Cần audit cách tạo context và propensity khi tái lập. [Nguồn](https://arxiv.org/html/2606.23015v1) |
| **UniER**, 16/05/2026 | Preprint; đọc benchmark | Đã có benchmark thống nhất item/path và kiểm tra sparsity/noise. Không nhận “đầu tiên benchmark robust” là đóng góp của ta. [Nguồn](https://arxiv.org/html/2605.16750v1) |
| **Ensuring Reliability in Programming KT**, 06/05/2026 | Preprint; đọc phương pháp kiểm toán | Đặt vấn đề thứ tự ServerTimestamp và temporal leakage trong triển khai. Đây là phát hiện tác giả báo cáo, chưa phải kết quả ta tự tái lập. [Nguồn](https://arxiv.org/abs/2605.04727) |
| **Learning Code-Edit Embeddings**, AIED 2025 | Đọc phương pháp | Code edits và test-case transitions đã được học thành biểu diễn; “thêm AST-diff” không đủ mới. [Nguồn](https://people.umass.edu/~andrewlan/papers/25aied-codeedit.pdf) |
| **UKT**, AAAI 2025 | Abstract/proceedings; chưa kiểm toán toàn bộ thực nghiệm | Uncertainty-aware KT đã có. Cần chứng minh uncertainty của ta giúp quyết định tốt hơn trong failure mode xác định. [Nguồn](https://ojs.aaai.org/index.php/AAAI/article/view/35007) |
| **Code-DKT**, 2022 | Đối chiếu câu hỏi và first/all-attempt evaluation | Bài đã phân biệt tín hiệu kiến thức chung và mức gần hoàn thành bài. “Repair khác transfer” không phải quan sát mới tự thân. [Nguồn](https://arxiv.org/abs/2206.03545) |
| **Robust Evaluation Matrix**, 2017 | Đối chiếu full paper | CMU/Stanford đã đánh giá policy trên nhiều student model. Cần vượt hơn việc đổi vài seed hoặc thêm một simulator. [Nguồn](https://www.cs.cmu.edu/~shayand/papers/L@S2017.pdf) |
| **Risk-Adaptive and Evidence-Constrained Feedback**, 24/09/2026 | Preprint; xác minh ngày và nội dung | Đã kết hợp calibrated risk, evidence constraints và can thiệp có giới hạn trong lập trình. “Thêm uncertainty + feedback” không phải khoảng trống đủ rõ. [Nguồn](https://arxiv.org/abs/2609.29874) |

Các nguồn phải kiểm tra thêm khi chuẩn bị Related Work: [PAKT, 2026](https://arxiv.org/html/2607.13103v1) đã phân tách ability/proficiency; [Multiscale Knowledge States for Programming, 09/04/2026](https://doi.org/10.1145/3774904.3792525) mới xác minh metadata; [KDG-Rec](https://doi.org/10.1109/TCSS.2026.3669970) đã có gán KC bằng LLM và graph cho recommendation, nhưng ở đây mới đọc abstract/metadata. Vì vậy không dùng “hai trạng thái local/global” hoặc “LLM + graph” như tuyên bố novelty độc lập.

Nguồn Neurocomputing DOI `10.1016/j.neucom.2026.134187` có metadata online/issue khác nhau và full text bị hạn chế. Không dùng nó làm căn cứ cho một thứ hạng SOTA tại cutoff trước khi xác minh bản công khai và ngày tương ứng.

## 5. Bài học từ lab lớn và sách nền tảng

**Nguồn sát bài toán hơn uy tín thương hiệu.** ETH/LMU giúp xác định baseline recommendation; Inria giúp xử lý learning from logs; Stanford và cộng sự trong CodeInsight giúp kiểm tra mô phỏng người học; CMU có nền tảng KT và đánh giá policy. Không cần đưa một LLM lớn vào chỉ để giống hệ thống của lab lớn.

Google DeepMind/Fab AI có [báo cáo Teaching with Gemini tháng 5/2026](https://storage.googleapis.com/deepmind-media/LearnLM/learnLM_sierraleone_may26.pdf), thử nghiệm ngẫu nhiên trên 1.763 học sinh, với tác động ITT báo cáo +0,258 độ lệch chuẩn. Đây là học toán có giáo viên tổ chức, không phải thử nghiệm RL chọn bài lập trình. Ý nghĩa là minh họa mức bằng chứng cần có khi phát biểu về hiệu quả học thật. Nghiên cứu offline của ta có đối tượng kết luận khác.

| Nền tảng đọc/tham chiếu | Phần nên dùng cho đề tài | Hệ quả thiết kế |
|---|---|---|
| [Sutton & Barto, Reinforcement Learning: An Introduction, 2nd ed., 2018](http://incompleteideas.net/book/the-book-2nd.html) | MDP, return, policy, off-policy learning; nguồn sách chính thức đã xác minh | Phải định nghĩa reward và môi trường trước khi chọn PPO/Q-learning. Trạng thái tri thức không được quan sát trực tiếp. |
| [Lattimore & Szepesvári, Bandit Algorithms, 2020](https://tor-lattimore.com/downloads/book/book.pdf) | Đã đọc phần contextual bandit và nền tảng conditional expectation/martingale liên quan | Bandit là đối chứng khoa học phù hợp cho mục tiêu tức thời; không phải mô hình bị loại vì “quá đơn giản”. |
| [Hernán & Robins, Causal Inference: What If, 2020](https://miguelhernan.org/whatifbook) | Trang sách và cấu trúc tài liệu đã xác minh; cần đọc tiếp phần observational và longitudinal khi thiết kế OPE | Viết estimand và giả định nhận diện trước estimator; không gọi tương quan tương lai là tác động can thiệp. |
| [National Academies, How People Learn II, 2018, chương 4](https://uwnxt.nationalacademies.org/read/24783/chapter/6) | Đã đọc phần tự điều chỉnh, truy hồi và giới hạn của một lần đánh giá | Không quy mọi tín hiệu “làm đúng” thành một mức hiểu cố định; cần bài khác, bối cảnh khác và độ bền theo thời gian nếu dữ liệu cho phép. |

Trong dự án, khái niệm “vùng phát triển gần nhất” chỉ nên là động cơ sư phạm. Không mặc định một ngưỡng xác suất đúng như 0,7 là định nghĩa đã được xác nhận của vùng này. Ngưỡng hoặc hàm tiện ích phải có phân tích độ nhạy và giới hạn diễn giải.

## 6. Vấn đề trung tâm: ba thứ thường bị nhập làm một

**A. Tiến bộ tại bài hiện tại.** Code vượt thêm test sau sửa lỗi, quen cấu trúc đề, hoặc làm theo gợi ý.

**B. Cập nhật hiểu biết của mô hình.** Sau quan sát mới, mô hình đổi ước lượng về người học; điều này có thể xảy ra dù tri thức người học không đổi.

**C. Khả năng vận dụng sang bài khác.** Dự đoán hoặc đo biểu hiện trên bài khác, đặc biệt lần đầu và không dùng đáp án của bài đó làm đầu vào. Ngay cả outcome này cũng chưa tự là tác động do bài khuyến nghị gây ra.

Ví dụ: hai sinh viên đều vượt 100% test. Một người làm đúng ngay; một người sửa 15 lần theo phản hồi. Ta không được mặc định người thứ hai yếu hơn, vì quá trình đó có thể giúp học sâu. Cũng không được mặc định tăng pass-rate trong 15 lần là tăng năng lực vận dụng. Đây là điều cần kiểm định sau khi kiểm soát độ khó, loại bài, lịch sử và trợ giúp có quan sát.

### Một kiểm tra toán học để phát hiện reward sai mục tiêu

Xét thế giới giả lập **không có học và không có quên**. Tri thức ẩn nhị phân `K` cố định. Mô hình dùng posterior đúng `p_t = E[K | H_t]`. Hành động được chọn dựa trên lịch sử sẵn có và ngẫu nhiên hóa độc lập với thông tin ẩn ngoài lịch sử. Với chính sách như vậy, luật kỳ vọng lặp cho:

`E[p_(t+1) - p_t | H_t, a_t] = 0`.

Đây là một tính chất xác suất chuẩn, không được tuyên bố là định lý mới. Nó gợi ý một bài kiểm tra thiết kế reward.

Đại lượng tri thức hoặc bộ bài probe phải giữ cố định khi so trước/sau. Thay bộ bài bằng bài dễ hơn có thể tăng điểm dự báo mà không liên quan tới tính chất trên. Với neural mastery score không phải posterior đúng, null test là một phép kiểm tra mô hình/metric, không phải bằng chứng toán học rằng mọi sai lệch đều là học giả.

Ví dụ tính chính xác: prior `P(K=1)=0,4`; xác suất trả lời đúng bằng `0,9` nếu đã biết và `0,2` nếu chưa biết. Khi đó:

- `P(đúng)=0,48`.
- Posterior khi đúng bằng `0,75`; khi sai bằng `1/13 ≈ 0,076923`.
- Posterior kỳ vọng vẫn bằng `0,4`; learning transition bằng 0.
- Nhưng nếu thưởng `max(p_(t+1)-p_t, 0)`, reward kỳ vọng bằng `0,168 > 0`.

Phép tính trên đã được kiểm tra bằng phân số chính xác. Nó là ví dụ tự xây dựng, **không phải kết quả trên dữ liệu thầy và không phải cáo buộc ExRec/UNO dùng đúng reward cắt ngọn này**. Bước nghiên cứu là tái lập reward thật của từng phương pháp và kiểm tra xem hiện tượng tương tự xảy ra ở đâu, dưới điều kiện nào. Reward chẩn đoán có thể hợp lệ cho mục tiêu thu thập thông tin; sai lầm là diễn giải nó thành learning gain.

Posterior gain có kỳ vọng dương không luôn là sai: khi tri thức thật chuyển trạng thái vì học, giả định `K` cố định không còn đúng. Thiết kế cần tách mô hình quan sát khỏi mô hình chuyển trạng thái, và kiểm tra trường hợp có học cùng trường hợp không học.

## 7. Câu hỏi nghiên cứu và đóng góp có thể bảo vệ

**Câu hỏi chính:** khi một chính sách khuyến nghị được tối ưu bằng mô hình học sinh từ log lập trình, nó có ưu tiên tín hiệu dễ tăng trong quá trình sửa bài hơn tín hiệu dự báo bài mới không, và ta có thể phát hiện/giảm sai lệch đó đến mức nào?

| Giả thuyết | Thử nghiệm có thể bác bỏ | Kết quả âm cũng có ý nghĩa gì? |
|---|---|---|
| H1. Một số reward nội bộ xếp hạng policy sai khi repair/observation update mạnh nhưng learning transition yếu | Thế giới có ground truth, quét mức repair và transfer độc lập; đo rank reversal và regret | Nếu không xảy ra, không được xây cả câu chuyện bài báo quanh failure mode đó |
| H2. Tín hiệu quá trình code giúp phân biệt hai loại tiến bộ sau khi đã kiểm soát feature đơn giản | So dự báo retry và first-attempt bài khác; ablation code/order/test transition với cùng split/budget | Nếu feature đếm lần thử đủ tốt, ghi nhận điều đó; không giữ encoder lớn chỉ để có kiến trúc phức tạp |
| H3. Policy được ràng buộc bởi hỗ trợ dữ liệu và bất định chọn sai ít hơn dưới model misspecification | So với cùng backbone không có ràng buộc, trên evaluator family chưa dùng tối ưu | Nếu chỉ giảm sai bằng cách gần như không đề xuất, kết quả không đủ; phải báo risk–coverage và utility–coverage |

Ba đóng góp ứng viên tạo thành một câu chuyện nhất quán:

1. **Đặc tả và kiểm toán một failure mode ở mức quyết định**, vượt hơn báo cáo AUC hoặc nhận xét chung “sửa đúng chưa chắc hiểu”.
2. **Một cơ chế tối ưu có thể giải thích bằng failure mode đó**, chẳng hạn objective tách diagnostic gain khỏi modeled transfer và ràng buộc hành động ngoài hỗ trợ.
3. **Một bộ thực nghiệm tái lập có thể bác bỏ kết luận**, gồm log thật, mô phỏng có ground truth và kiểm tra sai mô hình có chủ đích.

Local/global state, uncertainty, nhiều simulator và OPE đều đã có tiền lệ. Đóng góp cần nằm ở vấn đề được đặc tả, cơ chế, bằng chứng mới và so sánh trực tiếp với prior art. Chưa có cơ sở để viết “lần đầu tiên” ở giai đoạn này.

## 8. Phương pháp ứng viên và phạm vi thuật toán

Đơn vị dữ liệu là dòng sự kiện theo thời gian, với `student × problem × attempt`. Tại một quyết định chỉ được dùng prefix đã quan sát. Nếu người học quay lại bài cũ, không được gom tất cả lần nộp của bài đó thành một vector chứa cả tương lai.

Một mô hình ứng viên có:

- **Bộ mã hóa bằng chứng:** code trước thời điểm quyết định, thay đổi code, loại lỗi, kết quả test, số lần thử và thời gian có xử lý khoảng ngừng.
- **Trạng thái theo bài:** mô tả quá trình sửa bài, được quản lý theo từng bài khi đổi/ngắt/quay lại.
- **Trạng thái tích lũy theo người học:** được huấn luyện để dự báo bài khác; gắn với bài/KC, độ khó và lịch sử.
- **Hai đầu dự báo:** retry ở bài hiện tại và first attempt ở bài khác; thêm outcome trễ chỉ khi log thực sự chứa.
- **Bất định và calibration:** hiệu chỉnh bằng validation, đánh giá trên test; phân biệt uncertainty do thiếu dữ liệu với confidence của phân loại.

Tên gọi hai vector không chứng minh chúng đã tách được hai đại lượng nhận thức thật. Auxiliary loss và kiến trúc hai nhánh chỉ là inductive bias. Phải kiểm tra điều mỗi nhánh thật sự dự báo, khả năng chuyển miền, ablation và các negative control.

Đối với policy, hướng ứng viên là tối ưu giá trị bảo thủ trên tập mô hình người học và tập hành động đủ hỗ trợ:

`maximize_pi min_(M in M_valid) V_M(pi)`

với ràng buộc tập bài khả dụng, prerequisite có căn cứ, và mức lệch so hành vi ghi trong log. `M_valid` chỉ gồm mô hình vượt các kiểm tra định trước. Nếu không đủ bằng chứng ưu tiên bài nào, policy trở về chính sách tham chiếu đã định nghĩa. **Min qua các mô hình không tự tạo một lower confidence bound có bảo đảm**; muốn gọi là bound thống kê phải chứng minh coverage của tập bất định với giả định cụ thể.

Mục tiêu trên là khung nghiên cứu, không phải khẳng định robust optimization đã mới. Phải chứng minh phần sửa objective hoặc cách tạo tập mô hình xử lý failure mode cụ thể tốt hơn các đối chứng.

Thuật toán đối chiếu theo câu hỏi:

| Tình huống | Đối chứng/phương pháp cần có |
|---|---|
| Reward quan sát tức thời; chưa có tín hiệu dài hạn đáng tin | Contextual bandit, difficulty matching, curriculum, behavior cloning |
| Huấn luyện policy trong simulator | PPO/DQN hoặc thuật toán của ExRec, cùng reward và cùng bộ candidate; thêm UNO nếu tái lập được đúng protocol |
| Offline RL từ log có chuỗi/reward và support phù hợp | Fitted Q, CQL/IQL và behavior-constrained baseline; kiểm tra assumptions riêng |
| Log thiếu điều kiện nhận diện | Robust model-based study và sensitivity analysis; không gắn nhãn causal OPE |

[PPO gốc](https://arxiv.org/abs/1707.06347) cần tương tác với môi trường trong vòng huấn luyện. Simulator học từ log có thể cung cấp tương tác đó, nhưng không thay thế bằng chứng phản thực thật. [CQL](https://arxiv.org/abs/2006.04779) giảm quá lạc quan ngoài phân phối; không tự giải biến gây nhiễu ẩn. [Nghiên cứu AISTATS 2024 về offline policy dưới confounding](https://proceedings.mlr.press/v238/kausik24a.html) là đối chiếu quan trọng trước mọi claim nhân quả.

## 9. Thiết kế thực nghiệm đủ mạnh khi không có sinh viên thật

### Tầng A: kiểm định dự báo trên log thật

Target chính cần tách: next-retry của cùng bài và first-attempt của bài khác chưa làm. Một target gần “vận dụng” vẫn chỉ là outcome dự báo; độ khó và cơ chế chọn bài khác có thể gây sai lệch. Không gọi nó là ground truth đầy đủ của tri thức.

Baselines cần phủ những giả thuyết cạnh tranh: item difficulty/IRT; logistic với correctness/attempt/time; BKT/PFA; DKT và simpleKT/AKT; Code-DKT có kiểm tra thứ tự; một baseline code/test mạnh phù hợp schema như TIKTOC hoặc RSSM kiểu CodeInsight. UKT hoặc KCGen-KT chỉ thêm khi đối chiếu đúng câu hỏi và thông tin đầu vào. Dùng [pyKT](https://github.com/pykt-team/pykt-toolkit) để chuẩn hóa các baseline KT phù hợp; không mặc định framework ngăn mọi loại leakage lập trình.

Ablation thông tin: chỉ correctness; thêm counts/time; last code; pooling toàn prefix; ordered edits; đảo thứ tự edits; bỏ test transitions; cùng representation nhưng một/two-state. Dùng permutation hoặc negative control bảo toàn thống kê cần thiết, không coi mọi shuffle là một baseline công bằng nếu nó phá cả chronology.

Protocol:

- Split theo người học; thêm kiểm tra học kỳ/cohort và họ bài khi dữ liệu cho phép. Giữ nhóm code gần trùng hoặc template trong cùng phía khi đánh giá khả năng khái quát họ bài.
- Chronology được bảo toàn trong mọi prefix; không dùng code/test của response đang cần dự đoán làm feature của chính response đó.
- KC discovery, độ khó, normalization, chọn siêu tham số và calibration được fit đúng phía training/validation. Với bài mới, dùng nội dung đề có sẵn; không dùng lời giải tương lai của người học test để tạo nhãn/embedding.
- Tách item đã thấy với item mới: encoder ID và difficulty lookup không được hưởng thông tin test mà phương pháp khác không có.
- Nhiều test trong cùng submission là các nhãn đồng thời; tránh biến chúng thành chuỗi để nhãn trước làm lộ nhãn sau.
- Missing/dropped attempts không tự được gán sai. Report censoring, dropout và phạm vi outcome quan sát được.

Metrics: AUC/AUPRC khi phù hợp imbalance; **NLL và Brier** cho xác suất; calibration plot và ECE có cấu hình rõ; risk–coverage; phân tầng theo độ dài lịch sử, độ khó và cohort. Khoảng tin cậy bootstrap theo sinh viên, không coi triệu submissions là triệu người độc lập. Chọn primary metric trước, báo nhiều seed và ngân sách tuning công bằng.

### Tầng B: mô phỏng có ground truth

Xây nhiều họ thế giới: có/không learning transition, quên, local repair, transfer có hướng theo kỹ năng, trợ giúp/copy, và độ phủ chọn bài khác nhau. Đây là thí nghiệm do ta kiểm soát; không tuyên bố đã giống toàn bộ sinh viên Việt Nam.

Trong mỗi họ, biết được latent transition và return thật nên tính được policy regret, tỷ lệ đảo thứ hạng và độ chính xác của khoảng bất định. Quét cường độ sai mô hình, không chỉ chọn một cấu hình có lợi cho phương pháp mới. Đặc biệt giữ các trường hợp nơi policy tham chiếu thực sự tốt hơn để kiểm tra hệ thống có nhận ra hay không.

Negative controls chính: zero learning; chỉ thêm bằng chứng; chỉ giảm lỗi cú pháp nhưng không chuyển kiến thức; tăng coding ability của LLM simulator mà không đổi hồ sơ học sinh. Không suy ra kết quả cuối cùng chỉ từ một toy null test.

### Tầng C: mô phỏng học từ log và độ bền của xếp hạng policy

Lập ma trận `policy × evaluator` theo REM, rồi kiểm tra ngoài **họ** mô hình dùng để tối ưu, không chỉ ngoài seed. Ví dụ họ probabilistic có cấu trúc, recurrent, attention, state-space. Các evaluator phải đạt chất lượng dự báo tối thiểu tương đương hợp lý; không tạo một mô hình tồi tùy ý rồi dùng nó để phủ nhận policy khác.

Đo worst/quantile return trong tập mô hình đã định nghĩa, rank correlation, rank reversal, sensitivity theo horizon và reward, action-support coverage. Tính nhất quán giữa evaluator là bằng chứng độ bền tương đối; các mô hình vẫn có thể cùng sai và không thay được RCT.

Trên dữ liệu không có phản thực thật, gọi chênh lệch là **bất đồng xếp hạng**, không gọi một xếp hạng là sai khi chưa biết giá trị thật. Nếu dùng NDCG/Recall với bài tiếp theo trong log làm đáp án, metric chủ yếu đo khả năng bắt chước lựa chọn lịch sử; không dùng nó để kết luận bài gợi ý có giá trị học tập cao hơn.

### Tầng D: OPE trên log thật, chỉ khi audit đạt điều kiện

Tại thời điểm `t`, phải làm rõ bài nào có thể chọn, ai chọn, vì sao và outcome nào theo sau. Nếu có propensity thật, giữ lại nguyên vẹn. Nếu chỉ ước lượng behavior policy, phải nêu những biến quyết định bị bỏ sót và độ nhạy của kết quả.

Đối chiếu IPS/SNIPS/DR hoặc estimator tuần tự phù hợp; cross-fitting theo sinh viên, kiểm tra importance-weight tails và effective sample size. Không chọn estimator cho điểm đẹp nhất. DR không cứu thiếu overlap hoặc unobserved confounding.

Khi một lịch học bắt buộc khiến mọi sinh viên ở cùng trạng thái đều nhận một bài, không có dữ liệu để xác định tác động của bài chưa từng được chọn ở trạng thái đó. Embedding nội dung hoặc gộp bài theo độ khó có thể hỗ trợ ngoại suy bằng giả định, không tạo ra overlap đã quan sát. Nếu thiếu điều kiện, tầng D bị bỏ hoặc chuyển thành sensitivity analysis; ba tầng trên vẫn tạo thành một nghiên cứu phương pháp có giới hạn rõ.

## 10. Kiểm toán dữ liệu và bộ dữ liệu đối chiếu

Mỗi dataset tự tìm phải có data dictionary và thống kê trực tiếp từ file. Không chuyển số đếm trong paper thành số đếm của phiên bản tải về khi chưa kiểm chứng. Cần kiểm tra các thuộc tính sau trước khi khóa proposal:

| Trường/thuộc tính | Dùng để làm gì | Nếu thiếu |
|---|---|---|
| ID người học ẩn danh ổn định | Chuỗi lịch sử, split theo người | Không làm learner-specific KT đúng nghĩa |
| ID/phiên bản bài và đề bài | Gom attempts, semantics, họ bài | Khó xác định target mới và độ khó |
| Timestamp/server order | Prefix trước quyết định | Chưa thể bảo đảm đánh giá theo thời gian |
| Mọi lần nộp + code | Phân tích quá trình | Chỉ còn nghiên cứu trên tương tác/kết quả |
| Compile/runtime status, test outcomes | Evidence về lỗi và tiến triển | Dùng aggregate score với claim hẹp hơn |
| Bài khả dụng và nguồn chọn bài | Action space, logging policy | Giới hạn hoặc loại causal OPE |
| Hint/solution/AI assistance khi có | Phân biệt điều kiện làm bài | Thừa nhận biến gây nhiễu và độ nhạy |
| Bài khác, bài kiểm tra hoặc outcome trễ | Dự báo khả năng vận dụng | Không gọi same-item success là transfer |
| Cohort/course/term | Kiểm tra chuyển miền | Chỉ kết luận trong phạm vi quan sát |

**Nguồn chính đã tải và kiểm toán:** [CodeBench UFAM](https://codebench.icomp.ufam.edu.br/dataset/) cho quá trình lập trình Python; [ACcoding trên Zenodo](https://zenodo.org/records/11395043) cho lịch sử submission chủ yếu bằng C. Số liệu thực, phiên bản, điều kiện truy cập và kết quả pilot nằm trong [báo cáo triển khai](Du_lieu_va_thuc_nghiem_de_4.md).

**Nguồn đối chiếu bổ sung:**

- [CodeWorkout/CSEDM](https://sites.google.com/ncsu.edu/csedm-dc-2021/dataset): kiểm tra phiên bản, license và chính xác tập được xuất; Java khác C nên phân tích riêng domain shift.
- [CodeInsight](https://huggingface.co/datasets/CodeInsightTeam/code_insights_csv): rất sát dạng log cần dùng, nhưng quyền truy cập theo yêu cầu, chưa được cấp. Nếu dùng thêm các phiên bản từ cùng nguồn, phải kiểm tra trùng lặp trước khi gọi là external dataset.
- [Project CodeNet](https://github.com/IBM/Project_CodeNet): có user ID và thời gian, hữu ích cho representation/robustness; không tự có learning-gain labels hoặc logging policy giáo dục.
- [ProgSnap2](https://cssplice.org/progsnap2/): **chuẩn định dạng**, không phải một dataset; dùng để tổ chức event, snapshot và metadata.

Hai dataset khác tên nhưng cùng người học hoặc cùng nguồn không phải hai lần tái lập độc lập. Nếu không xin được dataset thứ hai, vẫn phải báo rõ thay vì gọi các random split của một dataset là external validation.

## 11. Tài nguyên tính toán phục vụ câu hỏi nghiên cứu

Kaggle không quyết định mức tham vọng khoa học; nó buộc ta tính chi phí tái lập. Không có căn cứ để hứa một cấu hình GPU hoặc quota cụ thể cho tài khoản người dùng. Kiểm tra GPU thực khi bắt đầu benchmark.

Thiết kế hợp lý: cache code/problem embeddings; huấn luyện state model và policy riêng; checkpoint đầy đủ; chạy nhiều seed cho các phương pháp chính. Sinh KC offline chỉ trên phần dữ liệu cho phép. Một encoder đóng băng với protocol tốt có thể trả lời câu hỏi chính; một mô hình 8B fine-tune không tự làm bằng chứng mạnh hơn.

Chi phí baseline lớn cần báo thật: KCGen-KT ghi dùng L40S 48GB và nhiều giờ cho một run; full reproduction nhiều split/tuning không tương đương chạy một notebook demo. Nếu thay backbone để vừa GPU, gọi đó là **adapted baseline**, ghi rõ khác biệt và cho các phương pháp quyền truy cập thông tin tương đương. Không tuyên bố thắng bản gốc chỉ từ bản rút gọn yếu hơn.

Ưu tiên compute: tính đúng của dữ liệu và split → tái lập baseline mạnh → ablation quyết định → stress tests → tăng kích thước mô hình khi đã thấy nút thắt. Đây là phân bổ bằng chứng nghiên cứu, không phải hạ mục tiêu thành bài tập đơn giản.

## 12. Tiêu chuẩn để tiến tới bài báo

Một bản thảo thuyết phục phải trả lời được:

1. Failure mode nào xuất hiện, khác gì prior art và tác động lên quyết định lớn đến đâu?
2. Cơ chế đề xuất xử lý đúng failure mode đó hay chỉ hưởng nhiều feature/compute hơn?
3. Kết quả tồn tại trên nhiều split/cohort/dataset đủ độc lập, ngoài một simulator thuận lợi hay không?
4. Khi nào phương pháp không hơn baseline và khi nào phải từ chối kết luận?
5. Phần nào là kết quả quan sát, phần nào phụ thuộc giả định, phần nào là ground truth trong simulation?

Các hình nên có: phân kỳ retry-versus-new-problem performance; policy ranking trên các evaluator family; regret theo mức repair/transfer/coverage; calibration và risk–coverage. Các bảng nên có: main results cùng confidence intervals, ablation, chi phí tính toán và giả định OPE.

EDM/AIED/LAK là những cộng đồng phù hợp với learner modeling và đánh giá giáo dục. Nếu có đóng góp phương pháp offline policy đủ tổng quát, có thể cân nhắc venue ML/recommendation phù hợp. Đây là định hướng chuyên môn, không phải xác nhận deadline/call hiện hành hay bảo đảm được nhận.

Điều kiện đổi hướng có căn cứ: nếu không có chronology và repeated attempts, bỏ claim về quá trình; nếu không có bài khác, bỏ claim transfer; nếu không có support, không diễn giải causal policy value. Nếu audit cho thấy cả ba thiếu, đề 5 hoặc đề 9 với một câu hỏi đánh giá hẹp và dữ liệu thật sẽ có cơ sở hơn tiếp tục dựng RL giả lập không kiểm chứng.

**Kết luận lựa chọn:** ưu tiên đề 4 với trọng tâm độ tin cậy của khuyến nghị offline và failure mode ở mức reward/quyết định. Không coi mô hình phức tạp là thay thế cho tính mới và bằng chứng. Công việc tiếp theo về mặt khoa học là khóa câu hỏi/estimand, kiểm toán dữ liệu, rồi tái lập các đối thủ gần trước khi chốt kiến trúc.

## 13. Những nguồn bổ sung nên giữ trong thư mục nghiên cứu

- [simpleKT, ICLR 2023](https://arxiv.org/abs/2302.06881): baseline kiểm tra giá trị của độ phức tạp.
- [TIKTOC, LAK 2025](https://arxiv.org/abs/2410.10829): code và test-case prediction.
- [srcML-DKT, EDM 2025](https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.short-papers.83/index.html): xử lý code lỗi cú pháp, first/all-attempt protocol.
- [KTbench / label leakage](https://arxiv.org/abs/2403.15304): cảnh báo chuyển một event đa-KC thành chuỗi làm lộ nhãn.
- [Using LLMs for KC-level Correctness Labeling](https://arxiv.org/abs/2602.17542): phải phân biệt nhãn hồi cứu từ last attempt với thông tin có sẵn tại first attempt.
- [The Misidentified Identifiability Problem of BKT](https://www.cs.cmu.edu/~shayand/papers/EDM2017.pdf): tránh phát biểu sai rằng mọi KT đều không identifiable; vấn đề ở đây là giả định, diễn giải và giá trị quyết định.
- [Eligible Actions for Off-Policy Evaluation](https://arxiv.org/abs/2207.00632): tập hành động được hỗ trợ và propensity overfitting.
- [ExRec code](https://github.com/oezyurty/ExRec), [UNO code](https://github.com/PengLinzhi/UNO-LPR), [UniER code](https://github.com/chanllon/UniER), [CodeInsight models](https://github.com/aims-foundations/dynamic-irt): kiểm tra commit, license và cấu hình trước khi tái lập; chưa tải/chạy benchmark trong lượt nghiên cứu này.

**Trạng thái của bản tổng quan:** đã hoàn thành đánh giá tài liệu và thiết kế nghiên cứu ban đầu; đã kiểm chứng phép tính null-test. Trạng thái thu thập dữ liệu và các thí nghiệm tiếp theo được ghi riêng trong `research/` và báo cáo dữ liệu mới. Chưa xác nhận tính mới cuối cùng hay tái lập đầy đủ các bảng SOTA.
