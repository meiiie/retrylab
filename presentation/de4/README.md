# Bài thuyết trình đề 4 (dựng bằng skill stencil)

Kết quả: `output/slides/retrylab-de4-stencil.pptx` — 28 slide 16:9, nền tối kiểu 3Blue1Brown, có lời thuyết trình trong phần ghi chú, 2 hoạt hình manim (chỉ chạy ở chế độ trình chiếu). Mọi con số lấy từ app, tức từ hai run đã khóa `accoding-learner-v3`, `accoding-policy-v3`.

Skill dùng: [ghanemja/stencil](https://github.com/ghanemja/stencil) commit `8f5c5a2` (MIT) — `pptx-template-styler` (template → `extract_style.py` → `content.json` → `apply_template.py`), `pptx-math-3b1b` (`render_math.py`, bảng màu và `apply_style` cho biểu đồ), `manim-3b1b` (`render_animation.py`, kiểu `custom_scene`). Stencil không được chép vào repo.

## Dựng lại

```powershell
git clone https://github.com/ghanemja/stencil <stencil>; git -C <stencil> checkout 8f5c5a2
python -m venv <venv>; <venv>\Scripts\pip install python-pptx matplotlib numpy sympy pillow manim playwright
python -X utf8 app/launch.py --no-browser                     # app phải chạy ở 8773
cd presentation/de4
python -X utf8 gather_data.py build/data.json                  # số liệu từ /api/v3
python -X utf8 capture_app.py build/screens                    # ảnh chụp app, ngữ cảnh trình duyệt tạm
<venv>\Scripts\python -X utf8 make_template.py build/template-3b1b.pptx
<venv>\Scripts\python -X utf8 <stencil>/pptx-template-styler/scripts/extract_style.py --template build/template-3b1b.pptx
<venv>\Scripts\python -X utf8 build_deck.py --stencil <stencil> --out ../../output/slides/retrylab-de4-stencil.pptx
```

## Những gì mở rộng so với stencil (không sửa mã của stencil)

- Template tự dựng: mọi khung ảnh 16:9 để `insert_picture` không cắt hình; khung chú thích mang `idx` nhỏ hơn khung ảnh vì `apply_template.py` lấy placeholder đầu tiên không phải tiêu đề làm chú thích.
- Biểu đồ có nhãn giá trị, cột nhóm màu và nhãn điểm có đường dẫn (`render_plot.py` không có chú thích), nhưng dùng nguyên `style.apply_style` và bảng màu Manim.
- GIF của manim bị dithering từng khung (~50–60 MB mỗi clip); `compact_gif` gom điểm ảnh về bảng màu cố định, 960×540, giữ một nửa số khung → ~2–6 MB.
- Biến môi trường `PYTHONUTF8=1` cho các tiến trình con, vì `render_animation.py` ghi file cảnh không chỉ định mã hóa (chữ tiếng Việt lỗi trên Windows).
- Bảng được định dạng lại cho nền tối sau khi dựng.

Kiểm tra trực quan: xuất từng slide ra PNG bằng PowerPoint (`build/preview/`), đã xem cả 28 slide.
