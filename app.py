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
st.subheader("Format Portrait (Margin Standar Resmi)")

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
col1, col2 = st.columns([2, 1])
with col1:
    selected_produk = st.selectbox("Pilih Produk Obat:", produks)
with col2:
    diskon = st.number_input("Diskon (%)", min_value=0, max_value=100, value=0, step=1)

# --- PERHITUNGAN LIVE UNTUK PREVIEW HARGA ---
prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]

hna_val = 0.0
if 'HNA' in prod_data.index: hna_val = safe_float(prod_data['HNA'])
elif 'Harga Hna' in prod_data.index: hna_val = safe_float(prod_data['Harga Hna'])
    
isi_val = safe_float(prod_data.get('Isi', 1))
if isi_val <= 0: isi_val = 1
    
harga_net = hna_val - (hna_val * diskon / 100)
harga_total_ppn = harga_net * 1.11 
harga_jadi_satuan = harga_total_ppn / isi_val

link_web_val = prod_data.get('Link Web', '')
if pd.isna(link_web_val): link_web_val = ''

# Menampilkan Kotak Preview Harga Jadi
st.success(f"💡 **Preview Harga Jadi (Satuan Terkecil): Rp {harga_jadi_satuan:,.0f}**")

# --- TOMBOL TAMBAH ---
if st.button("➕ Tambah ke SPH", use_container_width=True):
    st.session_state.keranjang.append({
        'Nama Produk': selected_produk,
        'Indikasi': prod_data.get('Indikasi', '-'),
        'Kemasan': prod_data.get('Kemasan', '-'),
        'Isi': int(isi_val),
        'HNA': hna_val,
        'Diskon': diskon,
        'Harga Jadi Satuan': harga_jadi_satuan,
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
            except:
                pass
            
        qr_path = "ttd_qr.png"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data("https://portal.dexagroup.com/ebc/?i=DX013070722")
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_path)
        
        class PDF(FPDF):
            def header(self):
                if os.path.exists(logo_png):
                    # X diset 30 mengikuti margin kiri, Y diset 12
                    self.image(logo_png, 30, 12, 45)
                    self.set_y(30) # Tulisan mulai pada margin atas 30mm
                else:
                    self.set_y(30)
                    self.set_font('Arial', 'B', 15)
                    self.set_text_color(0, 86, 179)
                    self.cell(0, 8, 'PT DEXA MEDICA', 0, 1, 'L')
                    self.ln(5)
                
            def footer(self):
                # Margin bawah 25mm (-25)
                self.set_y(-25)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128)
                self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

        # === HALAMAN 1: SURAT UTAMA ===
        pdf = PDF('P', 'mm', 'A4')
        # Setting margin: Kiri=30mm, Atas=30mm, Kanan=25mm
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
        
        # === TABEL HEADER (Font 10pt) ===
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(235, 235, 235) 
        pdf.set_text_color(30, 30, 30)
        pdf.set_draw_color(160, 160, 160) 
        
        # Lebar kertas (210) - Margin Kiri (30) - Margin Kanan (25) = Lebar Tabel (155mm)
        col_widths = [48, 17, 8, 26, 11, 45] 
        headers = ['Nama Produk', 'Kemasan', 'Isi', 'HNA (Rp)', 'Disc', 'Harga Jadi (Satuan Terkecil)']
        
        # Gambar header secara manual menggunakan cell bertumpuk jika teks panjang
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        max_h_header = 10 # Tinggi header
        
        for i in range(len(headers)):
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.rect(x, y, col_widths[i], max_h_header, style='DF') # D=Draw, F=Fill
            # Mengatur teks header ke tengah
            pdf.set_xy(x, y + 2.5)
            # Khusus untuk "Harga Jadi", ukurannya disesuaikan agar tidak meluap
            if i == 5:
                pdf.set_font('Arial', 'B', 9) 
            else:
                pdf.set_font('Arial', 'B', 10)
            pdf.multi_cell(col_widths[i], 5, headers[i], 0, 'C')
            pdf.set_xy(x + col_widths[i], start_y)
            
        pdf.ln(max_h_header)
        
        # === TABEL ISI (Font 10pt, Line spacing padat) ===
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        
        for item in st.session_state.keranjang:
            row = [
                sanitize_text(item['Nama Produk']),
                sanitize_text(item['Kemasan']),
                str(item['Isi']),
                f"{item['HNA']:,.0f}",
                f"{item['Diskon']}%",
                f"{item['Harga Jadi Satuan']:,.0f}"
            ]
            
            # Hitung tinggi sel dinamis berdasarkan font 10pt
            max_h = 6 # Tinggi minimum
            for i, text in enumerate(row):
                lines = 0
                for paragraph in str(text).split('\n'):
                    w = pdf.get_string_width(paragraph)
                    # Spasi antar tepi dihitung (col_widths[i] - 2)
                    lines += math.ceil(w / (col_widths[i] - 2)) if w > 0 else 1
                # Menggunakan tinggi 5 untuk spasi baris standar yang terlihat padat (1.0 - 1.15)
                h = lines * 5 
                if h > max_h: max_h = h
                
            max_h = max_h + 4 # Padding estetika tabel atas & bawah
            
            start_x = pdf.get_x()
            start_y = pdf.get_y()
            
            # Cek batas halaman baru (297mm - margin bawah 25 - pengaman)
            if start_y + max_h > 265: 
                pdf.add_page()
                start_y = pdf.get_y()
                
            for i in range(len(row)):
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.rect(x, y, col_widths[i], max_h)
                
                align = 'R' if i in [3, 4, 5] else 'C' if i in [1, 2] else 'L'
                
                pdf.set_xy(x, y + 2) # Padding teks dalam tabel
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
                    pdf.image(found_brosur, w=155) # Lebar 155 disesuaikan area margin baru
                    pdf.ln(3)
                except: pass
            else:
                if not (url_produk and url_produk != '-' and url_produk.startswith('http')):
                    x_brosur = pdf.get_x()
                    y_brosur = pdf.get_y()
                    pdf.set_draw_color(200, 200, 200)
                    pdf.rect(x_brosur, y_brosur, 155, 20) 
                    pdf.set_font('Arial', 'I', 9)
                    pdf.set_text_color(150, 150, 150)
                    pdf.set_xy(x_brosur, y_brosur + 6)
                    pdf.cell(155, 5, f"( Detail Brosur tidak tersedia. Tambahkan Link Web pada Master Data )", 0, 1, 'C')
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_draw_color(160, 160, 160)
                    pdf.set_y(y_brosur + 23)
            
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
