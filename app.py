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
_LOGIN_SUPA_URL = "https://fhnffpgotkxxtwmwbizy.supabase.co"
_LOGIN_SUPA_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", "")

def _log_login(email):
    """Log login event to Supabase for tracking."""
    try:
        if not _LOGIN_SUPA_KEY:
            return
        sb = create_client(_LOGIN_SUPA_URL, _LOGIN_SUPA_KEY)
        sb.table("login_events").insert({
            "email": email.lower().strip(),
            "logged_in_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        import sys
        print(f"Login tracking error: {e}", file=sys.stderr)

def _log_page_view():
    """Log a page view event when login page is displayed (once per session)."""
    if st.session_state.get('_page_view_logged'):
        return
    try:
        if not _LOGIN_SUPA_KEY:
            return
        sb = create_client(_LOGIN_SUPA_URL, _LOGIN_SUPA_KEY)
        sb.table("login_events").insert({
            "email": "__page_view__",
            "logged_in_at": datetime.utcnow().isoformat()
        }).execute()
        st.session_state['_page_view_logged'] = True
    except Exception as e:
        import sys
        print(f"Page view tracking error: {e}", file=sys.stderr)

def check_password():
    if st.session_state.get('authenticated'):
        return True

    # Track page view
    _log_page_view()

    # Hide everything Streamlit
    st.markdown("""
    <style>
        [data-testid="stSidebar"], header, footer,
        [data-testid="stToolbar"], [data-testid="stDecoration"],
        #MainMenu, .stDeployButton,
        [data-testid="stStatusWidget"],
        .viewerBadge_container__r5tak,
        .styles_viewerBadge__CvC9N,
        ._profileContainer_gzau3_53,
        [data-testid="manage-app-button"],
        [data-testid="stBottom"] { display: none !important; visibility: hidden !important; height: 0 !important; }

        .stApp, [data-testid="stAppViewContainer"],
        .main .block-container, .main,
        section.main > div { background-color: #0a1628 !important; padding-top: 0 !important; }

        /* Input styling - works with light theme inputs on dark background */
        .stTextInput > label {
            color: rgba(255,255,255,0.4) !important;
            font-size: 12px !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
            font-weight: 600 !important;
        }
        .stTextInput > div > div > input {
            border: 1px solid rgba(212,168,75,0.3) !important;
            border-radius: 4px !important;
            padding: 14px 16px !important;
            font-size: 15px !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #d4a84b !important;
            box-shadow: 0 0 0 2px rgba(212,168,75,0.15) !important;
        }

        /* Gold button */
        .stButton > button {
            background: linear-gradient(135deg, #d4a84b 0%, #b8923e 100%) !important;
            color: #0a1628 !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 14px 32px !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
            width: 100% !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #e0b855 0%, #c49d45 100%) !important;
            box-shadow: 0 4px 20px rgba(212,168,75,0.3) !important;
        }
        .stButton > button:active, .stButton > button:focus {
            background: linear-gradient(135deg, #d4a84b 0%, #b8923e 100%) !important;
            color: #0a1628 !important;
        }

        .stAlert { background-color: rgba(220,38,38,0.08) !important; border: 1px solid rgba(220,38,38,0.2) !important; border-radius: 4px !important; }
        .stAlert p { color: #fca5a5 !important; }
    </style>
    """, unsafe_allow_html=True)

    left, spacer_col, right = st.columns([1.3, 0.15, 0.85])

    with left:
        st.markdown('<div style="padding:6vh 0 0 2vw;margin-bottom:5vh;"><span style="font-family:Georgia,serif;font-size:28px;font-weight:bold;color:#ffffff;">Velarion</span><span style="font-family:Georgia,serif;font-size:28px;font-weight:bold;color:#d4a84b;">.</span><span style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:rgba(255,255,255,0.3);margin-left:12px;vertical-align:middle;">Company Intelligence</span></div>', unsafe_allow_html=True)

        st.markdown('<div style="padding:0 0 0 2vw;margin-bottom:4vh;"><h1 style="font-family:Georgia,serif;font-size:clamp(28px,3.2vw,42px);font-weight:bold;color:#ffffff;line-height:1.12;margin:0 0 20px 0;">AI-Powered Executive<br>Compensation <em style="color:#22b89a;font-style:italic;">Intelligence.</em></h1><p style="font-size:16px;color:rgba(255,255,255,0.55);line-height:1.7;max-width:520px;margin:0;">Structured compensation data from SEC proxy filings. AI-powered peer analysis. Updated quarterly.</p></div>', unsafe_allow_html=True)

        st.markdown('<div style="padding:0 0 0 2vw;margin-bottom:4vh;"><div style="font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:16px;">Industry Coverage</div><div style="display:flex;flex-wrap:wrap;gap:8px;"><span style="padding:7px 16px;font-size:13px;font-weight:600;background:#1a8c7a;color:#ffffff;border:1px solid #1a8c7a;">Real Estate <span style="font-size:10px;font-weight:700;letter-spacing:0.5px;margin-left:6px;opacity:0.7;">LIVE</span></span><span style="padding:7px 16px;font-size:13px;color:rgba(255,255,255,0.3);border:1px solid rgba(255,255,255,0.08);">Banks <span style="font-size:10px;opacity:0.5;margin-left:4px;">Q2</span></span><span style="padding:7px 16px;font-size:13px;color:rgba(255,255,255,0.3);border:1px solid rgba(255,255,255,0.08);">Biotech <span style="font-size:10px;opacity:0.5;margin-left:4px;">Q3</span></span><span style="padding:7px 16px;font-size:13px;color:rgba(255,255,255,0.3);border:1px solid rgba(255,255,255,0.08);">Energy <span style="font-size:10px;opacity:0.5;margin-left:4px;">Q3</span></span><span style="padding:7px 16px;font-size:13px;color:rgba(255,255,255,0.3);border:1px solid rgba(255,255,255,0.08);">Technology <span style="font-size:10px;opacity:0.5;margin-left:4px;">Q4</span></span></div></div>', unsafe_allow_html=True)

        st.markdown('<div style="padding:0 0 0 2vw;"><div style="border-left:2px solid #d4a84b;padding-left:16px;"><p style="font-size:14px;color:rgba(255,255,255,0.5);line-height:1.6;font-style:italic;margin:0 0 8px 0;">"I built this because leadership compensation is one of the most important decisions a company makes &mdash; but gathering, analyzing, and presenting the data behind those decisions is still painfully inefficient. Velarion solves this by applying the power of AI to deliver real-time data and analysis to the executives, boards, and advisors who need it most."</p><p style="font-size:12px;color:rgba(255,255,255,0.3);margin:0;font-weight:600;">Andy Richardson &mdash; Founder, Former Real Estate Executive</p></div></div>', unsafe_allow_html=True)

    with right:
        st.markdown("""
        <div style="margin-top:14vh;margin-bottom:20px;">
            <div style="width:40px;height:2px;background:#d4a84b;margin-bottom:20px;"></div>
            <div style="font-size:20px;font-weight:bold;color:#ffffff;font-family:Georgia,serif;margin-bottom:6px;">Sign in</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.35);">Access your company intelligence dashboard</div>
        </div>
        """, unsafe_allow_html=True)

        email = st.text_input("EMAIL", key="auth_email", placeholder="you@company.com")
        pw = st.text_input("PASSWORD", type="password", key="auth_pw", placeholder="Enter your password")

        if st.button("Sign In", use_container_width=True):
            email_clean = email.strip().lower()
            if email_clean and "@" in email_clean and pw == "demo2026":
                st.session_state['authenticated'] = True
                st.session_state['user_email'] = email_clean
                _log_login(email_clean)
                st.rerun()
            elif not email_clean or "@" not in email_clean:
                st.error("Please enter a valid email address.")
            else:
                st.error("Invalid credentials. Please try again.")

        st.markdown("""
        <div style="margin-top:28px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.05);">
            <p style="font-size:11px;color:rgba(255,255,255,0.5);margin:0 0 4px 0;">Early beta access through March 31, 2026</p>
            <p style="font-size:11px;color:rgba(255,255,255,0.4);margin:0;">Questions? <a href="mailto:andy@velarion.ai" style="color:#d4a84b;text-decoration:none;">andy@velarion.ai</a></p>
        </div>
        """, unsafe_allow_html=True)

    return False

if not check_password(): st.stop()

SUPABASE_URL = "https://fhnffpgotkxxtwmwbizy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZobmZmcGdvdGt4eHR3bXdiaXp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEwNzAzNTEsImV4cCI6MjA4NjY0NjM1MX0.XU80VORX49loeJlbrq0w9hiGOUAN7fgEH6FPiF1E-GU"
REIT_INDEX_TICKER = "VNQ"
FY_YEAR = 2024
RETURNS_YEAR = 2025  # Stock returns through this year (plus YTD current year)
POS_ORDER = {'CEO': 0, 'PRESIDENT': 1, 'COO': 2, 'CFO': 3, 'CIO': 4, 'GC': 5, 'CAO': 6, 'OTHER_NEO': 7}
PROPERTY_TYPE_MAP = {
    'Industrial/Logistics': 'Industrial', 'Self-Storage': 'Self Storage',
    'Multifamily/Residential': 'Multifamily', 'Residential': 'Multifamily',
    'Mortgage/mREIT': 'Mortgage',
}
TICKER_RECLASSIFY = {
    # Net Lease
    'ADC': 'Net Lease', 'BNL': 'Net Lease', 'EPRT': 'Net Lease', 'FCPT': 'Net Lease',
    'FVR': 'Net Lease', 'GNL': 'Net Lease', 'GTY': 'Net Lease', 'NNN': 'Net Lease',
    'NTST': 'Net Lease', 'O': 'Net Lease', 'OLP': 'Net Lease', 'ONL': 'Net Lease',
    'GIPR': 'Net Lease', 'WPC': 'Net Lease', 'PKST': 'Net Lease', 'MDV': 'Net Lease',
    'EPR': 'Net Lease', 'SAFE': 'Net Lease', 'SILA': 'Net Lease',
    # Retail
    'AKR': 'Retail', 'BFS': 'Retail', 'BRX': 'Retail', 'CBL': 'Retail', 'CTO': 'Retail',
    'FRT': 'Retail', 'IVT': 'Retail', 'KIM': 'Retail', 'KRG': 'Retail', 'MAC': 'Retail',
    'PECO': 'Retail', 'REG': 'Retail', 'SITC': 'Retail', 'SKT': 'Retail', 'SPG': 'Retail',
    'WSR': 'Retail', 'WHLR': 'Retail', 'RPT': 'Retail',
    # Office
    'AAT': 'Office', 'BDN': 'Office', 'BXP': 'Office', 'CDP': 'Office', 'CUZ': 'Office',
    'DEA': 'Office', 'DEI': 'Office', 'ESRT': 'Office', 'FSP': 'Office', 'HIW': 'Office',
    'HPP': 'Office', 'JBGS': 'Office', 'KRC': 'Office', 'NYC': 'Office', 'PDM': 'Office',
    'SLG': 'Office', 'VNO': 'Office', 'CLPR': 'Office',
    # Industrial
    'EGP': 'Industrial', 'FR': 'Industrial', 'ILPT': 'Industrial', 'LXP': 'Industrial',
    'PLD': 'Industrial', 'PLYM': 'Industrial', 'REXR': 'Industrial', 'STAG': 'Industrial',
    'COLD': 'Industrial', 'LINE': 'Industrial',
    # Residential / Multifamily
    'AIV': 'Residential', 'ALX': 'Residential', 'AMH': 'Residential', 'AVB': 'Residential',
    'BRT': 'Residential', 'CPT': 'Residential', 'CSR': 'Residential', 'ELME': 'Residential',
    'EQR': 'Residential', 'ESS': 'Residential', 'IRT': 'Residential', 'MAA': 'Residential',
    'NXRT': 'Residential', 'UDR': 'Residential', 'UMH': 'Residential', 'VRE': 'Residential',
    # Healthcare
    'AHR': 'Healthcare', 'CHCT': 'Healthcare', 'CTRE': 'Healthcare', 'DHC': 'Healthcare',
    'DOC': 'Healthcare', 'GMRE': 'Healthcare', 'HR': 'Healthcare', 'LTC': 'Healthcare',
    'MPW': 'Healthcare', 'NHI': 'Healthcare', 'NHPAP': 'Healthcare', 'OHI': 'Healthcare',
    'SBRA': 'Healthcare', 'STRW': 'Healthcare', 'UHT': 'Healthcare', 'VTR': 'Healthcare',
    'WELL': 'Healthcare',
    # Lodging
    'AHT': 'Lodging', 'APLE': 'Lodging', 'BHR': 'Lodging', 'CLDT': 'Lodging',
    'DRH': 'Lodging', 'HST': 'Lodging', 'IHT': 'Lodging', 'INN': 'Lodging',
    'PEB': 'Lodging', 'RHP': 'Lodging', 'RLJ': 'Lodging', 'SOHO': 'Lodging',
    'SVC': 'Lodging',
    # Self-Storage
    'EXR': 'Self-Storage', 'NSA': 'Self-Storage', 'PSA': 'Self-Storage',
    'SELF': 'Self-Storage', 'SMA': 'Self-Storage',
    # Data Center / Tower / Infrastructure
    'AMT': 'Infrastructure', 'CCI': 'Infrastructure', 'DLR': 'Infrastructure',
    'EQIX': 'Infrastructure', 'IRM': 'Infrastructure', 'SBAC': 'Infrastructure',
    # Mortgage
    'ABR': 'Mortgage', 'ACR': 'Mortgage', 'ACRE': 'Mortgage', 'AGNC': 'Mortgage',
    'ARI': 'Mortgage', 'BRSP': 'Mortgage', 'BXMT': 'Mortgage', 'CHMI': 'Mortgage',
    'CIM': 'Mortgage', 'DX': 'Mortgage', 'FBRT': 'Mortgage', 'GPMT': 'Mortgage',
    'KREF': 'Mortgage', 'LADR': 'Mortgage', 'LFT': 'Mortgage', 'LOAN': 'Mortgage',
    'MFA': 'Mortgage', 'MITT': 'Mortgage', 'NLY': 'Mortgage', 'PMT': 'Mortgage',
    'RC': 'Mortgage', 'RITM': 'Mortgage', 'RWT': 'Mortgage', 'SACH': 'Mortgage',
    'SEVN': 'Mortgage', 'STWD': 'Mortgage', 'SUNS': 'Mortgage', 'TRTX': 'Mortgage',
    'TWO': 'Mortgage',
    # Specialty / Other
    'ARE': 'Life Science', 'CXW': 'Specialty', 'ELS': 'Manufactured Housing',
    'FPI': 'Specialty', 'GLPI': 'Gaming', 'HHH': 'Diversified', 'LAMR': 'Specialty',
    'MDRR': 'Diversified', 'OUT': 'Specialty', 'PCH': 'Timber', 'PSTL': 'Specialty',
    'PW': 'Specialty', 'RYN': 'Timber', 'SQFT': 'Specialty', 'SUI': 'Manufactured Housing',
    'VICI': 'Gaming', 'WY': 'Timber', 'ADAM': 'Specialty',
}
POSITION_DISPLAY = {'CEO': 'CEO', 'PRESIDENT': 'President', 'COO': 'COO', 'CFO': 'CFO', 'CIO': 'CIO', 'GC': 'GC', 'CAO': 'CAO'}

# Acquired/merged/delisted companies — for "NOT IN DATABASE" context
ACQUIRED_COMPANIES = {
    'duke realty': 'Acquired by Prologis (2022)',
    'life storage': 'Acquired by Extra Space Storage (2023)',
    'spirit realty': 'Acquired by Realty Income (2024)',
    'rpt realty': 'Merged into Kimco Realty (2024)',
    'store capital': 'Taken private by GIC (2023)',
    'ps business parks': 'Acquired by Blackstone (2022)',
    'monmouth': 'Acquired by Industrial Logistics Properties (2022)',
    'columbia property': 'Merged into Prologis (2022)',
    'preferred apartment': 'Taken private by Blackstone (2022)',
    'bluerock residential': 'Taken private by Blackstone (2022)',
    'american campus': 'Acquired by Blackstone (2022)',
    'healthcare trust': 'Merged into American Healthcare REIT (2022)',
    'paladin realty': 'Delisted',
    'inland real estate': 'Acquired by Inland Western (merged)',
    'cole credit': 'Merged into American Realty Capital',
    'xenia hotels': 'Name changed / restructured',
    'hersha hospitality': 'Taken private (2023)',
    'condor hospitality': 'Merged (2023)',
}
POSITION_FILTER_LABEL = {**POSITION_DISPLAY}
# Positions shown in sidebar filter
FILTER_POSITIONS = ['CEO', 'PRESIDENT', 'COO', 'CFO', 'CIO', 'GC', 'CAO']

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    .stApp { font-family: 'DM Sans', sans-serif; background: #f7f8fa; }
    /* HEADER — deep navy */
    .main-header { background: linear-gradient(135deg, #0a1628 0%, #1a365d 60%, #234578 100%); padding: 2rem 2.5rem; border-radius: 12px; margin-bottom: 0.3rem; color: white; box-shadow: 0 4px 20px rgba(10,22,40,0.3); }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; letter-spacing: -0.02em; }
    .main-header p { margin: 0.3rem 0 0 0; opacity: 0.8; font-size: 0.92rem; }
    .intro-text { color: #334155; font-size: 0.9rem; line-height: 1.55; padding: 0.4rem 0 0.8rem 0; }
    /* INSTRUCTION BOXES — warm cream/gold tint */
    .tab-instruction { background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border: 1px solid #d4a017; border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 1rem; font-size: 0.83rem; color: #78350f; font-weight: 500; }
    .tab-cta { background: linear-gradient(135deg, #b8860b 0%, #d4a017 100%); border-radius: 8px; padding: 0.7rem 1rem; margin-bottom: 1rem; font-size: 0.9rem; color: white; font-weight: 600; text-align: center; }
    /* KPI CARDS — white with gold top accent */
    .metric-card { background: white; border: 1px solid #d6d3d1; border-top: 3px solid #b8860b; border-radius: 10px; padding: 1rem 1.2rem; text-align: center; height: 130px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 2px 8px rgba(10,22,40,0.06); }
    .metric-card .label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.07em; color: #57534e; font-weight: 700; white-space: nowrap; }
    .metric-card .value { font-size: 1.5rem; font-weight: 700; color: #0f172a; margin-top: 0.15rem; }
    .metric-card .sub { font-size: 0.78rem; color: #78716c; margin-top: 0.1rem; font-weight: 500; }
    /* AI NARRATIVE — navy accent */
    .ai-narrative { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border: 1px solid #94a3b8; border-left: 5px solid #1a365d; border-radius: 8px; padding: 1.2rem 1.5rem; margin: 1rem 0; font-size: 0.9rem; line-height: 1.65; color: #1e293b; text-align: justify; box-shadow: 0 2px 8px rgba(26,54,93,0.06); }
    .ai-narrative .ai-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #1a365d; font-weight: 700; margin-bottom: 0.5rem; text-align: left; }
    /* AI REPORT — gold accent */
    .ai-report { background: linear-gradient(135deg, #fffbeb 0%, #fefce8 100%); border: 1px solid #d4a017; border-left: 5px solid #b8860b; border-radius: 8px; padding: 1.5rem 2rem; margin: 1rem 0; font-size: 0.9rem; line-height: 1.7; color: #1e293b; text-align: justify; box-shadow: 0 2px 8px rgba(184,134,11,0.08); }
    .ai-report .ai-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #92400e; font-weight: 700; margin-bottom: 0.5rem; text-align: left; }
    .ai-report h4 { color: #1a365d; font-size: 1.15rem; margin: 1.2rem 0 0.3rem 0; padding: 0; text-align: left; }
    .ai-report p { margin: 0 0 0.8rem 0; text-align: justify; }
    .ai-report .js-plotly-plot, .ai-report iframe { margin-top: 1rem; }
    .ai-narrative h4 { color: #1a365d; font-size: 1.15rem; margin: 1.2rem 0 0.3rem 0; padding: 0; text-align: left; }
    .ai-narrative p { margin: 0 0 0.8rem 0; text-align: justify; }
    /* UTILITY BOXES */
    .lookup-box { background: #fafaf9; border: 1px solid #d6d3d1; border-radius: 10px; padding: 1rem 1.5rem 0.3rem 1.5rem; margin-bottom: 0.5rem; text-align: center; }
    .lookup-box h2 { margin: 0 0 0.3rem 0; font-size: 1.15rem; font-weight: 700; color: #0f172a; }
    .lookup-box p { margin: 0 0 0.5rem 0; color: #57534e; font-size: 0.83rem; }
    .stats-bar { background: #fafaf9; border: 1px solid #d6d3d1; border-radius: 10px; padding: 1rem 1.5rem; margin-top: 1rem; display: flex; gap: 2rem; flex-wrap: wrap; justify-content: center; }
    .stats-bar .stat { text-align: center; }
    .stats-bar .stat-label { font-size: 0.72rem; text-transform: uppercase; color: #57534e; font-weight: 600; }
    .stats-bar .stat-value { font-size: 1.1rem; font-weight: 700; color: #0f172a; }
    .analysis-picker { background: #fafaf9; border: 1px solid #d6d3d1; border-radius: 10px; padding: 1rem 1.5rem; margin: 0.5rem 0; }
    /* BADGES */
    .partial-year { background: #fbbf24; color: #78350f; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .ext-badge { background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .hl-row { background: #fef9ee; border: 1px solid #d4a017; border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; font-size: 0.88rem; }
    .filter-note { font-size: 0.75rem; color: #57534e; line-height: 1.4; padding: 0.5rem 0; border-top: 1px solid #d6d3d1; margin-top: 0.5rem; }
    .widen-warn { background: #fffbeb; border: 1px solid #d4a017; border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.8rem; color: #92400e; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
    /* SIDEBAR — warm light gray, push content down to align with main content */
    section[data-testid="stSidebar"] { background: #f5f3f0; }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 2.5rem; }
    section[data-testid="stSidebar"] .stMarkdown h3 { font-size: 0.83rem; text-transform: uppercase; letter-spacing: 0.07em; color: #1a365d; margin-top: 0.8rem; }
    /* TAGS — navy */
    span[data-baseweb="tag"] { background-color: #1a365d !important; color: white !important; }
    span[data-baseweb="tag"] span[role="presentation"] { color: white !important; }
    /* BUTTONS — navy primary */
    .stButton > button { background: linear-gradient(135deg, #1a365d 0%, #234578 100%) !important; color: white !important; border: none !important; font-weight: 600 !important; border-radius: 8px !important; padding: 0.5rem 1.2rem !important; font-size: 0.85rem !important; height: 48px !important; display: flex !important; align-items: center !important; justify-content: center !important; box-shadow: 0 2px 6px rgba(26,54,93,0.25) !important; }
    .stButton > button:hover { background: linear-gradient(135deg, #0f2440 0%, #1a365d 100%) !important; box-shadow: 0 3px 10px rgba(26,54,93,0.35) !important; }
    .stButton > button[kind="secondary"] { font-size: 0.75rem !important; padding: 0.3rem 0.7rem !important; border-radius: 6px !important; font-weight: 500 !important; height: 38px !important; }
    /* LINK BUTTONS — navy */
    .stLinkButton > a { background: linear-gradient(135deg, #1a365d 0%, #234578 100%) !important; color: white !important; border: none !important; font-weight: 600 !important; border-radius: 8px !important; padding: 0.6rem 1.5rem !important; font-size: 0.95rem !important; text-decoration: none !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; width: 100% !important; box-sizing: border-box !important; box-shadow: 0 2px 6px rgba(26,54,93,0.25) !important; }
    .stLinkButton > a:hover { background: linear-gradient(135deg, #0f2440 0%, #1a365d 100%) !important; color: white !important; }
    /* DOWNLOAD BUTTON — gold */
    .stDownloadButton > button { background: linear-gradient(135deg, #b8860b 0%, #d4a017 100%) !important; color: white !important; border: none !important; font-weight: 600 !important; border-radius: 8px !important; box-shadow: 0 2px 6px rgba(184,134,11,0.25) !important; }
    /* SLIDER — navy */
    div[data-baseweb="slider"] div[role="slider"] { background: #1a365d !important; border-color: #1a365d !important; }
    div[data-baseweb="slider"] [data-testid="stThumbValue"] { color: #1a365d !important; }
    .stCheckbox label span { font-weight: 600 !important; font-size: 0.95rem !important; }
    .footnote { font-size: 0.73rem; color: #78716c; font-style: italic; margin-top: 0.3rem; }
    .source-note { font-size: 0.68rem; color: #78716c; margin-top: 0.2rem; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; color: #0f172a !important; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #1a365d !important; }
    /* Chart spacing — more room between text and charts */
    .stPlotlyChart { margin-top: 0.8rem !important; margin-bottom: 0.5rem !important; }
    /* Context refinement textarea */
    [data-testid="stTextArea"] textarea { background-color: #fefefe !important; border: 1px solid #d6d3d1 !important; }
    /* Download button font */
    div[data-testid="stDownloadButton"] button { font-size: 0.78rem !important; padding: 0.4rem 0.8rem !important; }
    /* Proxy peer expander — navy/gold */
    div[data-testid="stExpander"] { max-width: 70%; }
    div[data-testid="stExpander"] details { border: 2px solid #1a365d !important; border-radius: 10px !important; background: linear-gradient(135deg, #f8f6f3 0%, #faf9f7 100%) !important; }
    div[data-testid="stExpander"] summary { font-weight: 600 !important; color: #1a365d !important; }
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
    # Clean up garbage region values
    if 'geographic_region' in df.columns:
        # Fix known misclassifications
        df.loc[df['hq_state'] == 'IL', 'geographic_region'] = 'Midwest'
        # Fold Unknown/Other into nearest region by HQ state
        _state_region_fix = {
            'CO': 'Mountain', 'UT': 'Mountain', 'MT': 'Mountain', 'WY': 'Mountain', 'NM': 'Southwest',
            'AZ': 'Southwest', 'NV': 'Southwest', 'HI': 'California', 'AK': 'Pacific Northwest',
        }
        for st, reg in _state_region_fix.items():
            mask = (df['geographic_region'].isin(['Unknown','Other'])) & (df['hq_state'] == st)
            df.loc[mask, 'geographic_region'] = reg
        # Any remaining Unknown/Other → assign "National" so they're not lost
        df.loc[df['geographic_region'].isin(['Unknown','Other','']), 'geographic_region'] = 'National'
        df.loc[df['geographic_region'].isna(), 'geographic_region'] = 'National'
    # Placeholder for 8-K cross-reference partial year flag (populated when 8-K data is in Supabase)
    if 'partial_year_8k' not in df.columns:
        df['partial_year_8k'] = False
    return df

@st.cache_data(ttl=300)
def load_peer_groups():
    """Load proxy-disclosed peer groups from Supabase (paginated to handle >1000 rows)."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        all_data = []
        offset = 0
        batch = 1000
        while True:
            result = sb.table('proxy_peer_groups').select('*').range(offset, offset + batch - 1).execute()
            if result.data:
                all_data.extend(result.data)
            if not result.data or len(result.data) < batch:
                break
            offset += batch
        if all_data:
            return pd.DataFrame(all_data)
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_total_returns(tickers):
    try:
        import yfinance as yf
    except ImportError:
        return {}
    all_t = list(set(tickers + [REIT_INDEX_TICKER]))
    # Pull data from 3 years before RETURNS_YEAR through today (for YTD)
    start_3y = datetime(RETURNS_YEAR - 3, 1, 1)
    today = datetime.now()
    try:
        data = yf.download(all_t, start=start_3y, end=today + timedelta(days=1), progress=False)['Close']
    except Exception:
        return {}
    if data.empty: return {}
    if isinstance(data, pd.Series): data = data.to_frame(all_t[0])
    returns = {}
    for t in all_t:
        if t not in data.columns: continue
        p = data[t].dropna()
        if len(p) < 20: continue
        # 1-Year return: RETURNS_YEAR (e.g., Jan 1 2025 - Dec 31 2025)
        fy_end = p[p.index <= pd.Timestamp(datetime(RETURNS_YEAR, 12, 31) + timedelta(days=7))]
        if fy_end.empty: continue
        cur_fy = fy_end.iloc[-1]
        s1 = p[p.index >= pd.Timestamp(datetime(RETURNS_YEAR-1, 12, 28))]
        r1 = ((cur_fy / s1.iloc[0]) - 1) * 100 if len(s1) > 1 else None
        # 3-Year return: RETURNS_YEAR-2 through RETURNS_YEAR (e.g., 2023-2025)
        s3 = p[p.index >= pd.Timestamp(datetime(RETURNS_YEAR-3, 12, 28))]
        r3 = ((cur_fy / s3.iloc[0]) - 1) * 100 if len(s3) > 1 else None
        # YTD return: Jan 1 of current year through today
        ytd_start = p[p.index >= pd.Timestamp(datetime(RETURNS_YEAR + 1, 1, 1) - timedelta(days=5))]
        ytd_cur = p.iloc[-1] if not p.empty else None
        r_ytd = ((ytd_cur / ytd_start.iloc[0]) - 1) * 100 if ytd_start is not None and len(ytd_start) > 1 and ytd_cur is not None else None
        returns[t] = {'return_1y': r1, 'return_3y': r3, 'return_ytd': r_ytd}
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
    # Preserve section markers on their own line before converting newlines
    text = re.sub(r'\n\s*(\[SECTION:\w+\])\s*\n', r'\n\1\n', text)
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
    """Detect partial-year NEOs via heuristics. 
    Future: also cross-ref 8-K appointment dates in the proxy fiscal year."""
    if pd.isna(row['total_comp']) or row['total_comp'] == 0: return False
    # Former exec = always partial year
    title = str(row.get('title', '')).lower()
    if 'former' in title: return True
    # Check if we have 8-K data flag (populated by load_supabase when 8-K data is available)
    if row.get('partial_year_8k'): return True
    # Heuristic: compare to peers
    pp = peers_df[peers_df['position'] == row['position']]['total_comp'].dropna()
    if len(pp) < 3: return False
    stock = row.get('stock_based_comp')
    stock_missing = pd.isna(stock) or stock == 0 or stock is None or stock == ''
    sal = row.get('base_salary', 0) or 0
    sal_peers = peers_df[peers_df['position'] == row['position']]['base_salary'].dropna()
    sal_median = sal_peers.median() if len(sal_peers) >= 3 else 0
    # Partial year signals:
    total_low = row['total_comp'] < pp.quantile(0.25)
    sal_low = sal > 0 and sal_median > 0 and sal < sal_median * 0.5
    sal_very_low = sal > 0 and sal_median > 0 and sal < sal_median * 0.3
    # Exclude intentional $1/$0 salary execs (common for founder/CEOs with large equity packages)
    intentional_low_sal = sal <= 10 and not stock_missing and row['total_comp'] > pp.median() * 0.5
    if intentional_low_sal:
        return False
    # Case 1: low total + no equity
    # Case 2: low salary + no equity
    # Case 3: very low salary (< 30% of median) — even with equity (likely mid-year start with sign-on grant)
    return bool((total_low and stock_missing) or (sal_low and stock_missing) or sal_very_low)

def get_peer_stats(filt):
    return filt[filt['comp_source'] != 'external_manager']

def sort_by_position(co_df):
    return co_df.sort_values('pos_order')

def filter_fingerprint(filt_df):
    """Return a hashable tuple of filtered tickers — changes when peer group changes."""
    return tuple(sorted(filt_df['ticker'].unique()))

STALE_WARNING = '<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:0.6rem 1rem;font-size:0.83rem;color:#92400e;margin:0.5rem 0;">\u26A0\uFE0F Peer group filters have changed since this analysis was generated. Click the generate button again to refresh with the updated peer group.</div>'

@st.cache_data(ttl=86400)
def lookup_proxy_url(company_name, fy_year):
    """Look up the most recent DEF 14A proxy filing URL on SEC EDGAR."""
    import requests as _req
    try:
        clean_name = company_name.replace(',', '').replace('.', '').replace("'", '')
        query = f'%22{clean_name.replace(" ", "+")}%22'
        url = f'https://efts.sec.gov/LATEST/search-index?q={query}&forms=DEF+14A&dateRange=custom&startdt={fy_year+1}-01-01&enddt={fy_year+1}-12-31'
        resp = _req.get(url, headers={'User-Agent': 'Velarion Research andy@velarion.ai'}, timeout=10)
        if resp.status_code != 200:
            return None
        import json
        data = json.loads(resp.text)
        hits = data.get('hits', {}).get('hits', [])
        if not hits:
            return None
        hit = hits[0]
        parts = hit['_id'].split(':')
        accession = parts[0]
        filename = parts[1]
        cik = hit['_source']['ciks'][0].lstrip('0')
        return f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace("-","")}/{filename}'
    except Exception:
        return None

def peer_context_str(filt, pt, excluded_tks=None):
    ps = get_peer_stats(filt)
    # Use all peers in the filtered set, not just the company's own property type
    all_pts = sorted(ps['property_type'].dropna().unique())
    n = ps['ticker'].nunique()
    mc_valid = filt['market_cap'].dropna()
    mcr = f"${mc_valid.min()/1e9:.2f}B\u2013${mc_valid.max()/1e9:.2f}B" if not mc_valid.empty else "$0B\u2013$0B"
    tickers = sorted(ps['ticker'].unique())
    pt_label = ' & '.join(all_pts) if len(all_pts) <= 3 else f"{len(all_pts)} property types"
    return n, mcr, tickers, pt_label

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
    color = "#b8860b" if pct and pct >= 50 else "#1a365d" if pct and pct >= 25 else "#475569" if pct is not None else "#94a3b8"
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
    <thead><tr style="background:#f8f6f3;position:sticky;top:0;"><th style="padding:6px;text-align:left;">Rank</th><th style="padding:6px;text-align:left;">Ticker</th><th style="padding:6px;text-align:left;">Company</th><th style="padding:6px;text-align:left;">Executive</th><th style="padding:6px;text-align:right;">Salary</th><th style="padding:6px;text-align:right;">Cash Bonus</th><th style="padding:6px;text-align:right;">Stock</th><th style="padding:6px;text-align:right;">Total Comp</th><th style="padding:6px;text-align:right;">Mkt Cap</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table></div>"""
    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# AI — COMPENSATION CONSULTANT TONE
# ============================================================
def get_client():
    try:
        import anthropic; return anthropic.Anthropic()
    except Exception: return None

AI_TONE = """ROLE: You are a seasoned REIT compensation consultant preparing a confidential briefing for a comp committee member — similar to Pearl Meyer or FW Cook. Your audience is management preparing for board meetings and comp committee negotiations.

APPROACH:
1. STATE the positioning (data and percentiles)
2. ANALYZE the compensation mix vs peer medians (salary/cash/equity split)
3. CONNECT compensation to shareholder returns and operating performance (pay-for-performance)
4. FLAG what to watch — frame observations QUALITATIVELY, hedge quantitative comparisons
5. RECOMMEND directional action grounded in data

MANAGEMENT-FRIENDLY TONE: Always lean toward the management team's perspective. When comp is low and performance is strong, advocate clearly: "Performance strongly supports a move toward the upper quartile." When comp is high and performance is strong: "Compensation reflects market-appropriate recognition of strong results." When comp is high and performance is weak: "The board may want to ensure incentive structures are tied to specific forward-looking performance metrics." When comp is low and performance is weak: "Current positioning reflects the performance trajectory, with room to adjust as results improve."

HEDGING: Use "may," "appears to," "suggests," "could create pressure" when making forward-looking observations. Do NOT cite specific dollar amounts from CD&A — the committee already knows what they paid. Frame CD&A observations qualitatively.

CRITICAL RULES: No markdown (no asterisks, bold, headers, bullets). Plain flowing paragraphs only. No title. Weave peer group details (property type, count, market cap range, company names) naturally into the text. Always include the compensation mix comparison. Always include a pay-for-performance assessment."""

@st.cache_data(ttl=86400)
def fetch_cda_text(company_name, fy_year):
    """Extract CD&A section text from the DEF 14A proxy filing."""
    import requests as _req
    from bs4 import BeautifulSoup
    try:
        proxy_url = lookup_proxy_url(company_name, fy_year)
        if not proxy_url:
            return None
        resp = _req.get(proxy_url, headers={'User-Agent': 'Velarion Research andy@velarion.ai'}, timeout=20)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        # Find CD&A section
        cda_start = None
        cda_end = None
        lines = text.split('\n')
        for i, line in enumerate(lines):
            ll = line.lower().strip()
            if cda_start is None and ('compensation discussion and analysis' in ll or 'compensation discussion & analysis' in ll):
                cda_start = i
            elif cda_start is not None and i > cda_start + 10:
                # Look for end markers
                if any(marker in ll for marker in ['compensation committee report', 'report of the compensation committee',
                    'summary compensation table', 'executive compensation tables']):
                    cda_end = i
                    break
        if cda_start is not None:
            end = cda_end if cda_end else min(cda_start + 500, len(lines))
            cda_text = '\n'.join(lines[cda_start:end])
            # Truncate to ~50K chars to fit in context
            return cda_text[:50000] if len(cda_text) > 50000 else cda_text
        return None
    except Exception:
        return None

@st.cache_data(ttl=86400)
def fetch_earnings_data(company_name, ticker):
    """Fetch recent quarterly earnings press releases from 8-K filings."""
    import requests as _req
    try:
        clean_name = company_name.replace(',', '').replace('.', '').replace("'", '')
        query = f'%22{clean_name.replace(" ", "+")}%22'
        url = f'https://efts.sec.gov/LATEST/search-index?q={query}&forms=8-K&dateRange=custom&startdt=2024-06-01&enddt=2025-12-31'
        resp = _req.get(url, headers={'User-Agent': 'Velarion Research andy@velarion.ai'}, timeout=10)
        if resp.status_code != 200:
            return None
        import json
        data = json.loads(resp.text)
        hits = data.get('hits', {}).get('hits', [])
        # Look for earnings-related 8-Ks (Item 2.02 = Results of Operations)
        earnings_texts = []
        for hit in hits[:15]:  # Check up to 15 most recent 8-Ks
            try:
                doc_id = hit['_id']
                parts = doc_id.split(':')
                accession = parts[0]
                filename = parts[1]
                cik = hit['_source']['ciks'][0].lstrip('0')
                filing_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace("-","")}/{filename}'
                filing_resp = _req.get(filing_url, headers={'User-Agent': 'Velarion Research andy@velarion.ai'}, timeout=15)
                if filing_resp.status_code != 200:
                    continue
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(filing_resp.text, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)[:3000]
                tl = text.lower()
                # Check if this is an earnings/results filing
                if any(kw in tl for kw in ['results of operations', 'financial results', 'earnings', 'revenue', 'net income',
                    'funds from operations', 'ffo', 'affo', 'net operating income', 'same-store']):
                    date = hit['_source']['file_date']
                    earnings_texts.append(f"[{date}] {text[:2000]}")
                    if len(earnings_texts) >= 4:  # Get up to 4 quarters
                        break
            except Exception:
                continue
        return '\n\n'.join(earnings_texts) if earnings_texts else None
    except Exception:
        return None

@st.cache_data(ttl=3600)
def fetch_current_stock(ticker):
    """Fetch current stock price and YTD return."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        hist = stock.history(period='1y')
        if hist.empty:
            return None
        current_price = hist['Close'].iloc[-1]
        # YTD: from Jan 1 of current year (RETURNS_YEAR + 1)
        current_yr = RETURNS_YEAR + 1
        ytd_start = hist[hist.index >= f'{current_yr}-01-01']
        if not ytd_start.empty and len(hist) > 0:
            jan1_price = ytd_start['Close'].iloc[0]
            ytd_return = (current_price / jan1_price - 1) * 100
        else:
            ytd_return = None
        # Also get VNQ for comparison
        vnq = yf.Ticker('VNQ')
        vnq_hist = vnq.history(period='1y')
        vnq_ytd = None
        if not vnq_hist.empty:
            vnq_ytd_start = vnq_hist[vnq_hist.index >= f'{current_yr}-01-01']
            if not vnq_ytd_start.empty:
                vnq_ytd = (vnq_hist['Close'].iloc[-1] / vnq_ytd_start['Close'].iloc[0] - 1) * 100
        return {
            'current_price': current_price,
            'ytd_return': ytd_return,
            'vnq_ytd': vnq_ytd,
            'as_of': hist.index[-1].strftime('%b %d, %Y')
        }
    except Exception:
        return None

def gen_exec(row, peers, all_df, ret_data, filt, widened=False, wide_peers_df=None):
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    pos = row['position']; pt = row['property_type']
    # If widened, use the wide peer set for percentiles; otherwise use property-type peers
    if widened and wide_peers_df is not None:
        ps = wide_peers_df
        pp = ps[ps['position'] == pos]
    else:
        ps = get_peer_stats(peers)
        pp = ps[ps['position'] == pos]
    n_co, mcr, tickers, pt_label = peer_context_str(peers, pt)
    st_d = {}
    for f in ['base_salary','cash_bonus_incentive','stock_based_comp','total_comp']:
        s = pp[f].dropna(); v = row[f]; p = percentile_rank(v, s) if pd.notna(v) else None
        st_d[f] = {'val': float(v) if pd.notna(v) else 0, 'pct': p, 'med': float(s.median()) if len(s)>0 else 0, 'n': len(s)}
    is_ext = row['comp_source'] == 'external_manager'; is_part = detect_partial(row, peers)
    tk = row['ticker']; r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    mix = comp_mix_str(row); peer_mix = peer_mix_median(ps, pos)
    co_r1 = r.get('return_1y')
    peer_r1s = [ret_data.get(t,{}).get('return_1y') for t in tickers if ret_data.get(t,{}).get('return_1y') is not None]
    ret_pct = percentile_rank(co_r1, pd.Series(peer_r1s)) if co_r1 is not None and peer_r1s else None
    notes = ""
    if is_part: notes += "\nNOTE: Partial-year hire — comp reflects less than full year. Explicitly note this in the analysis and state that compensation should not be compared at face value to full-year peers."
    if is_ext: notes += "\nNOTE: Externally managed."
    wider_note = ""
    if widened:
        n_wide = st_d['total_comp']['n']
        n_wide_cos = pp['ticker'].nunique()
        wider_note = f"""
NOTE: The {pt_label} peer group had fewer than 5 {pos}s, so this analysis uses {n_wide} {pos}s across {n_wide_cos} REITs (all property types) in the same market cap range as the benchmark.
INSTRUCTION: Explicitly note that the peer group was widened beyond {pt_label} to all REITs in the market cap range due to limited same-sector peers. Use the widened data as primary benchmark."""
    prompt = f"""REIT compensation analysis. 4-6 sentences.
{row['first_name']} {row['last_name']}, {pos}, {row['company_name']} ({tk}) | {pt} | Mkt Cap ${row['market_cap']/1e9:.2f}B
Total ${st_d['total_comp']['val']:,.0f} ({ordinal(st_d['total_comp']['pct'])} pctl, {quartile_label(st_d['total_comp']['pct'])}) | Salary ${st_d['base_salary']['val']:,.0f} ({ordinal(st_d['base_salary']['pct'])} pctl) | Bonus ${st_d['cash_bonus_incentive']['val']:,.0f} ({ordinal(st_d['cash_bonus_incentive']['pct'])} pctl) | Stock ${st_d['stock_based_comp']['val']:,.0f} ({ordinal(st_d['stock_based_comp']['pct'])} pctl)
Comp mix: {mix} | Peer median mix: {peer_mix}
Peer group: {st_d['total_comp']['n']} {pos}s | Tickers: {', '.join(pp['ticker'].unique())}
FY{RETURNS_YEAR} Returns: {tk} {fmt_return(co_r1)} ({ordinal(ret_pct)} pctl, {quartile_label(ret_pct)}) | Peer avg {fmt_return(np.mean(peer_r1s) if peer_r1s else None)} | FTSE Nareit {fmt_return(vnq.get('return_1y'))} | YTD {RETURNS_YEAR+1} {fmt_return(r.get('return_ytd'))}
NOTE: Compensation data is from FY{FY_YEAR} proxy (filed {FY_YEAR+1}). Returns through Dec 31, {RETURNS_YEAR} plus YTD {RETURNS_YEAR+1}. ONLY reference figures provided above. Do NOT invent any data.{wider_note}{notes}
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

def gen_analysis(co_d, filt, ret_data, all_df=None, mcap_min=0, mcap_max=50.0):
    """Combined company + returns analysis for Company View tab."""
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    cn = co_d['company_name'].iloc[0]; tk = co_d['ticker'].iloc[0]; pt = co_d['property_type'].iloc[0]; mc = co_d['market_cap'].iloc[0]
    ea = is_ext_advised(co_d, filt); ps = get_peer_stats(filt)
    n_co, mcr, tickers, pt_label = peer_context_str(filt, pt)
    en = "\nNOTE: Externally advised." if ea else ""
    # Build widened peer set for thin positions
    MIN_PEERS = 5
    wide_ps = None
    if all_df is not None:
        wide_base = all_df[all_df['ticker'] != tk].copy()
        if mcap_max >= 50.0:
            wide_base = wide_base[(wide_base['market_cap'] >= mcap_min*1e9) | (wide_base['market_cap'].isna())]
        else:
            wide_base = wide_base[((wide_base['market_cap'] >= mcap_min*1e9) & (wide_base['market_cap'] <= mcap_max*1e9)) | (wide_base['market_cap'].isna())]
        wide_ps = get_peer_stats(wide_base)
    elines = []
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; ip = detect_partial(rw, filt)
        pp = ps[ps['position']==rw['position']]
        n_pos = len(pp[pp['total_comp'].notna()])
        widened = False
        use_ps = ps
        if n_pos < MIN_PEERS and wide_ps is not None:
            pp_wide = wide_ps[wide_ps['position']==rw['position']]
            if len(pp_wide[pp_wide['total_comp'].notna()]) >= n_pos:
                pp = pp_wide
                use_ps = wide_ps
                widened = True
        pct = percentile_rank(rw['total_comp'], pp['total_comp'])
        t = rw['total_comp'] if pd.notna(rw['total_comp']) else 0
        mix = comp_mix_str(rw); pm = peer_mix_median(use_ps, rw['position'])
        fl = []
        if ie: fl.append('Ext')
        if ip: fl.append('Partial Yr')
        if widened: fl.append(f'Widened to {len(pp)} all-REIT peers')
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
FY{RETURNS_YEAR} Returns: {tk} 1-Yr {fmt_return(r.get('return_1y'))} ({ordinal(ret_pct)} pctl returns, {quartile_label(ret_pct)}) | 3-Yr {fmt_return(r.get('return_3y'))} | YTD {RETURNS_YEAR+1} {fmt_return(r.get('return_ytd'))}
Peer Avg ({n_co} cos): 1-Yr {fmt_return(np.mean(peer_r1s) if peer_r1s else None)} | 3-Yr {fmt_return(np.mean(p3) if p3 else None)}
FTSE Nareit: 1-Yr {fmt_return(vnq.get('return_1y'))} | 3-Yr {fmt_return(vnq.get('return_3y'))} | YTD {RETURNS_YEAR+1} {fmt_return(vnq.get('return_ytd'))}
Peers: {n_co} companies | Tickers: {', '.join(tickers)}
NOTE: Compensation data is from the FY{FY_YEAR} DEF 14A proxy filing (filed in {FY_YEAR+1}). Returns are through Dec 31, {RETURNS_YEAR} (1-yr and 3-yr) plus YTD {RETURNS_YEAR+1}. Frame the analysis as: how has the compensation structure approved by the board performed against {RETURNS_YEAR} shareholder returns?
CRITICAL: Only reference return figures explicitly provided above. Do NOT invent, estimate, or reference any return data not given. Do NOT reference years or periods for which no data is provided.
INSTRUCTIONS: Cover (1) each executive's compensation positioning and mix vs peers, (2) shareholder returns vs peer group and FTSE Nareit, (3) pay-for-performance assessment comparing comp quartile to returns quartile, and (4) a clear directional recommendation. If comp is below returns quartile, advocate for the management team. If any executive is flagged as [Partial Yr], explicitly note their compensation reflects a partial year of service and should not be compared at face value to full-year peers — do NOT characterize their pay as "low" or "below median" since it only reflects a fraction of the year. For partial-year executives, focus on compensation structure and mix rather than dollar amounts or percentile rankings. If ALL executives are partial year, lead with that context and frame the entire analysis around comp structure, equity weighting, and forward-looking positioning rather than peer dollar comparisons. If any executive is flagged as [Widened], note that the peer group was expanded beyond the primary peer set due to limited same-position peers.{en}
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=700, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

def gen_full(co_d, filt, ret_data, excluded_tks=None, added_tks=None, all_df=None, mcap_min=0, mcap_max=50.0, peer_mode='proxy'):
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    cn = co_d['company_name'].iloc[0]; tk = co_d['ticker'].iloc[0]; pt = co_d['property_type'].iloc[0]; mc = co_d['market_cap'].iloc[0]
    hq = f"{co_d['hq_city'].iloc[0]}, {co_d['hq_state'].iloc[0]}"
    ea = is_ext_advised(co_d, filt); ps = get_peer_stats(filt)
    n_co, mcr, tickers, pt_label = peer_context_str(filt, pt)
    # Peer group descriptor based on mode
    if peer_mode == 'proxy':
        peer_desc = f"{n_co} companies from {cn}'s proxy-disclosed compensation peer group (cross-sector, not limited to REITs)"
    else:
        peer_desc = f"{n_co} custom peer companies"
    en = "\nCRITICAL: Externally advised." if ea else ""
    # Build widened peer set for thin positions
    MIN_PEERS = 5
    wide_ps = None
    if all_df is not None:
        wide_base = all_df[all_df['ticker'] != tk].copy()
        if mcap_max >= 50.0:
            wide_base = wide_base[(wide_base['market_cap'] >= mcap_min*1e9) | (wide_base['market_cap'].isna())]
        else:
            wide_base = wide_base[((wide_base['market_cap'] >= mcap_min*1e9) & (wide_base['market_cap'] <= mcap_max*1e9)) | (wide_base['market_cap'].isna())]
        wide_ps = get_peer_stats(wide_base)
    esecs = []
    widened_positions = []
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; ip = detect_partial(rw, filt)
        pp = ps[ps['position']==rw['position']]
        n_pos = len(pp[pp['total_comp'].notna()])
        # Auto-widen if thin
        if n_pos < MIN_PEERS and wide_ps is not None:
            pp_wide = wide_ps[wide_ps['position']==rw['position']]
            if len(pp_wide[pp_wide['total_comp'].notna()]) >= n_pos:
                pp = pp_wide
                widened_positions.append(rw['position'])
                use_ps = wide_ps
            else:
                use_ps = ps
        else:
            use_ps = ps
        t = rw['total_comp'] if pd.notna(rw['total_comp']) else 0
        tp = percentile_rank(rw['total_comp'], pp['total_comp']); mix = comp_mix_str(rw); pm = peer_mix_median(use_ps, rw['position'])
        fl = []
        if ie: fl.append('EXT')
        if ip: fl.append('PARTIAL YR')
        if rw['position'] in widened_positions: fl.append(f'WIDENED TO {len(pp)} ALL-REIT PEERS')
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
    
    # Custom peer group modification notes
    excl_note = ""
    if peer_mode == 'custom':
        mod_notes = []
        if excluded_tks:
            mod_notes.append(f"Removed from proxy peer group: {', '.join(sorted(excluded_tks))}")
        if added_tks:
            mod_notes.append(f"Added beyond proxy peer group: {', '.join(sorted(added_tks))}")
        if mod_notes:
            excl_note = f"\nCUSTOM PEER GROUP MODIFICATIONS (vs. company's proxy-disclosed peers): {'. '.join(mod_notes)}. Note these modifications in the peer group description."
    
    # Fetch enrichment data
    cda_text = fetch_cda_text(cn, FY_YEAR)
    earnings_text = fetch_earnings_data(cn, tk)
    current_stock = fetch_current_stock(tk)
    
    # Build enrichment sections for prompt
    enrichment = ""
    if cda_text:
        # Truncate CD&A for prompt (keep under ~8K chars for the prompt)
        cda_snippet = cda_text[:8000]
        enrichment += f"\n\nCD&A EXCERPT (from FY{FY_YEAR} proxy — use to identify performance metrics, comp philosophy, say-on-pay results, and peer group rationale):\n{cda_snippet}"
    if earnings_text:
        earnings_snippet = earnings_text[:4000]
        enrichment += f"\n\nRECENT QUARTERLY EARNINGS (use for operational context — FFO/AFFO, revenue, occupancy, same-store NOI):\n{earnings_snippet}"
    if current_stock:
        enrichment += f"\n\nCURRENT STOCK DATA (as of {current_stock['as_of']}):"
        enrichment += f"\n  {tk}: ${current_stock['current_price']:.2f} | YTD {RETURNS_YEAR+1}: {current_stock['ytd_return']:+.1f}%" if current_stock.get('ytd_return') is not None else ""
        enrichment += f"\n  VNQ (REIT Index) YTD {RETURNS_YEAR+1}: {current_stock['vnq_ytd']:+.1f}%" if current_stock.get('vnq_ytd') is not None else ""
    
    prompt = f"""REIT compensation analysis (~600-800 words). You are advising this management team — preparing them for what their board and comp committee will ask.
{cn} ({tk}) | {pt} | {co_d['reit_type'].iloc[0]} | HQ: {hq} | Mkt Cap ${mc/1e9:.2f}B
EXECUTIVES:\n{chr(10).join(esecs)}
{rl}
Budget: ${tb:,.0f} ({ordinal(bp)} pctl vs {len(pcos)} peers)
FY{RETURNS_YEAR} Returns: {tk} 1-Yr {fmt_return(r.get('return_1y'))} ({ordinal(ret_pct)} pctl, {quartile_label(ret_pct)}) | 3-Yr {fmt_return(r.get('return_3y'))} | YTD {RETURNS_YEAR+1} {fmt_return(r.get('return_ytd'))}
Peer Avg: 1-Yr {fmt_return(np.mean(p1) if p1 else None)} | 3-Yr {fmt_return(np.mean(p3) if p3 else None)}
FTSE Nareit: 1-Yr {fmt_return(vnq.get('return_1y'))} | 3-Yr {fmt_return(vnq.get('return_3y'))} | YTD {RETURNS_YEAR+1} {fmt_return(vnq.get('return_ytd'))}
Peers: {peer_desc} | Tickers: {', '.join(tickers)}{excl_note}{enrichment}

NOTE: Compensation data is from the FY{FY_YEAR} DEF 14A proxy filing (filed in {FY_YEAR+1}). Returns are 1-yr and 3-yr through Dec 31, {RETURNS_YEAR}, plus YTD {RETURNS_YEAR+1}. Frame the analysis as: how has the compensation structure approved by the board in the {FY_YEAR} proxy performed against {RETURNS_YEAR} and current shareholder returns?
CRITICAL: Only reference return figures explicitly provided above. Do NOT invent, estimate, or reference any return data not given. Do NOT reference years or periods for which no data is provided.

CRITICAL FORMAT INSTRUCTIONS: You MUST include the exact section markers shown below on their own line before each section. These markers control chart placement. Do not skip any markers.

[SECTION:POSITIONING]
<h4>Executive Compensation Overview</h4>
Opening assessment: Company context, peer group with company names (note if cross-sector), and overall compensation positioning. Then each exec: positioning, comp mix vs peer mix, assessment (2-3 sent each). If any executive is flagged as [Partial Yr], note their compensation reflects a partial year and should not be compared at face value — do NOT say pay is "low" or "below peers" when it simply reflects incomplete tenure. Focus on comp structure and mix instead. If ALL executives are partial year, lead with that context and frame the analysis around structure, equity alignment, and forward-looking positioning rather than peer dollar comparisons. If any executive is flagged as [WIDENED], note the peer group was widened beyond the primary peer set.

[SECTION:MIX]
<h4>Compensation Mix & Structure</h4>
Overall comp mix philosophy and how the company's approach to salary/cash/equity split compares to peers. CEO/CFO ratio analysis. (3-4 sent)

[SECTION:RETURNS]
<h4>FY{RETURNS_YEAR} Performance & Pay Alignment</h4>
PAY-FOR-PERFORMANCE: Compare comp quartile vs returns quartile using the {RETURNS_YEAR} returns AND YTD {RETURNS_YEAR+1} stock performance provided above. If CD&A data is available, reference the company's stated performance metrics (AFFO targets, same-store NOI, etc.) and whether recent earnings suggest they are tracking. Advocate for management where data supports it. (3-4 sent)

[SECTION:WATCH]
<h4>Board Considerations</h4>
Based on CD&A compensation structure, recent earnings trajectory, and stock performance, flag 2-3 things management should be prepared to address with the board. Frame as "management should be prepared to discuss..." not prescriptive. (2-3 sent)

Summary with peer group disclosure including any excluded companies (2-3 sent, list all peer tickers)
DISCLAIMER at end: "Note: This analysis is based on SEC DEF 14A proxy data, publicly available earnings releases, and market data. Verify all information against original filings before making decisions."{en}
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=2000, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

# ============================================================
# PDF (enhanced with percentile cards and peer tables)
# ============================================================
# ============================================================
# CHARTS — Plotly visuals for Full Analysis report
# ============================================================
import plotly.graph_objects as go

CHART_COLORS = {
    'primary': '#1a365d',    # navy
    'secondary': '#234578',  # lighter navy
    'accent': '#f59e0b',     # amber
    'danger': '#dc2626',     # red
    'muted': '#94a3b8',      # slate
    'bg': '#f8fafc',         # light bg
    'text': '#0f172a',       # dark text
    'salary': '#1a365d',
    'cash': '#0ea5e9',
    'equity': '#8b5cf6',
}

def chart_comp_mix(co_d, peers, pt, all_df=None, mcap_min=0, mcap_max=50.0):
    """Stacked horizontal bar: company comp mix vs peer median."""
    ps = get_peer_stats(peers)
    tk = co_d['ticker'].iloc[0]
    MIN_PEERS = 5
    wide_ps = None
    if all_df is not None:
        wide_base = all_df[all_df['ticker'] != tk].copy()
        if mcap_max >= 50.0:
            wide_base = wide_base[(wide_base['market_cap'] >= mcap_min*1e9) | (wide_base['market_cap'].isna())]
        else:
            wide_base = wide_base[((wide_base['market_cap'] >= mcap_min*1e9) & (wide_base['market_cap'] <= mcap_max*1e9)) | (wide_base['market_cap'].isna())]
        wide_ps = get_peer_stats(wide_base)
    fig = go.Figure()
    labels = []
    sal_pcts = []; cash_pcts = []; eq_pcts = []
    # Company execs
    for _, rw in sort_by_position(co_d).iterrows():
        if rw['comp_source'] == 'external_manager': continue
        tc = rw['total_comp'] if pd.notna(rw['total_comp']) and rw['total_comp'] > 0 else 1
        s = (rw['base_salary'] or 0) / tc * 100
        c = (rw['cash_bonus_incentive'] or 0) / tc * 100
        e = (rw['stock_based_comp'] or 0) / tc * 100
        pos_d = POSITION_DISPLAY.get(rw['position'], rw['position'])
        labels.append(f"{rw['last_name']} ({pos_d})")
        sal_pcts.append(round(s, 1)); cash_pcts.append(round(c, 1)); eq_pcts.append(round(e, 1))
    # Peer median — use widened if thin
    for pos in ['CEO','CFO','COO','CIO','GC','CAO']:
        pp = ps[ps['position']==pos]
        use_pp = pp
        suffix = ''
        if len(pp) < MIN_PEERS and wide_ps is not None:
            pp_wide = wide_ps[wide_ps['position']==pos]
            if len(pp_wide) >= len(pp):
                use_pp = pp_wide
                suffix = ' *'
        if len(use_pp) < 2: continue
        tc_med = use_pp['total_comp'].median()
        if pd.isna(tc_med) or tc_med <= 0: continue
        s_med = use_pp['base_salary'].median() / tc_med * 100
        c_med = use_pp['cash_bonus_incentive'].median() / tc_med * 100
        e_med = use_pp['stock_based_comp'].median() / tc_med * 100
        labels.append(f"Peer {POSITION_DISPLAY.get(pos, pos)}{suffix}")
        sal_pcts.append(round(s_med, 1)); cash_pcts.append(round(c_med, 1)); eq_pcts.append(round(e_med, 1))
    fig.add_trace(go.Bar(name='Base Salary', y=labels, x=sal_pcts, orientation='h', marker_color=CHART_COLORS['salary'], text=[f'{v:.0f}%' for v in sal_pcts], textposition='inside', textfont=dict(color='white', size=11)))
    fig.add_trace(go.Bar(name='Cash Bonus', y=labels, x=cash_pcts, orientation='h', marker_color=CHART_COLORS['cash'], text=[f'{v:.0f}%' for v in cash_pcts], textposition='inside', textfont=dict(color='white', size=11)))
    fig.add_trace(go.Bar(name='Non-Cash Equity', y=labels, x=eq_pcts, orientation='h', marker_color=CHART_COLORS['equity'], text=[f'{v:.0f}%' for v in eq_pcts], textposition='inside', textfont=dict(color='white', size=11)))
    fig.update_layout(barmode='stack', height=max(250, len(labels)*42+30), margin=dict(l=10, r=10, t=60, b=10),
        title=dict(text='Compensation Mix: Company vs Peer Median', font=dict(size=14, color=CHART_COLORS['text']), y=0.97),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, font=dict(size=11)),
        xaxis=dict(title='% of Total Compensation', range=[0, 100], showgrid=False),
        yaxis=dict(autorange='reversed'), plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Inter, Helvetica, Arial, sans-serif'))
    return fig

def chart_pay_performance(co_d, peers, ret_data, pt):
    """Scatter: comp percentile vs returns percentile for each company."""
    ps = get_peer_stats(peers)
    tickers = sorted(ps['ticker'].unique())
    tk = co_d['ticker'].iloc[0]
    # Get total comp percentile and return percentile for each company
    all_tc = ps.groupby('ticker')['total_comp'].sum()
    ret_1y = {t: ret_data.get(t, {}).get('return_1y') for t in tickers}
    ret_series = pd.Series({t: v for t, v in ret_1y.items() if v is not None})
    x_vals = []; y_vals = []; texts = []; colors = []; sizes = []
    for t in tickers:
        if t not in all_tc or t not in ret_series: continue
        comp_pct = percentile_rank(all_tc[t], all_tc)
        ret_pct = percentile_rank(ret_series[t], ret_series)
        if comp_pct is None or ret_pct is None: continue
        x_vals.append(comp_pct); y_vals.append(ret_pct)
        cn = ps[ps['ticker']==t]['company_name'].iloc[0] if not ps[ps['ticker']==t].empty else t
        texts.append(f"{t}<br>{cn[:25]}")
        colors.append(CHART_COLORS['accent'] if t == tk else CHART_COLORS['muted'])
        sizes.append(14 if t == tk else 9)
    # Add subject company from co_d if not in peers
    if tk not in [t for t in tickers if t in all_tc.index]:
        co_tc = co_d['total_comp'].sum()
        co_ret = ret_data.get(tk, {}).get('return_1y')
        if co_ret is not None:
            comp_pct = percentile_rank(co_tc, all_tc)
            ret_pct = percentile_rank(co_ret, ret_series)
            if comp_pct is not None and ret_pct is not None:
                x_vals.append(comp_pct); y_vals.append(ret_pct)
                texts.append(f"{tk}<br>{co_d['company_name'].iloc[0][:25]}")
                colors.append(CHART_COLORS['accent']); sizes.append(14)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='markers+text', text=[t.split('<br>')[0] for t in texts],
        textposition='top center', textfont=dict(size=10), hovertext=texts,
        marker=dict(color=colors, size=sizes, line=dict(width=1, color='white'))))
    # Quadrant lines at 50th percentile
    fig.add_hline(y=50, line_dash='dot', line_color='#cbd5e1', line_width=1)
    fig.add_vline(x=50, line_dash='dot', line_color='#cbd5e1', line_width=1)
    # Quadrant labels
    fig.add_annotation(x=25, y=90, text='Low Comp / High Returns', showarrow=False, font=dict(size=9, color='#b8860b'), opacity=0.6)
    fig.add_annotation(x=75, y=90, text='High Comp / High Returns', showarrow=False, font=dict(size=9, color='#64748b'), opacity=0.6)
    fig.add_annotation(x=25, y=10, text='Low Comp / Low Returns', showarrow=False, font=dict(size=9, color='#64748b'), opacity=0.6)
    fig.add_annotation(x=75, y=10, text='High Comp / Low Returns', showarrow=False, font=dict(size=9, color='#dc2626'), opacity=0.6)
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10),
        title=dict(text='Pay-for-Performance: Compensation vs Returns Percentile', font=dict(size=14, color=CHART_COLORS['text'])),
        xaxis=dict(title='Total Comp Percentile', range=[0, 100], showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(title='1-Year Return Percentile', range=[0, 100], showgrid=True, gridcolor='#f1f5f9'),
        plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
        font=dict(family='Inter, Helvetica, Arial, sans-serif'))
    return fig

def chart_returns_comparison(tk, ret_data, peer_tickers, pt):
    """Grouped bar: company vs peer avg vs FTSE Nareit returns."""
    r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    p1 = [ret_data.get(t,{}).get('return_1y') for t in peer_tickers if ret_data.get(t,{}).get('return_1y') is not None]
    p3 = [ret_data.get(t,{}).get('return_3y') for t in peer_tickers if ret_data.get(t,{}).get('return_3y') is not None]
    categories = ['1-Year Return', '3-Year Return']
    co_vals = [r.get('return_1y'), r.get('return_3y')]
    peer_vals = [np.mean(p1) if p1 else None, np.mean(p3) if p3 else None]
    vnq_vals = [vnq.get('return_1y'), vnq.get('return_3y')]
    fig = go.Figure()
    fig.add_trace(go.Bar(name=tk, x=categories, y=co_vals, marker_color=CHART_COLORS['accent'],
        text=[f'{v:+.1f}%' if v is not None else 'N/A' for v in co_vals], textposition='outside', textfont=dict(size=12, color=CHART_COLORS['text'])))
    fig.add_trace(go.Bar(name='Peer Avg', x=categories, y=peer_vals, marker_color=CHART_COLORS['primary'],
        text=[f'{v:+.1f}%' if v is not None else 'N/A' for v in peer_vals], textposition='outside', textfont=dict(size=12, color=CHART_COLORS['text'])))
    fig.add_trace(go.Bar(name='FTSE Nareit', x=categories, y=vnq_vals, marker_color=CHART_COLORS['muted'],
        text=[f'{v:+.1f}%' if v is not None else 'N/A' for v in vnq_vals], textposition='outside', textfont=dict(size=12, color=CHART_COLORS['text'])))
    y_min = min([v for v in co_vals + peer_vals + vnq_vals if v is not None] or [0]) - 5
    y_max = max([v for v in co_vals + peer_vals + vnq_vals if v is not None] or [0]) + 8
    fig.update_layout(barmode='group', height=380, margin=dict(l=10, r=10, t=70, b=10),
        title=dict(text=f'Shareholder Returns: {tk} vs Peers vs FTSE Nareit', font=dict(size=14, color=CHART_COLORS['text']), y=0.97),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, font=dict(size=11)),
        yaxis=dict(title='Return (%)', range=[y_min, y_max], showgrid=True, gridcolor='#f1f5f9', zeroline=True, zerolinecolor='#cbd5e1'),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Inter, Helvetica, Arial, sans-serif'))
    return fig

def chart_exec_positioning(co_d, peers, all_df=None, mcap_min=0, mcap_max=50.0):
    """Horizontal bar: each exec's total comp percentile vs peers. Auto-widens thin positions."""
    ps = get_peer_stats(peers)
    tk = co_d['ticker'].iloc[0]
    MIN_PEERS = 5
    wide_ps = None
    if all_df is not None:
        wide_base = all_df[all_df['ticker'] != tk].copy()
        if mcap_max >= 50.0:
            wide_base = wide_base[(wide_base['market_cap'] >= mcap_min*1e9) | (wide_base['market_cap'].isna())]
        else:
            wide_base = wide_base[((wide_base['market_cap'] >= mcap_min*1e9) & (wide_base['market_cap'] <= mcap_max*1e9)) | (wide_base['market_cap'].isna())]
        wide_ps = get_peer_stats(wide_base)
    labels = []; pcts = []; colors = []; annotations = []
    for _, rw in sort_by_position(co_d).iterrows():
        if rw['comp_source'] == 'external_manager': continue
        pp = ps[ps['position']==rw['position']]
        n_pos = len(pp[pp['total_comp'].notna()])
        widened = False
        if n_pos < MIN_PEERS and wide_ps is not None:
            pp_wide = wide_ps[wide_ps['position']==rw['position']]
            if len(pp_wide[pp_wide['total_comp'].notna()]) >= n_pos:
                pp = pp_wide
                widened = True
        pct = percentile_rank(rw['total_comp'], pp['total_comp'])
        if pct is None: continue
        pos_d = POSITION_DISPLAY.get(rw['position'], rw['position'])
        suffix = ' *' if widened else ''
        labels.append(f"{rw['last_name']} ({pos_d}){suffix}")
        pcts.append(pct)
        colors.append(CHART_COLORS['accent'] if pct >= 50 else CHART_COLORS['primary'])
        annotations.append(widened)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=pcts, orientation='h', marker_color=colors,
        text=[f'{p}th' for p in pcts], textposition='outside', textfont=dict(size=12, color=CHART_COLORS['text'])))
    fig.add_vline(x=50, line_dash='dot', line_color='#dc2626', line_width=1, annotation_text='50th pctl', annotation_position='top')
    fig.add_vline(x=25, line_dash='dot', line_color='#cbd5e1', line_width=1)
    fig.add_vline(x=75, line_dash='dot', line_color='#cbd5e1', line_width=1)
    footnote = '  * = widened to all REITs in market cap range' if any(annotations) else ''
    fig.update_layout(height=max(200, len(labels)*50), margin=dict(l=10, r=40, t=40, b=30),
        title=dict(text='Executive Compensation Positioning (Total Comp Percentile)', font=dict(size=14, color=CHART_COLORS['text'])),
        xaxis=dict(title='Percentile vs Peers', range=[0, 100], showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(autorange='reversed'),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Inter, Helvetica, Arial, sans-serif'))
    if footnote:
        fig.add_annotation(text=footnote, xref='paper', yref='paper', x=0, y=-0.15, showarrow=False, font=dict(size=10, color='#94a3b8'))
    return fig

# ============================================================
# PDF
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
    hs = ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#1a365d'), spaceAfter=4, spaceBefore=10)
    prs_h = ParagraphStyle('PRH', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#0f172a'), spaceAfter=4, spaceBefore=8)
    story.append(Paragraph("Velarion Company Intelligence", ts))
    story.append(Paragraph(f"REIT Compensation Analysis: {cn} ({tk})", ss))
    story.append(Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y')} | FY{FY_YEAR} Proxy Data | Returns through Dec 31, {RETURNS_YEAR}", ds))
    story.append(Spacer(1, 8))
    mc = co_d['market_cap'].iloc[0]; pt = co_d['property_type'].iloc[0]; hq = f"{co_d['hq_city'].iloc[0]}, {co_d['hq_state'].iloc[0]}"
    r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    info = [['Company', cn, 'Property Type', pt], ['Ticker', tk, 'Market Cap', fmt_mcap(mc)],
            ['HQ', hq, 'REIT Type', co_d['reit_type'].iloc[0]],
            [f'1-Yr Return (FY{RETURNS_YEAR})', fmt_return(r.get('return_1y')), 'FTSE Nareit 1-Yr', fmt_return(vnq.get('return_1y'))],
            ['3-Yr Return', fmt_return(r.get('return_3y')), 'FTSE Nareit 3-Yr', fmt_return(vnq.get('return_3y'))],
            [f'YTD {RETURNS_YEAR+1}', fmt_return(r.get('return_ytd')), f'FTSE Nareit YTD {RETURNS_YEAR+1}', fmt_return(vnq.get('return_ytd'))]]
    it = Table(info, colWidths=[1.3*inch, 2.2*inch, 1.2*inch, 2.2*inch])
    it.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),8.5),
        ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),
        ('TEXTCOLOR',(0,0),(0,-1),colors.HexColor('#475569')),('TEXTCOLOR',(2,0),(2,-1),colors.HexColor('#475569')),
        ('BOTTOMPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),3),
        ('LINEBELOW',(0,-1),(-1,-1),0.5,colors.HexColor('#e2e8f0'))]))
    story.append(it); story.append(Spacer(1, 10))
    ps = get_peer_stats(filt); prp = ps[ps['property_type'] == pt]
    n_co, mcr, peer_tickers, _ = peer_context_str(filt, pt)
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
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f8f6f3')),('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#475569')),
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
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f8f6f3')),
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
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f8f6f3')),
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
peer_groups_df = load_peer_groups()

# Separate REIT companies from non-REIT peer companies for dropdown
reit_df = df[~df['property_type'].str.startswith('Peer', na=True)].copy()
all_tickers = list(df['ticker'].unique())
ret_data = load_total_returns(all_tickers)
# Company dropdown: REIT-only
reit_tickers = sorted(reit_df['ticker'].unique())
co_labels = {clabel(t, reit_df[reit_df['ticker']==t]['company_name'].iloc[0]): t for t in reit_tickers if not reit_df[reit_df['ticker']==t].empty}
co_opts = list(co_labels.keys())
all_props = sorted(reit_df['property_type'].dropna().unique())
PLACEHOLDER = "-- Select your company --"

def _get_not_in_db_reason(peer_name):
    """Return reason why a peer company is not in the database."""
    name_lower = str(peer_name).lower().strip()
    for key, reason in ACQUIRED_COMPANIES.items():
        if key in name_lower:
            return reason
    return "May be private, acquired, or outside current coverage"

def _build_proxy_peer_data(ticker, peer_groups_df, df):
    """Build proxy peer group data for a company. Returns (peer_df, in_univ_tickers, in_univ_df)."""
    if peer_groups_df.empty:
        return pd.DataFrame(), [], pd.DataFrame()
    co_peers = peer_groups_df[peer_groups_df['ticker'] == ticker].copy()
    if co_peers.empty:
        return pd.DataFrame(), [], pd.DataFrame()
    in_univ = co_peers[co_peers['in_universe'] == True]
    in_univ_tickers = sorted(in_univ['peer_ticker'].dropna().unique())
    # Get comp data for in-universe peers
    in_univ_df = df[df['ticker'].isin(in_univ_tickers)].copy()
    return co_peers, in_univ_tickers, in_univ_df

# GOLD SAMPLE REPORT BUTTON (right-aligned)
_spacer_l, _btn_col = st.columns([4, 1])
with _btn_col:
    try:
        with open("reit_exec_changes_20260215.pdf", "rb") as _pdf_f:
            st.download_button("\U0001F4C4 Sample Monthly Report", data=_pdf_f.read(), file_name="Velarion_REIT_Exec_Changes_Sep2025.pdf", mime="application/pdf",
                key="sample_report_btn")
    except Exception:
        pass

# HEADER
st.markdown('<div class="main-header"><h1>Velarion Company Intelligence</h1><p>REIT Executive Compensation Benchmarking \u2014 FY2024 Proxy Data</p></div>', unsafe_allow_html=True)
st.markdown(f'<div class="intro-text">Explore executive compensation across {len(reit_tickers)} publicly traded REITs. Select a company to benchmark against its proxy-disclosed peer group, or build a custom comparison set.</div>', unsafe_allow_html=True)

# Track peer group mode: 'proxy' (default) or 'custom'
if 'peer_mode' not in st.session_state:
    st.session_state['peer_mode'] = 'proxy'

# All available company labels for peer selection (ALL companies in db, including non-REIT peers)
all_db_labels = {clabel(t, df[df['ticker']==t]['company_name'].iloc[0]): t for t in sorted(df['ticker'].unique()) if not df[df['ticker']==t].empty}
all_db_label_list = sorted(all_db_labels.keys())

# Market cap presets
MCAP_PRESETS = {
    'All Market Caps': (0, None),
    'Micro Cap (< $500M)': (0, 0.5),
    'Small Cap ($500M – $2B)': (0.5, 2.0),
    'Mid Cap ($2B – $10B)': (2.0, 10.0),
    'Large Cap ($10B – $50B)': (10.0, 50.0),
    'Mega Cap (> $50B)': (50.0, None),
    'Custom Range': (None, None),
}

def _ticker_in_mcap_range(ticker, mcap_min_b, mcap_max_b):
    """Check if a ticker falls within market cap range (in billions)."""
    co = reit_df[reit_df['ticker'] == ticker]
    if co.empty: 
        # Non-REIT peers — check in full df
        co = df[df['ticker'] == ticker]
    if co.empty: return True  # Unknown — keep
    mc = co['market_cap'].iloc[0]
    if pd.isna(mc): return True  # Unknown — keep
    mc_b = mc / 1e9
    if mcap_min_b is not None and mc_b < mcap_min_b: return False
    if mcap_max_b is not None and mc_b > mcap_max_b: return False
    return True

def _label_to_ticker(label):
    """Convert a company label back to ticker."""
    return co_labels.get(label) or all_db_labels.get(label)

# SIDEBAR
with st.sidebar:
    st.markdown('<div style="margin-top:34vh;"></div>', unsafe_allow_html=True)
    # Determine if a company is selected
    cv_selected = st.session_state.get('cv_co', PLACEHOLDER)
    has_company = cv_selected and cv_selected != PLACEHOLDER and cv_selected in co_labels
    
    if has_company:
        sel_tk = co_labels[cv_selected]
        sel_co_data = df[df['ticker'] == sel_tk]
        sel_pt = sel_co_data['property_type'].iloc[0] if not sel_co_data.empty else ""
        co_peers, proxy_tickers, proxy_peer_df = _build_proxy_peer_data(sel_tk, peer_groups_df, df)
        has_proxy_peers = len(proxy_tickers) >= 1
        # Build proxy peer labels (for pre-populating custom mode)
        proxy_peer_labels = []
        for pt in proxy_tickers:
            co_data = df[df['ticker'] == pt]
            if not co_data.empty:
                lbl = clabel(pt, co_data['company_name'].iloc[0])
                proxy_peer_labels.append(lbl)
        proxy_peer_labels = sorted(proxy_peer_labels)
    else:
        sel_tk = None; sel_pt = ""; co_peers = pd.DataFrame(); proxy_tickers = []; proxy_peer_df = pd.DataFrame(); has_proxy_peers = False; proxy_peer_labels = []
    
    # Mode toggle
    if has_company and has_proxy_peers:
        st.markdown("## Peer Group")
        # Check if we need to reset to proxy (company changed)
        if st.session_state.pop('_reset_to_proxy', False):
            st.session_state['peer_mode_radio'] = "Proxy Peers"
        elif 'peer_mode_radio' not in st.session_state:
            st.session_state['peer_mode_radio'] = "Proxy Peers"
        prev_mode = st.session_state.get('peer_mode', 'proxy')
        mode = st.radio("Benchmarking source", ["Proxy Peers", "Custom Peer Group"], 
                       key="peer_mode_radio", label_visibility="collapsed")
        new_mode = 'proxy' if mode == "Proxy Peers" else 'custom'
        
        # Detect toggle from proxy to custom — pre-populate with proxy peers
        if prev_mode == 'proxy' and new_mode == 'custom':
            st.session_state['custom_peer_sel'] = proxy_peer_labels
            st.session_state['_custom_mcap_preset'] = 'All Market Caps'
        # Detect toggle from custom to proxy — reset custom state
        elif prev_mode == 'custom' and new_mode == 'proxy':
            if 'custom_peer_sel' in st.session_state:
                del st.session_state['custom_peer_sel']
            if '_custom_mcap_preset' in st.session_state:
                del st.session_state['_custom_mcap_preset']
        
        st.session_state['peer_mode'] = new_mode
        
        if new_mode == 'proxy':
            co_name_display = sel_co_data["company_name"].iloc[0] if not sel_co_data.empty else sel_tk
            st.markdown(f'<div class="filter-note">\U0001F3AF Benchmarking uses peer group from <strong>{co_name_display}</strong>\'s FY{FY_YEAR} DEF 14A proxy filing ({len(proxy_tickers)} peers in database).</div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.75rem;color:#94a3b8;margin-top:0.8rem;padding:0.5rem;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0;">\U0001F512 Custom filters available when "Custom Peer Group" is selected above.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="filter-note">\U0001F527 Starting from proxy peers. Edit companies, adjust market cap, or add by property type below.</div>', unsafe_allow_html=True)
    elif has_company:
        st.markdown("## Custom Peer Group Filters")
        st.session_state['peer_mode'] = 'custom'
        st.markdown(f'<div class="filter-note">\u26A0\uFE0F No proxy peer group found in {sel_tk}\'s FY{FY_YEAR} DEF 14A filing. Defaulting to {sel_pt} REITs. Use Custom Peer Group Filters to refine.</div>', unsafe_allow_html=True)
    else:
        st.markdown("## Peer Group")
        st.session_state['peer_mode'] = 'proxy'  # No mode selection when no company
        st.markdown('<div class="filter-note">\U0001F4A1 Select a company to auto-load its proxy peer group.</div>', unsafe_allow_html=True)
        # Clear any stale custom state
        for k in ['custom_peer_sel', '_custom_mcap_preset', '_mcap_removed', '_add_by_pt', '_pt_add_sel']:
            st.session_state.pop(k, None)

    # ---- CUSTOM MODE FILTERS ----
    if st.session_state['peer_mode'] == 'custom' and has_company:
        
        # === 1. PEER COMPANIES (primary control) ===
        st.markdown("### Peer Companies")
        if has_company and has_proxy_peers:
            st.markdown('<div style="font-size:0.78rem;color:#64748b;margin-bottom:0.3rem;">Starting from proxy peers. Add or remove companies.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:0.78rem;color:#64748b;margin-bottom:0.3rem;">Select companies for comparison.</div>', unsafe_allow_html=True)
        
        # Initialize custom peer selection
        if 'custom_peer_sel' not in st.session_state:
            if has_company and has_proxy_peers:
                st.session_state['custom_peer_sel'] = proxy_peer_labels
            elif has_company and sel_pt:
                # No proxy peers — default to same property type
                pt_peers = reit_df[(reit_df['property_type'] == sel_pt) & (reit_df['ticker'] != sel_tk)]
                pt_labels = sorted([clabel(t, pt_peers[pt_peers['ticker']==t]['company_name'].iloc[0]) for t in pt_peers['ticker'].unique() if not pt_peers[pt_peers['ticker']==t].empty])
                st.session_state['custom_peer_sel'] = pt_labels
            else:
                st.session_state['custom_peer_sel'] = []
        
        sel_companies = st.multiselect("Peer companies", all_db_label_list, 
                                        label_visibility="collapsed", key="custom_peer_sel")
        
        # === 2. MARKET CAP RANGE ===
        st.markdown("### Market Cap Range")
        if '_custom_mcap_preset' not in st.session_state:
            st.session_state['_custom_mcap_preset'] = 'All Market Caps'
        mcap_choice = st.selectbox("Market cap range", list(MCAP_PRESETS.keys()), 
                                    label_visibility="collapsed", key="_custom_mcap_preset")
        
        mcap_min_b, mcap_max_b = MCAP_PRESETS[mcap_choice]
        
        # Custom range inputs
        if mcap_choice == 'Custom Range':
            cc1, cc2 = st.columns(2)
            with cc1:
                mcap_min_b = st.number_input("Min ($B)", min_value=0.0, value=0.0, step=0.5, key="_custom_mcap_min")
            with cc2:
                mcap_max_b = st.number_input("Max ($B)", min_value=0.0, value=50.0, step=0.5, key="_custom_mcap_max")
                if mcap_max_b == 0: mcap_max_b = None
        
        # Convert to raw values for downstream (billions to raw)
        mcap_min = mcap_min_b if mcap_min_b is not None else 0.0
        mcap_max = mcap_max_b if mcap_max_b is not None else 50.0
        
        # Filter selected companies by market cap range (no rerun — just filter downstream)
        if mcap_choice != 'All Market Caps':
            filtered_companies = []
            removed_by_mcap = []
            for lbl in sel_companies:
                tk = _label_to_ticker(lbl)
                if tk and not _ticker_in_mcap_range(tk, mcap_min_b, mcap_max_b):
                    removed_by_mcap.append(tk)
                else:
                    filtered_companies.append(lbl)
            if removed_by_mcap:
                st.markdown(f'<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.75rem;color:#92400e;margin:0.3rem 0;">\u26A0\uFE0F {len(removed_by_mcap)} companies outside market cap range excluded from analysis: {", ".join(removed_by_mcap)}</div>', unsafe_allow_html=True)
            sel_companies = filtered_companies
        
        # === 3. ADD BY PROPERTY TYPE (bulk-add tool) ===
        add_by_pt = st.checkbox("Add companies to peer list by Property Type", key="_add_by_pt")
        if add_by_pt:
            pt_options = sorted(reit_df['property_type'].dropna().unique())
            pt_add = st.multiselect("Select property types to add", pt_options, 
                                     label_visibility="collapsed", key="_pt_add_sel")
            if pt_add:
                # Find all companies matching the selected property types AND within market cap range
                pt_eligible = reit_df[reit_df['property_type'].isin(pt_add)].copy()
                new_labels = []
                for _, row in pt_eligible.drop_duplicates('ticker').iterrows():
                    tk = row['ticker']
                    if _ticker_in_mcap_range(tk, mcap_min_b, mcap_max_b):
                        lbl = clabel(tk, row['company_name'])
                        if lbl not in sel_companies:
                            new_labels.append(lbl)
                if new_labels:
                    # Add to sel_companies for this render pass (downstream will pick them up)
                    sel_companies = sorted(set(sel_companies + new_labels))
                    st.markdown(f'<div style="background:#fef9ee;border:1px solid #d4a017;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.75rem;color:#92400e;margin:0.3rem 0;">\u2705 Added {len(new_labels)} companies from {", ".join(pt_add)} to analysis</div>', unsafe_allow_html=True)
        
        # Track changes vs proxy peer baseline
        sel_tickers = set(_label_to_ticker(c) for c in sel_companies if _label_to_ticker(c))
        proxy_tk_set = set(proxy_tickers) if has_proxy_peers else set()
        removed_from_proxy = sorted(proxy_tk_set - sel_tickers) if proxy_tk_set else []
        added_beyond_proxy = sorted(sel_tickers - proxy_tk_set) if proxy_tk_set else []
        excluded_tickers = removed_from_proxy  # For downstream compatibility
        
        # Set sel_prop to all (property type no longer used as filter)
        sel_prop = all_props
    else:
        # Proxy mode defaults
        sel_prop = all_props
        mcap_min = 0.0; mcap_max = 50.0
        sel_companies = []; excluded_tickers = []

# BUILD FILTERED DATASET
if st.session_state.get('peer_mode') == 'proxy' and has_company and has_proxy_peers:
    # Proxy mode: filter to proxy peer tickers + subject company
    all_proxy_tks = list(set(proxy_tickers + [sel_tk]))
    filt = df[df['ticker'].isin(all_proxy_tks)].copy()
    filt_no_pos = filt.copy()
    excluded_tickers = []
else:
    # Custom mode: use selected companies from sidebar
    sel_co_tickers = [_label_to_ticker(c) for c in sel_companies if _label_to_ticker(c)]
    filt = df[df['ticker'].isin(sel_co_tickers)].copy()
    filt_no_pos = filt.copy()
peer_stats_df = get_peer_stats(filt)

# METRICS — context-aware
c1,c2,c3,c4,c5 = st.columns(5)
cv_selected = st.session_state.get('cv_co', PLACEHOLDER)
if cv_selected and cv_selected != PLACEHOLDER and cv_selected in co_labels:
    cv_tk = co_labels[cv_selected]
    peers_in_filt = filt[filt['ticker'] != cv_tk]
    n_peer_cos = peers_in_filt['ticker'].nunique()
    peer_stats_for_kpi = get_peer_stats(peers_in_filt)
    mode_label = "proxy peers" if st.session_state.get('peer_mode') == 'proxy' else "custom peers"
    with c1: st.markdown(f'<div class="metric-card"><div class="label">Peer Companies</div><div class="value">{n_peer_cos}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="label">Executives</div><div class="value">{len(peer_stats_for_kpi)}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="label">Med. Salary</div><div class="value">{fmt_dollars(peer_stats_for_kpi["base_salary"].median())}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="label">Med. Total Comp</div><div class="value">{fmt_dollars(peer_stats_for_kpi["total_comp"].median())}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><div class="label">Med. Mkt Cap</div><div class="value">{fmt_mcap(peers_in_filt["market_cap"].median())}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
else:
    # No company selected — show full REIT universe
    reit_stats = get_peer_stats(reit_df)
    with c1: st.markdown(f'<div class="metric-card"><div class="label">Companies</div><div class="value">{reit_df["ticker"].nunique()}</div><div class="sub">in universe</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="label">Executives</div><div class="value">{len(reit_stats)}</div><div class="sub">all positions</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="label">Med. Salary</div><div class="value">{fmt_dollars(reit_stats["base_salary"].median())}</div><div class="sub">all REITs</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="label">Med. Total Comp</div><div class="value">{fmt_dollars(reit_stats["total_comp"].median())}</div><div class="sub">all REITs</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><div class="label">Med. Mkt Cap</div><div class="value">{fmt_mcap(reit_df["market_cap"].median())}</div><div class="sub">all REITs</div></div>', unsafe_allow_html=True)
st.markdown("")

# COMPANY VIEW
st.markdown("#### Company Compensation Overview")
cv_opts = [PLACEHOLDER] + co_opts
cv_selected_val = st.session_state.get('cv_co', PLACEHOLDER)
if not cv_selected_val or cv_selected_val == PLACEHOLDER:
    st.markdown('<div class="tab-instruction">\U0001F4A1 Select a company to view executive compensation and generate AI-powered analysis.</div>', unsafe_allow_html=True)
_dd_col, _ = st.columns([1, 1])
with _dd_col:
    sel3 = st.selectbox("cv", cv_opts, key="cv_co", label_visibility="collapsed")
if sel3 and sel3 != PLACEHOLDER:
    prev_cv = st.session_state.get('_prev_cv')
    if prev_cv != sel3:
        st.session_state['_prev_cv'] = sel3
        st.session_state['selected_company'] = sel3
        st.session_state['peer_mode'] = 'proxy'  # Reset to proxy mode on company change
        st.session_state['_reset_to_proxy'] = True  # Flag for sidebar to reset radio
        # Clear custom peer state
        if 'custom_peer_sel' in st.session_state:
            del st.session_state['custom_peer_sel']
        if '_custom_mcap_preset' in st.session_state:
            del st.session_state['_custom_mcap_preset']
        # Clear all toggle states
        for k in ['show_league', 'show_comp_table', 'lk_rpt', 'lk_tk', 'fp_lk_rpt', 'lk_addendum', 'lk_user_context']:
            st.session_state.pop(k, None)
        # Clear per-exec toggle states
        for k in list(st.session_state.keys()):
            if k.startswith(('show_peers_', 'cv_peer_', 'exec_analysis_', 'exec_narr_')):
                del st.session_state[k]
        st.rerun()
    stk3 = co_labels[sel3]; cd3 = df[df['ticker']==stk3]
    if not cd3.empty:
        cn3 = cd3['company_name'].iloc[0]; pt3 = cd3['property_type'].iloc[0]
        st.markdown(f"### {cn3} ({stk3})")
        c1,c2,c3 = st.columns(3)
        c1.metric("HQ", f"{cd3['hq_city'].iloc[0]}, {cd3['hq_state'].iloc[0]}"); c2.metric("Property Type", pt3); c3.metric("Market Cap", fmt_mcap(cd3['market_cap'].iloc[0]))
        cr3 = ret_data.get(stk3, {}); vnq3 = ret_data.get(REIT_INDEX_TICKER, {})
        if cr3:
            r1,r2,r3,r4,r5,r6 = st.columns(6)
            r1.metric(f"{stk3} 1-Yr (FY{RETURNS_YEAR})", fmt_return(cr3.get('return_1y')))
            r2.metric(f"{stk3} 3-Yr", fmt_return(cr3.get('return_3y')))
            r3.metric(f"{stk3} YTD {RETURNS_YEAR+1}", fmt_return(cr3.get('return_ytd')))
            r4.metric(f"FTSE Nareit 1-Yr", fmt_return(vnq3.get('return_1y')))
            r5.metric(f"FTSE Nareit 3-Yr", fmt_return(vnq3.get('return_3y')))
            r6.metric(f"FTSE Nareit YTD {RETURNS_YEAR+1}", fmt_return(vnq3.get('return_ytd')))
        ea3 = is_ext_advised(cd3, df)
        if ea3: st.markdown(f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:0.6rem 1rem;font-size:0.83rem;color:#92400e;margin:0.5rem 0;">\u26A0\uFE0F {get_ext_note(cd3)}</div>', unsafe_allow_html=True)
        components.html('<button onclick="window.parent.print()" style="background:#475569;color:white;border:none;border-radius:6px;padding:5px 14px;font-size:0.75rem;font-weight:600;cursor:pointer;float:right;">\U0001F5A8 Print This Page</button>', height=35)
        
        # ---- PROXY-DISCLOSED PEER GROUP ----
        co_peers_display, proxy_tks_display, _ = _build_proxy_peer_data(stk3, peer_groups_df, df)
        if not co_peers_display.empty:
            st.markdown("---")
            is_proxy_mode = st.session_state.get('peer_mode') == 'proxy'
            in_univ = co_peers_display[co_peers_display['in_universe'] == True]
            out_univ = co_peers_display[co_peers_display['in_universe'] == False]
            active_tag = " \u2705 ACTIVE" if is_proxy_mode else ""
            with st.expander(f"Proxy-Disclosed Compensation Peer Group ({len(in_univ)} of {len(co_peers_display)} in database){active_tag}", expanded=False):
                st.markdown(f'<div style="font-size:0.85rem;color:#475569;margin-bottom:0.7rem;">From {cn3}\'s FY{co_peers_display["fiscal_year"].iloc[0]} DEF 14A proxy filing \u2014 the companies their compensation committee benchmarks against.</div>', unsafe_allow_html=True)
                
                peer_html_rows = []
                for _, pr in co_peers_display.sort_values('peer_name_as_disclosed').iterrows():
                    tk_display = f" ({pr['peer_ticker']})" if pd.notna(pr.get('peer_ticker')) and pr['peer_ticker'] else ""
                    if pr.get('in_universe'):
                        badge = '<span style="background:#e8edf5;color:#1a365d;padding:1px 6px;border-radius:4px;font-size:0.7rem;font-weight:600;">IN DATABASE</span>'
                        reason_col = ""
                    else:
                        badge = '<span style="background:#fee2e2;color:#991b1b;padding:1px 6px;border-radius:4px;font-size:0.7rem;font-weight:600;">NOT IN DATABASE</span>'
                        reason = _get_not_in_db_reason(pr['peer_name_as_disclosed'])
                        reason_col = f'<span style="font-size:0.72rem;color:#991b1b;font-style:italic;">{reason}</span>'
                    peer_html_rows.append(f'<tr><td style="padding:4px 8px;font-size:0.82rem;">{pr["peer_name_as_disclosed"]}{tk_display}</td><td style="padding:4px 8px;">{badge}</td><td style="padding:4px 8px;">{reason_col}</td></tr>')
                
                peer_html = f'''<div style="max-height:500px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:0.5rem;">
                <table style="width:100%;border-collapse:collapse;">
                <thead><tr style="background:#f8f6f3;position:sticky;top:0;"><th style="padding:6px 8px;text-align:left;font-size:0.75rem;">Company</th><th style="padding:6px 8px;text-align:left;font-size:0.75rem;">Status</th><th style="padding:6px 8px;text-align:left;font-size:0.75rem;">Note</th></tr></thead>
                <tbody>{''.join(peer_html_rows)}</tbody></table></div>'''
                st.markdown(peer_html, unsafe_allow_html=True)
        
        # ---- PEER BENCHMARKING (lead with this) ----
        st.markdown("---")
        st.markdown("#### Peer Compensation Benchmarking")
        peers_only = filt_no_pos[filt_no_pos['ticker'] != stk3]
        n_co, mcr, peer_tks, _ = peer_context_str(peers_only, pt3)
        auto_peers = get_peer_stats(peers_only)
        
        # Show peer source context
        no_proxy = not proxy_tickers or len(proxy_tickers) == 0
        if st.session_state.get('peer_mode') == 'proxy':
            peer_line = f"Compared to <strong>{n_co} proxy-disclosed peer companies</strong> from {cn3}'s FY{FY_YEAR} DEF 14A filing ({', '.join(peer_tks)})"
        else:
            # Check if this is a no-proxy-peer company defaulting to property type
            if no_proxy:
                peer_line = f'<div style="background:#fffbeb;border:1px solid #d4a017;border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.5rem;font-size:0.85rem;color:#92400e;">\u26A0\uFE0F <strong>No proxy-defined compensation peer group found</strong> in {cn3}\'s FY{FY_YEAR} DEF 14A filing. Defaulted to {pt3} REITs.</div>'
                peer_line += f"Compared to <strong>{n_co} {pt3} peer companies</strong> ({', '.join(peer_tks)})"
            else:
                peer_line = f"Compared to <strong>{n_co} custom peer companies</strong> ({', '.join(peer_tks)})"
            # Show changes vs proxy baseline
            changes = []
            if hasattr(st.session_state, '__contains__') and proxy_tickers:
                r_from_p = [t for t in (set(proxy_tickers) - set(peer_tks))] if proxy_tickers else []
                a_beyond_p = [t for t in peer_tks if t not in proxy_tickers] if proxy_tickers else []
                if r_from_p:
                    changes.append(f'<span style="color:#dc2626;font-size:0.85rem;">Removed from proxy peers: {", ".join(sorted(r_from_p))}</span>')
                if a_beyond_p:
                    changes.append(f'<span style="color:#1a365d;font-size:0.85rem;">Added beyond proxy peers: {", ".join(sorted(a_beyond_p))}</span>')
            if changes:
                peer_line += "<br>" + "<br>".join(changes)
        st.markdown(f"<div style='font-size:1.0rem;color:#475569;margin:0.5rem 0;'>{peer_line}</div>", unsafe_allow_html=True)
        
        if st.session_state.get('peer_mode') == 'custom':
            if no_proxy:
                st.markdown('<div style="background:#f8f6f3;border:1px solid #d4a017;border-radius:8px;padding:0.6rem 1rem;margin:0.5rem 0 1rem 0;font-size:0.83rem;color:#78350f;">\U0001F527 Use <strong>Custom Peer Group Filters</strong> in the sidebar to further refine this peer group.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background:#f8f6f3;border:1px solid #d4a017;border-radius:8px;padding:0.6rem 1rem;margin:0.5rem 0 1rem 0;font-size:0.83rem;color:#78350f;">\U0001F527 <strong>Custom Mode:</strong> Adjust filters in the sidebar to refine your comparison set. Switch to Proxy Peers in the sidebar to use the board\'s disclosed peer group.</div>', unsafe_allow_html=True)
        cur_fp0 = filter_fingerprint(peers_only)
        # Compute custom changes vs proxy for AI context
        custom_removed = sorted(set(proxy_tickers) - set(peer_tks)) if proxy_tickers and st.session_state.get('peer_mode') == 'custom' else []
        custom_added = sorted(set(peer_tks) - set(proxy_tickers)) if proxy_tickers and st.session_state.get('peer_mode') == 'custom' else []
        # Button layout: 2x2 grid
        btn_r1a, btn_r1b = st.columns(2)
        with btn_r1a:
            if st.button("\U0001F4CB  Generate Full Compensation Analysis", key="cv_lookup_rpt", use_container_width=True):
                with st.spinner("Generating full analysis (fetching CD&A, earnings, stock data)..."):
                    st.session_state['lk_rpt'] = gen_full(cd3, peers_only, ret_data, excluded_tks=custom_removed, added_tks=custom_added, all_df=df, mcap_min=mcap_min, mcap_max=mcap_max, peer_mode=st.session_state.get('peer_mode', 'proxy'))
                    st.session_state['lk_tk'] = stk3
                    st.session_state['fp_lk_rpt'] = cur_fp0
                    # Clear any previous addendum
                    st.session_state.pop('lk_addendum', None)
                    st.session_state.pop('lk_user_context', None)
        with btn_r1b:
            if st.button("\U0001F3C6  League Tables", key="cv_league_toggle", use_container_width=True):
                st.session_state['show_league'] = not st.session_state.get('show_league', False)
        btn_r2a, btn_r2b = st.columns(2)
        with btn_r2a:
            if st.button("\U0001F4CB  Comp Summary Table", key="cv_comp_toggle", use_container_width=True):
                st.session_state['show_comp_table'] = not st.session_state.get('show_comp_table', False)
        with btn_r2b:
            proxy_url = lookup_proxy_url(cn3, FY_YEAR)
            if proxy_url:
                st.link_button("\U0001F4C4  View Proxy", proxy_url, use_container_width=True)
            else:
                st.button("\U0001F4C4  View Proxy", key="cv_proxy_btn", disabled=True, use_container_width=True, help="Proxy filing not found on SEC EDGAR")
        # Display Full Report
        if st.session_state.get('lk_tk') == stk3 and st.session_state.get('lk_rpt'):
            if st.session_state.get('fp_lk_rpt') != cur_fp0:
                st.markdown(STALE_WARNING, unsafe_allow_html=True)
            rt = st.session_state['lk_rpt']
            
            # Parse sections and interleave charts
            st.markdown(f'<div class="ai-report"><div class="ai-label">\U0001F4CB Compensation Analysis \u2014 {cn3}</div>', unsafe_allow_html=True)
            
            # Split on section markers
            import re
            section_pattern = r'\[SECTION:(POSITIONING|MIX|RETURNS|WATCH)\]'
            parts = re.split(section_pattern, rt)
            
            try:
                n_co_ctx, _, peer_tks_ctx, _ = peer_context_str(peers_only, pt3)
            except Exception:
                peer_tks_ctx = []
            
            i = 0
            while i < len(parts):
                text = parts[i].strip()
                if text and text not in ('POSITIONING', 'MIX', 'RETURNS', 'WATCH'):
                    st.markdown(text, unsafe_allow_html=True)
                elif text == 'POSITIONING':
                    if i + 1 < len(parts):
                        st.markdown(parts[i+1].strip(), unsafe_allow_html=True)
                        i += 1
                    try:
                        fig_pos = chart_exec_positioning(cd3, peers_only, all_df=df, mcap_min=mcap_min, mcap_max=mcap_max)
                        st.plotly_chart(fig_pos, use_container_width=True, key="rpt_pos_chart")
                    except Exception: pass
                elif text == 'MIX':
                    if i + 1 < len(parts):
                        st.markdown(parts[i+1].strip(), unsafe_allow_html=True)
                        i += 1
                    try:
                        fig_mix = chart_comp_mix(cd3, peers_only, pt3, all_df=df, mcap_min=mcap_min, mcap_max=mcap_max)
                        st.plotly_chart(fig_mix, use_container_width=True, key="rpt_mix_chart")
                    except Exception: pass
                elif text == 'RETURNS':
                    if i + 1 < len(parts):
                        st.markdown(parts[i+1].strip(), unsafe_allow_html=True)
                        i += 1
                    try:
                        ch1, ch2 = st.columns(2)
                        with ch1:
                            fig_ret = chart_returns_comparison(stk3, ret_data, peer_tks_ctx, pt3)
                            st.plotly_chart(fig_ret, use_container_width=True, key="rpt_ret_chart")
                        with ch2:
                            fig_pfp = chart_pay_performance(cd3, peers_only, ret_data, pt3)
                            st.plotly_chart(fig_pfp, use_container_width=True, key="rpt_pfp_chart")
                    except Exception: pass
                elif text == 'WATCH':
                    if i + 1 < len(parts):
                        st.markdown(parts[i+1].strip(), unsafe_allow_html=True)
                        i += 1
                i += 1
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Show if analysis was regenerated with user context
            if st.session_state.get('lk_user_context'):
                st.markdown(f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:6px;padding:0.5rem 0.8rem;font-size:0.78rem;color:#92400e;margin:0.5rem 0;">\U0001F504 This analysis was regenerated with additional user-provided context.</div>', unsafe_allow_html=True)
            
            # Context refinement input
            st.markdown('<div style="margin-top:1rem;padding:1rem 1.2rem;background:#fffbeb;border:1px solid #d4a017;border-left:4px solid #b8860b;border-radius:8px;">'
                '<div style="font-size:0.9rem;font-weight:700;color:#92400e;margin-bottom:0.4rem;">\U0001F4AC Refine this analysis with additional context</div>'
                '<div style="font-size:0.8rem;color:#475569;margin-bottom:0.5rem;">Add information the AI should consider \u2014 pending transactions, employment agreements, recruiting context, strategic plans. The analysis will be regenerated incorporating your context, with a footnote disclosing what was provided.</div>'
                '</div>', unsafe_allow_html=True)
            user_context = st.text_area("Additional context", placeholder="e.g., 'The company is in active negotiations for a $2B portfolio acquisition' or 'The CEO has a verbal agreement for a 3-year extension with a $1.5M base'", 
                                         label_visibility="collapsed", key="user_analysis_context", height=100)
            ctx_col1, ctx_col2 = st.columns([1, 4])
            with ctx_col1:
                if st.button("\U0001F504 Regenerate with Context", key="cv_gen_addendum", use_container_width=True, disabled=not user_context):
                    with st.spinner("Regenerating analysis with additional context..."):
                        # Get all the same data as the original analysis
                        peers_for_regen = filt_no_pos[filt_no_pos['ticker'] != stk3]
                        regen_prompt = f"""You are a senior compensation consultant. Regenerate the full compensation analysis for {cn3} ({stk3}), incorporating the additional context provided by the user.

ORIGINAL ANALYSIS (for reference — maintain same structure and data):
{rt}

USER-PROVIDED ADDITIONAL CONTEXT:
{user_context}

INSTRUCTIONS:
1. Regenerate the complete analysis, weaving in the user's context where it is relevant
2. Maintain all original section markers: [SECTION:POSITIONING], [SECTION:MIX], [SECTION:RETURNS], [SECTION:WATCH]
3. Use the same factual compensation and returns data from the original
4. Where user context is incorporated, integrate it naturally into the narrative
5. At the very end, after [SECTION:WATCH], add a clearly marked footnote section:
   <div style="margin-top:1rem;padding:0.8rem;background:#fffbeb;border:1px solid #fcd34d;border-radius:6px;font-size:0.8rem;color:#92400e;">
   <strong>Disclosure:</strong> This analysis incorporates the following additional context provided by the user, which has not been independently verified against SEC filings: "{user_context}"
   </div>
6. CRITICAL: Only reference return figures and compensation data from the original analysis. Do NOT invent any numbers.

Use section headers: <h4>Executive Compensation Overview</h4>, <h4>Compensation Mix & Structure</h4>, <h4>FY{RETURNS_YEAR} Performance & Pay Alignment</h4>, <h4>Board Considerations</h4>

{AI_TONE}"""
                        try:
                            cl = get_client()
                            if cl:
                                resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=2500, messages=[{"role":"user","content":regen_prompt}])
                                st.session_state['lk_rpt'] = clean_ai(resp.content[0].text)
                                st.session_state['lk_user_context'] = user_context
                                st.rerun()
                            else:
                                st.error("API client not available. Check ANTHROPIC_API_KEY.")
                        except Exception as e:
                            st.error(f"Error regenerating: {e}")
            
            # Close / Download buttons
            cl0, dl0 = st.columns([1,4])
            with cl0:
                if st.button("\u2715 Close Report", key="cv_close_lk_rpt"):
                    del st.session_state['lk_rpt']
                    st.session_state.pop('lk_addendum', None)
                    st.session_state.pop('lk_user_context', None)
                    st.rerun()
            with dl0:
                try:
                    pdf = make_pdf(cn3, stk3, rt, cd3, ret_data, peers_only)
                    st.download_button("\U0001F4E5 Download PDF", data=pdf, file_name=f"Velarion_{stk3}_Analysis.pdf", mime="application/pdf", key="cv_lk_pdf")
                except Exception: pass
        
        # ---- LEAGUE TABLES (inline toggle) ----
        if st.session_state.get('show_league', False):
            st.markdown("---")
            st.markdown("#### League Tables")
            lt_pos_col, lt_spacer = st.columns([1, 3])
            with lt_pos_col:
                lpos = st.selectbox("Position", FILTER_POSITIONS, format_func=lambda x: POSITION_FILTER_LABEL.get(x,x), key="cv_lt_pos")
            hl_tk = stk3
            ldf = filt[(filt['position']==lpos) & (filt['comp_source']!='external_manager')].copy()
            if not ldf.empty:
                ldf = ldf.sort_values('total_comp', ascending=False).reset_index(drop=True)
                ldf['_rank'] = range(1, len(ldf)+1)
                pos_label = POSITION_FILTER_LABEL.get(lpos, lpos)
                if st.session_state.get('peer_mode') == 'proxy':
                    lprop_label = "Proxy Peer Group"
                else:
                    lprop_label = "Custom Peer Group"
                st.markdown(f"##### {lprop_label} \u2014 {pos_label} Rankings (FY{FY_YEAR})")
                components.html('<button onclick="window.parent.print()" style="background:#475569;color:white;border:none;border-radius:6px;padding:5px 14px;font-size:0.75rem;font-weight:600;cursor:pointer;float:right;">\U0001F5A8 Print This Page</button>', height=35)
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
                is_combined_lt = filt['property_type'].dropna().nunique() > 1
                if is_combined_lt:
                    lshow['Prop Type'] = ldf['property_type'].values
                lshow[f'1-Yr (FY{RETURNS_YEAR})'] = ldf['ticker'].apply(lambda t: fmt_return(ret_data.get(t,{}).get('return_1y'))).values
                lshow['3-Yr'] = ldf['ticker'].apply(lambda t: fmt_return(ret_data.get(t,{}).get('return_3y'))).values
                lshow[f'YTD {RETURNS_YEAR+1}'] = ldf['ticker'].apply(lambda t: fmt_return(ret_data.get(t,{}).get('return_ytd'))).values
                if hl_tk and hl_tk in lshow['Ticker'].values:
                    hl_mask = lshow['Ticker'] == hl_tk
                    lshow = pd.concat([lshow[hl_mask], lshow[~hl_mask]]).reset_index(drop=True)
                    styled = lshow.style.apply(lambda x: ['background-color: #eff6ff; font-weight: 600;' if x.name == 0 else '' for _ in x], axis=1)
                    st.dataframe(styled, use_container_width=True, hide_index=True, height=400)
                else:
                    st.dataframe(lshow, use_container_width=True, hide_index=True, height=400)
                # Stats
                ret_1y_vals = pd.Series([ret_data.get(t,{}).get('return_1y') for t in ldf['ticker']], dtype=float).dropna()
                ret_3y_vals = pd.Series([ret_data.get(t,{}).get('return_3y') for t in ldf['ticker']], dtype=float).dropna()
                hl_comp_row = None; hl_pct_row = None; hl_pct_vals = []
                if hl_tk and hl_tk in ldf['ticker'].values:
                    hr = ldf[ldf['ticker']==hl_tk].iloc[0]
                    hl_label = f"{hr['company_name']} ({hl_tk})"
                    hl_comp_row = {'': hl_label}; hl_pct_row = hl_label
                    for col, label in [('base_salary','Salary'),('cash_bonus_incentive','Cash Bonus'),('stock_based_comp','Non-Cash Equity'),('total_comp','Total Comp'),('market_cap','Market Cap')]:
                        v = hr[col]
                        if col == 'market_cap':
                            hl_comp_row[label] = f"${v/1e9:.2f}B" if pd.notna(v) else "\u2014"
                            hl_pct_vals.append(f"${v/1e9:.2f}B" if pd.notna(v) else "\u2014")
                        else:
                            hl_comp_row[label] = fmt_dollars(v) if pd.notna(v) and v > 0 else "\u2014"
                            hl_pct_vals.append(fmt_dollars(v) if pd.notna(v) and v > 0 else "\u2014")
                    hl_ret_1y = ret_data.get(hl_tk,{}).get('return_1y'); hl_ret_3y = ret_data.get(hl_tk,{}).get('return_3y')
                    hl_comp_row['1-Yr Return'] = fmt_return(hl_ret_1y); hl_comp_row['3-Yr Return'] = fmt_return(hl_ret_3y)
                    hl_pct_vals.extend([fmt_return(hl_ret_1y), fmt_return(hl_ret_3y)])
                st.markdown(f"##### {pos_label} Compensation Statistics ({len(ldf)} executives)")
                comp_cols = [('base_salary','Salary'),('cash_bonus_incentive','Cash Bonus'),('stock_based_comp','Non-Cash Equity'),('total_comp','Total Comp'),('market_cap','Market Cap')]
                mean_row = {'': 'Mean'}; med_row = {'': 'Median'}
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
                summary_rows = [hl_comp_row, mean_row, med_row] if hl_comp_row else [mean_row, med_row]
                summary_df = pd.DataFrame(summary_rows)
                if hl_comp_row:
                    styled_summary = summary_df.style.apply(lambda x: ['background-color: #eff6ff; font-weight: 600;' if x.name == 0 else '' for _ in x], axis=1)
                    st.dataframe(styled_summary, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                st.markdown(f'<div class="footnote">\u00B9 Grant date fair value per ASC Topic 718. | ^ = Estimated partial-year hire</div>', unsafe_allow_html=True)
            else:
                st.info(f"No {POSITION_FILTER_LABEL.get(lpos,lpos)} data for the current peer group.")
        
        # ---- COMP SUMMARY TABLE (inline toggle) ----
        if st.session_state.get('show_comp_table', False):
            st.markdown("---")
            st.markdown("#### Compensation Summary")
            components.html('<button onclick="window.parent.print()" style="background:#475569;color:white;border:none;border-radius:6px;padding:5px 14px;font-size:0.75rem;font-weight:600;cursor:pointer;float:right;margin-bottom:8px;">\U0001F5A8 Print Compensation Summary</button>', height=35)
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
        
        # ---- INDIVIDUAL EXEC BENCHMARKING ----
        st.markdown("---")
        is_proxy_mode = st.session_state.get('peer_mode') == 'proxy'
        # Build widened peer sets for cascade
        # Step 2: Same property type peers (excluding subject company)
        pt_peers_base = reit_df[reit_df['ticker'] != stk3]
        pt_peers_base = pt_peers_base[pt_peers_base['property_type'] == pt3]
        pt_peers = get_peer_stats(pt_peers_base)
        # Step 3: All REITs (for both proxy and custom mode) — exclude cross-sector peers
        wide_peers_base = df[df['ticker'] != stk3].copy()
        wide_peers_base = wide_peers_base[~wide_peers_base['property_type'].str.startswith('Peer', na=True)]
        wide_peers_base = wide_peers_base[wide_peers_base['property_type'].notna() & (wide_peers_base['property_type'] != '')]
        if not is_proxy_mode:
            if mcap_max >= 50.0:
                wide_peers_base = wide_peers_base[(wide_peers_base['market_cap'] >= mcap_min*1e9) | (wide_peers_base['market_cap'].isna())]
            else:
                wide_peers_base = wide_peers_base[((wide_peers_base['market_cap'] >= mcap_min*1e9) & (wide_peers_base['market_cap'] <= mcap_max*1e9)) | (wide_peers_base['market_cap'].isna())]
        wide_peers = get_peer_stats(wide_peers_base)
        MIN_PEERS = 4
        for idx, (_, er) in enumerate(sort_by_position(cd3).iterrows()):
            if 'former' in str(er.get('title', '')).lower():
                continue
            ie = er['comp_source']=='external_manager'; ip = detect_partial(er, df); pos = er['position']; pd2 = POSITION_DISPLAY.get(pos, pos)
            badges = ''
            if ie: badges += ' <span class="ext-badge">EXT. MANAGED</span>'
            if ip: badges += ' <span class="partial-year">PARTIAL YEAR</span>'
            pos_tag = f" \u2014 {pd2}" if pd2 else ""
            # Show title unless it's just the position name repeated
            title_str = er['title'] if er.get('title') else ""
            title_lower = title_str.lower().strip()
            # Hide title if it's just "President", "Chief Executive Officer", "CFO", etc. with no additional info
            simple_titles = {
                'CEO': ['chief executive officer', 'ceo'],
                'PRESIDENT': ['president'],
                'CFO': ['chief financial officer', 'cfo'],
                'COO': ['chief operating officer', 'coo'],
                'CIO': ['chief investment officer', 'cio'],
                'GC': ['general counsel', 'chief legal officer'],
                'CAO': ['chief accounting officer', 'cao'],
            }
            skip_title = title_lower in simple_titles.get(pos, [])
            title_display = f" | {title_str}" if title_str and not skip_title else ""
            st.markdown(f"**{er['first_name']} {er['last_name']}**{pos_tag}{badges}{title_display}", unsafe_allow_html=True)
            if ie:
                cols = st.columns(4)
                for i, (f, l) in enumerate([('base_salary','Base Salary'),('cash_bonus_incentive','Cash Bonus/Incentive'),('stock_based_comp','Non-Cash Equity \u00B9'),('total_comp','Total Compensation')]):
                    v = er[f]
                    with cols[i]: st.markdown(render_pct_card(v, None, l, is_ext=True), unsafe_allow_html=True)
                peer_key = f"show_peers_{stk3}_{pos}_{idx}"
                if st.button(f"\U0001F465 View {pd2 if pd2 else 'Peer'} Comparison", key=f"cv_peer_{pos}_{idx}", use_container_width=False):
                    st.session_state[peer_key] = not st.session_state.get(peer_key, False)
                if st.session_state.get(peer_key, False):
                    render_peer_table(er, peers_only, pos)
                st.markdown("")
                continue
            # Widening cascade
            narrow_peers = auto_peers[auto_peers['position']==pos]
            n_narrow = len(narrow_peers[narrow_peers['total_comp'].notna()])
            widened = False
            widen_desc = ""
            if n_narrow >= MIN_PEERS:
                peers = narrow_peers
            elif is_proxy_mode:
                # Proxy cascade: Step 2 — same property type
                pt_pos_peers = pt_peers[pt_peers['position']==pos]
                n_pt = len(pt_pos_peers[pt_pos_peers['total_comp'].notna()])
                if n_pt >= MIN_PEERS:
                    peers = pt_pos_peers
                    widened = True
                    widen_desc = f"Widened to <strong>{n_pt} {pd2 if pd2 else 'NEO'}s across {pt_pos_peers['ticker'].nunique()} {pt3} REITs</strong> (only {n_narrow} in proxy peer group)."
                else:
                    # Step 3 — all REITs
                    all_pos_peers = wide_peers[wide_peers['position']==pos]
                    n_all = len(all_pos_peers[all_pos_peers['total_comp'].notna()])
                    if n_all >= MIN_PEERS:
                        peers = all_pos_peers
                        widened = True
                        widen_desc = f"Widened to <strong>{n_all} {pd2 if pd2 else 'NEO'}s across {all_pos_peers['ticker'].nunique()} REITs</strong> (only {n_narrow} in proxy peers, {n_pt} in {pt3})."
                    else:
                        peers = narrow_peers  # Use what we have
                        if n_narrow > 0:
                            st.markdown(f'<div style="background:#f8f6f3;border:1px solid #d4a017;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.78rem;color:#78350f;margin:0.3rem 0;">\u2139\uFE0F Limited peer data: {n_narrow} {pd2 if pd2 else "NEO"}s available.</div>', unsafe_allow_html=True)
            else:
                # Custom mode — widen to all REITs in market cap range
                all_pos_peers = wide_peers[wide_peers['position']==pos]
                n_all = len(all_pos_peers[all_pos_peers['total_comp'].notna()])
                if n_all >= MIN_PEERS:
                    peers = all_pos_peers
                    widened = True
                    widen_desc = f"Widened to <strong>{n_all} {pd2 if pd2 else 'NEO'}s across {all_pos_peers['ticker'].nunique()} companies</strong> (only {n_narrow} in custom peer group)."
                else:
                    peers = narrow_peers
            n_pos = len(peers[peers['total_comp'].notna()])
            if widened and widen_desc:
                st.markdown(f'<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.78rem;color:#92400e;margin:0.3rem 0;">\U0001F504 {widen_desc}</div>', unsafe_allow_html=True)
            cols = st.columns(4)
            for i, (f, l) in enumerate([('base_salary','Base Salary'),('cash_bonus_incentive','Cash Bonus/Incentive'),('stock_based_comp','Non-Cash Equity \u00B9'),('total_comp','Total Compensation')]):
                v = er[f]; p = percentile_rank(v, peers[f]); med = peers[f].median(); n = len(peers[f].dropna())
                with cols[i]: st.markdown(render_pct_card(v, p, l, med=med, n=n, is_ext=ie, is_partial=ip), unsafe_allow_html=True)
            nk = f"cv_n_{stk3}_{er['position']}_{er['last_name']}_{idx}"
            if nk not in st.session_state: st.session_state[nk] = None
            pos_btn_label = pd2 if pd2 else er['first_name'] + ' ' + er['last_name']
            peer_key = f"show_peers_{stk3}_{pos}_{idx}"
            eb1, eb2, eb_spacer = st.columns([2, 2, 5])
            with eb1:
                if st.button(f"Generate {pos_btn_label} Analysis", key=f"cv_b_{nk}", use_container_width=True, type="secondary"):
                    with st.spinner("Generating..."):
                        st.session_state[nk] = gen_exec(er, peers_only, df, ret_data, peers_only, widened=widened, wide_peers_df=wide_peers if widened else None)
                        st.session_state[f"fp_{nk}"] = cur_fp0
            with eb2:
                if st.button(f"View {pos_btn_label} Peers", key=f"cv_peer_{pos}_{idx}", use_container_width=True, type="secondary"):
                    st.session_state[peer_key] = not st.session_state.get(peer_key, False)
            if st.session_state[nk]:
                if st.session_state.get(f"fp_{nk}") != cur_fp0:
                    st.markdown(STALE_WARNING, unsafe_allow_html=True)
                st.markdown(f'<div class="ai-narrative"><div class="ai-label">\U0001F4CA {pos_btn_label} Compensation Analysis</div>{st.session_state[nk]}</div>', unsafe_allow_html=True)
                if st.button(f"\u2715 Close {pos_btn_label} Analysis", key=f"cv_close_{nk}"):
                    st.session_state[nk] = None
                    st.rerun()
            if st.session_state.get(peer_key, False):
                render_peer_table(er, peers if widened else peers_only, pos)
            st.markdown("")
        
        st.markdown(f'<div class="footnote">\u00B9 Non-cash equity reflects grant date fair value per ASC Topic 718 as reported in the Summary Compensation Table. This represents the probable value at the time of grant, not realized compensation.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="source-note">Returns: Yahoo Finance, 1-Yr and 3-Yr through Dec 31, {RETURNS_YEAR} | YTD {RETURNS_YEAR+1} through current</div>', unsafe_allow_html=True)

# MONTHLY INTELLIGENCE — placeholder, revisit placement later
# st.markdown("---")
# st.markdown("#### Monthly Executive Intelligence")
# st.markdown('<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:1.2rem 1.5rem;margin:0.5rem 0;">'
#     '<div style="font-size:0.85rem;color:#0c4a6e;line-height:1.6;">'
#     '\U0001F4E8 <strong>Monthly Executive Changes Report</strong> \u2014 Track C-suite movements, new hires, departures, '
#     'and employment agreement terms across the REIT universe. Delivered monthly to subscribers.'
#     '<br><br><span style="color:#64748b;font-size:0.8rem;">Coming soon \u2014 reports will be available for download here.</span>'
#     '</div></div>', unsafe_allow_html=True)

# FOOTER
st.markdown("---")
st.markdown(f'<div style="text-align:center;color:#94a3b8;font-size:0.78rem;padding:1rem 0;">Velarion Company Intelligence | SEC DEF 14A proxy filings | FY{FY_YEAR}<br>\u00A9 2026 Velarion.ai \u2014 For institutional use only. Not investment advice.</div>', unsafe_allow_html=True)
