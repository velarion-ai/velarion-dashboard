"""
Velarion Company Intelligence — REIT Executive Compensation Dashboard
Deploy: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import io, re
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from supabase import create_client

st.set_page_config(page_title="Velarion Company Intelligence", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ============================================================
# AUTH GATE
# ============================================================
def check_password():
    if st.session_state.get('authenticated'): return True
    st.markdown('<div style="max-width:400px;margin:4rem auto;text-align:center;">', unsafe_allow_html=True)
    st.markdown("### 🔒 Velarion Company Intelligence")
    st.markdown("Enter credentials to access the dashboard.")
    user = st.text_input("Username", key="auth_user")
    pw = st.text_input("Password", type="password", key="auth_pw")
    if st.button("Login"):
        if user == "velarion" and pw == "demo2026":
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.markdown('</div>', unsafe_allow_html=True)
    return False

if not check_password(): st.stop()

SUPABASE_URL = "https://fhnffpgotkxxtwmwbizy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZobmZmcGdvdGt4eHR3bXdiaXp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEwNzAzNTEsImV4cCI6MjA4NjY0NjM1MX0.XU80VORX49loeJlbrq0w9hiGOUAN7fgEH6FPiF1E-GU"
REIT_INDEX_TICKER = "VNQ"
FY_YEAR = 2024
POS_ORDER = {'CEO': 0, 'PRESIDENT': 1, 'COO': 2, 'CFO': 3, 'CIO': 4, 'GC': 5, 'CAO': 6, 'OTHER_NEO': 7}
PROPERTY_TYPE_MAP = {
    'Industrial/Logistics': 'Industrial', 'Self-Storage': 'Self Storage',
    'Multifamily/Residential': 'Multifamily', 'Residential': 'Multifamily',
    'Mortgage/mREIT': 'Mortgage',
}
TICKER_RECLASSIFY = {
    'CTO': 'Retail', 'CURB': 'Retail', 'UE': 'Retail', 'WSR': 'Retail',
    'FCPT': 'Net Lease', 'GTY': 'Net Lease', 'PKST': 'Net Lease',
    'ESRT': 'Office', 'HPP': 'Office', 'JBGS': 'Office', 'PDM': 'Office',
    'LTC': 'Healthcare', 'STRW': 'Healthcare',
    'UMH': 'Multifamily',
    'PSTL': 'Specialty', 'HOUS': 'Specialty',
    'FBRT': 'Mortgage',
}
POSITION_DISPLAY = {'CEO': 'CEO', 'PRESIDENT': 'Pres', 'COO': 'COO', 'CFO': 'CFO', 'CIO': 'CIO', 'GC': 'GC', 'CAO': 'CAO'}
POSITION_FILTER_LABEL = {**POSITION_DISPLAY}
# Positions shown in sidebar filter
FILTER_POSITIONS = ['CEO', 'PRESIDENT', 'COO', 'CFO', 'CIO', 'GC', 'CAO']

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    .stApp { font-family: 'DM Sans', sans-serif; }
    .main-header { background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); padding: 1.8rem 2.5rem; border-radius: 12px; margin-bottom: 0.3rem; color: white; }
    .main-header h1 { margin: 0; font-size: 1.7rem; font-weight: 700; }
    .main-header p { margin: 0.2rem 0 0 0; opacity: 0.75; font-size: 0.9rem; }
    .intro-text { color: #475569; font-size: 0.9rem; line-height: 1.55; padding: 0.4rem 0 0.8rem 0; }
    .tab-instruction { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 1rem; font-size: 0.83rem; color: #0c4a6e; }
    .tab-cta { background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%); border-radius: 8px; padding: 0.7rem 1rem; margin-bottom: 1rem; font-size: 0.9rem; color: white; font-weight: 600; text-align: center; }
    .metric-card { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem 1.2rem; text-align: center; }
    .metric-card .label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em; color: #64748b; font-weight: 600; }
    .metric-card .value { font-size: 1.5rem; font-weight: 700; color: #0f172a; margin-top: 0.15rem; }
    .metric-card .sub { font-size: 0.78rem; color: #94a3b8; margin-top: 0.1rem; }
    .ai-narrative { background: linear-gradient(135deg, #f0f9ff 0%, #f8fafc 100%); border: 1px solid #bae6fd; border-left: 4px solid #0284c7; border-radius: 8px; padding: 1.2rem 1.5rem; margin: 1rem 0; font-size: 0.9rem; line-height: 1.65; color: #1e293b; }
    .ai-narrative .ai-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #0284c7; font-weight: 700; margin-bottom: 0.5rem; }
    .ai-report { background: linear-gradient(135deg, #f0fdf4 0%, #f8fafc 100%); border: 1px solid #86efac; border-left: 4px solid #16a34a; border-radius: 8px; padding: 1.5rem 2rem; margin: 1rem 0; font-size: 0.9rem; line-height: 1.7; color: #1e293b; }
    .ai-report .ai-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #16a34a; font-weight: 700; margin-bottom: 0.5rem; }
    .lookup-box { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px; padding: 1rem 1.5rem 0.3rem 1.5rem; margin-bottom: 0.5rem; text-align: center; }
    .lookup-box h2 { margin: 0 0 0.3rem 0; font-size: 1.15rem; font-weight: 700; color: #0f172a; }
    .lookup-box p { margin: 0 0 0.5rem 0; color: #475569; font-size: 0.83rem; }
    .stats-bar { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px; padding: 1rem 1.5rem; margin-top: 1rem; display: flex; gap: 2rem; flex-wrap: wrap; justify-content: center; }
    .stats-bar .stat { text-align: center; }
    .stats-bar .stat-label { font-size: 0.72rem; text-transform: uppercase; color: #64748b; font-weight: 600; }
    .stats-bar .stat-value { font-size: 1.1rem; font-weight: 700; color: #0f172a; }
    .analysis-picker { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px; padding: 1rem 1.5rem; margin: 0.5rem 0; }
    .partial-year { background: #fbbf24; color: #78350f; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .ext-badge { background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .hl-row { background: #dbeafe; border: 1px solid #93c5fd; border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; font-size: 0.88rem; }
    .filter-note { font-size: 0.75rem; color: #64748b; line-height: 1.4; padding: 0.5rem 0; border-top: 1px solid #e2e8f0; margin-top: 0.5rem; }
    .widen-warn { background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.8rem; color: #9a3412; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
    section[data-testid="stSidebar"] { background: #f8fafc; }
    section[data-testid="stSidebar"] .stMarkdown h3 { font-size: 0.83rem; text-transform: uppercase; letter-spacing: 0.07em; color: inherit; margin-top: 0.8rem; }
    span[data-baseweb="tag"] { background-color: #0f766e !important; color: white !important; }
    span[data-baseweb="tag"] span[role="presentation"] { color: white !important; }
    .stButton > button { background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important; color: white !important; border: none !important; font-weight: 600 !important; border-radius: 8px !important; padding: 0.6rem 1.5rem !important; font-size: 0.95rem !important; }
    .stButton > button:hover { background: linear-gradient(135deg, #0f766e 0%, #115e59 100%) !important; }
    .stDownloadButton > button { background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important; color: white !important; border: none !important; font-weight: 600 !important; border-radius: 8px !important; }
    div[data-baseweb="slider"] div[role="slider"] { background: #0f766e !important; border-color: #0f766e !important; }
    div[data-baseweb="slider"] [data-testid="stThumbValue"] { color: #0f766e !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: #f1f5f9; padding: 4px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { font-size: 1.05rem !important; font-weight: 600 !important; padding: 0.7rem 1.3rem !important; border-radius: 8px !important; color: #475569 !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: transparent !important; height: 0px !important; }
    .stTabs [aria-selected="true"] { color: white !important; background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important; border-radius: 8px !important; }
    .stCheckbox label span { font-weight: 600 !important; font-size: 0.95rem !important; }
    .footnote { font-size: 0.73rem; color: #94a3b8; font-style: italic; margin-top: 0.3rem; }
    .source-note { font-size: 0.68rem; color: #94a3b8; margin-top: 0.2rem; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    @media print {
        section[data-testid="stSidebar"] { display: none !important; }
        header, footer, #MainMenu { display: none !important; }
        .stButton, .stDownloadButton { display: none !important; }
        .main-header { break-inside: avoid; }
        .metric-card { break-inside: avoid; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA
# ============================================================
@st.cache_data(ttl=300)
def load_data():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    result = sb.table('exec_comp').select('*').execute()
    df = pd.DataFrame(result.data)
    for c in ['base_salary','cash_bonus_incentive','stock_based_comp','total_comp','market_cap']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
    df['fiscal_year'] = pd.to_numeric(df['fiscal_year'], errors='coerce').astype('Int64')
    df['property_type'] = df['property_type'].replace(PROPERTY_TYPE_MAP)
    df.loc[df['reit_type'] == 'Mortgage REIT', 'property_type'] = 'Mortgage'
    for tk, pt in TICKER_RECLASSIFY.items():
        df.loc[df['ticker'] == tk, 'property_type'] = pt
    # Exclude OTHER_NEO and Former executives
    df = df[df['position'] != 'OTHER_NEO'].copy()
    df = df[~df['title'].str.lower().str.contains('former', na=False)].copy()
    df['position_display'] = df['position'].map(POSITION_DISPLAY).fillna(df['position'])
    df['pos_order'] = df['position'].map(POS_ORDER).fillna(99)
    return df

@st.cache_data(ttl=3600)
def load_total_returns(tickers):
    try:
        import yfinance as yf
    except ImportError:
        return {}
    all_t = list(set(tickers + [REIT_INDEX_TICKER]))
    end_d = datetime(FY_YEAR, 12, 31)
    start_3y = datetime(FY_YEAR - 3, 1, 1)
    try:
        data = yf.download(all_t, start=start_3y, end=end_d + timedelta(days=7), progress=False)['Close']
    except Exception:
        return {}
    if data.empty: return {}
    if isinstance(data, pd.Series): data = data.to_frame(all_t[0])
    returns = {}
    for t in all_t:
        if t not in data.columns: continue
        p = data[t].dropna()
        if len(p) < 20: continue
        fy_end = p[p.index <= pd.Timestamp(end_d + timedelta(days=7))]
        if fy_end.empty: continue
        cur = fy_end.iloc[-1]
        s1 = p[p.index >= pd.Timestamp(datetime(FY_YEAR-1, 12, 28))]
        r1 = ((cur / s1.iloc[0]) - 1) * 100 if len(s1) > 1 else None
        s3 = p[p.index >= pd.Timestamp(datetime(FY_YEAR-3, 12, 28))]
        r3 = ((cur / s3.iloc[0]) - 1) * 100 if len(s3) > 1 else None
        returns[t] = {'return_1y': r1, 'return_3y': r3}
    return returns

# ============================================================
# HELPERS
# ============================================================
def fmt_dollars(val, ext_managed=False):
    if ext_managed and (pd.isna(val) or val is None or val == 0): return "EX-MGD"
    if pd.isna(val) or val is None: return "\u2014"
    if val == 0: return "$0"
    if abs(val) >= 1e6: return f"${val/1e6:,.1f}M"
    if abs(val) >= 1e3: return f"${val/1e3:,.0f}K"
    return f"${val:,.0f}"

def fmt_mcap(v):
    if pd.isna(v) or v is None: return "\u2014"
    return f"${v/1e9:,.2f}B"

def fmt_return(v):
    if v is None: return "N/A"
    return f"{'+' if v >= 0 else ''}{v:.1f}%"

def percentile_rank(value, series):
    if pd.isna(value) or len(series.dropna()) == 0: return None
    if len(series.dropna()) <= 1: return None
    rank = int((series.dropna() < value).sum() / len(series.dropna()) * 100)
    if rank == 0 and len(series.dropna()) > 1: rank = 1
    return rank

def quartile_label(pct):
    if pct is None: return "N/A"
    if pct >= 75: return "top quartile"
    if pct >= 50: return "second quartile"
    if pct >= 25: return "third quartile"
    return "bottom quartile"

def ordinal(n):
    if n is None: return "\u2014"
    if 11 <= n % 100 <= 13: return f"{n}th"
    return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n%10]}"

def clabel(t, n): return f"{t} \u2014 {n}"

def clean_ai(text):
    if not text: return text
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = text.replace('$', '&#36;')
    text = re.sub(r'\n\s*\n', '<br><br>', text)
    return text

def is_ext_advised(co_d, all_df):
    return (co_d['comp_source'] == 'external_manager').any() or 'CEO' not in co_d['position'].values

def get_ext_note(co_d):
    has_ext = (co_d['comp_source'] == 'external_manager').any()
    has_ceo = 'CEO' in co_d['position'].values
    if has_ext and not has_ceo: return "This company is externally advised. Officers shown reflect only those compensated directly."
    if has_ext: return "This company has externally managed executives. Some officers are compensated through the external management agreement."
    if not has_ceo: return "No CEO compensation data is available. The company may be externally advised."
    return ""

def detect_partial(row, peers_df):
    if pd.isna(row['total_comp']) or row['total_comp'] == 0: return False
    # Former exec = always partial year
    title = str(row.get('title', '')).lower()
    if 'former' in title: return True
    pp = peers_df[peers_df['position'] == row['position']]['total_comp'].dropna()
    if len(pp) < 3: return False
    stock = row.get('stock_based_comp')
    stock_missing = pd.isna(stock) or stock == 0 or stock is None
    sal = row.get('base_salary', 0) or 0
    sal_peers = peers_df[peers_df['position'] == row['position']]['base_salary'].dropna()
    sal_low = len(sal_peers) >= 3 and sal > 0 and sal < sal_peers.quantile(0.15)
    return bool((row['total_comp'] < pp.quantile(0.15) and stock_missing) or (sal_low and stock_missing))

def get_peer_stats(filt):
    return filt[filt['comp_source'] != 'external_manager']

def sort_by_position(co_df):
    return co_df.sort_values('pos_order')

def filter_fingerprint(filt_df):
    """Return a hashable tuple of filtered tickers — changes when peer group changes."""
    return tuple(sorted(filt_df['ticker'].unique()))

STALE_WARNING = '<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:0.6rem 1rem;font-size:0.83rem;color:#92400e;margin:0.5rem 0;">\u26A0\uFE0F Peer group filters have changed since this analysis was generated. Click the generate button again to refresh with the updated peer group.</div>'

def peer_context_str(filt, pt):
    ps = get_peer_stats(filt)
    n = ps[ps['property_type']==pt]['ticker'].nunique()
    mc_valid = filt['market_cap'].dropna()
    mcr = f"${mc_valid.min()/1e9:.2f}B\u2013${mc_valid.max()/1e9:.2f}B" if not mc_valid.empty else "$0B\u2013$0B"
    tickers = sorted(ps[ps['property_type']==pt]['ticker'].unique())
    return n, mcr, tickers

def comp_mix_str(row):
    t = row['total_comp'] if pd.notna(row['total_comp']) and row['total_comp'] > 0 else 1
    s = row['base_salary'] if pd.notna(row['base_salary']) else 0
    b = row['cash_bonus_incentive'] if pd.notna(row['cash_bonus_incentive']) else 0
    sk = row['stock_based_comp'] if pd.notna(row['stock_based_comp']) else 0
    return f"{s/t*100:.0f}% salary / {b/t*100:.0f}% cash / {sk/t*100:.0f}% equity"

def peer_mix_median(peers_df, position):
    pp = peers_df[peers_df['position']==position]
    if pp.empty: return "N/A"
    tots = pp['total_comp'].replace(0, np.nan).dropna()
    if tots.empty: return "N/A"
    valid = pp[pp['total_comp'] > 0]
    s_pct = (valid['base_salary'].fillna(0) / valid['total_comp'] * 100).median()
    b_pct = (valid['cash_bonus_incentive'].fillna(0) / valid['total_comp'] * 100).median()
    sk_pct = (valid['stock_based_comp'].fillna(0) / valid['total_comp'] * 100).median()
    return f"{s_pct:.0f}% salary / {b_pct:.0f}% cash / {sk_pct:.0f}% equity"

def render_pct_card(val, pct, label, med=None, n=None, is_ext=False, is_partial=False):
    if is_ext and (pd.isna(val) or val == 0):
        return f'<div style="padding:0.7rem;background:#fffbeb;border-radius:8px;border-left:3px solid #ca8a04;"><div style="font-size:0.68rem;text-transform:uppercase;color:#64748b;">{label}</div><div style="font-size:1.05rem;font-weight:700;color:#92400e;">EX-MGD</div></div>'
    pct_d = ordinal(pct) if pct is not None else "\u2014"
    color = "#16a34a" if pct and pct >= 50 else "#0284c7" if pct and pct >= 25 else "#475569" if pct is not None else "#94a3b8"
    partial_tag = '<div style="margin-top:3px;"><span class="partial-year">PARTIAL YEAR</span></div>' if is_partial else ''
    med_line = f'<div style="font-size:0.65rem;color:#94a3b8;margin-top:3px;">Median: {fmt_dollars(med)} | n={n}</div>' if med is not None and n is not None else ''
    return f'<div style="padding:0.7rem;background:#f8fafc;border-radius:8px;border-left:3px solid {color};"><div style="font-size:0.68rem;text-transform:uppercase;color:#64748b;">{label}</div><div style="font-size:1.05rem;font-weight:700;color:#0f172a;">{fmt_dollars(val)}</div><div style="font-size:0.82rem;color:{color};font-weight:600;">{pct_d} percentile</div><div style="background:#e2e8f0;border-radius:4px;height:5px;margin-top:5px;"><div style="width:{pct or 0}%;height:100%;background:{color};border-radius:4px;"></div></div>{med_line}{partial_tag}</div>'

def render_peer_table(exec_row, peers_df, position):
    ps = get_peer_stats(peers_df)
    pp = ps[ps['position'] == position].sort_values('total_comp', ascending=False).reset_index(drop=True)
    if pp.empty: return
    tk = exec_row['ticker']
    rows = []
    for i, (_, r) in enumerate(pp.iterrows()):
        is_hl = r['ticker'] == tk
        bg = "background:#dbeafe;" if is_hl else ("background:#f8fafc;" if i % 2 else "")
        fw = "font-weight:600;" if is_hl else ""
        mc = fmt_mcap(r['market_cap']) if pd.notna(r.get('market_cap')) else "\u2014"
        rows.append(f"<tr style='{bg}{fw}'><td>{i+1}</td><td>{r['ticker']}</td><td>{r['company_name'][:30]}</td><td>{r['first_name']} {r['last_name']}</td><td style='text-align:right'>{fmt_dollars(r['base_salary'])}</td><td style='text-align:right'>{fmt_dollars(r['cash_bonus_incentive'])}</td><td style='text-align:right'>{fmt_dollars(r['stock_based_comp'])}</td><td style='text-align:right'>{fmt_dollars(r['total_comp'])}</td><td style='text-align:right'>{mc}</td></tr>")
    html = f"""<div style="max-height:300px;overflow-y:auto;margin:0.5rem 0;border:1px solid #e2e8f0;border-radius:8px;">
    <table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
    <thead><tr style="background:#f0f9ff;position:sticky;top:0;"><th style="padding:6px;text-align:left;">Rank</th><th style="padding:6px;text-align:left;">Ticker</th><th style="padding:6px;text-align:left;">Company</th><th style="padding:6px;text-align:left;">Executive</th><th style="padding:6px;text-align:right;">Salary</th><th style="padding:6px;text-align:right;">Cash Bonus</th><th style="padding:6px;text-align:right;">Stock</th><th style="padding:6px;text-align:right;">Total Comp</th><th style="padding:6px;text-align:right;">Mkt Cap</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table></div>"""
    st.markdown(html, unsafe_allow_html=True)

def render_widen_warning(n_pos, pos_label, pt, key_suffix):
    """Render small peer group warning with guidance."""
    st.markdown(f'<div class="widen-warn">\u26A0\uFE0F Small peer group ({n_pos} {pos_label}{"s" if n_pos != 1 else ""} in {pt}). The AI analysis will incorporate a broader group of {pos_label}s across all REITs in the selected market cap range. For manual comparison, use the League Tables tab or adjust the sidebar filters. Note: if sidebar filters are adjusted, all executives will be compared against the selected filtered group.</div>', unsafe_allow_html=True)

# ============================================================
# AI — COMPENSATION CONSULTANT TONE
# ============================================================
def get_client():
    try:
        import anthropic; return anthropic.Anthropic()
    except Exception: return None

AI_TONE = """ROLE: You are a senior compensation consultant advising the management team — similar to Pearl Meyer or FW Cook. Your audience is the C-suite preparing for board meetings and comp committee negotiations.

