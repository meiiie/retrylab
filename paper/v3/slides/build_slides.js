// Vietnamese presentation for topic 4 (study v3). Numbers come from slide_data.json, exported from the
// verified harness runs by export_slide_data.py. Run: node build_slides.js  (pptxgenjs from tmp/slides).
const path = require("path");
const fs = require("fs");
const pptxgen = require(path.resolve(__dirname, "../../../tmp/slides/node_modules/pptxgenjs"));

const D = JSON.parse(fs.readFileSync(path.join(__dirname, "slide_data.json"), "utf8"));
const OUT = path.resolve(__dirname, "../../../output/slides/retrylab-v3-thuyet-trinh.pptx");

const C = { ink: "13213C", ink2: "3B4A63", muted: "6B7280", teal: "0E7C7B", tealSoft: "D7EFEE",
  coral: "E4572E", coralSoft: "FCE3DA", gray: "F3F5F8", line: "D9DEE6", white: "FFFFFF", gold: "C9A227" };
const H = "Cambria", B = "Calibri";

const nf = (x, d = 2) => Number(x).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
const int = (x) => Number(x).toLocaleString("vi-VN");
const sgn = (x, d = 1) => (x > 0 ? "+" : "") + nf(x, d);

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.author = "Nhóm đề tài 4";
pres.title = "Tác tử chọn bài tập lập trình học từ dữ liệu thật";

function title(slide, text, sub) {
  // one line at 26pt holds about 46 characters of Cambria bold; shrink longer titles instead of wrapping
  const size = text.length <= 46 ? 26 : text.length <= 54 ? 23 : 21;
  slide.addText(text, { x: 0.5, y: 0.3, w: 9, h: 0.6, fontFace: H, fontSize: size, bold: true, color: C.ink,
    margin: 0, isTextBox: true });
  if (sub) slide.addText(sub, { x: 0.5, y: 0.88, w: 9, h: 0.35, fontFace: B, fontSize: 13, color: C.muted,
    margin: 0, isTextBox: true });
}
function card(slide, x, y, w, h, fill = C.gray) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill },
    line: { color: fill }, shadow: { type: "outer", color: "000000", opacity: 0.08, blur: 6, offset: 2, angle: 90 } });
}
function badge(slide, x, y, label, fill = C.teal) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.46, h: 0.46, fill: { color: fill }, line: { color: fill } });
  slide.addText(label, { x, y, w: 0.46, h: 0.46, fontFace: B, fontSize: 14, bold: true, color: C.white,
    align: "center", valign: "middle", margin: 0, isTextBox: true });
}
function footer(slide, n, dark = false) {
  slide.addText(`Đề 4 · Nghiên cứu v3 · ${n}`, { x: 7.4, y: 5.27, w: 2.1, h: 0.25, fontFace: B, fontSize: 9,
    color: dark ? "9AA7BD" : C.muted, align: "right", margin: 0, isTextBox: true });
}
function chartBase(extra) {
  return Object.assign({ fontFace: B, catAxisLabelFontSize: 10, valAxisLabelFontSize: 9, catAxisLabelColor: C.ink2,
    valAxisLabelColor: C.muted, valGridLine: { color: "E5E7EB", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelFontSize: 9, dataLabelColor: C.ink2, dataLabelFormatCode: "0.0",
    titleFontFace: B, titleFontSize: 12, titleColor: C.ink2, showTitle: true }, extra);
}

// 1 — title --------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.ink };
  s.addText("ĐỀ 4 · AAI · HỆ KHUYẾN NGHỊ BÀI TẬP LẬP TRÌNH CÁ NHÂN HÓA", { x: 0.6, y: 0.7, w: 8.8, h: 0.3,
    fontFace: B, fontSize: 12, bold: true, color: "8FD3CF", charSpacing: 2, margin: 0, isTextBox: true });
  s.addText("Tác tử chọn bài học từ dữ liệu thật —\nnó có thật sự “dạy”?", { x: 0.6, y: 1.15, w: 8.8, h: 1.6,
    fontFace: H, fontSize: 36, bold: true, color: C.white, margin: 0, isTextBox: true });
  s.addText("Mô hình nhận thức (DKT, cây định danh entropy) → MDP → DQN/PPO → đánh giá trên 9 thế giới mô phỏng, "
    + "trong đó có một thế giới không hề có học.", { x: 0.6, y: 2.95, w: 8.2, h: 0.8, fontFace: B, fontSize: 15,
    color: "D6DEEA", margin: 0, isTextBox: true });
  const stats = [[int(D.learners), "người học thật"], [int(D.submissions), "lượt nộp C/C++"], ["4/4", "giả thuyết xác nhận"]];
  stats.forEach(([v, l], i) => {
    s.addText(v, { x: 0.6 + i * 2.9, y: 4.05, w: 2.7, h: 0.55, fontFace: H, fontSize: 28, bold: true,
      color: i === 2 ? "8FD3CF" : C.white, margin: 0, isTextBox: true });
    s.addText(l, { x: 0.6 + i * 2.9, y: 4.6, w: 2.7, h: 0.3, fontFace: B, fontSize: 12, color: "9AA7BD", margin: 0,
      isTextBox: true });
  });
  s.addNotes("Mở đầu: đề 4 yêu cầu một tác tử chọn bài tập tiếp theo dựa trên mô hình nhận thức và học tăng cường. "
    + "Nhóm xây toàn bộ chuỗi trên dữ liệu thật và đặt câu hỏi phản biện: điểm số 'tiến bộ' mà các hệ KT+RL thường báo cáo có thật sự đo việc học không?");
}

