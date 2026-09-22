import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(
    page_title="SPH SOLHAYS 2026",
    page_icon="📄",
    layout="centered"
)

# ==========================================
# 1. KONEKSI DATA DISKON DARI SOLHAYS02_APP
# ==========================================
SPREADSHEET_ID = "1ZX3QEoFxIAld-nM63-9JD5UW_FVm88mAe72fswOYlT0"

@st.cache_data(ttl=30)
def fetch_history_diskon():
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=datasales"
    try:
        df = pd.read_csv(url)
        for col in ['customer', 'product']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        for col in ['valuesales', 'DAF']:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '').str.replace(' ', ''), 
                    errors='coerce'
                ).fillna(0)
        
        df['Disc_GJ'] = df.apply(
            lambda r: (r['DAF'] / r['valuesales'] * 100) if r['valuesales'] > 0 else 0, axis=1
        )
        return df
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# 2. MASTER DATA & KAMUS PEMETAAN OUTLET
# ==========================================
MASTER_PRODUK = {
    "ALBAPURE 20% 100ML": {"hna": 1650000.00, "kemasan": "Botol", "isi": 1},
    "DOFEN INJ 400MG": {"hna": 300000.00, "kemasan": "Ampul", "isi": 5},
    "INBUMIN FC TAB": {"hna": 195000.00, "kemasan": "Box", "isi": 30},
    "LEVICA 4ML": {"hna": 450000.00, "kemasan": "Vial", "isi": 1},
    "REPACOR": {"hna": 125000.00, "kemasan": "Box", "isi": 10}
}

OUTLET_MAPPING_SPH = {
    "RSUD Ir. Soekarno Sukoharjo": "SOEKARNO",
    "RS Kustati Surakarta": "KUSTATI",
    "RS Kasih Ibu Solo": "KASIH IBU",
    "RS Hermina Solo": "HERMINA",
    "RSUD Pandan Arang Boyolali": "PANDAN ARANG",
    "RS Islam Klaten": "ISLAM"
}

# ==========================================
# 3. FUNGSI GENERATOR PDF SPH
# ==========================================
def generate_pdf_sph(rs_name, prod_name, hna, final_price, disc_pct):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    # Header Dokumen
    pdf.cell(0, 10, "SURAT PENAWARAN HARGA (SPH)", ln=True, align="center")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "PT DEXA MEDICA - Rayon SOLHAYS02", ln=True, align="center")
    pdf.ln(10)
    
    # Informasi Outlet
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, f"Kepada Yth:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Manajemen / Bagian Pengadaan", ln=True)
    pdf.cell(0, 6, f"{rs_name}", ln=True)
    pdf.ln(10)
    
    # Detail Penawaran Produk (Tabel Sederhana)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 8, "Nama Produk", 1, 0, "C", True)
    pdf.cell(30, 8, "HNA (Rp)", 1, 0, "C", True)
    pdf.cell(30, 8, "Diskon (%)", 1, 0, "C", True)
    pdf.cell(40, 8, "Harga Penawaran", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(90, 8, f"{prod_name}", 1, 0, "L")
    pdf.cell(30, 8, f"{hna:,.2f}", 1, 0, "R")
    pdf.cell(30, 8, f"{disc_pct:.2f}%", 1, 0, "R")
    pdf.cell(40, 8, f"{final_price:,.2f}", 1, 1, "R")
    
    pdf.ln(15)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 6, "Dokumen ini digenerate secara otomatis melalui SPH App SOLHAYS02.", ln=True)
    
    # Simpan ke file temporary
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp_file.name)
    return tmp_file.name

# ==========================================
# 4. TAMPILAN UTAMA SPH
# ==========================================
st.markdown("### 📄 SPH / solhays_2026")
st.caption("Format Portrait dengan Live Preview History Diskon & Cetak PDF")
st.divider()

df_history = fetch_history_diskon()

# --- PILIH OUTLET & PRODUK ---
st.markdown("#### 1. Pilih Outlet / Rumah Sakit")
selected_rs = st.selectbox("Outlet Tujuan", list(OUTLET_MAPPING_SPH.keys()), label_visibility="collapsed")