APPROACH:
1. STATE the positioning (data and percentiles)
2. ANALYZE the compensation mix vs peer medians (salary/cash/equity split)
3. CONNECT compensation to shareholder returns (pay-for-performance)
4. RECOMMEND directional action grounded in data

MANAGEMENT-FRIENDLY TONE: Always lean toward the management team's perspective. When comp is low and performance is strong, advocate clearly: "Performance strongly supports a move toward the upper quartile." When comp is high and performance is strong: "Compensation reflects market-appropriate recognition of strong results." When comp is high and performance is weak: "The board may want to ensure incentive structures are tied to specific forward-looking performance metrics." When comp is low and performance is weak: "Current positioning reflects the performance trajectory, with room to adjust as results improve."

CRITICAL RULES: No markdown (no asterisks, bold, headers, bullets). Plain flowing paragraphs only. No title. Weave peer group details (property type, count, market cap range, company names) naturally into the text. Always include the compensation mix comparison. Always include a pay-for-performance assessment."""

def gen_exec(row, peers, all_df, ret_data, filt):
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    pos = row['position']; pt = row['property_type']; ps = get_peer_stats(peers); pp = ps[ps['position'] == pos]
    n_co, mcr, tickers = peer_context_str(peers, pt)
    st_d = {}
    for f in ['base_salary','cash_bonus_incentive','stock_based_comp','total_comp']:
        s = pp[f].dropna(); v = row[f]; p = percentile_rank(v, s) if pd.notna(v) else None
        st_d[f] = {'val': float(v) if pd.notna(v) else 0, 'pct': p, 'med': float(s.median()) if len(s)>0 else 0, 'n': len(s)}
    is_ext = row['comp_source'] == 'external_manager'; is_part = detect_partial(row, peers)
    tk = row['ticker']; r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    mix = comp_mix_str(row); peer_mix = peer_mix_median(ps, pos)
    # Returns quartile
    co_r1 = r.get('return_1y')
    peer_r1s = [ret_data.get(t,{}).get('return_1y') for t in tickers if ret_data.get(t,{}).get('return_1y') is not None]
    ret_pct = percentile_rank(co_r1, pd.Series(peer_r1s)) if co_r1 is not None and peer_r1s else None
    notes = ""
    if is_part: notes += "\nNOTE: Partial-year hire — comp reflects less than full year. Explicitly note this in the analysis and state that compensation should not be compared at face value to full-year peers."
    if is_ext: notes += "\nNOTE: Externally managed."
    # Broader context for small peer groups
    broader = ""
    if st_d['total_comp']['n'] < 5:
        notes += f"\nNOTE: Small {pt} peer group ({st_d['total_comp']['n']} {pos}s)."
        all_ps = get_peer_stats(all_df)
        mc_min = peers['market_cap'].min() if not peers.empty else 0.5e9
        mc_max = peers['market_cap'].max() if not peers.empty else 5e9
        all_pos = all_ps[(all_ps['position']==pos) & (all_ps['market_cap']>=mc_min) & (all_ps['market_cap']<=mc_max)]
        if len(all_pos) >= 3:
            all_tc = all_pos['total_comp'].dropna(); all_pct = percentile_rank(row['total_comp'], all_tc)
            all_n = len(all_tc); all_med = all_tc.median()
            all_mix = peer_mix_median(all_ps[(all_ps['market_cap']>=mc_min)&(all_ps['market_cap']<=mc_max)], pos)
            broader = f"""
