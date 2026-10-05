# Bộ báo cáo theo hướng dẫn tạp chí

Bản sửa dàn trang ngày **27/09/2026**, dựa trên thực nghiệm đã khóa `catalog-policy-v2` và mốc tài liệu 26/09/2026. Xem [các lỗi đã sửa và thông số đo lại](LAYOUT_REVISION.md). Đây là bản đọc nghiên cứu có nguồn chỉnh sửa; chưa được xác nhận là một hồ sơ hoàn toàn sẵn sàng nộp Q1.

## Mở tài liệu

- [Bản tiếng Việt để đọc/báo cáo](../../output/pdf/retrylab-journal-vi.pdf).
- [Bản tiếng Anh theo cấu trúc nghiên cứu](../../output/pdf/retrylab-journal-en.pdf).
- [Nguồn LaTeX tiếng Anh](../topic4_policy.tex): dùng lớp `elsarticle` của Elsevier, frontmatter/abstract/keywords; văn bản, công thức, bảng và hình TikZ/PGFPlots có thể chỉnh sửa, không cần file hình hoặc bibliography bên ngoài. Biên dịch chưa được xác nhận do lỗi môi trường.
- [Bản Markdown tiếng Việt](report_vi.md) và [tiếng Anh](report_en.md): đã điền số liệu tự động, có thể đọc/chỉnh sửa.
- [Hình tóm tắt SVG](figures/graphical_abstract.svg), [sơ đồ hệ thống](figures/figure_1_architecture.svg), [quy trình](figures/figure_2_protocol.svg), [kết quả dự báo và chính sách](figures/figure_3_prediction_policy.svg), [tương phản trong năm môi trường](figures/figure_4_stress_contrasts.svg).
- [Bảng kết quả đầy đủ CSV](tables/policy_results.csv), [tương phản ghép cặp](tables/paired_contrasts.csv), [kết quả fit](tables/filter_fits.csv).
- [Đối chiếu yêu cầu tạp chí](JOURNAL_ALIGNMENT.md); [nguồn và bài mẫu đã tải](references/SOURCES.md).

Ứng dụng/kịch bản demo vẫn ở [app/DEMO_READY.md](../../app/DEMO_READY.md). Báo cáo khoa học này bổ sung cho kịch bản vận hành, không thay thế lệnh kiểm tra trước buổi demo.

## Tạp chí và bài mẫu

Chọn **Computers and Education: Artificial Intelligence** vì phạm vi AI trong giáo dục phù hợp đề tài. Xếp hạng đã kiểm chứng là **Q1, SJR 2024, danh mục Education**; không đổi nhãn thành Q1 năm 2026 hoặc JCR. Quy cách lấy từ hướng dẫn tác giả được truy cập ngày 26/09/2026, không suy ra từ chữ Q1.

Bài mẫu đã tải hợp pháp từ HAL/Inria: Sein Minn (2022), *AI-assisted knowledge assessment techniques for adaptive learning environments*, 3, 100050; DOI [10.1016/j.caeai.2022.100050](https://doi.org/10.1016/j.caeai.2022.100050). Đây là bài tổng quan. Chúng tôi tham khảo cách trình bày mô hình, công thức, hình, bảng và tài liệu tham khảo; bài thực nghiệm của dự án có cấu trúc phương pháp/kết quả/thảo luận riêng. Không sao chép nội dung, sơ đồ, logo hoặc dàn trang xuất bản của Elsevier.

## Tái dựng trong workspace

Chạy từ thư mục gốc dự án, bằng Python có `numpy`, `matplotlib`, `reportlab`, `PyMuPDF`, `Pillow`:

```powershell
python -X utf8 paper/journal/build_report.py
python -X utf8 paper/journal/check_report.py
python -X utf8 tools/harness.py verify-run catalog-policy-v2
```

Môi trường đã chạy: `C:/Python313/python.exe`, Python 3.13.7. Script dùng font Times New Roman của Windows. Không cần GPU, Internet hoặc huấn luyện lại để dựng báo cáo. Các script dựa trên cấu trúc workspace và hồ sơ kiểm thử hiện tại; ZIP báo cáo là gói đọc/chỉnh sửa, không phải toàn bộ môi trường tái huấn luyện độc lập.

Sửa nội dung ở `manuscript_en.md` / `manuscript_vi.md`, rồi chạy lại. Các token `{{...}}` trong template lấy từ artifact, không xuất hiện trong tài liệu thành phẩm. Đầu ra `report_en.md`, `report_vi.md`, `paper/topic4_policy.tex` và hai PDF là file được sinh. Nếu sửa trực tiếp TeX/Markdown đầu ra, lần dựng sau sẽ thay đổi các chỉnh sửa đó; cần chuyển sửa nội dung trở lại template.

## Nguồn số liệu và bảo toàn kết quả

`build_assets.py` kiểm tra mã băm run, đọc `summary.json`, so trung bình gain và practice correctness với toàn bộ `rollouts.npz`, rồi tạo 35 dòng kết quả, 15 tương phản, 6 kết quả fit. Khoảng tin cậy được lấy nguyên từ kết quả đã khóa, không chọn lại sau khi nhìn kết quả. `build_report.py` đọc cấu hình, checkpoint, danh mục, hồ sơ demo/parity để điền số liệu. Đây là khai thác artifact thực nghiệm đã có, không phải thu thêm dữ liệu người thật.

`asset_manifest.json` ghi mã băm đầu vào/hình/bảng; `report_build.json` ghi kiểm tra token, abstract, highlights và mã băm bản thảo; `report_qa.json` ghi kiểm tra PDF. `layout_en.json` và `layout_vi.json` ghi lề 25 mm và tọa độ chèn hình/công thức. Hình SVG giữ text chỉnh sửa được; PDF dùng đường vector và font nhúng. Các biểu đồ không do mô hình tạo ảnh sinh ra. Hỗ trợ của AI trong viết mã vẽ và soạn thảo được công bố trong bản thảo; tác giả vẫn phải xem chính sách AI của nơi nộp.

## Cách tạo PDF và tình trạng TeX

PDF được dựng bằng **ReportLab + PyMuPDF**, dùng cùng văn bản, số liệu, công thức và hình vector; không được mô tả là PDF biên dịch từ TeX. Trình biên dịch tích hợp đã được gọi nhưng lỗi môi trường `Unable to find standard directories for platform`. Nguồn TeX được giữ và mở trong editor; tính biên dịch chưa được xác nhận. `native_compile_status.json` lưu chẩn đoán. Hình trong TeX được mã hóa trực tiếp bằng TikZ/PGFPlots và giữ cùng dữ liệu, nhưng bố cục khác bản PDF đọc.

Hồ sơ dự báo lịch sử, model, run thí nghiệm và dữ liệu người dùng không bị ghi đè. Bản TeX policy trước chỉnh lý được lưu ở `archive/topic4_policy.pre-journal.tex`.

## Trước khi gửi tạp chí

Đọc `JOURNAL_ALIGNMENT.md` và `AUTHOR_INFORMATION.md`. Cần tác giả thật xác nhận tên/đơn vị/đóng góp, tài trợ, xung đột lợi ích, đạo đức và toàn bộ nội dung. Chưa có DOI kho dữ liệu hoặc baseline hiện đại đã tái lập cùng benchmark. Không sử dụng số lượng rollout mô phỏng như số sinh viên thật, không gọi simulated cost là thời gian làm bài đo được, và không coi việc đúng form là bằng chứng đủ để công bố Q1.