// 2 — requirement ---------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Đề bài yêu cầu gì?", "Ba thành phần kỹ thuật và một mục tiêu sư phạm");
  const items = [
    ["1", "Mô hình hóa nhận thức", "DKT hoặc cây định danh rút gọn dựa trên entropy để chẩn đoán kỹ năng yếu/mạnh (mảng, con trỏ, vòng lặp…)."],
    ["2", "Khung quyết định MDP", "Trạng thái = mức hiểu; hành động = đề xuất một bài; phần thưởng = cải thiện điểm và thời gian giải."],
    ["3", "Học chính sách", "Huấn luyện tác tử bằng Q-learning (DQN) hoặc PPO."],
  ];
  items.forEach(([n, h, b], i) => {
    const x = 0.5 + i * 3.05;
    card(s, x, 1.45, 2.85, 2.55);
    badge(s, x + 0.25, 1.68, n);
    s.addText(h, { x: x + 0.25, y: 2.25, w: 2.4, h: 0.4, fontFace: H, fontSize: 16, bold: true, color: C.ink, margin: 0, isTextBox: true });
    s.addText(b, { x: x + 0.25, y: 2.7, w: 2.4, h: 1.2, fontFace: B, fontSize: 12.5, color: C.ink2, margin: 0, valign: "top", isTextBox: true });
  });
  card(s, 0.5, 4.25, 9, 0.75, C.tealSoft);
  s.addText([{ text: "Mục tiêu: ", options: { bold: true, color: C.teal } },
    { text: "chọn bài “vừa sức” — vùng phát triển gần nhất: quá khó thì nản, quá dễ thì chán.", options: { color: C.ink } }],
    { x: 0.75, y: 4.33, w: 8.5, h: 0.6, fontFace: B, fontSize: 14, valign: "middle", margin: 0, isTextBox: true });
  footer(s, 2);
  s.addNotes("Nhắc lại nguyên văn tinh thần đề 4 của thầy. Nhóm làm đủ cả ba: DKT và cây định danh entropy, MDP với phần thưởng gồm điểm và công sức, DQN và PPO.");
}

