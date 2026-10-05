# Kế hoạch triển khai: RetryLab — Gia sư AI lập trình (desktop)

**Goal:** thay giao diện chính bằng một app kiểu desktop kể trọn chuỗi đề 4 trên dữ liệu thật (chẩn đoán → gợi ý RL → phiên học → đối chứng âm → đánh giá) cộng trang luyện Python và bảng thuyết trình 8 bước.
**Architecture:** Flask hiện có phục vụ SPA JavaScript thuần tại `/` (giao diện cũ chuyển sang `/classic`); `realdata_engine.py` thêm các hàm giải thích và phiên học từng bước tái dùng đúng lớp của nghiên cứu; `app/desktop.py` mở cửa sổ Edge/Chrome chế độ `--app`.
**Tech Stack:** Python 3.13, Flask, PyTorch (CPU, chỉ suy luận), ES modules không bundler, SVG tự vẽ, Pyodide (đã vendored), Playwright cho kiểm thử trình duyệt.
**Thiết kế đã duyệt:** `docs/specs/2026-09-29-gia-su-ai-desktop-design.md`.

## 0. Luật chung cho mọi gói việc (bắt buộc)

- KHÔNG tạo/sửa: bất kỳ `CLAUDE.md`, `AGENTS.md`, thư mục `.claude/`, `.agents/`, tệp bộ nhớ, tệp cấu hình/settings, `harness/protected.json`, `app/engine.py`, mọi thứ trong `research/`, `paper/`, `data/`, `research/runs/`.
- KHÔNG `git commit`/`push`/đổi cấu hình git. KHÔNG xóa hay đặt lại localStorage của người dùng; kiểm thử trình duyệt chỉ dùng ngữ cảnh Playwright tạm.
- KHÔNG dừng tiến trình theo tên/mẫu; chỉ dừng tiến trình do chính bạn khởi động, theo PID. KHÔNG dùng cổng 8773 (app của người dùng).
- CSP hiện có phải giữ: không `<script>` nội tuyến, **không thuộc tính `style="…"` và không thẻ `<style>`** (kể cả trong SVG), không `eval`, không tải gì từ Internet. Kiểu động dùng CSSOM: `el.style.setProperty(...)`. Thuộc tính trình bày SVG (`fill`, `stroke`, `width`…) được phép.
- Chữ trên giao diện bằng tiếng Việt, trung thực: kết quả phiên học là **mô phỏng**; mã học viên là **ẩn danh**; mô hình luyện Python **học từ người học mô phỏng**.
- Số hiển thị kiểu Việt: dấu phẩy thập phân (`0,62`), dấu chấm hàng nghìn (`562.912`).
- Cuối việc: báo cáo tệp đã đổi, lệnh kiểm thử đã chạy và kết quả, vấn đề còn lại, và **mã model chính xác của bạn**.

## 1. Hợp đồng API (backend ↔ giao diện)

Tất cả số liệu gain tính bằng điểm phần trăm (pp, ×100); xác suất và post-test là tỉ lệ 0–1. JSON không chứa NaN/Infinity.

`problem` (dùng chung) = `{"id": int, "skill": str, "skill_vi": str, "skill_en": str, "difficulty": float|null}` (đúng như `_problem()` hiện có).

**GET `/api/v3/status`** → `{"state": "loading"|"ready"|"error"|"unavailable", "reason": str|null, "session_token": str, "demo_learner": "L0xx"|null}`. `ready` khi `ensure()` xong; `unavailable` khi thiếu run (dùng `self.root`, không dùng hằng module); `error` khi sai hash hoặc nạp lỗi; `demo_learner` chỉ có khi `ready`.

**GET `/api/v3/meta`** (giữ nguyên) + thêm `policy_kinds: {policy: "dqn"|"ppo"|"rule"}` cho 14 chính sách, `world_measures: {world: "latent"|"model"}` cho 9 thế giới (`dkt*`, `sakt*` → `model`; `afm/pfa/zpd/irt` → `latent`), `skills: [{"skill", "name_vi", "name_en"}]` theo thứ tự `kc_map.FUNDAMENTALS`, và `counts: {"learners": int, "interactions": int, "problems": int}` đọc từ `research/runs/accoding-learner-v3/data_counts.json` (`interactions`, `distinct_problems`) và tổng `split_counts` (thêm một test mới cho `counts`, không sửa test có sẵn).

