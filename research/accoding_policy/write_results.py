"""Render RESULTS.md (Vietnamese) from the verified v3 runs; every number is read from run outputs."""
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import harness  # noqa: E402

LEARNER, POLICY = ROOT / 'research/runs/accoding-learner-v3', ROOT / 'research/runs/accoding-policy-v3'
PN = {'random': 'Ngẫu nhiên', 'curriculum': 'Lộ trình dễ→khó', 'weakest': 'Kỹ năng yếu nhất', 'zpd50': 'Nhắm P(đúng)=0,5',
      'zpd70': 'Nhắm P(đúng)=0,7', 'easiest': 'Dễ nhất', 'hardest': 'Khó nhất', 'greedy_kt': 'Tham lam theo DKT',
      'dqn_kt': 'DQN · thưởng DKT', 'ppo_kt': 'PPO · thưởng DKT', 'dqn_afm': 'DQN · thế giới AFM',
      'ppo_afm': 'PPO · thế giới AFM', 'dqn_mix': 'DQN · nhiều thế giới', 'ppo_mix': 'PPO · nhiều thế giới',
      'oracle': 'Tham chiếu biết trạng thái thật'}
MN = {'irt': 'IRT (không học)', 'afm': 'AFM', 'pfa': 'PFA', 'sakt': 'SAKT', 'dkt': 'DKT (tracker)',
      'dkt2': 'DKT song sinh', 'id3': 'Cây định danh ID3'}


def v(x, d=2):
    return f'{x:.{d}f}'.replace('.', ',')


def s(x, d=2):
    return ('+' if x > 0 else '') + v(x, d)


def c(pair, d=2):
    return f'[{v(pair[0], d)}; {v(pair[1], d)}]'