// 3 — why redo --------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Vì sao phải làm lại trên dữ liệu thật?", "Bản trước chỉ là mô phỏng do nhóm tự đặt tham số");
  card(s, 0.5, 1.45, 4.35, 3.3, C.coralSoft);
  s.addText("Trước (v1–v2)", { x: 0.8, y: 1.62, w: 3.9, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: C.coral, margin: 0, isTextBox: true });
  s.addText([
    { text: "Thế giới BKT 3 kỹ năng, 12 bài tự viết", options: { bullet: true, breakLine: true } },
    { text: "Tham số học/đoán/trượt do nhóm tự đặt", options: { bullet: true, breakLine: true } },
    { text: "Không có DKT, không có PPO", options: { bullet: true, breakLine: true } },
    { text: "Dữ liệu thật chỉ dùng cho dự báo, tách rời việc chọn bài", options: { bullet: true } }],
    { x: 0.8, y: 2.1, w: 3.85, h: 2.4, fontFace: B, fontSize: 13.5, color: C.ink, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
  card(s, 5.15, 1.45, 4.35, 3.3, C.tealSoft);
  s.addText("Nay (v3)", { x: 5.45, y: 1.62, w: 3.9, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: C.teal, margin: 0, isTextBox: true });
  s.addText([
    { text: `${int(D.learners)} người học thật, ${int(D.interactions)} lượt gặp bài đầu`, options: { bullet: true, breakLine: true } },
    { text: `${int(D.problems)} bài C; nhãn kỹ năng do giảng viên gán`, options: { bullet: true, breakLine: true } },
    { text: "6 mô hình người học + cây định danh; DQN và PPO", options: { bullet: true, breakLine: true } },
    { text: "Protocol và 4 giả thuyết khóa trước khi mở dữ liệu", options: { bullet: true } }],
    { x: 5.45, y: 2.1, w: 3.85, h: 2.4, fontFace: B, fontSize: 13.5, color: C.ink, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
  footer(s, 3);
  s.addNotes("Tự đánh giá thẳng thắn: bản cũ là đồ chơi vì mọi thứ quan trọng đều do nhóm tự đặt. Bản mới học từ log thật và khóa giả thuyết trước để tránh 'chọn kết quả đẹp'.");
}

// 4 — data ------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Dữ liệu: ACcoding, OJ lập trình C của Đại học Beihang", "Chỉ dùng người học chưa từng xuất hiện trong các nghiên cứu trước");
  const stats = [[int(D.learners), "người học (≥ 20 bài)"], [int(D.submissions), "lượt nộp C/C++"], [int(D.interactions), "lượt gặp bài đầu tiên"], [int(D.problems), "bài tập"]];
  stats.forEach(([v, l], i) => {
    const x = 0.5 + i * 2.28;
    card(s, x, 1.45, 2.08, 1.3);
    s.addText(v, { x: x + 0.15, y: 1.6, w: 1.8, h: 0.6, fontFace: H, fontSize: 24, bold: true, color: C.teal, margin: 0, isTextBox: true });
    s.addText(l, { x: x + 0.15, y: 2.2, w: 1.8, h: 0.4, fontFace: B, fontSize: 12, color: C.ink2, margin: 0, isTextBox: true });
  });
  const parts = [["A · 40%", "fit tracker DKT và thế giới huấn luyện", C.teal], ["B · 40%", "fit các thế giới đánh giá độc lập", C.ink2], ["T · 20%", `${int(D.test_learners)} người học kiểm tra`, C.coral]];
  parts.forEach(([h, b, col], i) => {
    const x = 0.5 + i * 3.05;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.05, w: 2.85, h: 1.05, rectRadius: 0.1, fill: { color: C.white }, line: { color: col, width: 1.5 } });
    s.addText(h, { x: x + 0.2, y: 3.13, w: 2.5, h: 0.4, fontFace: H, fontSize: 16, bold: true, color: col, margin: 0, isTextBox: true });
    s.addText(b, { x: x + 0.2, y: 3.52, w: 2.5, h: 0.5, fontFace: B, fontSize: 12, color: C.ink2, margin: 0, isTextBox: true });
  });
  s.addText("Nhãn = AC ở lần nộp đầu; công sức = số lần nộp tới khi AC. 96 nhãn kiến thức gom thành 15 nhóm kỹ năng (mảng, con trỏ, vòng lặp, xâu, đệ quy…).",
    { x: 0.5, y: 4.35, w: 9, h: 0.6, fontFace: B, fontSize: 12.5, color: C.muted, margin: 0, isTextBox: true });
  footer(s, 4);
  s.addNotes("Dữ liệu công khai (CC BY 4.0). Chia người học bằng hash cố định trước khi xem kết quả: A để huấn luyện, B để đánh giá độc lập, T để kiểm tra.");
}

// 5 — learner models ------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Mô hình nhận thức: sáu mô hình dự báo ngang nhau", `Dự báo lần nộp đầu của ${int(D.test_learners)} người học chưa thấy`);
  const names = { irt: "IRT (không học)", afm: "AFM", pfa: "PFA", sakt: "SAKT", dkt: "DKT (tracker)", dkt2: "DKT song sinh", id3: "Cây định danh ID3" };
  const rows = [[{ text: "Mô hình", options: { bold: true, color: C.white, fill: { color: C.ink } } },
    { text: "AUC", options: { bold: true, color: C.white, fill: { color: C.ink }, align: "right" } },
    { text: "NLL", options: { bold: true, color: C.white, fill: { color: C.ink }, align: "right" } }]];
  ["irt", "afm", "pfa", "sakt", "dkt", "dkt2", "id3"].forEach((k) => rows.push([
    { text: names[k], options: { bold: k === "dkt" } }, { text: nf(D.auc[k], 3), options: { align: "right" } },
    { text: nf(D.nll[k], 4), options: { align: "right" } }]));
  s.addTable(rows, { x: 0.5, y: 1.45, w: 4.6, colW: [2.4, 1.1, 1.1], fontFace: B, fontSize: 12, color: C.ink,
    border: { type: "solid", pt: 0.5, color: C.line }, rowH: 0.36 });
  card(s, 5.4, 1.45, 4.1, 1.35, C.tealSoft);
  const nlls = Object.entries(D.nll).filter(([k]) => k !== "id3").map(([, v]) => v);
  s.addText([{ text: `Chênh NLL ≤ ${nf(Math.max(...nlls) - Math.min(...nlls), 4)}`, options: { bold: true, color: C.teal, fontSize: 18, breakLine: true } },
    { text: "Chỉ nhìn độ chính xác dự báo thì không chọn được mô hình nào “đúng” để làm simulator.", options: { color: C.ink, fontSize: 12.5 } }],
    { x: 5.6, y: 1.55, w: 3.75, h: 1.15, fontFace: B, margin: 0, valign: "middle", isTextBox: true });
  card(s, 5.4, 3.0, 4.1, 1.95);
  const FEAT = { problem_success_rate: "tỷ lệ qua của bài", overall_success: "tỷ lệ đúng chung", primary_skill: "kỹ năng",
    skill_practice: "số bài đã luyện kỹ năng", released_difficulty: "độ khó", recent5_success: "đúng 5 bài gần nhất",
    skill_success: "tỷ lệ đúng ở kỹ năng" };
  const SK = { "Conditionals": "rẽ nhánh", "Sorting and searching": "sắp xếp/tìm kiếm", "Arithmetic and number theory": "số học",
    "Strings": "xâu", "Dynamic programming": "quy hoạch động", "Data structures": "cấu trúc dữ liệu", "Loops": "vòng lặp", "Arrays": "mảng" };
  const val = (v) => v.replace(">=", "≥ ").replace("<", "< ").replace(/(\d)\.(\d)/g, "$1,$2").replace("-", "–");
  const say = (r) => r.conditions.map((c) => { const [f, v] = c.split(" = "); return `${FEAT[f] || f} ${f === "primary_skill" ? "= " + (SK[v] || v) : val(v)}`; }).join(" VÀ ");
  const low = D.rules.filter((r) => r.p < 0.5 && r.conditions.length <= 3 && r.conditions.some((c) => Object.keys(SK).some((k) => c.endsWith(k))))[0];
  const high = D.rules.filter((r) => r.p > 0.5 && r.conditions.length <= 3).sort((a, b) => b.n - a.n)[0];
  s.addText([{ text: "Luật từ cây định danh (entropy, đã rút gọn)", options: { bold: true, color: C.ink, breakLine: true } },
    { text: `NẾU ${say(low)} THÌ P(đúng) ≈ ${nf(low.p, 2)} (n=${int(low.n)})`, options: { color: C.coral, fontSize: 11.5, breakLine: true } },
    { text: `NẾU ${say(high)} THÌ P(đúng) ≈ ${nf(high.p, 2)} (n=${int(high.n)})`, options: { color: C.teal, fontSize: 11.5 } }],
    { x: 5.6, y: 3.12, w: 3.75, h: 1.75, fontFace: B, fontSize: 12.5, margin: 0, valign: "top", paraSpaceAfter: 4, isTextBox: true });
  footer(s, 5);
  s.addNotes("DKT có đủ dữ liệu thì bắt kịp IRT/PFA; cây ID3 kém hơn chút nhưng giải thích được. Điểm then chốt: sáu mô hình dự báo gần như y hệt nhau.");
}

