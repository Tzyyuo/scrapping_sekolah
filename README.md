# Scrapping SMA/SMK Referensi Kemdikbud

Script ini digunakan untuk melakukan scraping data sekolah jenjang SMA/SMK di kecamatan Baleendah, Kabupaten Bandung, Jawa Barat dari situs https://referensi.data.kemdikbud.go.id/pendidikan/dikmen. Data yang diambil meliputi NPSN, nama sekolah, alamat, kelurahan, status, email, telepon, dan website sekolah.

## Fitur
- Navigasi otomatis ke provinsi, kabupaten, dan kecamatan tertentu
- Scraping seluruh data sekolah pada kecamatan Baleendah
- Scraping detail kontak sekolah (email, telepon, website) dari halaman detail
- Hasil disimpan dalam file CSV

## Kebutuhan Sistem
- Python 3.7+
- Google Chrome (pastikan sudah terinstall)
- ChromeDriver (otomatis dikelola oleh webdriver-manager)

## Instalasi Dependensi
Jalankan perintah berikut untuk menginstall semua dependensi yang diperlukan:

```bash
pip install selenium webdriver-manager pandas beautifulsoup4
```

## Cara Menjalankan
1. Pastikan Google Chrome sudah terinstall di komputer Anda.
2. Jalankan script dengan perintah berikut di terminal:

```bash
python scrap_sma_smk_referensi_kemdikbud.py
```

3. Script akan membuka browser Chrome secara otomatis, melakukan scraping, dan menyimpan hasil ke file `daftar_sma_smk_baleendah_detail.csv`.

## Output
- File hasil scraping: `daftar_sma_smk_baleendah_detail.csv`
- Jika terjadi error pada proses scraping kecamatan, akan dibuat file screenshot `debug_kecamatan_baleendah.png` untuk membantu debugging.

## Catatan
- Script ini hanya mengambil data untuk kecamatan Baleendah di Kabupaten Bandung, Jawa Barat.
- Jika ingin scraping kecamatan/kabupaten/provinsi lain, Anda perlu mengubah bagian navigasi pada script.
- Jika website target mengalami perubahan struktur, script mungkin perlu penyesuaian.

## Troubleshooting
- Jika browser tidak terbuka, pastikan Chrome sudah terinstall dan versi ChromeDriver sesuai dengan versi Chrome Anda.
- Jika scraping gagal pada tahap tertentu, cek pesan error di terminal dan file screenshot debug jika tersedia.

## Lisensi
Script ini bebas digunakan untuk keperluan edukasi dan riset. 