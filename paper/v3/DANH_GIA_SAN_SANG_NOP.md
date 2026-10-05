# Đánh giá mức sẵn sàng nộp — bản thảo v3 (28/09/2026)

Tài liệu này trả lời bốn câu hỏi: bài đã hoàn thiện chưa, đã đạt chuẩn để nộp chưa, nhắm Q mấy là hợp lý, và định dạng đã đúng chưa. Đây là đánh giá kỹ thuật và khoa học, **không phải dự báo xác suất được nhận** — quyết định thuộc về biên tập viên và phản biện. Mọi con số về kết quả nghiên cứu trong bản thảo được chèn tự động từ hai run đã xác minh `accoding-learner-v3` và `accoding-policy-v3`; phần nghiên cứu (dữ liệu, mô hình, run) **không thay đổi** trong lần làm việc này.

## 0. Trả lời ngắn

| Câu hỏi | Trả lời |
|---|---|
| Bài đã hoàn thiện chưa? | **Bản thảo đã đầy đủ** mọi phần của một bài nghiên cứu (31 trang A4, 6 hình, 4 bảng, 2 mệnh đề có chứng minh, 73 tài liệu tham khảo đã xác minh). **Chưa hoàn thiện để nộp**: còn các việc chỉ tác giả làm được (tên, đơn vị, khai báo, kho mã, đọc duyệt toàn bộ). |
| Đạt chuẩn để nộp chưa? | **Về định dạng: đạt** các yêu cầu có thể kiểm tra của *Computers and Education: Artificial Intelligence* (C&E:AI). **Về khoa học: đủ để gửi phản biện** ở tạp chí Q1 chuyên ngành, nhưng với một bộ dữ liệu, không có phân tích độ nhạy và chưa thử biện pháp khắc phục, khả năng bị yêu cầu sửa lớn hoặc bị từ chối là đáng kể. |
| Q mấy là hợp lý? | Q1 là mục tiêu hợp lý **về chủ đề và mức chặt chẽ**, nhưng nên chọn tạp chí Q1 chuyên ngành phù hợp nhất (IJAIED, UMUAI) trước C&E:AI. Nếu làm thêm 3 việc ở Mục 6 (tái lập trên CodeBench, phân tích độ nhạy, thử một biện pháp khắc phục), cơ hội ở Q1 tăng rõ rệt. Phương án an toàn: JEDM (Q3 theo SJR 2024 nhưng là tạp chí chuyên ngành uy tín, không thu phí) hoặc bản rút gọn ở hội nghị EDM/AIED. |
| Format đúng chưa? | **Đúng với bản nộp**: template LaTeX chính thức của Elsevier (`elsarticle`), một cột, 12pt, A4, tài liệu tham khảo APA 7, phụ lục đánh số A/B (Table C.1), trang tiêu đề tách riêng, hình nộp thành tệp riêng `Figure_1…6`. Bản in cuối (2 cột, chữ 8pt) do nhà xuất bản dàn trang sau khi nhận bài — tác giả **không** tự làm giống bản in. |

## 1. Những gì đã làm trong lần này

**Bản thảo tiếng Việt** (`paper/v3/vi/`, PDF: `output/pdf/retrylab-v3-ban-thao-tieng-viet.pdf`, 32 trang): dịch đầy đủ mọi mục, bảng, phụ lục và chú thích hình; hình vẽ lại với nhãn tiếng Việt và dấu thập phân kiểu Việt (0,775); số liệu điền tự động như bản tiếng Anh; tài liệu tham khảo giữ chuẩn APA, trích dẫn trong văn bản dùng "và", "và cộng sự". Đây là **bản dịch làm việc** để học, báo cáo, bảo vệ — không phải bản nộp (C&E:AI chỉ nhận tiếng Anh).

**Sửa bản tiếng Anh theo Guide for Authors của C&E:AI** (bảng đối chiếu ở Mục 2):

