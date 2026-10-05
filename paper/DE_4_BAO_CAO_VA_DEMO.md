# Đề 4: Hệ khuyến nghị bài tập lập trình cá nhân hóa

**Bản tích hợp ngày 26/09/2026.** Có app chạy thật, mô hình trạng thái đã fit, policy Double DQN đã train và thực nghiệm đã chạy. Đây là prototype nghiên cứu; chưa có thử nghiệm sinh viên thật, chưa chứng minh SOTA hoặc mức công bố Q1/Q2/A*.

## 1. Chúng ta đang giải quyết việc gì?

Đề 4 yêu cầu một hệ thống tự gợi ý bài lập trình tiếp theo dựa trên tình trạng kiến thức của người học và học tăng cường. Chỉ dự báo “bài đang xét sẽ đúng hay sai” chưa hoàn thành yêu cầu đó. Hệ thống phải chọn **bài nào** trong số các bài có thể làm.

Hãy tưởng tượng một người hướng dẫn dạy trẻ xếp hình. Người hướng dẫn có ba việc: nhìn sản phẩm xem có đúng không; ghi nhớ trẻ đang vướng ở thao tác nào; chọn mẫu hình tiếp theo. Trong app, đó là **bộ chạy test**, **mô hình trạng thái**, và **chính sách chọn bài**. Ba việc này liên quan nhưng không thay thế nhau.

Không có dữ liệu do thầy cung cấp và không có can thiệp trên sinh viên thật. Vì vậy, dự án có hai nhánh bằng chứng: log lập trình công khai để kiểm chứng dự báo; và người học mô phỏng để huấn luyện, đánh giá chính sách trên ngân hàng bài của app. Hai nhánh được giữ riêng.

## 2. Những gì đã có trong bản này

| Thành phần | Đã thực hiện | Chứng minh được |
|---|---|---|
| Ngân hàng bài | 12 bài Python, đề, ví dụ, gợi ý, 96 test; gồm Fibonacci | Có nội dung có thể thực hành, không chỉ các ID giả |
| Chấm bài | Python thật trong worker của trình duyệt | Bài làm có qua bộ test cụ thể không |
| Mô hình người học | Bayes filter kiểu BKT, fit trên log mô phỏng, ba nhóm kỹ năng và độ quen bài | Cách cập nhật trạng thái từ lịch sử; chưa đo năng lực người thật |
| Chính sách | Double DQN 6.796 tham số; chín mạng đã train | Có policy học từ reward, không đổi tên quy tắc thành RL |
| Tích hợp | Cùng file catalog và kiểm tra SHA256 ở train/app; suy luận trong trình duyệt | Mô hình và app dùng cùng mã bài/thứ tự hành động |
| Đánh giá | 7 policy, 5 môi trường, 3 seed, 31.500 rollout | So sánh giá trị trong mô phỏng và kiểm tra thất bại |
| Trình diễn | Bàn thử nghiệm lịch sử, trạng thái, Q, bài bị loại, xuất dấu vết | Người xem có thể tự kiểm tra quyết định |
| Bản thảo | Bản tiếng Anh riêng và báo cáo tiếng Việt này | Có Methods/Results/Limitations; chưa phải bài đã phản biện hoặc được chấp nhận |

Ngân hàng dùng ba nhãn kỹ năng chính: lọc và tích lũy; bộ nhớ và cấu trúc dữ liệu; cập nhật trạng thái. Nhãn và độ khó do tác giả gán, chưa được chuyên gia hiệu chuẩn. Simulator không viết hoặc chạy mã: nó sinh nhãn đúng/sai theo những giả định được ghi rõ.

## 3. Model của chúng ta là gì và train thế nào?

**Mô hình thứ nhất: ghi nhớ việc người học đã làm.** Nó có ba con số bên trong, ban đầu đều 30%. Đây là giá trị khởi tạo trong mô phỏng, không phải kết luận “bạn biết 30% Python”. Sau một quan sát đúng/sai, mô hình cập nhật con số tương ứng. Nếu người học đã gặp lại cùng bài nhiều lần, mô hình cho phép kết quả đúng được giải thích một phần bằng độ quen bài.

