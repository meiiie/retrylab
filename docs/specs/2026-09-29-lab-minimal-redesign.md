# Thiết kế lại giao diện RetryLab theo phong cách "lab tối giản" (29/09/2026)

Yêu cầu của người dùng: giao diện hiện tại "hơi xấu", "tham lam ở mỗi khung hình", nhìn bối rối. Mong muốn: tối giản kiểu phòng thí nghiệm, sạch, **mỗi chữ xuất hiện đều có ý nghĩa**. Đặc tả này thay phần hình thức và mật độ nội dung của `app/static/studio/`; API, dữ liệu, phép tính và các ràng buộc trung thực giữ nguyên.

Nguồn quy tắc: các skill `~/.claude/skills/better-layout`, `better-typography`, `better-colors`, `better-writing`, `better-ui`, `better-accessibility` (đọc `SKILL.md` của từng skill; phần tham chiếu khi cần). Khi đặc tả này và skill khác nhau, theo đặc tả này.

## 1. Chẩn đoán

| Vấn đề | Ví dụ hiện tại |
|---|---|
| Quá nhiều khối trên một màn hình | Học viên: 3 cột, 7 thẻ cùng lúc; Tổng quan: hero + 4 thẻ số + 5 thẻ quy trình + 3 thẻ phát hiện + hộp cảnh báo |
| Trang trí không mang thông tin | Hình quỹ đạo ở hero, icon trong mọi thẻ và mục menu, viền + bo góc + bóng cho mọi khối |
| Chữ lặp hoặc không cần | "Gia sư AI lập trình" dưới logo, 3 tag ở hero, nhãn "Mô phỏng" lặp ở nhiều khối, phụ đề nhắc lại tiêu đề, câu giải thích nhắc lại con số vừa hiện |
| Quá nhiều màu | Xanh dương, cam, xanh lá, vàng nền, đỏ, thanh bên xanh đen đậm |

## 2. Nguyên tắc

1. **Một màn hình trả lời một câu hỏi.** Tiêu đề là tên màn hình (trùng mục menu). Dòng dẫn ngay dưới là **câu trả lời** — một phát hiện có số, không phải lời giới thiệu.
2. **Ngân sách nội dung.** Mặc định mỗi màn hình hiện: 1 hình chính, tối đa 3–4 con số chính, tối đa 1 đoạn văn ≤ 2 câu. Phần còn lại nằm sau một điều khiển mở rộng có nhãn rõ (`<details>`, tab, hoặc panel chi tiết khi chọn một phần tử).
3. **Mỗi chữ có việc.** Được phép: nhãn gọi tên một đại lượng kèm đơn vị; câu nêu một sự thật có số; hướng dẫn một hành động; cảnh báo làm thay đổi cách hiểu một con số. Không được phép: khẩu hiệu, tag trang trí, câu nhắc lại con số bên cạnh, phụ đề diễn lại tiêu đề, "Bấm vào đây", lời cảnh báo lặp lại.
4. **Phạm vi trung thực nói một lần.** Dòng phạm vi cố định ở chân thanh bên: "Chính sách được đánh giá bằng mô phỏng · dữ liệu ACcoding ẩn danh". Bên trong màn hình chỉ nhắc khi mức bằng chứng **khác** với dòng đó (ví dụ Luyện Python: mô hình học từ người học mô phỏng; Phiên học: một lần chạy của một học viên, không phải trung bình).
5. **Nhóm bằng khoảng trắng, không bằng khung.** Không bọc mọi thứ trong thẻ. Phân tách phần bằng khoảng trắng và một đường kẻ mảnh phía trên. Chỉ dùng nền/khung cho: điều khiển, vùng soạn code, panel nổi (tooltip, tour), phần tử đang được chọn.
6. **Một màu, một nghĩa.** Mực đen–xám cho nội dung; một màu nhấn cho tương tác và lựa chọn; hai màu dữ liệu có nghĩa cố định (Mục 3). Không dùng màu nền để trang trí.
7. **Không icon trang trí.** Chỉ giữ icon có chức năng: mở ngoài ↗, chạy ▶, đóng ✕, mở rộng ▸. Menu không có icon.
8. **Chuyển động tối thiểu.** Chỉ đổi màu/độ mờ ≤ 150 ms. Không nhịp đập, không trượt vào. Tôn trọng `prefers-reduced-motion`.

## 3. Token

Viết trong `css/base.css`, ký hiệu hex như hiện tại (không đổi hệ ký hiệu).

