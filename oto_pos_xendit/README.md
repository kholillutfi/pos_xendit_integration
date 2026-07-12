# Pos Xendit

Pos Xendit adalah module integrasi pembayaran Xendit untuk Point of Sale
Odoo. Module ini membantu kasir membuat pembayaran QRIS dari layar POS,
menampilkan QRIS untuk pelanggan, mencatat transaksi Xendit, dan menerima
update status pembayaran melalui webhook.

## Fitur Utama

* Menambahkan opsi Xendit sebagai payment terminal di konfigurasi Point of Sale.
* Menyediakan menu konfigurasi Xendit untuk mengatur environment sandbox atau
  production, secret key, webhook token, endpoint QRIS, endpoint test payment,
  API version, dan template body request.
* Mendukung request QRIS dari POS menggunakan reference dan amount dari transaksi
  POS.
* Menampilkan QRIS pada layar POS dan menyimpan QR string sebagai gambar agar
  mudah digunakan kasir.
* Menyimpan response API Xendit pada konfigurasi untuk kebutuhan pengecekan dan
  troubleshooting.
* Mencatat transaksi Xendit pada model khusus dengan payment request ID,
  reference, nominal, status Xendit, state internal, waktu kedaluwarsa, dan
  tanggal pembayaran.
* Menyediakan endpoint status transaksi dan cancel transaksi untuk kebutuhan
  sinkronisasi dari POS.
* Menerima webhook Xendit dan menyimpan riwayat payload webhook sebagai audit
  transaksi.
* Mengatur hak akses khusus agar konfigurasi dan transaksi Xendit hanya dikelola
  oleh user POS yang berwenang.

## Konfigurasi

1. Aktifkan fitur Xendit pada pengaturan Point of Sale.
2. Buat konfigurasi Xendit melalui menu Payment Xendit.
3. Isi secret key, webhook token, API version, dan endpoint yang digunakan.
4. Pilih environment sandbox untuk pengujian atau production untuk transaksi
   nyata.
5. Hubungkan konfigurasi Xendit ke payment method POS yang menggunakan terminal
   Xendit.

## Alur Pembayaran

1. Kasir memilih metode pembayaran Xendit pada layar POS.
2. POS mengirim request QRIS ke Xendit menggunakan data order.
3. QRIS ditampilkan pada layar POS untuk dibayar pelanggan.
4. Transaksi disimpan ke daftar transaksi Xendit.
5. Status pembayaran dapat diperbarui melalui pengecekan status atau webhook
   dari Xendit.

## Catatan Operasional

Pada mode production, field dan tombol untuk test payment disembunyikan dari
form konfigurasi agar operator fokus pada endpoint pembayaran utama. Mode
sandbox tetap menyediakan area test payment untuk kebutuhan pengujian.
