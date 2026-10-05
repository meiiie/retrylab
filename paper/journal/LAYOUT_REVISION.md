# Sửa dàn trang sau phản hồi của người dùng

Ngày sửa: **27/09/2026** (giờ Việt Nam). Dữ liệu và mốc tổng quan nghiên cứu vẫn giữ theo thực nghiệm/tài liệu đến 26/09/2026.

Bản trước chưa đủ chỉn chu về dàn trang. Kiểm tra cũ xác nhận font nhúng, dữ liệu và nội dung không tràn khỏi trang, nhưng chưa kiểm tra các mép chữ/bảng/hình có thẳng hàng với nhau. Do đó, kết luận trình bày đã hoàn thiện trước đó là quá sớm.

## Lỗi tìm thấy và cách sửa

| Vấn đề trong bản trước | Sửa trong bản hiện tại |
|---|---|
| Frame mặc định thêm 6 pt padding mỗi bên nhưng bảng vẫn dùng chiều rộng toàn khung; đo PDF cũ thấy mép chữ phải khoảng 517.36 pt, mép bảng 529.28 pt | Frame không có padding; chiều rộng chữ, hình và bảng cùng 160 mm; mép trái 25 mm, mép phải 25 mm |
| Lề dọc 52 pt khác lề ngang 72 pt; hình và bảng tạo cảm giác lệch | Khổ A4, bốn lề 25 mm; header/footer nằm trong vùng riêng |
| Công thức xuất theo bounding box rồi phóng rộng, khiến mỗi phương trình có cỡ chữ khác | Math serif 11 pt trên canvas đúng chiều rộng nội dung; tỷ lệ chèn 1:1; số phương trình căn cùng mép phải |
| Sơ đồ có chữ quá dài so với ô và tỷ lệ chữ nhỏ | Rút gọn nhãn, điều chỉnh khổ hình; kiểm tra bounding box của từng nhãn nằm trong ô |
| Biểu đồ quá cao làm nhiều khoảng trống ở cuối trang | Giảm chiều cao đồ thị nhưng giữ cỡ nhãn, giữ hình/caption cùng trang và cho đoạn văn gần hình điền khoảng trống khi phù hợp |
| Phụ lục có nhiều lần ngắt trang, lặp tên môi trường và chỉ còn vài dòng ở trang cuối | Cả 35 kết quả nằm trên một trang; nhóm theo môi trường, căn phải các cột số |
| Tài liệu tham khảo dễ bị tách còn vài mục trên trang riêng | Giữ tiêu đề và toàn bộ tám mục thành một khối; không để tiêu đề đứng một mình |
| TeX sử dụng lớp article chung | Đổi sang `elsarticle`, frontmatter/abstract/keywords riêng, chế độ preprint/author–year |

## Thông số của bản đọc

- A4, lề nội dung 25 mm bốn phía, không padding ẩn trong frame.
- Times New Roman 11 pt, khoảng dòng 14.5 pt; tiêu đề 18 pt; caption 9.5 pt; bảng 9.3 pt.
- Bảng không đường dọc hoặc tô nền; số căn phải; heading, caption và mép bảng dùng cùng tọa độ.
- Hình và phương trình vector, font nhúng; số trang ở giữa chân trang.
- PDF tiếng Anh: 12 trang. PDF tiếng Việt: 11 trang.

Đây là **lựa chọn dàn trang nhất quán của dự án**, không phải khẳng định tạp chí bắt buộc lề 25 mm hoặc font 11 pt. Q1 không phải tên một template.

## Căn cứ và ranh giới xác nhận

[Hướng dẫn tạp chí](https://www.sciencedirect.com/journal/computers-and-education-artificial-intelligence/publish/guide-for-authors) yêu cầu source chỉnh sửa được, bảng dạng văn bản, công thức chỉnh sửa được và hình phù hợp; Word dùng một cột, LaTeX có thể dùng hai cột. [Elsevier LaTeX instructions](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions) giới thiệu lớp `elsarticle`. Dàn trang cuối cùng của bài đã được nhận là bước riêng của nhà xuất bản.

`check_report.py` nay kiểm tra biên trái/phải 25 mm, vị trí hình/caption, kích thước chèn phương trình và font nhúng. `layout_en.json` / `layout_vi.json` ghi tọa độ thật; `visual_review.json` gắn việc xem ảnh trang với hash PDF hiện tại. Các kết quả khoa học giữ nguyên; run gốc vẫn được xác minh trước khi dựng.

Trình biên dịch tích hợp tiếp tục trả lỗi môi trường `Unable to find standard directories for platform`. PDF dùng ReportLab/PyMuPDF, không phải đầu ra biên dịch `elsarticle`. Chưa xác nhận nguồn TeX biên dịch thành công và chưa tuyên bố hồ sơ hoàn toàn sẵn sàng nộp tạp chí. Bản này sửa dàn trang; không tạo thêm bằng chứng về hiệu quả học tập.

Bản cũ được lưu trong `archive/layout-v1-report.zip` để truy vết. Không thay đổi dữ liệu người dùng, model hoặc kết quả thực nghiệm đã khóa.
