import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import io
import re

st.set_page_config(page_title="SPH Dexa Medica", page_icon="📄", layout="centered")

st.title("📄 Cetak SPH - Mobile")
st.subheader("PT Dexa Medica")

def sanitize_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '- ').encode('latin-1', 'replace').decode('latin-1')

# Fungsi cerdas untuk mengatasi error format angka (titik/koma/Rp) di CSV
def safe_float(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).strip()
    val_str = re.sub(r'[^\d,\.-]', '', val_str) # Hapus karakter selain angka, titik, koma
    
    if '.' in val_str and ',' in val_str:
        if val_str.rfind('.') > val_str.rfind(','):
            val_str = val_str.replace(',', '')
        else:
            val_str = val_str.replace('.', '').replace(',', '.')
    else:
        if val_str.count('.') > 1:
            val_str = val_str.replace('.', '')
        elif val_str.count(',') > 1:
            val_str = val_str.replace(',', '')
        else:
            if ',' in val_str:
                parts = val_str.split(',')
                if len(parts[1]) == 3:
                    val_str = val_str.replace(',', '')
                else:
                    val_str = val_str.replace(',', '.')
            elif '.' in val_str:
                parts = val_str.split('.')
                if len(parts[1]) == 3:
                    val_str = val_str.replace('.', '')
    try:
        return float(val_str)
    except:
        return 0.0

# Load Data dengan aman & bersihkan nama kolom
@st.cache_data
def load_data():
    df_cust = pd.read_csv("SPH2026_Customer.csv")
    df_prod = pd.read_csv("SPH2026_Master_Obat.csv")
    
    # Hapus spasi tak kasat mata dari nama kolom
    df_cust.columns = df_cust.columns.str.strip()
    df_prod.columns = df_prod.columns.str.strip()
    
    return df_cust, df_prod

try:
    df_customer, df_harga = load_data()
except Exception as e:
    st.error(f"Gagal memuat file CSV: {e}")
    st.stop()

outlets = df_customer['Nama Outlet'].dropna().unique().tolist()
produks = df_harga['Nama Produk'].dropna().unique().tolist()

# ---- INISIALISASI KERANJANG SPH ----
if 'keranjang' not in st.session_state:
    st.session_state.keranjang = []

# ---- FORM INPUT OUTLET ----
st.markdown("### 1. Pilih Outlet / Rumah Sakit")
selected_outlet = st.selectbox("Outlet:", outlets, label_visibility="collapsed")

# ---- FORM INPUT PRODUK ----
st.markdown("### 2. Tambah Produk ke SPH")
col1, col2 = st.columns([2, 1])
with col1:
    selected_produk = st.selectbox("Pilih Produk Obat:", produks)
with col2:
    # FORMAT DISKON DIUBAH MENJADI ANGKA BULAT (10, 20, 30, dst)
    diskon = st.number_input("Diskon (%)", min_value=0, max_value=100, value=0, step=1)

if st.button("➕ Tambah ke SPH", use_container_width=True):
    prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]
    
    # Deteksi dan ubah harga dengan aman ke angka (mencegah ValueError)
    hna_val = 0.0
    if 'HNA' in prod_data.index: 
        hna_val = safe_float(prod_data['HNA'])
    elif 'Harga Hna' in prod_data.index: 
        hna_val = safe_float(prod_data['Harga Hna'])
        
    harga_jadi = hna_val - (hna_val * diskon / 100)
    
    # Masukkan ke keranjang
    st.session_state.keranjang.append({
        'Nama Produk': selected_produk,
        'Kemasan': prod_data.get('Kemasan', '-'),
        'HNA': hna_val,
        'Diskon': diskon,
        'Harga Jadi': harga_jadi,
        'Indikasi': prod_data.get('Indikasi', '-')
    })
    st.success(f"Berhasil menambahkan {selected_produk}! (Gulir ke bawah untuk melihat tabel)")

