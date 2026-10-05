# Kết quả xác nhận trên nhóm người học mới

**69.825 cặp cùng target tương lai từ 1.500 người chưa xuất hiện trong pilot.** Protocol, cohort selection, model/alpha và mã đánh giá được khóa theo thứ tự trước khi xem kết quả mới. Đây là xác nhận tách người học trên cùng nền tảng/thời kỳ, không phải thử nghiệm nhân quả hay đánh giá chính sách đề xuất.

Kết quả chính xác nhận lợi ích dự đoán nhỏ của việc cập nhật lịch sử. Với mô hình chỉ fit lần đầu, full update giảm NLL so với freeze; lợi ích cũng tồn tại trong control được huấn luyện trực tiếp trên cùng future target ở cả H0/H1. Tuy nhiên, thay đổi xác suất trung bình phụ thuộc mạnh vào cách đặt bài toán huấn luyện và không thể gọi là learning gain.

## Lỗi dự đoán tổng thể

| Predictor | Alpha chọn trên validation | NLL freeze | NLL full | NLL selected | Brier freeze | Brier full | Brier selected |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mọi lượt nộp | 0.5 | 0.589148 | 0.587049 | 0.585624 | 0.201973 | 0.200905 | 0.200268 |
| Chỉ lần đầu | 0.75 | 0.581115 | 0.579549 | 0.579131 | 0.198780 | 0.198115 | 0.197947 |
| Paired-target + phase | 1 | 0.580450 | 0.579035 | 0.579035 | 0.198501 | 0.197908 | 0.197908 |

## Chênh lệch ghép cặp và khoảng bootstrap

Âm là lỗi thấp hơn. Khoảng percentile 95% từ **1.000 lượt bootstrap theo người học**, với cùng lượt lấy mẫu cho mọi predictor/contrast; point estimates cho mỗi pair trọng số bằng nhau. Khoảng điều kiện trên mô hình và alpha đã fit; chưa bao gồm bất định của tập train/validation. Contrast primary là “chỉ lần đầu, full − freeze, NLL”; các khoảng khác mô tả thứ cấp, không điều chỉnh đa so sánh.

| Predictor | ΔNLL full − freeze [95%] | ΔNLL selected − full [95%] | ΔBrier full − freeze [95%] |
|---|---|---|---|
| Mọi lượt nộp | -0.002099 [-0.003262; -0.000829] | -0.001425 [-0.002049; -0.000844] | -0.001068 [-0.001590; -0.000495] |
| Chỉ lần đầu | -0.001566 [-0.002300; -0.000756] | -0.000418 [-0.000614; -0.000236] | -0.000665 [-0.000980; -0.000333] |
| Paired-target + phase | -0.001416 [-0.001842; -0.000971] | +0.000000 [+0.000000; +0.000000] | -0.000593 [-0.000779; -0.000405] |

## Calibration và thay đổi xác suất

Tỷ lệ accepted của cùng target là **46,7712%**. ECE dùng 10 khoảng xác suất có độ rộng cố định; các bin đầy đủ nằm trong `calibration_bins.csv`. Không chọn lại alpha hoặc hiệu chỉnh bằng nhãn confirmation.

| Predictor | Mean Δp full (điểm phần trăm) | Khoảng 95% Δp (điểm phần trăm) | ECE freeze | ECE full | ECE selected |
|---|---:|---|---:|---:|---:|
| Mọi lượt nộp | +4.9427 | [+4.8947; +4.9915] | 0.045583 | 0.036700 | 0.039771 |
| Chỉ lần đầu | +2.4789 | [+2.4489; +2.5082] | 0.014387 | 0.011700 | 0.007673 |
| Paired-target + phase | -0.0153 | [-0.0372; +0.0063] | 0.006132 | 0.007155 | 0.007155 |

Control paired-target có mean Δp gần 0 và khoảng chứa 0, đồng thời NLL/Brier vẫn cải thiện. Đây phù hợp với cập nhật thông tin dự đoán; phase intercept cũng có thể căn chỉnh trung bình một cách cơ học trong training. Không diễn giải kết quả này là phục hồi trạng thái năng lực thật, bằng chứng không học, hay chứng minh reward/policy thất bại.

