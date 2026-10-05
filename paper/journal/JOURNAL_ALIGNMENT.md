# Đối chiếu quy cách và phạm vi bản thảo

Ngày truy cập: **26/09/2026**. Nguồn chuẩn: [Guide for Authors, Computers and Education: Artificial Intelligence](https://www.sciencedirect.com/journal/computers-and-education-artificial-intelligence/publish/guide-for-authors). Bản chụp nội dung dùng kiểm tra được lưu tại `references/publisher-and-ranking-snapshot.md`.

**Sửa dàn trang 27/09/2026:** [biên bản sửa](LAYOUT_REVISION.md). Bản trước đáp ứng một số thành phần nội dung nhưng có lỗi căn khung và tỷ lệ công thức; bảng bên dưới không phải chứng nhận toàn bộ định dạng đã đạt chuẩn nộp bài. Nguồn mới dùng `elsarticle`; chưa biên dịch thành công. PDF là bản đọc được dựng riêng, dùng A4/lề 25 mm/cỡ chữ 11 pt như lựa chọn trình bày của dự án.

Q1 là thứ hạng trong một hệ thống/năm/danh mục, không phải một template chung. Xếp hạng kiểm chứng: [SCImago Education, dữ liệu 2024](https://www.scimagojr.com/journalrank.php?category=3304), Q1, SJR 5.217. Không khẳng định JCR hoặc thứ hạng 2026.

| Mục | Bản hiện tại | Trạng thái |
|---|---|---|
| Bản nghiên cứu có thể chỉnh sửa | TeX `elsarticle`, Markdown nguồn, bảng CSV | Có; chưa xác nhận biên dịch TeX |
| Abstract tối đa 250 từ | 191 từ tiếng Anh, tự kiểm tra | Đạt giới hạn hình thức |
| 1–7 từ khóa tiếng Anh | 6 từ khóa | Đạt |
| Các phần phương pháp, kết quả, thảo luận | RQs; thuật toán; splits; baseline; CI; negative controls; giới hạn | Đã viết theo nội dung thực tế |
| Công thức có thể chỉnh sửa | 4 phương trình trong TeX, vector trong PDF | Có |
| Bảng là dữ liệu chỉnh sửa được | 3 bảng chính, phụ lục đầy đủ; CSV; không đường dọc/tô nền | Có |
| Hình đánh số và caption | 4 hình chính, caption riêng, SVG/PDF vector | Có |
| Highlights, được khuyến khích | 5 câu, mỗi câu ≤85 ký tự, `highlights.txt` | Có |
| Graphical abstract, được khuyến khích | Sơ đồ riêng dạng SVG và PDF vector | Có; cần tác giả duyệt chính sách AI/artwork |
| APA 7, author–year | 8 tài liệu, xếp theo họ tác giả; DOI/URL; preprint có nhãn | Đã chuẩn hóa; cần tác giả rà soát cuối |
| Phản biện ẩn danh hai chiều | Main manuscript không có tên tác giả, đơn vị hoặc email | Trang tác giả phải được hoàn tất riêng |
| Data/code availability | Nêu artifact cục bộ; không giả DOI công khai | Chưa tạo kho công khai |
| Tài trợ, lợi ích, đóng góp, đạo đức | Trạng thái được công bố; biểu mẫu thông tin riêng | Cần xác nhận từ tác giả thật |
| AI-assisted technologies | Có declaration trung thực về hỗ trợ Codex và mã dựng hình | Chưa tuyên bố tác giả đã duyệt hoặc tạp chí cho phép |
| Khả năng công bố | Mô phỏng có giả định; không thắng baseline chính; chưa đối chiếu benchmark hiện đại | Không suy ra đủ chất lượng Q1 từ định dạng |

## Những gì lấy từ bài mẫu

Bài Minn (2022) đã xuất bản minh họa cách phân cấp mục, đặt công thức, dẫn hình/bảng, thảo luận giới hạn và trình bày tài liệu tham khảo. Bài đó là tổng quan, không phải đối chứng kết quả thực nghiệm của dự án. Dàn trang hai cột xuất bản thuộc quy trình nhà xuất bản; không cần giả lập logo, volume, DOI hay ngày chấp nhận để bản nộp trông giống bài đã được nhận. Bản của chúng tôi dùng một cột dễ phản biện, với source có thể chỉnh sửa.

## Những điều chưa thể hoàn tất bằng đổi hình thức

Chưa tái hiện ExRec/UniER trong một thiết lập chung, chưa hiệu chuẩn simulator bằng dữ liệu người thật khớp ngân hàng, chỉ có ba fit và một ngân sách. Đóng góp thuật toán mới và hiệu quả giáo dục chưa được xác lập. Chỉnh lý này giúp trình bày chính xác và chuyên nghiệp hơn; nó không bổ sung bằng chứng chưa tồn tại.

Không cần một can thiệp sinh viên ngoài phạm vi người dùng đã xác định. Hướng nâng bằng chứng phù hợp là dữ liệu công khai khớp bài/lịch sử, baseline tái lập được, kiểm định simulator và độ nhạy có thiết kế mới. Mọi số liệu bổ sung chỉ được đưa vào khi đã thực sự chạy và kiểm tra.