Tham số được fit bằng cách thử một lưới learning/guess/slip/memory và chọn cấu hình có lỗi log-likelihood thấp nhất trên train. Mỗi seed có 300 lịch sử train và 100 lịch sử validation khác. Không dùng nhãn của lần nộp đang dự báo để tính dự báo trước đó.

**Mô hình thứ hai: chọn bài.** Double DQN nhận 28 số: ba ước lượng kỹ năng, số lần đã gặp 12 bài, 12 cờ đã đạt và ngân sách bước còn lại. Nó trả 12 điểm Q. Q lớn hơn nghĩa là mạng dự đoán tổng phần thưởng tốt hơn trong môi trường đã học; Q không phải phần trăm đúng.

Policy thử chọn bài trong mô phỏng, thấy kết quả, nhận reward, rồi điều chỉnh trọng số. Mỗi mạng học 24.000 lượt tương tác, 2.000 phiên, với 5.872 lần cập nhật gradient. Tổng cộng chín mạng và 216.000 transition. Cấu hình thử nghiệm được khóa trước khi xem tập kiểm tra v2.

Reward chính gồm chi phí giả định cho mỗi bài và điểm thăm dò cuối phiên trên các bài chưa luyện. Policy chỉ nhận kết quả thăm dò ngẫu nhiên, không được nhìn thẳng “kiến thức thật” của simulator. Một đối chứng đổi reward thành số lần làm đúng bài luyện để kiểm tra ảnh hưởng của cách đặt mục tiêu.

**Khi bạn dùng app, trọng số không được train lại.** App chỉ đọc lịch sử mới, cập nhật trạng thái và tính lại Q. GPU/Kaggle không cần thiết để chạy bản này; toàn bộ thực nghiệm mới đã chạy bằng CPU.

## 4. Ví dụ Fibonacci, từ đầu đến cuối

1. **Chưa nộp lần nào:** mô hình vẫn tính được dự báo từ giá trị khởi tạo và thông tin bài. Nhưng chưa có bằng chứng cá nhân; không được nói nó đã hiểu bạn.
2. **Nộp sai:** bộ chạy test báo test nào sai. Mô hình chỉ dùng nhãn chưa qua toàn bộ bài, không coi “3/8 test” là “37,5% năng lực”.
3. **Sửa rồi nộp:** nếu mã khác và có kết quả chấm hợp lệ, mô hình cập nhật tiếp. Lịch sử sai-sai-đúng khác lịch sử đúng ngay lần đầu, dù lần cuối cả hai đều đúng.
4. **Chạy lại y nguyên mã:** nhật ký thao tác có thể thêm một lần chạy nhưng mô hình không coi đó là bằng chứng học mới.
5. **Chọn bài sau:** mạng Q xếp hạng các bài chưa đạt, còn trong tập hành động. Nó có thể gợi ý một kỹ năng khác, không bắt buộc bài được đoán dễ đúng nhất.
6. **Ôn lại Fibonacci đã đạt bằng mã khác:** app vẫn cho chạy test. Vì lịch sử đó nằm ngoài cách simulator huấn luyện policy, app ghi rõ dùng quy tắc dự phòng cho gợi ý tiếp theo. Không giả vờ đã kiểm chứng spaced repetition.

Mô hình hiện không đo thời gian quên theo ngày, không suy ra bạn có chép lời giải không, và không đọc ngữ nghĩa mã để chẩn đoán lỗi. Đây là các giới hạn cụ thể, không phải khả năng đã được triển khai.

## 5. Kết quả thực nghiệm nói gì?

Mỗi môi trường có 300 người học mô phỏng dùng chung giữa policy và seed để so sánh ghép cặp. Tổng 31.500 rollout không có nghĩa 31.500 người học độc lập; chỉ có 1.500 định danh evaluation khác nhau. Thước đo chính là thay đổi xác suất kỳ vọng qua bài thăm dò chưa luyện, không cộng điểm “nhớ bài cũ”.

