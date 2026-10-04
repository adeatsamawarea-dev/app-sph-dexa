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
st.subheader("Format Portrait (Pilihan Input Diskon / Harga Jadi)")

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

# --- FILE REKAP CSV ---
REKAP_FILE = "Rekap_SPH.csv"

def simpan_ke_rekap(data_rows):
    new_df = pd.DataFrame(data_rows)
    if os.path.exists(REKAP_FILE):
        try:
            existing_df = pd.read_csv(REKAP_FILE)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.to_csv(REKAP_FILE, index=False)
        except:
            new_df.to_csv(REKAP_FILE, index=False)
    else:
        new_df.to_csv(REKAP_FILE, index=False)

def cek_riwayat_outlet(outlet_name):
    if os.path.exists(REKAP_FILE):
        try:
            df_rekap = pd.read_csv(REKAP_FILE)
            if not df_rekap.empty and 'Outlet' in df_rekap.columns:
                matched = df_rekap[df_rekap['Outlet'] == outlet_name]
                if len(matched) > 0:
                    return len(matched), matched.iloc[-1]['Tanggal']
        except:
            pass
    return 0, None

# --- ANTARMUKA APLIKASI ---
st.markdown("### 1. Pilih Outlet / Rumah Sakit")
selected_outlet = st.selectbox("Outlet:", outlets, label_visibility="collapsed")

jumlah_riwayat, tgl_terakhir = cek_riwayat_outlet(selected_outlet)
if jumlah_riwayat > 0:
    st.warning(f"⚠️ **Perhatian:** Outlet **{selected_outlet}** sudah pernah dibuatkan SPH sebanyak **{jumlah_riwayat} kali** (Terakhir pada: {tgl_terakhir}).")

st.markdown("### 2. Tambah Produk & Metode Diskon")
selected_produk = st.selectbox("Pilih Produk Obat:", produks)

# Ambil data produk terpilih untuk acuan perhitungan
prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]
hna_val = 0.0
if 'HNA' in prod_data.index: hna_val = safe_float(prod_data['HNA'])
elif 'Harga Hna' in prod_data.index: hna_val = safe_float(prod_data['Harga Hna'])
isi_val = safe_float(prod_data.get('Isi', 1))
if isi_val <= 0: isi_val = 1

# PILIHAN METODE INPUT DISKON
metode_diskon = st.radio("Pilih Cara Input Diskon:", ["Berdasarkan Persen (%)", "Berdasarkan Target Harga Jadi (Satuan)"])

