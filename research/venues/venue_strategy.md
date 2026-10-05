# Chiến lược công bố cho nghiên cứu cập nhật mô hình người học từ lịch sử lập trình

Ngày kiểm tra nguồn: **26/09/2026**. Phạm vi: dữ liệu lịch sử ACcoding và CodeBench; chưa có thử nghiệm can thiệp với sinh viên thật. Đây là đánh giá mức độ phù hợp và yêu cầu bản thảo, không phải dự báo xác suất được nhận. Không gửi bài, liên hệ ban biên tập, đăng preprint hay cam kết phí xuất bản trong lần làm việc này.

## 1. Quyết định đề xuất

**Mục tiêu chính: International Journal of Artificial Intelligence in Education (IJAIED).** Vấn đề cập nhật mô hình người học, phân biệt tín hiệu sửa cùng bài với dự báo bài khác, và hệ quả của cập nhật đối với khuyến nghị phù hợp trực tiếp với student modelling, cognitive diagnosis và evaluation of AIED systems. Một nghiên cứu phương pháp có đánh giá offline chặt chẽ có thể phù hợp; không cần biến kết quả dự báo thành tuyên bố đã cải thiện học tập. Nguồn chính thức của tạp chí liệt kê rõ các chủ đề này trong [phạm vi và hướng dẫn hiện hành](https://www.sciencedirect.com/journal/international-journal-of-artificial-intelligence-in-education/publish/guide-for-authors).

**Mục tiêu thứ hai: ACM Transactions on Computing Education (TOCE).** Phù hợp nếu câu chuyện cuối cùng cung cấp hiểu biết có giá trị cho việc học lập trình: khi nào thông tin từ sửa code đáng tin, bối cảnh bài tập và ngôn ngữ ảnh hưởng thế nào, và người thiết kế hệ thống nên thay đổi quy trình đánh giá ra sao. Chỉ thêm một mô hình dự báo tốt hơn sẽ yếu; phải giải thích đóng góp cho computing education. [Phạm vi TOCE](https://dl.acm.org/journal/toce) yêu cầu công nghệ giáo dục gắn trực tiếp với học computing, được đặt trong nghiên cứu trước đó, có câu hỏi và phương pháp nghiên cứu.

**Lựa chọn thứ ba theo độ phù hợp chuyên môn: Journal of Educational Data Mining (JEDM).** Đây là nơi phù hợp cho một nghiên cứu kiểm định phương pháp đo, tái lập và so sánh đánh giá trên nhiều bộ dữ liệu. Tuy nhiên, bảng SJR 2024 đọc được trực tiếp xếp JEDM Q3; không giới thiệu nó như phương án Q1/Q2. JEDM yêu cầu đóng góp có khả năng khái quát ngoài một ứng dụng đơn lẻ và khuyến khích công khai mã, dữ liệu và kết quả trung gian. [Phạm vi và tiêu chí phản biện JEDM](https://jedm.educationaldatamining.org/index.php/JEDM/about).

Nếu công trình có **một phương pháp khắc phục có nguyên lý rõ, vượt kiểm định trên nhiều mô hình và nhiều tập dữ liệu, đồng thời chứng minh ảnh hưởng tới chất lượng quyết định**, IEEE TLT hoặc một hội nghị như AIED/RecSys trở nên đáng cân nhắc. AAAI là mục tiêu cao hơn có điều kiện; chưa có cơ sở coi một pilot logistic regression hay một ví dụ giả lập là đóng góp đạt ngưỡng A*.

## 2. Q1, Q2 và A* là những hệ khác nhau

- **JCR quartile** thuộc Journal Citation Reports của Clarivate, phụ thuộc năm và ngành. Impact Factor không tự xác định quartile nếu thiếu bảng phân hạng ngành.
- **SJR quartile** thuộc SCImago và dữ liệu Scopus; không phải JCR. Một tạp chí có thể có nhiều quartile theo ngành.
- **CORE/ICORE A*, A, B, C** phân hạng hội nghị; không chuyển đổi thành Q1/Q2 của tạp chí.
- Chất lượng của từng bài và độ phù hợp chuyên môn không được suy ra từ nhãn của nơi xuất bản.

Các trang SCImago lấy được trong lần kiểm tra này có nhãn rõ **SJR 2024**. Bảng dưới chỉ báo cáo đúng năm đó; không gọi là “Q1 năm 2026”, cũng không khẳng định đây là năm xếp hạng mới nhất đang tồn tại. Không sử dụng số “Impact IF” của trang tổng hợp như JCR Impact Factor.

| Tạp chí | Bằng chứng quartile đọc trực tiếp | Cách diễn đạt được phép |
|---|---|---|
| IJAIED | SJR 2024: Q1 ở Computational Theory and Mathematics; Education; E-learning | “IJAIED thuộc Q1 theo SJR 2024 trong các ngành được liệt kê” |
| TOCE | SJR 2024: Q1 ở Computer Science (miscellaneous); Education | “TOCE thuộc Q1 theo SJR 2024” |
| IEEE TLT | SJR 2024: Q1 ở Computer Science Applications; Education; E-learning; Engineering (miscellaneous) | “TLT thuộc Q1 theo SJR 2024”; không suy ra JCR |
| JEDM | SJR 2024: Q3 ở Artificial Intelligence; Computer Science Applications; Education | “JEDM là tạp chí chuyên ngành EDM; snapshot SJR 2024 là Q3” |
| Computers and Education: Artificial Intelligence | Trang xếp hạng SCImago có kết quả Q1 nhưng lần lấy nội dung này chưa xác nhận đủ năm + hàng category trên hồ sơ tạp chí | Không gán một quartile/năm chắc chắn trong quyết định này |

Nguồn gốc dữ liệu: [SCImago IJAIED](https://www.scimagojr.com/journalsearch.php?q=19600156811&tip=sid), [SCImago TOCE](https://www.scimagojr.com/journalsearch.php?q=19700183047&tip=sid), [SCImago TLT](https://www.scimagojr.com/journalsearch.php?q=19700167026&tip=sid), [SCImago JEDM](https://www.scimagojr.com/journalsearch.php?q=21101042013&tip=sid). **JCR hiện hành chưa được xác minh trong lần tra cứu này.** Nếu cơ sở đào tạo yêu cầu Q1/Q2 theo JCR, cần đối chiếu đúng hồ sơ JCR và năm được cơ sở chấp nhận trước khi chọn nơi nộp.

Hệ ICORE hiện hành có trang thông báo [ICORE 2026 Ranking Released](https://www.core.edu.au/icore-portal/icore-portal-2026-rankings-updates). Các bản ghi chính thức được kiểm tra:

| Hội nghị | Nhãn trên ICORE2026 | Phù hợp với công trình này |
|---|---|---|
| [AAAI](https://portal.core.edu.au/conf-ranks/1629/) | **A*** | Chỉ ưu tiên khi đóng góp AI có tính tổng quát, có lý thuyết hoặc phương pháp mới và đánh giá đủ mạnh |
| [ACM RecSys](https://portal.core.edu.au/conf-ranks/?by=all&page=1&search=recsys&sort=atitle) | **A** | Cần đóng góp thực chất về đánh giá/ra quyết định khuyến nghị; dự báo đúng-sai đơn thuần chưa đủ |
| [AIED](https://portal.core.edu.au/conf-ranks/?by=all&page=1&search=aied&sort=atitle) | **A** | Rất phù hợp về người học, hệ thống thích ứng, đánh giá AI giáo dục |
| [LAK](https://portal.core.edu.au/conf-ranks/?by=all&page=1&search=learning+analytics&sort=atitle) | **A** | Phù hợp khi liên kết chặt với lý thuyết học, diễn giải dữ liệu và tác động thiết kế hệ thống |
| [EDM](https://portal.core.edu.au/conf-ranks/446/) | **B** | Rất phù hợp về phương pháp và dữ liệu; nhãn B không làm mất giá trị chuyên môn của một kết quả tốt |

Các nhãn trên là nhãn của **hội nghị chính**, không tự áp dụng cho workshop hoặc một bài bất kỳ.

## 3. Form và chính sách tạp chí đã kiểm tra

### IJAIED: cần dùng hướng dẫn Elsevier từ 2026

**IJAIED đã chuyển từ Springer sang Elsevier từ 01/01/2026.** [Trang Springer](https://link.springer.com/journal/40593) xác nhận việc chuyển. Vì vậy, template và quy trình Springer cũ không phải hướng dẫn nộp bài hiện hành của tạp chí này; AIED conference vẫn là một nơi xuất bản khác.

Theo [Guide for authors của IJAIED](https://www.sciencedirect.com/journal/international-journal-of-artificial-intelligence-in-education/publish/guide-for-authors):

- Phản biện double anonymized, thông thường ít nhất hai người phản biện độc lập.
- Abstract tối đa 250 từ, 1–7 keywords. Không tìm thấy giới hạn cứng tổng số từ/trang trên trang hướng dẫn lấy được; không tự gán giới hạn của nhà xuất bản cũ.
- Cần nguồn có thể biên tập `.doc/.docx` hoặc `.tex`; PDF không thay thế source file. Word dùng một cột; hướng dẫn cho phép hai cột với LaTeX.
- Chính sách research data là Option A: khuyến khích lưu dữ liệu ở kho phù hợp và trích dẫn bộ dữ liệu. Đây không phải yêu cầu được phép phân phối lại mọi dữ liệu bên thứ ba.
- Cần khai báo việc dùng generative AI trong chuẩn bị bản thảo; AI không là tác giả. Người đứng tên phải kiểm tra, chỉnh sửa và chịu trách nhiệm khoa học. Không ghi trong bản nháp rằng bước kiểm tra của tác giả con người đã hoàn tất nếu chưa xảy ra.

### TOCE

Theo [Author guidelines của TOCE](https://dl.acm.org/journal/toce/author-guidelines):

- ACM journal template; bản review theo quy trình ACM dùng một cột. Có thể dùng `acmart` với `manuscript, review, anonymous`.
- Double-anonymous. Cần xử lý danh tính trong bản thảo và artifact, không chỉ bỏ tên trên trang đầu.
- **Không có giới hạn cứng số trang/từ**; hướng dẫn cho biết đa số bài khoảng 15–25 trang journal. Đây là mô tả phổ biến, không phải mức tối thiểu hay trần bắt buộc.
- Từ tháng 05/2026, tạp chí yêu cầu trích dẫn author–year; LaTeX dùng `\citestyle{acmauthoryear}`.
- Khuyến khích báo cáo phương pháp theo chuẩn phù hợp, ví dụ APA JARS khi thích hợp; khuyến khích software/data artifacts. Cần khai báo dùng AI theo chính sách ACM.
- Bài về lập trình phải đưa ra tri thức cho computing education; không nên lấy số lượng lớp mô hình hay số bảng ablation thay cho ý nghĩa giáo dục.

### JEDM

Theo [Submission guidelines](https://jedm.educationaldatamining.org/index.php/JEDM/about/submissions) và [Information for authors](https://jedm.educationaldatamining.org/index.php/JEDM/information/authors):

- Nộp PDF theo template của JEDM; trang tác giả liên kết gói LaTeX `2024_08_02_jedm-latex.zip`. Không tìm thấy giới hạn cứng trang/từ trên các trang này; không coi đó là xác nhận được phép dài vô hạn.
- Có thể nộp bản ẩn danh để được double-blind; hướng dẫn chung của tạp chí mô tả ba phản biện ẩn danh cho bài qua vòng đánh giá đầy đủ.
- Khuyến khích mã có thể lưu trữ, trích dẫn và tái lập, dữ liệu và kết quả trung gian. Không thu phí xuất bản theo trang chính thức.
- Bài mở rộng từ hội nghị phải có ít nhất 1/3 nội dung mới, giải thích đóng góp mới và xử lý quyền sử dụng nội dung; đây không phải lời khuyên chia nhỏ công trình.
- Có mục khai báo AI trước References, nêu công cụ, mục đã dùng và mục đích. Người đứng tên chịu trách nhiệm nội dung.

### IEEE Transactions on Learning Technologies

Theo [TLT author resources](https://ieee-edusociety.org/publication/tlt/tlt-author-resources) và [giới thiệu TLT](https://ieee-edusociety.org/publication/about-publications/tlt):

- Từ 01/01/2025, regular paper tối đa 14 trang, short 8, survey/tutorial 18, tính theo bản IEEE hai cột sau production. Có quy định phí quá trang; không tự suy ra số trang source một cột.
- Single-anonymous; reviewer biết tác giả. Phải dùng template TLT lấy qua IEEE Template Selector.
- Trang tác giả có thông báo mới yêu cầu IEEE Author Portal, dù đoạn hướng dẫn cũ bên dưới còn nhắc ScholarOne. Khi nộp phải theo thông báo mới thay vì đoạn cũ.
- Phải có đóng góp kỹ thuật hoặc thiết kế đáng kể và chứng minh công nghệ có thể hỗ trợ học. Chỉ đánh giá một công nghệ sẵn có phù hợp khi đem lại insight kỹ thuật/thiết kế quan trọng.
- Phải khai báo AI-generated text theo chính sách IEEE. Không xác nhận một yêu cầu bắt buộc mở toàn bộ raw data từ các trang đã đọc.

### Computers and Education: Artificial Intelligence

Theo [Guide for authors](https://www.sciencedirect.com/journal/computers-and-education-artificial-intelligence/publish/guide-for-authors):

- Double anonymized; title page chứa danh tính và bản thảo ẩn danh là hai tệp riêng.
- Abstract tối đa 250 từ; 1–7 keywords; highlights 3–5 dòng, mỗi dòng tối đa 85 ký tự.
- Hướng dẫn được lấy không hiện một giới hạn tổng số từ rõ ràng. Một trang tổng hợp nói 8.000 từ nhưng không dùng điều đó như quy định xác minh được.
- Research data Option B: khuyến khích nộp, trích dẫn và liên kết dữ liệu; nếu không thể chia sẻ, giải thích lý do. Cần CRediT và khai báo AI.
- Đây là lựa chọn khi có diễn giải mạnh về AI trong giáo dục và hàm ý ứng dụng; một audit kỹ thuật hẹp về feature lịch sử có thể chưa đủ rộng.

## 4. Form hội nghị: dùng làm chuẩn tham chiếu, không coi là cửa nộp đang mở

Các quy định dưới đây là **kỳ 2026 đã xác minh**, không phải deadline tương lai hay cam kết quy định kỳ sau giữ nguyên. Không lập lịch nộp từ deadline cũ.

| Hội nghị | Form của kỳ 2026 | Yêu cầu liên quan |
|---|---|---|
| [EDM 2026](https://educationaldatamining.org/edm2026/call-for-papers/) | Full 10 trang; acknowledgements và references không tính; template EDM | Double-blind; khuyến khích anonymous code; full paper phải là nghiên cứu trưởng thành, nguyên gốc |
| [AIED 2026](https://aied-conference.org/2026/call-for-paper) | Full 14 trang **gồm references**; Springer proceedings/LNCS-LNAI | Double-blind; chấp nhận đóng góp lý thuyết, thực nghiệm, thiết kế; yêu cầu báo cáo đặc tính dữ liệu, giới hạn và khía cạnh đạo đức |
| [LAK26](https://www.solaresearch.org/events/lak/lak26/submission-guidelines/) | Full 16 trang ACM **một cột gồm references** | Double-blind; nền tảng lý thuyết/khái niệm, phương pháp và đóng góp cho learning analytics cần rõ |
| [RecSys26](https://recsys.acm.org/recsys26/call/) | Long 8 trang nội dung ACM hai cột; references không tính | Bài tự đủ nội dung; khuyến khích anonymous code/data và phụ lục tái lập; reviewer không bắt buộc đọc phụ liệu |
| [AAAI-26](https://aaai.org/conference/aaai/aaai-26/submission-instructions/) | 7 trang kỹ thuật hai cột, thêm trang references và reproducibility checklist | Anonymous/double-blind; checklist tái lập bắt buộc, được reviewer đánh giá |

## 5. Ngưỡng bằng chứng trước khi gọi bản thảo là sẵn sàng nộp

Phần này là **đánh giá khoa học cho dự án**, không phải các điều kiện số lượng được tạp chí ấn định.

1. **Đóng góp được phân biệt với tài liệu gần nhất.** Chỉ ra prior work đã mô hình hóa lần thử đầu, retry, sửa code, uncertainty hay policy evaluation như thế nào. Khoảng trống phải là một câu hỏi/giới hạn chưa được xử lý đủ, không phải câu “chưa ai dùng mô hình X trên dataset Y”. Ghi lại cả các nghiên cứu làm yếu giả thuyết ban đầu.
2. **Đơn vị đo khớp với phát biểu.** Tách đúng-sai cùng bài, độ chính xác dự báo bài mới, cập nhật xác suất, thay đổi ranking và learning gain. Quan sát xác suất tăng không tự chứng minh tri thức tăng; quan sát dự báo tốt hơn cũng không tự chứng minh khuyến nghị tốt hơn.
3. **Hiệu ứng có thể tái lập.** Ít nhất phải có đối chứng trên hai nguồn độc lập nếu muốn khái quát qua môi trường C/Python; báo cáo chính xác điều kiện nào cùng đo được. “Hai dataset” không tự bảo đảm external validity.
4. **Đánh giá mô hình và protocol đủ mạnh.** Cần baseline đơn giản, mô hình KT liên quan, baseline/ablation loại bỏ hoặc nén retry; kiểm tra chia theo người học và chia theo thời gian. Không so sánh trực tiếp hai AUC trên hai quần thể khác nhau rồi kết luận retry gây sai lệch.
5. **Đánh giá thống kê theo cấu trúc dữ liệu.** Báo effect size cùng khoảng bất định, bootstrap theo người học hoặc đơn vị phụ thuộc phù hợp; ghi số người học, bài, cặp đo và điều kiện loại bỏ. Báo cả kết quả không cải thiện. Với nhiều giả thuyết, phân biệt phân tích xác nhận và khám phá.
6. **Có hệ quả quyết định thực sự.** Nếu đặt “recommendation” vào tiêu đề, cần thí nghiệm cho thấy cập nhật đổi lựa chọn gì và vì sao đáng quan tâm. Ground-truth regret trong môi trường kiểm soát là một bằng chứng giới hạn; không thay thế tác động lên người học thật. Log thiếu propensity/action set không tự cho phép causal OPE.
7. **Ứng dụng offline có thể kiểm tra.** Có pipeline tái lập và giao diện/CLI cho một lịch sử thực tế đã ẩn danh, xuất dự báo trước–sau, lý do thay đổi và tập bài đề xuất trong candidate set hợp lệ. Đây là ứng dụng kỹ thuật; không gọi là đánh giá hiệu quả giáo dục ngoài thực tế.
8. **Hồ sơ artifact rõ quyền sử dụng.** Công khai code, môi trường, seed, config, manifest nguồn/checksum và script tái tạo khi được phép; với raw data có điều kiện sử dụng chưa rõ, liên kết nguồn chính thức và giải thích hạn chế thay vì phát tán lại. Không tự khai có IRB/ethics approval hoặc consent mới.

**Q1 theo SJR là mục tiêu có thể định hướng thiết kế công trình; không phải thuộc tính của bản thảo hiện tại.** Các thí nghiệm pilot trước đó thiết lập tính khả thi, chưa thay thế bộ kết quả hoàn chỉnh. Đối với AAAI A*, cần chứng minh tại sao phát hiện/phương pháp có giá trị cho bài toán AI rộng hơn ngoài một phân tích log giáo dục. Nếu kết quả cuối cùng là một audit đáng tin nhưng cải thiện thuật toán nhỏ, chọn IJAIED/TOCE/JEDM theo đóng góp thực tế sẽ hợp lý hơn việc ép câu chuyện thành SOTA.

## 6. Khung bản thảo làm việc

Viết bản nghiên cứu bằng tiếng Anh, abstract không quá 250 từ để dễ chuyển IJAIED/TOCE, với cấu trúc:

1. Introduction: vấn đề cụ thể, vì sao metric hiện có chưa trả lời câu hỏi, câu hỏi nghiên cứu và các đóng góp đã có bằng chứng.
2. Related work: repeated attempts/code changes, learner modelling, exercise recommendation, evaluation validity; đối chiếu trên từng thuộc tính và protocol.
3. Problem and estimands: lịch sử trước thời điểm dự báo, đối tượng cần dự báo/đánh giá, candidate set, những đại lượng quan sát được và không nhận diện được.
4. Audit protocol / proposed method: paired fixed-probe design, phương pháp cập nhật hoặc hiệu chỉnh nếu kết quả chứng minh cần thiết; pseudocode và giả định.
5. Data and experimental setup: nguồn, phiên bản, lựa chọn cohort, sơ đồ dữ liệu, splits, baselines, tuning budgets, metrics, uncertainty, leakage checks.
6. Results: mỗi bảng trả lời một câu hỏi; tách thí nghiệm thực hiện với kế hoạch tương lai. Không có bảng số giả hay placeholder được diễn đạt như kết quả.
7. Decision-level analysis / application: ảnh hưởng tới ranking và quyết định, các giả định, failure cases, minh họa pipeline.
8. Discussion and threats to validity: ý nghĩa, giới hạn causal/measurement/external validity, tác động dữ liệu cũ và ngôn ngữ lập trình.
9. Conclusion: chỉ các kết luận được kết quả hỗ trợ.
10. Data/code availability, ethics and AI-use statements, funding/conflicts/CRediT khi venue yêu cầu; tác giả con người hoàn thiện thông tin thật trước nộp.

Nên giữ một bản nội dung trung lập trước, rồi chuyển đúng template sau khi kết quả quyết định venue. Không đưa sẵn logo nhà xuất bản, volume, DOI giả, tên tác giả giả hay dòng “accepted”.

## 7. Giới hạn kiểm chứng của bản ghi này

Các trang hướng dẫn là trang web hiện hành, phần lớn không có ngày phiên bản; kết quả truy cập được ghi ở ngày kiểm tra. Một số nguồn tìm kiếm đưa ra số liệu năm khác hoặc dữ liệu chưa đủ header; những mục đó không được dùng để gán quartile. Không suy diễn deadline sắp tới từ kỳ 2026. Không xác nhận chi phí xuất bản hiện hành vì quyết định khoa học chưa đòi hỏi cam kết thanh toán; việc nộp phải kiểm tra lại guide và phí ngay tại thời điểm nộp.