**GET `/api/v3/learners`** → `{"items": [{"id", "history": int, "success": float, "posttest_forecast": float, "weakest": {"skill", "name_vi", "mastery"}}], "demo_learner": "L0xx"}`. `weakest` = argmin mức thành thạo tracker trong các kỹ năng có ≥ 1 bài trong tập ứng viên. `demo_learner`: trong các học viên có 20 ≤ history ≤ 45, chọn nhỏ nhất theo `|success − 0.6| + |history − 30| / 100`, hòa thì mã nhỏ hơn. Tóm tắt tính một lần rồi lưu đệm.

**GET `/api/v3/learners/<id>`** (giữ nguyên).

**GET `/api/v3/learners/<id>/explain?policy=<name>[&flips=0,3]`** →
```json
{"learner_id": "L012", "policy": "ppo_afm", "kind": "ppo", "score_label": "Xác suất chọn",
 "chosen": {"problem": {...}, "tracker_p": 0.62, "drift_pp": 0.41, "score": 0.31},
 "candidates": [{"problem": {...}, "tracker_p": 0.62, "drift_pp": 0.41, "score": 0.31}, "... tối đa 5, score giảm dần"],
 "id3": {"probability": 0.093, "support": 250,
         "path": [{"feature": "problem_success_rate", "feature_vi": "Tỉ lệ vượt qua của bài", "value": 0, "value_vi": "< 0,30"}]},
 "eligible": 94}
```
Điểm theo chính sách (chỉ các bài hợp lệ): DQN = Q của mạng; PPO = softmax các logit đã che; `random` = `np.random.default_rng(7).random(...)` (giống `_decisions`); `curriculum` = −β_A; `easiest` = p; `hardest` = −p; `zpd50/zpd70` = −|p − mục tiêu|; `weakest` = p trong kỹ năng yếu nhất (bài ngoài kỹ năng đó bị loại khỏi danh sách); `greedy_kt` = kỳ vọng tăng post-test − chi phí, giống hệt `policy_env.greedy_tracker`. `chosen` phải trùng lựa chọn của `/api/v3/learners/<id>` cho mọi chính sách. `drift_pp` = 100 × độ trôi của tracker với bài đó. `id3`: đặc trưng tính y hệt `learner_benchmark.tree_features` cho (lịch sử + bài được chọn), đi cây `models/A_id3.json`, xác suất lá = (pos+1)/(n+2), `support` = n của lá; `path` liệt kê các nút đã đi qua (tên và nhãn giá trị bằng tiếng Việt). `flips` là vị trí lịch sử đảo kết quả, như `/api/v3/whatif`.

**POST `/api/v3/session`** (cần header `X-RetryLab-Token`) với `{"learner_id", "world", "policy", "forced": [null|0|1, ...]}` (`forced` tùy chọn, dài ≤ 10, phần tử là `null`, `0` hoặc `1`, không nhận `true/false`) →
```json
{"learner_id", "world", "policy", "measure": "latent"|"model", "lam": 0.05, "seed": int,
 "skills": [{"skill", "name_vi"}],
 "start": {"tracker_post": 0.58, "world_post": 0.55, "skills": [10 số]},
 "steps": [{"step": 1, "problem": {...}, "tracker_p", "world_p", "outcome": 0|1, "forced": bool, "submissions",
            "drift_pp", "surprise_pp", "tracker_post", "world_post", "reward", "skills": [10 số]}],
 "summary": {"world_gain", "tracker_gain", "tracker_drift", "tracker_surprise", "extra_submissions", "return", "phantom_gain"},
 "note": str}
```
Dựng lại vòng lặp của `policy_env.run_episodes` từng bước với **cùng seed** như `simulate()` (`eval_seed + 50000 + index`) và cùng thứ tự luồng ngẫu nhiên. Ép kết quả: thay `uniforms[t]` bằng `0.0` (ép đúng) hoặc `1.0` (ép sai) trước `world.step`. `reward = 100·Δworld_post − lam·(submissions − 1)`; `return = Σ reward`; `phantom_gain = tracker_gain − world_gain`. Không ép gì thì kết quả phải khớp tuyệt đối `simulate()`.

