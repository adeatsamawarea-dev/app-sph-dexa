import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import io
import re

st.set_page_config(page_title="SPH Dexa Medica", page_icon="📄", layout="centered")

st.title("📄 Cetak SPH - Mobile")
st.subheader("PT Dexa Medica")

# Fungsi pembersih teks
def sanitize_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '- ').encode('latin-1', 'replace').decode('latin-1')

# Fungsi cerdas untuk mengatasi error format angka di CSV
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

# Load Data
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

# ---- INISIALISASI KERANJANG ----
if 'keranjang' not in st.session_state:
    st.session_state.keranjang = []

# ---- FORM INPUT PRODUK ----
st.markdown("### 2. Tambah Produk ke SPH")

selected_produk = st.selectbox("Pilih Produk Obat:", produks)

# Tarik data HNA produk terlebih dahulu agar bisa dijadikan acuan hitung
prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]
hna_val = 0.0
if 'HNA' in prod_data.index: 
    hna_val = safe_float(prod_data['HNA'])
elif 'Harga Hna' in prod_data.index: 
    hna_val = safe_float(prod_data['Harga Hna'])

# Pilihan 2 Metode Input
metode = st.radio("Atur harga berdasarkan:", ["Diskon (%)", "Harga Jadi (Rp)"], horizontal=True)

if metode == "Diskon (%)":
    diskon = st.number_input("Input Diskon (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
    harga_jadi = round(hna_val - (hna_val * diskon / 100))
else:
    harga_jadi = st.number_input("Input Harga Jadi (Rp)", min_value=0.0, value=float(hna_val), step=100.0)
    # Hitung mundur persentase diskon berdasarkan harga jadi
    if hna_val > 0:
        diskon = round(((hna_val - harga_jadi) / hna_val) * 100, 2)
    else:
        diskon = 0.0

# --- PREVIEW BANTUAN HNA & HARGA JADI (LIVE) ---
st.info(f"💡 **Preview:** HNA **Rp {hna_val:,.0f}** | Diskon **{diskon:g}%** ➡️ Harga Akhir **Rp {harga_jadi:,.0f}**")

# Tombol untuk memasukkan ke keranjang
if st.button("➕ Tambah ke SPH", use_container_width=True):
    st.session_state.keranjang.append({
        'Nama Produk': selected_produk,
        'Kemasan': prod_data.get('Kemasan', '-'),
        'HNA': hna_val,
        'Diskon': diskon,
        'Harga Jadi': harga_jadi,
        'Indikasi': prod_data.get('Indikasi', '-')
    })
    st.success(f"Berhasil menambahkan {selected_produk}! (Gulir ke bawah)")
    
# ---- TAMPILKAN KERANJANG ----
if len(st.session_state.keranjang) > 0:
    st.markdown("### 📋 Daftar Produk di SPH ini:")
    df_keranjang = pd.DataFrame(st.session_state.keranjang)
    
    df_tampil = df_keranjang[['Nama Produk', 'Kemasan', 'Diskon', 'Harga Jadi']].copy()
    df_tampil['Harga Jadi'] = df_tampil['Harga Jadi'].apply(lambda x: f"Rp {x:,.0f}")
    df_tampil['Diskon'] = df_tampil['Diskon'].apply(lambda x: f"{x:g}%")
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
            self.set_font('Arial', 'B', 16)
            self.set_text_color(220, 20, 60)
            self.cell(0, 8, 'PT DEXA MEDICA', 0, 1, 'L')
            
            self.set_font('Arial', 'I', 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, 'Expertise for the Promotion of Health', 0, 1, 'L')
            
            self.set_draw_color(220, 20, 60)
            self.set_line_width(0.8)
            self.line(20, 25, 190, 25)
            self.set_line_width(0.2)
            self.line(20, 26, 190, 26)
            self.ln(10)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    
    pdf.set_margins(left=20, top=15, right=15)
    pdf.add_page()
    
    tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    pdf.cell(0, 8, f'Surakarta, {tgl_sekarang}', 0, 1, 'R')
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, 'Perihal : Penawaran Harga', 0, 1, 'L')
    pdf.ln(5)
    
    pdf.cell(0, 5, 'Kepada Yth.', 0, 1)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, sanitize_text(cust_data.get('Direktur', '-')), 0, 1)
    pdf.cell(0, 5, sanitize_text(cust_data.get('Nama Outlet', '-')), 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, 'di Tempat', 0, 1)
    pdf.ln(5)
    
    pdf.cell(0, 6, 'Dengan hormat,', 0, 1)
    pdf.multi_cell(0, 5, 'Semoga Bapak/Ibu dalam keadaan sehat dan sukses selalu. Bersama surat ini, kami dari PT Dexa Medica bermaksud menyampaikan penawaran harga khusus untuk produk kami sebagai berikut:')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(220, 20, 60) 
    pdf.set_text_color(255, 255, 255) 
    pdf.set_draw_color(200, 200, 200) 
    
    pdf.cell(60, 8, 'Nama Produk', 1, 0, 'C', 1)
    pdf.cell(25, 8, 'Kemasan', 1, 0, 'C', 1)
    pdf.cell(30, 8, 'HNA (Rp)', 1, 0, 'C', 1)
    pdf.cell(15, 8, 'Disc', 1, 0, 'C', 1)
    pdf.cell(45, 8, 'Harga Jadi (Rp)', 1, 1, 'C', 1)
    
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    
    fill = False
    pdf.set_fill_color(245, 245, 245)
    
    for item in st.session_state.keranjang:
        nama = sanitize_text(item['Nama Produk'])[:30]
        kemasan = sanitize_text(item['Kemasan'])[:12]
        
        pdf.cell(60, 8, nama, 1, 0, 'L', fill)
        pdf.cell(25, 8, kemasan, 1, 0, 'C', fill)
        pdf.cell(30, 8, f"{item['HNA']:,.0f}", 1, 0, 'R', fill)
        pdf.cell(15, 8, f"{item['Diskon']:g}%", 1, 0, 'C', fill)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(45, 8, f"{item['Harga Jadi']:,.0f}", 1, 1, 'R', fill)
        pdf.set_font('Arial', '', 9)
        
        fill = not fill 
        
    pdf.ln(5)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, f'Besar harapan kami agar penawaran ini dapat menjadi langkah awal dari kerjasama yang baik antara PT Dexa Medica dengan {sanitize_text(cust_data.get("Nama Outlet", "-"))}.')
    pdf.ln(8)
    
    pdf.cell(0, 6, 'Hormat kami,', 0, 1)
    
    x_pos = pdf.get_x()
    y_pos = pdf.get_y()
    
    try:
        pdf.image('qr-code.png', x=x_pos, y=y_pos + 2, w=25)
        pdf.ln(30)
    except Exception as e:
        pdf.ln(20) 
        
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, 'Ade Budi Susetyo', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, 'Regional Lead (PIMDA)', 0, 1)
    pdf.cell(0, 5, 'PT Dexa Medica', 0, 1)
    
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    
    st.success("✅ SPH Berhasil Dibuat!")
    st.download_button(
        label="📥 DOWNLOAD SPH SEKARANG",
        data=pdf_bytes,
        file_name=f"SPH_{selected_outlet.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True)