BROADER CONTEXT (use because {pt} peer group is too small):
Across ALL {all_n} {pos}s in the ${mc_min/1e9:.2f}B-${mc_max/1e9:.2f}B range (all property types):
Total comp ${st_d['total_comp']['val']:,.0f} = {ordinal(all_pct)} percentile | Median ${all_med:,.0f} | Peer mix: {all_mix}
INSTRUCTION: Note the {pt} peer group is too small, then use the all-REIT data as the primary benchmark for your analysis and recommendations."""
    prompt = f"""REIT compensation analysis. 4-6 sentences.
{row['first_name']} {row['last_name']}, {pos}, {row['company_name']} ({tk}) | {pt} | Mkt Cap ${row['market_cap']/1e9:.2f}B
Total ${st_d['total_comp']['val']:,.0f} ({ordinal(st_d['total_comp']['pct'])} pctl, {quartile_label(st_d['total_comp']['pct'])}) | Salary ${st_d['base_salary']['val']:,.0f} ({ordinal(st_d['base_salary']['pct'])} pctl) | Bonus ${st_d['cash_bonus_incentive']['val']:,.0f} ({ordinal(st_d['cash_bonus_incentive']['pct'])} pctl) | Stock ${st_d['stock_based_comp']['val']:,.0f} ({ordinal(st_d['stock_based_comp']['pct'])} pctl)
Comp mix: {mix} | Peer median mix: {peer_mix}
Peer group: {st_d['total_comp']['n']} {pt} {pos}s from {n_co} cos in {mcr} | Tickers: {', '.join(tickers)}
FY{FY_YEAR} Returns: {tk} {fmt_return(co_r1)} ({ordinal(ret_pct)} pctl, {quartile_label(ret_pct)}) | {pt} avg {fmt_return(np.mean(peer_r1s) if peer_r1s else None)} | FTSE Nareit {fmt_return(vnq.get('return_1y'))}{broader}{notes}
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

def gen_returns(co_d, filt, ret_data):
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    tk = co_d['ticker'].iloc[0]; cn = co_d['company_name'].iloc[0]; pt = co_d['property_type'].iloc[0]
    r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    n_co, mcr, tickers = peer_context_str(filt, pt)
    p1 = [ret_data.get(t,{}).get('return_1y') for t in tickers if ret_data.get(t,{}).get('return_1y') is not None]
    p3 = [ret_data.get(t,{}).get('return_3y') for t in tickers if ret_data.get(t,{}).get('return_3y') is not None]
    ret_pct = percentile_rank(r.get('return_1y'), pd.Series(p1)) if r.get('return_1y') is not None and p1 else None
    prompt = f"""REIT returns and pay-for-performance analysis. 4-5 sentences. Calendar year {FY_YEAR}.
{cn} ({tk}) | {pt} | Mkt Cap ${co_d['market_cap'].iloc[0]/1e9:.2f}B
{tk}: 1-Yr {fmt_return(r.get('return_1y'))} ({ordinal(ret_pct)} pctl, {quartile_label(ret_pct)}) | 3-Yr {fmt_return(r.get('return_3y'))}
{pt} Avg ({n_co} cos): 1-Yr {fmt_return(np.mean(p1) if p1 else None)} | 3-Yr {fmt_return(np.mean(p3) if p3 else None)}
FTSE Nareit: 1-Yr {fmt_return(vnq.get('return_1y'))} | 3-Yr {fmt_return(vnq.get('return_3y'))}
Peers: {', '.join(tickers)} | Mkt cap: {mcr}
Connect returns to compensation positioning. If returns outperform peers but comp is below median, advocate for management. If returns lag but comp is high, suggest tying incentives to forward metrics.
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=400, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

def gen_analysis(co_d, filt, ret_data):
    """Combined company + returns analysis for Company View tab."""
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    cn = co_d['company_name'].iloc[0]; tk = co_d['ticker'].iloc[0]; pt = co_d['property_type'].iloc[0]; mc = co_d['market_cap'].iloc[0]
    ea = is_ext_advised(co_d, filt); ps = get_peer_stats(filt)
    n_co, mcr, tickers = peer_context_str(filt, pt)
    en = "\nNOTE: Externally advised." if ea else ""
    elines = []
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; ip = detect_partial(rw, filt)
        pp = ps[ps['position']==rw['position']]; pct = percentile_rank(rw['total_comp'], pp['total_comp'])
        t = rw['total_comp'] if pd.notna(rw['total_comp']) else 0
        mix = comp_mix_str(rw); pm = peer_mix_median(ps, rw['position'])
        fl = []
        if ie: fl.append('Ext')
        if ip: fl.append('Partial Yr')
        fs = f" [{', '.join(fl)}]" if fl else ""
        elines.append(f"  {rw['first_name']} {rw['last_name']}, {POSITION_DISPLAY.get(rw['position'],rw['position'])}: ${t:,.0f} ({ordinal(pct)} pctl, {quartile_label(pct)}) | Mix: {mix} | Peer mix: {pm}{fs}")
    tb = co_d['total_comp'].sum(); pcos = ps.groupby('ticker')['total_comp'].sum(); bp = percentile_rank(tb, pcos)
    r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    peer_r1s = [ret_data.get(t,{}).get('return_1y') for t in tickers if ret_data.get(t,{}).get('return_1y') is not None]
    p3 = [ret_data.get(t,{}).get('return_3y') for t in tickers if ret_data.get(t,{}).get('return_3y') is not None]
    ret_pct = percentile_rank(r.get('return_1y'), pd.Series(peer_r1s)) if r.get('return_1y') is not None and peer_r1s else None
    prompt = f"""REIT compensation and performance analysis. 6-8 sentences covering both team compensation positioning and shareholder returns.
{cn} ({tk}) | {pt} | Mkt Cap ${mc/1e9:.2f}B
TEAM:\n{chr(10).join(elines)}
Budget: ${tb:,.0f} ({ordinal(bp)} pctl vs {len(pcos)} peers)
FY{FY_YEAR} Returns: {tk} 1-Yr {fmt_return(r.get('return_1y'))} ({ordinal(ret_pct)} pctl returns, {quartile_label(ret_pct)}) | 3-Yr {fmt_return(r.get('return_3y'))}
{pt} Avg ({n_co} cos): 1-Yr {fmt_return(np.mean(peer_r1s) if peer_r1s else None)} | 3-Yr {fmt_return(np.mean(p3) if p3 else None)}
FTSE Nareit: 1-Yr {fmt_return(vnq.get('return_1y'))} | 3-Yr {fmt_return(vnq.get('return_3y'))}
Peers: {n_co} {pt} REITs, mkt cap {mcr} | Tickers: {', '.join(tickers)}
INSTRUCTIONS: Cover (1) each executive's compensation positioning and mix vs peers, (2) shareholder returns vs peer group and FTSE Nareit, (3) pay-for-performance assessment comparing comp quartile to returns quartile, and (4) a clear directional recommendation. If comp is below returns quartile, advocate for the management team. If any executive is flagged as [Partial Yr], explicitly note their compensation reflects a partial year of service and should not be compared at face value to full-year peers.{en}
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=700, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