```css
--paper: #ffffff;        /* nền nội dung */
--paper-2: #f7f7f6;      /* thanh bên, nền điều khiển nhẹ, hàng đang hover */
--rule: #e7e7e4;         /* đường kẻ mảnh */
--rule-strong: #cfcfca;  /* viền điều khiển */
--ink: #141414;          /* chữ chính, nút chính */
--ink-2: #4b4b48;        /* chữ phụ (≥ 7:1 trên trắng) */
--ink-3: #6f6f6a;        /* chú thích, nhãn nhỏ (≥ 4.5:1 trên trắng) */
--accent: #1f5fcc;       /* tương tác: link, focus, lựa chọn, thanh kỹ năng được chọn */
--accent-soft: #eef3fc;  /* nền của phần tử đang chọn */
--signal: #d9480f;       /* dữ liệu: điều tracker báo, tiến bộ ảo, giá trị âm */
--signal-soft: #fbe9e1;
--truth: #141414;        /* dữ liệu: tiến bộ thật (đường liền, mực) */
--good: #2f7d4f;         /* chỉ cho ✓ đạt test / giả thuyết được ủng hộ */
--bad: #b42318;          /* chỉ cho ✗ sai test / lỗi */
```

Heatmap: dương = dải của `--accent`, âm = dải của `--signal`, 0 = trắng. Đường tiến bộ thật = `--truth` liền; tracker báo = `--signal` liền; vùng giữa hai đường (tiến bộ ảo) = `--signal-soft`.

**Chữ.** `--font: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif`; `--display: "Segoe UI Variable Display", var(--font)` cho tiêu đề và số lớn; `--mono: "Cascadia Mono", Consolas, monospace` cho mã học viên, mã bài, chỉ số bước, code. Thang cỡ (px): 12 nhãn/chú thích · 13 bảng · 14 giao diện · 15 đoạn đọc · 18 tiêu đề phần · 24 tiêu đề trang · 40 số chính. Độ đậm 400/500/600. Số dùng `font-variant-numeric: tabular-nums`. Chữ viết thường tự nhiên (sentence case), không viết hoa toàn bộ.

**Khoảng cách** (px): 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64. Trong nhóm 8–12; giữa nhóm ≥ 24; giữa các phần 48. Cột nội dung rộng tối đa 1200px, lề 40px (32px khi < 1280px). Đoạn đọc ≤ 68ch.

**Bề mặt.** Bo góc 6px cho điều khiển, 8px cho panel nổi; không bo thẻ vì không còn thẻ. Bóng chỉ cho panel nổi (tooltip, tour, menu). Viền 1px `--rule-strong` cho điều khiển; đường kẻ 1px `--rule` cho cấu trúc.

## 4. Thành phần dùng chung

| Thành phần | Quy tắc |
|---|---|
| Thanh bên | Nền `--paper-2`, rộng 208px, kẻ phải 1px. Trên: chữ "RetryLab" (15px/600), không phụ đề. Menu chỉ chữ, có số thứ tự `01`–`06` bằng mono `--ink-3`; mục đang mở: chữ `--ink` + vạch trái 2px `--ink`. Dưới: trạng thái "● Mô hình sẵn sàng" (12px), dòng phạm vi (12px `--ink-3`), nút "Thuyết trình" (viền), link "Giao diện cũ" (12px). |
| Đầu trang | Tiêu đề 24px/600 + dòng trả lời 15px `--ink-2` (≤ 1 câu), hành động ở phải dạng nút viền hoặc link. Kẻ dưới 1px. Không phụ đề lặp. |
| Nút | Chính: nền `--ink`, chữ trắng, cao 32px — **tối đa một nút chính mỗi màn hình**. Phụ: viền `--rule-strong`, chữ `--ink`. Link-nút: chữ `--accent`. Nhãn bắt đầu bằng động từ. Nhấn: `scale(0.96)`. |
| Số chính (stat) | Nhãn 12px `--ink-3` phía trên, giá trị 40px/500 `--display` tabular, đơn vị 14px `--ink-3` sau giá trị, chú thích ≤ 1 dòng 12px. Không khung. Hàng số cách nhau bằng khoảng trắng. |
| Phần (section) | Kẻ trên 1px, tiêu đề 18px/600, chú thích ≤ 1 dòng 13px `--ink-3`. |
| Bảng | 13px, kẻ ngang mảnh giữa hàng, không kẻ dọc, số căn phải tabular, tiêu đề cột 12px `--ink-3`. Hàng được chọn: nền `--accent-soft`. |
| Tab / segmented | Chữ 14px, gạch dưới 2px `--ink` cho tab đang mở; không nền màu. |
| Badge | Chỉ cho trạng thái thay đổi được (ví dụ "mẫu", "đạt 8/8"). Chữ 12px, viền mảnh, không nền màu. Không badge trang trí. |
| Mở rộng | `<details>` với `<summary>` "▸ nhãn nói rõ nội dung bên trong" (ví dụ "▸ 10 bước chi tiết"), không "Xem thêm". |
| Biểu đồ | Không khung, không nền; lưới ngang mảnh `--rule` hoặc không có; nhãn trục 12px `--ink-3`; ghi nhãn trực tiếp ở cuối đường/thanh thay cho chú giải khi được; đơn vị ở tiêu đề trục. |
| Panel tour | Nổi, nền trắng, bo 8px, bóng; "4/8" bằng mono; tiêu đề 15px/600; lời nói 14px; nút "Lùi" (phụ) và "Tiếp" (chính). Vòng làm nổi: viền 2px `--accent`, cách 4px, không nhịp đập. |

