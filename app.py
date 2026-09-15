import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import math
import re

st.set_page_config(page_title="SPH Dexa Medica", page_icon="📄", layout="centered")

st.title("📄 Cetak SPH - Mobile")
st.subheader("Template: Cetak_SPH")

# Fungsi pembersih teks
def sanitize_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '- ').encode('latin-1', 'replace').decode('latin-1')

# Fungsi cerdas membaca angka dari CSV (Menghindari ValueError)
def safe_float(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).strip()
    val_str = re.sub(r'[^\d,\.-]', '', val_str)
    
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

@st.cache_data
def load_data():
    df_cust = pd.read_csv("SPH2026_Customer.csv")
    df_prod = pd.read_csv("SPH2026_Master_Obat.csv")
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

if 'keranjang' not in st.session_state:
    st.session_state.keranjang = []

st.markdown("### 1. Pilih Outlet / Rumah Sakit")
selected_outlet = st.selectbox("Outlet:", outlets, label_visibility="collapsed")

st.markdown("### 2. Tambah Produk ke SPH")
col1, col2 = st.columns([2, 1])
with col1:
    selected_produk = st.selectbox("Pilih Produk Obat:", produks)
with col2:
    diskon = st.number_input("Diskon (%)", min_value=0, max_value=100, value=0, step=1)

if st.button("➕ Tambah ke SPH", use_container_width=True):
    prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]
    
    hna_val = 0.0
    if 'HNA' in prod_data.index: hna_val = safe_float(prod_data['HNA'])
    elif 'Harga Hna' in prod_data.index: hna_val = safe_float(prod_data['Harga Hna'])
        
    harga_jadi = hna_val - (hna_val * diskon / 100)
    
    st.session_state.keranjang.append({
        'Nama Produk': selected_produk,
        'Komposisi': prod_data.get('Komposisi', '-'),
        'Indikasi': prod_data.get('Indikasi', '-'),
        'Satuan': prod_data.get('Kemasan', '-'),
        'Isi': prod_data.get('Isi', '-'),
        'HNA': hna_val,
        'Diskon': diskon,
        'Harga Jadi': harga_jadi
    })
    st.success(f"Berhasil menambahkan {selected_produk}! (Lihat tabel di bawah)")

