# Tự kiểm toán bản đề 4 tích hợp

## Hoàn tất được trong phạm vi hiện tại

Có đầy đủ pipeline kỹ thuật của đề: ngân hàng bài có thể làm; nhãn kỹ năng và trạng thái quan sát; MDP xấp xỉ/POMDP belief; policy học thật; reward khai báo; tập evaluation khác train; baseline; app thể hiện hành động thật; báo cáo và bản thảo có kết quả đo lường. Bản chạy có thể được trình diễn và kiểm tra lại.

Quyết định khớp catalog được giải quyết bằng **fit/train mới trên simulator dùng đúng catalog**. Điều này thay thế nhu cầu ghép giả ID ACcoding vào app. Không coi đây là kiểm chứng simulator-to-human transfer. Bản v1 sáu virtual task không được đưa trực tiếp vào luồng sinh viên.

## Các nhận định đã bị bác bỏ hoặc chưa được hỗ trợ

| Nhận định | Phán quyết |
|---|---|
| App chỉ đang đổi tên quy tắc thành RL | Không đúng ở nhánh learned: có chín mạng, replay, gradient updates và checkpoint. Fallback vẫn ghi đúng là rule. |
| Aware filter dự báo tốt hơn nên chọn bài cũng tốt hơn | Không được hỗ trợ: nominal aware/probe thấp hơn naive và weakest-skill. |
| Tăng xác suất qua bài chứng minh tăng năng lực | Không đúng: xác suất response, latent belief, practice score và transfer gain là các biến khác nhau. |
| Cùng mã bài nên simulator đã đúng với sinh viên thật | Không đúng: chỉ kiểm tra được tương thích kỹ thuật. |
| Đã đánh bại ExRec/UniER hoặc đạt SOTA 26/09/2026 | Không có thực nghiệm hỗ trợ; tài liệu chỉ được dùng để định vị prior art. |
| Đã sẵn sàng gửi bài khẳng định tác động giáo dục Q1/Q2/A* | Chưa. Không có human efficacy hoặc đối chứng recommendation hiện đại trong cùng benchmark. |

## Hướng công bố khả thi hơn

Bản thảo hiện tại trung thực ở mức prototype/simulator stress test và negative result. Nếu tiếp tục tới venue mạnh, cần một protocol mới sau khi thừa nhận evaluation v2 đã được xem: chạy các baseline recommendation công bố trong benchmark chung; dùng nguồn log/đề/test ghép thật hoặc một simulator được fit/kiểm tra bằng dữ liệu ngoài; thêm nhiều seed, budget sweep và độ nhạy skill mapping. Không cần hứa tuyển sinh viên vì người dùng đã loại phương án đó. Có thể theo hướng phương pháp đánh giá offline, nhưng không dùng dữ liệu thiếu propensity để tạo kết luận nhân quả.

Việc bài báo có được chấp nhận là quyết định phản biện bên ngoài. “Hoàn tất prototype và hồ sơ đo lường” không đồng nghĩa “đã đạt hạng venue”.

## Giới hạn vận hành đã công khai

Policy hoạt động trong ngân sách 12 quan sát; ba quan sát mỗi bài, không tự gán lại bài đã đạt. App phát hiện lịch sử ngoài support và fallback minh bạch. Dữ liệu trình duyệt cũ được giữ, không xóa để khiến demo đẹp hơn. Bản báo cáo gốc/engine/hash cũ vẫn nguyên. Native LaTeX compiler gặp lỗi platform; file tiếng Anh còn chỉnh sửa được, PDF tiếng Việt là tài liệu xuất riêng đã được kiểm tra.