- Khổ giấy: trước là US Letter (216 × 279 mm) dù để tùy chọn a4paper — XeTeX bỏ qua tùy chọn đó; nay là A4 thật.
- Tài liệu tham khảo: trước là kiểu Harvard của Elsevier và chỉ **29 mục** (dưới phân vị 10 của C&E:AI — xem Mục 4); nay **APA 7** do `apa_refs.py` sinh (danh sách tác giả đầy đủ tới 20 người, "[Preprint]" + DOI arXiv, "[dataset]" cho bộ dữ liệu, sắp xếp theo APA), **73 mục** đều đã kiểm tra ở Crossref/DataCite/ERIC (đọc số trang in trên PDF)/JEDM/PMLR/NeurIPS/JMLR/arXiv. Build từ chối nếu có trích dẫn thiếu mục hoặc mục không được trích.
- Phụ lục: bảng phụ lục nay đánh số Table C.1, D.1 (trước theo số của thân bài); thêm Phụ lục A (chứng minh), phương trình (A.1), (A.2).
- Trang tiêu đề tách riêng (`title_page.tex`/`.pdf`) cho phản biện ẩn danh hai chiều; bản thảo không còn chi tiết định danh (đã bỏ cụm "by our group").
- Mục khai báo AI đổi đúng tên và câu mẫu của nhà xuất bản ("…in the manuscript preparation process"), đặt trước References; tách Data availability và Ethics; tài trợ, xung đột lợi ích, CRediT, lời cảm ơn chuyển sang trang tiêu đề.
- Hình: bỏ các dòng chú thích nằm trong ảnh, chuyển vào caption (Guide yêu cầu tối thiểu chữ trong hình); thêm nhãn panel (a)(b)(c); nộp thành tệp vector riêng `Figure_1.pdf … Figure_6.pdf`.
- Ghi chú bảng đặt **dưới** thân bảng (Guide yêu cầu).
- Highlights sinh từ số liệu run, build kiểm tra 3–5 dòng, mỗi dòng ≤ 85 ký tự (hiện tối đa 83).

**Sửa nội dung để tránh bị phản biện bắt lỗi:**

- Thêm **Mệnh đề 1** (mô hình Bayes nhất quán không học ⇒ độ trôi = 0) và **Mệnh đề 2** (trong chính bộ mô phỏng, tiến bộ kỳ vọng = độ trôi tích lũy), chứng minh ở Phụ lục A, và một kiểm tra thực nghiệm: trong DKT-A, phần bất ngờ trung bình −0,70 đến 0,00 điểm %, cách 0 tối đa 2,3 sai số chuẩn Monte Carlo, trong khi độ trôi tích lũy của PPO là 29,0 điểm %. Điều này biến quan sát thực nghiệm (H3) thành một kết quả có giải thích hình thức.
- **Sửa hai phát biểu quá mức.** (1) Highlight cũ "RL gains vanish in independent worlds" và phiên bản giữa chừng "≤0,3 pp in independent worlds" là **sai phạm vi**: ở bản song sinh DKT và SAKT-B, PPO thưởng KT vẫn hơn ngẫu nhiên +10,07 và +5,87 điểm %; phát biểu đúng là "trong các thế giới có học ẩn" (≤ 0,35, làm tròn lên để giới hạn trên không bị nói thấp). (2) "Agents trained with an explicit learning model are the most robust" nay nói rõ: chỉ trong họ thế giới ẩn có chung cấu trúc logistic cộng; ở DKT-B chúng **kém** ngẫu nhiên (−0,86 và −1,31 điểm %).
- Ghi nhãn **khẳng định / thăm dò**: H1–H4 là khẳng định; độ ổn định thứ hạng (Kendall τ), độ bền trường hợp xấu nhất, tương quan độ trôi, chuỗi tiếp diễn thật là thăm dò (protocol không đăng ký trước các phân tích này).
- Mở rộng phần tổng quan thành 4 tiểu mục, định vị rõ so với Lee & Brunskill (2012), Rollinson & Brunskill (2015), ma trận đánh giá bền vững (Doroudi và cộng sự, 2017), khai thác sai số mô hình trong RL dựa trên mô hình và tối ưu quá mức phần thưởng; thêm mục Thảo luận "Relation to model exploitation" và biện pháp khắc phục có thể kiểm định.
- Giới hạn viết đầy đủ hơn: 3 seed, khoảng tin cậy có điều kiện, tương quan trên các chính sách không độc lập, chưa phân tích độ nhạy, một trường đại học.
- Mọi con số trước đây còn gõ tay (ví dụ "about 1.5 pp") nay sinh từ run; các cận "at most" được làm tròn ra ngoài.