// 6 — MDP -------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Bài toán quyết định và các tác tử", "Mỗi episode: 10 bài, bắt đầu từ lịch sử thật của một người học");
  const boxes = [["Trạng thái", `Dự báo của DKT cho ${D.pool} bài + 10 kỹ năng + bài còn làm được + số bước còn lại`, C.teal],
    ["Hành động", `Chọn 1 trong ${D.pool} bài chưa gặp (ngân hàng theo quy tắc cố định từ A)`, C.ink2],
    ["Phần thưởng", `Δ bài kiểm tra sau (${D.post} bài) − 0,05 điểm × số lần nộp thêm`, C.coral]];
  boxes.forEach(([h, b, col], i) => {
    const x = 0.5 + i * 3.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.45, w: 2.8, h: 1.55, rectRadius: 0.12, fill: { color: C.white }, line: { color: col, width: 1.5 } });
    s.addText(h, { x: x + 0.2, y: 1.55, w: 2.4, h: 0.4, fontFace: H, fontSize: 16, bold: true, color: col, margin: 0, isTextBox: true });
    s.addText(b, { x: x + 0.2, y: 1.97, w: 2.45, h: 0.95, fontFace: B, fontSize: 11.5, color: C.ink2, margin: 0, valign: "top", isTextBox: true });
    if (i < 2) s.addText("→", { x: x + 2.8, y: 1.95, w: 0.3, h: 0.5, fontFace: B, fontSize: 20, color: C.muted, align: "center", margin: 0, isTextBox: true });
  });
  card(s, 0.5, 3.25, 4.4, 1.75, C.tealSoft);
  s.addText([{ text: "Tác tử học (3 seed mỗi loại)", options: { bold: true, color: C.teal, breakLine: true } },
    { text: "Double DQN và PPO, huấn luyện trong 3 điều kiện:", options: { breakLine: true } },
    { text: "thưởng từ DKT (cách phổ biến) · thế giới AFM · trộn nhiều thế giới", options: {} }],
    { x: 0.7, y: 3.35, w: 4.0, h: 1.55, fontFace: B, fontSize: 12.5, color: C.ink, margin: 0, valign: "top", isTextBox: true });
  card(s, 5.1, 3.25, 4.4, 1.75);
  s.addText([{ text: "8 quy tắc so sánh", options: { bold: true, color: C.ink, breakLine: true } },
    { text: "ngẫu nhiên · dễ→khó · kỹ năng yếu nhất · nhắm P(đúng)=0,5/0,7 · dễ nhất · khó nhất · tham lam theo DKT (như ExRec)", options: {} }],
    { x: 5.3, y: 3.35, w: 4.0, h: 1.55, fontFace: B, fontSize: 12.5, color: C.ink2, margin: 0, valign: "top", isTextBox: true });
  footer(s, 6);
  s.addNotes("Phần thưởng đúng như đề: cải thiện điểm (bài kiểm tra sau) và thời gian (đo bằng số lần nộp thêm). DQN là họ Q-learning, PPO là policy gradient.");
}

