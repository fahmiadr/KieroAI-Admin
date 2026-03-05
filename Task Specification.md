# **Technical Task Specification: KieroOPS Enhancement Phase 2**

**Document Objective:** Panduan implementasi teknis untuk *Agent / Developer* dalam melakukan refaktorisasi arsitektur database, implementasi AG Grid untuk tabel dinamis, pengujian koneksi, dan mekanisme *polling* status service secara *real-time* pada ekosistem KieroOPS.

## **Task 1: Refaktorisasi Database Config ke Connection String URI**

**Konteks:**

Saat ini konfigurasi database di file registry JSON (seperti registry\_prod.json) menggunakan multi-field (host, port, username, database\_name). Ini harus disederhanakan menjadi single-field yang mereferensikan *Environment Variable Key* yang berisi **Connection String URI** (standar RFC 3986\) di file .env masing-masing service.

**Langkah Eksekusi (Backend):**

1. **Update JSON Schema:**  
   Ubah struktur object "database" pada file configs/registry\_prod.json dan configs/registry\_dev.json.  
   *Hapus:* host, port, username, database\_name.  
   *Pertahankan/Tambahkan:* engine, connection\_env\_key, saved\_queries.  
   *Contoh:*  
   "database": {  
       "engine": "postgresql",  
       "connection\_env\_key": "DATABASE\_URL",  
       "saved\_queries": \[ ... \]  
   }