**Kiểm tra tự động** (`paper/v3/build.py`, bản ghi `paper/v3/build_record.json`): xác minh hai run qua harness; biên dịch Tectonic (XeLaTeX) bản Anh, bản Việt, gói nộp và trang tiêu đề; dừng nếu có tham chiếu/trích dẫn chưa định nghĩa, thiếu glyph, nhãn trùng, tóm tắt > 250 từ, từ khóa ngoài 1–7, highlights sai quy tắc. Lần build cuối: không lỗi, không hộp tràn > 5 pt. Harness `fast` và `policy` đạt; `verify-run` hai run đạt.

## 2. Đối chiếu định dạng với Guide for Authors của C&E:AI

Nguồn: bản chụp hướng dẫn trong `paper/journal/references/publisher-and-ranking-snapshot.md` (lấy 26/09/2026). Hướng dẫn có thể đổi — **kiểm tra lại ngay trước khi nộp**.

| Yêu cầu của Guide | Hiện trạng | Còn phải làm |
|---|---|---|
| Nguồn chỉnh sửa được (.tex), PDF không thay nguồn | `submission/manuscript.tex` biên dịch độc lập cùng `Figure_N.pdf` | — |
| Phản biện ẩn danh hai chiều: trang tiêu đề và bản thảo ẩn danh là hai tệp | `submission/title_page.tex` + bản thảo không tên | Tác giả điền tên, đơn vị, email, tác giả liên hệ |
| Tóm tắt ≤ 250 từ, đứng độc lập, không trích dẫn | 245 từ (build đếm), không trích dẫn | — |
| 1–7 từ khóa tiếng Anh, tránh cụm có "and/of" | 6 từ khóa | — |
| Highlights 3–5 dòng, ≤ 85 ký tự, tệp riêng có chữ "highlights" | 5 dòng, tối đa 83 ký tự, `highlights.txt` | — |
| Graphical abstract (khuyến khích, không bắt buộc) | **Không làm** | Nếu muốn, tác giả tự vẽ: Elsevier **cấm** dùng AI tạo sinh/hỗ trợ bởi AI để làm graphical abstract |
| Công thức, bảng dạng văn bản; bảng không kẻ dọc, không tô nền; ghi chú dưới bảng | booktabs, không kẻ dọc; ghi chú dưới bảng | — |
| Hình nộp thành tệp riêng `Figure_1…`; caption có tiêu đề ngắn (không in trong hình) + mô tả; ít chữ trong hình | 6 tệp vector PDF, font nhúng; chú thích chuyển ra caption | Xem rủi ro chính sách AI với hình (Mục 5) |
| Mục đánh số 1, 1.1; tham chiếu chéo theo số | Có | — |
| Phụ lục A, B…; phương trình (A.1); bảng Table A.1 | Có (Table C.1, D.1; Eq. A.1–A.2) | — |
| Tài liệu tham khảo APA 7, xếp chữ cái rồi năm, a/b cho cùng tác giả-năm, DOI dạng link, preprint ghi rõ, dữ liệu có "[dataset]" | Có, sinh tự động, 73 mục, 1–1 với trích dẫn | Tác giả đọc lại danh mục |
| Mục khai báo AI tạo sinh trước References, đúng tên mục | Có, đúng tên và câu mẫu | **Tác giả xác nhận/sửa cho đúng thực tế** |
| Research data — Option B: gửi kho, trích dẫn, liên kết | Có câu Data availability; bộ dữ liệu được trích dẫn | Tạo kho mã/kết quả (ẩn danh khi phản biện, ví dụ OSF view-only) và thay câu "upon acceptance" bằng liên kết |
| CRediT, tài trợ, xung đột lợi ích, lời cảm ơn | Khung sẵn trong trang tiêu đề | Tác giả điền; lời cảm ơn chỉ ở trang tiêu đề |
| Giới hạn độ dài | Guide không nêu giới hạn cứng số từ | Thân bài ≈ 5.300 từ; toàn bài ≈ 8.700 từ kể cả tài liệu tham khảo |
| Không yêu cầu giãn dòng đôi / đánh số dòng | 12pt, một cột, giãn dòng 1,2 | — |

