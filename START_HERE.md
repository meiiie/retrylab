# Hồ sơ nghiên cứu đề tài 4

Mốc rà soát tài liệu và thực nghiệm: **26/09/2026**. Dự án tự tìm dữ liệu công khai; không có dataset do thầy cung cấp và không thử nghiệm can thiệp với sinh viên mới.

**Mới nhất (28–29/09/2026) — nghiên cứu v3 trên dữ liệu ACcoding thật:** [kết quả](research/accoding_policy/RESULTS.md), [bản thảo tiếng Anh](output/pdf/retrylab-v3-manuscript.pdf), [bản thảo tiếng Việt](output/pdf/retrylab-v3-ban-thao-tieng-viet.pdf), [đánh giá mức sẵn sàng nộp](paper/v3/DANH_GIA_SAN_SANG_NOP.md). Mọi kết quả chính sách là mô phỏng.

**Mở ứng dụng:** bấm đúp [RetryLab.cmd](RetryLab.cmd) — cửa sổ ứng dụng riêng với sáu màn hình (Tổng quan, Học viên, Phiên học, Đánh giá, Luyện Python, Mô hình) và nút ▶ Thuyết trình. [Hướng dẫn](app/README.md). Giao diện cũ vẫn ở `http://127.0.0.1:8773/classic`.

**Chuẩn bị demo:** bấm [check_demo.cmd](app/check_demo.cmd), đợi `DEMO CHECK PASSED`, rồi làm theo [kịch bản demo Gia sư AI](app/DEMO_GIA_SU_AI.md). Kịch bản cho giao diện cũ: [DEMO_READY.md](app/DEMO_READY.md). Dùng đúng máy và workspace đã được kiểm tra; không xóa tiến độ cá nhân để diễn tập.

**Báo cáo trước đó — dàn trang sửa ngày 27/09/2026:** [Bộ bản thảo theo hướng dẫn tạp chí](paper/journal/README.md), [PDF tiếng Việt](output/pdf/retrylab-journal-vi.pdf), [PDF tiếng Anh](output/pdf/retrylab-journal-en.pdf), [nguồn TeX](paper/topic4_policy.tex). Đã tham khảo bài Minn (2022) và hướng dẫn Computers and Education: Artificial Intelligence; xếp hạng kiểm chứng Q1/SJR 2024, không phải bảo đảm chất lượng công bố. Hình SVG/PDF vector, bảng và các con số được dựng từ artifact thực nghiệm đã khóa. Đã sửa lề, cỡ chữ, phương trình, bảng và ngắt trang; xem [biên bản sửa dàn trang](paper/journal/LAYOUT_REVISION.md). PDF dùng ReportLab + PyMuPDF; nguồn TeX dùng `elsarticle` nhưng trình biên dịch tích hợp vẫn lỗi môi trường, chưa xác nhận biên dịch thành công.

**Bắt đầu từ bản đề 4 tích hợp:** [Kịch bản báo cáo và demo ngắn](paper/DE_4_BAO_CAO_VA_DEMO.md), [bàn thử nghiệm chọn bài](http://127.0.0.1:8773/classic#policy), [kết quả v2 đầy đủ](research/catalog_policy/RESULTS.md). Prototype đã nối 12 bài Python → Bayes filter → Double DQN → gợi ý bài. Policy học từ mô phỏng; chưa có bằng chứng hiệu quả với sinh viên thật hoặc SOTA. Bản PDF hướng dẫn demo cũ vẫn được giữ riêng tại `output/pdf/retrylab-de4-bao-cao.pdf`.

**Phạm vi:** xem [đối chiếu đề 4](DOI_CHIEU_DE_4_VA_HUONG_TRIEN_KHAI.md). [Harness](harness/README.md) giữ kiểm tra, provenance và tiến độ; chạy `python tools/harness.py status`. [Nhánh catalog/policy v2](research/catalog_policy/README.md) ghi rõ các giả định và giới hạn. Nhánh [v1](research/policy/README.md) và dự báo ACcoding phía dưới là kết quả lịch sử, không bị ghi đè.

**Trình duyệt thường:** [start.cmd](app/start.cmd) mở cùng ứng dụng trong trình duyệt mặc định; giao diện cũ ở `/classic`. Luồng sinh viên có 12 bài và 96 test thật. Khu Nghiên cứu gồm bàn thử nghiệm policy mô phỏng và phát lại ACcoding thật riêng biệt. [Biên bản v2](app/TOPIC4_VALIDATION.md) phân biệt kiểm tra phần mềm với hiệu quả giáo dục. Các bản nháp/tiến độ trên trình duyệt được giữ nguyên.

Tài liệu nhánh dự báo đã đóng băng:

1. [Báo cáo nghiên cứu bằng tiếng Việt](paper/BAO_CAO_NGHIEN_CUU.md): quyết định hướng đề tài, kết quả thực, khoảng trống còn lại và đánh giá khả năng công bố.
2. [Bản thảo tiếng Anh](paper/manuscript.tex): nội dung nghiên cứu có thể chỉnh sửa; bản đọc PDF cùng thư mục.
3. [Hướng dẫn tái lập](research/reproducibility/README.md): môi trường, thứ tự chạy, các điểm khóa validation trước confirmation và phân biệt kết quả tham chiếu với rerun.
4. [Đối chiếu prior art](research/literature/gap_audit.md), [bổ sung đến 22–26/09/2026](research/literature/supplementary_gap_audit.md), [câu hỏi mã trung gian](research/literature/revision_information_gap.md).
5. [Phản biện khoa học nội bộ](research/review/reviewer_report.md) và [đối chiếu venue](research/venues/venue_strategy.md).

Kết quả chi tiết:

- [ACcoding: nhóm 1.500 người học mới](research/confirmation/RESULTS.md).
- [CodeBench: các định nghĩa outcome và kiểm tra đầu tiên](research/codebench_experiment/results.md).
- [CodeBench: paired-task control trên partition mới](research/codebench_experiment/paired_task_results.md).
- [GRU: ba seed cho hai training tasks](research/sequential/validation_converged/final_results.md).
- [Kiểm tra theo lịch](research/confirmation/temporal_RESULTS.md).
- [Mã trung gian: phép thử trên học kỳ mới](research/revision_information/results.md).
- [Ứng dụng cảnh báo và trade-offs](research/application/results_table.md); [biểu đồ](research/application/figures/screening_changes.png).

Hai báo cáo ở thư mục gốc lưu định hướng và pilot ban đầu; chúng có ghi chú dẫn sang kết quả cập nhật. Không lấy một giả thuyết hoặc kế hoạch trong bản cũ làm kết quả đã chứng minh.

`data/` và các checkpoint là dữ liệu làm việc cục bộ. Gói nguồn được tạo riêng bằng danh sách cho phép, không bao gồm raw data, dự đoán theo người học, checkpoint hoặc toàn văn của bên thứ ba. Không có giấy phép phát hành chung hay chứng nhận ẩn danh tự động cho toàn bộ workspace. Chưa nộp bài hoặc công bố hồ sơ này ra ngoài.
