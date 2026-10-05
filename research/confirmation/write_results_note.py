"""Render already-frozen aggregate results; performs no model selection."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
result = json.loads((OUT / 'results.json').read_text(encoding='utf-8'))
lock = json.loads((OUT / 'validation_lock.json').read_text(encoding='utf-8'))
rows = result['aggregates']
models = ['all_submissions', 'first_attempt', 'paired_target']
labels = {'all_submissions': 'Mọi lượt nộp', 'first_attempt': 'Chỉ lần đầu', 'paired_target': 'Paired-target + phase'}


def row(model, policy, group='all', value='all'):
    return next(r for r in rows if (r['model'], r['policy'], r['group'], r['value']) == (model, policy, group, value))


def contrast(model, name, metric='nll'):
    return next(r for r in result['contrasts'] if (r['model'], r['contrast'], r['metric']) == (model, name, metric))


def interval(value):
    return f"{value['difference']:+.6f} [{value['lower_95']:+.6f}; {value['upper_95']:+.6f}]"


lines = [
    '# Kết quả xác nhận trên nhóm người học mới', '',
    '**69.825 cặp cùng target tương lai từ 1.500 người chưa xuất hiện trong pilot.** Protocol, cohort selection, model/alpha và mã đánh giá được khóa theo thứ tự trước khi xem kết quả mới. Đây là xác nhận tách người học trên cùng nền tảng/thời kỳ, không phải thử nghiệm nhân quả hay đánh giá chính sách đề xuất.', '',
    'Kết quả chính xác nhận lợi ích dự đoán nhỏ của việc cập nhật lịch sử. Với mô hình chỉ fit lần đầu, full update giảm NLL so với freeze; lợi ích cũng tồn tại trong control được huấn luyện trực tiếp trên cùng future target ở cả H0/H1. Tuy nhiên, thay đổi xác suất trung bình phụ thuộc mạnh vào cách đặt bài toán huấn luyện và không thể gọi là learning gain.', '',
    '## Lỗi dự đoán tổng thể', '',
    '| Predictor | Alpha chọn trên validation | NLL freeze | NLL full | NLL selected | Brier freeze | Brier full | Brier selected |',
    '|---|---:|---:|---:|---:|---:|---:|---:|']
for model in models:
    a, b, c = [row(model, policy) for policy in ['freeze', 'full', 'selected_alpha']]
    lines.append(f"| {labels[model]} | {lock['selected_alpha'][model]:g} | {a['nll']:.6f} | {b['nll']:.6f} | {c['nll']:.6f} | {a['brier']:.6f} | {b['brier']:.6f} | {c['brier']:.6f} |")
lines += ['', '## Chênh lệch ghép cặp và khoảng bootstrap', '',
          'Âm là lỗi thấp hơn. Khoảng percentile 95% từ **1.000 lượt bootstrap theo người học**, với cùng lượt lấy mẫu cho mọi predictor/contrast; point estimates cho mỗi pair trọng số bằng nhau. Khoảng điều kiện trên mô hình và alpha đã fit; chưa bao gồm bất định của tập train/validation. Contrast primary là “chỉ lần đầu, full − freeze, NLL”; các khoảng khác mô tả thứ cấp, không điều chỉnh đa so sánh.', '',
          '| Predictor | ΔNLL full − freeze [95%] | ΔNLL selected − full [95%] | ΔBrier full − freeze [95%] |',
          '|---|---|---|---|']
for model in models:
    lines.append(f"| {labels[model]} | {interval(contrast(model, 'full_minus_freeze'))} | {interval(contrast(model, 'selected_minus_full'))} | {interval(contrast(model, 'full_minus_freeze', 'brier'))} |")
lines += ['', '## Calibration và thay đổi xác suất', '',
          'Tỷ lệ accepted của cùng target là **46,7712%**. ECE dùng 10 khoảng xác suất có độ rộng cố định; các bin đầy đủ nằm trong `calibration_bins.csv`. Không chọn lại alpha hoặc hiệu chỉnh bằng nhãn confirmation.', '',
          '| Predictor | Mean Δp full (điểm phần trăm) | Khoảng 95% Δp (điểm phần trăm) | ECE freeze | ECE full | ECE selected |',
          '|---|---:|---|---:|---:|---:|']
for model in models:
    a, b, c = [row(model, policy) for policy in ['freeze', 'full', 'selected_alpha']]
    diff = contrast(model, 'full_minus_freeze', 'probability')
    lines.append(f"| {labels[model]} | {100*diff['difference']:+.4f} | [{100*diff['lower_95']:+.4f}; {100*diff['upper_95']:+.4f}] | {a['ece_10_fixed_bins']:.6f} | {b['ece_10_fixed_bins']:.6f} | {c['ece_10_fixed_bins']:.6f} |")
lines += ['', 'Control paired-target có mean Δp gần 0 và khoảng chứa 0, đồng thời NLL/Brier vẫn cải thiện. Đây phù hợp với cập nhật thông tin dự đoán; phase intercept cũng có thể căn chỉnh trung bình một cách cơ học trong training. Không diễn giải kết quả này là phục hồi trạng thái năng lực thật, bằng chứng không học, hay chứng minh reward/policy thất bại.', '',
          'Shrinkage validation giúp hai predictor vốn fit bài toán submission trực tiếp; paired-target chọn alpha=1 nên selected và full trùng nhau. Đó là hiệu chỉnh baseline đơn giản, chưa phải thuật toán mới. Không có phép kiểm định superiority giữa các predictor được khóa trong thiết kế này.', '',
          '## Các lát cắt đã khai báo trước', '',
          'Bảng dưới dùng predictor primary “chỉ lần đầu”. Toàn bộ các predictor/policy có trong `aggregate_metrics.csv`. Không có CI riêng cho các lát cắt; khác biệt giữa các hàng không phải tác động của số lần luyện tập.', '',
          '| Lát cắt | Giá trị | Số pairs | ΔNLL full − freeze | ΔNLL selected − full | Mean Δp full |',
          '|---|---|---:|---:|---:|---:|']
for group in ['episode_first_ac', 'episode_end_ac', 'retry_group']:
    values = sorted({r['value'] for r in rows if r['model'] == 'first_attempt' and r['group'] == group})
    for value in values:
        a, b, c = [row('first_attempt', policy, group, value) for policy in ['freeze', 'full', 'selected_alpha']]
        lines.append(f"| {group} | {value} | {a['rows']} | {b['nll']-a['nll']:+.6f} | {c['nll']-b['nll']:+.6f} | {b['mean_probability_change_from_freeze']:+.6f} |")
c = result['coverage']
lines += ['', '## Coverage và giới hạn', '',
          f"Có {c['episodes']:,} đoạn cùng bài, trong đó {c['multi_submission_episodes']:,} đoạn nhiều lượt. Loại {c['excluded_no_next_episode']:,} đoạn không có successor quan sát, {c['excluded_next_previously_observed']:,} đoạn có bài kế tiếp đã từng gặp, và {c['excluded_next_unknown_training_item']:,} đoạn có bài kế tiếp chưa có trong training. Giữ {c['retained_pairs']:,} pairs = {100*c['coverage_of_multi_submission_episodes']:.2f}% đoạn nhiều lượt, bao phủ {100*c['coverage_of_first_observed_targets']:.2f}% các lần đầu quan sát trong confirmation.", '',
          'Danh tính bài kế tiếp được biết khi đánh giá, nên kết quả vẫn điều kiện trên target được quan sát. Điều kiện có ≥20 bài nhìn vào toàn bộ snapshot; stopping, dropout và chọn bài chưa được nhận dạng nhân quả. Độ khó train có thể dùng sự kiện muộn hơn ngày test. Lần đầu là lần đầu trong extract, non-AC gồm lỗi vận hành, và timestamp trùng giây được xếp theo submission ID.', '',
          '## Mốc khóa và tái lập', '',
          f"- Validation/model lock: `{lock['locked_at_utc']}`; fit mất {lock['elapsed_seconds']:.1f} giây (thời gian trong hàm phân tích, không gồm toàn bộ overhead công cụ).",
          f"- Mở confirmation cho modeling: `{result['confirmation_opened_at_utc']}`; hoàn tất `{result['completed_at_utc']}`; evaluation mất {result['elapsed_seconds']:.1f} giây.",
          '- Mô hình mọi lượt: 295.788 training rows; chỉ lần đầu: 127.005; paired-target: 98.038 rows từ 49.019 training pairs, trọng số 0,5 mỗi stage.',
          '- Validation: 10.734 pairs từ 211/212 người; alpha lần lượt 0,5 / 0,75 / 1.',
          '- `locked_protocol.md` và hai amendment giữ nguyên; `implementation_integrity.json` niêm phong hash evaluator/helper/validation lock.',
          '- Các kiểm tra overlap=0, toàn bộ người mới forced confirmation, cùng target difficulty, H1 đúng frozen target prediction đều qua.',
          '- Đã có read-only code review trước evaluate; không phát hiện lỗi quan trọng. Không sửa mô hình hoặc retune sau kết quả confirmation.',
          '- Forecast cá nhân chỉ tồn tại trong handoff nội bộ đã cho phép; báo cáo và các bảng ở thư mục này là tổng hợp.', '',
          'Xem `METHODS.md`, `results.json`, `validation_lock.json`, `paired_contrasts.csv`, `calibration_bins.csv` và các script để tái lập. Đây là một kiểm tra xác nhận nội bộ có khóa trước kết quả, không phải preregistration độc lập bên ngoài.']
(OUT / 'RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(str(OUT / 'RESULTS.md'))
