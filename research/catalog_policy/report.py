"""Render aggregate, already-inspected evidence; never fits/selects a model."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent


def main():
    data=json.loads((ROOT/'research/runs/catalog-policy-v2/summary.json').read_text(encoding='utf-8'))
    names={'random':'Random','curriculum':'Curriculum','weakest':'Weakest skill','zpd':'Target p=0.7',
           'ddqn_naive':'DDQN naive / probe','ddqn_aware':'DDQN aware / probe','ddqn_success':'DDQN aware / correctness'}
    lines=['# Kết quả đề 4 — ngân hàng bài và policy v2','',
      '**Phạm vi: người học mô phỏng, không phải tiến bộ của sinh viên thật.**', '',
      'Run `catalog-policy-v2` hoàn tất ngày 26/09/2026; 216.000 transition huấn luyện, 31.500 rollout kiểm tra trên 1.500 định danh người học mô phỏng ghép cặp.', '',
      '## Kết luận chính','',
      'Filter xét độ quen bài giảm NLL ở cả ba tập validation. Tuy nhiên, trong môi trường nominal, policy tương ứng có tiến bộ kỳ vọng thấp hơn DDQN naive 0,93 điểm phần trăm và thấp hơn quy tắc kỹ năng yếu nhất 1,24 điểm phần trăm. Vì vậy **không kết luận policy mới tốt hơn baseline**.', '',
      'Môi trường prerequisite cho kết quả khác với nominal, cho thấy thứ hạng phụ thuộc cơ chế mô phỏng. Trong repair-only, tất cả policy có gain bằng 0 theo đúng định nghĩa môi trường, dù tỷ lệ đúng khi luyện vẫn cao. Đây là kiểm tra cơ chế/null control, không phải phát hiện thực nghiệm về người thật.', '',
      '## Dự báo trước kết quả trên validation mô phỏng','',
      '| Seed | NLL naive | NLL xét độ quen bài |','|---|---:|---:|']
    for seed,fit in data['fits'].items():
        lines.append(f"| {seed} | {fit['naive']['validation_nll']:.6f} | {fit['aware']['validation_nll']:.6f} |")
    lines += ['', '## Tiến bộ trên bài thăm dò chưa luyện','',
      'Đơn vị gain và CI: điểm phần trăm của expected probe success cuối trừ đầu. Tỷ lệ đúng khi luyện là một đại lượng khác.', '',
      '| Môi trường | Policy | Gain | CI 95% | Đúng khi luyện |','|---|---|---:|---|---:|']
    for row in data['rows']:
        ci='; '.join(f'{x*100:.2f}' for x in row['probe_gain']['ci95'])
        lines.append(f"| {row['world']} | {names[row['policy']]} | {row['probe_gain']['mean']*100:.2f} | [{ci}] | {row['practice_success']['mean']*100:.2f}% |")
    lines += ['', '## Chênh lệch ghép cặp','',
      '| Môi trường | Aware/probe trừ | Gain chênh lệch | CI 95% |','|---|---|---:|---|']
    for row in data['contrasts']:
        ci='; '.join(f'{x*100:.2f}' for x in row['ci95'])
        lines.append(f"| {row['world']} | {names[row['right']]} | {row['mean']*100:.2f} | [{ci}] |")
    lines += ['', '## Cách đọc và giới hạn','',
      '- 1.500 bootstrap replicate lấy mẫu lại learner sau khi trung bình ba fit, cùng learner giữa policy. CI có điều kiện trên ba fit; xem `per_fit` trong JSON để đánh giá biến thiên fit. Không hiệu chỉnh nhiều so sánh.',
      '- Không chọn lại checkpoint theo những số này. App dùng aware/probe seed 101 vì đã ấn định trước kiểm tra, phục vụ demo cơ chế. Nó không phải hệ khuyến nghị được xác nhận là tốt nhất.',
      '- Không khẳng định mô hình đã hội tụ tối ưu. 24.000 transition mỗi mạng là ngân sách cố định; không có learning-curve/budget sweep để chứng minh đủ huấn luyện.',
      '- Kỹ năng/độ khó/dynamics là giả định tác giả. Mô phỏng sinh nhãn binary, không chạy mã; nội dung bài dùng cho tính tương thích phần mềm và demo.',
      '- Kết quả ACcoding thật được giữ riêng: cập nhật lịch sử giảm NLL nhỏ; không đo việc gán bài khác hoặc tác động học tập.',
      '- Muốn công bố kết luận mạnh cần benchmark ngoài simulator này và đối chứng recommendation hiện đại chạy thật. Tài liệu SOTA không thay thế phép so sánh.', '',
      '![Kết quả gain trên năm môi trường](figures/transfer_gain.png)', '',
      'Nguồn số liệu: `research/runs/catalog-policy-v2/summary.json`, `rollouts.npz`, `protocol.json`, `record.json`. Bản JSON aggregate trong app được kiểm tra checksum khi triển khai.']
    (HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    figures=HERE/'figures'
    figures.mkdir(exist_ok=True)
    fig,axes=plt.subplots(3,2,figsize=(13,12),layout='constrained')
    colors=['#8294a5','#a99c84','#28785b','#937f9f','#6672a3','#2455bc','#bb7447']
    for ax,world in zip(axes.flat,['nominal','repair_only','slow_transfer','forgetting','prerequisites']):
        rows=[row for row in data['rows'] if row['world']==world]
        for i,row in enumerate(rows):
            m=row['probe_gain']['mean']*100
            low,high=[x*100 for x in row['probe_gain']['ci95']]
            ax.errorbar(m,i,xerr=[[m-low],[high-m]],fmt='o',color=colors[i],capsize=3)
        ax.set_yticks(range(7),[names[row['policy']] for row in rows],fontsize=9)
        ax.invert_yaxis()
        ax.axvline(0,color='#bbb',linewidth=.7)
        ax.set_xlim(-2,26)
        ax.set_title(world.replace('_',' ').title())
        ax.set_xlabel('Expected transfer gain (percentage points)')
        ax.grid(axis='x',alpha=.2)
        ax.spines[['top','right']].set_visible(False)
    axes.flat[-1].axis('off')
    axes.flat[-1].text(.02,.7,'Synthetic learners only\n\n300 paired learners / world\nThree fixed fitted models\n95% learner-bootstrap intervals\n\nIntervals do not quantify human effects\nor all training-run variability.',fontsize=12,va='top')
    fig.suptitle('Repeated-item correctness is distinct from transfer\nCatalog-aligned Double DQN benchmark',fontsize=16)
    for extension in ['png','pdf','svg']:
        fig.savefig(figures/f'transfer_gain.{extension}',dpi=180)
    plt.close(fig)
    print('Wrote aggregate report and PNG/PDF/SVG figure.')


if __name__=='__main__':
    main()
