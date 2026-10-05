# RetryLab — Gia sư AI cho bài tập lập trình

Ứng dụng máy tính cho đề tài 4: từ dữ liệu nộp bài thật đến mô hình người học, luật đọc được, chính sách chọn bài học tăng cường, đánh giá trong nhiều thế giới mô phỏng và phần luyện Python cho sinh viên. Chạy hoàn toàn trên máy, không cần GPU hay Internet.

## Mở ứng dụng

Bấm đúp **`RetryLab.cmd`** ở thư mục gốc của dự án. Launcher tái sử dụng máy chủ đang chạy hoặc khởi động máy chủ mới (lần đầu khoảng 20–40 giây), rồi mở RetryLab trong cửa sổ riêng, không có thanh địa chỉ và tab, tại `http://127.0.0.1:8773/`. Cuối thanh bên hiện **● Mô hình sẵn sàng** khi các mô hình v3 đã nạp xong. Cửa sổ dòng lệnh tự đóng khi xong; nếu có lỗi, nó dừng lại để bạn đọc thông báo.

Muốn có biểu tượng trên Desktop, chạy một lần `python app/desktop.py --install-shortcut`. Lệnh này tạo lối tắt `RetryLab` (biểu tượng `app/static/studio/icon.ico`) trỏ tới `RetryLab.cmd`; nó chỉ chạy khi bạn gọi rõ ràng.

Launcher ưu tiên Microsoft Edge, rồi Google Chrome, ở chế độ cửa sổ riêng; nếu không có cả hai, RetryLab mở bằng trình duyệt mặc định. Cửa sổ dùng hồ sơ mặc định của trình duyệt được chọn, nên tiến độ luyện tập đã lưu trong trình duyệt đó vẫn hiện. Nếu trước đây bạn luyện tập bằng trình duyệt khác, chọn nó bằng `.\RetryLab.cmd --browser chrome` (hoặc `edge`, `default`). Tùy chọn khác: `--port 8774`, `--no-server` (máy chủ đã chạy sẵn), `--dry-run` (chỉ in kế hoạch JSON).

Không dùng cửa sổ riêng: `python app/launch.py` (hoặc `app/start.cmd`) mở trình duyệt thường; `python app/server.py --port 8774` chạy ở terminal và dừng bằng Ctrl+C. Máy chủ chỉ bind loopback, không dành cho triển khai công khai hoặc nhiều người dùng.

**Trước khi thuyết trình:** bấm đúp `app/check_demo.cmd`, đợi `DEMO CHECK PASSED`, rồi theo [kịch bản demo Gia sư AI](DEMO_GIA_SU_AI.md).

## Sáu màn hình

| Màn hình | Nội dung |
|---|---|
| **Tổng quan** | Dữ liệu ACcoding (4.634 học viên, 562.912 lần nộp đầu), chuỗi năm khâu và kết quả chính. |
| **Học viên** | 60 học viên của nhóm kiểm tra; bốn tab: Gợi ý (bài và lý do của từng chính sách), Kỹ năng (DKT so với trung bình lớp), Lịch sử, Luật ID3. |
| **Phiên học** | Mô phỏng 10 bước gợi ý → làm bài → cập nhật trong một thế giới đã chọn; tách tiến bộ thật với tiến bộ tracker báo (trôi + bất ngờ). Có thể ép kết quả đúng/sai từng bước. |
| **Đánh giá** | Ma trận 14 chính sách × 9 thế giới, khoảng tin cậy và bốn giả thuyết đăng ký trước. |
| **Luyện tập** | Python (12 bài, gợi ý bằng Double DQN học trên người học mô phỏng) hoặc C (13 bài, trình thông dịch JSCPP, gợi ý bằng quy tắc vùng phát triển gần); chạy test ngay trong ứng dụng và nhận bài tiếp theo. |
| **Mô hình** | MDP, bảy mô hình người học, DQN/PPO với ba điều kiện huấn luyện, chín thế giới đánh giá, giới hạn và hai bản thảo PDF. |

Nút **Thuyết trình** (thanh bên) hoặc **Bắt đầu thuyết trình** (Tổng quan) chạy tour 8 bước: tự chuyển màn hình, làm nổi bật vùng cần nói và hiện lời gợi ý. Phím → / ← để chuyển bước, Esc để đóng.