def gen_company(co_d, filt, ret_data):
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    cn = co_d['company_name'].iloc[0]; tk = co_d['ticker'].iloc[0]; pt = co_d['property_type'].iloc[0]; mc = co_d['market_cap'].iloc[0]
    ea = is_ext_advised(co_d, filt); ps = get_peer_stats(filt)
    n_co, mcr, tickers = peer_context_str(filt, pt)
    en = "\nNOTE: Externally advised." if ea else ""
    elines = []
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; ip = detect_partial(rw, filt)
        pp = ps[ps['position']==rw['position']]; pct = percentile_rank(rw['total_comp'], pp['total_comp'])
        t = rw['total_comp'] if pd.notna(rw['total_comp']) else 0
        mix = comp_mix_str(rw); pm = peer_mix_median(ps, rw['position'])
        fl = []
        if ie: fl.append('Ext')
        if ip: fl.append('Partial Yr')
        fs = f" [{', '.join(fl)}]" if fl else ""
        elines.append(f"  {rw['first_name']} {rw['last_name']}, {POSITION_DISPLAY.get(rw['position'],rw['position'])}: ${t:,.0f} ({ordinal(pct)} pctl, {quartile_label(pct)}) | Mix: {mix} | Peer mix: {pm}{fs}")
    tb = co_d['total_comp'].sum(); pcos = ps.groupby('ticker')['total_comp'].sum(); bp = percentile_rank(tb, pcos)
    r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    peer_r1s = [ret_data.get(t,{}).get('return_1y') for t in tickers if ret_data.get(t,{}).get('return_1y') is not None]
    ret_pct = percentile_rank(r.get('return_1y'), pd.Series(peer_r1s)) if r.get('return_1y') is not None and peer_r1s else None
    prompt = f"""REIT compensation analysis. 5-7 sentences with pay-for-performance assessment.
{cn} ({tk}) | {pt} | Mkt Cap ${mc/1e9:.2f}B
TEAM:\n{chr(10).join(elines)}
Budget: ${tb:,.0f} ({ordinal(bp)} pctl vs {len(pcos)} peers)
FY{FY_YEAR} Returns: {tk} {fmt_return(r.get('return_1y'))} ({ordinal(ret_pct)} pctl returns, {quartile_label(ret_pct)}) | FTSE Nareit {fmt_return(vnq.get('return_1y'))}
Peers: {n_co} {pt} REITs, mkt cap {mcr} | Tickers: {', '.join(tickers)}
PAY-FOR-PERFORMANCE: Compare the compensation quartile vs returns quartile. If comp quartile is below returns quartile, advocate for the management team. Provide a clear directional recommendation.{en}
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

def gen_full(co_d, filt, ret_data):
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    cn = co_d['company_name'].iloc[0]; tk = co_d['ticker'].iloc[0]; pt = co_d['property_type'].iloc[0]; mc = co_d['market_cap'].iloc[0]
    hq = f"{co_d['hq_city'].iloc[0]}, {co_d['hq_state'].iloc[0]}"
    ea = is_ext_advised(co_d, filt); ps = get_peer_stats(filt)
    n_co, mcr, tickers = peer_context_str(filt, pt)
    en = "\nCRITICAL: Externally advised." if ea else ""
    esecs = []
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; ip = detect_partial(rw, filt)
        pp = ps[ps['position']==rw['position']]; t = rw['total_comp'] if pd.notna(rw['total_comp']) else 0
        tp = percentile_rank(rw['total_comp'], pp['total_comp']); mix = comp_mix_str(rw); pm = peer_mix_median(ps, rw['position'])
        fl = []
        if ie: fl.append('EXT')
        if ip: fl.append('PARTIAL YR')
        fs = f" [{','.join(fl)}]" if fl else ""
        esecs.append(f"  {rw['first_name']} {rw['last_name']}, {POSITION_DISPLAY.get(rw['position'],rw['position'])}{fs}: Total ${t:,.0f} ({ordinal(tp)} pctl, {quartile_label(tp)}) | Mix: {mix} | Peer mix: {pm}")
    rl = ""
    ceo = co_d[co_d['position']=='CEO']; cfo = co_d[co_d['position']=='CFO']
    if not ceo.empty and not cfo.empty and pd.notna(cfo['total_comp'].iloc[0]) and cfo['total_comp'].iloc[0] > 0:
        r2 = ceo['total_comp'].iloc[0]/cfo['total_comp'].iloc[0]
        pce = ps[ps['position']=='CEO']['total_comp'].dropna().median()
        pcf = ps[ps['position']=='CFO']['total_comp'].dropna().median()
        rl = f"CEO/CFO Ratio: {r2:.1f}x (peer: {pce/pcf:.1f}x)" if pcf > 0 else ""
    r = ret_data.get(tk,{}); vnq = ret_data.get(REIT_INDEX_TICKER,{})
    p1 = [ret_data.get(t,{}).get('return_1y') for t in tickers if ret_data.get(t,{}).get('return_1y') is not None]
    p3 = [ret_data.get(t,{}).get('return_3y') for t in tickers if ret_data.get(t,{}).get('return_3y') is not None]
    ret_pct = percentile_rank(r.get('return_1y'), pd.Series(p1)) if r.get('return_1y') is not None and p1 else None
    tb = co_d['total_comp'].sum(); pcos = ps.groupby('ticker')['total_comp'].sum(); bp = percentile_rank(tb, pcos)
    prompt = f"""REIT compensation analysis (~500-600 words). You are advising this management team.
{cn} ({tk}) | {pt} | {co_d['reit_type'].iloc[0]} | HQ: {hq} | Mkt Cap ${mc/1e9:.2f}B
EXECUTIVES:\n{chr(10).join(esecs)}
{rl}
Budget: ${tb:,.0f} ({ordinal(bp)} pctl vs {len(pcos)} peers)
FY{FY_YEAR} Returns: {tk} 1-Yr {fmt_return(r.get('return_1y'))} ({ordinal(ret_pct)} pctl, {quartile_label(ret_pct)}) | 3-Yr {fmt_return(r.get('return_3y'))}
{pt} Avg: 1-Yr {fmt_return(np.mean(p1) if p1 else None)} | 3-Yr {fmt_return(np.mean(p3) if p3 else None)}
FTSE Nareit: 1-Yr {fmt_return(vnq.get('return_1y'))} | 3-Yr {fmt_return(vnq.get('return_3y'))}
Peers: {n_co} {pt} REITs, mkt cap {mcr} | Tickers: {', '.join(tickers)}
Sections (flowing paragraphs, blank line between):
1. Company overview, peer group with company names (2-3 sent)
2. Each exec: positioning, comp mix vs peer mix, assessment (2-3 sent each). IMPORTANT: If any executive is flagged as [Partial Yr], explicitly note that their compensation reflects a partial year of service and should not be compared at face value to full-year peers. Recommend the board evaluate their annualized run-rate when setting go-forward compensation.
3. Overall comp mix philosophy (2-3 sent)
4. CEO/CFO ratio (1-2 sent)
5. PAY-FOR-PERFORMANCE: Compare comp quartile vs returns quartile. Advocate for management where data supports it. Provide clear recommendations. (3-4 sent)
6. Summary with peer group disclosure (2-3 sent, list all peer tickers)
DISCLAIMER at end: "Note: This analysis is based on SEC DEF 14A proxy data and does not account for employment agreements, one-time awards, or unvested equity not yet reported."{en}
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=1400, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