st.divider()

st.markdown("#### 2. Tambah Produk ke SPH")
selected_prod = st.selectbox("Pilih Produk Obat:", list(MASTER_PRODUK.keys()), label_visibility="collapsed")

hna_prod = MASTER_PRODUK.get(selected_prod, {}).get("hna", 0.0)
if selected_prod in MASTER_PRODUK:
    prod_info = MASTER_PRODUK[selected_prod]
    st.info(f"ℹ️ HNA: Rp {prod_info['hna']:,.2f} | Kemasan: {prod_info['kemasan']} | Isi: {prod_info['isi']}")

st.divider()

# ==========================================
# 5. PREVIEW HISTORY DISKON
# ==========================================
st.markdown("#### 🔍 Preview History Diskon (SOLHAYS02)")

if not df_history.empty:
    keyword_query = OUTLET_MAPPING_SPH.get(selected_rs, selected_rs)
    match_hist = df_history[
        (df_history['customer'].str.contains(keyword_query, case=False, na=False)) & 
        (df_history['product'].str.contains(selected_prod, case=False, na=False))
    ]
    
    if not match_hist.empty:
        st.success(f"✅ Ditemukan riwayat transaksi untuk **{selected_prod}** di **{selected_rs}**:")
        display_hist = match_hist[['Periode', 'Invoice', 'Unit', 'valuesales', 'DAF', 'Disc_GJ', 'Name']].copy()
        display_hist['valuesales'] = display_hist['valuesales'].map('{:,.2f}'.format)
        display_hist['DAF'] = display_hist['DAF'].map('{:,.2f}'.format)
        display_hist['Disc_GJ'] = display_hist['Disc_GJ'].map('{:.2f}%'.format)
        
        st.dataframe(display_hist, use_container_width=True, height=180)
    else:
        st.warning(f"⚠️ Belum ada history untuk produk ini di outlet tersebut.")
else:
    st.caption("Menghubungkan database history...")

st.divider()

# ==========================================
# 6. MODE PERHITUNGAN HARGA
# ==========================================
st.markdown("#### Mode Perhitungan Harga:")
calc_mode = st.radio("Pilih Mode:", ["Input Diskon (%)", "Input Target Harga Jadi"], horizontal=True, label_visibility="collapsed")

target_harga = 0.0
input_disc_pct = 0.0

if calc_mode == "Input Target Harga Jadi":
    target_harga = st.number_input("Target Harga Jadi (Rp)", min_value=0.0, value=985000.00, step=1000.00, format="%.2f")
    auto_disc = ((hna_prod - target_harga) / hna_prod * 100) if hna_prod > 0 else 0.0
    if auto_disc < 0: auto_disc = 0.0
    input_disc_pct = auto_disc
    st.success(f"💡 **Diskon Otomatis Terhitung:**\n### **{auto_disc:.2f}%**")
else:
    input_disc_pct = st.number_input("Masukkan Diskon (%)", min_value=0.0, max_value=100.0, value=20.00, step=0.50, format="%.2f")
    target_harga = hna_prod - (hna_prod * input_disc_pct / 100.0)
    st.info(f"💰 **Harga Hasil Penawaran:** Rp {target_harga:,.2f}")

st.divider()

# ==========================================
# 7. TOMBOL GENERATE & DOWNLOAD PDF
# ==========================================
if st.button("💾 Generate Dokumen SPH (PDF)", type="primary", use_container_width=True):
    pdf_path = generate_pdf_sph(selected_rs, selected_prod, hna_prod, target_harga, input_disc_pct)
    
    with open(pdf_path, "rb") as pdf_file:
        byte_pdf = pdf_file.read()
        
    st.balloons()
    st.success("Dokumen SPH PDF berhasil dibuat! Silakan unduh melalui tombol di bawah:")
    
    st.download_button(
        label="⬇️ Download File PDF SPH Sekarang",
        data=byte_pdf,
        file_name=f"SPH_{selected_rs.replace(' ', '_')}_{selected_prod.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