Trong môi trường giống lúc train:

| Chính sách | Tiến bộ trên bài thăm dò | Tỷ lệ đúng khi luyện |
|---|---:|---:|
| Chọn ngẫu nhiên | 16,96 điểm phần trăm | 51,69% |
| Theo độ khó | 16,64 | 54,75% |
| Chọn kỹ năng yếu nhất | 19,16 | 50,76% |
| Chọn dự báo gần 70% | 14,16 | 59,72% |
| Double DQN bỏ qua độ quen bài | 18,85 | 54,29% |
| Double DQN xét độ quen bài | 17,91 | 53,61% |
| Double DQN thưởng khi làm đúng | 17,24 | 56,16% |

Filter xét độ quen bài giảm lỗi dự báo ở cả ba validation, nhưng policy dùng filter đó thấp hơn policy naive 0,93 điểm phần trăm; CI ghép cặp 95% là [-1,87; -0,05]. So với quy tắc kỹ năng yếu nhất, chênh lệch là -1,24 điểm phần trăm; CI [-2,27; -0,21]. **Kết quả không ủng hộ việc tuyên bố policy mới vượt baseline trong môi trường chính.**

Trong môi trường chỉ nhớ bài cũ mà không học thêm, tất cả policy có tiến bộ chuyển giao bằng 0, dù vẫn có 43,75-54,86% câu trả lời đúng khi luyện. Mức 0 là điều được thiết kế vào negative control. Nó kiểm tra hệ thống đo đúng đại lượng, không chứng minh rằng sinh viên thật không học qua việc sửa bài.

CI được bootstrap trên learner sau khi trung bình ba fit; có điều kiện trên ba mạng đã học, không bao phủ toàn bộ ngẫu nhiên huấn luyện. Có nhiều so sánh chưa hiệu chỉnh; không lấy một khoảng thuận lợi ở môi trường khác để gọi là chiến thắng tổng thể. Bảng đầy đủ ở `research/catalog_policy/RESULTS.md`.

Model đưa vào app được ấn định là aware/probe seed 101 trước kiểm tra để minh họa cơ chế. Nó không phải mô hình được chọn vì thắng bảng kết quả. App luôn ghi “gợi ý thử nghiệm - mô hình học từ mô phỏng”.

## 6. Demo trong 8 phút

**Phút 0-1 - giải thích ba vai trò.** Nói: “Bộ test kiểm tra bài làm. Model ghi nhớ lịch sử để ước lượng trạng thái. Policy quyết định bước tiếp theo. Tôi sẽ cho thấy cả ba hoạt động.”

**Phút 1-3 - Python thật.** Mở `http://127.0.0.1:8773/#exercise/fibonacci`. Dùng mã sai `return n`, xem phản hồi, rồi thay bằng lời giải dưới đây. Lời giải mẫu phục vụ demo kỹ thuật, không được đưa vào bằng chứng sinh viên tự học.

```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```

Chạy test, xem 8/8 và gợi ý bài. Nếu trình duyệt đã có nhiều lịch sử nên hiện fallback, giải thích đúng lý do; không xóa tiến độ người dùng để che nó.

**Phút 3-5 - so sánh lịch sử có kiểm soát.** Mở `http://127.0.0.1:8773/#policy`. Chọn “Fibonacci - đúng ngay lần đầu”, ghi nhận trạng thái; đổi sang “sai → sai → đúng”. Chỉ vào dự báo trước kết quả và trạng thái sau kết quả. Hai người có kết quả cuối giống nhau nhưng thông tin lịch sử khác. Đây là hai lịch sử giả định, không phải hai sinh viên đã tuyển vào thí nghiệm.

**Phút 5-6 - kiểm tra policy.** Mở “Điểm Q, dự báo và bài bị loại”. Chỉ ra bài đã đạt bị loại, bài được gợi ý có Q cao nhất trong các ứng viên, và Q khác xác suất. Bấm “Mở bài này” để thấy quyết định dẫn tới đúng bài có thể làm.