# ---- TAMPILKAN KERANJANG ----
if len(st.session_state.keranjang) > 0:
    st.markdown("### 📋 Daftar Produk di SPH ini:")
    df_keranjang = pd.DataFrame(st.session_state.keranjang)
    
    df_tampil = df_keranjang[['Nama Produk', 'Kemasan', 'Diskon', 'Harga Jadi']].copy()
    df_tampil['Harga Jadi'] = df_tampil['Harga Jadi'].apply(lambda x: f"Rp {x:,.0f}")
    df_tampil['Diskon'] = df_tampil['Diskon'].apply(lambda x: f"{x}%")
    st.table(df_tampil)
    
    if st.button("🗑️ Hapus Semua Produk", type="secondary"):
        st.session_state.keranjang = []
        st.rerun()

    # ---- TOMBOL GENERATE PDF ----
    st.markdown("---")
    if st.button("📄 Generate & Download PDF SPH", type="primary", use_container_width=True):
        cust_data = df_customer[df_customer['Nama Outlet'] == selected_outlet].iloc[0]
        
        class PDF(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 15)
                self.set_text_color(0, 86, 179)
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
        
        tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, f'Boyolali, {tgl_sekarang}', 0, 1, 'R')
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 6, 'Kepada Yth.', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 5, sanitize_text(cust_data.get('Direktur', '-')), 0, 1)
        pdf.cell(0, 5, sanitize_text(cust_data.get('Nama Outlet', '-')), 0, 1)
        pdf.multi_cell(0, 5, sanitize_text(cust_data.get('Alamat', '-')))
        pdf.ln(5)
        
        pdf.cell(0, 6, 'Dengan hormat,', 0, 1)
        pdf.multi_cell(0, 5, 'Semoga Bapak/Ibu dalam keadaan sehat dan sukses selalu. Bersama surat ini, kami dari PT Dexa Medica bermaksud menyampaikan penawaran harga khusus untuk produk kami sebagai berikut:')
        pdf.ln(5)
        
        # Tabel Header
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(60, 8, 'Nama Produk', 1, 0, 'C', 1)
        pdf.cell(25, 8, 'Kemasan', 1, 0, 'C', 1)
        pdf.cell(35, 8, 'HNA (Rp)', 1, 0, 'C', 1)
        pdf.cell(20, 8, 'Disc', 1, 0, 'C', 1)
        pdf.cell(50, 8, 'Harga Jadi (Rp)', 1, 1, 'C', 1)
        
        # Tabel Isi Multipel Produk
        pdf.set_font('Arial', '', 9)
        for item in st.session_state.keranjang:
            nama = sanitize_text(item['Nama Produk'])[:30]
            kemasan = sanitize_text(item['Kemasan'])[:12]
            
            pdf.cell(60, 8, nama, 1)
            pdf.cell(25, 8, kemasan, 1, 0, 'C')
            pdf.cell(35, 8, f"{item['HNA']:,.0f}", 1, 0, 'R')
            pdf.cell(20, 8, f"{item['Diskon']}%", 1, 0, 'C')
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(50, 8, f"{item['Harga Jadi']:,.0f}", 1, 1, 'R')
            pdf.set_font('Arial', '', 9)
            
        # Indikasi Multipel
        pdf.ln(8)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, 'Indikasi Produk:', 0, 1)
        for idx, item in enumerate(st.session_state.keranjang, start=1):
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(0, 5, f"{idx}. {sanitize_text(item['Nama Produk'])}", 0, 1)
            pdf.set_font('Arial', '', 9)
            indikasi_bersih = sanitize_text(item['Indikasi']).replace('\n', ' ')
            pdf.multi_cell(0, 5, f"    {indikasi_bersih}")
            pdf.ln(2)
            
        pdf.ln(3)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 5, f'Besar harapan kami agar penawaran ini dapat menjadi langkah awal dari kerjasama yang baik antara PT Dexa Medica dengan {sanitize_text(cust_data.get("Nama Outlet", "-"))}.')
        pdf.ln(5)
        
        pdf.cell(0, 6, 'Hormat kami,', 0, 1)
        pdf.ln(20)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 5, 'Ade Budi Susetyo', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 5, 'Regional Lead (PIMDA)', 0, 1)
        pdf.cell(0, 5, 'PT Dexa Medica', 0, 1)
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        st.success("✅ SPH Berhasil Dibuat!")
        st.download_button(
            label="📥 DOWNLOAD SPH SEKARANG",
            data=pdf_bytes,
            file_name=f"SPH_{selected_outlet.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
