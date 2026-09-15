import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import math
import re
import os
from PIL import Image
import qrcode

st.set_page_config(page_title="SPH Dexa Medica", page_icon="📄", layout="centered")

st.title("📄 Cetak SPH - Mobile")
st.subheader("Format Portrait (Smart Calculator & Rapi)")

# --- FUNGSI PENDUKUNG ---
def sanitize_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '- ').encode('latin-1', 'replace').decode('latin-1')

def safe_float(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).strip()
    val_str = re.sub(r'[^\d,\.-]', '', val_str)
    
    if '.' in val_str and ',' in val_str:
        if val_str.rfind('.') > val_str.rfind(','): val_str = val_str.replace(',', '')
        else: val_str = val_str.replace('.', '').replace(',', '.')
    else:
        if val_str.count('.') > 1: val_str = val_str.replace('.', '')
        elif val_str.count(',') > 1: val_str = val_str.replace(',', '')
        else:
            if ',' in val_str:
                parts = val_str.split(',')
                if len(parts[1]) == 3: val_str = val_str.replace(',', '')
                else: val_str = val_str.replace(',', '.')
            elif '.' in val_str:
                parts = val_str.split('.')
                if len(parts[1]) == 3: val_str = val_str.replace('.', '')
    try: return float(val_str)
    except: return 0.0

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

# --- ANTARMUKA APLIKASI ---
st.markdown("### 1. Pilih Outlet / Rumah Sakit")
selected_outlet = st.selectbox("Outlet:", outlets, label_visibility="collapsed")

st.markdown("### 2. Tambah Produk ke SPH")
selected_produk = st.selectbox("Pilih Produk Obat:", produks)

# Tarik data produk
prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]
hna_val = 0.0
if 'HNA' in prod_data.index: hna_val = safe_float(prod_data['HNA'])
elif 'Harga Hna' in prod_data.index: hna_val = safe_float(prod_data['Harga Hna'])
    
isi_val = safe_float(prod_data.get('Isi', 1))
if isi_val <= 0: isi_val = 1

# Prioritaskan baca kolom 'Satuan', jika tidak ada baru baca 'Kemasan'
satuan_val = prod_data.get('Satuan', prod_data.get('Kemasan', '-'))
link_web_val = prod_data.get('Link Web', '')
if pd.isna(link_web_val): link_web_val = ''

# Menampilkan informasi dasar (HNA)
st.info(f"ℹ️ **Info Dasar Produk:** HNA: **Rp {hna_val:,.0f}** | Isi: **{int(isi_val)}** | Satuan: **{sanitize_text(satuan_val)}**")

# --- FITUR SMART CALCULATOR ---
st.markdown("#### Mode Perhitungan Harga:")
mode_hitung = st.radio(
    "Pilih cara input:",
    ["Input Diskon (%)", "Input Target Harga Jadi (Otomatis Hitung Diskon)"],
    horizontal=True,
    label_visibility="collapsed"
)

col1, col2 = st.columns([1, 1])

