# Chính sách chọn bài: nhánh mô phỏng riêng

Nhánh này hoàn thiện một phần còn thiếu của đề 4 bằng **mô hình người học được fit và policy Q-learning được train thật**, trên dữ liệu **hoàn toàn mô phỏng**. Không đổi mô hình ACcoding và không gán kết quả cho sinh viên thật.

`protocol.json` định nghĩa câu hỏi, nguồn dữ liệu, mục tiêu, seed, split, ngân sách và mọi output trước khi chạy. `data_contract.md` xác định vì sao chưa thể gắn trực tiếp model/policy này vào ngân hàng bài Python của app.

Chạy kiểm tra và một thực nghiệm mới:

```powershell
python -X utf8 tools/harness.py check --suite policy
python -X utf8 tools/harness.py run policy-controlled-v1 --protocol research/policy/protocol.json -- "{python}" research/policy/benchmark.py --output "{run}"
python -X utf8 tools/harness.py verify-run policy-controlled-v1
```

Mỗi seed tạo hai mô hình người học từ 400 lịch sử, báo NLL trên 100 lịch sử khác, rồi train hai bảng Q qua 4.000 học viên mô phỏng/mỗi bảng. Policy được đánh giá với bốn đối chứng trên 5 môi trường × 400 học viên, cùng ngân sách 8 bài. Có môi trường chỉ tăng khả năng qua bài cũ mà không học thêm, và môi trường quan hệ tiên quyết khác cấu trúc môi trường train.

Policy chỉ nhận lịch sử/kết quả và trạng thái ước lượng. Reward terminal là một điểm kiểm tra mô phỏng quan sát được; latent mastery chỉ dành cho bộ đánh giá độc lập. Action costs là giả định đơn vị thời gian, không phải thời gian đo từ người thật.

Kiểm tra có ý nghĩa: thế giới không học không thể tăng điểm probe kỳ vọng; không chọn bài đã hết lượt; prediction không đọc nhãn tương lai; update không sửa lịch sử; Q-learning tái lập được; fallback cho state chưa gặp được ghi rõ.

Các bảng kết quả chỉ báo trung bình, từng seed và khoảng min/max mô tả. Không gọi ba seed là kiểm định ý nghĩa thống kê, không tuyên bố thắng SOTA. Nếu policy không hơn baseline thì giữ nguyên kết quả để quyết định thí nghiệm tiếp theo.
