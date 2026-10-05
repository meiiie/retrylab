# RetryLab: từ bảng nghiên cứu đến một trải nghiệm có thể sử dụng

Ghi chép lần thiết kế UX trước tích hợp model. Bản hiện tại giữ các nguyên tắc giao diện, mở rộng lên 12 bài và thay gợi ý chính bằng Double DQN có nhãn mô phỏng/fallback. Xem `README.md` và `TOPIC4_VALIDATION.md` để biết trạng thái triển khai mới.

Ngày: 26/09/2026. Thiết kế lại theo yêu cầu làm rõ hành động cho sinh viên và người nghiên cứu. Dùng skill `apple-design` làm hướng dẫn về sự rõ ràng, tính quen thuộc, phân cấp và quyền kiểm soát của người dùng; không coi đây là một bộ quy tắc chính thức mang tên Steve Jobs.

## Vấn đề cần giải quyết

Phiên bản trước mở vào một hồ sơ nghiên cứu với mã bài, mô hình, xác suất và nhiều bảng. Nó giúp kiểm chứng nghiên cứu, nhưng một sinh viên chưa có đề để giải hoặc một hành động tiếp theo đủ rõ. Việc thay màu hay giảm số thẻ không giải quyết được thiếu sót đó.

## Hai hành trình

**Sinh viên:** một nút bắt đầu → một đề có ví dụ → một ô viết Python → phản hồi test cụ thể → sửa mã hoặc mở gợi ý → hoàn thành → bài tiếp theo có lý do. Bản nháp và tiến độ ở lại trên trình duyệt. Có thể mở bất kỳ bài nào; không ép theo lộ trình. Không yêu cầu tài khoản hoặc GPU.

**Người nghiên cứu:** lời dẫn vào câu hỏi nghiên cứu → một hồ sơ với dự báo ban đầu → thêm quan sát → mở kết quả đã ẩn → kiểm tra toàn tập và khoảng tin cậy. Bộ chọn hồ sơ, bảng năm mô hình, xuất dữ liệu và thay chuỗi đầu vào được đưa xuống phần mở rộng. Các số đo vẫn có thể kiểm tra lại.

## Quyết định giao diện

- Thanh điều hướng có ba mục rõ nghĩa: Luyện tập, Tiến độ, Nghiên cứu.
- Một hành động chính ở mỗi bước. Màu xanh chỉ hành động; phản hồi đúng/sai có chữ và biểu tượng, không chỉ dựa vào màu.
- Nền trung tính, chữ hệ thống, khoảng cách nhất quán. Nội dung học tập đi trước thuật ngữ nghiên cứu.
- Gợi ý, chi tiết test, nội dung in và thông tin phương pháp chỉ mở khi cần.
- Trạng thái chờ, lỗi, dừng, bản nháp thay đổi và lưu không thành công đều có thông báo cụ thể. Đặt lại mã có hoàn tác.
- Giao diện co thành một cột trên màn hình nhỏ, bảng và mã dài cuộn trong vùng riêng. Có focus bàn phím, skip link, nhãn cho trình đọc màn hình và hỗ trợ giảm chuyển động.

## Quyết định triển khai

Tách điều hướng, nội dung bài, lưu tiến độ, phiên thực thi và màn hình nghiên cứu thành module riêng. Tách HTML thành template và CSS theo khu vực. Bỏ các tệp giao diện cũ sau khi thay thế; giữ một đường khởi chạy duy nhất. Không thêm framework chỉ để đổi giao diện.

Mỗi lượt chạy có worker riêng để không nhận kết quả trễ của bài trước hoặc giữ biến cũ. Hủy được cả lúc Python đang khởi động. Mã người học không được đưa vào `exec` của máy chủ. Python trong trình duyệt vẫn là bộ thực thi thật, có lỗi cú pháp, ngoại lệ và thời gian giới hạn.

## Ranh giới cần giữ đúng

Tám bài Python là nội dung tự biên soạn. Gợi ý bài dựa trên quy tắc `authored-rule-v1`, không phải mô hình từ nghiên cứu đã học trên các bài này. Nhật ký có namespace riêng và chỉ xuất khi người dùng yêu cầu; không nhập vào bộ confirmation.

App có thể chứng minh khả năng vận hành và tính nhất quán với kết quả nghiên cứu. Bộ kiểm tra tự động không chứng minh sinh viên thấy dễ dùng, học tốt hơn hay chính sách gợi ý có hiệu quả. Các phát biểu đó cần thiết kế đánh giá riêng; hiện chưa có người học thật tham gia.

Biên bản kiểm tra và các giới hạn của phép đo nằm trong `VALIDATION.md`.