2. **Update db\_helper.py (Koneksi DSN):**  
   Modifikasi fungsi koneksi untuk membaca *Connection String*.  
   * Gunakan library os.getenv(connection\_env\_key) untuk mengambil URL (misal: postgresql://user:pass@localhost:5432/dbname) dari direktori .env service.  
   * Jika engine \== 'postgresql', gunakan psycopg2.connect(dsn=connection\_string).  
   * Jika engine \== 'mysql', parse URI atau gunakan sqlalchemy.create\_engine(connection\_string) sebagai layer abstraksi (direkomendasikan untuk fleksibilitas URI).

## **Task 2: Implementasi Endpoint "Test Connection"**

**Konteks:**

Menyediakan API endpoint ringan untuk melakukan validasi TCP/Socket ke database sebelum eksekusi query DML/DQL.

**Langkah Eksekusi (Backend & Frontend):**

1. **Buat Route Baru (app.py):**  
   * **Metode:** POST /api/database/test  
   * **Payload:** {"service\_id": "\<string\>"}  
   * **Logic:** \- Cari service\_id di registry.  
     * Ekstrak connection\_env\_key dan muat string dari .env.  
     * Lakukan percobaan koneksi (misal conn \= psycopg2.connect(...)).  
     * *Success:* Jika koneksi objek terbentuk, langsung jalankan conn.close() dan kembalikan response {"success": true, "message": "Connection established successfully"} HTTP 200\.  
     * *Failed:* Tangkap exception (try-except) dan kembalikan {"success": false, "error": str(e)} HTTP 400\.  
2. **UI Implementation (templates/):**  
   * Tambahkan sebuah tombol \<button id="btnTestConn"\> (ikon steker/plug) di UI Modal Database di sebelah indikator nama database.  
   * Buat fungsi AJAX/Fetch JavaScript yang memanggil endpoint /api/database/test.  
   * Berikan *feedback* visual (Spinner saat *loading*, Alert/Toast berwarna hijau/merah berdasarkan *response*).

## **Task 3: Eksekusi Query Dinamis & Pagination dengan AG Grid**

**Konteks:**

Mengganti tabel HTML statis dengan **AG Grid** (Community Edition) untuk menangani rendering data besar dengan *Client-Side Pagination*, *Sorting*, dan *Filtering* bawaan.

**Langkah Eksekusi:**

1. **Modifikasi Endpoint Execute (POST /api/database/execute):**  
   * Pastikan endpoint mengembalikan struktur JSON yang flat dan bersih.  
   * **Format Response Wajib:**  
     {  
         "success": true,  
         "columns": \["id", "timestamp", "log\_level", "message"\],  
         "rows": \[  
             {"id": 1, "timestamp": "2026-03-04", "log\_level": "INFO", "message": "System started"},  
             {"id": 2, "timestamp": "2026-03-04", "log\_level": "ERROR", "message": "Failed to load"}  
         \]  
     }

     *(Catatan: Ubah format pengembalian row dari array of arrays/tuple menjadi array of objects/dictionaries agar kompatibel langsung dengan rowData AG Grid).*  
2. **Integrasi AG Grid di Frontend (templates/services.html atau modal file):**  
   * **Load Library:** Masukkan CDN AG Grid di head/body template.  
     \<script src="\[https://cdn.jsdelivr.net/npm/ag-grid-community/dist/ag-grid-community.min.js\](https://cdn.jsdelivr.net/npm/ag-grid-community/dist/ag-grid-community.min.js)"\>\</script\>

   * **Container DOM:** Siapkan container dengan class theme.  
     \<div id="dbGridContainer" class="ag-theme-alpine-dark" style="height: 500px; width: 100%;"\>\</div\>

   * **Logika JavaScript:** Pada fungsi fetch() hasil eksekusi database, inisialisasi AG Grid:  
     let gridOptions \= null; // Global reference

     function renderAgGrid(columns, rowData) {  
         const gridDiv \= document.querySelector('\#dbGridContainer');

         // Hancurkan grid lama jika sudah ada (mencegah memory leak)  
         if (gridOptions && gridOptions.api) {  
             gridOptions.api.destroy();  
         }

         // Mapping columns string ke AG Grid ColDef object  
         const columnDefs \= columns.map(col \=\> {  
             return { field: col, sortable: true, filter: true, resizable: true };  
         });

         gridOptions \= {  
             columnDefs: columnDefs,  
             rowData: rowData,  
             pagination: true,             // AKTIFKAN PAGINATION AG GRID  
             paginationPageSize: 50,       // SET LIMIT PER PAGE  
             defaultColDef: { flex: 1, minWidth: 100 },  
             overlayLoadingTemplate: '\<span class="ag-overlay-loading-center"\>Memuat Data...\</span\>',  
             overlayNoRowsTemplate: '\<span class="ag-overlay-loading-center"\>Tidak ada data ditemukan\</span\>'  
         };

         new agGrid.Grid(gridDiv, gridOptions);  
     }

## **Task 4: Real-Time Service Status Polling (State Synchronization)**

**Konteks:**

Menghilangkan ketergantungan *hard-reload* halaman untuk mengecek *state* service (Running/Stopped/Error). Frontend harus melakukan sinkronisasi *state* secara periodik (*asynchronous polling*).

**Langkah Eksekusi:**

1. **Buat API Polling (app.py):**  
   * **Metode:** GET /api/services/status  
   * **Logic:** Iterasi semua service di registry, gunakan fungsi evaluate\_service\_status(service) (yang sudah memuat logika systemctl is-active).  
   * **Response Format:**  
     {  
         "success": true,  
         "data": {  
             "kiai\_analyzer": "Running",  
             "kiai\_phonebot": "Error",  
             "kiero\_web\_admin": "Running"  
         }  
     }

2. **Frontend Poller Task (dashboard.html / app.js):**  
   * Implementasikan setInterval dengan interval 5000ms (5 detik).  
   * Pada *callback interval*, lakukan fetch('/api/services/status').  
   * **DOM Manipulation Logic:**  
     * Iterasi Object.entries(data).  
     * Pilih DOM element berdasarkan atribut ID/Class (misal id="status-badge-kiai\_analyzer").  
     * Update teks (contoh: "RUNNING", "STOPPED", "ERROR").  
     * Update class warna (contoh: hapus class badge-danger, tambahkan class badge-success jika status berubah dari Error ke Running).  
     * *(Opsional)* Update *state toggle switch* (jika ada) agar sinkron (checked/unchecked) mengikuti *actual state* dari server.

**End of Specification.**