// 7 — evaluation design -----------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Đánh giá: 9 thế giới, trong đó có một “đối chứng âm”", "Thế giới sinh phản hồi khác với mô hình mà tác tử dùng để chấm điểm");
  const worlds = [["DKT-A", "thế giới huấn luyện", C.ink2], ["AFM-A", "thế giới huấn luyện", C.ink2], ["DKT-A song sinh", "cùng dữ liệu, khác seed", C.ink2],
    ["DKT-B", "người học khác", C.teal], ["SAKT-B", "kiến trúc khác", C.teal], ["AFM-B", "học theo số lần luyện", C.teal],
    ["PFA-B", "học theo đúng/sai", C.teal], ["ZPD-B", "giả định vùng phát triển", C.teal], ["IRT-B", "KHÔNG có học: tiến bộ thật = 0", C.coral]];
  worlds.forEach(([h, b, col], i) => {
    const x = 0.5 + (i % 3) * 3.05, y = 1.4 + Math.floor(i / 3) * 1.12;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.85, h: 0.95, rectRadius: 0.1, fill: { color: i === 8 ? C.coralSoft : C.white }, line: { color: col, width: 1.25 } });
    s.addText(h, { x: x + 0.18, y: y + 0.08, w: 2.5, h: 0.38, fontFace: H, fontSize: 15, bold: true, color: col, margin: 0, isTextBox: true });
    s.addText(b, { x: x + 0.18, y: y + 0.48, w: 2.5, h: 0.38, fontFace: B, fontSize: 11.5, color: C.ink2, margin: 0, isTextBox: true });
  });
  s.addText("Mọi chính sách chạy trên cùng " + int(D.episodes) + " episode bắt đầu từ người học kiểm tra; ghi cả tiến bộ theo thế giới và tiến bộ mà tracker DKT tự báo.",
    { x: 0.5, y: 4.85, w: 9, h: 0.35, fontFace: B, fontSize: 11.5, color: C.muted, margin: 0, isTextBox: true });
  footer(s, 7);
  s.addNotes("Ý tưởng then chốt: đối chứng âm như trong dịch tễ học. Ở IRT-B không ai học được gì, nên mọi 'tiến bộ' tracker báo ở đây đều là ảo.");
}

// 8 — H1 ------------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "H1: thắng lớn “tại nhà”, gần 0 ở thế giới độc lập", "Mức hơn chọn ngẫu nhiên (điểm phần trăm bài kiểm tra) — H1 được xác nhận");
  const labels = ["DKT-A (huấn luyện)", "DKT song sinh", "DKT-B", "SAKT-B", "AFM-B", "PFA-B", "ZPD-B"];
  s.addChart(pres.charts.BAR, [{ name: "DQN · thưởng DKT", labels, values: D.h1.dqn_kt }, { name: "PPO · thưởng DKT", labels, values: D.h1.ppo_kt }],
    chartBase({ x: 0.5, y: 1.35, w: 6.1, h: 3.75, barDir: "col", barGrouping: "clustered", chartColors: [C.ink2, C.coral],
      showLegend: true, legendPos: "b", legendFontSize: 10, title: "Hơn ngẫu nhiên (điểm %)", dataLabelPosition: "outEnd", catAxisLabelFontSize: 9 }));
  card(s, 6.85, 1.45, 2.65, 3.55, C.coralSoft);
  s.addText([{ text: sgn(D.h1.ppo_kt[0], 1), options: { fontFace: H, fontSize: 30, bold: true, color: C.coral, breakLine: true } },
    { text: "PPO trong simulator huấn luyện", options: { fontSize: 12, color: C.ink, breakLine: true } },
    { text: " ", options: { fontSize: 8, breakLine: true } },
    { text: sgn(Math.max(...D.h1.ppo_kt.slice(4)), 2), options: { fontFace: H, fontSize: 30, bold: true, color: C.teal, breakLine: true } },
    { text: "cao nhất ở AFM-B / PFA-B / ZPD-B", options: { fontSize: 12, color: C.ink } }],
    { x: 7.05, y: 1.6, w: 2.3, h: 3.25, fontFace: B, margin: 0, valign: "top", isTextBox: true });
  footer(s, 8);
  s.addNotes("Nếu chỉ đánh giá trong DKT-A như nhiều bài báo KT+RL, ta sẽ kết luận RL rất tốt. Chuyển sang thế giới có cấu trúc học rõ ràng, lợi thế gần như biến mất.");
}

