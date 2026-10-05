# Probe cùng một kết quả tương lai trước/sau một chuỗi nộp lại

Đây là kiểm tra **cập nhật trạng thái dự đoán**, không phải ước lượng tác động học tập hay giá trị chính sách đề xuất bài.

Với mỗi người trong test split, tìm đoạn liên tiếp nộp cùng bài `i` có ít nhất hai lần nộp. `H0` kết thúc sau lần nộp đầu của đoạn; `H1` kết thúc sau lần nộp cuối. Cả hai trạng thái dự đoán **cùng kết quả accepted của lần đầu quan sát trên bài `j` ngay sau đoạn đó**. Bài `j` phải chưa xuất hiện trong toàn lịch sử đã quan sát của người này và phải có trong training. Danh tính tương lai của `j` được biết khi đánh giá; đây là điều kiện oracle, không phải mô phỏng quyết định đề xuất trực tuyến.

## Cách làm cố định

- Import helper, hash split và cách ước lượng độ khó từ `research/pilot/first_vs_retry.py`, không sửa tệp đó.
- Một StandardScaler và logistic regression L2, `C=1`, `max_iter=500`, được fit rồi đóng băng. Không tuning hay dùng validation.
- Bảy biến: độ khó training của `j`, tổng lượt lịch sử, tỷ lệ AC lịch sử, kết quả cuối, tỷ lệ AC 5/20 lượt gần nhất, số bài từng gặp. Loại `gap_seconds` trong cả training và dự đoán; không dùng timestamp của target làm đặc trưng.
- `H0` lấy prefix ngay trước lượt thứ hai của đoạn `i`; `H1` lấy prefix ngay trước `j`. Thay độ khó ở cả hai bằng cùng độ khó `j`. Nhãn của `j` chỉ dùng tính loss sau dự đoán.
- Một sensitivity đã được yêu cầu riêng: giữ nguyên mọi lựa chọn và test pairs, chỉ fit mô hình trên **lần đầu quan sát** của training users. Hai mô hình báo riêng, không gộp hoặc chọn theo kết quả.

## Phạm vi quan sát

Test có 234 người, 64.371 lượt nộp, 27.868 lần đầu quan sát bài. Có 32.810 đoạn cùng bài; 12.793 đoạn có ít nhất hai lượt. Loại tuần tự:

| Lý do | Số đoạn |
|---|---:|
| Không quan sát được đoạn tiếp theo | 117 |
| Bài tiếp theo đã từng quan sát trước đó | 1.703 |
| Bài tiếp theo chưa có trong training | 23 |
| Giữ lại | **10.950** |

Có 233 người đóng góp pairs; giữ 85,59% đoạn nhiều lượt và bao phủ 39,29% các target lần đầu trong test. Có **2.473 đoạn kết thúc chưa AC**, vẫn được giữ. Có 240 đoạn đã AC ngay từ lượt đầu, nên không gọi mọi lượt bổ sung là “sửa lỗi”.

## Kết quả tổng hợp

Chênh lệch là `H1 − H0`; NLL/Brier giảm là tốt hơn. Khoảng dưới đây là bootstrap theo người học, 100 lần, percentile 95%, mang tính thăm dò.

| Training predictor | NLL H0 → H1 | ΔNLL [95%] | Brier H0 → H1 | ΔBrier [95%] |
|---|---|---|---|---|
| Mọi lượt nộp, 295.788 dòng | 0,588809 → 0,585660 | −0,003149 [−0,006545; +0,000213] | 0,201916 → 0,200255 | −0,001661 [−0,003247; −0,000166] |
| Chỉ lần đầu, 127.005 dòng | 0,580150 → 0,577637 | −0,002513 [−0,004574; −0,000336] | 0,198573 → 0,197375 | −0,001198 [−0,002129; −0,000312] |

Trung bình xác suất dự đoán thay đổi +0,050410 ở mô hình mọi lượt và +0,025198 ở mô hình chỉ lần đầu. Đây là **thay đổi niềm tin của predictor**, không phải mức tăng năng lực. Độ lớn thay đổi phụ thuộc lựa chọn quần thể training; chưa thực hiện so sánh giá trị hay thứ hạng chính sách.

Với predictor chỉ fit lần đầu, ΔNLL ở đoạn kết thúc chưa AC là −0,002040; ở đoạn kết thúc AC là −0,002652. Theo số lượt bổ sung 1 / 2–3 / ≥4, ΔNLL lần lượt −0,005003 / +0,000497 / −0,002048. Đây là các lát cắt mô tả, không có kiểm định/CI riêng hay điều chỉnh đa so sánh; không diễn giải khác biệt giữa lát cắt như tác động của số lần luyện tập.

Kết quả chỉ hỗ trợ nhận xét hẹp: các quan sát bổ sung trong đoạn nộp bài cung cấp một lượng thông tin có ích cho dự đoán kết quả kế tiếp của mô hình này. Nó chưa chứng minh chuyển giao kiến thức, lợi ích nhân quả của việc nộp lại, hoặc chất lượng đề xuất bài. Khoảng ΔNLL của mô hình mọi lượt còn chứa 0; 100 bootstrap chỉ phù hợp chẩn đoán sơ bộ.

## Kiểm tra và giới hạn

Fixture tổng hợp đã kiểm tra thủ công các đặc trưng của prefix `[0]` và `[0,1]`. Đổi nhãn/score/timestamp của target và các lượt sau, rồi thêm dữ liệu tương lai, không làm thay đổi hai vector đặc trưng. Dự đoán H1 khớp dự đoán thông thường của đúng predictor đã đóng băng trên target; mỗi target chỉ được tính một lần. Kiểm tra read-only độc lập của agent reviewer không phát hiện lỗi quan trọng.

Lựa chọn người có ≥20 bài, lựa chọn đoạn nhiều lượt, dừng nộp bài, dropout và danh tính bài kế tiếp đều chưa được nhận dạng nhân quả. “Lần đầu” chỉ là lần đầu trong bản dữ liệu phát hành. Training split theo người không theo thời gian, nên độ khó bài có thể học từ các sự kiện muộn hơn ngày của target test. Thứ tự khi timestamp trùng giây dùng submission ID; nhãn không AC có thể gồm lỗi vận hành. Point estimates cho mỗi pair trọng số bằng nhau; bootstrap theo người xử lý phụ thuộc, không sửa selection bias. Không tối ưu kiến trúc, reward hay chính sách từ các kết quả này.

## Tệp và tái lập

- `summary.json`, `aggregates.csv`: predictor fit mọi lượt.
- `first_attempt_summary.json`, `first_attempt_aggregates.csv`: sensitivity fit lần đầu.
- Chỉ xuất tổng hợp; không lưu dự đoán cá nhân.

```powershell
python research/fixed_probe/fixed_future_probe.py --input data/processed/accoding/submissions_cohort.csv --bootstrap 100
python research/fixed_probe/fixed_future_probe.py --input data/processed/accoding/submissions_cohort.csv --bootstrap 100 --train-first-only
```
