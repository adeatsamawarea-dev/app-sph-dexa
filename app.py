import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="SPH SOLHAYS 2026",
    page_icon="📄",
    layout="centered"  # Menggunakan layout centered agar interface lebih sempit & rapi (tidak terlalu lebar)
)

# ==========================================
# 1. KONEKSI DATA DISKON DARI SOLHAYS02_APP
# ==========================================
SPREADSHEET_ID = "1ZX3QEoFxIAld-nM63-9JD5UW_FVm88mAe72fswOYlT0"

@st.cache_data(ttl=30)
def fetch_history_diskon():
    """Mengambil riwayat data sales & diskon secara live dari aplikasi SOLHAYS02_APP"""
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
        st.error(f"Gagal memuat database history SOLHAYS02: {e}")
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
# 3. TAMPILAN UTAMA SPH (COMPACT LAYOUT)
# ==========================================
st.markdown("### 📄 SPH / solhays_2026")
st.caption("Format Portrait dengan Live Preview History Diskon")
st.divider()

df_history = fetch_history_diskon()

# --- 1. PILIH OUTLET ---
st.markdown("#### 1. Pilih Outlet / Rumah Sakit")
list_sph_rs = list(OUTLET_MAPPING_SPH.keys())
selected_rs = st.selectbox("Outlet Tujuan", list_sph_rs, label_visibility="collapsed")

st.divider()

# --- 2. TAMBAH PRODUK KE SPH ---
st.markdown("#### 2. Tambah Produk ke SPH")
product_options = list(MASTER_PRODUK.keys())
selected_prod = st.selectbox("Pilih Produk Obat:", product_options, label_visibility="collapsed")

if selected_prod in MASTER_PRODUK:
    prod_info = MASTER_PRODUK[selected_prod]
    st.info(f"ℹ️ HNA: Rp {prod_info['hna']:,.2f} | Kemasan: {prod_info['kemasan']} | Isi: {prod_info['isi']}")

st.divider()

# ==========================================
# 4. LIVE PREVIEW HISTORY DISKON (TANPA RATA-RATA)
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
        
        # Tampilkan tabel detail history langsung (tanpa metrik rata-rata)
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
# 5. MODE PERHITUNGAN HARGA (INPUT ANGKA SEBELUMNYA)
# ==========================================
st.markdown("#### Mode Perhitungan Harga:")
calc_mode = st.radio("Pilih Mode:", ["Input Diskon (%)", "Input Target Harga Jadi"], horizontal=True, label_visibility="collapsed")

target_harga = 0.0
hna_prod = MASTER_PRODUK.get(selected_prod, {}).get("hna", 0.0)

if calc_mode == "Input Target Harga Jadi":
    target_harga = st.number_input("Target Harga Jadi (Rp)", min_value=0.0, value=985000.00, step=1000.00, format="%.2f")
    auto_disc = ((hna_prod - target_harga) / hna_prod * 100) if hna_prod > 0 else 0.0
    if auto_disc < 0: auto_disc = 0.0
    
    st.success(f"💡 **Diskon Otomatis Terhitung:**\n### **{auto_disc:.2f}%**")
else:
    input_disc_pct = st.number_input("Masukkan Diskon (%)", min_value=0.0, max_value=100.0, value=20.00, step=0.50, format="%.2f")
    target_harga = hna_prod - (hna_prod * input_disc_pct / 100.0)
    st.info(f"💰 **Harga Hasil Penawaran:** Rp {target_harga:,.2f}")

st.divider()

if st.button("💾 Simpan & Cetak Dokumen SPH", type="primary", use_container_width=True):
    st.balloons()
    st.success(f"Dokumen SPH untuk **{selected_rs}** berhasil diproses!")