# ============================================================
# PDF (enhanced with percentile cards and peer tables)
# ============================================================
def make_pdf(cn, tk, report_text, co_d, ret_data, filt):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch, leftMargin=0.85*inch, rightMargin=0.85*inch)
    story = []
    ts = ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#0f172a'), spaceAfter=4)
    ss = ParagraphStyle('S', fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#475569'), spaceAfter=16)
    bs = ParagraphStyle('B', fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor('#1e293b'), spaceAfter=10)
    ds = ParagraphStyle('D', fontName='Helvetica', fontSize=7, textColor=colors.HexColor('#94a3b8'), spaceAfter=3)
    hs = ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#0d9488'), spaceAfter=4, spaceBefore=10)
    prs_h = ParagraphStyle('PRH', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#0f172a'), spaceAfter=4, spaceBefore=8)
    story.append(Paragraph("Velarion Company Intelligence", ts))
    story.append(Paragraph(f"REIT Compensation Analysis: {cn} ({tk})", ss))
    story.append(Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y')} | FY{FY_YEAR} Proxy Data | Returns through Dec 31, {FY_YEAR}", ds))
    story.append(Spacer(1, 8))
    mc = co_d['market_cap'].iloc[0]; pt = co_d['property_type'].iloc[0]; hq = f"{co_d['hq_city'].iloc[0]}, {co_d['hq_state'].iloc[0]}"
    r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    info = [['Company', cn, 'Property Type', pt], ['Ticker', tk, 'Market Cap', fmt_mcap(mc)],
            ['HQ', hq, 'REIT Type', co_d['reit_type'].iloc[0]],
            [f'1-Yr Return (FY{FY_YEAR})', fmt_return(r.get('return_1y')), 'FTSE Nareit 1-Yr', fmt_return(vnq.get('return_1y'))],
            ['3-Yr Return', fmt_return(r.get('return_3y')), 'FTSE Nareit 3-Yr', fmt_return(vnq.get('return_3y'))]]
    it = Table(info, colWidths=[1.3*inch, 2.2*inch, 1.2*inch, 2.2*inch])
    it.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),8.5),
        ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),
        ('TEXTCOLOR',(0,0),(0,-1),colors.HexColor('#475569')),('TEXTCOLOR',(2,0),(2,-1),colors.HexColor('#475569')),
        ('BOTTOMPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),3),
        ('LINEBELOW',(0,-1),(-1,-1),0.5,colors.HexColor('#e2e8f0'))]))
    story.append(it); story.append(Spacer(1, 10))
    ps = get_peer_stats(filt); prp = ps[ps['property_type'] == pt]
    n_co, mcr, peer_tickers = peer_context_str(filt, pt)
    story.append(Paragraph("PEER GROUP BENCHMARKS", hs))
    story.append(Paragraph(f"Peer group: {n_co} {pt} REITs, market cap {mcr}", ds))
    for pos in ['CEO','CFO','CIO','GC']:
        pps = prp[prp['position']==pos]['total_comp'].dropna()
        if len(pps) >= 2:
            story.append(Paragraph(f"{POSITION_DISPLAY.get(pos,pos)} Total Comp (n={len(pps)}): Median {fmt_dollars(pps.median())} | 25th {fmt_dollars(pps.quantile(0.25))} | 75th {fmt_dollars(pps.quantile(0.75))}", bs))
    story.append(Spacer(1, 6))
    # Exec summary table
    story.append(Paragraph("EXECUTIVE COMPENSATION SUMMARY", hs))
    td = [['Name', 'Position', 'Base Salary', 'Cash Bonus', 'Non-Cash Equity', 'Total Comp']]
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; ip = detect_partial(rw, filt)
        fl = []
        if ie: fl.append('*')
        if ip: fl.append('^')
        td.append([f"{rw['first_name']} {rw['last_name']}{''.join(fl)}", POSITION_DISPLAY.get(rw['position'],rw['position']),
            fmt_dollars(rw['base_salary'], ext_managed=ie), fmt_dollars(rw['cash_bonus_incentive'], ext_managed=ie),
            fmt_dollars(rw['stock_based_comp'], ext_managed=ie), fmt_dollars(rw['total_comp'], ext_managed=ie)])
    ct = Table(td, colWidths=[1.6*inch, 0.6*inch, 0.95*inch, 0.95*inch, 0.95*inch, 0.95*inch])
    ct.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8.5),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f0f9ff')),('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#475569')),
        ('ALIGN',(2,0),(-1,-1),'RIGHT'),('BOTTOMPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),
        ('LINEBELOW',(0,0),(-1,0),0.5,colors.HexColor('#cbd5e1')),('LINEBELOW',(0,-1),(-1,-1),0.5,colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f8fafc')])]))
    story.append(ct)
    footnotes = []
    if (co_d['comp_source']=='external_manager').any(): footnotes.append("* Externally managed")
    if any(detect_partial(rw, filt) for _, rw in co_d.iterrows()): footnotes.append("^ Partial-year hire (estimated)")
    for fn in footnotes: story.append(Paragraph(fn, ds))
    story.append(Spacer(1, 8))
    # Percentile rankings
    story.append(Paragraph("PERCENTILE RANKINGS", hs))
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; pos = rw['position']
        pd_name = POSITION_DISPLAY.get(pos, pos)
        pp = prp[prp['position']==pos]
        fl = []
        if ie: fl.append('Ext')
        if detect_partial(rw, filt): fl.append('Partial Yr')
        fs = f" [{', '.join(fl)}]" if fl else ""
        story.append(Paragraph(f"{rw['first_name']} {rw['last_name']} - {pd_name}{fs} | Mix: {comp_mix_str(rw)}", prs_h))
        pct_row = []
        for comp_f, comp_l in [('base_salary','Salary'),('cash_bonus_incentive','Cash Bonus'),('stock_based_comp','Equity'),('total_comp','Total Comp')]:
            v = rw[comp_f]; pct = percentile_rank(v, pp[comp_f]) if not ie else None
            med = pp[comp_f].median() if len(pp[comp_f].dropna()) > 0 else None
            n_p = len(pp[comp_f].dropna())
            pct_str = f"{ordinal(pct)} pctl" if pct is not None else ("EX-MGD" if ie else "N/A")
            pct_row.append([comp_l, fmt_dollars(v, ext_managed=ie), pct_str, fmt_dollars(med) if med else "\u2014", str(n_p)])
        pt_table = [['Component', 'Amount', 'Percentile', 'Peer Median', 'n']] + pct_row
        pt_t = Table(pt_table, colWidths=[1*inch, 1*inch, 1*inch, 1*inch, 0.5*inch])
        pt_t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7.5),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f0f9ff')),
            ('ALIGN',(1,0),(-1,-1),'RIGHT'),('BOTTOMPADDING',(0,0),(-1,-1),2),('TOPPADDING',(0,0),(-1,-1),2),
            ('LINEBELOW',(0,0),(-1,0),0.5,colors.HexColor('#cbd5e1'))]))
        story.append(pt_t)
    story.append(Spacer(1, 8))
    # Peer tables
    story.append(Paragraph("PEER COMPARISON TABLES", hs))
    for pos in ['CEO','CFO','COO','CIO','GC']:
        pos_peers = prp[prp['position']==pos].sort_values('total_comp', ascending=False)
        if pos_peers.empty: continue
        story.append(Paragraph(f"{POSITION_DISPLAY.get(pos,pos)} Rankings ({len(pos_peers)} peers)", prs_h))
        peer_rows = [['Rank','Ticker','Executive','Salary','Bonus','Equity','Total','Mkt Cap']]
        for i, (_, pr) in enumerate(pos_peers.iterrows()):
            peer_rows.append([str(i+1), pr['ticker'], f"{pr['first_name']} {pr['last_name']}",
                fmt_dollars(pr['base_salary']), fmt_dollars(pr['cash_bonus_incentive']),
                fmt_dollars(pr['stock_based_comp']), fmt_dollars(pr['total_comp']), fmt_mcap(pr['market_cap'])])
        peer_t = Table(peer_rows, colWidths=[0.35*inch, 0.45*inch, 1.2*inch, 0.65*inch, 0.65*inch, 0.65*inch, 0.7*inch, 0.65*inch])
        style_cmds = [('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f0f9ff')),
            ('ALIGN',(3,0),(-1,-1),'RIGHT'),('BOTTOMPADDING',(0,0),(-1,-1),2),('TOPPADDING',(0,0),(-1,-1),2),
            ('LINEBELOW',(0,0),(-1,0),0.5,colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f8fafc')])]
        for i, (_, pr) in enumerate(pos_peers.iterrows()):
            if pr['ticker'] == tk:
                style_cmds.append(('BACKGROUND',(0,i+1),(-1,i+1),colors.HexColor('#dbeafe')))
                style_cmds.append(('FONTNAME',(0,i+1),(-1,i+1),'Helvetica-Bold'))
        peer_t.setStyle(TableStyle(style_cmds))
        story.append(peer_t); story.append(Spacer(1, 4))
    story.append(Spacer(1, 12))
    story.append(Paragraph("COMPENSATION ANALYSIS", hs))
    pdf_text = report_text.replace('&#36;', '$')
    pdf_text = pdf_text.replace('<br><br>', '\n\n').replace('<br>', '\n')
    for para in pdf_text.split('\n\n'):
        para = para.strip()
        if para: story.append(Paragraph(para, bs))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Velarion Company Intelligence | velarion.ai", ds))
    story.append(Paragraph(f"SEC DEF 14A | FY{FY_YEAR} | Stock comp per ASC Topic 718 | Returns: Yahoo Finance (VNQ proxy) through Dec 31, {FY_YEAR}", ds))
    story.append(Paragraph("For institutional use only. Not investment advice.", ds))
    story.append(Paragraph(f"Peer group ({len(peer_tickers)} companies): {', '.join(peer_tickers)}", ds))
    doc.build(story); buf.seek(0); return buf

# ============================================================
# LOAD
# ============================================================
df = load_data()
if df.empty: st.error("No data."); st.stop()
all_tickers = list(df['ticker'].unique())
ret_data = load_total_returns(all_tickers)
co_labels = {clabel(t, df[df['ticker']==t]['company_name'].iloc[0]): t for t in sorted(df['ticker'].unique())}
co_opts = list(co_labels.keys())
all_props = sorted(df['property_type'].dropna().unique())
PLACEHOLDER = "-- Select your company --"

# HEADER
st.markdown('<div class="main-header"><h1>Velarion Company Intelligence</h1><p>REIT Executive Compensation Benchmarking \u2014 FY2024 Proxy Data</p></div>', unsafe_allow_html=True)
st.markdown('<div class="intro-text">Explore executive compensation across 62 publicly traded REITs. Customize your peer group in the sidebar, then navigate the tabs for benchmarking, AI-powered analysis, and downloadable reports.</div>', unsafe_allow_html=True)

# AUTO-FILTER: If Tab 0 set a pending property type, apply it before sidebar renders
if '_pending_pt' in st.session_state:
    pending_pt = st.session_state.pop('_pending_pt')
    st.session_state['pt_all'] = False
    st.session_state['pt_sel'] = [pending_pt]

# Detect current auto-filter state for sidebar display
auto_pt = None
if 'selected_company' in st.session_state and st.session_state.get('selected_company') != PLACEHOLDER:
    sel_co_label = st.session_state['selected_company']
    if sel_co_label in co_labels:
        sel_co_tk = co_labels[sel_co_label]
        sel_co_data = df[df['ticker'] == sel_co_tk]
        if not sel_co_data.empty:
            auto_pt = sel_co_data['property_type'].iloc[0]
        # Sync Tab 3 (Company View) — only if selection came from Tab 0
        if st.session_state.get('_sync_source') == 'tab0':
            if sel_co_label in co_opts:
                st.session_state['cv_co'] = sel_co_label
            st.session_state['_sync_source'] = None  # consume the flag
        # Sync Tab 0 (How Do I Stack Up) — only if selection came from Tab 3
        if st.session_state.get('_sync_source') == 'tab3':
            lk_opts_sync = [PLACEHOLDER] + co_opts
            if sel_co_label in lk_opts_sync:
                st.session_state['lookup_co'] = sel_co_label
            st.session_state['_sync_source'] = None

# SIDEBAR
with st.sidebar:
    st.markdown("## Peer Group Filters")
    if auto_pt:
        st.markdown(f'<div class="filter-note">\U0001F3AF Filtered to <strong>{auto_pt}</strong> peers. Adjust below to customize.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="filter-note">\U0001F4A1 Select a company to auto-set filters, or customize below.</div>', unsafe_allow_html=True)
    st.markdown("### Property Type")
    if 'pt_all' not in st.session_state:
        st.session_state['pt_all'] = True
    all_pt = st.checkbox("Select All", key="pt_all")
    if 'pt_sel' not in st.session_state:
        st.session_state['pt_sel'] = all_props if all_pt else []
    sel_prop = st.multiselect("Property type", all_props, label_visibility="collapsed", key="pt_sel")
    st.markdown("### Position")
    positions = FILTER_POSITIONS
    all_pos_chk = st.checkbox("Select All", value=True, key="pos_all")
    sel_pos = st.multiselect("Position", positions, default=positions if all_pos_chk else [], format_func=lambda x: POSITION_FILTER_LABEL.get(x,x), label_visibility="collapsed", key="pos_sel")
    st.markdown("### Market Cap Range")
    # Non-linear scale: fine-grained $0-25B, coarser $25-50B+
    mcap_breakpoints = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.5, 10.0, 12.5, 15.0, 17.5, 20.0, 25.0, 30.0, 40.0, 50.0]
    mcap_labels = {v: f"${v:.2f}B" if v < 50 else ">$50B" for v in mcap_breakpoints}
    mcap_min, mcap_max = st.select_slider("Mkt cap",
        options=mcap_breakpoints,
        value=(0.0, 50.0),
        format_func=lambda x: ">$50B" if x >= 50.0 else f"${x:.1f}B" if x >= 1.0 else f"${x:.2f}B",
        label_visibility="collapsed")
    st.markdown("### Region")
    regions = sorted(df['geographic_region'].dropna().unique())
    all_reg_chk = st.checkbox("Select All", value=True, key="reg_all")
    sel_reg = st.multiselect("Region", regions, default=regions if all_reg_chk else [], label_visibility="collapsed", key="reg_sel")