**So với một bài đã xuất bản.** Đã đo bài C&E:AI của Minn (2022) (bản PDF xuất bản, giấy phép CC BY, lưu ở `paper/journal/references/`): A4, **hai cột, chữ Charis 8pt, khoảng dòng ~10,5 pt, lề ~12–13 mm**, 13 trang cho ~12.400 từ. Bản thảo của chúng ta: A4, **một cột, Latin Modern 12pt, khoảng dòng ~14,5 pt**, 31 trang. Khác biệt này là đúng quy trình: tác giả nộp theo template (Elsevier cho phép LaTeX một hoặc hai cột ở bản nộp), nhà xuất bản dàn trang lại khi bài được nhận. Cấu trúc các mục cuối của bài xuất bản (Declaration of competing interest, Acknowledgment, References) khớp với cách chúng ta tách: phần định danh ở trang tiêu đề, phần còn lại trong bản thảo.

## 3. Đánh giá khoa học theo góc nhìn phản biện

**Điểm mạnh** (đáng kể với chuẩn Q1):

- Protocol khóa trước khi nạp một quần thể chưa từng dùng; 4 giả thuyết đăng ký trước, đều được ủng hộ; tách rõ khẳng định và thăm dò.
- Thiết kế đánh giá có sức chẩn đoán: 9 thế giới, một **đối chứng âm** biết chắc tiến bộ thật bằng 0, phép **phân rã chính xác** và hai mệnh đề giải thích vì sao tiến bộ trong mô phỏng bằng độ trôi.
- Dữ liệu thật quy mô lớn (562.912 lần nộp đầu, 4.634 người học), khoảng tin cậy bootstrap theo người học/lượt, báo cáo cả kết quả bất lợi.
- Tái lập hoàn toàn: mọi số trong bài sinh từ run có mã băm; hình có bảng CSV đi kèm.
- Đóng góp có tính khái quát cho cộng đồng (bốn kiểm tra rẻ cho mọi đánh giá dựa trên mô phỏng).

**Điểm yếu mà phản biện Q1 gần như chắc chắn nêu** (xếp theo mức nghiêm trọng):

1. **Một bộ dữ liệu, một trường, một ngôn ngữ (C).** Kết luận về "các pipeline KT–RL" cần ít nhất một lần tái lập độc lập. Dữ liệu CodeBench (Python, UFAM) đã có sẵn trong máy (`data/raw/codebench`, 471 người học, 235 bài), chưa rõ giấy phép phân phối lại nhưng dùng để phân tích được.
2. **Chưa phân tích độ nhạy**: chân trời 10 bài, trọng số công sức λ = 0,05, quy tắc tập ứng viên, kiến trúc tracker. Phản biện sẽ hỏi kết luận có đổi khi các lựa chọn này đổi không.
3. **Mới chẩn đoán, chưa chữa**: bài chỉ ra vấn đề và đề xuất kiểm tra, nhưng chưa thử biện pháp (ví dụ phạt độ bất đồng giữa DKT và bản song sinh). Câu hỏi "vậy nên làm gì?" chỉ được trả lời bằng đề xuất.
4. **Thế giới ẩn cùng họ AFM**: phần "RL học được gì" có điều kiện (đã ghi rõ trong bài, nhưng vẫn làm yếu thông điệp tích cực).
5. **Thống kê**: 3 seed huấn luyện; khoảng tin cậy có điều kiện trên mô hình đã fit; tương quan Spearman trên 14 chính sách không độc lập. Đã nêu trong Giới hạn; phản biện khó tính có thể yêu cầu thêm seed.
6. **Đề tài yêu cầu "thời gian giải"**, bài đo công sức bằng số lượt nộp (log không có thời gian làm bài đáng tin). Đã nêu.
7. **Không thử với người học thật.** Chấp nhận được với một bài phương pháp đánh giá (bài nói rõ mọi kết quả chính sách là mô phỏng), nhưng ở C&E:AI — tạp chí thiên về hàm ý giáo dục — đây là rủi ro bị từ chối ngay ở vòng biên tập.
8. **Mệnh đề đơn giản về toán** (tính chất martingale). Giá trị nằm ở ứng dụng và diễn giải; nên trình bày như công cụ chẩn đoán, không như định lý sâu (bản hiện tại đã làm vậy).

## 4. Nhắm Q mấy là hợp lý