**Trang:** `GET /` trả `app/static/studio/index.html` (chứa `id="studio-app"`); `GET /classic` render `templates/index.html` cũ. `GET /api/health` không được nạp engine nghiên cứu cũ. Engine cũ (`StudyEngine`) chỉ khởi tạo khi một route cũ cần (ví dụ `/api/meta`, `/api/cases`). `/api/v3/status` trả token phiên để giao diện mới POST được mà không gọi `/api/meta`. Khi chạy `server.py` trực tiếp: làm nóng engine v3 ở luồng nền.

Hợp đồng được khóa bởi `app/tests/test_tutor.py` (đã viết trước, đang đỏ).

## 2. Quy ước giao diện (frontend)

```
app/static/studio/index.html      khung trang (id="studio-app"); nạp css/*.css và main.js bằng đường dẫn tuyệt đối /static/studio/...
app/static/studio/main.js         router hash + khung (thanh bên, vùng nội dung), đăng ký view
app/static/studio/api.js          getJSON(path), postJSON(path, body) — tự lấy token từ /api/v3/status; lỗi → Error(message tiếng Việt)
app/static/studio/state.js        store nhỏ: get(key), set(patch), subscribe(fn), emit(event, payload), on(event, fn)
app/static/studio/ui.js           h(tag, attrs, ...children), svg(...), setStyle(el, obj), fmt.{pct,num,pp,int}, nhãn chính sách/thế giới, toast, skeleton, errorPanel
app/static/studio/charts.js       SVG: barList, lineChart, heatmap, timeline, sparkline (tooltip khi di chuột)
app/static/studio/views/*.js      overview, learners, session, evaluation, practice, model
app/static/studio/tour.js         bảng thuyết trình
app/static/studio/css/base.css    token, bố cục, thành phần dùng chung
app/static/studio/css/<view>.css  CSS riêng mỗi view (overview, learners, session, evaluation, practice, model, tour)
```

- **View:** `export default { id, title, async mount(root, params, ctx) { ...; return cleanup } }`, với `ctx = { api, state, navigate, toast, status }`. Route: `#/overview` (mặc định), `#/learners`, `#/learners/<id>`, `#/session`, `#/evaluation`, `#/practice`, `#/practice/<exerciseId>`, `#/model`. Mục "Lưu trữ" mở `/classic`.
- **State dùng chung:** `learnerId`, `policy` (mặc định `ppo_afm`), `world` (mặc định `afm_B`), `demoLearner`. Sự kiện: `session:run` `{learnerId, world, policy, forced?}`.
- **Điểm neo cho bảng thuyết trình** (thuộc tính `data-tour`): overview `kpis`, `pipeline`; learners `skills`, `timeline`, `id3`, `recommendation`, `policies`; session `session-controls`, `session-chart`, `session-summary`; evaluation `heatmap`, `hypotheses`; practice `practice-skills`, `practice-recommendation`, `practice-editor`.
- **Token màu:** nền `#f5f6f8`, bề mặt `#ffffff`, viền `#e2e5e9`, chữ `#16191d`/`#4d5661`/`#7c8691`; thanh bên `#0f1722`; nhấn `#2a78d6`; đúng `#1a7f4b` (nền `#e7f5ed`), sai `#c4322f` (nền `#fbeaea`), cảnh báo `#9a5b00` (nền `#fdf3e2`). Chuỗi biểu đồ theo bảng màu đã kiểm tra của bài báo: tracker tự báo = cam `#eb6834`, tiến bộ thật = xanh ngọc `#1baf7a`, trung tính = xanh `#2a78d6`; bản đồ nhiệt phân kỳ đỏ `#b3322f` → xám `#f0efec` → xanh `#184f95`. Trạng thái đúng/sai luôn kèm ký hiệu ✓/✗, không chỉ dùng màu.
- **Chữ:** `"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif`, 15px; mã: `"Cascadia Mono", Consolas, monospace`; số dùng `font-variant-numeric: tabular-nums`.
- **Cửa sổ chuẩn** 1440×900; dưới 1100px thanh bên thu gọn thành biểu tượng.
- Trước khi viết biểu đồ: gọi skill `dataviz` và theo quy tắc của nó (đường 2px, điểm ≥ 8px, có chú giải khi ≥ 2 chuỗi, lưới nhạt, tooltip khi di chuột, không trục kép).

## 3. Các gói việc

Thứ tự: G1, G2, G3 chạy song song → duyệt → G4, G5 song song → duyệt → G6 → duyệt cuối (người chủ trì).

