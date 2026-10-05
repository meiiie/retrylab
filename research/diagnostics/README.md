# Kiểm tra reward trong thế giới được kiểm soát

Chạy: `python research/diagnostics/reward_audit.py` từ thư mục dự án. Thư viện chuẩn Python là đủ. Script ghi `reward_audit_results.csv` và `reward_audit_summary.json`.

Đây là kiểm tra logic/khởi tạo benchmark, chưa phải thí nghiệm trên sinh viên hoặc kết quả tái lập phương pháp đã công bố. Các tham số được tự đặt có chủ đích để phân biệt những hiện tượng cần nghiên cứu. Không dùng kết quả này để tuyên bố có thuật toán mới hay đạt SOTA.

## Đặc tả

Tri thức nhị phân ẩn có prior 0.1, 0.4 hoặc 0.7. Có ba action: quan sát chẩn đoán, sửa bài hiện tại, và luyện tập có khả năng làm tăng tri thức. Mỗi bước thực hiện chuyển trạng thái học trước, rồi sinh phản hồi. Khả năng trả lời đúng khi đã biết là 0.9; khi chưa biết thường là 0.2. Ở thế giới có sửa bài, action `repair` có thể đạt 0.85 dù chưa biết kỹ năng; đó là giả định về thành công cục bộ của toy model, không phải tỷ lệ ước lượng từ dữ liệu.

Năm cấu hình thế giới: chỉ thêm thông tin không học; sửa bài nhưng không học; và ba mức learning transition 0.02, 0.05, 0.15. Mỗi chính sách được tối ưu với horizon 4 cho một trong ba objective: số lần thành công, tổng thay đổi posterior có dấu, tổng phần tăng dương của posterior.

Mọi nhánh được liệt kê bằng quy hoạch động, dùng số thực và làm tròn belief 12 chữ số để cache; không Monte Carlo. 45 tổ hợp được xuất. Hai kiểm tra tính nhất quán: giá trị planner và evaluator khớp trong sai số số học; thế giới có learning transition bằng 0 luôn có true expected mastery gain bằng 0.

## Ý nghĩa kết quả

Với prior 0.4, thế giới không học vẫn tạo positive-only posterior return khoảng 0.348 sau bốn lượt, trong khi true expected gain bằng 0. Tăng hiểu biết của mô hình về người học có thể có giá trị chẩn đoán; nó không tự là việc người học học thêm.

Ở thế giới chỉ sửa bài, chính sách tối ưu xác suất thành công đạt expected success rate 0.87. Một evaluator cố tình sai, bỏ qua khả năng sửa bài khi chưa nắm kỹ năng, báo expected gain khoảng 0.486 trong khi true gain vẫn bằng 0.

Evaluator sai này **chỉ chấm lại trajectory**. Nó không điều khiển policy; các policy trong script dùng dynamics/posterior đúng. Do đó kết quả chưa chứng minh một policy học được đã khai thác sai số của một simulator học được. Thí nghiệm ấy là bước riêng cần triển khai và đánh giá trên log thật cùng môi trường đối chứng.

Signed posterior gain khớp expected true gain trong toy model nhờ đặc tả đúng. Không suy ra rằng lấy signed difference của một neural mastery score bất kỳ là giải pháp nhân quả cho dữ liệu thật.

## Hướng mở rộng có thể bác bỏ giả thuyết

1. Đổi slip/guess, thời điểm learning transition, horizon và forgetting; cố định latent probe trước/sau.
2. Huấn luyện evaluator từ sample có giới hạn, thay vì cấp oracle parameters.
3. Cho policy tối ưu evaluator đã học rồi đo true value độc lập.
4. So các objective/biện pháp hiệu chỉnh ở cùng lượng dữ liệu và compute; báo cả trường hợp giả thuyết không đúng.