**Phút 6-7 - đối chứng thất bại.** Chuyển môi trường kết quả sang “Chỉ nhớ bài cũ - không học thêm”. Chỉ vào cột làm đúng và gain bằng 0. Câu trình bày: “Nếu chỉ nhìn tỷ lệ đúng trong luyện tập, ta có thể đánh giá nhầm mục tiêu.”

**Phút 7-8 - kết luận trung thực.** Mở môi trường chính, cho thấy baseline kỹ năng yếu nhất cao hơn aware/probe. Nói: “Tôi đã hoàn thành hệ thống có thể chạy và kiểm toán. Thực nghiệm cho thấy cải thiện dự báo chưa đủ đảm bảo cải thiện policy. Chưa có dữ liệu để kết luận tác động với người thật.” Xuất dấu vết JSON nếu hội đồng muốn đối chiếu.

## 7. Những câu hỏi hội đồng có thể hỏi

**Đây có phải RL thật không?** Có: mạng nhận trạng thái, chọn hành động, nhận reward và được cập nhật bằng Double DQN. Có checkpoint, replay buffer và run record. Khi app dùng quy tắc dự phòng thì nhãn đó hiện rõ; không gọi fallback là RL.

**Vì sao chưa dùng PPO hoặc DKT lớn?** Đề nêu các hướng kỹ thuật thay thế. Phiên bản này dùng Bayes filter để quan sát được cơ chế và Double DQN để học chọn bài. Không thêm mạng lớn chỉ để tăng độ phức tạp. Nếu rubric bắt buộc đúng DKT/PPO thì cần đối chiếu lại với yêu cầu cụ thể; PDF hiện tại không ghi rubric như vậy.

**Bài đầu cho người mới lấy đâu ra phần trăm?** Từ prior và tham số học ở mô phỏng. Tính được số không có nghĩa đã biết năng lực cá nhân. App ghi rõ thiếu lịch sử.

**Vậy tác dụng thật sự là gì?** Trong sản phẩm: nối kết quả làm bài với một bước tiếp theo có thể kiểm tra. Trong nghiên cứu: thử và đo xem trạng thái/reward nào dẫn tới lựa chọn tốt hơn theo mục tiêu đã khai báo. Hai tác dụng này chưa đồng nghĩa hiệu quả giáo dục đã được chứng minh.

**Có đạt Q1/Q2/A* không?** Chưa có cơ sở để nhận định đã đạt. Double DQN và KT+RL đã có từ trước; ExRec và UniER là prior art đáng kể. Bản này phù hợp một prototype và nghiên cứu kiểm tra cơ chế/negative result. Muốn gửi venue mạnh cần đối chứng hiện đại được chạy thật, benchmark độc lập hơn và đóng góp mới rõ ràng. Không có thử nghiệm sinh viên thật thì phải giữ phạm vi offline/simulation.

## 8. Mở, kiểm tra, tái lập

```powershell
python app/launch.py --no-browser
python -X utf8 tools/harness.py check --suite all
python -X utf8 tools/harness.py verify-run catalog-policy-v2
```

Nguồn tiếng Anh: `paper/topic4_policy.tex`. Protocol: `research/catalog_policy/protocol.json`. Thiết kế và mã train: `research/catalog_policy/`. Kết quả gốc và chín checkpoint: `research/runs/catalog-policy-v2/`. Các artifact nghiên cứu cũ giữ nguyên.

Nguồn chính: [Code-DKT](https://arxiv.org/abs/2206.03545), [ExRec](https://proceedings.neurips.cc/paper_files/paper/2025/hash/13707aad517ddd6c09ea02e0f55e1e7a-Abstract-Conference.html), [UniER](https://arxiv.org/abs/2605.16750), [counterfactual instructional policy](https://arxiv.org/abs/2606.23015), [Double DQN](https://arxiv.org/abs/1509.06461). Phân tích nguồn và giới hạn đối chiếu: `research/catalog_policy/LITERATURE_AND_DATA.md`.
