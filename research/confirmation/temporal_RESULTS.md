# Kiểm tra chronological phụ trên dữ liệu tương lai

**Hướng cải thiện dự đoán vẫn xuất hiện khi chỉ fit từ quá khứ, nhưng phạm vi dữ liệu còn rất hẹp.** Đây là secondary/exploratory sensitivity vì kết quả confirmation chính đã được xem trước khi lập protocol phụ; không phải một confirmation độc lập mới.

Cutoff được chọn hoàn toàn từ timestamp của 1.054 training users cũ: 80th percentile, interpolation='higher', bằng **2025-10-27T08:45:57**. Fit first-attempt logistic từ **236,631** events ở/before cutoff, với **103,285** target lần đầu. Toàn bộ scaler, item difficulty và tham số chỉ lấy từ phần quá khứ này; không tune alpha. Có 2,220 bài trong training reference quá khứ.

Đánh giá vẫn dùng full observed prefix của người held-out, nhưng yêu cầu cả H0 và H1 ở/after cutoff và target thực sự muộn hơn H1. First-observed được xác định trước khi lọc thời gian; không biến một lần nộp lại sau cutoff thành “lần đầu”.

## Kết quả trên 2.291 pairs / 516 người

| Cách cập nhật | NLL | Brier | Mean p | Tỷ lệ AC | ECE 10 bins |
|---|---:|---:|---:|---:|---:|
| freeze | 0.650422 | 0.230270 | 0.498176 | 0.574422 | 0.080802 |
| full | 0.646527 | 0.228424 | 0.523568 | 0.574422 | 0.054134 |

| Contrast full − freeze | Chênh lệch | Bootstrap 95% |
|---|---:|---|
| nll | -0.00389455 | [-0.00758543; -0.00010021] |
| brier | -0.00184519 | [-0.00363634; -0.00001670] |
| probability | +0.02539222 | [+0.02399912; +0.02671486] |

Các khoảng dùng 1.000 lần bootstrap ghép cặp theo người học. Đầu trên của khoảng NLL/Brier rất gần 0; mức giảm lỗi nhỏ, ECE vẫn khoảng 0,054 sau cập nhật, và mean probability còn thấp hơn tỷ lệ accepted khoảng 5,09 điểm phần trăm. Không coi kết quả này là bằng chứng mạnh về hiệu quả prospective rộng, learning gain hay policy value.

## Attrition phải đọc cùng kết quả

Từ 83,303 đoạn nhiều lượt trong confirmation, loại 735 đoạn không có next episode, 12,492 có next item đã từng gặp, và **11,130** có next item chưa thuộc training support quá khứ. Còn 58,946 base pairs; sau đó loại 56,655 pairs có H0 trước cutoff. Không có trường hợp H1 trước cutoff sau khi H0 đã đạt điều kiện, và không có successor-time tie trong phần sau cutoff. Cuối cùng còn **2.291 pairs**, chỉ 2.75% tổng đoạn nhiều lượt và 3.89% base pairs có item support quá khứ.

Trong confirmation chính dùng training reference toàn thời kỳ, chỉ 251 pairs bị loại vì unknown item; temporal reference loại 11.130. Sự thay đổi support và quần thể giữ lại rất lớn. Không diễn giải khác biệt NLL giữa hai thí nghiệm là tác động thuần túy của việc sửa leakage hoặc chronology.

## Bằng chứng thời gian

| Mốc | Timestamp nguồn |
|---|---|
| Cutoff | 2025-10-27T08:45:57 |
| Training event muộn nhất có thể dùng cho tham số | 2025-10-27T08:45:57 |
| H0 sớm nhất giữ lại | 2025-10-27T09:07:52 |
| H1 sớm nhất giữ lại | 2025-10-27T09:13:29 |
| Target sớm nhất giữ lại | 2025-10-27T10:17:25 |
| Target muộn nhất giữ lại | 2025-12-30T14:24:33 |

Timestamp không khai báo múi giờ. Kiểm tra chronology áp dụng cho trường `created_at`; thời điểm hoàn thành judge/feedback không được phát hành, nên khả năng đã quan sát verdict ở mỗi checkpoint vẫn là giả định của log. Strict target > H1 loại successor tie; các tie nội bộ khác vẫn xếp theo submission ID.

## Lát cắt mô tả đã khóa trước

| Lát cắt | Giá trị | Pairs | ΔNLL full − freeze | ΔBrier full − freeze |
|---|---|---:|---:|---:|
| episode_first_ac | 0 | 2208 | -0.004084 | -0.001926 |
| episode_first_ac | 1 | 83 | +0.001145 | +0.000310 |
| episode_end_ac | 0 | 555 | +0.009828 | +0.004832 |
| episode_end_ac | 1 | 1736 | -0.008282 | -0.003980 |
| retry_group | 1 | 1015 | -0.004010 | -0.001956 |
| retry_group | 2-3 | 776 | -0.008068 | -0.003807 |
| retry_group | 4+ | 500 | +0.002815 | +0.001425 |

Không có CI riêng cho các lát cắt và không suy luận tác động của luyện tập từ khác biệt giữa chúng. Predictor này vẫn được fit cho immediate first-attempt prediction rồi dùng ở checkpoint H0 sớm hơn; paired-target control của nhánh chính không được lặp lại trong temporal sensitivity.

## Tái lập và sửa lỗi được ghi nhận

- `temporal_protocol.md`: khóa trước temporal performance, sau khi biết kết quả chính.
- `temporal_cutoff_lock.json`, `temporal_fit_lock.json`: cutoff và model/reference gốc được giữ nguyên.
- Lần chạy đầu dừng trước predictions/losses do pandas nullable Boolean ở boundary đầu tiên. Sửa boundary đó thành True theo định nghĩa episode; fixture và reviewer check đều qua. Resume kiểm tra hash/equality rồi dùng lại cùng model/reference, không refit hoặc chọn lại cutoff.
- `temporal_repair_01.json` lưu thời điểm, lỗi, source hash cũ/mới và hash model/reference đã đóng băng.
- `temporal_results.json`, `temporal_aggregate_metrics.csv`, `temporal_paired_contrasts.csv`, `temporal_calibration_bins.csv` chứa kết quả và metadata đầy đủ.
- Không xuất temporal predictions cá nhân và không thay đổi kết quả confirmation chính.

Lần resume hoàn tất trong 119.7 giây tính trong hàm phân tích; tổng công việc còn có lần chạy lỗi trước đó. Kết quả này kiểm tra một hạn chế thời gian cụ thể, chưa giải quyết future-item oracle selection, stopping/dropout, dữ liệu cùng nền tảng, hay nhận dạng nhân quả.