Các màn hình nghiên cứu dùng mô hình và kết quả của hai run đã khóa `accoding-learner-v3` và `accoding-policy-v3`; máy chủ kiểm tra hash của cả hai run trước khi trả dữ liệu. Giải thích quyết định và phiên học được tính lại bằng chính mã nghiên cứu với cùng seed, và được kiểm thử là khớp với kết quả đã ghi. Mọi kết quả về chính sách đến từ mô phỏng; chưa có thử nghiệm can thiệp với người học thật.

## Luyện Python

1. Mở **Luyện Python**. Thanh kỹ năng cho biết niềm tin hiện tại của mô hình; khối **Gợi ý** giải thích vì sao chọn bài tiếp theo. Bấm **Làm bài này** hoặc chọn một bài trong thư viện 12 bài (ví dụ `#/practice/fibonacci`).
2. Đọc đề và ví dụ, viết hàm vào ô mã. Bấm **Chạy kiểm tra** hoặc Ctrl + Enter. Python chạy bằng Pyodide trong trình duyệt, 8 test mỗi bài.
3. Nếu sai, xem đầu vào, kết quả của bạn và kết quả cần trả về; có **Gợi ý từng bước**. Khi qua đủ test, xem mục mô hình đã cập nhật và bấm **Làm bài tiếp theo**.

Mã nháp và nhật ký lưu trong trình duyệt (khóa `retrylab.practice.v1`, cùng định dạng với giao diện cũ, nên tiến độ hiện ở cả hai nơi); xóa dữ liệu trình duyệt sẽ mất bản lưu. Mỗi lượt chạy giới hạn 2,5 giây và có thể bấm **Dừng**. Mã không được gửi lên máy chủ.

Bài gợi ý dùng Bayes filter và Double DQN đã fit/train trên người học mô phỏng với cùng bộ bài. Qua test không đồng nghĩa thành thạo; các ước lượng chưa được hiệu chuẩn với người thật. Khi ngoài phạm vi huấn luyện hoặc không tải được mô hình, ứng dụng ghi rõ là đang dùng quy tắc dự phòng. Mô hình ACcoding không được gán cho bài Python.

## Luyện C