diskon = 0.0
if metode_diskon == "Berdasarkan Persen (%)":
    diskon = float(st.number_input("Masukkan Diskon (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1))
else:
    # Input Berdasarkan Target Harga Jadi Satuan (Inc PPN)
    target_harga_jadi = st.number_input("Masukkan Target Harga Jadi / Satuan (Inc PPN & Dibagi Isi):", min_value=0.0, value=0.0, step=100.0)
    if target_harga_jadi > 0:
        # Rumusbalik: target = ((HNA - (HNA * disc / 100)) * 1.11) / isi
        # target * isi / 1.11 = HNA - (HNA * disc / 100)
        # HNA * disc / 100 = HNA - (target * isi / 1.11)
        # disc = (HNA - (target * isi / 1.11)) / HNA * 100
        net_target = (target_harga_jadi * isi_val) / 1.11
        if hna_val > 0:
            diskon = max(0.0, min(100.0, ((hna_val - net_target) / hna_val) * 100))
            st.info(f"💡 Diskon otomatis dihitung: **{diskon:.2f}%**")

if st.button("➕ Tambah ke SPH", use_container_width=True):
    harga_net = hna_val - (hna_val * diskon / 100)
    harga_total_ppn = harga_net * 1.11 
    harga_jadi_satuan = harga_total_ppn / isi_val
    
    st.session_state.keranjang.append({
        'Nama Produk': selected_produk,
        'Komposisi': prod_data.get('Komposisi', '-'),
        'Indikasi': prod_data.get('Indikasi', '-'),
        'Satuan': prod_data.get('Kemasan', '-'),
        'Isi': int(isi_val),
        'HNA': hna_val,
        'Diskon': round(diskon, 2),
        'Harga Jadi Satuan': harga_jadi_satuan
    })
    st.success(f"Berhasil menambahkan {selected_produk} (Diskon: {diskon:.1f}%)!")

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
    
    # --- GENERATE PDF & LOGGING REKAP ---
    if st.button("📄 Generate & Download PDF SPH", type="primary", use_container_width=True):
        cust_data = df_customer[df_customer['Nama Outlet'] == selected_outlet].iloc[0]
        
        logo_path = "logoDX.webp"
        logo_png = "logo_temp.png"
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            img.save(logo_png, "PNG")
            
        qr_path = "ttd_qr.png"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data("https://portal.dexagroup.com/ebc/?i=DX013070722")
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_path)
        
        no_dokumen = f"SPH/{datetime.datetime.now().strftime('%Y%m%d/%H%M%S')}"
        tgl_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        rekap_rows = []
        for item in st.session_state.keranjang:
            rekap_rows.append({
                'Nomor Dokumen': no_dokumen,
                'Tanggal': tgl_str,
                'Outlet': selected_outlet,
                'Produk': item['Nama Produk'],
                'Diskon (%)': f"{item['Diskon']}%",
                'Harga Jadi Satuan (Inc PPN)': f"Rp {item['Harga Jadi Satuan']:,.0f}"
            })
        simpan_ke_rekap(rekap_rows)

        class PDF(FPDF):
            def header(self):
                if os.path.exists(logo_png):
                    self.image(logo_png, 7, 8, 50)
                    self.ln(18)
                else:
                    self.set_font('Arial', 'B', 15)
                    self.set_text_color(0, 86, 179)
                    self.cell(0, 8, 'PT DEXA MEDICA', 0, 1, 'L')
                    self.ln(5)
                
            def footer(self):
                self.set_y(-12)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128)
                self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

        # === HALAMAN 1: SURAT UTAMA ===
        pdf = PDF('P', 'mm', 'A4')
        pdf.set_margins(7, 7, 7)
        pdf.add_page()
        
        tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, f'Surakarta, {tgl_sekarang}', 0, 1, 'R')
        
        pdf.ln(3)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 5, f'Perihal : Surat Penawaran Harga ({no_dokumen})', 0, 1, 'L')
        pdf.ln(3)
        
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, 'Kepada Yth,', 0, 1, 'L')
        pdf.cell(0, 5, 'Kepala Farmasi', 0, 1, 'L')
        pdf.cell(0, 5, sanitize_text(cust_data.get('Nama Outlet', '-')), 0, 1, 'L')
        pdf.cell(0, 5, 'di Tempat', 0, 1, 'L')
        pdf.ln(4)
        
        pdf.cell(0, 5, 'Dengan hormat,', 0, 1, 'L')
        pdf.multi_cell(0, 5, f"Sebelumnya kami menyampaikan terimakasih kepada {sanitize_text(cust_data.get('Nama Outlet', '-'))} atas kepercayaan dan kerjasama yang telah terjalin dengan baik selama ini dengan PT Dexa Medica . Bersama surat ini kami PT. Dexa Medica mengajukan penawaran harga untuk produk berikut :")
        pdf.ln(3)
        
        # === TABEL HEADER ===
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(224, 224, 224)
        pdf.set_text_color(40, 40, 40)
        pdf.set_draw_color(180, 180, 180)
        
        col_widths = [45, 56, 15, 10, 25, 12, 33] 
        headers = ['Nama Produk', 'Komposisi', 'Satuan', 'Isi', 'HNA (Rp)', 'Disc', 'Harga Jadi / Sat']
        
        for i in range(len(headers)):
            pdf.cell(col_widths[i], 8, headers[i], 1, 0, 'C', 1)
        pdf.ln()
        
        # Tabel Isi
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(0, 0, 0)
        for item in st.session_state.keranjang:
            row = [
                sanitize_text(item['Nama Produk']),
                sanitize_text(item['Komposisi']),
                sanitize_text(item['Satuan']),
                str(item['Isi']),
                f"{item['HNA']:,.0f}",
                f"{item['Diskon']}%",
                f"{item['Harga Jadi Satuan']:,.0f}"
            ]
            
            max_lines = 1
            for i, text in enumerate(row):
                col_w = col_widths[i] - 4
                chars_per_line = max(1, int(col_w / 2.1))
                
                total_lines = 0
                for paragraph in str(text).split('\n'):
                    p_len = len(paragraph)
                    lines_needed = math.ceil(p_len / chars_per_line) if p_len > 0 else 1
                    total_lines += lines_needed
                if total_lines > max_lines:
                    max_lines = total_lines
                    
            max_h = max(6, max_lines * 4.2 + 3)
                
            start_x = pdf.get_x()
            start_y = pdf.get_y()
            
            if start_y + max_h > 245: 
                pdf.add_page()
                start_y = pdf.get_y()
                
            for i in range(len(row)):
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.rect(x, y, col_widths[i], max_h)
                
                align = 'R' if i in [4, 5, 6] else 'C' if i in [2, 3] else 'L'
                pdf.set_xy(x + 1, y + 1.5)
                pdf.multi_cell(col_widths[i] - 2, 3.8, str(row[i]), 0, align)
                pdf.set_xy(x + col_widths[i], start_y)
                
            pdf.ln(max_h)
            
        pdf.ln(4)
        pdf.set_font('Arial', '', 9.5)
        pdf.multi_cell(0, 5, 'Kami berharap produk PT. Dexa Medica ini dapat menjadi standard di Rumah Sakit yang Bapak/Ibu pimpin. Demikian surat permohonan ini, atas perhatian dan kerjasamanya kami ucapkan terimakasih.')
        pdf.ln(3)
        
        pdf.cell(0, 5, 'Salam,', 0, 1, 'L')
        
        y_ttd = pdf.get_y()
        if os.path.exists(qr_path):
            pdf.image(qr_path, 7, y_ttd + 2, 22)
            
        pdf.ln(26)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 5, 'Ade Budi Susetyo', 0, 1, 'L')
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, 'Regional Lead (PIMDA)', 0, 1, 'L')
        
        # === HALAMAN 2: LAMPIRAN ===
        pdf.add_page()
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(0, 86, 179)
        pdf.cell(0, 8, 'LAMPIRAN: INDIKASI DAN BROSUR PRODUK', 0, 1, 'C')
        pdf.ln(3)
        
        for idx, item in enumerate(st.session_state.keranjang, start=1):
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(0, 86, 179)
            pdf.cell(0, 6, f"{idx}. {sanitize_text(item['Nama Produk'])}", 0, 1, 'L')
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(0, 5, "Indikasi:", 0, 1, 'L')
            pdf.set_font('Arial', '', 9)
            indikasi_bersih = sanitize_text(item['Indikasi']).replace('\n', ' ')
            pdf.multi_cell(0, 5, indikasi_bersih)
            pdf.ln(2)
            
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(0, 5, "Brosur Produk:", 0, 1, 'L')
            
            clean_prod_name = re.sub(r'[^\w]', '_', item['Nama Produk'])
            brosur_file = f"brosur_{clean_prod_name}.png"
            brosur_file_jpg = f"brosur_{clean_prod_name}.jpg"
            
            found_brosur = None
            if os.path.exists(brosur_file): found_brosur = brosur_file
            elif os.path.exists(brosur_file_jpg): found_brosur = brosur_file_jpg
            
            if found_brosur:
                try:
                    pdf.image(found_brosur, w=196)
                    pdf.ln(3)
                except:
                    pass
            else:
                x_brosur = pdf.get_x()
                y_brosur = pdf.get_y()
                pdf.set_draw_color(200, 200, 200)
                pdf.rect(x_brosur, y_brosur, 196, 28) 
                pdf.set_font('Arial', 'I', 8)
                pdf.set_text_color(150, 150, 150)
                pdf.set_xy(x_brosur, y_brosur + 10)
                pdf.cell(196, 5, f"( Upload file '{brosur_file}' ke GitHub untuk menampilkan brosur asli )", 0, 1, 'C')
                
            pdf.set_text_color(0, 0, 0)
            pdf.set_draw_color(180, 180, 180)
            pdf.ln(3)
            
            if pdf.get_y() > 250:
                pdf.add_page()
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        if os.path.exists(logo_png): os.remove(logo_png)
        if os.path.exists(qr_path): os.remove(qr_path)
        
        st.success("✅ SPH Berhasil Dibuat & Telah Direkap Otomatis!")
        st.download_button(
            label="📥 DOWNLOAD SPH SEKARANG",
            data=pdf_bytes,
            file_name=f"SPH_{selected_outlet.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- MENU LIHAT REKAP ---
st.markdown("---")
with st.expander("📊 Lihat Rekap SPH Keseluruhan (Database GSheet)"):
    if os.path.exists(REKAP_FILE):
        df_rekap_view = pd.read_csv(REKAP_FILE)
        st.dataframe(df_rekap_view, use_container_width=True)
        
        st.download_button(
            label="📥 Download File Rekap (.csv)",
            data=df_rekap_view.to_csv(index=False).encode('utf-8'),
            file_name="Rekap_SPH_Dexa.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("Belum ada data rekap. Buat SPH pertama Anda untuk mulai merekap.")
