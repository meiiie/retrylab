"""Render the completed secondary temporal check without further experiments."""
from pathlib import Path
import json

out = Path(__file__).resolve().parent
r = json.loads((out / 'temporal_results.json').read_text(encoding='utf-8'))
fit = json.loads((out / 'temporal_fit_lock.json').read_text(encoding='utf-8'))
cutoff = json.loads((out / 'temporal_cutoff_lock.json').read_text(encoding='utf-8'))
base = r['coverage']['base_pair_coverage_with_past_training_item_support']
rows = r['aggregates']


def get(policy, group='all', value='all'):
    return next(row for row in rows if (row['policy'], row['group'], row['value']) == (policy, group, value))


lines = [
    '# Kiểm tra chronological phụ trên dữ liệu tương lai', '',
    '**Hướng cải thiện dự đoán vẫn xuất hiện khi chỉ fit từ quá khứ, nhưng phạm vi dữ liệu còn rất hẹp.** Đây là secondary/exploratory sensitivity vì kết quả confirmation chính đã được xem trước khi lập protocol phụ; không phải một confirmation độc lập mới.', '',
    f"Cutoff được chọn hoàn toàn từ timestamp của 1.054 training users cũ: 80th percentile, interpolation='higher', bằng **{cutoff['cutoff']}**. Fit first-attempt logistic từ **{fit['past_training_rows']:,}** events ở/before cutoff, với **{fit['first_attempt_fit_rows']:,}** target lần đầu. Toàn bộ scaler, item difficulty và tham số chỉ lấy từ phần quá khứ này; không tune alpha. Có {fit['known_training_items']:,} bài trong training reference quá khứ.", '',
    'Đánh giá vẫn dùng full observed prefix của người held-out, nhưng yêu cầu cả H0 và H1 ở/after cutoff và target thực sự muộn hơn H1. First-observed được xác định trước khi lọc thời gian; không biến một lần nộp lại sau cutoff thành “lần đầu”.', '',
    '## Kết quả trên 2.291 pairs / 516 người', '',
    '| Cách cập nhật | NLL | Brier | Mean p | Tỷ lệ AC | ECE 10 bins |',
    '|---|---:|---:|---:|---:|---:|']
for policy in ['freeze', 'full']:
    a = get(policy)
    lines.append(f"| {policy} | {a['nll']:.6f} | {a['brier']:.6f} | {a['mean_probability']:.6f} | {a['acceptance_rate']:.6f} | {a['ece_10_fixed_bins']:.6f} |")
lines += ['', '| Contrast full − freeze | Chênh lệch | Bootstrap 95% |', '|---|---:|---|']
for c in r['contrasts']:
    lines.append(f"| {c['metric']} | {c['difference_full_minus_freeze']:+.8f} | [{c['lower_95']:+.8f}; {c['upper_95']:+.8f}] |")
lines += ['', 'Các khoảng dùng 1.000 lần bootstrap ghép cặp theo người học. Đầu trên của khoảng NLL/Brier rất gần 0; mức giảm lỗi nhỏ, ECE vẫn khoảng 0,054 sau cập nhật, và mean probability còn thấp hơn tỷ lệ accepted khoảng 5,09 điểm phần trăm. Không coi kết quả này là bằng chứng mạnh về hiệu quả prospective rộng, learning gain hay policy value.', '',
          '## Attrition phải đọc cùng kết quả', '',
          f"Từ {base['multi_submission_episodes']:,} đoạn nhiều lượt trong confirmation, loại {base['excluded_no_next_episode']:,} đoạn không có next episode, {base['excluded_next_previously_observed']:,} có next item đã từng gặp, và **{base['excluded_next_unknown_training_item']:,}** có next item chưa thuộc training support quá khứ. Còn {base['retained_pairs']:,} base pairs; sau đó loại {r['coverage']['excluded_h0_before_cutoff']:,} pairs có H0 trước cutoff. Không có trường hợp H1 trước cutoff sau khi H0 đã đạt điều kiện, và không có successor-time tie trong phần sau cutoff. Cuối cùng còn **2.291 pairs**, chỉ {100*r['coverage']['retained_pairs']/base['multi_submission_episodes']:.2f}% tổng đoạn nhiều lượt và {100*r['coverage']['fraction_of_base_pairs_retained']:.2f}% base pairs có item support quá khứ.", '',
          'Trong confirmation chính dùng training reference toàn thời kỳ, chỉ 251 pairs bị loại vì unknown item; temporal reference loại 11.130. Sự thay đổi support và quần thể giữ lại rất lớn. Không diễn giải khác biệt NLL giữa hai thí nghiệm là tác động thuần túy của việc sửa leakage hoặc chronology.', '',
          '## Bằng chứng thời gian', '',
          '| Mốc | Timestamp nguồn |', '|---|---|']