## 5. Từ ngữ thống nhất

| Dùng | Không dùng xen kẽ |
|---|---|
| học viên (người trong dữ liệu ACcoding); "bạn" trong Luyện Python | người học, sinh viên, user |
| bài | câu hỏi, item |
| chính sách | policy, tác tử (trừ khi nói về DQN/PPO đang học) |
| thế giới (môi trường mô phỏng) | môi trường, simulator |
| tiến bộ thật · tracker báo · tiến bộ ảo (= tracker báo − tiến bộ thật) · trôi · bất ngờ | các biến thể khác |
| điểm % (đơn vị của tiến bộ) | pp, % khi là chênh lệch |
| lần nộp đầu | lượt, submission |

Số theo kiểu Việt (0,775; 4.634). Dấu trừ thật "−". Khoảng tin cậy dạng "[25,1; 26,4]" màu `--ink-3`.

## 6. Từng màn hình — ngân sách nội dung

Giữ nguyên mọi móc `data-tour`, `data-action`, `data-role`, `data-view`, `data-nav`, `data-state` mà tour và test đang dùng (danh sách ở `docs/plans/2026-09-29-gia-su-ai-desktop.md` §2 và trong từng view); nếu phải đổi vị trí, gắn móc vào phần tử mới tương ứng.

### 01 Tổng quan — "Đề tài làm gì và tìm thấy gì?"
- Tiêu đề: "Tổng quan". Dòng trả lời nói việc làm và phát hiện trong một câu, số lấy từ API, ví dụ: "Học tăng cường chọn bài tập tiếp theo cho từng học viên — nhưng ở thế giới không ai học, tracker DKT vẫn báo +25,7 điểm %."
- Hàng số (`data-tour="kpis"`): 4.634 học viên · 562.912 lần nộp đầu · 109 bài ứng viên · 14 chính sách × 9 thế giới. Không icon, không khung.
- Quy trình (`data-tour="pipeline"`): một dòng 5 bước đánh số, mỗi bước là link tới màn hình tương ứng, kèm ≤ 6 chữ mô tả.
- Một hình phát hiện chính: PPO · thưởng DKT — "tracker báo" so với "tiến bộ thật" ở DKT-A, AFM-B, IRT-B (số từ `/api/v3/meta`). Một câu kết luận có số.
- Nút chính "Bắt đầu thuyết trình"; link "Mở học viên mẫu L035".
- Bỏ: hero trang trí, 3 tag, 3 thẻ H1–H3 (đã có ở Đánh giá), hộp cảnh báo (đã có ở thanh bên).

### 02 Học viên — "Hệ thống thấy gì ở một học viên và gợi ý bài nào?"
- Trái (240px): danh sách gọn — mỗi hàng: mã (mono), số bài, % đúng lần đầu; ô tìm theo mã. Bỏ chip kỹ năng và thanh nhỏ ở từng hàng.
- Phải: đầu học viên: "L035" + 3 số trên một dòng (bài đã làm · đúng lần đầu · dự báo post-test). Link "Chạy phiên học với học viên này".
- Tab (một tab hiện một lúc): **Gợi ý** (mặc định) · **Kỹ năng** · **Lịch sử** · **Luật ID3**. Trạng thái tab ở `state` khóa `learnerTab` ∈ `recommendation | skills | history | id3`; view nghe thay đổi của khóa này (tour dùng nó).
  - Gợi ý (`data-tour="recommendation"`): chọn chính sách; bài được chọn (mã, kỹ năng, độ khó) + 2 số (P(đúng) theo DKT, trôi kỳ vọng); "Vì sao" ≤ 3 dòng, mỗi dòng một lý do; "▸ 5 ứng viên hàng đầu"; "▸ 14 chính sách chọn gì" (`data-tour="policies"`).
  - Kỹ năng (`data-tour="skills"`): thanh DKT với vạch trung bình lớp và chênh có dấu (giữ logic của G4), một câu giải thích vì sao so với lớp.
  - Lịch sử (`data-tour="timeline"`): dòng thời gian đúng/sai.
  - Luật ID3 (`data-tour="id3"`): đường đi của cây và P(đúng), so với DKT.