### G1 — Backend (tệp: `app/realdata_engine.py`, `app/server.py`)
- [ ] Đọc `app/tests/test_tutor.py`, `app/tests/test_realdata.py`, `app/tests/test_engine.py`, `research/accoding_policy/policy_env.py` (`run_episodes`, `Heuristic`, `greedy_tracker`, `Tracker`), `rl.py`, `learner_benchmark.py` (`tree_features`, `tree_value_names`).
- [ ] Cài đặt đúng hợp đồng Mục 1 cho tới khi `python -X utf8 -m unittest discover -s app/tests -p "test_tutor.py" -v` xanh.
- [ ] Không làm hỏng: `python -X utf8 tools/harness.py check --suite backend` phải xanh (thêm `test_tutor.py` vào bộ `backend` trong `tools/harness.py`).
- [ ] Chỉ đọc từ nghiên cứu; không sửa mã trong `research/`.

### G2 — Trình khởi chạy desktop (tệp: `app/desktop.py`, `RetryLab.cmd` ở gốc, `app/tests/desktop_launch_check.py`; có thể tách hàm dùng chung trong `app/launch.py` nhưng giữ nguyên hành vi CLI hiện có)
- [ ] Test trước: `desktop.py --dry-run --no-server --port 8799` in JSON `{"url": "http://127.0.0.1:8799/", "browser": <đường dẫn|null>, "command": [...]}` với `--app=http://127.0.0.1:8799/` và `--window-size=1440,900` khi có Edge/Chrome; `--browser default` → `command` null, `mode` `"default-browser"`.
- [ ] Tìm Edge (App Paths trong registry, `%ProgramFiles(x86)%`, `%ProgramFiles%`, `%LocalAppData%`), rồi Chrome, cuối cùng trình duyệt mặc định. Dùng hồ sơ trình duyệt mặc định (không `--user-data-dir`) để giữ tiến độ.
- [ ] Không có `--dry-run`: đảm bảo server chạy (tái dùng nếu đã chạy, như `launch.py`), đợi `/api/health`, mở cửa sổ, rồi thoát. In tiến trình tiếng Việt.
- [ ] `RetryLab.cmd`: chạy `python "%~dp0app\desktop.py"`; báo lỗi dễ hiểu nếu thiếu Python.
- [ ] Tùy chọn `--install-shortcut`: tạo lối tắt "RetryLab" trên Desktop (PowerShell WScript.Shell) trỏ tới `RetryLab.cmd`, biểu tượng `app/static/studio/icon.ico` (tạo bằng Pillow). Chỉ chạy khi được gọi rõ ràng; test không được gọi tùy chọn này.
- [ ] Thêm `["app/tests/desktop_launch_check.py"]` vào bộ `demo` trong `tools/harness.py` (chỉ thêm, không sửa dòng khác).

### G3 — Nền tảng giao diện (tệp: `app/static/studio/index.html`, `main.js`, `api.js`, `state.js`, `ui.js`, `charts.js`, `css/base.css`, `css/overview.css`, `css/model.css`, `views/overview.js`, `views/model.js`; tạo view giữ chỗ + CSS rỗng cho `learners`, `session`, `evaluation`, `practice`, `tour`; `app/tests/studio_shell_check.py`)
- [ ] Khung app: thanh bên (logo, 6 mục, "Lưu trữ" → `/classic`, nút "▶ Thuyết trình" phát sự kiện `tour:open`), đầu trang của từng view, vùng nội dung, trạng thái đang nạp mô hình từ `/api/v3/status` (thăm dò đến khi `ready`, hiện lý do nếu `unavailable`/`error`).
- [ ] `ui.js`, `charts.js`, `state.js`, `api.js` theo Mục 2; `charts.js` có trang minh họa nội bộ cho test.
- [ ] View **Tổng quan**: 4 ô số liệu từ `/api/v3/meta` (người học, lần nộp đầu — lấy từ meta `population`/`split`, AUC DKT, 14 × 9), sơ đồ chuỗi 5 khâu bấm được, 3 thông điệp chính (H1–H3 bằng lời thường), nút bắt đầu thuyết trình.
- [ ] View **Mô hình**: sơ đồ MDP (trạng thái 230 chiều = 109 xác suất + 109 cờ hợp lệ + 10 kỹ năng + post-test + bước còn lại; hành động 109 bài; phần thưởng), 7 mô hình người học và độ chính xác, DQN/PPO và 3 điều kiện huấn luyện, 9 thế giới, giới hạn.
- [ ] Test trước: `studio_shell_check.py --url` mở `/`, đi qua mọi route, không lỗi console/CSP, thanh bên đánh dấu đúng mục, Tổng quan có 4 ô số liệu.
- [ ] Phát triển trên server riêng cổng 8782 (`python app/server.py --port 8782`), mở `http://127.0.0.1:8782/static/studio/index.html` nếu route `/` chưa có.

