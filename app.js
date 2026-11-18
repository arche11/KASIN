const rupiah = value => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value);
const icons = { masuk: '#i-arrow-down', keluar: '#i-arrow-up' };
const motivationWords = [
  'Mulai saja, lalu terus bertumbuh.', 'Tekun hari ini, kuat esok hari.', 'Berani mencoba, berani berkembang.',
  'Jujur melangkah, hebat dalam berkarya.', 'Ide sederhana bisa jadi luar biasa.', 'Disiplin kecil membawa hasil besar.',
  'Peduli membuat kelas terasa berarti.', 'Fokus pada tujuan, nikmati prosesnya.', 'Percaya diri, peluang akan mengikuti.',
  'Mandiri melangkah, tetap terbuka belajar.', 'Teliti bekerja, hasilnya lebih bermakna.', 'Gigih berusaha sampai berhasil.',
  'Santun bersikap, luas wawasan.', 'Sigap bertindak, siap hadapi tantangan.', 'Terus berinovasi, ciptakan hal berguna.',
  'Cermat memilih, mantap melangkah.', 'Kompak bersama, hebat berkarya.', 'Tulus membantu, tumbuh bersama.',
  'Cerdas berpikir, rendah hati bertindak.', 'Adaptif berubah, teguh pada tujuan.', 'Temukan solusi di setiap tantangan.',
  'Aktif bertanya, cepat bertumbuh.', 'Sebarkan energi positif di sekitar.', 'Hasil baik lahir dari kebiasaan baik.',
  'Konsisten lebih kuat daripada sesekali hebat.', 'Setiap proses membawamu lebih dekat.', 'Bersyukur, lalu terus berusaha.',
  'Sabar berproses, jangan berhenti berharap.', 'Rajin berlatih, makin terampil.', 'Latihan hari ini, percaya diri esok.',
  'Kolaborasi membuka banyak kemungkinan.', 'Berani bermimpi, tekun mewujudkannya.', 'Jaga keseimbangan, tetap melangkah.',
  'Peka melihat, ringan membantu.', 'Luwes berpikir, tangguh bertindak.', 'Apresiasi proses, rayakan kemajuan.',
  'Berdaya untuk diri, bermanfaat bagi sekitar.', 'Jaga integritas dalam setiap pilihan.',
  'Semangat belajar, berani jadi lebih baik.', 'Kerja keras membuat kesempatan berarti.',
  'Terus berkarya, tinggalkan kebaikan.'
];
const studentNames = [
  'Nama siswa 01', 'Nama siswa 02', 'Nama siswa 03', 'Nama siswa 04', 'Nama siswa 05',
  'Nama siswa 06', 'Nama siswa 07', 'Nama siswa 08', 'Nama siswa 09', 'Nama siswa 10',
  'Nama siswa 11', 'Nama siswa 12', 'Nama siswa 13', 'Nama siswa 14', 'Nama siswa 15',
  'Nama siswa 16', 'Nama siswa 17', 'Nama siswa 18', 'Nama siswa 19', 'Nama siswa 20',
  'Nama siswa 21', 'Nama siswa 22', 'Nama siswa 23', 'Nama siswa 24', 'Nama siswa 25',
  'Nama siswa 26', 'Nama siswa 27', 'Nama siswa 28', 'Nama siswa 29', 'Nama siswa 30',
  'Nama siswa 31', 'Nama siswa 32', 'Nama siswa 33', 'Nama siswa 34', 'Nama siswa 35',
  'Nama siswa 36', 'Nama siswa 37', 'Nama siswa 38', 'Nama siswa 39', 'Nama siswa 40',
  'Nama siswa 41',
];
const students = motivationWords.map((word, index) => ({
  id: String(index + 1).padStart(2, '0'),
  name: studentNames[index] || `Siswa ${String(index + 1).padStart(2, '0')}`,
  word,
}));
const state = { rows: [], kind: 'masuk', month: '', session: null, authMode: 'login' };
const $ = selector => document.querySelector(selector);
const today = new Date();
$('#today-label').textContent = new Intl.DateTimeFormat('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(today);

function dateLabel(iso) {
  return new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${iso}T00:00:00`));
}
function safe(value) {
  const node = document.createElement('span'); node.textContent = value ?? ''; return node.innerHTML;
}
function renderStudents() {
  $('#student-grid').innerHTML = students.map(student => `<article class="student-card"><div class="student-photo"><span class="student-photo-placeholder"><svg><use href="#i-users"></use></svg><small>${student.id}</small></span><img src="/students/${student.id}.jpg" alt="Foto ${safe(student.name)}" loading="lazy" onerror="this.remove()"><span class="student-index">${student.id}</span></div><div class="student-card-info"><strong class="student-name">${safe(student.name)}</strong><span class="motivation-phrase">${safe(student.word)}</span></div></article>`).join('');
}
async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.session?.access_token) headers.set('Authorization', `Bearer ${state.session.access_token}`);
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401 && state.session) {
    state.session = null; sessionStorage.removeItem('kasin.session'); showAuth('Sesi Anda berakhir. Silakan masuk kembali.');
  }
  return response;
}
function showAuth(message = '') {
  $('#auth-screen').hidden = false; $('#app-shell').hidden = true; $('#auth-message').textContent = message;
}
async function startSession(session) {
  state.session = session; sessionStorage.setItem('kasin.session', JSON.stringify(session));
  setView('beranda');
  const user = session.user || {}; const role = user.app_metadata?.role || 'siswa';
  const name = user.user_metadata?.full_name || user.user_metadata?.name || user.email || 'Pengguna KASIN';
  $('#user-name').textContent = name; $('#user-role').textContent = role === 'bendahara' ? 'Bendahara' : 'Siswa';
  $('#user-avatar').textContent = name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase();
  const isBendahara = role === 'bendahara';
  $('#add-transaction').hidden = !isBendahara; $('#empty-add').hidden = !isBendahara;
  $('#auth-screen').hidden = true; $('#app-shell').hidden = false;
  try { await refresh(); }
  catch (error) { toast(error.message || 'Data kas belum bisa dimuat'); }
}
function setAuthMode(mode) {
  state.authMode = mode;
  const registering = mode === 'register';
  $('#auth-title').textContent = registering ? 'Buat akun KASIN' : 'Masuk ke akun';
  $('#auth-description').textContent = registering ? 'Buat akun siswa atau bendahara untuk kelas 10 PPLG 1.' : 'Gunakan email dan kata sandi untuk membuka buku kas kelas.';
  $('#auth-name-wrap').hidden = !registering; $('#auth-role-wrap').hidden = !registering;
  $('#auth-invite-wrap').hidden = !registering || $('#auth-form').elements.role.value !== 'bendahara';
  $('#auth-form').elements.name.required = registering;
  $('#auth-form').elements.password.autocomplete = registering ? 'new-password' : 'current-password';
  $('#auth-submit').textContent = registering ? 'Buat akun' : 'Masuk';
  $('#auth-switch-text').textContent = registering ? 'Sudah punya akun?' : 'Belum punya akun?';
  $('#auth-switch').textContent = registering ? 'Masuk' : 'Buat akun';
  $('#auth-message').textContent = '';
}
async function refresh() {
  const query = state.month ? `?bulan=${encodeURIComponent(state.month)}` : '';
  const [summaryResponse, rowsResponse] = await Promise.all([apiFetch('/api/summary'), apiFetch(`/api/transactions${query}`)]);
  const summary = await summaryResponse.json();
  if (!summaryResponse.ok) throw new Error(summary.error || 'Ringkasan kas belum bisa dimuat.');
  const rows = await rowsResponse.json();
  if (!rowsResponse.ok) throw new Error(rows.error || 'Daftar transaksi belum bisa dimuat.');
  state.rows = rows;
  $('#balance').textContent = rupiah(summary.saldo);
  $('#income').textContent = rupiah(summary.masuk.total);
  $('#expense').textContent = rupiah(summary.keluar.total);
  $('#income-count').textContent = summary.masuk.count;
  $('#expense-count').textContent = summary.keluar.count;
  renderRows();
}
function renderRows() {
  const needle = $('#search').value.trim().toLocaleLowerCase('id-ID');
  const filtered = state.rows.filter(row => [row.description, row.person, row.category].join(' ').toLocaleLowerCase('id-ID').includes(needle));
  $('#total-count').textContent = state.rows.length;
  $('#shown-count').textContent = filtered.length;
  $('#empty-state').hidden = filtered.length > 0;
  $('#transaction-list').innerHTML = filtered.map(row => `<tr>
    <td><div class="transaction-cell"><span class="transaction-icon ${row.kind}"><svg><use href="${icons[row.kind]}"></use></svg></span><span><span class="transaction-title">${safe(row.description)}</span><span class="transaction-sub">${row.kind === 'masuk' ? 'Dana diterima' : 'Dana digunakan'}</span></span></div></td>
    <td><span class="category-pill">${safe(row.category)}</span></td><td class="date-cell">${dateLabel(row.happened_on)}</td><td class="person-cell">${safe(row.person || '—')}</td>
    <td class="amount-cell ${row.kind}">${row.kind === 'masuk' ? '+' : '−'} ${rupiah(row.amount)}</td></tr>`).join('');
}
function toast(message) { const el = $('#toast'); el.querySelector('span').textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2600); }
function setView(view) {
  const titles = { beranda: 'Ringkasan', transaksi: 'Transaksi', tentang: 'Tentang kelas' };
  state.view = titles[view] ? view : 'beranda';
  const dashboard = state.view === 'beranda'; const transactions = state.view === 'transaksi';
  $('.welcome-row').hidden = !dashboard; $('.summary-grid').hidden = !dashboard;
  $('#transactions-intro').hidden = !transactions; $('#transaksi').hidden = state.view === 'tentang';
  $('#tentang').hidden = state.view !== 'tentang';
  $('#current-page').textContent = titles[state.view];
  $('#transaksi h2').textContent = transactions ? 'Semua transaksi' : 'Transaksi terbaru';
  document.querySelectorAll('.nav-link').forEach(link => {
    const active = link.dataset.view === state.view;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
  history.replaceState(null, '', `#${state.view}`);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

$('#auth-switch').addEventListener('click', () => setAuthMode(state.authMode === 'login' ? 'register' : 'login'));
$('#auth-form').elements.role.addEventListener('change', () => {
  $('#auth-invite-wrap').hidden = state.authMode !== 'register' || $('#auth-form').elements.role.value !== 'bendahara';
});
$('#auth-form').addEventListener('submit', async event => {
  event.preventDefault();
  const formElement = event.currentTarget; const form = Object.fromEntries(new FormData(formElement).entries());
  const registering = state.authMode === 'register'; const button = $('#auth-submit'); button.disabled = true; $('#auth-message').textContent = '';
  try {
    const response = await fetch(registering ? '/api/register' : '/api/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Akun belum bisa diproses.');
    formElement.reset(); setAuthMode('login'); await startSession(result);
  } catch (error) { $('#auth-message').textContent = error.message; }
  finally { button.disabled = false; }
});
$('#logout-button').addEventListener('click', () => {
  state.session = null; state.rows = []; sessionStorage.removeItem('kasin.session'); showAuth('Anda sudah keluar dari KASIN.');
});
document.querySelectorAll('.nav-link').forEach(link => link.addEventListener('click', event => {
  event.preventDefault(); setView(link.dataset.view);
}));

function openModal() { $('#modal').hidden = false; document.body.style.overflow = 'hidden'; $('#transaction-form').elements.description.focus(); }
function closeModal() { $('#modal').hidden = true; document.body.style.overflow = ''; $('#form-error').textContent = ''; }
$('#add-transaction').addEventListener('click', openModal);
$('#empty-add').addEventListener('click', openModal);
$('#close-modal').addEventListener('click', closeModal);
$('#cancel-modal').addEventListener('click', closeModal);
$('#modal').addEventListener('click', event => { if (event.target === $('#modal')) closeModal(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape' && !$('#modal').hidden) closeModal(); });
document.querySelectorAll('.type-option').forEach(button => button.addEventListener('click', () => {
  state.kind = button.dataset.kind;
  document.querySelectorAll('.type-option').forEach(option => option.classList.toggle('selected', option === button));
}));
$('#search').addEventListener('input', renderRows);
$('#month-filter').addEventListener('change', async event => { state.month = event.target.value; await refresh(); });
$('#transaction-form').addEventListener('submit', async event => {
  event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); const button = $('#save-button'); button.disabled = true;
  const payload = Object.fromEntries(form.entries()); payload.kind = state.kind; payload.amount = Number(payload.amount);
  try {
    const response = await apiFetch('/api/transactions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Transaksi gagal disimpan.');
    formElement.reset(); formElement.elements.happened_on.value = today.toISOString().slice(0, 10); closeModal(); await refresh(); toast('Transaksi berhasil disimpan');
  } catch (error) { $('#form-error').textContent = error.message; }
  finally { button.disabled = false; }
});
$('#download-csv').addEventListener('click', () => {
  const columns = ['Tanggal', 'Jenis', 'Keterangan', 'Kategori', 'Nama', 'Nominal'];
  const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  const rows = state.rows.map(r => [r.happened_on, r.kind === 'masuk' ? 'Pemasukan' : 'Pengeluaran', r.description, r.category, r.person, r.amount]);
  const csv = '\uFEFF' + [columns, ...rows].map(row => row.map(quote).join(',')).join('\r\n');
  const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' })); link.download = `kasin-${today.toISOString().slice(0, 10)}.csv`; link.click(); URL.revokeObjectURL(link.href);
});
$('#transaction-form').elements.happened_on.value = today.toISOString().slice(0, 10);
renderStudents();
try {
  const saved = sessionStorage.getItem('kasin.session');
  if (saved) { setView('beranda'); startSession(JSON.parse(saved)); } else showAuth();
} catch { sessionStorage.removeItem('kasin.session'); showAuth(); }