### 03 Phiên học — "Làm theo gợi ý 10 bước thì tiến bộ thật khác tracker báo bao nhiêu?"
- Một hàng điều khiển (`data-tour="session-controls"`): Học viên · Thế giới · Chính sách · nút chính "Chạy" · "Tự quyết định Đúng/Sai" (chế độ phụ). "Mẫu nhanh" thành 2 link nhỏ.
- Hình chính (`data-tour="session-chart"`): hai đường qua bước 0–10 — tiến bộ thật (mực) và tracker báo (`--signal`), nhãn giá trị ở cuối đường, vùng chênh tô `--signal-soft`.
- Tổng kết (`data-tour="session-summary"`): 3 số — tiến bộ thật, tracker báo, tiến bộ ảo — và một dòng phân rã "ảo = trôi +32,3 + bất ngờ −0,9". Một câu nhắc: "Một lần chạy của một học viên; kết quả nghiên cứu là trung bình 926 lần." Phần thưởng và lần nộp thêm vào bảng bước.
- "▸ 10 bước chi tiết": bảng bước.
- Bỏ khung kỹ năng lặp lại (đã có ở Học viên), các nhãn "Mô phỏng" rời.

### 04 Đánh giá — "Chính sách nào giúp học thật, trong thế giới nào?"
- Dòng trả lời có số (ví dụ: "Chính sách học theo thưởng DKT dẫn đầu trong bộ mô phỏng của nó nhưng không hơn ngẫu nhiên ở thế giới có học ẩn.").
- Hình chính (`data-tour="heatmap"`): ma trận 14 × 9, chọn "Hơn chọn ngẫu nhiên | Tiến bộ". Chọn một ô → panel chi tiết bên phải (chỉ khi đã chọn; trước đó chỉ một dòng hướng dẫn).
- Bốn giả thuyết (`data-tour="hypotheses"`): bảng 4 hàng — H · phát biểu ngắn · số chính kèm khoảng tin cậy · kết luận. Mỗi hàng mở ra được để xem bằng chứng và tiêu chí đăng ký.
- Chuyển sang Mô hình: biểu đồ AUC/NLL. Bỏ danh sách giới hạn (đã có ở Mô hình và thanh bên).

### 05 Luyện Python — "Làm bài nào tiếp theo, và vì sao?"
- Trang chính: bài gợi ý (tên, một câu đề, nút chính "Làm bài này") (`data-tour="practice-recommendation"`); "▸ Vì sao gợi ý bài này" chứa các lý do; mức thành thạo 3 kỹ năng dạng thanh mảnh (`data-tour="practice-skills"`); thư viện 12 bài dạng danh sách theo kỹ năng (tên · trạng thái), không thẻ. Một dòng: "Mô hình gợi ý học từ người học mô phỏng; con số là ước lượng, không phải điểm."
- Trang làm bài: đề (trái), soạn code + kết quả (phải). Kết quả: "5/8 test đạt" + các test sai hiện trước; "Mô hình đã cập nhật" một dòng; nút chính "Làm bài tiếp theo" chỉ khi đạt.

### 06 Mô hình — "Bài toán được hình thức hóa và huấn luyện thế nào?"
- MDP: 3 cột định nghĩa S / A / R (mỗi cột: một con số lớn + ≤ 2 dòng) và công thức phần thưởng; hình lưới bài giữ nhưng nhỏ.
- Bảng mô hình người học (7 hàng: mô hình · loại · AUC · NLL) + biểu đồ AUC đưa từ Đánh giá sang.
- Bảng tác tử: DQN / PPO × 3 điều kiện huấn luyện + thế giới đã tập luyện (`meta.training_worlds`).
- Bảng thế giới: mã · nhóm · đo bằng · có huấn luyện/chỉ đánh giá.
- Giới hạn: ≤ 5 dòng. Hai link PDF ở đầu trang.

## 7. Ràng buộc giữ nguyên

- CSP: không script nội tuyến, không `style="…"`, không `<style>`, không eval, không tài nguyên ngoài (font hệ thống, không tải font).
- API, lưu trữ `retrylab.practice.v1`, sự kiện `state` (`tour:open`, `session:run`, `policy`, `learnerId`) và hợp đồng view trong `main.js` giữ nguyên; thêm khóa `learnerTab`.
- Số liệu luôn đọc từ API; không gõ tay kết quả nghiên cứu.
- Kiểm thử: mỗi gói cập nhật test của mình cho cấu trúc mới **mà không làm yếu phép kiểm**: vẫn so số với API, không lỗi console, không vi phạm CSP, không tràn ngang ở 1100/1280/1440px, ảnh chụp 1440×900.