// 9 — H2/H3 -----------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "H2–H3: “tiến bộ ảo” khi không hề có học", "Thế giới IRT-B: tiến bộ thật của mọi chính sách = 0 — H2 và H3 được xác nhận");
  const order = ["ppo_kt", "dqn_kt", "greedy_kt", "dqn_mix", "ppo_afm", "curriculum", "zpd70", "random", "zpd50"];
  const names = { ppo_kt: "PPO · thưởng DKT", dqn_kt: "DQN · thưởng DKT", greedy_kt: "Tham lam theo DKT", dqn_mix: "DQN · nhiều thế giới",
    ppo_afm: "PPO · thế giới AFM", curriculum: "Dễ → khó", zpd70: "Nhắm P=0,7", random: "Ngẫu nhiên", zpd50: "Nhắm P=0,5" };
  s.addChart(pres.charts.BAR, [{ name: "Tracker DKT tự báo", labels: order.map((p) => names[p]), values: order.map((p) => D.h2[p]) }],
    chartBase({ x: 0.5, y: 1.35, w: 5.9, h: 3.75, barDir: "bar", chartColors: [C.coral], showLegend: false,
      title: "Tiến bộ tracker báo cáo (điểm %)", dataLabelPosition: "outEnd", catAxisOrientation: "maxMin" }));
  card(s, 6.65, 1.45, 2.85, 1.6, C.gray);
  s.addText([{ text: "Tiến bộ thật: 0,00", options: { bold: true, color: C.ink, fontSize: 16, breakLine: true } },
    { text: "Thế giới không có tham số học — theo định nghĩa không ai tiến bộ.", options: { fontSize: 12, color: C.ink2 } }],
    { x: 6.85, y: 1.55, w: 2.5, h: 1.4, fontFace: B, margin: 0, valign: "top", isTextBox: true });
  card(s, 6.65, 3.25, 2.85, 1.75, C.coralSoft);
  s.addText([{ text: `ρ = ${nf(D.h3, 2)}`, options: { fontFace: H, bold: true, color: C.coral, fontSize: 28, breakLine: true } },
    { text: "tương quan hạng giữa tiến bộ “tại nhà” và tiến bộ ảo trên 14 chính sách", options: { fontSize: 12, color: C.ink } }],
    { x: 6.85, y: 3.35, w: 2.5, h: 1.55, fontFace: B, margin: 0, valign: "top", isTextBox: true });
  footer(s, 9);
  s.addNotes("Đây là phát hiện trung tâm: thứ hạng đánh giá trong simulator gần như chính là thứ hạng 'tiến bộ ảo'. Chính sách càng giỏi tối ưu tracker thì càng được tracker khen, dù không dạy gì.");
}