**Hệ xếp hạng.** "Q" có hai hệ: SJR (SCImago, dữ liệu Scopus) và JCR (Clarivate, Web of Science); quartile phụ thuộc năm và ngành. Kiểm tra với trường/khoa xem họ công nhận hệ nào. Các nhãn dưới đây là **SJR 2024** đã đọc trực tiếp trên SCImago ngày 26/09/2026. Hôm nay (28/09/2026) SCImago chặn truy cập tự động nên **chưa kiểm chứng được SJR 2025** (theo kết quả tìm kiếm, SCImago đã hiển thị dữ liệu 2025) — mở scimagojr.com kiểm tra lại trước khi quyết định.

| Nơi nộp | Hạng (đã kiểm chứng) | Độ phù hợp với bài này |
|---|---|---|
| **IJAIED** (Int. J. of AI in Education; chuyển sang Elsevier từ 01/01/2026) | Q1 — SJR 2024 (Education; E-learning; Computational Theory) | **Cao nhất**: RL cho sắp xếp trình tự dạy học và đánh giá mô hình người học là chủ đề cốt lõi; tổng quan của Doroudi (2019) và Riedmann (2025) đều đăng ở đây |
| **UMUAI** (User Modeling and User-Adapted Interaction) | Q1 theo trang tổng hợp, **chưa đọc trực tiếp trên SCImago** | Cao: mô hình người học (Corbett & Anderson 1994, Chi 2011, Pelánek 2017 đều đăng ở đây) |
| **C&E:AI** (mục tiêu hiện tại của bản thảo) | Q1 — SJR 2024 = 5,217, **hạng 1/1.597** trong ngành Education | Trung bình: phạm vi có "personalized and intelligent educational systems", nhưng tạp chí rất cạnh tranh và chủ yếu đăng bài về AI tạo sinh, năng lực AI; bài nặng phương pháp, không có học sinh thật dễ bị hỏi về hàm ý giáo dục |
| IEEE TLT | Q1 — SJR 2024 | Trung bình: giới hạn 14 trang hai cột, phản biện một chiều |
| ACM TOCE | Q1 — SJR 2024 | Thấp hơn: cần hàm ý cho dạy-học lập trình rõ hơn |
| **JEDM** | **Q3** — SJR 2024 | Rất phù hợp về phương pháp; uy tín trong cộng đồng EDM, không phí; nhưng nhãn Q3 |
| Hội nghị EDM (CORE B) / AIED (CORE A) | Không phải hệ Q | Bản rút gọn 10–14 trang, nhanh có phản hồi |

**Khuyến nghị.** Với chất lượng hiện tại, đặt mục tiêu **Q1 chuyên ngành (IJAIED hoặc UMUAI)** là hợp lý; C&E:AI để sau hoặc chỉ khi bổ sung được các việc ở Mục 6 và làm đậm hàm ý giáo dục. Nếu cần kết quả chắc và nhanh (ví dụ cho môn học), JEDM hoặc một hội nghị là lựa chọn an toàn. Không có cơ sở để hứa "chắc chắn Q1": bài hiện có 1 bộ dữ liệu và chưa có phân tích độ nhạy — hai lý do thường gặp nhất khiến bài phương pháp bị yêu cầu sửa lớn. Nếu chuyển tạp chí, phải đổi định dạng theo hướng dẫn của tạp chí mới (ví dụ JEDM dùng template riêng; TLT dùng template IEEE).

**Số liệu đối chứng (OpenAlex, bài nghiên cứu 2024–2025)** về số tài liệu tham khảo: C&E:AI trung vị 63 (IQR 44–87, n = 299; phân vị 10 = 33); IJAIED 52 (41–69); TOCE 52; TLT 51; UMUAI 53. Bản thảo cũ (29 mục) nằm dưới phân vị 10 của C&E:AI — dấu hiệu "tổng quan mỏng"; bản hiện tại 73 mục.

## 5. Rủi ro chính sách cần tác giả quyết định