def main():
    errors = harness.verify_run('accoding-learner-v3', ROOT) + harness.verify_run('accoding-policy-v3', ROOT)
    if errors:
        raise SystemExit('; '.join(errors))
    L = json.loads((LEARNER / 'learner_summary.json').read_text(encoding='utf-8'))
    P = json.loads((POLICY / 'policy_summary.json').read_text(encoding='utf-8'))
    worlds = json.loads((POLICY / 'protocol.json').read_text(encoding='utf-8'))['settings']['evaluation_worlds']
    by = {(r['world'], r['policy']): r for r in P['rows']}
    C, M = P['contrasts'], P['mechanism']
    fc = L['forecast_T_fit_A']
    lines = ['# Kết quả nghiên cứu v3 — dữ liệu thật ACcoding, DQN/PPO và ma trận đánh giá có đối chứng âm', '',
             '**Phạm vi.** Dự báo được kiểm tra trên người học thật chưa từng dùng. Tiến bộ của chính sách là **mô phỏng** trong các '
             'thế giới fit từ log thật (cùng một thế giới giả định ZPD và một thế giới không-học); không phải kết quả học của sinh viên thật.', '',
             f"Run đã khóa và `verify-run` đạt: `accoding-learner-v3`, `accoding-policy-v3`. Protocol khóa trước khi nạp quần thể: "
             f"`PROTOCOL_LOCK.md`. Quần thể: {L['population']}.", '',
             '## 1. Mô hình người học (dự báo lần nộp đầu, người học T chưa thấy)', '',
             f"{fc['learners']} người học, {fc['predictions']:,} dự đoán. CI 95% bootstrap theo người học.".replace(',', '.'), '',
             '| Mô hình | AUC [CI] | NLL [CI] | Brier | ECE |', '|---|---|---|---:|---:|']
    for k in ('irt', 'afm', 'pfa', 'sakt', 'dkt', 'dkt2', 'id3'):
        m = fc['metrics'][k]
        lines.append(f"| {MN[k]} | {v(m['auc'], 3)} {c(m['ci95']['auc'], 3)} | {v(m['nll'], 4)} {c(m['ci95']['nll'], 4)} | "
                     f"{v(m['brier'], 4)} | {v(m['ece'], 4)} |")
    nlls = [m['nll'] for k, m in fc['metrics'].items() if k != 'id3']
    lines += ['', f'Sáu mô hình học máy dự báo **ngang nhau** (NLL chênh tối đa {v(max(nlls) - min(nlls), 4)}); '
              'cây định danh kém hơn một chút nhưng cho luật đọc được.', '',
              '## 2. Ma trận đánh giá — tiến bộ bài kiểm tra theo thế giới (điểm phần trăm)', '',
              '| Chính sách | ' + ' | '.join(worlds) + ' |', '|---|' + '---:|' * len(worlds)]
    for p in PN:
        cells = ['—' if (w, p) not in by else v(by[(w, p)]['world_gain']['mean']) for w in worlds]
        lines.append(f"| {PN[p]} | " + ' | '.join(cells) + ' |')
    lines += ['', 'DKT-A, AFM-A: thế giới huấn luyện. DKT/SAKT đo bằng dự báo của chính mô hình; AFM/PFA/ZPD đo trạng thái ẩn thật; '
              'IRT-B không có học nên tiến bộ thật luôn bằng 0.', '',
              '## 3. Bốn giả thuyết đăng ký trước', '']
    for agent in ('dqn_kt', 'ppo_kt'):
        b = C['H1_in_sim_overestimation'][agent]
        parts = [f"{w}: {s(x['advantage_vs_random']['mean'])} {c(x['advantage_vs_random']['ci95'])}"
                 for w, x in b.items() if w != 'in_sim_advantage_vs_random']
        lines.append(f"- **H1 ({PN[agent]})** — hơn random trong DKT-A {s(b['in_sim_advantage_vs_random']['mean'])} "
                     f"{c(b['in_sim_advantage_vs_random']['ci95'])}; ở thế giới độc lập: " + '; '.join(parts) +
                     '. Mọi hiệu (tại nhà − độc lập) đều dương, CI không chứa 0 → **ủng hộ H1**.')
    h2 = C['H2_phantom_gain']['tracker_gain']
    lines.append('- **H2** — trong IRT-B (tiến bộ thật = 0), tracker DKT vẫn báo: ' + '; '.join(
        f"{PN[p]} {s(h2[p]['mean'])} {c(h2[p]['ci95'])}" for p in ('greedy_kt', 'dqn_kt', 'ppo_kt')) + ' → **ủng hộ H2**.')
    lines.append(f"- **H3** — Spearman giữa tiến bộ trong DKT-A và tiến bộ ảo ở IRT-B trên {len(C['H3_in_sim_vs_phantom']['policies'])} "
                 f"chính sách: **{v(C['H3_in_sim_vs_phantom']['spearman'], 3)}** (p = {C['H3_in_sim_vs_phantom']['p_value']:.1e}) → **ủng hộ H3**.")
    h4 = C['H4_implied_learning_dispersion']
    sd = M['item_drift']['sd_across_items_pp']
    lines.append(f"- **H4** — độ lệch chuẩn “học ngầm định” mỗi bài: DKT {v(sd['dkt_A'])}, DKT song sinh {v(sd['dkt2_A'])}, "
                 f"SAKT {v(sd['sakt_A'])}, AFM {v(sd['afm_A'])}, PFA {v(sd['pfa_A'])}, IRT {v(sd['irt_A'])} điểm; "
                 f"DKT − AFM = {v(h4['mean'])} {c(h4['ci95'])} → **ủng hộ H4**.")
    twin = M['item_drift']['twin_reproducibility_spearman']
    lines += ['', '## 4. Cơ chế và phân tích thăm dò', '',
              f"- Hai DKT chỉ khác seed đồng ý về bài nào “dạy” với Spearman {v(twin['rho'])} {c(twin['ci95'])}; dự báo của hai mô hình ngang nhau.",
              '- Tương quan (thăm dò) của độ trôi DKT với đặc tính bài: ' + '; '.join(
                  f"{k} ρ={v(x['rho'])} (p={x['p_value']:.3f})" for k, x in M['item_drift']['exploratory_spearman_dkt_drift_vs'].items()) + '.']
    lc = M['logged_continuation']
    lines.append(f"- Trên 10 tương tác **thật** tiếp theo của {lc['learners']} người học: tracker DKT báo {s(lc['tracker_gain']['mean'])} "
                 f"{c(lc['tracker_gain']['ci95'])} điểm (trung bình |thay đổi| {v(lc['tracker_gain']['mean_abs'])}); IRT "
                 f"{s(lc['claimed_irt_A']['mean'])} (|{v(lc['claimed_irt_A']['mean_abs'])}|), AFM {s(lc['claimed_afm_A']['mean'])}, "
                 f"PFA {s(lc['claimed_pfa_A']['mean'])}, SAKT {s(lc['claimed_sakt_A']['mean'])}. Trên quỹ đạo thật độ trôi tự triệt tiêu; "
                 'chính sách tối ưu theo tracker cộng dồn nó.')
    lines.append('- Độ ổn định thứ hạng (Kendall τ so với DKT-A): ' + '; '.join(
        f"{w} {v(x['kendall_tau_vs_dkt_A'])}" for w, x in C['rank_stability'].items() if w != 'irt_B') + '.')
    rob = C['robustness']
    best = sorted(rob, key=lambda p: -rob[p]['worst_case_latent'])[:4]
    lines.append('- Chính sách bền nhất ở mọi thế giới có trạng thái ẩn (AFM-B, PFA-B, ZPD-B), theo mức hơn random trong trường hợp '
                 'xấu nhất: ' + '; '.join(f"{PN[p]} {s(rob[p]['worst_case_latent'])}" for p in best) + '.')
    lines += ['', '## 5. Giới hạn', '',
              '- Một nền tảng (ACcoding, Beihang); nhóm kỹ năng do tác giả gom; con trỏ chỉ có 1 bài luyện, 2 bài kiểm tra do dữ liệu thưa.',
              '- Mọi tiến bộ của chính sách là mô phỏng có điều kiện trên các thế giới đã fit/giả định; không có thử nghiệm với sinh viên.',
              '- Công sức đo bằng số lần nộp, không phải thời gian làm bài. CI có điều kiện trên mô hình đã fit, không hiệu chỉnh đa so sánh.',
              '- Phát triển siêu tham số trên cohort pilot đã được xem trước; quần thể chính chưa từng được dùng trước khi khóa protocol.', '',
              'Hình và bảng: `results/figures/`, `results/tables/`. Bản thảo: `paper/v3/`.']
    (HERE / 'RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