### G4 — Học viên + Phiên học (tệp: `views/learners.js`, `views/session.js`, `css/learners.css`, `css/session.css`, `app/tests/studio_learners_session_check.py`)
- [ ] Học viên: danh sách 60 học viên (tìm kiếm, sắp xếp), hồ sơ, bản đồ 10 kỹ năng, dòng thời gian (bấm để đảo kết quả giả định, có nút hoàn tác), thẻ Gợi ý (chọn chính sách, bài được chọn, 5 ứng viên, lý do bằng lời), luật ID3, bảng 14 chính sách.
- [ ] Phiên học: chọn học viên/chính sách/thế giới (tên dễ hiểu), Bước tiếp/Tự chạy/Làm lại, chế độ "Tôi quyết định Đúng/Sai", biểu đồ hai đường, thanh kỹ năng cập nhật, bảng bước (phần thưởng, số lần nộp, độ trôi), tổng kết + giải thích tiến bộ ảo, nút mẫu "Đối chứng âm".
- [ ] Lắng nghe `session:run`; có các neo `data-tour` ở Mục 2.
- [ ] Test Playwright cho hai view, cổng 8783.

### G5 — Luyện Python + Đánh giá (tệp: `views/practice.js`, `views/evaluation.js`, `css/practice.css`, `css/evaluation.css`, `app/tests/studio_practice_eval_check.py`)
- [ ] Luyện Python: tái dùng `/static/js/curriculum.js`, `adaptive.js`, `practice-store.js`, `python-runner.js`; đọc `app/static/js/practice.js` để giữ **y hệt** định dạng lưu lượt làm; mức thành thạo 3 kỹ năng, bài gợi ý + lý do + nhãn mô phỏng, thư viện 12 bài; không gian làm bài (đề, ví dụ, gợi ý từng bước, ô code có Tab/tự thụt dòng/Ctrl+Enter, kết quả từng test, thẻ "Mô hình đã cập nhật" và bài tiếp theo).
- [ ] Đánh giá: bản đồ nhiệt 14 × 9 (bấm ô xem chi tiết), 4 thẻ H1–H4, biểu đồ độ chính xác 7 mô hình, điểm chính và giới hạn.
- [ ] Test Playwright: nhập lời giải đúng cho bài gợi ý, qua 8/8, thấy thẻ cập nhật; bản đồ nhiệt đủ 14 × 9 ô; cổng 8784.

### G6 — Thuyết trình + tích hợp kiểm thử (tệp: `tour.js`, `css/tour.css`, `app/tests/studio_tour_check.py`, các test trình duyệt cũ, `tools/harness.py`)
- [ ] 8 bước như bản thiết kế; bảng góc dưới phải, Lùi/Tiếp/Đóng, phím ←/→/Esc, tô sáng phần tử `data-tour`.
- [ ] Đưa các test trình duyệt cũ sang `/classic` (trang tải `/classic`, API vẫn `/api/...`).
- [ ] Bộ `browser` của harness chạy cả test cũ lẫn các test studio mới.

### Đợt sau (đã được người dùng chọn ngày 29/09/2026): Luyện C
Làm sau khi G4–G6 và duyệt cuối xong, theo một thiết kế riêng: ~12 bài C tự soạn kiểu online judge (stdin/stdout) có bộ test; trình thông dịch C chạy trong trình duyệt (không chạy code trên server, máy không có gcc/clang); gắn mỗi bài vào 10 kỹ năng ACcoding, mượn độ khó từ bài ACcoding tương tự và **ghi rõ là chuyển giao thử nghiệm, chưa kiểm chứng**; không nối trực tiếp với mô hình DKT đã khóa. Lý do: dữ liệu thật là C (98,0% lượt nộp), còn phần luyện hiện tại là Python.

### Duyệt cuối (người chủ trì)
- [ ] Đọc diff từng gói, chạy `fast`, `policy`, `backend`, `browser`, `demo`; chụp màn hình từng view ở 1440×900; sửa lỗi; cập nhật README app, kịch bản demo, HANDOFF, workboard.