if len(st.session_state.keranjang) > 0:
    st.markdown("### 📋 Daftar Produk di SPH ini:")
    df_keranjang = pd.DataFrame(st.session_state.keranjang)
    
    df_tampil = df_keranjang[['Nama Produk', 'Satuan', 'Diskon', 'Harga Jadi']].copy()
    df_tampil['Harga Jadi'] = df_tampil['Harga Jadi'].apply(lambda x: f"Rp {x:,.0f}")
    df_tampil['Diskon'] = df_tampil['Diskon'].apply(lambda x: f"{x}%")
    st.table(df_tampil)
    
    if st.button("🗑️ Hapus Semua Produk", type="secondary"):
        st.session_state.keranjang = []
        st.rerun()

    st.markdown("---")
    if st.button("📄 Generate & Download PDF SPH", type="primary", use_container_width=True):
        cust_data = df_customer[df_customer['Nama Outlet'] == selected_outlet].iloc[0]
        
        class PDF(FPDF):
            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128)
                self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

        # === SETUP LANDSCAPE ===
        pdf = PDF('L', 'mm', 'A4')
        pdf.add_page()
        
        # Tanggal (Kanan Atas)
        tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, f'Boyolali, {tgl_sekarang}', 0, 1, 'R')
        
        # Header (Kiri)
        pdf.ln(5)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, 'Perihal : Surat Penawaran Harga', 0, 1, 'L')
        pdf.ln(5)
        
        pdf.cell(0, 5, 'Kepada Yth,', 0, 1, 'L')
        pdf.cell(0, 5, sanitize_text(cust_data.get('Direktur', '-')), 0, 1, 'L')
        pdf.cell(0, 5, sanitize_text(cust_data.get('Nama Outlet', '-')), 0, 1, 'L')
        pdf.cell(0, 5, sanitize_text(cust_data.get('Alamat', 'di Tempat')), 0, 1, 'L')
        pdf.ln(5)
        
        # Pembuka
        pdf.cell(0, 5, 'Dengan hormat,', 0, 1, 'L')
        pdf.cell(0, 5, 'Bersama surat ini kami PT. Dexa Medica mengajukan penawaran harga untuk produk berikut :', 0, 1, 'L')
        pdf.ln(3)
        
        # === TABEL HEADER ===
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(240, 240, 240)
        
        col_widths = [30, 35, 100, 15, 10, 25, 12, 35]
        headers = ['Nama Produk', 'Komposisi', 'Indikasi', 'Satuan', 'Isi', 'HNA', '%', 'Harga Jadi Satuan']
        
        for i in range(len(headers)):
            pdf.cell(col_widths[i], 8, headers[i], 1, 0, 'C', 1)
        pdf.ln()
        
        # === TABEL ISI (MULTI-LINE TEXT WRAP) ===
        pdf.set_font('Arial', '', 8)
        for item in st.session_state.keranjang:
            row = [
                sanitize_text(item['Nama Produk']),
                sanitize_text(item['Komposisi']),
                sanitize_text(item['Indikasi']),
                sanitize_text(item['Satuan']),
                sanitize_text(item['Isi']),
                f"{item['HNA']:,.0f}",
                f"{item['Diskon']}%",
                f"{item['Harga Jadi']:,.0f}"
            ]
            
            # Kalkulasi Tinggi Baris Maksimal
            max_h = 5
            for i, text in enumerate(row):
                lines = 0
                for paragraph in str(text).split('\n'):
                    w = pdf.get_string_width(paragraph)
                    lines += math.ceil(w / (col_widths[i] - 2)) if w > 0 else 1
                h = lines * 4.5
                if h > max_h: max_h = h
                
            start_x = pdf.get_x()
            start_y = pdf.get_y()
            
            # Auto Page Break jika baris melebihi kertas
            if start_y + max_h > 190: 
                pdf.add_page()
                start_y = pdf.get_y()
                
            for i in range(len(row)):
                x = pdf.get_x()
                y = pdf.get_y()
                
                # Menggambar Garis Kotak
                pdf.rect(x, y, col_widths[i], max_h)
                
                # Posisi Teks: Kanan untuk Harga, Tengah untuk Kemasan, Kiri untuk Nama Obat
                align = 'R' if i in [5, 6, 7] else 'C' if i in [3, 4] else 'L'
                
                # Menuliskan teks di dalam kotak
                pdf.multi_cell(col_widths[i], 4.5, str(row[i]), 0, align)
                
                # Menggeser kursor ke kolom selanjutnya
                pdf.set_xy(x + col_widths[i], start_y)
                
            pdf.ln(max_h)
            
        # === PENUTUP ===
        pdf.ln(5)
        pdf.set_font('Arial', '', 10)
        teks_penutup = "Kami berharap produk PT. Dexa Medica ini dapat menjadi standard di Rumah Sakit yang Bapak/Ibu pimpin. Demikian surat permohonan ini, atas perhatian dan kerjasamanya kami ucapkan terimakasih."
        pdf.multi_cell(0, 5, teks_penutup)
        pdf.ln(5)
        
        pdf.cell(0, 5, 'Salam,', 0, 1, 'L')
        pdf.ln(20) # Ruang Tanda Tangan
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 5, 'Ade - Div. Harmony', 0, 1, 'L')
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        st.success("✅ SPH Berhasil Dibuat!")
        st.download_button(
            label="📥 DOWNLOAD SPH SEKARANG",
            data=pdf_bytes,
            file_name=f"SPH_{selected_outlet.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