- **AI trong chuẩn bị bản thảo.** Elsevier cho phép dùng công cụ AI nhưng không được thay thế tư duy phê phán của con người; tác giả chịu trách nhiệm toàn bộ nội dung và phải khai báo. Công trình này (mã, thí nghiệm, bản thảo) được làm với sự hỗ trợ lớn của trợ lý AI. Trước khi nộp, người đứng tên cần **tự đọc, hiểu và bảo vệ được** từng phương pháp, phép tính và kết luận, sửa văn phong theo ý mình, và giữ câu khai báo trung thực.
- **Hình vẽ.** Elsevier: "không cho phép dùng AI tạo sinh hoặc công cụ hỗ trợ bởi AI để tạo hay chỉnh sửa hình". Các hình của bài là biểu đồ dữ liệu do matplotlib kết xuất tất định từ kết quả run; mã vẽ được viết với trợ giúp của AI. Đây là vùng xám: câu khai báo đã nêu "analysis and plotting code"; nếu muốn chắc chắn, tác giả có thể tự viết lại mã vẽ hoặc hỏi ban biên tập trước khi nộp. Graphical abstract thì bị cấm rõ ràng nếu có AI tham gia — vì vậy không làm.
- **Công bố trùng lặp.** Khi nộp Elsevier, tác giả cam kết bài chưa và sẽ không đăng ở nơi khác "bằng tiếng Anh hay bất kỳ ngôn ngữ nào". Bản tiếng Việt dùng làm báo cáo môn học/luận văn thì được (Guide loại trừ "academic thesis"), nhưng **không đăng bản tiếng Việt lên một tạp chí** trong khi bài tiếng Anh đang được xét.
- **Quyền tác giả.** Ai đủ tiêu chí tác giả (thiết kế, phân tích, viết, duyệt cuối) — ví dụ giảng viên hướng dẫn — là quyết định của nhóm; AI không được đứng tên.
- **Ẩn danh.** Kho mã gửi kèm phản biện phải ẩn danh (không lộ tên người dùng, đường dẫn máy, tên dự án cá nhân).
- **Phí xuất bản.** C&E:AI là tạp chí truy cập mở có phí (APC); mức phí chưa được kiểm tra trong lần này.

## 6. Lộ trình để tăng sức nặng khoa học (chưa làm — chờ quyết định)

Mỗi việc là một nghiên cứu mới có protocol và run riêng trong harness (không sửa run v3 đã khóa), chạy bằng CPU trên máy hiện tại.

1. **Tái lập trên CodeBench (Python)** — v4: bộ chuyển dữ liệu (lần nộp đầu, nhóm kỹ năng theo bài/đợt), fit 6 mô hình, chạy lại ma trận đánh giá với đối chứng âm; khóa protocol trước khi xem kết quả. Đây là việc có giá trị nhất cho phản biện Q1.
2. **Phân tích độ nhạy** — chân trời 20 bài, λ ∈ {0; 0,2}, thêm seed; báo cáo H1–H3 có giữ không.
3. **Thử một biện pháp khắc phục** — phần thưởng phạt độ bất đồng giữa DKT và bản song sinh (kiểu MOPO/ensemble), xem tiến bộ ảo có giảm và tiến bộ ở thế giới ẩn có tăng không.
4. (Tùy chọn) Nghiên cứu nhỏ với học sinh — cần phê duyệt đạo đức; ngoài phạm vi hiện tại.

## 7. Việc tác giả phải làm trước khi bấm nộp

Xem `SUBMISSION_CHECKLIST.md` (đã cập nhật). Tóm tắt: điền trang tiêu đề; xác nhận khai báo AI; điền CRediT, tài trợ, xung đột lợi ích; tạo kho mã ẩn danh và cập nhật Data availability; hoàn thiện thư gửi biên tập (`cover_letter_draft.md`); đọc duyệt toàn bộ bản tiếng Anh; kiểm tra lại Guide, hạng tạp chí và phí ngay trước khi nộp.

## 8. Tệp bàn giao

| Tệp | Nội dung |
|---|---|
| `output/pdf/retrylab-v3-manuscript.pdf` | Bản thảo tiếng Anh (31 trang, A4) |
| `output/pdf/retrylab-v3-ban-thao-tieng-viet.pdf` | Bản thảo tiếng Việt (32 trang, A4) |
| `paper/v3/submission/` | Gói nộp: `manuscript.tex/pdf` ẩn danh, `title_page.tex/pdf`, `highlights.txt`, `Figure_1–6.pdf`, `supplementary/*.csv`, `cover_letter_draft.md`, `README.md` |
| `paper/v3/build.py`, `apa_refs.py`, `references.bib` | Dựng lại cả hai bản và gói nộp; tài liệu tham khảo APA 7 |
| `paper/v3/build_record.json` | Mã băm run, số từ tóm tắt, số tài liệu, kết quả biên dịch và kiểm tra |