// 10 — mechanism ------------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Vì sao? DKT “tin” vào mức học rất khác nhau", "Độ trôi = thay đổi dự báo mà chính mô hình kỳ vọng sau một lần luyện — H4 được xác nhận");
  const models = [["DKT (tracker)", "dkt_A"], ["DKT song sinh", "dkt2_A"], ["SAKT", "sakt_A"], ["AFM", "afm_A"], ["PFA", "pfa_A"], ["IRT", "irt_A"]];
  s.addChart(pres.charts.BAR, [{ name: "Độ lệch chuẩn độ trôi", labels: models.map((m) => m[0]), values: models.map((m) => D.drift_sd[m[1]]) }],
    chartBase({ x: 0.5, y: 1.35, w: 5.4, h: 3.7, barDir: "col", chartColors: [C.ink2], showLegend: false,
      title: "Độ phân tán “học ngầm định” mỗi bài (điểm %)", dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00" }));
  const facts = [[`Tracker báo = trôi + bất ngờ`, "Mô hình không-học đúng nghĩa (IRT) có độ trôi bằng 0 tuyệt đối — kiểm chứng bằng toán và bằng test."],
    [`Hai DKT khác seed: ρ = ${nf(D.twin, 2)}`, "Dự báo ngang nhau nhưng bất đồng về việc bài nào “dạy”."],
    [`Quỹ đạo thật: |Δ| ${nf(D.continuation.tracker_gain, 1)} so với ${nf(D.continuation.claimed_irt_A, 1)} (IRT)`, "Trên chuỗi thật độ trôi tự triệt tiêu; RL tìm chuỗi “lạ” để cộng dồn nó."]];
  facts.forEach(([h, b], i) => {
    card(s, 6.15, 1.35 + i * 1.25, 3.35, 1.12, i === 0 ? C.tealSoft : C.gray);
    s.addText([{ text: h, options: { bold: true, color: C.ink, breakLine: true } }, { text: b, options: { color: C.ink2, fontSize: 11 } }],
      { x: 6.3, y: 1.42 + i * 1.25, w: 3.05, h: 1.0, fontFace: B, fontSize: 12.5, margin: 0, valign: "top", isTextBox: true });
  });
  footer(s, 10);
  s.addNotes("Công cụ chẩn đoán mới: tách tiến bộ tracker báo thành độ trôi (niềm tin nội tại của mô hình) và phần bằng chứng. Với IRT, độ trôi bằng 0 theo định luật xác suất toàn phần.");
}

// 11 — what works ----------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Điều vẫn hiệu quả: RL học trong thế giới AFM", "Mức hơn ngẫu nhiên ở ba thế giới có trạng thái ẩn (điểm %) — mô phỏng");
  const pols = [["dqn_afm", "DQN · AFM", C.teal], ["ppo_afm", "PPO · AFM", "4FB3AF"], ["zpd70", "Nhắm P=0,7", C.ink2], ["dqn_kt", "DQN · thưởng DKT", "F2A28C"], ["ppo_kt", "PPO · thưởng DKT", C.coral], ["curriculum", "Dễ → khó", "9CA3AF"]];
  const labels = ["AFM-B", "PFA-B", "ZPD-B"];
  s.addChart(pres.charts.BAR, pols.map(([k, n]) => ({ name: n, labels, values: D.latent_adv[k] })),
    chartBase({ x: 0.5, y: 1.35, w: 6.2, h: 3.75, barDir: "col", barGrouping: "clustered", chartColors: pols.map((p) => p[2]),
      showLegend: true, legendPos: "b", legendFontSize: 9, title: "Hơn ngẫu nhiên (điểm %)", showValue: false }));
  card(s, 6.95, 1.45, 2.55, 3.55, C.tealSoft);
  s.addText([{ text: sgn(D.worst_case.dqn_afm, 2), options: { fontFace: H, fontSize: 28, bold: true, color: C.teal, breakLine: true } },
    { text: "trường hợp xấu nhất của DQN-AFM (tốt nhất mọi chính sách)", options: { fontSize: 11.5, color: C.ink, breakLine: true } },
    { text: " ", options: { fontSize: 8, breakLine: true } },
    { text: `${nf(D.extra_afmB.dqn_afm, 1)} so với ${nf(D.extra_afmB.random, 1)}`, options: { fontFace: H, fontSize: 22, bold: true, color: C.ink, breakLine: true } },
    { text: "lần nộp thêm / 10 bài (so với ngẫu nhiên)", options: { fontSize: 11.5, color: C.ink } }],
    { x: 7.1, y: 1.6, w: 2.25, h: 3.3, fontFace: B, margin: 0, valign: "top", isTextBox: true });
  footer(s, 11);
  s.addNotes("RL không vô dụng: khi thế giới huấn luyện có cấu trúc học rõ ràng, tác tử học được chính sách bền và tiết kiệm công sức. Lộ trình dễ→khó ('quá dễ') luôn kém nhất.");
}

// 12 — app demo ---------------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Demo ứng dụng: http://127.0.0.1:8773/#realdata", "Mô hình đã khóa và kiểm tra hash; học viên thật được ẩn danh");
  s.addImage({ path: path.join(__dirname, "app_simulation.png"), x: 0.5, y: 1.35, w: 5.9, h: 3.32 });
  const steps = ["Chọn học viên L001–L060, xem chẩn đoán 10 kỹ năng", "Xem 14 chính sách chọn bài nào và vì sao", "Bấm ô kết quả để giả định đúng/sai → quyết định đổi",
    "Chạy 10 bước ở IRT-B: thật 0,00 · DKT tự báo lớn"];
  steps.forEach((t, i) => {
    badge(s, 6.7, 1.4 + i * 0.85, String(i + 1), i === 3 ? C.coral : C.teal);
    s.addText(t, { x: 7.3, y: 1.35 + i * 0.85, w: 2.2, h: 0.6, fontFace: B, fontSize: 11.5, color: C.ink, margin: 0, valign: "middle", isTextBox: true });
  });
  footer(s, 12);
  s.addNotes("Demo trực tiếp: mở trang Nghiên cứu → Dữ liệu thật · v3. Trước buổi báo cáo chạy app/check_demo.cmd để kiểm tra.");
}

// 13 — conclusions (dark) ----------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.ink };
  s.addText("Kết luận và khuyến nghị", { x: 0.6, y: 0.45, w: 8.8, h: 0.6, fontFace: H, fontSize: 28, bold: true, color: C.white, margin: 0, isTextBox: true });
  const recs = [["Đối chứng âm", "Luôn đánh giá chính sách trong một thế giới không có học; mọi tiến bộ ở đó là ảo."],
    ["Tách độ trôi", "Báo cáo tiến bộ tracker = độ trôi + bất ngờ; độ trôi lớn là dấu hiệu bị khai thác."],
    ["Thế giới độc lập", "Đánh giá trên thế giới fit từ người học khác và có cấu trúc học tường minh."],
    ["Fit lại khác seed", "Hai mô hình dự báo ngang nhau có thể bất đồng về việc bài nào “dạy”."]];
  recs.forEach(([h, b], i) => {
    const x = 0.6 + (i % 2) * 4.45, y = 1.35 + Math.floor(i / 2) * 1.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 4.2, h: 1.4, rectRadius: 0.12, fill: { color: "1D2E4F" }, line: { color: "2C3F63" } });
    badge(s, x + 0.2, y + 0.2, String(i + 1), i === 0 ? C.coral : C.teal);
    s.addText(h, { x: x + 0.8, y: y + 0.18, w: 3.2, h: 0.45, fontFace: H, fontSize: 17, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText(b, { x: x + 0.8, y: y + 0.65, w: 3.25, h: 0.7, fontFace: B, fontSize: 12, color: "C9D3E3", margin: 0, valign: "top", isTextBox: true });
  });
  s.addText("Mọi tiến bộ của chính sách là mô phỏng; chưa có thử nghiệm với sinh viên thật.", { x: 0.6, y: 4.75, w: 8.8, h: 0.35,
    fontFace: B, fontSize: 12, italic: true, color: "8FD3CF", margin: 0, isTextBox: true });
  footer(s, 13, true);
  s.addNotes("Thông điệp: đừng tin con số tiến bộ trong simulator KT khi chưa qua bốn kiểm tra này. Tác tử học trong thế giới có cấu trúc học rõ ràng là lựa chọn bền nhất.");
}

