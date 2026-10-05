# Kết quả nghiên cứu v3 — dữ liệu thật ACcoding, DQN/PPO và ma trận đánh giá có đối chứng âm

**Phạm vi.** Dự báo được kiểm tra trên người học thật chưa từng dùng. Tiến bộ của chính sách là **mô phỏng** trong các thế giới fit từ log thật (cùng một thế giới giả định ZPD và một thế giới không-học); không phải kết quả học của sinh viên thật.

Run đã khóa và `verify-run` đạt: `accoding-learner-v3`, `accoding-policy-v3`. Protocol khóa trước khi nạp quần thể: `PROTOCOL_LOCK.md`. Quần thể: 4634 ACcoding learners absent from pilot/confirmatory cohorts with >= 20 distinct released problems.

## 1. Mô hình người học (dự báo lần nộp đầu, người học T chưa thấy)

926 người học. 112.950 dự đoán. CI 95% bootstrap theo người học.

| Mô hình | AUC [CI] | NLL [CI] | Brier | ECE |
|---|---|---|---:|---:|
| IRT (không học) | 0,775 [0,772; 0,779] | 0,5667 [0,5636; 0,5702] | 0,1926 | 0,0062 |
| AFM | 0,776 [0,773; 0,779] | 0,5657 [0,5626; 0,5693] | 0,1922 | 0,0055 |
| PFA | 0,776 [0,773; 0,780] | 0,5655 [0,5624; 0,5690] | 0,1921 | 0,0046 |
| SAKT | 0,775 [0,772; 0,779] | 0,5667 [0,5633; 0,5701] | 0,1927 | 0,0119 |
| DKT (tracker) | 0,775 [0,771; 0,778] | 0,5669 [0,5636; 0,5703] | 0,1927 | 0,0045 |
| DKT song sinh | 0,775 [0,771; 0,778] | 0,5672 [0,5640; 0,5707] | 0,1928 | 0,0084 |
| Cây định danh ID3 | 0,763 [0,760; 0,767] | 0,5796 [0,5762; 0,5831] | 0,1975 | 0,0056 |

Sáu mô hình học máy dự báo **ngang nhau** (NLL chênh tối đa 0,0017); cây định danh kém hơn một chút nhưng cho luật đọc được.

## 2. Ma trận đánh giá — tiến bộ bài kiểm tra theo thế giới (điểm phần trăm)

| Chính sách | dkt_A | afm_A | dkt2_A | dkt_B | sakt_B | afm_B | pfa_B | zpd_B | irt_B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ngẫu nhiên | 1,42 | 1,83 | 3,33 | 1,31 | 3,36 | 1,72 | 1,63 | 1,93 | 0,00 |
| Lộ trình dễ→khó | 3,51 | 0,54 | -2,12 | 2,34 | 14,17 | 0,53 | 0,63 | 0,52 | 0,00 |
| Kỹ năng yếu nhất | 4,92 | 1,30 | 1,93 | 5,15 | 3,48 | 0,97 | 0,95 | 0,92 | 0,00 |
| Nhắm P(đúng)=0,5 | -0,86 | 1,75 | 2,58 | -0,97 | 2,32 | 1,66 | 1,51 | 2,18 | 0,00 |
| Nhắm P(đúng)=0,7 | 4,04 | 1,88 | 4,45 | -1,23 | 6,88 | 1,92 | 2,03 | 2,13 | 0,00 |
| Dễ nhất | 0,60 | 0,91 | 8,15 | 5,12 | 8,31 | 0,86 | 0,84 | 0,70 | 0,00 |
| Khó nhất | 3,31 | 2,62 | 7,30 | 2,16 | 0,49 | 2,72 | 2,19 | 1,37 | 0,00 |
| Tham lam theo DKT | 15,31 | 2,02 | 9,00 | -2,99 | 5,70 | 2,35 | 2,42 | 2,00 | 0,00 |
| DQN · thưởng DKT | 14,59 | 1,72 | 10,46 | 7,57 | 4,10 | 1,84 | 1,82 | 1,68 | 0,00 |
| PPO · thưởng DKT | 28,58 | 1,65 | 13,40 | 2,71 | 9,24 | 2,04 | 1,97 | 1,88 | 0,00 |
| DQN · thế giới AFM | 5,06 | 3,07 | 4,48 | 0,46 | 5,27 | 3,24 | 3,35 | 2,59 | 0,00 |
| PPO · thế giới AFM | 7,15 | 3,05 | 7,95 | 0,00 | 2,83 | 3,14 | 3,34 | 2,30 | 0,00 |
| DQN · nhiều thế giới | 13,11 | 1,92 | 7,22 | 1,63 | 7,52 | 2,11 | 1,94 | 2,09 | 0,00 |
| PPO · nhiều thế giới | 11,54 | 2,76 | 5,89 | 1,98 | 5,72 | 3,07 | 3,08 | 2,25 | 0,00 |
| Tham chiếu biết trạng thái thật | — | 3,20 | — | — | — | 3,48 | 3,97 | 3,64 | 0,00 |

