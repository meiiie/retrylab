# Checklist trước khi nộp (mục tiêu hiện tại: Computers & Education: AI; phương án: IJAIED, UMUAI)

Đánh giá đầy đủ: `DANH_GIA_SAN_SANG_NOP.md`. Yêu cầu tạp chí lấy từ Guide for Authors đã lưu (`paper/journal/references/publisher-and-ranking-snapshot.md`, 26/09/2026). Hạng Q1 của C&E:AI là theo **SJR 2024** (ngành Education); **không có gì bảo đảm được nhận**.

## Đã có (kiểm tra tự động bởi `python -X utf8 paper/v3/build.py`)

- [x] Kết quả xác nhận trên quần thể chưa từng dùng, protocol khóa trước (`research/accoding_policy/PROTOCOL_LOCK.md`), hai run qua `verify-run`.
- [x] Bản thảo LaTeX `elsarticle`, A4, biên dịch sạch bằng Tectonic (không tham chiếu/trích dẫn thiếu, không thiếu glyph, không hộp tràn > 5 pt).
- [x] Tóm tắt ≤ 250 từ (245), 6 từ khóa (1–7), 5 highlights ≤ 85 ký tự (tối đa 83) trong `highlights.txt`.
- [x] Bản thảo ẩn danh + trang tiêu đề tách riêng (`title_page.tex`).
- [x] Tài liệu tham khảo APA 7, 73 mục đã xác minh, khớp 1–1 với trích dẫn; bộ dữ liệu trích dẫn có "[dataset]".
- [x] Phụ lục đánh số A–E, bảng C.1/D.1, phương trình (A.1)–(A.2).
- [x] Hình nộp thành tệp vector riêng `Figure_1–6.pdf`; chú thích nằm trong caption; bảng CSV bổ sung trong `submission/supplementary/`.
- [x] Các mục Data availability, Ethics statement và "Declaration of generative AI and AI-assisted technologies in the manuscript preparation process" (bản nháp) đặt trước References.
- [x] Gói nộp `submission/` biên dịch độc lập; bản dịch tiếng Việt `vi/` (không dùng để nộp).

## Tác giả phải làm

- [ ] Điền `submission/title_page.tex`: tên, đơn vị (tên chính thức, địa chỉ đầy đủ), email, tác giả liên hệ, lời cảm ơn.
- [ ] Xác nhận/sửa câu khai báo AI cho đúng thực tế; **tự đọc, hiểu và bảo vệ được** mọi phương pháp và kết luận (chính sách AI của Elsevier: AI không thay thế tư duy của tác giả).
- [ ] Quyết định về hình vẽ: mã vẽ được viết với trợ giúp của AI (xem Mục 5 của bản đánh giá); giữ khai báo hoặc tự viết lại mã vẽ.
- [ ] Tài trợ, xung đột lợi ích, CRediT (trang tiêu đề + công cụ khai báo của hệ thống nộp).
- [ ] Kho mã/kết quả công khai (ẩn danh khi phản biện, ví dụ OSF view-only) và thay câu Data availability bằng liên kết.
- [ ] Hoàn thiện thư gửi biên tập `cover_letter_draft.md`.
- [ ] Kiểm tra lại Guide for Authors, hạng tạp chí (SJR/JCR theo yêu cầu của trường, năm mới nhất) và phí APC ngay trước khi nộp.
- [ ] Không đăng bản tiếng Việt lên tạp chí khác trong khi bài tiếng Anh đang được xét (dùng làm báo cáo/luận văn thì được).

## Nên làm để bài mạnh hơn (khuyến nghị cho Q1)

- [ ] Tái lập trên bộ dữ liệu thứ hai (CodeBench, Python — đã có trong `data/raw/codebench`).
- [ ] Phân tích độ nhạy: chân trời dài hơn, trọng số công sức khác, thêm seed.
- [ ] Thử một biện pháp khắc phục (phạt độ bất đồng giữa DKT và bản song sinh).
- [ ] Thử nghiệm có đối chứng với sinh viên (cần phê duyệt đạo đức) — ngoài phạm vi hiện tại.