// 14 — limits and next -----------------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Giới hạn và bước tiếp theo", "Trình bày đúng mức bằng chứng");
  card(s, 0.5, 1.4, 4.35, 3.55, C.gray);
  s.addText("Giới hạn", { x: 0.75, y: 1.55, w: 3.9, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: C.ink, margin: 0, isTextBox: true });
  s.addText([{ text: "Một nền tảng (ACcoding) và một họ môn học", options: { bullet: true, breakLine: true } },
    { text: "Tiến bộ chính sách là mô phỏng; thế giới ZPD là giả định", options: { bullet: true, breakLine: true } },
    { text: "Con trỏ chỉ có 1 bài luyện (dữ liệu thưa)", options: { bullet: true, breakLine: true } },
    { text: "Công sức đo bằng số lần nộp, không phải thời gian", options: { bullet: true } }],
    { x: 0.75, y: 2.0, w: 3.9, h: 2.8, fontFace: B, fontSize: 13, color: C.ink2, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
  card(s, 5.15, 1.4, 4.35, 3.55, C.tealSoft);
  s.addText("Tiếp theo", { x: 5.4, y: 1.55, w: 3.9, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: C.teal, margin: 0, isTextBox: true });
  s.addText([{ text: "Lặp lại trên bộ dữ liệu thứ hai (CodeBench, Python)", options: { bullet: true, breakLine: true } },
    { text: "Thử nghiệm có đối chứng với sinh viên thật", options: { bullet: true, breakLine: true } },
    { text: "Huấn luyện tác tử bi quan theo bất đồng giữa các simulator", options: { bullet: true, breakLine: true } },
    { text: "Hoàn thiện bản thảo gửi tạp chí (C&E: AI / IJAIED)", options: { bullet: true } }],
    { x: 5.4, y: 2.0, w: 3.9, h: 2.8, fontFace: B, fontSize: 13, color: C.ink2, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
  footer(s, 14);
  s.addNotes("Nói rõ những gì chưa chứng minh được. Đây là điểm mạnh của nghiên cứu, không phải điểm yếu.");
}

// 15 — references ---------------------------------------------------------------------------------------------------------------------------
{
  const s = pres.addSlide();
  title(s, "Tài liệu chính", "Danh mục đầy đủ trong paper/v3/references.bib (đã kiểm tra DOI)");
  const refs = ["Chen et al. (2024). ACcoding: A graph-based dataset for online judge programming. Scientific Data 11, 548.",
    "Piech et al. (2015). Deep Knowledge Tracing. NeurIPS 28.", "Pandey & Karypis (2019). A Self-Attentive Model for Knowledge Tracing. EDM.",
    "Doroudi, Aleven & Brunskill (2017). Robust Evaluation Matrix. L@S.", "Doroudi, Aleven & Brunskill (2019). Where's the Reward? IJAIED 29(4).",
    "Ozyurt et al. (2025). ExRec: Personalized Exercise Recommendation with Semantically-Grounded KT. NeurIPS 38.",
    "Lipsitch et al. (2010). Negative Controls. Epidemiology 21(3).", "D'Amour et al. (2022). Underspecification. JMLR 23(226)."];
  s.addText(refs.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < refs.length - 1 } })),
    { x: 0.5, y: 1.35, w: 9, h: 3.4, fontFace: B, fontSize: 12.5, color: C.ink2, paraSpaceAfter: 5, valign: "top", margin: 0, isTextBox: true });
  s.addText("Cảm ơn thầy và các bạn đã lắng nghe!", { x: 0.5, y: 4.8, w: 9, h: 0.4, fontFace: H, fontSize: 18, bold: true, color: C.teal, margin: 0, isTextBox: true });
  footer(s, 15);
  s.addNotes("Cảm ơn và mời câu hỏi.");
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
pres.writeFile({ fileName: OUT }).then((f) => console.log("Wrote " + f));
