import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import io

# Konfigurasi Halaman (Responsive untuk HP)
st.set_page_config(page_title="SPH Dexa Medica", page_icon="📄", layout="centered")

# Header Aplikasi
st.title("📄 Cetak SPH - Mobile")
st.subheader("PT Dexa Medica")

# Fungsi untuk membersihkan karakter khusus agar tidak error di PDF
def sanitize_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '- ').encode('latin-1', 'replace').decode('latin-1')

# Load Data CSV
@st.cache_data
def load_data():
    df_cust = pd.read_csv("SPH2026_Customer.csv")
    df_prod = pd.read_csv("SPH2026_Master_Obat.csv")
    return df_cust, df_prod

try:
    df_customer, df_harga = load_data()
except Exception as e:
    st.error("Gagal memuat database CSV. Pastikan file berada di folder yang sama.")
    st.stop()

outlets = df_customer['Nama Outlet'].dropna().unique().tolist()
produks = df_harga['Nama Produk'].dropna().unique().tolist()

# ---- FORM INPUT ----
selected_outlet = st.selectbox("Pilih Outlet / RS:", outlets)
selected_produk = st.selectbox("Pilih Produk Obat:", produks)
diskon = st.number_input("Diskon (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)

# Tombol Generate
if st.button("Generate & Download SPH", use_container_width=True):
    
    # Ambil data spesifik
    cust_data = df_customer[df_customer['Nama Outlet'] == selected_outlet].iloc[0]
    prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]
    
    hna = float(prod_data['HNA'])
    harga_jadi = hna - (hna * diskon / 100)
    
    # --- SETUP PDF ---
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.set_text_color(0, 86, 179) # Biru korporat
            self.cell(0, 8, 'SURAT PENAWARAN HARGA', 0, 1, 'C')
            self.set_font('Arial', 'B', 11)
            self.cell(0, 6, 'PT DEXA MEDICA', 0, 1, 'C')
            self.line(10, 25, 200, 25)
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    
    # Tanggal SPH (Mengikuti tanggal hari ini saat di-klik)
    tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f'Boyolali, {tgl_sekarang}', 0, 1, 'R')
    
    # Penerima
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'Kepada Yth.', 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, sanitize_text(cust_data['Direktur']), 0, 1)
    pdf.cell(0, 5, sanitize_text(cust_data['Nama Outlet']), 0, 1)
    pdf.multi_cell(0, 5, sanitize_text(cust_data['Alamat']))
    pdf.ln(5)
    
    # Pembuka
    pdf.cell(0, 6, 'Dengan hormat,', 0, 1)
    pdf.multi_cell(0, 5, 'Semoga Bapak/Ibu dalam keadaan sehat dan sukses selalu. Bersama surat ini, kami dari PT Dexa Medica bermaksud menyampaikan penawaran harga khusus untuk produk kami sebagai berikut:')
    pdf.ln(5)
    
    # Tabel Header
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(50, 8, 'Nama Produk', 1, 0, 'C', 1)
    pdf.cell(30, 8, 'Kemasan', 1, 0, 'C', 1)
    pdf.cell(40, 8, 'HNA (Rp)', 1, 0, 'C', 1)
    pdf.cell(20, 8, 'Disc', 1, 0, 'C', 1)
    pdf.cell(50, 8, 'Harga Jadi (Rp)', 1, 1, 'C', 1)
    
    # Tabel Isi
    pdf.set_font('Arial', '', 10)
    # Memotong string terlalu panjang agar muat di kolom HP
    nama_prod = sanitize_text(prod_data['Nama Produk'])[:23]
    kemasan = sanitize_text(prod_data['Kemasan'])[:15]
    
    pdf.cell(50, 8, nama_prod, 1)
    pdf.cell(30, 8, kemasan, 1, 0, 'C')
    pdf.cell(40, 8, f'{hna:,.0f}', 1, 0, 'R')
    pdf.cell(20, 8, f'{diskon}%', 1, 0, 'C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(50, 8, f'{harga_jadi:,.0f}', 1, 1, 'R')
    
    # Indikasi
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, 'Indikasi:', 0, 1)
    pdf.set_font('Arial', '', 10)
    indikasi_bersih = sanitize_text(prod_data['Indikasi']).replace('\n', ' ')
    pdf.multi_cell(0, 5, indikasi_bersih)
    pdf.ln(8)
    
    # Penutup
    pdf.multi_cell(0, 5, f'Besar harapan kami agar penawaran ini dapat menjadi langkah awal dari kerjasama yang baik antara PT Dexa Medica dengan {sanitize_text(cust_data["Nama Outlet"])}.')
    pdf.ln(5)
    
    # TTD
    pdf.cell(0, 6, 'Hormat kami,', 0, 1)
    pdf.ln(20) # Ruang kosong untuk tanda tangan
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, 'Ade Budi Susetyo', 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, 'Regional Lead (PIMDA)', 0, 1)
    pdf.cell(0, 5, 'PT Dexa Medica', 0, 1)
    
    # Export PDF to memory (agar bisa langsung di-download web tanpa disimpan di folder server)
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    
    # Tombol Download PDF
    st.success("✅ Dokumen berhasil dibuat!")
    st.download_button(
        label="📥 KLIK DI SINI UNTUK DOWNLOAD SPH",
        data=pdf_bytes,
        file_name=f"SPH_{selected_outlet}_{selected_produk}.pdf".replace(" ", "_"),
        mime="application/pdf",
        use_container_width=True
    )