Shrinkage validation giúp hai predictor vốn fit bài toán submission trực tiếp; paired-target chọn alpha=1 nên selected và full trùng nhau. Đó là hiệu chỉnh baseline đơn giản, chưa phải thuật toán mới. Không có phép kiểm định superiority giữa các predictor được khóa trong thiết kế này.

## Các lát cắt đã khai báo trước

Bảng dưới dùng predictor primary “chỉ lần đầu”. Toàn bộ các predictor/policy có trong `aggregate_metrics.csv`. Không có CI riêng cho các lát cắt; khác biệt giữa các hàng không phải tác động của số lần luyện tập.

| Lát cắt | Giá trị | Số pairs | ΔNLL full − freeze | ΔNLL selected − full | Mean Δp full |
|---|---|---:|---:|---:|---:|
| episode_first_ac | 0 | 68048 | -0.001721 | -0.000390 | +0.025387 |
| episode_first_ac | 1 | 1777 | +0.004353 | -0.001490 | +0.001881 |
| episode_end_ac | 0 | 16739 | -0.000778 | -0.000194 | -0.019677 |
| episode_end_ac | 1 | 53086 | -0.001815 | -0.000489 | +0.038810 |
| retry_group | 1 | 32033 | -0.002607 | -0.000360 | +0.035478 |
| retry_group | 2-3 | 24102 | -0.001203 | -0.000394 | +0.023969 |
| retry_group | 4+ | 13690 | +0.000229 | -0.000598 | +0.001222 |

## Coverage và giới hạn

Có 215,200 đoạn cùng bài, trong đó 83,303 đoạn nhiều lượt. Loại 735 đoạn không có successor quan sát, 12,492 đoạn có bài kế tiếp đã từng gặp, và 251 đoạn có bài kế tiếp chưa có trong training. Giữ 69,825 pairs = 83.82% đoạn nhiều lượt, bao phủ 38.82% các lần đầu quan sát trong confirmation.

Danh tính bài kế tiếp được biết khi đánh giá, nên kết quả vẫn điều kiện trên target được quan sát. Điều kiện có ≥20 bài nhìn vào toàn bộ snapshot; stopping, dropout và chọn bài chưa được nhận dạng nhân quả. Độ khó train có thể dùng sự kiện muộn hơn ngày test. Lần đầu là lần đầu trong extract, non-AC gồm lỗi vận hành, và timestamp trùng giây được xếp theo submission ID.

## Mốc khóa và tái lập

- Validation/model lock: `2026-09-26T02:20:56.161647+00:00`; fit mất 125.7 giây (thời gian trong hàm phân tích, không gồm toàn bộ overhead công cụ).
- Mở confirmation cho modeling: `2026-09-26T02:22:26.188060+00:00`; hoàn tất `2026-09-26T02:26:22.292893+00:00`; evaluation mất 236.1 giây.
- Mô hình mọi lượt: 295.788 training rows; chỉ lần đầu: 127.005; paired-target: 98.038 rows từ 49.019 training pairs, trọng số 0,5 mỗi stage.
- Validation: 10.734 pairs từ 211/212 người; alpha lần lượt 0,5 / 0,75 / 1.
- `locked_protocol.md` và hai amendment giữ nguyên; `implementation_integrity.json` niêm phong hash evaluator/helper/validation lock.
- Các kiểm tra overlap=0, toàn bộ người mới forced confirmation, cùng target difficulty, H1 đúng frozen target prediction đều qua.
- Đã có read-only code review trước evaluate; không phát hiện lỗi quan trọng. Không sửa mô hình hoặc retune sau kết quả confirmation.
- Forecast cá nhân chỉ tồn tại trong handoff nội bộ đã cho phép; báo cáo và các bảng ở thư mục này là tổng hợp.

Xem `METHODS.md`, `results.json`, `validation_lock.json`, `paired_contrasts.csv`, `calibration_bins.csv` và các script để tái lập. Đây là một kiểm tra xác nhận nội bộ có khóa trước kết quả, không phải preregistration độc lập bên ngoài.
