# KASIN

Buku kas digital kelas 10 PPLG 1, SMKN 1 CIOMAS. Website berbahasa Indonesia dengan ikon SVG. Backend memakai Python standard library; penyimpanan dapat memakai Supabase atau SQLite lokal.

## Menyiapkan Supabase

1. Buat proyek di [Supabase](https://supabase.com/dashboard).
2. Di proyek, buka **SQL Editor** lalu jalankan seluruh isi file `supabase.sql`. Ini membuat tabel `transactions`.
3. Buka **Project Settings > API Keys** dan salin **Project URL** serta **Secret key**. Pada proyek lama, gunakan `service_role` sebagai pengganti secret key.
4. Di PowerShell pada folder proyek, jalankan `Copy-Item .env.example .env`, lalu `notepad .env`. Isi `SUPABASE_URL` dan `SUPABASE_SECRET_KEY` dengan nilai proyek Anda. Ganti juga `BENDAHARA_INVITE_CODE` dengan kode rahasia buatan Anda. Jangan kirim atau publikasikan file `.env`.
5. Jalankan `python server.py`, lalu buka `http://127.0.0.1:8000`.
6. Pastikan alamat `http://127.0.0.1:8000/api/health` menampilkan `"penyimpanan":"Supabase"`.

> Bila URL dan kunci belum diisi, aplikasi otomatis memakai SQLite lokal dan membuat empat transaksi contoh. Saat memakai Supabase, aplikasi tidak menambahkan data contoh: tabel proyek Anda dimulai kosong.

## Menjalankan

Pastikan Python 3.9 atau lebih baru tersedia. Jalankan `python server.py` dari folder proyek. Terminal harus tetap terbuka selama aplikasi digunakan. Untuk berhenti, tekan `Ctrl+C`.

## API backend

- `GET /api/health` — status server dan penyimpanan yang sedang dipakai.
- `GET /api/summary` — total pemasukan, pengeluaran, saldo, dan jumlah transaksi.
- `GET /api/transactions` — riwayat transaksi.
- `GET /api/transactions?bulan=2026-11` — transaksi untuk bulan tertentu.
- `POST /api/transactions` — catat transaksi baru sebagai JSON.
- `POST /api/register` — buat akun siswa atau bendahara.
- `POST /api/login` — masuk dengan email dan kata sandi.

## Akun siswa dan bendahara

Daftar lewat halaman login KASIN. Akun siswa dapat melihat ringkasan dan transaksi. Hanya bendahara yang dapat mencatat transaksi. Pendaftaran bendahara memerlukan kode `BENDAHARA_INVITE_CODE` di `.env`; berikan kode itu hanya kepada bendahara yang ditunjuk. Peran disimpan pada metadata akun yang dikelola backend Supabase, bukan dipilih dari permintaan transaksi browser.

Pendaftaran dibuat dari backend menggunakan Supabase Auth Admin API. Kunci rahasia tetap berada di `.env` server dan tidak dikirim ke halaman web. Pengguna tetap bisa membaca data kas setelah login; jangan letakkan server ini di internet tanpa menambahkan pembatasan akses akun dan perlindungan operasional yang sesuai.

## Foto siswa

Halaman **Tentang kelas** menampilkan 41 kartu dengan foto di atas, nama di tengah, dan kalimat motivasi di bawahnya. Taruh foto JPG bernama `01.jpg` sampai `41.jpg` di folder `students`. Urutan foto mengikuti nomor kartu. Nama siswa dan motivasi dapat disunting dalam daftar `students` di `app.js`. Foto belum termasuk dalam ZIP karena belum diberikan.

## Deploy ke Vercel

Proyek ini sudah menyertakan fungsi Python di `api/` untuk endpoint API. Vercel menjalankan fungsi tersebut sebagai request terpisah; `python server.py` tetap dipakai untuk pemakaian lokal.

1. Ekstrak ZIP proyek ke folder kerja. Pastikan folder `api` dan file `vercel.json` ikut ada.
2. Pasang Node.js, lalu buka PowerShell di folder proyek dan jalankan `npm install --global vercel`.
3. Jalankan `vercel link`, masuk ke akun Vercel saat diminta, lalu pilih atau buat proyek baru.
4. Di Vercel Dashboard, buka proyek → **Settings → Environment Variables**. Tambahkan `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, dan `BENDAHARA_INVITE_CODE`. Pilih environment **Production** (tambahkan **Preview** juga jika ingin mencoba tautan preview).
5. Dari PowerShell folder proyek, jalankan `vercel --prod`. Setelah selesai, Vercel memberikan alamat situs publik.
6. Buka `https://alamat-proyek-anda/api/health`; pastikan `penyimpanan` menunjukkan `Supabase`, lalu coba login dan mencatat transaksi.

Variabel Vercel disimpan di pengaturan proyek, bukan di kode. Jangan upload `.env` atau `kasin.db`. Perubahan environment variable baru berlaku setelah deployment baru; deploy ulang dengan `vercel --prod` setelah mengubahnya.

Contoh badan JSON untuk `POST /api/transactions`:

```json
{
  "kind": "masuk",
  "description": "Iuran kas mingguan",
  "person": "Seluruh kelas",
  "amount": 25000,
  "category": "Iuran",
  "happened_on": "2026-11-18"
}
```

Nilai `kind` adalah `masuk` atau `keluar`. Nominal berupa rupiah bulat positif.

## Catatan keamanan

Kunci Supabase yang dipakai adalah kunci rahasia backend. Simpan hanya di `.env` pada komputer/server yang Anda kendalikan; jangan pernah masukkan ke `app.js`, `index.html`, atau file ZIP yang dibagikan. Backend contoh ini hanya mendengarkan di komputer sendiri (`127.0.0.1`). Jika ingin dipakai lewat internet atau oleh banyak perangkat, hosting backend dan tambahkan login serta pembatasan akses sebelum dibuka ke publik.