if mode_hitung == "Input Diskon (%)":
    with col1:
        diskon_input = st.number_input("Masukkan Diskon (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    
    # Hitung Harga Jadi
    harga_jadi_kalkulasi = (hna_val - (hna_val * diskon_input / 100)) * 1.11 / isi_val
    
    with col2:
        st.success(f"💡 **Harga Jadi:**\n### Rp {harga_jadi_kalkulasi:,.0f}")
        
    diskon_final = diskon_input
    harga_jadi_final = harga_jadi_kalkulasi

else:
    harga_maksimal = (hna_val * 1.11) / isi_val
    with col1:
        harga_input = st.number_input("Masukkan Target Harga Jadi (Rp)", min_value=0.0, value=float(harga_maksimal), step=1000.0)
    
    # Hitung Balik Diskon
    if hna_val > 0:
        diskon_kalkulasi = (1 - ((harga_input * isi_val) / (hna_val * 1.11))) * 100
    else:
        diskon_kalkulasi = 0.0
        
    with col2:
        st.success(f"💡 **Diskon Otomatis:**\n### {diskon_kalkulasi:,.2f}%")
        
    diskon_final = round(diskon_kalkulasi, 2)
    harga_jadi_final = harga_input


# --- TOMBOL TAMBAH ---
if st.button("➕ Tambah ke SPH", use_container_width=True):
    st.session_state.keranjang.append({
        'Nama Produk': selected_produk,
        'Indikasi': prod_data.get('Indikasi', '-'),
        'Satuan': satuan_val,
        'Isi': int(isi_val),
        'HNA': hna_val,
        'Diskon': diskon_final,
        'Harga Jadi Satuan': harga_jadi_final,
        'Link Web': str(link_web_val).strip()
    })
    st.toast(f"Berhasil menambahkan {selected_produk} ke SPH!", icon="✅")

if len(st.session_state.keranjang) > 0:
    st.markdown("### 📋 Daftar Produk di SPH:")
    df_keranjang = pd.DataFrame(st.session_state.keranjang)
    
    df_tampil = df_keranjang[['Nama Produk', 'Diskon', 'Harga Jadi Satuan']].copy()
    df_tampil['Harga Jadi Satuan'] = df_tampil['Harga Jadi Satuan'].apply(lambda x: f"Rp {x:,.0f}")
    df_tampil['Diskon'] = df_tampil['Diskon'].apply(lambda x: f"{x}%")
    st.table(df_tampil)
    
    if st.button("🗑️ Hapus Semua Produk", type="secondary"):
        st.session_state.keranjang = []
        st.rerun()

    st.markdown("---")
    
    # --- GENERATE PDF ---
    if st.button("📄 Generate & Download PDF SPH", type="primary", use_container_width=True):
        cust_data = df_customer[df_customer['Nama Outlet'] == selected_outlet].iloc[0]
        
        logo_path = "logoDX.webp"
        logo_png = "logo_temp.png"
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img.save(logo_png, "PNG")
            except: pass
            
        qr_path = "ttd_qr.png"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data("https://portal.dexagroup.com/ebc/?i=DX013070722")
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_path)
        
        class PDF(FPDF):
            def header(self):
                if os.path.exists(logo_png):
                    self.image(logo_png, 30, 12, 45)
                    self.set_y(30)
                else:
                    self.set_y(30)
                    self.set_font('Arial', 'B', 15)
                    self.set_text_color(0, 86, 179)
                    self.cell(0, 8, 'PT DEXA MEDICA', 0, 1, 'L')
                    self.ln(5)
                
            def footer(self):
                self.set_y(-25)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128)
                self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

        # === HALAMAN 1: SURAT UTAMA ===
        pdf = PDF('P', 'mm', 'A4')
        pdf.set_margins(30, 30, 25)
        pdf.add_page()
        
        tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, f'Boyolali, {tgl_sekarang}', 0, 1, 'R')
        
        pdf.ln(3)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 5, 'Perihal : Surat Penawaran Harga', 0, 1, 'L')
        
        pdf.ln(8) 
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, 'Kepada Yth,', 0, 1, 'L')
        pdf.cell(0, 5, 'Kepala Farmasi', 0, 1, 'L')
        pdf.cell(0, 5, sanitize_text(cust_data.get('Nama Outlet', '-')), 0, 1, 'L')
        
        pdf.ln(8) 
        pdf.cell(0, 5, 'Dengan hormat,', 0, 1, 'L')
        pdf.cell(0, 5, 'Bersama surat ini kami PT. Dexa Medica mengajukan penawaran harga untuk produk berikut :', 0, 1, 'L')
        pdf.ln(4)
        
        # === TABEL HEADER (WRAP TEXT & PROPORSI BARU) ===
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(235, 235, 235) 
        pdf.set_text_color(30, 30, 30)
        pdf.set_draw_color(160, 160, 160) 
        
        # Lebar Kertas(210) - Margin Kiri(30) - Kanan(25) = Lebar Tabel(155)
        # Penyesuaian agar teks Satuan tidak turun ke bawah
        col_widths = [56, 20, 10, 23, 14, 32] 
        headers = ['Nama Produk', 'Satuan', 'Isi', 'HNA (Rp)', 'Disc', 'Harga Jadi\n(Sat/Terkecil)']
        
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        max_h_header = 10 
        
        for i in range(len(headers)):
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.rect(x, y, col_widths[i], max_h_header, style='DF')
            
            # Deteksi Baris Baru (Wrap Text)
            if '\n' in headers[i]:
                pdf.set_xy(x, y + 1.5)
                pdf.multi_cell(col_widths[i], 3.5, headers[i], 0, 'C')
            else:
                pdf.set_xy(x, y + 3)
                pdf.multi_cell(col_widths[i], 4, headers[i], 0, 'C')
                
            pdf.set_xy(x + col_widths[i], start_y)
            
        pdf.ln(max_h_header)
        
        # === TABEL ISI ===
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        
        for item in st.session_state.keranjang:
            # Gunakan 'Satuan' sesuai permintaan Bapak
            row = [
                sanitize_text(item['Nama Produk']),
                sanitize_text(item['Satuan']),
                str(item['Isi']),
                f"{item['HNA']:,.0f}",
                f"{item['Diskon']:g}%", # :g akan menghilangkan .00 jika pas bulat
                f"{item['Harga Jadi Satuan']:,.0f}"
            ]
            
            max_h = 6
            for i, text in enumerate(row):
                lines = 0
                for paragraph in str(text).split('\n'):
                    w = pdf.get_string_width(paragraph)
                    lines += math.ceil(w / (col_widths[i] - 2)) if w > 0 else 1
                h = lines * 5 
                if h > max_h: max_h = h
                
            max_h = max_h + 4 
            
            start_x = pdf.get_x()
            start_y = pdf.get_y()
            
            if start_y + max_h > 265: 
                pdf.add_page()
                start_y = pdf.get_y()
                
            for i in range(len(row)):
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.rect(x, y, col_widths[i], max_h)
                
                align = 'R' if i in [3, 4, 5] else 'C' if i in [1, 2] else 'L'
                
                pdf.set_xy(x, y + 2) 
                pdf.multi_cell(col_widths[i], 5, str(row[i]), 0, align)
                pdf.set_xy(x + col_widths[i], start_y)
                
            pdf.ln(max_h)
            
        pdf.ln(6)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 5, 'Kami berharap produk PT. Dexa Medica ini dapat menjadi standard di Rumah Sakit yang Bapak/Ibu pimpin. Demikian surat permohonan ini, atas perhatian dan kerjasamanya kami ucapkan terimakasih.')
        
        pdf.ln(8) 
        pdf.cell(0, 5, 'Salam,', 0, 1, 'L')
        
        y_ttd = pdf.get_y()
        if os.path.exists(qr_path):
            pdf.image(qr_path, 30, y_ttd + 2, 22)
            
        pdf.ln(26)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 5, 'Ade Budi Susetyo', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, 'AM', 0, 1, 'L') 
        
        # === HALAMAN 2: LAMPIRAN ===
        pdf.add_page()
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(0, 86, 179)
        pdf.cell(0, 8, 'LAMPIRAN: DETAIL PRODUK', 0, 1, 'C')
        pdf.ln(4)
        
        for idx, item in enumerate(st.session_state.keranjang, start=1):
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(0, 86, 179)
            pdf.cell(0, 6, f"{idx}. {sanitize_text(item['Nama Produk'])}", 0, 1, 'L')
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 5, "Indikasi:", 0, 1, 'L')
            pdf.set_font('Arial', '', 10)
            indikasi_bersih = sanitize_text(item['Indikasi']).replace('\n', ' ')
            pdf.multi_cell(0, 5, indikasi_bersih)
            pdf.ln(2)
            
            url_produk = item.get('Link Web', '')
            if url_produk and url_produk != '-' and url_produk.startswith('http'):
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 5, "Informasi Lengkap (Website):", 0, 1, 'L')
                
                pdf.set_font('Arial', 'U', 10)
                pdf.set_text_color(0, 0, 255) 
                pdf.cell(0, 5, 'Klik di sini untuk melihat brosur & detail di Web Resmi Dexa', 0, 1, 'L', link=url_produk)
                
                pdf.set_text_color(0, 0, 0) 
                pdf.ln(3)
            
            clean_prod_name = re.sub(r'[^\w]', '_', item['Nama Produk'])
            brosur_file = f"brosur_{clean_prod_name}.png"
            brosur_file_jpg = f"brosur_{clean_prod_name}.jpg"
            
            found_brosur = None
            if os.path.exists(brosur_file): found_brosur = brosur_file
            elif os.path.exists(brosur_file_jpg): found_brosur = brosur_file_jpg
            
            if found_brosur:
                try:
                    pdf.image(found_brosur, w=155) 
                    pdf.ln(3)
                except: pass
            
            pdf.ln(4)
            
            if pdf.get_y() > 255:
                pdf.add_page()
        
        try:
            pdf_bytes = bytes(pdf.output()) 
        except:
            pdf_bytes = pdf.output(dest='S').encode('latin-1') 
        
        if os.path.exists(logo_png): os.remove(logo_png)
        if os.path.exists(qr_path): os.remove(qr_path)
        
        st.success("✅ SPH Berhasil Dibuat!")
        st.download_button(
            label="📥 DOWNLOAD SPH SEKARANG",
            data=pdf_bytes,
            file_name=f"SPH_{selected_outlet.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
