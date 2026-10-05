# RetryLab — hệ gợi ý bài tập lập trình thích ứng (Đề tài 4, AAI)

Mô hình người học (IRT, AFM, PFA, DKT, SAKT, cây ID3) → bài toán chọn bài viết thành MDP → chính sách học tăng cường (Double DQN, PPO) → đánh giá trong 9 thế giới mô phỏng, có đối chứng âm → ứng dụng máy tính với luyện tập Python và C.

*An adaptive programming-exercise recommender built on real ACcoding submission logs (4,634 learners, 562,912 first attempts): knowledge-tracing learner models, an MDP, Double DQN/PPO agents, and an evaluation across nine simulated worlds including a no-learning negative control. Main finding: a DKT tracker reports large gains even where no learning is possible ("phantom gain"), and policies that win inside the training simulator are the ones that create the most phantom gain. All policy results are simulated; no human-subject study was run.*

## Bắt đầu

| Muốn | Mở |
|---|---|
| Tổng quan dự án và tài liệu | [START_HERE.md](START_HERE.md) |
| Chạy ứng dụng | [app/README.md](app/README.md) |
| Kịch bản demo | [app/DEMO_GIA_SU_AI.md](app/DEMO_GIA_SU_AI.md) |
| Kết quả nghiên cứu v3 | [research/accoding_policy/RESULTS.md](research/accoding_policy/RESULTS.md) |
| Bản thảo (tiếng Anh / tiếng Việt) | [output/pdf/retrylab-v3-manuscript.pdf](output/pdf/retrylab-v3-manuscript.pdf) · [output/pdf/retrylab-v3-ban-thao-tieng-viet.pdf](output/pdf/retrylab-v3-ban-thao-tieng-viet.pdf) |
| Bài thuyết trình | [output/slides/retrylab-de4-stencil.pptx](output/slides/retrylab-de4-stencil.pptx) |
| Đối chiếu yêu cầu đề 4 | [DOI_CHIEU_DE_4_VA_HUONG_TRIEN_KHAI.md](DOI_CHIEU_DE_4_VA_HUONG_TRIEN_KHAI.md) |

## Chạy trên Windows

1. Cài Python 3.13 (chọn "Add python.exe to PATH"), rồi `pip install -r app/requirements.txt`.
2. `python app/download_runtime.py` để tải runtime Python cho trình duyệt (Pyodide, đã ghim SHA-512).
3. Bấm đúp `RetryLab.cmd`, hoặc tải `RetryLab.exe` ở mục Releases, đặt vào thư mục gốc của repo rồi bấm đúp. Exe chỉ là trình khởi động: ứng dụng vẫn chạy bằng Python đã cài.

Không cần GPU hay Internet khi chạy. Máy chủ chỉ nghe trên `127.0.0.1`.

## Không có trong repo

- **Dữ liệu thô** (ACcoding, CodeBench) và **các run nghiên cứu** (`research/runs/`, checkpoint mô hình): không đăng lại. ACcoding: [Zenodo 11395043](https://zenodo.org/records/11395043); CodeBench chưa có giấy phép phân phối lại. Thiếu các artifact này, màn hình nghiên cứu báo "không khả dụng"; phần luyện Python và C vẫn chạy được. Cách tái tạo: [research/reproducibility/README.md](research/reproducibility/README.md) và `python tools/harness.py`.
- Runtime Pyodide (tải bằng bước 2 ở trên). Trình thông dịch C (JSCPP 2.0.9, MIT, đã sửa cho CSP) có sẵn trong `app/static/vendor/jscpp/`; xem [app/THIRD_PARTY.md](app/THIRD_PARTY.md).

## Phạm vi trung thực

Mọi kết quả về chính sách là mô phỏng; chưa thử nghiệm với người học thật. Dự báo xác suất, số test qua, mức thành thạo và tiến bộ là các đại lượng khác nhau. Bài Python và C do nhóm tự soạn, không chung mã bài với ACcoding; gợi ý cho bài C là quy tắc minh bạch, không phải mô hình học.