Chọn **C** ở đầu màn Luyện tập (`#/practice-c`). 13 bài tự soạn gắn theo 10 nhóm kỹ năng ACcoding (nhãn chưa kiểm chứng chuyển giao; không nối với mô hình ACcoding đã khóa). Bạn chỉ viết hàm, không viết `main`; ứng dụng ghép `main` cho từng test và chạy bằng JSCPP 2.0.9 trong Web Worker (giới hạn 3 giây, kiểm tra SHA-256 của trình thông dịch trước khi chạy, không gửi mã lên máy chủ). Bài gợi ý chọn bằng quy tắc minh bạch: Beta theo kỹ năng, chỉnh theo độ khó, chọn bài có P(đạt) gần 65%. Tiến độ lưu ở khóa riêng `retrylab.practice.c.v1`. JSCPP là trình thông dịch, chậm hơn C thật và không hỗ trợ đủ chuẩn (ví dụ `\` trong chuỗi, `%lld`, chia số âm); bài và test đã tránh các chỗ này. Dựng lại trình thông dịch: `python -X utf8 app/vendor_src/build_jscpp.py <thư mục tạm>`.

## Giao diện cũ (`/classic`)

Giao diện trước đây vẫn ở **Lưu trữ (giao diện cũ)** cuối thanh bên, hoặc `http://127.0.0.1:8773/classic`. Các công cụ ở đó:

1. **Phát lại hồ sơ** (`/classic#replay`): 69.825 cặp dự báo ACcoding, năm mô hình, phát lại từng bước H0→H1, mở phán quyết thật của bài đích, xuất JSON. Kết quả bài đích chỉ được lấy khi người dùng bấm mở.
2. **Thử nghiệm đầu vào:** sửa nhãn AC/chưa AC, thêm hoặc bớt lần nộp rồi chạy lại năm mô hình. Nhãn giả lập không phải dữ liệu quan sát mới.
3. **Bằng chứng thực nghiệm** (`/classic#evidence`): metric H0/H1, CI bootstrap, biểu đồ NLL và hiệu chỉnh; trình khám phá ngưỡng được ghi rõ là thăm dò sau nghiên cứu.
4. **Bàn thử nghiệm chọn bài** (`/classic#policy`) cho policy v2 trên bộ bài Python, và **ACcoding v3** (`/classic#realdata`).

Tính chính xác của nhánh phát lại:

- Ba logistic lấy từ `research/confirmation/frozen_models.joblib` cùng `training_reference.json`; kiểm tra hash với `validation_lock.json` trước khi load.
- Sáu GRU lấy từ `research/sequential/validation_converged/` (checkpoint cuối đã hội tụ), dùng lớp `QueryGRU` của nghiên cứu; hai ensemble lấy trung bình xác suất của các seed 11, 29, 47.
- `data/processed/accoding/confirmatory_submissions.csv` được kiểm tra hash; các cặp tái dựng phải khớp 69.825 cặp và nhãn của cả năm mô hình.
- Mỗi hồ sơ được suy luận lại trên prefix, không đọc nhãn tương lai; H0/H1 phải khớp CSV dự báo gốc (dung sai `1e-12` cho logistic, `2e-6` cho GRU), sai khác chặn hiển thị hồ sơ.
- Logistic PAIRED chỉ định nghĩa với phase 0 ở H0 và phase 1 ở H1; các bước ở giữa trả `null`.
- Metric sàng lọc/CI đọc từ `research/application/results_{logistic,gru}.json`; biểu đồ ΔNLL dùng CI của phân tích dự báo chính để khớp bản thảo.
- `R00001`…`R69825` là mã hồ sơ theo thứ tự hash cố định; không gửi mã người học hay mã lần nộp gốc đến trình duyệt.

## Artifact cần có khi tái dựng trên máy khác

Giữ nguyên cấu trúc workspace. Giao diện chính cần hai run `research/runs/accoding-learner-v3/` và `research/runs/accoding-policy-v3/` cùng mã `research/accoding_policy/`. Giao diện cũ cần `research/confirmation/`, `research/sequential/validation_converged/`, `research/application/`, `research/pilot/`, `research/fixed_probe/`, `data/processed/accoding/` và `data/processed/private_predictions/`; hướng dẫn tái tạo ở `research/reproducibility/README.md`. Không có chế độ tự thay bằng dữ liệu giả khi thiếu artifact: màn hình tương ứng báo rõ là không khả dụng.

## Kiểm tra

Từ thư mục gốc:

```powershell
python -X utf8 tools/harness.py check --suite backend   # API, tính khớp với run v3, giải thích và phiên học
python -X utf8 tools/harness.py check --suite browser   # giao diện chính và giao diện cũ, máy chủ đang chạy ở 8773
python -X utf8 tools/harness.py check --suite demo      # diễn tập, launcher desktop, khôi phục sau lỗi
```

Kiểm tra trình duyệt dùng Playwright/Chromium trong ngữ cảnh tạm, không đụng tới tiến độ luyện tập của bạn. Ảnh chụp ở `app/test_outputs/`.

## Cấu trúc

- `server.py`: máy chủ Flask (loopback), phục vụ `/` (giao diện chính), `/classic` (giao diện cũ), API và tài liệu. `realdata_engine.py`: nạp run v3, kiểm tra hash, học viên, giải thích, phiên học. `engine.py`: suy luận phát lại ACcoding nguyên bản (được bảo vệ).
- `desktop.py` + `../RetryLab.cmd`: mở cửa sổ ứng dụng; `launch.py`: khởi động hoặc tái sử dụng máy chủ.
- `static/studio/`: giao diện chính — `main.js` (điều hướng), `api.js`, `state.js`, `ui.js`, `charts.js` (SVG), `tour.js` (thuyết trình), `views/` (sáu màn hình), `css/`.
- `static/js/`, `templates/`, `static/styles/`: giao diện cũ. Phần luyện Python của giao diện chính dùng lại `curriculum.js`, `adaptive.js`, `practice-store.js`, `python-runner.js` / `python-worker.js` và `static/python/grader.py`.
- `static/data/catalog-v2.json`: đề/test/nhãn kỹ năng; `policy-v2.json` + `policy-manifest-v2.json`: checkpoint policy mô phỏng và checksum.

Python chạy bằng Pyodide 314.0.7 phục vụ từ `static/vendor/pyodide/`; mỗi lượt chạy dùng worker riêng. CSP chặn script nội tuyến và tải tài nguyên ngoài. Gói `retrylab_source.zip` chỉ chứa nguồn; khi khôi phục, chạy `python app/download_runtime.py` để tải runtime đã ghim SHA-512. Xem `THIRD_PARTY.md`.