for key, label in [('cutoff', 'Cutoff'), ('latest_parameter_source_event', 'Training event muộn nhất có thể dùng cho tham số'),
                   ('minimum_h0', 'H0 sớm nhất giữ lại'), ('minimum_h1', 'H1 sớm nhất giữ lại'),
                   ('minimum_target', 'Target sớm nhất giữ lại'), ('maximum_target', 'Target muộn nhất giữ lại')]:
    lines.append(f"| {label} | {r['date_proof'][key]} |")
lines += ['', 'Timestamp không khai báo múi giờ. Kiểm tra chronology áp dụng cho trường `created_at`; thời điểm hoàn thành judge/feedback không được phát hành, nên khả năng đã quan sát verdict ở mỗi checkpoint vẫn là giả định của log. Strict target > H1 loại successor tie; các tie nội bộ khác vẫn xếp theo submission ID.', '',
          '## Lát cắt mô tả đã khóa trước', '',
          '| Lát cắt | Giá trị | Pairs | ΔNLL full − freeze | ΔBrier full − freeze |', '|---|---|---:|---:|---:|']
for group in ['episode_first_ac', 'episode_end_ac', 'retry_group']:
    for value in sorted({row['value'] for row in rows if row['group'] == group}):
        a, b = get('freeze', group, value), get('full', group, value)
        lines.append(f"| {group} | {value} | {a['rows']} | {b['nll']-a['nll']:+.6f} | {b['brier']-a['brier']:+.6f} |")
lines += ['', 'Không có CI riêng cho các lát cắt và không suy luận tác động của luyện tập từ khác biệt giữa chúng. Predictor này vẫn được fit cho immediate first-attempt prediction rồi dùng ở checkpoint H0 sớm hơn; paired-target control của nhánh chính không được lặp lại trong temporal sensitivity.', '',
          '## Tái lập và sửa lỗi được ghi nhận', '',
          '- `temporal_protocol.md`: khóa trước temporal performance, sau khi biết kết quả chính.',
          '- `temporal_cutoff_lock.json`, `temporal_fit_lock.json`: cutoff và model/reference gốc được giữ nguyên.',
          '- Lần chạy đầu dừng trước predictions/losses do pandas nullable Boolean ở boundary đầu tiên. Sửa boundary đó thành True theo định nghĩa episode; fixture và reviewer check đều qua. Resume kiểm tra hash/equality rồi dùng lại cùng model/reference, không refit hoặc chọn lại cutoff.',
          '- `temporal_repair_01.json` lưu thời điểm, lỗi, source hash cũ/mới và hash model/reference đã đóng băng.',
          '- `temporal_results.json`, `temporal_aggregate_metrics.csv`, `temporal_paired_contrasts.csv`, `temporal_calibration_bins.csv` chứa kết quả và metadata đầy đủ.',
          '- Không xuất temporal predictions cá nhân và không thay đổi kết quả confirmation chính.', '',
          f"Lần resume hoàn tất trong {r['elapsed_seconds']:.1f} giây tính trong hàm phân tích; tổng công việc còn có lần chạy lỗi trước đó. Kết quả này kiểm tra một hạn chế thời gian cụ thể, chưa giải quyết future-item oracle selection, stopping/dropout, dữ liệu cùng nền tảng, hay nhận dạng nhân quả."]
(out / 'temporal_RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(str(out / 'temporal_RESULTS.md'))
