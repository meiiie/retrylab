import { $, esc, download } from './shared.js';
import { catalog, exercises } from './curriculum.js';
import { recommendation, projectHistory } from './adaptive.js';
import { loadPractice } from './practice-store.js';

let bound = false, events = [], personal = true, latest, summary, generation = 0;
const pct = value => `${(value*100).toFixed(1)}%`;
const names = {random:'Chọn ngẫu nhiên',curriculum:'Thứ tự độ khó',weakest:'Kỹ năng yếu nhất',zpd:'Dự báo gần 70%',
  ddqn_naive:'Double DQN · bỏ qua độ quen bài',ddqn_aware:'Double DQN · xét độ quen bài',ddqn_success:'Double DQN · thưởng khi làm đúng'};
const worlds = {nominal:'Giống cơ chế huấn luyện',repair_only:'Chỉ nhớ bài cũ · không học thêm',slow_transfer:'Học chậm hơn',forgetting:'Quên nhanh hơn',prerequisites:'Có kỹ năng tiên quyết'};

function syntheticRecords() {
  const records = {};
  events.forEach((event,index) => {
    const record = records[event.exercise_id] ||= {attempts: [], completed: false};
    record.attempts.push({at:new Date(Date.UTC(2026,8,26,0,0,index)).toISOString(),source:`lab-observation-${index}`,
      status:event.outcome ? 'passed' : 'failed',passed:event.outcome ? 8 : 0,total:8});
    record.completed ||= Boolean(event.outcome);
  });
  return records;
}

async function render() {
  const ownGeneration = ++generation;
  const records = personal ? loadPractice().records : syntheticRecords();
  const decision = await recommendation(records);
  if (ownGeneration !== generation) return;
  latest = decision;
  $('policy-history-note').textContent = personal
    ? `${decision.observations} quan sát từ nhật ký cá nhân; ${decision.ignored} lần chạy không dùng (mã trùng, lỗi chạy hoặc dữ liệu thiếu).`
    : 'Lịch sử giả định để trình diễn. Không phải kết quả của một sinh viên thực.';
  $('policy-selected').textContent = decision.exercise?.title || 'Đã hoàn thành bộ bài';
  $('policy-reason').textContent = decision.reason || decision.fallback;
  $('policy-decision-mode').textContent = decision.note;
  $('policy-open-exercise').hidden = !decision.exercise;
  $('policy-open-exercise').href = decision.exercise ? `#exercise/${decision.exercise.id}` : '#learn';
  $('policy-skills').innerHTML = catalog.skills.map((skill,k) => `<div class="skill-summary"><span>${esc(skill.title)}</span><strong>${decision.state ? pct(decision.state.beliefs[k]) : '—'}</strong><small>${decision.cold_start ? 'Giá trị khởi tạo · chưa cá nhân hóa' : 'Ước lượng trong mô hình'}</small></div>`).join('');
  $('policy-trace').innerHTML = decision.trace?.length ? decision.trace.map((step,index) => {
    const exercise = exercises.find(e => e.id === step.exercise_id), k = exercise.skill;
    return `<tr><td>${index+1}</td><td>${esc(exercise.title)}</td><td>${step.outcome ? 'Qua hết test' : 'Chưa qua'}</td><td>${pct(step.predicted_success)}</td><td>${pct(step.before[k])} → ${pct(step.after[k])}</td></tr>`;
  }).join('') : '<tr><td colspan="5">Chưa có kết quả. Dự báo hiện dựa trên giá trị khởi tạo từ mô phỏng.</td></tr>';
  $('policy-candidates').innerHTML = (decision.candidates || []).slice().sort((a,b)=>b.q-a.q).map(row =>
    `<tr class="${row.exercise.id === decision.exercise?.id ? 'selected' : ''}"><td>${esc(row.exercise.title)}</td><td>${row.q.toFixed(4)}</td><td>${pct(row.predicted_success)}</td><td>${row.eligible ? 'Có' : 'Đã đạt / đủ lượt thử'}</td></tr>`).join('');
  $('policy-version').textContent = `${decision.model_version || 'Chưa tải mô hình'} · ${decision.fallback || 'Huấn luyện mô phỏng, không cập nhật trọng số khi bạn nộp bài.'}`;
  $('policy-undo').disabled = !events.length;
}

function renderResults() {
  const world = $('policy-world').value;
  $('policy-results').innerHTML = summary.rows.filter(row => row.world === world).map(row =>
    `<tr><td>${names[row.policy]}</td><td>${(100*row.probe_gain.mean).toFixed(2)} đpt</td><td>[${row.probe_gain.ci95.map(x=>(100*x).toFixed(2)).join('; ')}]</td><td>${pct(row.practice_success.mean)}</td></tr>`).join('');
  const contrast = summary.contrasts.find(row => row.world === world && row.right === 'weakest');
  $('policy-result-note').textContent = world === 'repair_only'
    ? 'Không có học mới trong môi trường này: mọi chính sách có tiến bộ chuyển giao bằng 0, dù vẫn làm đúng nhiều bài đã luyện.'
    : `Double DQN xét độ quen bài so với quy tắc kỹ năng yếu nhất: ${(100*contrast.mean).toFixed(2)} điểm phần trăm; CI [${contrast.ci95.map(x=>(100*x).toFixed(2)).join('; ')}]. Phải đọc cả chiều âm và khoảng bất định.`;
}

function add(outcome) {
  if (personal) events = projectHistory(loadPractice().records).events.map(({exercise_id,outcome})=>({exercise_id,outcome}));
  personal = false;
  $('policy-scenario').value = 'custom';
  events.push({exercise_id:$('policy-item').value,outcome});
  render();
}

export async function showPolicyLab() {
  if (!bound) {
    $('policy-item').innerHTML = exercises.map(e=>`<option value="${e.id}">${esc(e.title)}</option>`).join('');
    $('policy-item').value = 'fibonacci';
    $('policy-scenario').addEventListener('change', () => {
      const scenario = $('policy-scenario').value;
      personal = scenario === 'personal';
      events = scenario === 'first-pass' ? [{exercise_id:'fibonacci',outcome:1}]
        : scenario === 'repair' ? [0,0,1].map(outcome=>({exercise_id:'fibonacci',outcome}))
        : scenario === 'transfer' ? [{exercise_id:'prefix-sums',outcome:1},{exercise_id:'fibonacci',outcome:1}] : [];
      render();
    });
    $('policy-add-fail').addEventListener('click',()=>add(0));
    $('policy-add-pass').addEventListener('click',()=>add(1));
    $('policy-undo').addEventListener('click',()=>{if (personal) return; events.pop(); render();});
    $('policy-world').addEventListener('change',renderResults);
    $('export-policy-trace').addEventListener('click',()=>download('RetryLab-quyet-dinh.json',{
      source:personal ? 'personal-browser-practice' : 'hypothetical-demo',
      exported_at:new Date().toISOString(),...latest,
      note:'Filter and policy trained only on synthetic responses. No human efficacy evidence. Q is not a probability.'}));
    bound = true;
  }
  await render();
  if (!summary) {
    const response = await fetch('/static/data/policy-results-v2.json');
    if (!response.ok) throw new Error('Chưa tải được kết quả thực nghiệm chính sách.');
    summary = await response.json();
    $('policy-world').innerHTML = Object.entries(worlds).map(([id,name])=>`<option value="${id}">${name}</option>`).join('');
  }
  renderResults();
}