# FILTER
filt = df.copy()
filt = filt[filt['property_type'].isin(sel_prop)]
filt_no_pos = filt.copy()  # Peer set without position filter — for company-specific views
filt = filt[filt['position'].isin(sel_pos)]
if mcap_max >= 50.0:
    filt = filt[(filt['market_cap'] >= mcap_min*1e9) | (filt['market_cap'].isna())]
    filt_no_pos = filt_no_pos[(filt_no_pos['market_cap'] >= mcap_min*1e9) | (filt_no_pos['market_cap'].isna())]
else:
    filt = filt[((filt['market_cap'] >= mcap_min*1e9) & (filt['market_cap'] <= mcap_max*1e9)) | (filt['market_cap'].isna())]
    filt_no_pos = filt_no_pos[((filt_no_pos['market_cap'] >= mcap_min*1e9) & (filt_no_pos['market_cap'] <= mcap_max*1e9)) | (filt_no_pos['market_cap'].isna())]
filt = filt[filt['geographic_region'].isin(sel_reg)]
filt_no_pos = filt_no_pos[filt_no_pos['geographic_region'].isin(sel_reg)]
peer_stats_df = get_peer_stats(filt)

# METRICS — context-aware: show full universe until a company is selected, then show peer group
c1,c2,c3,c4,c5 = st.columns(5)
pd_str = ', '.join([POSITION_FILTER_LABEL.get(p,p) for p in sel_pos if POSITION_FILTER_LABEL.get(p,p)])
cv_selected = st.session_state.get('cv_co', PLACEHOLDER)
if cv_selected and cv_selected != PLACEHOLDER and cv_selected in co_labels:
    # Company selected — show filtered peer group context
    cv_tk = co_labels[cv_selected]
    cv_pt = df[df['ticker']==cv_tk]['property_type'].iloc[0] if not df[df['ticker']==cv_tk].empty else ""
    with c1: st.markdown(f'<div class="metric-card"><div class="label">Peer Companies</div><div class="value">{filt["ticker"].nunique()}</div><div class="sub">{cv_pt} REITs</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="label">Executives</div><div class="value">{len(filt)}</div><div class="sub">{pd_str}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="label">Median Salary</div><div class="value">{fmt_dollars(peer_stats_df["base_salary"].median())}</div><div class="sub">peer group</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="label">Median Total Comp</div><div class="value">{fmt_dollars(peer_stats_df["total_comp"].median())}</div><div class="sub">peer group</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><div class="label">Median Mkt Cap</div><div class="value">{fmt_mcap(filt["market_cap"].median())}</div><div class="sub">peer group</div></div>', unsafe_allow_html=True)
else:
    # No company selected — show full universe
    with c1: st.markdown(f'<div class="metric-card"><div class="label">Companies</div><div class="value">{filt["ticker"].nunique()}</div><div class="sub">in universe</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="label">Executives</div><div class="value">{len(filt)}</div><div class="sub">{pd_str}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="label">Median Salary</div><div class="value">{fmt_dollars(peer_stats_df["base_salary"].median())}</div><div class="sub">all REITs</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="label">Median Total Comp</div><div class="value">{fmt_dollars(peer_stats_df["total_comp"].median())}</div><div class="sub">all REITs</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><div class="label">Median Mkt Cap</div><div class="value">{fmt_mcap(filt["market_cap"].median())}</div><div class="sub">all REITs</div></div>', unsafe_allow_html=True)
st.markdown("")

# TABS
tab3, tab0, tab4 = st.tabs(["\U0001F3E2 Company View", "\U0001F50D How Do I Stack Up?", "\U0001F3C6 League Tables"])

