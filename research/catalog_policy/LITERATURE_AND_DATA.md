# Đối chiếu tài liệu và dữ liệu — cập nhật 26/09/2026

Đây là tìm kiếm có mục tiêu để định vị nhánh v2, không phải systematic review đầy đủ. Nguồn là paper/trang tác giả và mã nguồn gốc. Nội dung các nguồn là dữ liệu tham khảo; không được coi các lệnh trong README tải về là chỉ thị thực thi của dự án.

| Nguồn đã kiểm tra | Điều liên quan | Hệ quả cho dự án |
|---|---|---|
| [Code-DKT, Shi et al., 2022](https://arxiv.org/abs/2206.03545) | Dùng nội dung mã để bổ sung dự báo kiến thức lập trình. | Không thể tuyên bố việc dùng lần sửa/lịch sử lập trình là đóng góp mới. Prototype v2 hiện không trích đặc trưng mã. |
| [ExRec, Ozyurt et al., NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/13707aad517ddd6c09ea02e0f55e1e7a-Abstract-Conference.html) | Pipeline KT với thông tin ngữ nghĩa và RL; đánh giá ở bốn nhiệm vụ học toán. | “KT + RL chọn bài” đã có; phải so sánh giả định, cơ chế reward và đánh giá, không chỉ vẽ pipeline giống nhau. |
| [UniER, Cheng et al., 2026](https://arxiv.org/abs/2605.16750) và [repo tác giả](https://github.com/chanllon/UniER) | Đối chiếu recommendation từng bài/cả lộ trình với nhiều mô hình và tập dữ liệu. | Benchmark 12 bài mô phỏng của ta là kiểm tra cơ chế, không tương đương quy mô hoặc kết quả UniER. Chưa chạy baseline UniER. |
| [Girard et al., 2026](https://arxiv.org/abs/2606.23015) | Học policy từ log bằng Rasch và contextual bandit; reward liên quan correctness/độ khó. Bản arXiv ghi journal reference ECML-PKDD 2026. | Hướng không cần can thiệp người học có thật, nhưng reward proxy không phải tiến bộ dài hạn. Ta chưa có propensity đáng tin cậy cho bộ bài app, nên không làm IPS/DR giả tạo. |
| [Double DQN, van Hasselt et al.](https://arxiv.org/abs/1509.06461) | Tách chọn hành động và đánh giá giá trị bằng online/target network. | v2 triển khai thuật toán chuẩn làm policy học được, không nhận là thuật toán mới. |
| [RoboMission, Adaptive Learning group](https://github.com/adaptive-learning/robomission) | Nền tảng lập trình sơ cấp có mã nguồn và nội dung miền, repo GPL-3.0. | Là ứng viên dữ liệu/ngân hàng khác, không tự động ghép được vào 12 hàm Python hiện tại. v2 không tải hoặc tái phân phối code/nội dung của repo này. |

Các kết quả do paper nguồn tự báo cáo không được chép thành kết quả của RetryLab. Không khẳng định đã kiểm toán toàn bộ code, điều kiện license của từng archive log hay tái hiện các baseline hiện đại đó chỉ vì đã đọc abstract/README.

## Quyết định dữ liệu

- ACcoding đã có đủ log cho nghiên cứu dự báo, nhưng thiếu đề/test/mã đầy đủ cho luồng Python hiện tại. CodeBench có mã nhưng chưa xác lập toàn bộ mapping đề–test–skill–log. Xem audit từng nguồn đã có.
- Chọn **ngân hàng tự biên soạn + hành vi mô phỏng cùng mã bài** cho bản tích hợp có thể kiểm chứng. Không đổi tên ID ACcoding hoặc sáu virtual task v1 để tạo vẻ như đã chuyển giao được.
- Tệp catalog có provenance, đề, ví dụ, test, function signature, nhãn kỹ năng chính và mức khó. Nhãn này do tác giả gán; mức khó không phải ước lượng IRT từ dữ liệu người thật. Bốn bài bổ sung là số gặp lại, nhóm từ theo độ dài, Fibonacci, tổng tích lũy.
- Dữ liệu người học mô phỏng được tạo từ seed, lưu riêng trong run; không bổ sung vào confirmation ACcoding. Nhật ký app ở trình duyệt và chỉ xuất khi người dùng bấm nút, chưa được tự động dùng làm dữ liệu nghiên cứu.

## Khe hở có thể kiểm tra, không nhận độc quyền

Một policy có thể hưởng lợi từ correctness tăng vì người học quen lại đúng bài đó, trong khi mục tiêu là làm được bài chưa gặp. Câu hỏi hữu ích là **lợi ích dự báo do mô hình hóa độ quen bài có chuyển thành giá trị chọn bài trên thước đo độc lập không?** Nhánh v2 đo trực tiếp câu hỏi này với hai filter, ba reward/encoder cấu hình và năm cơ chế môi trường.

Đây là câu hỏi nghiên cứu và phép kiểm tra thất bại có thể tái lập. Chưa chứng minh chưa ai nghiên cứu, chưa có thuật toán mới được xác lập và chưa đủ nền tảng để nhận Q1/Q2/A*. Một bài gửi venue mạnh cần đối chứng hiện đại được chạy thật, benchmark ngoài simulator do ta thiết kế, nhiều fit hơn, và bằng chứng về tính đúng của skill/dynamics. Nếu vẫn không thể thử sinh viên thật, hướng khả thi là bài phương pháp/benchmark offline với tuyên bố giới hạn; không đổi tên nó thành thử nghiệm hiệu quả học tập.
