# Luyện C trong RetryLab (29/09/2026)

Workboard: `c-practice`. Người dùng muốn luyện C vì dữ liệu nghiên cứu (ACcoding) là C. Ranh giới trung thực: bộ bài C do nhóm tự soạn, không chung mã bài với ACcoding; nhãn kỹ năng lấy theo 10 nhóm kỹ năng ACcoding nhưng **chưa kiểm chứng chuyển giao**; không nối với DKT/PPO đã khóa; gợi ý là **quy tắc minh bạch**, không phải mô hình học.

## Chạy C trong trình duyệt

- Trình thông dịch: JSCPP 2.0.9 (MIT), đóng gói tại `app/static/vendor/jscpp/jscpp.js` bằng `app/vendor_src/build_jscpp.py` (bỏ `eval` để hợp CSP; `system()` bị tắt). `manifest.json` ghi SHA-256; app kiểm tra hash trước khi chạy như với Pyodide.
- Chạy trong Web Worker riêng mỗi lượt, giới hạn 3 giây (dừng worker), in tối đa 8.000 ký tự. Mã không gửi lên máy chủ.
- Giới hạn đã đo: chậm hơn C thật nhiều lần (fib(20) ≈ 1 s); chuỗi chứa `\\` bị giải sai → bài và test tránh `\\`. JSCPP báo truy cập ngoài mảng ("index out of bound") — hiển thị như lỗi chạy có ích cho người học.
- Học viên viết **hàm**, không viết `main`. Bộ chấm ghép mã học viên + `main` sinh từ test; mỗi test in một dòng có đánh dấu `#k:` rồi so với kết quả mong đợi. Lỗi biên dịch báo đúng dòng trong mã học viên (mã học viên đặt đầu chương trình).

## 12 bài (`app/static/data/catalog-c-v1.json`)

| id | Tên | Kỹ năng ACcoding | Độ khó | Hàm |
|---|---|---|---|---|
| c-seconds | Đổi ra giây | basics | 1 | `int tong_giay(int h, int m, int s)` |
| c-grade | Xếp loại điểm | conditionals | 1 | `char xep_loai(int diem)` — ≥85 'A', ≥70 'B', ≥50 'C', còn lại 'D' |
| c-digit-sum | Tổng chữ số | loops | 1 | `int tong_chu_so(int n)` (n ≥ 0) |
| c-count-div | Đếm ước | loops | 2 | `int dem_uoc(int n)` (n ≥ 1) |
| c-sum-positive | Tổng số dương | arrays | 1 | `int tong_duong(int a[], int n)` |
| c-max-index | Vị trí lớn nhất đầu tiên | arrays | 2 | `int vi_tri_lon_nhat(int a[], int n)` (n ≥ 1) |
| c-vowels | Đếm nguyên âm | strings | 2 | `int dem_nguyen_am(char s[])` (a e i o u, chữ thường và hoa) |
| c-reverse | Đảo xâu tại chỗ | strings | 2 | `void dao_xau(char s[])` |
| c-swap | Hoán đổi qua con trỏ | pointers | 2 | `void hoan_doi(int *a, int *b)` |
| c-bits | Đếm bit 1 | bits | 2 | `int dem_bit_1(int n)` (n ≥ 0) |
| c-gcd | Ước chung lớn nhất | arithmetic | 2 | `int ucln(int a, int b)` (a, b ≥ 0, không đồng thời 0) |
| c-power | Lũy thừa đệ quy | recursion | 2 | `long long luy_thua(int a, int n)` → nếu JSCPP không hợp `long long`, dùng `int` với số nhỏ |
| c-sort | Sắp xếp tăng dần | sorting_search | 3 | `void sap_xep(int a[], int n)` |

(13 dòng: chọn 12 bằng cách bỏ `c-count-div` nếu thời gian chạy test quá 1 s/bài; nếu không, giữ cả 13 và ghi đúng số.)

Mỗi bài: đề 1–2 câu, quy tắc, 2 ví dụ, khung hàm, 3 gợi ý từng bước, 6–8 test gồm trường hợp biên, lời giải tham chiếu (chỉ dùng trong test, không gửi tới trình duyệt người học — lưu ở `app/tests/c_reference_solutions.json`), một lời giải sai điển hình cho demo.

## Gợi ý bài tiếp theo (quy tắc, không học)

Mỗi kỹ năng có Beta(1 + số lần đạt lần đầu, 1 + số lần chưa đạt lần đầu). P(đạt) ước lượng của một bài = logistic(logit(trung bình Beta) − 0,8 × (độ khó − 2)). Chọn bài chưa hoàn thành có P gần 0,65 nhất (vùng phát triển gần 60–70%); hòa thì độ khó thấp hơn. Hiển thị: bài gợi ý, kỹ năng, P ước lượng, một dòng "Quy tắc vùng phát triển gần — không phải mô hình học; nhãn kỹ năng theo nhóm ACcoding, chưa kiểm chứng chuyển giao."

## Giao diện

- Mục menu `05` đổi thành "Luyện tập"; trong màn có chọn ngôn ngữ **Python · C** (tab kiểu base). Route `#/practice` (Python, giữ nguyên) và `#/practice-c`, `#/practice-c/<id>` (C). Cùng phong cách lab tối giản và cùng bố cục với Luyện Python (trang chính: bài gợi ý, mức kỹ năng, thư viện theo kỹ năng; trang làm bài: đề | code + kết quả).
- Kho lưu riêng: `retrylab.practice.c.v1` (không đụng `retrylab.practice.v1`).
- Tour bước 8 nhắc có cả C.