# ---- TAB 0 ----
with tab0:
    st.markdown('<div class="lookup-box"><h2>How Do I Stack Up?</h2><p>Select your company. Filters will auto-set to your property type peers.</p>', unsafe_allow_html=True)
    lk_opts = [PLACEHOLDER] + co_opts
    # Sync: if a company was selected on another tab, pre-set the widget key
    if 'selected_company' in st.session_state and st.session_state.get('selected_company') in co_opts:
        st.session_state['lookup_co'] = st.session_state['selected_company']
    lk = st.selectbox("co", lk_opts, key="lookup_co", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    if lk and lk != PLACEHOLDER:
        # If company changed, set a pending filter flag and rerun
        prev_sel = st.session_state.get('selected_company')
        st.session_state['selected_company'] = lk
        if prev_sel != lk:
            st.session_state['_sync_source'] = 'tab0'
            ltk_tmp = co_labels[lk]; lcd_tmp = df[df['ticker']==ltk_tmp]
            if not lcd_tmp.empty:
                new_pt = lcd_tmp['property_type'].iloc[0]
                st.session_state['_pending_pt'] = new_pt
                st.rerun()
        ltk = co_labels[lk]; lcd = df[df['ticker']==ltk]
        if not lcd.empty:
            cn = lcd['company_name'].iloc[0]; mc = lcd['market_cap'].iloc[0]
            hq = f"{lcd['hq_city'].iloc[0]}, {lcd['hq_state'].iloc[0]}"; pt = lcd['property_type'].iloc[0]
            lr = ret_data.get(ltk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
            n_co, mcr, peer_tks = peer_context_str(filt_no_pos, pt)
            auto_peers = get_peer_stats(filt_no_pos)
            st.markdown(f"### {cn} ({ltk})")
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("HQ", hq); m2.metric("Property Type", pt); m3.metric("Market Cap", fmt_mcap(mc))
            m4.metric(f"1-Yr Return (FY{FY_YEAR})", fmt_return(lr.get('return_1y')))
            # Sector returns row
            if lr:
                ppt = filt_no_pos[filt_no_pos['property_type']==pt]['ticker'].unique()
                p1a = [ret_data.get(t,{}).get('return_1y') for t in ppt if ret_data.get(t,{}).get('return_1y') is not None]
                rc1,rc2,rc3,rc4 = st.columns(4)
                rc1.metric(f"{ltk} 1-Yr (FY{FY_YEAR})", fmt_return(lr.get('return_1y')))
                rc2.metric(f"{ltk} 3-Yr", fmt_return(lr.get('return_3y')))
                rc3.metric(f"{pt} Avg 1-Yr", fmt_return(np.mean(p1a) if p1a else None))
                rc4.metric("FTSE Nareit 1-Yr", fmt_return(vnq.get('return_1y')))
            st.markdown(f"<div style='font-size:1.0rem;color:#475569;margin:0.5rem 0;'>Compared to <strong>{n_co} {pt} REITs</strong> in the {mcr} market cap range ({', '.join(peer_tks)})</div>", unsafe_allow_html=True)
            ea = is_ext_advised(lcd, df)
            if ea: st.markdown(f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:0.6rem 1rem;font-size:0.83rem;color:#92400e;margin:0.5rem 0;">\u26A0\uFE0F {get_ext_note(lcd)}</div>', unsafe_allow_html=True)
            # Print button
            components.html('<button onclick="window.parent.print()" style="background:#475569;color:white;border:none;border-radius:6px;padding:5px 14px;font-size:0.75rem;font-weight:600;cursor:pointer;float:right;">\U0001F5A8 Print This Page</button>', height=35)
            st.markdown("---")
            cur_fp0 = filter_fingerprint(filt_no_pos)
            btn_a, btn_b = st.columns(2)
            with btn_a:
                if st.button("\U0001F4CA Generate Summary Analysis", key="lookup_sum"):
                    with st.spinner("Analyzing..."):
                        st.session_state['lk_sum'] = gen_analysis(lcd, filt_no_pos, ret_data)
                        st.session_state['lk_sum_tk'] = ltk
                        st.session_state['fp_lk_sum'] = cur_fp0
            with btn_b:
                if st.button("\U0001F4CB Generate Full Compensation Analysis", key="lookup_rpt"):
                    with st.spinner("Generating..."):
                        st.session_state['lk_rpt'] = gen_full(lcd, filt_no_pos, ret_data)
                        st.session_state['lk_tk'] = ltk
                        st.session_state['fp_lk_rpt'] = cur_fp0
            # Display Summary
            if st.session_state.get('lk_sum_tk') == ltk and st.session_state.get('lk_sum'):
                if st.session_state.get('fp_lk_sum') != cur_fp0:
                    st.markdown(STALE_WARNING, unsafe_allow_html=True)
                st.markdown(f'<div class="ai-narrative"><div class="ai-label">\U0001F4CA Compensation & Performance Summary</div>{st.session_state["lk_sum"]}</div>', unsafe_allow_html=True)
                if st.button("\u2715 Close Summary", key="close_lk_sum"):
                    del st.session_state['lk_sum']
                    st.rerun()
            # Display Full Report
            if st.session_state.get('lk_tk') == ltk and st.session_state.get('lk_rpt'):
                if st.session_state.get('fp_lk_rpt') != cur_fp0:
                    st.markdown(STALE_WARNING, unsafe_allow_html=True)
                rt = st.session_state['lk_rpt']
                st.markdown(f'<div class="ai-report"><div class="ai-label">\U0001F4CB Compensation Analysis \u2014 {cn}</div>{rt}</div>', unsafe_allow_html=True)
                cl0, dl0 = st.columns([1,4])
                with cl0:
                    if st.button("\u2715 Close Report", key="close_lk_rpt"):
                        del st.session_state['lk_rpt']
                        st.rerun()
                with dl0:
                    try:
                        pdf = make_pdf(cn, ltk, rt, lcd, ret_data, filt_no_pos)
                        st.download_button("\U0001F4E5 Download PDF", data=pdf, file_name=f"Velarion_{ltk}_Analysis.pdf", mime="application/pdf", key="lk_pdf")
                    except Exception: pass
            st.markdown("---")
            for idx, (_, er) in enumerate(sort_by_position(lcd).iterrows()):
                # Skip former executives
                if 'former' in str(er.get('title', '')).lower():
                    continue
                ie = er['comp_source']=='external_manager'; ip = detect_partial(er, df); pos = er['position']; pd2 = POSITION_DISPLAY.get(pos, pos)
                badges = ''
                if ie: badges += ' <span class="ext-badge">EXT. MANAGED</span>'
                if ip: badges += ' <span class="partial-year">PARTIAL YEAR</span>'
                pos_tag = f" \u2014 {pd2}" if pd2 else ""
                st.markdown(f"**{er['first_name']} {er['last_name']}**{pos_tag}{badges} | {er['title']}", unsafe_allow_html=True)
                if ie:
                    # Ext managed: show flat comp data only, no percentiles/analysis
                    cols = st.columns(4)
                    for i, (f, l) in enumerate([('base_salary','Base Salary'),('cash_bonus_incentive','Cash Bonus/Incentive'),('stock_based_comp','Non-Cash Equity \u00B9'),('total_comp','Total Compensation')]):
                        v = er[f]
                        with cols[i]: st.markdown(render_pct_card(v, None, l, is_ext=True), unsafe_allow_html=True)
                    with st.expander(f"\U0001F465 View {pd2 if pd2 else 'Peer'} Comparison"):
                        render_peer_table(er, filt_no_pos, pos)
                    st.markdown("")
                    continue
                peers = auto_peers[auto_peers['position']==pos]
                n_pos = len(peers[peers['total_comp'].notna()])
                cols = st.columns(4)
                for i, (f, l) in enumerate([('base_salary','Base Salary'),('cash_bonus_incentive','Cash Bonus/Incentive'),('stock_based_comp','Non-Cash Equity \u00B9'),('total_comp','Total Compensation')]):
                    v = er[f]; p = percentile_rank(v, peers[f]); med = peers[f].median(); n = len(peers[f].dropna())
                    with cols[i]: st.markdown(render_pct_card(v, p, l, med=med, n=n, is_ext=ie, is_partial=ip), unsafe_allow_html=True)
                if n_pos < 5:
                    pos_label_warn = pd2 if pd2 else 'NEO'
                    render_widen_warning(n_pos, pos_label_warn, pt, f"{ltk}_{pos}")
                # Per-exec analysis button
                nk = f"n_{ltk}_{er['position']}_{er['last_name']}_{idx}"
                if nk not in st.session_state: st.session_state[nk] = None
                pos_btn_label = pd2 if pd2 else er['first_name'] + ' ' + er['last_name']
                if st.button(f"\U0001F4CA Generate {pos_btn_label} Analysis", key=f"b_{nk}"):
                    with st.spinner("Generating..."):
                        st.session_state[nk] = gen_exec(er, filt_no_pos, df, ret_data, filt_no_pos)
                        st.session_state[f"fp_{nk}"] = cur_fp0
                if st.session_state[nk]:
                    if st.session_state.get(f"fp_{nk}") != cur_fp0:
                        st.markdown(STALE_WARNING, unsafe_allow_html=True)
                    st.markdown(f'<div class="ai-narrative"><div class="ai-label">\U0001F4CA {pos_btn_label} Compensation Analysis</div>{st.session_state[nk]}</div>', unsafe_allow_html=True)
                    if st.button(f"\u2715 Close {pos_btn_label} Analysis", key=f"close_{nk}"):
                        st.session_state[nk] = None
                        st.rerun()
                with st.expander(f"\U0001F465 View {pd2 if pd2 else 'Peer'} Comparison"):
                    render_peer_table(er, filt_no_pos, pos)
                st.markdown("")
            st.markdown(f'<div class="footnote">\u00B9 Grant date fair value per ASC Topic 718.</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="source-note">Returns: Yahoo Finance (VNQ proxy), through Dec 31, {FY_YEAR}</div>', unsafe_allow_html=True)

# ---- TAB 3 ----
with tab3:
    st.markdown("#### Company Compensation Overview")
    cv_opts = [PLACEHOLDER] + co_opts
    cv_selected_val = st.session_state.get('cv_co', PLACEHOLDER)
    if not cv_selected_val or cv_selected_val == PLACEHOLDER:
        st.markdown('<div class="tab-instruction">\U0001F4A1 Select a company to view executive compensation and generate AI-powered analysis.</div>', unsafe_allow_html=True)
    sel3 = st.selectbox("cv", cv_opts, key="cv_co", label_visibility="collapsed")
    if sel3 and sel3 != PLACEHOLDER:
        # If company changed, sync sidebar filters and rerun
        prev_cv = st.session_state.get('_prev_cv')
        if prev_cv != sel3:
            st.session_state['_prev_cv'] = sel3
            st.session_state['selected_company'] = sel3
            st.session_state['_sync_source'] = 'tab3'
            ltk_tmp = co_labels[sel3]; lcd_tmp = df[df['ticker']==ltk_tmp]
            if not lcd_tmp.empty:
                st.session_state['_pending_pt'] = lcd_tmp['property_type'].iloc[0]
                st.rerun()
        stk3 = co_labels[sel3]; cd3 = df[df['ticker']==stk3]
        if not cd3.empty:
            cn3 = cd3['company_name'].iloc[0]; pt3 = cd3['property_type'].iloc[0]
            st.markdown(f"### {cn3} ({stk3})")
            c1,c2,c3 = st.columns(3)
            c1.metric("HQ", f"{cd3['hq_city'].iloc[0]}, {cd3['hq_state'].iloc[0]}"); c2.metric("Property Type", pt3); c3.metric("Market Cap", fmt_mcap(cd3['market_cap'].iloc[0]))
            cr3 = ret_data.get(stk3, {}); vnq3 = ret_data.get(REIT_INDEX_TICKER, {})
            if cr3:
                r1,r2,r3,r4 = st.columns(4)
                r1.metric(f"{stk3} 1-Yr (FY{FY_YEAR})", fmt_return(cr3.get('return_1y')))
                r2.metric(f"{stk3} 3-Yr", fmt_return(cr3.get('return_3y')))
                r3.metric("FTSE Nareit 1-Yr", fmt_return(vnq3.get('return_1y')))
                r4.metric("FTSE Nareit 3-Yr", fmt_return(vnq3.get('return_3y')))
            ea3 = is_ext_advised(cd3, df)
            if ea3: st.markdown(f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:0.6rem 1rem;font-size:0.83rem;color:#92400e;margin:0.5rem 0;">\u26A0\uFE0F {get_ext_note(cd3)}</div>', unsafe_allow_html=True)
            # Print button
            components.html('<button onclick="window.parent.print()" style="background:#475569;color:white;border:none;border-radius:6px;padding:5px 14px;font-size:0.75rem;font-weight:600;cursor:pointer;float:right;">\U0001F5A8 Print This Page</button>', height=35)
            st.markdown("---")
            for idx, (_, rw) in enumerate(sort_by_position(cd3).iterrows()):
                ie = rw['comp_source']=='external_manager'; pd4 = POSITION_DISPLAY.get(rw['position'], rw['position'])
                sb = "\U0001F517" if ie else "\U0001F3E2"
                badges = ""
                if ie: badges += "<br><span class='ext-badge'>EXT. MANAGED</span>"
                if detect_partial(rw, df): badges += "<br><span class='partial-year'>PARTIAL YEAR</span>"
                pos_tag = f" \u2014 {pd4}" if pd4 else ""
                cols = st.columns([2,1,1,1,1])
                cols[0].markdown(f"**{sb} {rw['first_name']} {rw['last_name']}**{pos_tag}<br><span style='color:#64748b;font-size:0.78rem'>{rw['title']}</span>{badges}", unsafe_allow_html=True)
                cols[1].metric("Base Salary", fmt_dollars(rw['base_salary'], ext_managed=ie))
                cols[2].metric("Cash Bonus", fmt_dollars(rw['cash_bonus_incentive'], ext_managed=ie))
                cols[3].metric("Non-Cash Equity \u00B9", fmt_dollars(rw['stock_based_comp'], ext_managed=ie))
                cols[4].metric("Total Comp", fmt_dollars(rw['total_comp'], ext_managed=ie))
            st.markdown(f'<div class="footnote">\u00B9 Grant date fair value per ASC Topic 718.</div>', unsafe_allow_html=True)

# ---- TAB 4 ----
with tab4:
    st.markdown("#### Property Type League Tables")
    st.markdown('<div class="tab-instruction">\U0001F4A1 Compensation rankings by property type. Externally managed excluded.</div>', unsafe_allow_html=True)
    active_props = sorted([p for p in filt['property_type'].dropna().unique()])
    if not active_props: active_props = all_props
    is_combined = len(active_props) > 1
    if is_combined:
        combined_label = ' & '.join(active_props)
        lt_options = [combined_label]
    else:
        lt_options = active_props
        combined_label = None
    lp1, lp2, lp3 = st.columns([2,1,2])
    with lp1: lprop = st.selectbox("Property Type", lt_options, key="lt_prop")
    with lp2: lpos = st.selectbox("Position", FILTER_POSITIONS, format_func=lambda x: POSITION_FILTER_LABEL.get(x,x), key="lt_pos")
    # Auto-select highlighted company from active selection
    league_cos = sorted(filt[filt['comp_source']!='external_manager']['ticker'].unique())
    league_labels = {clabel(t, df[df['ticker']==t]['company_name'].iloc[0]): t for t in league_cos}
    hl_opts = ["None"] + list(league_labels.keys())
    # Auto-sync highlight from selected company, but allow manual override
    current_sel = st.session_state.get('selected_company', '')
    prev_synced = st.session_state.get('_lt_last_synced', '')
    if current_sel and current_sel != prev_synced and current_sel in hl_opts:
        st.session_state['lt_hl_company'] = current_sel
        st.session_state['_lt_last_synced'] = current_sel
    if 'lt_hl_company' not in st.session_state:
        st.session_state['lt_hl_company'] = "None"
    # If current highlight is no longer in the list (property type removed), reset
    if st.session_state['lt_hl_company'] not in hl_opts:
        st.session_state['lt_hl_company'] = "None"
    with lp3: highlight_co = st.selectbox("Highlight Company", hl_opts, index=hl_opts.index(st.session_state['lt_hl_company']), key="lt_hl_sel")
    st.session_state['lt_hl_company'] = highlight_co
    hl_tk = league_labels.get(highlight_co) if highlight_co != "None" else None
    ldf = filt[(filt['position']==lpos) & (filt['comp_source']!='external_manager')].copy()
    if not ldf.empty:
        ldf = ldf.sort_values('total_comp', ascending=False).reset_index(drop=True)
        ldf['_rank'] = range(1, len(ldf)+1)
        pos_label = POSITION_FILTER_LABEL.get(lpos, lpos)
        st.markdown(f"##### {lprop} \u2014 {pos_label} Rankings (FY{FY_YEAR})")
        components.html('<button onclick="window.parent.print()" style="background:#475569;color:white;border:none;border-radius:6px;padding:5px 14px;font-size:0.75rem;font-weight:600;cursor:pointer;float:right;">\U0001F5A8 Print This Page</button>', height=35)
        # Pin highlighted company to top
        if hl_tk and hl_tk in ldf['ticker'].values:
            hl_row = ldf[ldf['ticker']==hl_tk].iloc[0]; hl_rank = ldf[ldf['ticker']==hl_tk]['_rank'].iloc[0]
            hl_pct = percentile_rank(hl_row['total_comp'], ldf['total_comp'])
            hl_partial = detect_partial(hl_row, df)
            hl_badge = ' <span class="partial-year">PARTIAL YEAR</span>' if hl_partial else ''
            st.markdown(f'<div class="hl-row"><strong>\U0001F3AF {hl_row["company_name"]} ({hl_tk})</strong> \u2014 {hl_row["first_name"]} {hl_row["last_name"]} | #{hl_rank} of {len(ldf)} | {ordinal(hl_pct)} pctl | Total: <strong>{fmt_dollars(hl_row["total_comp"])}</strong>{hl_badge}</div>', unsafe_allow_html=True)
        lshow = pd.DataFrame()
        lshow['Rank'] = ldf['_rank'].values; lshow['Ticker'] = ldf['ticker'].values
        lshow['Company'] = ldf['company_name'].values
        lshow['Executive'] = ldf.apply(lambda r: f"{r['first_name']} {r['last_name']} ^" if detect_partial(r, df) else f"{r['first_name']} {r['last_name']}", axis=1).values
        lshow['Salary'] = ldf['base_salary'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) and x>0 else "\u2014").values
        lshow['Cash Bonus'] = ldf['cash_bonus_incentive'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) and x>0 else "\u2014").values
        lshow['Non-Cash Equity \u00B9'] = ldf['stock_based_comp'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) and x>0 else "\u2014").values
        lshow['Total Comp'] = ldf['total_comp'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) and x>0 else "\u2014").values
        lshow['Mkt Cap'] = ldf['market_cap'].apply(lambda x: f"${x/1e9:.2f}B" if pd.notna(x) else "\u2014").values
        if is_combined:
            lshow['Prop Type'] = ldf['property_type'].values
        lshow[f'1-Yr (FY{FY_YEAR})'] = ldf['ticker'].apply(lambda t: fmt_return(ret_data.get(t,{}).get('return_1y'))).values
        lshow['3-Yr'] = ldf['ticker'].apply(lambda t: fmt_return(ret_data.get(t,{}).get('return_3y'))).values
        # Pin highlighted company to top of table (keep original rank)
        if hl_tk and hl_tk in lshow['Ticker'].values:
            hl_mask = lshow['Ticker'] == hl_tk
            lshow = pd.concat([lshow[hl_mask], lshow[~hl_mask]]).reset_index(drop=True)
        st.dataframe(lshow, use_container_width=True, hide_index=True, height=400)
        # Gather return data for stats
        ret_1y_vals = pd.Series([ret_data.get(t,{}).get('return_1y') for t in ldf['ticker']], dtype=float).dropna()
        ret_3y_vals = pd.Series([ret_data.get(t,{}).get('return_3y') for t in ldf['ticker']], dtype=float).dropna()
        # Mean & Median stats per column
        st.markdown(f"##### {pos_label} Compensation Statistics ({len(ldf)} executives)")
        comp_cols = [('base_salary','Salary'),('cash_bonus_incentive','Cash Bonus'),('stock_based_comp','Non-Cash Equity'),('total_comp','Total Comp'),('market_cap','Market Cap')]
        mean_row = {'': 'Mean'}
        med_row = {'': 'Median'}
        for col, label in comp_cols:
            vals = ldf[col].dropna()
            if col != 'market_cap': vals = vals[vals > 0]
            if col == 'market_cap':
                mean_row[label] = f"${vals.mean()/1e9:.2f}B" if not vals.empty else "\u2014"
                med_row[label] = f"${vals.median()/1e9:.2f}B" if not vals.empty else "\u2014"
            else:
                mean_row[label] = fmt_dollars(vals.mean()) if not vals.empty else "\u2014"
                med_row[label] = fmt_dollars(vals.median()) if not vals.empty else "\u2014"
        mean_row['1-Yr Return'] = fmt_return(ret_1y_vals.mean()) if not ret_1y_vals.empty else "\u2014"
        med_row['1-Yr Return'] = fmt_return(ret_1y_vals.median()) if not ret_1y_vals.empty else "\u2014"
        mean_row['3-Yr Return'] = fmt_return(ret_3y_vals.mean()) if not ret_3y_vals.empty else "\u2014"
        med_row['3-Yr Return'] = fmt_return(ret_3y_vals.median()) if not ret_3y_vals.empty else "\u2014"
        summary_df = pd.DataFrame([mean_row, med_row])
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        # Percentile distribution table
        st.markdown("##### Percentile Distribution")
        pct_data = {'': ['25th Percentile', '50th Percentile', '75th Percentile']}
        for col, label in comp_cols:
            vals = ldf[col].dropna()
            if col != 'market_cap': vals = vals[vals > 0]
            if vals.empty:
                pct_data[label] = ['\u2014', '\u2014', '\u2014']
            elif col == 'market_cap':
                pct_data[label] = [f"${vals.quantile(0.25)/1e9:.2f}B", f"${vals.quantile(0.50)/1e9:.2f}B", f"${vals.quantile(0.75)/1e9:.2f}B"]
            else:
                pct_data[label] = [fmt_dollars(vals.quantile(0.25)), fmt_dollars(vals.quantile(0.50)), fmt_dollars(vals.quantile(0.75))]
        if not ret_1y_vals.empty:
            pct_data['1-Yr Return'] = [fmt_return(ret_1y_vals.quantile(0.25)), fmt_return(ret_1y_vals.quantile(0.50)), fmt_return(ret_1y_vals.quantile(0.75))]
        else:
            pct_data['1-Yr Return'] = ['\u2014', '\u2014', '\u2014']
        if not ret_3y_vals.empty:
            pct_data['3-Yr Return'] = [fmt_return(ret_3y_vals.quantile(0.25)), fmt_return(ret_3y_vals.quantile(0.50)), fmt_return(ret_3y_vals.quantile(0.75))]
        else:
            pct_data['3-Yr Return'] = ['\u2014', '\u2014', '\u2014']
        pct_df = pd.DataFrame(pct_data)
        st.dataframe(pct_df, use_container_width=True, hide_index=True)
        st.markdown(f'<div class="footnote">\u00B9 Grant date fair value per ASC Topic 718. | ^ = Estimated partial-year hire</div>', unsafe_allow_html=True)
    else:
        st.info(f"No {POSITION_FILTER_LABEL.get(lpos,lpos)} data for {lprop}.")

# FOOTER
st.markdown("---")
st.markdown(f'<div style="text-align:center;color:#94a3b8;font-size:0.78rem;padding:1rem 0;">Velarion Company Intelligence | SEC DEF 14A proxy filings | FY{FY_YEAR}<br>\u00A9 2026 Velarion.ai \u2014 For institutional use only. Not investment advice.</div>', unsafe_allow_html=True)
