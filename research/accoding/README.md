# ACcoding: kiểm chứng nguồn và dữ liệu thực tế

Kiểm tra ngày 26/09/2026. Đã tải trực tiếp, không đăng nhập, từ [Zenodo của tác giả](https://zenodo.org/records/11395043). Tệp mang nhãn `ACcoding-Dataset v2.0.0.zip`, công bố ngày **14/07/2026**. Đây là bộ log nộp bài có thể dùng ngay cho nghiên cứu dự đoán kết quả và phân biệt lần đầu với nộp lại.

## Tệp đã nhận và xác thực

- Tệp gốc: `data/raw/accoding/ACcoding-Dataset-v2.0.0.zip`.
- Kích thước: **96.056.846 byte**. MD5 trùng Zenodo: `abcf3517565312d0e6e2a1aba36b1236`.
- SHA256: `26b5637d2a912ce6ae4824e49e055a060c1162422c4a47508e3eb1017762ac1d`.
- Bản chụp metadata chính thức: `zenodo-11395043.json`, `zenodo-6522395.json`. Manifest: `manifest.json`.
- Chỉ đọc SQL như văn bản, không thực thi SQL và không thực thi mã sinh viên.

## Kết quả đọc toàn bộ bảng submissions

| Đại lượng | Giá trị trong bản đã tải |
|---|---:|
| Lượt nộp | 2.181.602 |
| Người dùng ẩn danh | 9.866 |
| Bài tập | 4.301 |
| Lượt nộp ngôn ngữ C | 2.137.950 |
| Lượt được chấp nhận (AC) | 909.100 |
| Nhãn kiến thức trong bảng tags | 96 |
| Liên kết problem–tag | 4.320 |
| Thời gian nộp sớm nhất | 2024-01-02 00:13:27 |
| Thời gian nộp muộn nhất | 2025-12-30 23:57:19 |

Các con số này được tính trực tiếp từ archive mới, không lấy lại thống kê 4.046.652 lượt nộp của bài báo năm 2024. Mô tả Zenodo ghi dữ liệu đến 12/05/2025, trong khi timestamps thực tế đi đến 30/12/2025; giữ nguyên sự không nhất quán này trong provenance. Không coi bản mới là phần mở rộng đầy đủ của bản cũ nếu chưa đối chiếu ID.

Schema submissions gồm `id, lang, result, score, time_cost, memory_cost, code_length, detail, created_at, creator_id, problem_id, contest_id`. Archive có các bảng users, problems, submissions, contests, tags, problem_tags và SQL quan hệ; schema từng bảng được lưu thành `*-schema.sql.txt`.

**Không có toàn bộ source code của từng lượt nộp**, không có văn bản đề bài, không có nội dung input/output test và không có kết quả từng test case. Trường `detail` có thông báo biên dịch, đôi khi chứa mảnh code; điều này không tương đương source đầy đủ. `test_setting` là cấu hình và tên các tệp test không được cung cấp trong archive. Vì vậy, ACcoding phù hợp nghiên cứu lịch sử nộp bài, trạng thái lỗi, lần đầu/nộp lại; không đủ để tái hiện phương pháp code-edit hoặc test-case tracing.

## Cohort pilot dùng ngay

`data/processed/accoding/submissions_cohort.csv` có **424.311 dòng**, **1.500 người dùng**, **2.768 bài**, **20.596.768 byte**; header:

```text
id,created_at,creator_id,problem_id,result,score,lang
```

CSV UTF-8, phân tách dấu phẩy; sắp xếp toàn cục theo `created_at`, rồi `id`. Giữ toàn bộ các dòng được phát hành của mỗi người đã chọn, mọi ngôn ngữ và trạng thái, không cắt N dòng đầu của toàn nền tảng. Có 177.441 dòng AC và 416.724 dòng C. Không có WT/JG trong cohort thực tế.

Chọn 1.500 SHA256 nhỏ nhất của chuỗi `accoding-pilot-v1:{creator_id}` trong 7.634 người có ít nhất 20 bài khác nhau trên toàn snapshot. `cohort_users.csv` lưu ID, số bài và hash; manifest cạnh CSV ghi quy tắc, kết quả, SHA256.

Điều kiện đủ lịch sử nhìn vào cả tương lai trong snapshot. Đây là quần thể pilot có lịch sử dài được chọn trước, không phải mẫu đại diện cho người mới hoặc toàn nền tảng. Lần đầu chỉ có nghĩa **lần đầu quan sát trong dữ liệu phát hành**, không chứng minh đây là lần đầu người học từng gặp bài. Nguồn không khai báo múi giờ; thứ tự ID khi trùng giây là giả định cần kiểm tra nhạy cảm.

AC biểu thị accepted. Nếu gặp WT/JG ở bản dữ liệu khác, cần loại khỏi target nhị phân vì chưa có kết quả cuối. Các trạng thái lỗi khác là không accepted; lỗi hệ thống như OE/IFNR/OFNR nên có phân tích nhạy cảm, không mặc nhiên diễn giải là thiếu kiến thức. Giữ `score` nguyên trạng; chưa có căn cứ chuẩn hóa thang điểm giữa các bài.

## Giấy phép và phạm vi kết luận

[Bài Scientific Data ngày 29/05/2024](https://www.nature.com/articles/s41597-024-03392-z) nói dữ liệu gốc dùng CC BY 4.0. Metadata của cả record Zenodo gốc và record đang tải ghi `other-open`. Audit ghi cả hai nguồn, không suy diễn rằng tuyên bố của bài năm 2024 giải quyết toàn bộ điều khoản của bản cập nhật năm 2026. Dữ liệu được cung cấp công khai, tải được ngay; khi phát hành lại dữ liệu cần kiểm tra điều khoản áp dụng cho bản cụ thể.

Những log này không chứa phân phối xác suất lựa chọn bài của hệ thống, không có phân nhóm ngẫu nhiên hay ground truth về mastery. Kết quả pilot có thể chứng minh khả năng dự đoán, sai lệch khi gộp lần đầu với nộp lại, và độ nhạy thứ hạng chính sách trong mô phỏng. Chúng không tự chứng minh chính sách làm người học tiến bộ trong thực tế.

## Tái lập

Chạy lần lượt từ thư mục dự án:

```powershell
python research/accoding/source_manifest.py
python research/accoding/extract_cohort.py
python research/accoding/audit_accoding.py
```

Hai lượt streaming của extractor đọc bảng SQL giải nén khoảng 1,13 GB; không cần nạp bảng vào cơ sở dữ liệu. Parser dừng nếu gặp định dạng ngoài dự kiến, không bỏ dòng âm thầm. `audit_summary.json` chứa kiểm tra schema, tổng số và tính duy nhất/thứ tự của cohort. Phần đánh giá mô hình do `research/pilot/` thực hiện riêng.
