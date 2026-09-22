import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="SPH SOLHAYS 2026 + Preview Diskon",
    page_icon="📄",
    layout="wide"
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
        # Bersihkan spasi teks
        for col in ['customer', 'product']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        # Bersihkan format angka
        for col in ['valuesales', 'DAF']:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '').str.replace(' ', ''), 
                    errors='coerce'
                ).fillna(0)
        
        # Hitung % Diskon (DAF / Value Sales) sesuai rumus G / J
        df['Disc_GJ'] = df.apply(
            lambda r: (r['DAF'] / r['valuesales'] * 100) if r['valuesales'] > 0 else 0, axis=1
        )
        return df
    except Exception as e:
        st.error(f"Gagal memuat database history SOLHAYS02: {e}")
        return pd.DataFrame()

# ==========================================
# 2. MASTER DATA PRODUK CONTOH / SPH
# ==========================================
# (Sesuaikan atau biarkan terhubung dengan master produk SPH-mu)
MASTER_PRODUK = {
    "ALBAPURE 20% 100ML": {"hna": 1650000, "kemasan": "Botol", "isi": 1},
    "DOFEN INJ 400MG": {"hna": 300000, "kemasan": "Ampul", "isi": 5},
    "INBUMIN FC TAB": {"hna": 195000, "kemasan": "Box", "isi": 30},
    "LEVICA 4ML": {"hna": 450000, "kemasan": "Vial", "isi": 1},
    "REPACOR": {"hna": 125000, "kemasan": "Box", "isi": 10}
}

# ==========================================
# 3. TAMPILAN UTAMA APLIKASI SPH
# ==========================================
st.title("📄 SPH / solhays_2026")
st.markdown("### Format SPH dengan Live Preview History Diskon (SOLHAYS02)")
st.divider()

# Ambil data history dari SOLHAYS02
df_history = fetch_history_diskon()

# Daftar Pilihan Rumah Sakit / Outlet
default_rs_list = [
    "RSUD Ir. Soekarno Sukoharjo",
    "RS Kustati Surakarta",
    "RS Kasih Ibu Solo",
    "RS Hermina Solo",
    "RSUD Pandan Arang Boyolali",
    "RS Islam Klaten"
]

if not df_history.empty and 'customer' in df_history.columns:
    sheet_rs = sorted([r for r in df_history['customer'].unique() if r and str(r).upper() != 'NAN'])
    list_rs = sorted(list(set(default_rs_list + sheet_rs)))
else:
    list_rs = default_rs_list

# --- 1. PILIH OUTLET / RUMAH SAKIT ---
st.markdown("#### 1. Pilih Outlet / Rumah Sakit")
selected_rs = st.selectbox("Outlet Tujuan", list_rs, label_visibility="collapsed")

st.divider()

# --- 2. TAMBAH PRODUK KE SPH ---
st.markdown("#### 2. Tambah Produk ke SPH")
product_options = list(MASTER_PRODUK.keys())
selected_prod = st.selectbox("Pilih Produk Obat:", product_options)

# Info Detail Produk
if selected_prod in MASTER_PRODUK:
    prod_info = MASTER_PRODUK[selected_prod]
    st.info(f"ℹ️ Info Produk: HNA: Rp {prod_info['hna']:,.0f} | Kemasan: {prod_info['kemasan']} | Isi: {prod_info['isi']}")

st.divider()

# ==========================================
# 4. LIVE PREVIEW HISTORY DISKON DARI SOLHAYS02
# ==========================================
st.markdown("#### 🔍 Preview History Diskon (SOLHAYS02 App)")

if not df_history.empty:
    # Filter pencocokan data history berdasarkan Outlet dan Produk yang dipilih
    match_hist = df_history[
        (df_history['customer'].str.contains(selected_rs, case=False, na=False)) & 
        (df_history['product'].str.contains(selected_prod, case=False, na=False))
    ]
    
    if not match_hist.empty:
        avg_hist_disc = match_hist['Disc_GJ'].mean()
        max_hist_disc = match_hist['Disc_GJ'].max()
        min_hist_disc = match_hist['Disc_GJ'].min()
        
        st.success(f"✅ Ditemukan riwayat transaksi untuk produk **{selected_prod}** di **{selected_rs}**!")
        
        h1, h2, h3 = st.columns(3)
        h1.metric("📉 Rata-rata Diskon (G/J)", f"{avg_hist_disc:.2f}%")
        h2.metric("🔺 Diskon Tertinggi", f"{max_hist_disc:.2f}%")
        h3.metric("🔻 Diskon Terendah", f"{min_hist_disc:.2f}%")
        
        with st.expander("📂 Lihat Detail Faktur & History Sebelumnya"):
            st.dataframe(
                match_hist[['Periode', 'Invoice', 'Unit', 'valuesales', 'DAF', 'Disc_GJ', 'Name']],
                use_container_width=True
            )
    else:
        st.warning(f"⚠️ Belum ada catatan history diskon untuk produk **{selected_prod}** di **{selected_rs}**. Pastikan menggunakan acuan standar penawaran.")
else:
    st.caption("Menghubungkan database history diskon SOLHAYS02...")

st.divider()

# ==========================================
# 5. MODE PERHITUNGAN HARGA & SPH
# ==========================================
st.markdown("#### Mode Perhitungan Harga:")
calc_mode = st.radio("Pilih Mode:", ["Input Diskon (%)", "Input Target Harga Jadi"], horizontal=True, label_visibility="collapsed")

target_harga = 0
input_disc_pct = 0

if calc_mode == "Input Target Harga Jadi":
    target_harga = st.number_input("Target Harga Jadi (Rp)", min_value=0.0, value=985000.0, step=1000.0)
    
    # Hitung otomatis persentase diskon berdasarkan HNA produk terpilih
    hna_prod = MASTER_PRODUK.get(selected_prod, {}).get("hna", 1)
    auto_disc = ((hna_prod - target_harga) / hna_prod * 100) if hna_prod > 0 else 0
    if auto_disc < 0: auto_disc = 0
    
    st.success(f"💡 **Diskon Otomatis Terhitung:**\n### **{auto_disc:.2f}%**")
else:
    input_disc_pct = st.slider("Masukkan Diskon (%)", 0.0, 100.0, 20.0, 0.5)
    hna_prod = MASTER_PRODUK.get(selected_prod, {}).get("hna", 0)
    target_harga = hna_prod - (hna_prod * input_disc_pct / 100)
    st.info(f"💰 **Harga Hasil Penawaran:** Rp {target_harga:,.0f}")

st.divider()

# Tombol Simpan / Cetak SPH
if st.button("💾 Simpan & Cetak Dokumen SPH", type="primary"):
    st.balloons()
    st.success(f"Dokumen SPH untuk **{selected_rs}** produk **{selected_prod}** berhasil diproses dan dicatat!")