DKT-A, AFM-A: thế giới huấn luyện. DKT/SAKT đo bằng dự báo của chính mô hình; AFM/PFA/ZPD đo trạng thái ẩn thật; IRT-B không có học nên tiến bộ thật luôn bằng 0.

## 3. Bốn giả thuyết đăng ký trước

- **H1 (DQN · thưởng DKT)** — hơn random trong DKT-A +13,17 [12,56; 13,73]; ở thế giới độc lập: dkt2_A: +7,12 [6,64; 7,60]; dkt_B: +6,26 [5,78; 6,73]; sakt_B: +0,74 [0,39; 1,11]; afm_B: +0,12 [0,07; 0,17]; pfa_B: +0,19 [0,14; 0,24]; zpd_B: -0,25 [-0,28; -0,22]. Mọi hiệu (tại nhà − độc lập) đều dương, CI không chứa 0 → **ủng hộ H1**.
- **H1 (PPO · thưởng DKT)** — hơn random trong DKT-A +27,16 [26,54; 27,74]; ở thế giới độc lập: dkt2_A: +10,07 [9,60; 10,57]; dkt_B: +1,40 [0,88; 1,88]; sakt_B: +5,87 [5,51; 6,22]; afm_B: +0,32 [0,26; 0,37]; pfa_B: +0,34 [0,29; 0,39]; zpd_B: -0,05 [-0,08; -0,02]. Mọi hiệu (tại nhà − độc lập) đều dương, CI không chứa 0 → **ủng hộ H1**.
- **H2** — trong IRT-B (tiến bộ thật = 0), tracker DKT vẫn báo: Tham lam theo DKT +12,57 [11,97; 13,19]; DQN · thưởng DKT +12,79 [12,17; 13,42]; PPO · thưởng DKT +25,72 [25,06; 26,38] → **ủng hộ H2**.
- **H3** — Spearman giữa tiến bộ trong DKT-A và tiến bộ ảo ở IRT-B trên 14 chính sách: **0,960** (p = 5.1e-08) → **ủng hộ H3**.
- **H4** — độ lệch chuẩn “học ngầm định” mỗi bài: DKT 3,31, DKT song sinh 3,15, SAKT 2,01, AFM 0,20, PFA 0,16, IRT 0,00 điểm; DKT − AFM = 3,11 [3,06; 3,16] → **ủng hộ H4**.

## 4. Cơ chế và phân tích thăm dò

- Hai DKT chỉ khác seed đồng ý về bài nào “dạy” với Spearman 0,35 [0,34; 0,36]; dự báo của hai mô hình ngang nhau.
- Tương quan (thăm dò) của độ trôi DKT với đặc tính bài: course_position ρ=-0,09 (p=0.374); support_fraction ρ=0,32 (p=0.001); attempter_success_rate ρ=-0,15 (p=0.116); irt_difficulty ρ=-0,26 (p=0.006).
- Trên 10 tương tác **thật** tiếp theo của 905 người học: tracker DKT báo +0,41 [-0,35; 1,15] điểm (trung bình |thay đổi| 9,43); IRT -0,13 (|2,42|), AFM +0,49, PFA +0,35, SAKT +1,30. Trên quỹ đạo thật độ trôi tự triệt tiêu; chính sách tối ưu theo tracker cộng dồn nó.
- Độ ổn định thứ hạng (Kendall τ so với DKT-A): dkt2_A 0,49; dkt_B 0,05; sakt_B 0,23; afm_B 0,27; pfa_B 0,27; zpd_B 0,08.
- Chính sách bền nhất ở mọi thế giới có trạng thái ẩn (AFM-B, PFA-B, ZPD-B), theo mức hơn random trong trường hợp xấu nhất: DQN · thế giới AFM +0,66; PPO · thế giới AFM +0,37; PPO · nhiều thế giới +0,32; Nhắm P(đúng)=0,7 +0,20.

## 5. Giới hạn

- Một nền tảng (ACcoding, Beihang); nhóm kỹ năng do tác giả gom; con trỏ chỉ có 1 bài luyện, 2 bài kiểm tra do dữ liệu thưa.
- Mọi tiến bộ của chính sách là mô phỏng có điều kiện trên các thế giới đã fit/giả định; không có thử nghiệm với sinh viên.
- Công sức đo bằng số lần nộp, không phải thời gian làm bài. CI có điều kiện trên mô hình đã fit, không hiệu chỉnh đa so sánh.
- Phát triển siêu tham số trên cohort pilot đã được xem trước; quần thể chính chưa từng được dùng trước khi khóa protocol.

Hình và bảng: `results/figures/`, `results/tables/`. Bản thảo: `paper/v3/`.
