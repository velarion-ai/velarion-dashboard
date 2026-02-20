"""
Velarion Company Intelligence — Real Estate Executive Compensation Dashboard
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
    """Inject JS beacon to track REAL page views (not bots/prefetchers).
    JavaScript only executes in actual browsers, not email link scanners or health checks."""
    if st.session_state.get('_page_view_logged'):
        return
    st.session_state['_page_view_logged'] = True
    
    # JS beacon: fires only in real browsers, captures UTM source and referrer
    beacon_js = f"""
    <script>
    (function() {{
        if (window._velarionTracked) return;
        window._velarionTracked = true;
        
        var params = new URLSearchParams(window.location.search);
        var utm_source = params.get('utm_source') || '';
        var utm_campaign = params.get('utm_campaign') || '';
        var utm_medium = params.get('utm_medium') || '';
        var referrer = document.referrer || '';
        var screen_w = screen.width || 0;
        var screen_h = screen.height || 0;
        var ua = navigator.userAgent || '';
        
        // Skip if this looks like a bot
        if (/bot|crawl|spider|prefetch|preview|scan|check/i.test(ua)) return;
        
        fetch('{_LOGIN_SUPA_URL}/rest/v1/login_events', {{
            method: 'POST',
            headers: {{
                'apikey': '{_LOGIN_SUPA_KEY}',
                'Authorization': 'Bearer {_LOGIN_SUPA_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal'
            }},
            body: JSON.stringify({{
                email: '__real_visit__',
                logged_in_at: new Date().toISOString(),
                utm_source: utm_source,
                utm_campaign: utm_campaign,
                referrer: referrer,
                user_agent: ua.substring(0, 200),
                screen_size: screen_w + 'x' + screen_h
            }})
        }}).catch(function() {{
            // Fallback: log without extra columns if schema not updated yet
            fetch('{_LOGIN_SUPA_URL}/rest/v1/login_events', {{
                method: 'POST',
                headers: {{
                    'apikey': '{_LOGIN_SUPA_KEY}',
                    'Authorization': 'Bearer {_LOGIN_SUPA_KEY}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal'
                }},
                body: JSON.stringify({{
                    email: '__real_visit__|' + utm_source + '|' + utm_campaign + '|' + screen_w + 'x' + screen_h,
                    logged_in_at: new Date().toISOString()
                }})
            }}).catch(function() {{}});
        }});
    }})();
    </script>
    """
    st.markdown(beacon_js, unsafe_allow_html=True)

def check_password():
    if st.session_state.get('authenticated'):
        return True

    # Check for auth token in query params (survives refresh)
    params = st.query_params
    auth_token = params.get("auth")
    admin_key = params.get("key")
    
    # Admin bypass
    if admin_key == "velarion2026":
        st.session_state['authenticated'] = True
        st.session_state['user_email'] = 'andy@velarion.ai'
        return True
    
    # Returning user with auth token
    if auth_token:
        # Decode: token is base64 of email
        try:
            import base64
            email = base64.b64decode(auth_token).decode('utf-8')
            if email and "@" in email:
                st.session_state['authenticated'] = True
                st.session_state['user_email'] = email
                return True
        except Exception:
            pass

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

        st.markdown('<div style="padding:0 0 0 2vw;"><div style="border-left:2px solid #d4a84b;padding-left:16px;"><p style="font-size:14px;color:rgba(255,255,255,0.5);line-height:1.6;font-style:italic;margin:0 0 8px 0;">"I built this because leadership compensation is one of the most consequential decisions a company makes &mdash; yet real insight has always meant expensive consultants and stale reports. Velarion provides granular transparency into how companies compensate their leaders, then synthesizes market performance, earnings, peer benchmarking, and governance data in real time into the kind of analysis you&rsquo;d expect from a top compensation consultant &mdash; delivered instantly, always current, and available whenever you need it."</p><p style="font-size:12px;color:rgba(255,255,255,0.3);margin:0;font-weight:600;">Andy Richardson &mdash; Founder, Former Real Estate Executive</p></div></div>', unsafe_allow_html=True)

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
                # Set auth token in URL so login survives refresh
                import base64
                token = base64.b64encode(email_clean.encode('utf-8')).decode('utf-8')
                st.query_params["auth"] = token
                st.rerun()
            elif not email_clean or "@" not in email_clean:
                st.error("Please enter a valid email address.")
            else:
                st.error("Invalid credentials. Please try again.")

        st.markdown("""
        <div style="margin-top:28px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.05);">
            <p style="font-size:11px;color:rgba(255,255,255,0.5);margin:0 0 4px 0;">Early beta access through March 31, 2026</p>
            <p style="font-size:11px;color:#22b89a;margin:0 0 4px 0;">🔄 New features and data updates added daily</p>
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
    /* Remove top padding/whitespace */
    .stMainBlockContainer { padding-top: 1rem !important; }
    .block-container { padding-top: 1rem !important; }
    header[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; padding: 0 !important; }
    /* Disable sidebar collapse button */
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    /* Force sidebar always visible */
    section[data-testid="stSidebar"] { min-width: 280px !important; }
    /* HEADER — deep navy */
    .main-header { background: linear-gradient(135deg, #0a1628 0%, #1a365d 60%, #234578 100%); padding: 2rem 2.5rem; border-radius: 12px; margin-bottom: 0.3rem; color: white; box-shadow: 0 4px 20px rgba(10,22,40,0.3); }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; letter-spacing: -0.02em; }
    .main-header p { margin: 0.3rem 0 0 0; opacity: 0.8; font-size: 0.92rem; }
    .intro-text { color: #334155; font-size: 0.9rem; line-height: 1.55; padding: 0.4rem 0 0.8rem 0; }
    /* INSTRUCTION BOXES — warm cream/gold tint */
    .tab-instruction { background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border: 1px solid #d4a017; border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 1rem; font-size: 0.83rem; color: #78350f; font-weight: 500; }
    .tab-cta { background: linear-gradient(135deg, #b8860b 0%, #d4a017 100%); border-radius: 8px; padding: 0.7rem 1rem; margin-bottom: 1rem; font-size: 0.9rem; color: white; font-weight: 600; text-align: center; }
    /* KPI CARDS — white with gold top accent */
    .metric-card { background: white; border: 1px solid #d6d3d1; border-top: 3px solid #b8860b; border-radius: 10px; padding: 0.8rem 0.6rem; text-align: center; height: 120px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 2px 8px rgba(10,22,40,0.06); }
    .metric-card .label { font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.07em; color: #57534e; font-weight: 700; white-space: nowrap; }
    .metric-card .value { font-size: 1.35rem; font-weight: 700; color: #0f172a; margin-top: 0.15rem; }
    .metric-card .sub { font-size: 0.72rem; color: #78716c; margin-top: 0.1rem; font-weight: 500; }
    /* AI NARRATIVE — navy accent */
    .ai-narrative { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border: 1px solid #94a3b8; border-left: 5px solid #1a365d; border-radius: 8px; padding: 1.2rem 1.5rem; margin: 1rem 0; font-size: 0.9rem; line-height: 1.65; color: #1e293b; text-align: justify; box-shadow: 0 2px 8px rgba(26,54,93,0.06); }
    .ai-narrative .ai-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #1a365d; font-weight: 700; margin-bottom: 0.5rem; text-align: left; }
    /* AI REPORT — gold accent */
    .ai-report { background: linear-gradient(135deg, #fffbeb 0%, #fefce8 100%); border: 1px solid #d4a017; border-left: 5px solid #b8860b; border-radius: 8px; padding: 1.5rem 2rem; margin: 1rem 0; font-size: 0.9rem; line-height: 1.7; color: #1e293b; text-align: justify; box-shadow: 0 2px 8px rgba(184,134,11,0.08); }
    .ai-report .ai-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #92400e; font-weight: 700; margin-bottom: 0.5rem; text-align: left; }
    .ai-report h4 { color: #1a365d; font-size: 1.15rem; margin: 1.2rem 0 0.3rem 0; padding: 0; text-align: left; }
    .ai-report p { margin: 0 0 0.8rem 0; text-align: justify; }
    .ai-report .js-plotly-plot, .ai-report iframe { margin-top: 1rem; }
    .ai-narrative h4 { color: #1a365d; font-size: 1.15rem; margin: 0.6rem 0 0.15rem 0; padding: 0; text-align: left; }
    .ai-narrative p { margin: 0 0 0.5rem 0; text-align: justify; }
    /* UTILITY BOXES */
    /* Disable Streamlit column resize handles — prevents accidental hiding */
    [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
        resize: none !important;
    }
    [data-testid="column-resize-handle"],
    .stHorizontalBlock [role="separator"],
    [data-testid="stHorizontalBlock"] > div > div[style*="cursor: col-resize"],
    [data-testid="stHorizontalBlock"] > div > div[draggable] {
        display: none !important;
        pointer-events: none !important;
    }
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
    /* Tab sizing */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.05rem;
        font-weight: 600;
    }
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
    # Supabase default limit is 1000 rows — paginate to get all records
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        result = sb.table('exec_comp').select('*').range(offset, offset + page_size - 1).execute()
        if not result.data:
            break
        all_rows.extend(result.data)
        if len(result.data) < page_size:
            break
        offset += page_size
    df = pd.DataFrame(all_rows)
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

@st.cache_data(ttl=300)
def load_director_comp():
    """Load director compensation data from Supabase."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        all_data = []
        offset = 0
        batch = 1000
        while True:
            result = sb.table('director_comp').select('*').range(offset, offset + batch - 1).execute()
            if result.data:
                all_data.extend(result.data)
            if not result.data or len(result.data) < batch:
                break
            offset += batch
        if all_data:
            ddf = pd.DataFrame(all_data)
            for c in ['fees_earned_cash','stock_awards','option_awards','all_other_comp','total_comp','change_in_pension','non_equity_incentive']:
                if c in ddf.columns: ddf[c] = pd.to_numeric(ddf[c], errors='coerce')
            # Compute total_comp if missing: sum of all comp components
            comp_cols = [c for c in ['fees_earned_cash','stock_awards','option_awards','non_equity_incentive','change_in_pension','all_other_comp'] if c in ddf.columns]
            if comp_cols:
                mask = ddf['total_comp'].isna() & ddf[comp_cols].notna().any(axis=1)
                ddf.loc[mask, 'total_comp'] = ddf.loc[mask, comp_cols].sum(axis=1)
            # Parse committees from JSON string
            if 'committees' in ddf.columns:
                import json as _json
                ddf['committees_list'] = ddf['committees'].apply(lambda x: _json.loads(x) if isinstance(x, str) and x.startswith('[') else (x if isinstance(x, list) else []))
            return ddf
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=300)
def load_fee_schedule():
    """Load director fee schedule data from Supabase."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = sb.table('director_fee_schedule').select('*').execute()
        if result.data:
            return pd.DataFrame(result.data)
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

def build_mcap_wide_peers(all_df, tk, co_d, position, min_peers=5):
    """Find the tightest market-cap band that yields at least min_peers for a given position.
    Starts at 0.5x-2x and widens in steps until enough peers are found or 10x is reached.
    Returns (peer_stats_df, n_companies, multiplier_used)."""
    mc = co_d['market_cap'].iloc[0] if 'market_cap' in co_d.columns and pd.notna(co_d['market_cap'].iloc[0]) else None
    base = all_df[all_df['ticker'] != tk].copy()
    if not mc or mc <= 0:
        ps = get_peer_stats(base)
        pp = ps[ps['position'] == position]
        return ps, len(pp['ticker'].unique()), None
    # Widen from tight to broad
    for mult in [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]:
        mc_low = mc / (1 + mult)    # e.g. mult=1.0 → 0.5x to 2x
        mc_high = mc * (1 + mult)
        filt = base[
            ((base['market_cap'] >= mc_low) & (base['market_cap'] <= mc_high)) |
            (base['market_cap'].isna())
        ]
        ps = get_peer_stats(filt)
        pp = ps[ps['position'] == position]
        n = len(pp[pp['total_comp'].notna()])
        if n >= min_peers:
            return ps, len(filt['ticker'].unique()), mult
    # Fallback: use everything
    ps = get_peer_stats(base)
    return ps, len(base['ticker'].unique()), None

def percentile_rank(value, series):
    """Compute percentile rank of value within peer series.
    Uses (values_below + 0.5 * values_equal) / n formula for proper mid-rank positioning.
    """
    if pd.isna(value) or len(series.dropna()) == 0: return None
    s = series.dropna()
    if len(s) <= 1: return None
    below = (s < value).sum()
    equal = (s == value).sum()
    rank = int((below + 0.5 * equal) / len(s) * 100)
    # Clamp to 1-99 range
    if rank < 1: rank = 1
    if rank > 99: rank = 99
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
def lookup_proxy_url(company_name, fy_year, cik=None):
    """Look up the most recent DEF 14A proxy filing URL on SEC EDGAR.
    Uses CIK-based filing index (fast, reliable) with EFTS full-text fallback."""
    import requests as _req
    import json as _json
    _headers = {'User-Agent': 'Velarion Research andy@velarion.ai'}
    
    # Method 1: CIK-based filing index (preferred — fast, no rate-limit issues)
    if cik:
        try:
            cik_padded = str(cik).zfill(10)
            url = f'https://data.sec.gov/submissions/CIK{cik_padded}.json'
            resp = _req.get(url, headers=_headers, timeout=8)
            if resp.status_code == 200:
                filings = resp.json().get('filings', {}).get('recent', {})
                forms = filings.get('form', [])
                dates = filings.get('filingDate', [])
                accessions = filings.get('accessionNumber', [])
                primary_docs = filings.get('primaryDocument', [])
                for i, f in enumerate(forms):
                    if f == 'DEF 14A':
                        cik_clean = str(cik).lstrip('0')
                        acc_clean = accessions[i].replace('-', '')
                        return f'https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc_clean}/{primary_docs[i]}'
        except Exception:
            pass
    
    # Method 2: EFTS full-text search fallback
    try:
        clean_name = company_name.replace(',', '').replace('.', '').replace("'", '')
        query = f'%22{clean_name.replace(" ", "+")}%22'
        url = f'https://efts.sec.gov/LATEST/search-index?q={query}&forms=DEF+14A&dateRange=custom&startdt={fy_year+1}-01-01&enddt={fy_year+1}-12-31'
        resp = _req.get(url, headers=_headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = _json.loads(resp.text)
        hits = data.get('hits', {}).get('hits', [])
        if not hits:
            return None
        hit = hits[0]
        parts = hit['_id'].split(':')
        accession = parts[0]
        filename = parts[1]
        cik_str = hit['_source']['ciks'][0].lstrip('0')
        return f'https://www.sec.gov/Archives/edgar/data/{cik_str}/{accession.replace("-","")}/{filename}'
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
    o = max(0, t - s - b - sk)
    return f"{s/t*100:.0f}% salary / {b/t*100:.0f}% cash / {sk/t*100:.0f}% equity / {o/t*100:.0f}% other"

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
    # % above/below median
    vs_med_line = ''
    if med is not None and med > 0 and val is not None and pd.notna(val) and not is_partial:
        diff_pct = (val - med) / med * 100
        if abs(diff_pct) < 0.5:
            vs_med_line = '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-top:2px;">At median</div>'
        elif diff_pct > 0:
            vs_med_line = f'<div style="font-size:0.75rem;color:#b8860b;font-weight:600;margin-top:2px;">{diff_pct:+.0f}% above median</div>'
        else:
            vs_med_line = f'<div style="font-size:0.75rem;color:#475569;font-weight:600;margin-top:2px;">{diff_pct:+.0f}% below median</div>'
    return f'<div style="padding:0.7rem;background:#f8fafc;border-radius:8px;border-left:3px solid {color};"><div style="font-size:0.68rem;text-transform:uppercase;color:#64748b;">{label}</div><div style="font-size:1.05rem;font-weight:700;color:#0f172a;">{fmt_dollars(val)}</div>{vs_med_line}<div style="font-size:0.82rem;color:{color};font-weight:600;">{pct_d} percentile</div><div style="background:#e2e8f0;border-radius:4px;height:5px;margin-top:5px;"><div style="width:{pct or 0}%;height:100%;background:{color};border-radius:4px;"></div></div>{med_line}{partial_tag}</div>'

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
        _oc = max(0, (r['total_comp'] or 0) - (r['base_salary'] or 0) - (r['cash_bonus_incentive'] or 0) - (r['stock_based_comp'] or 0)) if pd.notna(r.get('total_comp')) and r['total_comp'] > 0 else 0
        rows.append(f"<tr style='{bg}{fw}'><td>{i+1}</td><td>{r['ticker']}</td><td>{r['company_name'][:30]}</td><td>{r['first_name']} {r['last_name']}</td><td style='text-align:right'>{fmt_dollars(r['base_salary'])}</td><td style='text-align:right'>{fmt_dollars(r['cash_bonus_incentive'])}</td><td style='text-align:right'>{fmt_dollars(r['stock_based_comp'])}</td><td style='text-align:right;color:#64748b;'>{fmt_dollars(_oc)}</td><td style='text-align:right'>{fmt_dollars(r['total_comp'])}</td><td style='text-align:right'>{mc}</td></tr>")
    html = f"""<div style="max-height:300px;overflow-y:auto;margin:0.5rem 0;border:1px solid #e2e8f0;border-radius:8px;">
    <table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
    <thead><tr style="background:#f8f6f3;position:sticky;top:0;"><th style="padding:6px;text-align:left;">Rank</th><th style="padding:6px;text-align:left;">Ticker</th><th style="padding:6px;text-align:left;">Company</th><th style="padding:6px;text-align:left;">Executive</th><th style="padding:6px;text-align:right;">Salary</th><th style="padding:6px;text-align:right;">Cash Bonus</th><th style="padding:6px;text-align:right;">Stock</th><th style="padding:6px;text-align:right;color:#64748b;">Other</th><th style="padding:6px;text-align:right;">Total Comp</th><th style="padding:6px;text-align:right;">Mkt Cap</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table></div>"""
    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# AI — COMPENSATION CONSULTANT TONE
# ============================================================
def get_client():
    try:
        import anthropic; return anthropic.Anthropic()
    except Exception: return None

AI_TONE = """ROLE: You are a seasoned real estate compensation consultant preparing a confidential briefing for a comp committee member — similar to Pearl Meyer or FW Cook. Your audience is management preparing for board meetings and comp committee negotiations.

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

@st.cache_data(ttl=86400)
def fetch_say_on_pay(company_name, cik, fy_year):
    """Fetch say-on-pay vote results from 8-K Item 5.07 filing."""
    import requests as _req
    import re
    try:
        _headers = {'User-Agent': 'Velarion Research andy@velarion.ai'}
        # Search for voting results 8-K
        clean_name = company_name.replace(',', '').replace('.', '').replace("'", '')
        query = f'%22{clean_name.replace(" ", "+")}%22+%22Item+5.07%22'
        url = f'https://efts.sec.gov/LATEST/search-index?q={query}&forms=8-K&dateRange=custom&startdt={fy_year}-01-01&enddt={fy_year+1}-12-31'
        resp = _req.get(url, headers=_headers, timeout=10)
        if resp.status_code != 200:
            return None
        import json
        data = json.loads(resp.text)
        hits = data.get('hits', {}).get('hits', [])
        if not hits:
            return None
        # Get the first (most recent) hit
        hit = hits[0]
        doc_id = hit['_id']
        parts = doc_id.split(':')
        accession = parts[0]
        filename = parts[1]
        cik_clean = str(hit['_source']['ciks'][0]).lstrip('0')
        filing_url = f'https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession.replace("-","")}/{filename}'
        filing_date = hit['_source'].get('file_date', '')
        
        filing_resp = _req.get(filing_url, headers=_headers, timeout=15)
        if filing_resp.status_code != 200:
            return None
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(filing_resp.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        tl = text.lower()
        
        # Find say-on-pay / advisory comp vote
        result = {'filing_date': filing_date, 'filing_url': filing_url}
        
        # Look for patterns like "For 540,290,905 Against 34,635,610"
        # near "advisory" or "compensation of" or "say-on-pay"
        for marker in ['advisory basis, the compensation', 'advisory vote on executive compensation',
                        'say-on-pay', 'advisory vote on compensation']:
            idx = tl.find(marker)
            if idx >= 0:
                chunk = text[idx:idx+800]
                # Extract For/Against numbers
                for_match = re.search(r'For\s+([\d,]+)', chunk)
                against_match = re.search(r'Against\s+([\d,]+)', chunk)
                if for_match and against_match:
                    votes_for = int(for_match.group(1).replace(',', ''))
                    votes_against = int(against_match.group(1).replace(',', ''))
                    total = votes_for + votes_against
                    if total > 0:
                        result['votes_for'] = votes_for
                        result['votes_against'] = votes_against
                        result['approval_pct'] = round(votes_for / total * 100, 1)
                        result['approved'] = result['approval_pct'] > 50
                        return result
        return None
    except Exception:
        return None

@st.cache_data(ttl=86400)
def fetch_10k_financials(cik):
    """Fetch key financial metrics from XBRL structured data (10-K)."""
    import requests as _req
    try:
        _headers = {'User-Agent': 'Velarion Research andy@velarion.ai'}
        cik_padded = str(cik).zfill(10)
        url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json'
        resp = _req.get(url, headers=_headers, timeout=15)
        if resp.status_code != 200:
            return None
        import json
        data = json.loads(resp.text)
        facts = data.get('facts', {}).get('us-gaap', {})
        
        targets = {
            'Revenues': 'Revenue',
            'NetIncomeLoss': 'Net Income',
            'Assets': 'Total Assets',
            'LongTermDebt': 'Long-Term Debt',
            'EarningsPerShareDiluted': 'EPS (Diluted)',
            'CommonStockDividendsPerShareDeclared': 'Dividends/Share',
            'OperatingIncomeLoss': 'Operating Income',
        }
        
        results = {}
        for xbrl_key, label in targets.items():
            if xbrl_key not in facts:
                continue
            units = facts[xbrl_key].get('units', {})
            for unit_type, entries in units.items():
                annual = [e for e in entries if e.get('form') == '10-K']
                if not annual:
                    continue
                latest = annual[-1]
                prev = annual[-2] if len(annual) > 1 else None
                val = latest['val']
                period = latest.get('end', '')
                yoy = None
                if prev and prev['val'] and prev['val'] != 0:
                    yoy = round((val - prev['val']) / abs(prev['val']) * 100, 1)
                results[label] = {
                    'value': val,
                    'period': period,
                    'yoy_change': yoy,
                    'unit': unit_type,
                }
                break
        
        return results if results else None
    except Exception:
        return None

@st.cache_data(ttl=86400)
def fetch_10q_financials(cik):
    """Fetch recent quarterly financial metrics from XBRL (10-Q). Returns last 4 quarters."""
    import requests as _req
    try:
        _headers = {'User-Agent': 'Velarion Research andy@velarion.ai'}
        cik_padded = str(cik).zfill(10)
        url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json'
        resp = _req.get(url, headers=_headers, timeout=15)
        if resp.status_code != 200:
            return None
        import json
        data = json.loads(resp.text)
        facts = data.get('facts', {}).get('us-gaap', {})
        
        targets = {'Revenues': 'Revenue', 'NetIncomeLoss': 'Net Income',
                    'OperatingIncomeLoss': 'Operating Income', 'EarningsPerShareDiluted': 'EPS'}
        
        quarters = {}
        for xbrl_key, label in targets.items():
            if xbrl_key not in facts:
                continue
            units = facts[xbrl_key].get('units', {})
            for unit_type, entries in units.items():
                # Get quarterly entries — fp field indicates Q1/Q2/Q3
                qtr_entries = [e for e in entries if e.get('form') == '10-Q' and e.get('fp') in ('Q1','Q2','Q3')]
                # Take last 4
                for e in qtr_entries[-4:]:
                    period = f"{e.get('fp','')} {e.get('end','')[:4]}"
                    if period not in quarters:
                        quarters[period] = {}
                    val = e['val']
                    if unit_type == 'USD' and abs(val) >= 1e6:
                        val_str = f"${val/1e6:,.0f}M" if abs(val) < 1e9 else f"${val/1e9:,.1f}B"
                    elif unit_type == 'USD/shares':
                        val_str = f"${val:.2f}"
                    else:
                        val_str = f"{val:,.0f}"
                    quarters[period][label] = val_str
                break
        
        if not quarters:
            return None
        # Format as text
        lines = []
        for period in sorted(quarters.keys()):
            metrics = quarters[period]
            parts = [f"{k}: {v}" for k, v in metrics.items()]
            lines.append(f"  {period}: {' | '.join(parts)}")
        return '\n'.join(lines)
    except Exception:
        return None

@st.cache_data(ttl=86400)
def fetch_proxy_advisory_alerts(company_name, cik, fy_year):
    """Scan DEFA14A filings for ISS/Glass Lewis recommendations and company responses."""
    import requests as _req
    try:
        _headers = {'User-Agent': 'Velarion Research andy@velarion.ai'}
        clean_name = company_name.replace(',', '').replace('.', '').replace("'", '')
        query = f'%22{clean_name.replace(" ", "+")}%22'
        url = f'https://efts.sec.gov/LATEST/search-index?q={query}&forms=DEFA14A&dateRange=custom&startdt={fy_year}-01-01&enddt={fy_year+1}-06-30'
        resp = _req.get(url, headers=_headers, timeout=10)
        if resp.status_code != 200:
            return None
        import json
        data = json.loads(resp.text)
        hits = data.get('hits', {}).get('hits', [])
        if not hits:
            return None
        
        alerts = []
        from bs4 import BeautifulSoup
        for h in hits[:6]:
            doc_id = h['_id']
            parts = doc_id.split(':')
            accession = parts[0]
            filename = parts[1]
            cik_clean = str(h['_source']['ciks'][0]).lstrip('0')
            filing_date = h['_source'].get('file_date', '')
            filing_url = f'https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession.replace("-","")}/{filename}'
            
            try:
                filing_resp = _req.get(filing_url, headers=_headers, timeout=12)
                if filing_resp.status_code != 200:
                    continue
                soup = BeautifulSoup(filing_resp.text, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)[:5000]
                tl = text.lower()
                
                # Check for proxy advisory content
                has_iss = 'iss' in tl and any(w in tl for w in ['recommend', 'advises', 'advisory', 'against', 'vote for'])
                has_gl = 'glass lewis' in tl and any(w in tl for w in ['recommend', 'advises', 'advisory', 'against', 'vote for'])
                has_against = any(p in tl for p in ['recommends a vote against', 'recommend that stockholders vote against',
                    'recommends against', 'vote against the', 'has recommended against'])
                has_for = any(p in tl for p in ['recommends a vote for', 'recommend that stockholders vote for',
                    'recommends for', 'iss recommends'])
                has_response = any(p in tl for p in ['we disagree', 'company disagrees', 'we believe iss',
                    'contrary to', 'notwithstanding the recommendation', 'response to'])
                
                if has_iss or has_gl or has_against or has_response:
                    # Extract relevant snippet
                    snippet = text[:800]
                    for kw in ['iss', 'glass lewis', 'recommends', 'advisory']:
                        idx = tl.find(kw)
                        if idx >= 0:
                            snippet = text[max(0, idx - 100):idx + 700]
                            break
                    
                    alert = {
                        'date': filing_date,
                        'has_iss': has_iss,
                        'has_glass_lewis': has_gl,
                        'against': has_against,
                        'company_response': has_response,
                        'snippet': snippet[:600],
                    }
                    alerts.append(alert)
            except Exception:
                continue
        
        return alerts if alerts else None
    except Exception:
        return None

@st.cache_data(ttl=86400)
def fetch_institutional_ownership(company_name, cik, fy_year):
    """Extract top institutional owners from the DEF 14A proxy filing's beneficial ownership table."""
    import requests as _req
    import re
    try:
        _headers = {'User-Agent': 'Velarion Research andy@velarion.ai'}
        proxy_url = lookup_proxy_url(company_name, fy_year, cik)
        if not proxy_url:
            return None
        resp = _req.get(proxy_url, headers=_headers, timeout=20)
        if resp.status_code != 200:
            return None
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        tl = text.lower()
        
        # Find the beneficial ownership section
        start = None
        for marker in ['security ownership of certain beneficial', 'beneficial ownership of common',
                        'principal stockholders', 'known to us to beneficially own more than 5%',
                        'known to beneficially own more than 5%']:
            idx = tl.find(marker)
            if idx >= 0:
                start = idx
                break
        
        if start is None:
            return None
        
        chunk = text[start:start + 3000]
        
        # Parse institutional holders — look for patterns like "Name ... 85,929,843 ... 13%"
        owners = []
        known_institutions = [
            'Vanguard', 'BlackRock', 'State Street', 'Cohen & Steers', 'Capital International',
            'Capital Research', 'Fidelity', 'JPMorgan', 'T. Rowe Price', 'Wellington',
            'Invesco', 'Northern Trust', 'Goldman Sachs', 'Morgan Stanley', 'Dimensional',
            'Citadel', 'AEW', 'Brookfield', 'Heitman', 'Principal', 'Nuveen', 'TIAA',
            'Norges Bank', 'GIC', 'APG', 'PGGM', 'Canada Pension', 'CPPIB', 'Starboard',
            'Elliott', 'Land & Buildings', 'Barington', 'Third Point'
        ]
        
        lines = chunk.split('\n')
        for i, line in enumerate(lines):
            for inst in known_institutions:
                if inst.lower() in line.lower():
                    # Look in nearby lines for share count and percentage
                    nearby = '\n'.join(lines[max(0, i-1):i+5])
                    # Find percentage (e.g., "13%", "13 %", "13.2%")
                    pct_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%', nearby)
                    # Find share count (e.g., "85,929,843")
                    shares_match = re.search(r'(\d{1,3}(?:,\d{3}){2,})', nearby)
                    
                    if pct_match:
                        pct = float(pct_match.group(1))
                        shares = int(shares_match.group(1).replace(',', '')) if shares_match else None
                        # Filter out footnote numbers (small percentages unlikely to be ownership)
                        if pct >= 3.0:
                            owners.append({
                                'institution': inst,
                                'pct': pct,
                                'shares': shares,
                            })
                    break
        
        # Deduplicate and sort by percentage
        seen = set()
        unique = []
        for o in owners:
            if o['institution'] not in seen:
                seen.add(o['institution'])
                unique.append(o)
        unique.sort(key=lambda x: x['pct'], reverse=True)
        
        return unique[:7] if unique else None
    except Exception:
        return None

@st.cache_data(ttl=86400)
def fetch_material_8k_events(company_name, cik):
    """Fetch material 8-K events (CEO changes, acquisitions, restructuring, etc.)."""
    import requests as _req
    try:
        _headers = {'User-Agent': 'Velarion Research andy@velarion.ai'}
        clean_name = company_name.replace(',', '').replace('.', '').replace("'", '')
        query = f'%22{clean_name.replace(" ", "+")}%22'
        url = f'https://efts.sec.gov/LATEST/search-index?q={query}&forms=8-K&dateRange=custom&startdt=2024-06-01&enddt=2025-12-31'
        resp = _req.get(url, headers=_headers, timeout=10)
        if resp.status_code != 200:
            return None
        import json
        data = json.loads(resp.text)
        hits = data.get('hits', {}).get('hits', [])
        
        # Material item codes (exclude routine filings like 2.02 earnings, 9.01 exhibits)
        material_items = {
            '1.01': 'Material Agreement',
            '1.02': 'Bankruptcy/Receivership',
            '2.01': 'Acquisition/Disposition of Assets',
            '2.05': 'Restructuring/Impairment Costs',
            '2.06': 'Material Impairment',
            '3.01': 'Delisting/Transfer',
            '4.01': 'Auditor Change',
            '5.01': 'Change in Control',
            '5.02': 'Director/Officer Departure or Appointment',
        }
        
        events = []
        for h in hits[:30]:
            items = h['_source'].get('items', [])
            mat = [(code, material_items[code]) for code in items if code in material_items]
            if not mat:
                continue
            date = h['_source'].get('file_date', '')
            doc_id = h['_id']
            parts = doc_id.split(':')
            accession = parts[0]
            filename = parts[1]
            cik_clean = str(h['_source']['ciks'][0]).lstrip('0')
            
            # Fetch brief text for context
            try:
                filing_url = f'https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession.replace("-","")}/{filename}'
                from bs4 import BeautifulSoup
                filing_resp = _req.get(filing_url, headers=_headers, timeout=10)
                if filing_resp.status_code == 200:
                    soup = BeautifulSoup(filing_resp.text, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)[:500]
                else:
                    text = ""
            except Exception:
                text = ""
            
            item_labels = ', '.join(f"{code} ({label})" for code, label in mat)
            events.append(f"  [{date}] Items: {item_labels}\n    {text[:400]}")
            if len(events) >= 5:
                break
        
        return '\n'.join(events) if events else None
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
NOTE: The {pt_label} peer group had fewer than 5 {pos}s, so this analysis uses {n_wide} {pos}s across {n_wide_cos} similarly-sized companies (0.33x-3x market cap, all property types) as the benchmark.
INSTRUCTION: Explicitly note that the peer group was widened to similarly-sized companies due to limited same-sector peers. Use the widened data as primary benchmark."""
    prompt = f"""Real estate compensation analysis. 4-6 sentences.
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

def gen_analysis(co_d, filt, ret_data, all_df=None):
    """Combined company + returns analysis for Company View tab."""
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    cn = co_d['company_name'].iloc[0]; tk = co_d['ticker'].iloc[0]; pt = co_d['property_type'].iloc[0]; mc = co_d['market_cap'].iloc[0]
    ea = is_ext_advised(co_d, filt); ps = get_peer_stats(filt)
    n_co, mcr, tickers, pt_label = peer_context_str(filt, pt)
    en = "\nNOTE: Externally advised." if ea else ""
    # Widen thin positions adaptively by market cap proximity
    MIN_PEERS = 3
    elines = []
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; ip = detect_partial(rw, filt)
        pp = ps[ps['position']==rw['position']]
        n_pos = len(pp[pp['total_comp'].notna()])
        widened = False
        use_ps = ps
        if n_pos < MIN_PEERS and all_df is not None:
            wide_ps, n_wide_cos, mult = build_mcap_wide_peers(all_df, tk, co_d, rw['position'], MIN_PEERS)
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
        if widened: fl.append(f'Widened to {len(pp)} similar market cap peers')
        fs = f" [{', '.join(fl)}]" if fl else ""
        elines.append(f"  {rw['first_name']} {rw['last_name']}, {POSITION_DISPLAY.get(rw['position'],rw['position'])}: ${t:,.0f} ({ordinal(pct)} pctl, {quartile_label(pct)}) | Mix: {mix} | Peer mix: {pm}{fs}")
    tb = co_d['total_comp'].sum(); pcos = ps.groupby('ticker')['total_comp'].sum(); bp = percentile_rank(tb, pcos)
    r = ret_data.get(tk, {}); vnq = ret_data.get(REIT_INDEX_TICKER, {})
    peer_r1s = [ret_data.get(t,{}).get('return_1y') for t in tickers if ret_data.get(t,{}).get('return_1y') is not None]
    p3 = [ret_data.get(t,{}).get('return_3y') for t in tickers if ret_data.get(t,{}).get('return_3y') is not None]
    ret_pct = percentile_rank(r.get('return_1y'), pd.Series(peer_r1s)) if r.get('return_1y') is not None and peer_r1s else None
    prompt = f"""Real estate compensation and performance analysis. 6-8 sentences covering both team compensation positioning and shareholder returns.
{cn} ({tk}) | {pt} | Mkt Cap ${mc/1e9:.2f}B
TEAM:\n{chr(10).join(elines)}
Budget: ${tb:,.0f} ({ordinal(bp)} pctl vs {len(pcos)} peers)
FY{RETURNS_YEAR} Returns: {tk} 1-Yr {fmt_return(r.get('return_1y'))} ({ordinal(ret_pct)} pctl returns, {quartile_label(ret_pct)}) | 3-Yr {fmt_return(r.get('return_3y'))} | YTD {RETURNS_YEAR+1} {fmt_return(r.get('return_ytd'))}
Peer Avg ({n_co} cos): 1-Yr {fmt_return(np.mean(peer_r1s) if peer_r1s else None)} | 3-Yr {fmt_return(np.mean(p3) if p3 else None)}
FTSE Nareit: 1-Yr {fmt_return(vnq.get('return_1y'))} | 3-Yr {fmt_return(vnq.get('return_3y'))} | YTD {RETURNS_YEAR+1} {fmt_return(vnq.get('return_ytd'))}
Peers: {n_co} companies | Tickers: {', '.join(tickers)}
NOTE: Compensation data is from the FY{FY_YEAR} DEF 14A proxy filing (filed in {FY_YEAR+1}). Returns are through Dec 31, {RETURNS_YEAR} (1-yr and 3-yr) plus YTD {RETURNS_YEAR+1}. Frame the analysis as: how has the compensation structure approved by the board performed against {RETURNS_YEAR} shareholder returns?
CRITICAL: Only reference return figures explicitly provided above. Do NOT invent, estimate, or reference any return data not given. Do NOT reference years or periods for which no data is provided.
INSTRUCTIONS: Cover (1) each executive's compensation positioning and mix vs peers, (2) shareholder returns vs peer group and FTSE Nareit, (3) pay-for-performance assessment comparing comp quartile to returns quartile, and (4) a clear directional recommendation. If comp is below returns quartile, advocate for the management team. If any executive is flagged as [Partial Yr], explicitly note their compensation reflects a partial year of service and should not be compared at face value to full-year peers — do NOT characterize their pay as "low" or "below median" since it only reflects a fraction of the year. For partial-year executives, focus on compensation structure and mix rather than dollar amounts or percentile rankings. If ALL executives are partial year, lead with that context and frame the entire analysis around comp structure, equity weighting, and forward-looking positioning rather than peer dollar comparisons. If any executive is flagged as [Widened], note that the peer group was expanded beyond the primary peer set due to limited same-position peers.
At the very end, add a single-line italic footnote: "Sources: FY{FY_YEAR} DEF 14A proxy filing (SEC EDGAR), Yahoo Finance stock returns, Velarion peer compensation database ({n_co} companies)."{en}
{AI_TONE}"""
    try:
        resp = cl.messages.create(model="claude-sonnet-4-20250514", max_tokens=700, messages=[{"role":"user","content":prompt}])
        return clean_ai(resp.content[0].text)
    except Exception as e: return f"Error: {e}"

def gen_full(co_d, filt, ret_data, excluded_tks=None, added_tks=None, all_df=None, peer_mode='proxy'):
    cl = get_client()
    if not cl: return "Install anthropic library and set ANTHROPIC_API_KEY."
    cn = co_d['company_name'].iloc[0]; tk = co_d['ticker'].iloc[0]; pt = co_d['property_type'].iloc[0]; mc = co_d['market_cap'].iloc[0]
    hq = f"{co_d['hq_city'].iloc[0]}, {co_d['hq_state'].iloc[0]}"
    ea = is_ext_advised(co_d, filt); ps = get_peer_stats(filt)
    n_co, mcr, tickers, pt_label = peer_context_str(filt, pt)
    # Peer group descriptor based on mode
    if peer_mode == 'proxy':
        peer_desc = f"{n_co} companies from {cn}'s proxy-disclosed compensation peer group (cross-sector, not limited to real estate)"
    else:
        peer_desc = f"{n_co} custom peer companies"
    en = "\nCRITICAL: Externally advised." if ea else ""
    # Widen thin positions adaptively by market cap proximity
    MIN_PEERS = 3
    esecs = []
    widened_positions = []
    for _, rw in sort_by_position(co_d).iterrows():
        ie = rw['comp_source']=='external_manager'; ip = detect_partial(rw, filt)
        pp = ps[ps['position']==rw['position']]
        n_pos = len(pp[pp['total_comp'].notna()])
        use_ps = ps
        # Auto-widen if thin — but NOT in proxy mode (proxy peers are the intended comp group)
        if n_pos < MIN_PEERS and all_df is not None and peer_mode != 'proxy':
            wide_ps, n_wide_cos, mult = build_mcap_wide_peers(all_df, tk, co_d, rw['position'], MIN_PEERS)
            pp_wide = wide_ps[wide_ps['position']==rw['position']]
            if len(pp_wide[pp_wide['total_comp'].notna()]) >= n_pos:
                pp = pp_wide
                widened_positions.append(rw['position'])
                use_ps = wide_ps
        t = rw['total_comp'] if pd.notna(rw['total_comp']) else 0
        tp = percentile_rank(rw['total_comp'], pp['total_comp']); mix = comp_mix_str(rw); pm = peer_mix_median(use_ps, rw['position'])
        fl = []
        if ie: fl.append('EXT')
        if ip: fl.append('PARTIAL YR')
        if rw['position'] in widened_positions: fl.append(f'WIDENED TO {len(pp)} SIMILAR MARKET CAP PEERS')
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
    cik_val = co_d['cik'].iloc[0] if 'cik' in co_d.columns else None
    say_on_pay = fetch_say_on_pay(cn, cik_val, FY_YEAR + 1) if cik_val else None
    financials_10k = fetch_10k_financials(cik_val) if cik_val else None
    financials_10q = fetch_10q_financials(cik_val) if cik_val else None
    material_events = fetch_material_8k_events(cn, cik_val) if cik_val else None
    proxy_alerts = fetch_proxy_advisory_alerts(cn, cik_val, FY_YEAR + 1) if cik_val else None
    inst_owners = fetch_institutional_ownership(cn, cik_val, FY_YEAR) if cik_val else None
    
    # Build source list for footnotes
    sources = []
    proxy_url = lookup_proxy_url(cn, FY_YEAR, cik_val)
    sources.append(f"DEF 14A Proxy Statement, FY{FY_YEAR} (filed {FY_YEAR+1}), SEC EDGAR" + (f" — {proxy_url}" if proxy_url else ""))
    if cda_text:
        sources.append(f"Compensation Discussion & Analysis (CD&A) section from FY{FY_YEAR} DEF 14A")
    if earnings_text:
        sources.append(f"8-K Earnings Press Releases (quarterly results, 2024-2025), SEC EDGAR")
    if say_on_pay:
        sources.append(f"8-K Voting Results (Item 5.07), filed {say_on_pay.get('filing_date', '')}, SEC EDGAR")
    if financials_10k:
        sources.append(f"10-K Annual Report financial data via SEC EDGAR XBRL")
    if financials_10q:
        sources.append(f"10-Q Quarterly Report financial data via SEC EDGAR XBRL")
    if material_events:
        sources.append(f"8-K Material Event filings (leadership changes, acquisitions, restructuring), SEC EDGAR")
    if proxy_alerts:
        sources.append(f"DEFA14A Supplemental Proxy filings (proxy advisory firm recommendations/responses), SEC EDGAR")
    if inst_owners:
        sources.append(f"Beneficial Ownership disclosure from DEF 14A (institutional holders >5%), SEC EDGAR")
    if current_stock:
        sources.append(f"Current stock data via Yahoo Finance (as of {current_stock.get('as_of', 'today')})")
    sources.append(f"Historical stock returns (1-yr, 3-yr, YTD) via Yahoo Finance, through Dec 31, {RETURNS_YEAR}")
    sources.append(f"FTSE Nareit All Equity REITs Index (VNQ) benchmark returns")
    sources.append(f"Velarion Company Intelligence peer compensation database ({n_co} peer companies)")
    sources_str = chr(10).join(f"  {i+1}. {s}" for i, s in enumerate(sources))

    # Build enrichment sections for prompt
    enrichment = ""
    if cda_text:
        # Truncate CD&A for prompt (keep under ~8K chars for the prompt)
        cda_snippet = cda_text[:8000]
        enrichment += f"\n\nCD&A EXCERPT (from FY{FY_YEAR} proxy — use to identify performance metrics, comp philosophy, say-on-pay results, and peer group rationale):\n{cda_snippet}"
    if earnings_text:
        earnings_snippet = earnings_text[:4000]
        enrichment += f"\n\nRECENT QUARTERLY EARNINGS (use for operational context — FFO/AFFO, revenue, occupancy, same-store NOI):\n{earnings_snippet}"
    if say_on_pay:
        enrichment += f"\n\nSAY-ON-PAY VOTE RESULTS ({say_on_pay.get('filing_date', '')}):"
        enrichment += f"\n  Approval: {say_on_pay['approval_pct']}% ({say_on_pay['votes_for']:,} For / {say_on_pay['votes_against']:,} Against)"
        if say_on_pay['approval_pct'] < 70:
            enrichment += "\n  ⚠ LOW APPROVAL — This is a significant governance risk. Below 70% typically triggers enhanced engagement with shareholders and potential comp structure changes."
        elif say_on_pay['approval_pct'] >= 95:
            enrichment += "\n  Strong shareholder support for current compensation program."
    if financials_10k:
        enrichment += f"\n\n10-K FINANCIAL HIGHLIGHTS (most recent annual filing, SEC EDGAR XBRL):"
        for label, d in financials_10k.items():
            val = d['value']
            if d['unit'] == 'USD' and abs(val) >= 1e6:
                val_str = f"${val/1e6:,.0f}M" if abs(val) < 1e9 else f"${val/1e9:,.1f}B"
            elif d['unit'] == 'USD/shares':
                val_str = f"${val:.2f}"
            else:
                val_str = f"{val:,.0f}"
            yoy = f" (YoY: {d['yoy_change']:+.1f}%)" if d.get('yoy_change') is not None else ""
            enrichment += f"\n  {label}: {val_str}{yoy} [{d['period']}]"
    if financials_10q:
        enrichment += f"\n\nQUARTERLY FINANCIAL TREND (10-Q filings, SEC EDGAR XBRL — use to assess recent trajectory):\n{financials_10q}"
    if material_events:
        enrichment += f"\n\nMATERIAL EVENTS (8-K filings — leadership changes, acquisitions, restructuring, material agreements):\n{material_events}"
        enrichment += "\n  NOTE: Reference these events where they are relevant to compensation decisions, leadership transitions, or strategic context."
    if proxy_alerts:
        enrichment += f"\n\nPROXY ADVISORY ALERTS (DEFA14A filings — ISS/Glass Lewis recommendations and company responses):"
        for alert in proxy_alerts:
            advisory = []
            if alert.get('has_iss'): advisory.append('ISS')
            if alert.get('has_glass_lewis'): advisory.append('Glass Lewis')
            adv_str = ' & '.join(advisory) if advisory else 'Proxy advisory'
            status = "AGAINST recommendation" if alert.get('against') else "recommendation noted"
            response = " — COMPANY FILED RESPONSE" if alert.get('company_response') else ""
            enrichment += f"\n  [{alert['date']}] {adv_str}: {status}{response}"
            enrichment += f"\n    {alert['snippet'][:400]}"
        enrichment += "\n  ⚠ CRITICAL FOR BOARD PREP: If ISS or Glass Lewis recommended AGAINST say-on-pay, this MUST be addressed in Board Considerations. The comp committee will face direct questions about this."
    if inst_owners:
        enrichment += f"\n\nINSTITUTIONAL OWNERSHIP (from DEF 14A beneficial ownership table):"
        total_pct = 0
        for o in inst_owners:
            shares_str = f" ({o['shares']:,} shares)" if o.get('shares') else ""
            enrichment += f"\n  {o['institution']}: {o['pct']}%{shares_str}"
            total_pct += o['pct']
        enrichment += f"\n  Top {len(inst_owners)} holders control ~{total_pct:.0f}% of shares"
        # Flag if passive index funds dominate (they follow ISS)
        index_funds = [o for o in inst_owners if o['institution'] in ('Vanguard', 'BlackRock', 'State Street')]
        if index_funds:
            idx_pct = sum(o['pct'] for o in index_funds)
            enrichment += f"\n  NOTE: Passive index funds ({', '.join(o['institution'] for o in index_funds)}) hold ~{idx_pct:.0f}% — these investors typically follow ISS vote recommendations on say-on-pay."
    if current_stock:
        enrichment += f"\n\nCURRENT STOCK DATA (as of {current_stock['as_of']}):"
        enrichment += f"\n  {tk}: ${current_stock['current_price']:.2f} | YTD {RETURNS_YEAR+1}: {current_stock['ytd_return']:+.1f}%" if current_stock.get('ytd_return') is not None else ""
        enrichment += f"\n  VNQ (Real Estate Index) YTD {RETURNS_YEAR+1}: {current_stock['vnq_ytd']:+.1f}%" if current_stock.get('vnq_ytd') is not None else ""
    
    # Per-peer returns for richer analysis
    peer_ret_lines = []
    for pt_tk in tickers:
        pr = ret_data.get(pt_tk, {})
        if pr.get('return_1y') is not None:
            peer_ret_lines.append(f"  {pt_tk}: 1-Yr {fmt_return(pr.get('return_1y'))} | 3-Yr {fmt_return(pr.get('return_3y'))}")
    peer_ret_str = chr(10).join(peer_ret_lines) if peer_ret_lines else "  No peer return data available"
    
    prompt = f"""Real estate compensation analysis (~600-800 words). You are advising this management team — preparing them for what their board and comp committee will ask.
{cn} ({tk}) | {pt} | {co_d['reit_type'].iloc[0]} | HQ: {hq} | Mkt Cap ${mc/1e9:.2f}B
EXECUTIVES:\n{chr(10).join(esecs)}
{rl}
Budget: ${tb:,.0f} ({ordinal(bp)} pctl vs {len(pcos)} peers)
SHAREHOLDER RETURNS:
  {tk}: 1-Yr {fmt_return(r.get('return_1y'))} ({ordinal(ret_pct)} pctl, {quartile_label(ret_pct)}) | 3-Yr {fmt_return(r.get('return_3y'))} | YTD {RETURNS_YEAR+1} {fmt_return(r.get('return_ytd'))}
  FTSE Nareit Index: 1-Yr {fmt_return(vnq.get('return_1y'))} | 3-Yr {fmt_return(vnq.get('return_3y'))} | YTD {RETURNS_YEAR+1} {fmt_return(vnq.get('return_ytd'))}
  Peer Avg: 1-Yr {fmt_return(np.mean(p1) if p1 else None)} | 3-Yr {fmt_return(np.mean(p3) if p3 else None)}
INDIVIDUAL PEER RETURNS:
{peer_ret_str}
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
PAY-FOR-PERFORMANCE ANALYSIS (THIS IS THE MOST IMPORTANT SECTION):
You MUST explicitly state and compare these three return figures: (1) {tk}'s 1-yr return, (2) FTSE Nareit 1-yr return, and (3) peer average 1-yr return. State whether {tk} outperformed or underperformed vs EACH benchmark and by how much. Then compare: if comp is below median but returns are above average, that's a clear case for upward adjustment — say so directly with the numbers. If comp is above median but returns lag, flag the misalignment. Include 3-yr returns for trend context. Reference CD&A performance metrics if available. (4-5 sent, with specific return numbers)

[SECTION:WATCH]
<h4>Board Considerations</h4>
Based on CD&A compensation structure, recent earnings trajectory, and stock performance, flag 2-3 things management should be prepared to address with the board. Frame as "management should be prepared to discuss..." not prescriptive. (2-3 sent)

Summary with peer group disclosure including any excluded companies (2-3 sent, list all peer tickers)

[SECTION:SOURCES]
<h4>Sources</h4>
You MUST include a formatted sources section listing every data source used in this analysis. Use the source list below — include ALL of them as numbered items in plain text (no links, just descriptions). This is critical for credibility.
AVAILABLE SOURCES:
{sources_str}
{en}
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

def chart_comp_mix(co_d, peers, pt, all_df=None):
    """Stacked horizontal bar: company comp mix vs peer median."""
    ps = get_peer_stats(peers)
    tk = co_d['ticker'].iloc[0]
    MIN_PEERS = 3
    fig = go.Figure()
    labels = []
    sal_pcts = []; cash_pcts = []; eq_pcts = []; oth_pcts = []
    # Company execs
    for _, rw in sort_by_position(co_d).iterrows():
        if rw['comp_source'] == 'external_manager': continue
        tc = rw['total_comp'] if pd.notna(rw['total_comp']) and rw['total_comp'] > 0 else 1
        s = (rw['base_salary'] or 0) / tc * 100
        c = (rw['cash_bonus_incentive'] or 0) / tc * 100
        e = (rw['stock_based_comp'] or 0) / tc * 100
        o = max(0, 100 - s - c - e)
        pos_d = POSITION_DISPLAY.get(rw['position'], rw['position'])
        labels.append(f"{rw['last_name']} ({pos_d})")
        sal_pcts.append(round(s, 1)); cash_pcts.append(round(c, 1)); eq_pcts.append(round(e, 1)); oth_pcts.append(round(o, 1))
    # Peer median — use widened if thin
    for pos in ['CEO','CFO','COO','CIO','GC','CAO']:
        pp = ps[ps['position']==pos]
        use_pp = pp
        suffix = ''
        if len(pp) < MIN_PEERS and all_df is not None:
            wide_ps, _, _ = build_mcap_wide_peers(all_df, tk, co_d, pos, MIN_PEERS)
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
        o_med = max(0, 100 - s_med - c_med - e_med)
        labels.append(f"Peer {POSITION_DISPLAY.get(pos, pos)}{suffix}")
        sal_pcts.append(round(s_med, 1)); cash_pcts.append(round(c_med, 1)); eq_pcts.append(round(e_med, 1)); oth_pcts.append(round(o_med, 1))
    fig.add_trace(go.Bar(name='Base Salary', y=labels, x=sal_pcts, orientation='h', marker_color=CHART_COLORS['salary'], text=[f'{v:.0f}%' for v in sal_pcts], textposition='inside', textfont=dict(color='white', size=11)))
    fig.add_trace(go.Bar(name='Cash Bonus', y=labels, x=cash_pcts, orientation='h', marker_color=CHART_COLORS['cash'], text=[f'{v:.0f}%' for v in cash_pcts], textposition='inside', textfont=dict(color='white', size=11)))
    fig.add_trace(go.Bar(name='Non-Cash Equity', y=labels, x=eq_pcts, orientation='h', marker_color=CHART_COLORS['equity'], text=[f'{v:.0f}%' for v in eq_pcts], textposition='inside', textfont=dict(color='white', size=11)))
    fig.add_trace(go.Bar(name='All Other', y=labels, x=oth_pcts, orientation='h', marker_color='#94a3b8', text=[f'{v:.0f}%' if v >= 3 else '' for v in oth_pcts], textposition='inside', textfont=dict(color='white', size=11)))
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

def chart_exec_positioning(co_d, peers, all_df=None):
    """Grouped horizontal bar: exec total comp vs peer median side by side."""
    ps = get_peer_stats(peers)
    tk = co_d['ticker'].iloc[0]
    MIN_PEERS = 3
    labels = []; exec_vals = []; median_vals = []; hover_exec = []; hover_med = []
    for _, rw in sort_by_position(co_d).iterrows():
        if rw['comp_source'] == 'external_manager': continue
        if pd.isna(rw['total_comp']): continue
        pp = ps[ps['position']==rw['position']]
        n_pos = len(pp[pp['total_comp'].notna()])
        widened = False
        if n_pos < MIN_PEERS and all_df is not None:
            wide_ps, _, _ = build_mcap_wide_peers(all_df, tk, co_d, rw['position'], MIN_PEERS)
            pp_wide = wide_ps[wide_ps['position']==rw['position']]
            if len(pp_wide[pp_wide['total_comp'].notna()]) >= n_pos:
                pp = pp_wide
                widened = True
        med = pp['total_comp'].dropna().median()
        if pd.isna(med) or med == 0: continue
        val = rw['total_comp']
        pos_d = POSITION_DISPLAY.get(rw['position'], rw['position'])
        suffix = ' *' if widened else ''
        labels.append(f"{rw['last_name']} ({pos_d}){suffix}")
        exec_vals.append(val / 1e6)
        median_vals.append(med / 1e6)
        hover_exec.append(f"${val:,.0f}")
        hover_med.append(f"${med:,.0f} (n={n_pos})")
    if not labels: return None
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=exec_vals, orientation='h', name='Actual',
        marker_color=CHART_COLORS['primary'],
        text=[f'${v:.1f}M' for v in exec_vals], textposition='outside',
        textfont=dict(size=11, color=CHART_COLORS['text']),
        hovertext=hover_exec, hoverinfo='text'
    ))
    fig.add_trace(go.Bar(
        y=labels, x=median_vals, orientation='h', name='Peer Median',
        marker_color='#d4a84b', marker_opacity=0.6,
        text=[f'${v:.1f}M' for v in median_vals], textposition='outside',
        textfont=dict(size=11, color='#92400e'),
        hovertext=hover_med, hoverinfo='text'
    ))
    footnote = '  * = widened to similarly-sized companies' if any('*' in l for l in labels) else ''
    fig.update_layout(
        barmode='group', bargroupgap=0.15,
        height=max(220, len(labels)*70),
        margin=dict(l=10, r=60, t=40, b=30),
        title=dict(text='Executive Total Comp vs Peer Median', font=dict(size=14, color=CHART_COLORS['text'])),
        xaxis=dict(title='Total Compensation ($M)', showgrid=True, gridcolor='#f1f5f9', tickprefix='$', ticksuffix='M'),
        yaxis=dict(autorange='reversed'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=11)),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Inter, Helvetica, Arial, sans-serif')
    )
    if footnote:
        fig.add_annotation(text=footnote, xref='paper', yref='paper', x=0, y=-0.12, showarrow=False, font=dict(size=10, color='#94a3b8'))
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
    story.append(Paragraph(f"Real Estate Compensation Analysis: {cn} ({tk})", ss))
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
    story.append(Paragraph(f"Peer group: {n_co} {pt} companies, market cap {mcr}", ds))
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
st.markdown('<div class="main-header"><h1>Velarion Company Intelligence</h1><p>Executive &amp; Board Compensation Advisory &mdash; Powered by AI</p></div>', unsafe_allow_html=True)
st.markdown(f'<div class="intro-text">Explore executive and board compensation across {len(reit_tickers)} publicly traded real estate companies. Select a company to benchmark against its proxy-disclosed peer group, or build a custom comparison set.</div>', unsafe_allow_html=True)

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
        st.markdown(f'<div class="filter-note">\u26A0\uFE0F No proxy peer group found in {sel_tk}\'s FY{FY_YEAR} DEF 14A filing. Defaulting to {sel_pt} companies. Use Custom Peer Group Filters to refine.</div>', unsafe_allow_html=True)
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
c1,c2,c3,c4,c5,c6 = st.columns(6)
cv_selected = st.session_state.get('cv_co', PLACEHOLDER)
_dir_kpi_df = load_director_comp()
if cv_selected and cv_selected != PLACEHOLDER and cv_selected in co_labels:
    cv_tk = co_labels[cv_selected]
    peers_in_filt = filt[filt['ticker'] != cv_tk]
    n_peer_cos = peers_in_filt['ticker'].nunique()
    peer_stats_for_kpi = get_peer_stats(peers_in_filt)
    mode_label = "proxy peers" if st.session_state.get('peer_mode') == 'proxy' else "custom peers"
    _dir_peer = _dir_kpi_df[_dir_kpi_df['ticker'].isin(peers_in_filt['ticker'].unique())] if not _dir_kpi_df.empty else pd.DataFrame()
    _med_dir = _dir_peer['total_comp'].dropna().median() if not _dir_peer.empty else 0
    with c1: st.markdown(f'<div class="metric-card"><div class="label">Peer Companies</div><div class="value">{n_peer_cos}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="label">Executives</div><div class="value">{len(peer_stats_for_kpi)}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="label">Med. Exec Salary</div><div class="value">{fmt_dollars(peer_stats_for_kpi["base_salary"].median())}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="label">Med. Exec Total</div><div class="value">{fmt_dollars(peer_stats_for_kpi["total_comp"].median())}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><div class="label">Med. Director Comp</div><div class="value">{fmt_dollars(_med_dir)}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
    with c6: st.markdown(f'<div class="metric-card"><div class="label">Med. Mkt Cap</div><div class="value">{fmt_mcap(peers_in_filt["market_cap"].median())}</div><div class="sub">{mode_label}</div></div>', unsafe_allow_html=True)
else:
    # No company selected — show full REIT universe
    reit_stats = get_peer_stats(reit_df)
    _n_dir_total = len(_dir_kpi_df) if not _dir_kpi_df.empty else 0
    _med_dir_all = _dir_kpi_df['total_comp'].dropna().median() if not _dir_kpi_df.empty else 0
    with c1: st.markdown(f'<div class="metric-card"><div class="label">Companies</div><div class="value">{reit_df["ticker"].nunique()}</div><div class="sub">in universe</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="label">Executives</div><div class="value">{len(reit_stats)}</div><div class="sub">all companies</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="label">Directors</div><div class="value">{_n_dir_total:,}</div><div class="sub">all companies</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="label">Med. Exec Total</div><div class="value">{fmt_dollars(reit_stats["total_comp"].median())}</div><div class="sub">all executives</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><div class="label">Med. Director Comp</div><div class="value">{fmt_dollars(_med_dir_all)}</div><div class="sub">all directors</div></div>', unsafe_allow_html=True)
    with c6: st.markdown(f'<div class="metric-card"><div class="label">Med. Mkt Cap</div><div class="value">{fmt_mcap(reit_df["market_cap"].median())}</div><div class="sub">all companies</div></div>', unsafe_allow_html=True)
st.markdown("")

# COMPANY VIEW
st.markdown("#### Company Compensation Intelligence")
cv_opts = [PLACEHOLDER] + co_opts
_dd_col, _ = st.columns([1, 1])
with _dd_col:
    sel3 = st.selectbox("cv", cv_opts, key="cv_co", label_visibility="collapsed")
cv_selected_val = st.session_state.get('cv_co', PLACEHOLDER)
if not cv_selected_val or cv_selected_val == PLACEHOLDER:
    # Engaging pre-select state highlighting Board + Management coverage
    # Use same filtered datasets as top metric cards for consistent counts
    dir_df_preview = load_director_comp()
    _n_dirs = len(dir_df_preview) if not dir_df_preview.empty else 0
    _n_execs = len(reit_df) if not reit_df.empty else 0
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a365d 0%,#2d4a7a 100%);border-radius:12px;padding:2rem 2.5rem;margin:0.5rem 0 1.5rem 0;color:white;border:2px solid #b8860b;box-shadow:0 4px 12px rgba(184,134,11,0.15);">
        <div style="font-size:1.1rem;font-weight:600;margin-bottom:1.2rem;">Select a company above to access full compensation intelligence with AI</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;">
            <div style="background:rgba(255,255,255,0.1);border-radius:8px;padding:1.2rem;">
                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;opacity:0.7;margin-bottom:0.5rem;">\U0001F4BC Executive Compensation</div>
                <div style="font-size:1.5rem;font-weight:700;">{_n_execs:,} Executives</div>
                <div style="font-size:0.75rem;opacity:0.5;margin-top:0.5rem;">Base salary, cash bonus, equity awards, total comp<br>Peer benchmarking &bull; AI-powered analysis &bull; League tables</div>
            </div>
            <div style="background:rgba(255,255,255,0.1);border-radius:8px;padding:1.2rem;">
                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;opacity:0.7;margin-bottom:0.5rem;">\U0001F3DB\uFE0F Board of Directors</div>
                <div style="font-size:1.5rem;font-weight:700;">{_n_dirs:,} Directors</div>
                <div style="font-size:0.75rem;opacity:0.5;margin-top:0.5rem;">Component &amp; aggregate board compensation<br>Peer benchmarking &bull; AI-powered analysis</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
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
        _hq = f"{cd3['hq_city'].iloc[0]}, {cd3['hq_state'].iloc[0]}"
        _mcap = fmt_mcap(cd3['market_cap'].iloc[0])
        cr3 = ret_data.get(stk3, {}); vnq3 = ret_data.get(REIT_INDEX_TICKER, {})
        
        # Build returns HTML if available
        _ret_html = ""
        if cr3:
            _r1y = fmt_return(cr3.get('return_1y')); _r3y = fmt_return(cr3.get('return_3y')); _rytd = fmt_return(cr3.get('return_ytd'))
            _v1y = fmt_return(vnq3.get('return_1y')); _v3y = fmt_return(vnq3.get('return_3y')); _vytd = fmt_return(vnq3.get('return_ytd'))
            _ret_html = f"""
            <div style="border-top:1px solid #e2e8f0;margin-top:0.8rem;padding-top:0.8rem;">
                <table style="width:75%;font-size:0.9rem;border-collapse:collapse;">
                    <tr style="color:#64748b;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em;">
                        <td style="padding:2px 0;width:16%;">1-Yr (FY{RETURNS_YEAR})</td>
                        <td style="padding:2px 0;width:16%;">3-Year (FY{RETURNS_YEAR})</td>
                        <td style="padding:2px 0;width:18%;">YTD {RETURNS_YEAR+1}</td>
                        <td style="padding:2px 0;width:16%;">FTSE Nareit 1-Yr</td>
                        <td style="padding:2px 0;width:16%;">FTSE Nareit 3-Yr</td>
                        <td style="padding:2px 0;width:18%;">FTSE Nareit YTD</td>
                    </tr>
                    <tr style="font-weight:700;color:#1e293b;">
                        <td style="padding:2px 0;">{_r1y}</td>
                        <td style="padding:2px 0;">{_r3y}</td>
                        <td style="padding:2px 0;">{_rytd}</td>
                        <td style="padding:2px 0;color:#64748b;">{_v1y}</td>
                        <td style="padding:2px 0;color:#64748b;">{_v3y}</td>
                        <td style="padding:2px 0;color:#64748b;">{_vytd}</td>
                    </tr>
                </table>
            </div>"""
        
        # Company profile card — use components.html because st.markdown strips <table>
        _profile_html = f"""
        <div style="font-family:'Source Sans Pro','Segoe UI',Roboto,sans-serif;font-size:16px;border:1px solid #e2e8f0;border-radius:10px;padding:1.4rem 1.8rem;background:white;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
            <div style="font-size:1.5rem;font-weight:700;color:#1e293b;margin-bottom:0.6rem;">{cn3} ({stk3})</div>
            <div style="display:flex;gap:2.5rem;font-size:0.95rem;color:#475569;">
                <div><span style="color:#94a3b8;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">HQ</span><br><span style="font-weight:600;color:#1e293b;">{_hq}</span></div>
                <div><span style="color:#94a3b8;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Property Type</span><br><span style="font-weight:600;color:#1e293b;">{pt3}</span></div>
                <div><span style="color:#94a3b8;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Market Cap</span><br><span style="font-weight:600;color:#1e293b;">{_mcap}</span></div>
            </div>
            {_ret_html}
        </div>
        """
        _profile_h = 190 if cr3 else 120
        components.html(_profile_html, height=_profile_h, scrolling=False)
        
        ea3 = is_ext_advised(cd3, df)
        if ea3: st.markdown(f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:0.6rem 1rem;font-size:0.83rem;color:#92400e;margin:0.5rem 0;">\u26A0\uFE0F {get_ext_note(cd3)}</div>', unsafe_allow_html=True)
        components.html('<button onclick="window.parent.print()" style="background:#475569;color:white;border:none;border-radius:6px;padding:5px 14px;font-size:0.75rem;font-weight:600;cursor:pointer;float:right;">\U0001F5A8 Print This Page</button>', height=35)
        
        # ---- PEER BENCHMARKING ----
        st.markdown("#### Compensation Benchmarking")
        
        tab_exec, tab_board = st.tabs(["\U0001F4BC Executive", "\U0001F3DB\uFE0F Board"])
        
        with tab_exec:
            peers_only = filt_no_pos[filt_no_pos['ticker'] != stk3]
            n_co, mcr, peer_tks, _ = peer_context_str(peers_only, pt3)
            auto_peers = get_peer_stats(peers_only)
        
            # Show peer source context
            no_proxy = not proxy_tickers or len(proxy_tickers) == 0
            if st.session_state.get('peer_mode') == 'proxy':
                n_proxy_total = len(proxy_tickers) if proxy_tickers else 0
                if n_co < n_proxy_total:
                    peer_line = f"Compared to <strong>{n_co} of {n_proxy_total} proxy-disclosed peer companies</strong> from {cn3}'s FY{FY_YEAR} DEF 14A filing ({', '.join(peer_tks)})"
                else:
                    peer_line = f"Compared to <strong>{n_co} proxy-disclosed peer companies</strong> from {cn3}'s FY{FY_YEAR} DEF 14A filing ({', '.join(peer_tks)})"
            else:
                # Check if this is a no-proxy-peer company defaulting to property type
                if no_proxy:
                    peer_line = f'<div style="background:#fffbeb;border:1px solid #d4a017;border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.5rem;font-size:0.85rem;color:#92400e;">\u26A0\uFE0F <strong>No proxy-defined compensation peer group found</strong> in {cn3}\'s FY{FY_YEAR} DEF 14A filing. Defaulted to {pt3} companies.</div>'
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
                if st.button("\U0001F4CB  Generate Executive Compensation Analysis", key="cv_lookup_rpt", use_container_width=True):
                    with st.spinner("\u23F3 Report generating — pulling CD&A, earnings, and stock data. This takes 10-15 seconds..."):
                        st.session_state['lk_rpt'] = gen_full(cd3, peers_only, ret_data, excluded_tks=custom_removed, added_tks=custom_added, all_df=df, peer_mode=st.session_state.get('peer_mode', 'proxy'))
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
                if st.button("\U0001F4CB  Executive Compensation Summary Table", key="cv_comp_toggle", use_container_width=True):
                    st.session_state['show_comp_table'] = not st.session_state.get('show_comp_table', False)
            with btn_r2b:
                proxy_url = lookup_proxy_url(cn3, FY_YEAR, cik=cd3['cik'].iloc[0] if 'cik' in cd3.columns else None)
                if proxy_url:
                    st.link_button("\U0001F4C4  View Proxy", proxy_url, use_container_width=True)
                else:
                    st.button("\U0001F4C4  View Proxy", key="cv_proxy_btn", disabled=True, use_container_width=True, help="Proxy filing not found on SEC EDGAR")
            # ---- PROXY-DISCLOSED PEER GROUP (moved below buttons) ----
            co_peers_display, proxy_tks_display, _ = _build_proxy_peer_data(stk3, peer_groups_df, df)
            if not co_peers_display.empty:
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

            # Display Full Report
            if st.session_state.get('lk_tk') == stk3 and st.session_state.get('lk_rpt'):
                if st.session_state.get('fp_lk_rpt') != cur_fp0:
                    st.markdown(STALE_WARNING, unsafe_allow_html=True)
                rt = st.session_state['lk_rpt']
            
                # Parse sections and interleave charts
                st.markdown(f'<div class="ai-report"><div class="ai-label">\U0001F4CB Compensation Analysis \u2014 {cn3}</div>', unsafe_allow_html=True)
            
                # Split on section markers
                import re
                section_pattern = r'\[SECTION:(POSITIONING|MIX|RETURNS|WATCH|SOURCES)\]'
                parts = re.split(section_pattern, rt)
            
                try:
                    n_co_ctx, _, peer_tks_ctx, _ = peer_context_str(peers_only, pt3)
                except Exception:
                    peer_tks_ctx = []
            
                i = 0
                while i < len(parts):
                    text = parts[i].strip()
                    if text and text not in ('POSITIONING', 'MIX', 'RETURNS', 'WATCH', 'SOURCES'):
                        st.markdown(text, unsafe_allow_html=True)
                    elif text == 'POSITIONING':
                        if i + 1 < len(parts):
                            st.markdown(parts[i+1].strip(), unsafe_allow_html=True)
                            i += 1
                        try:
                            fig_pos = chart_exec_positioning(cd3, peers_only, all_df=df)
                            st.plotly_chart(fig_pos, use_container_width=True, key="rpt_pos_chart")
                        except Exception: pass
                    elif text == 'MIX':
                        if i + 1 < len(parts):
                            st.markdown(parts[i+1].strip(), unsafe_allow_html=True)
                            i += 1
                        try:
                            fig_mix = chart_comp_mix(cd3, peers_only, pt3, all_df=df)
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
                    elif text == 'SOURCES':
                        if i + 1 < len(parts):
                            src_html = parts[i+1].strip()
                            st.markdown(f'<div style="margin-top:1.5rem;padding:1rem;background:#f8f6f3;border:1px solid #e2e0db;border-radius:8px;font-size:0.8rem;color:#64748b;">{src_html}</div>', unsafe_allow_html=True)
                            i += 1
                    i += 1
            
                st.markdown('</div>', unsafe_allow_html=True)
            
                # Show if analysis was regenerated with user context
                if st.session_state.get('lk_user_context'):
                    st.markdown(f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:6px;padding:0.5rem 0.8rem;font-size:0.78rem;color:#92400e;margin:0.5rem 0;">\U0001F504 This analysis was regenerated with additional user-provided context.</div>', unsafe_allow_html=True)
            
                # Context refinement input
                st.markdown('<div style="margin-top:1rem;padding:1rem 1.2rem;background:#fffbeb;border:1px solid #d4a017;border-left:4px solid #b8860b;border-radius:8px;">'
                    '<div style="font-size:0.9rem;font-weight:700;color:#92400e;margin-bottom:0.4rem;">\U0001F4AC Refine this analysis with additional context</div>'
                    '<div style="font-size:0.8rem;color:#475569;margin-bottom:0.5rem;">Add information the AI should consider \u2014 executive accomplishments during the year, important transactions, strategic initiatives, recruiting context, employment agreements. The analysis will be regenerated incorporating your context, with a footnote disclosing what was provided.</div>'
                    '</div>', unsafe_allow_html=True)
                user_context = st.text_area("Additional context", placeholder="e.g., 'The CEO led a $2B portfolio acquisition and expanded into 3 new markets' or 'The CFO negotiated a $500M credit facility at favorable terms'", 
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
            # Step 3: Adaptive market-cap-relative peers (for widening thin positions)
            # Built per-position below, not pre-computed
            MIN_PEERS = 4 if not is_proxy_mode else 3
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
                        widen_desc = f"Widened to <strong>{n_pt} {pd2 if pd2 else 'NEO'}s across {pt_pos_peers['ticker'].nunique()} {pt3} companies</strong> (only {n_narrow} in proxy peer group)."
                    else:
                        # Step 3 — adaptive market-cap-relative peers
                        wide_ps_3, _, _ = build_mcap_wide_peers(df, stk3, cd3, pos, MIN_PEERS)
                        all_pos_peers = wide_ps_3[wide_ps_3['position']==pos]
                        n_all = len(all_pos_peers[all_pos_peers['total_comp'].notna()])
                        if n_all >= MIN_PEERS:
                            peers = all_pos_peers
                            widened = True
                            widen_desc = f"Widened to <strong>{n_all} {pd2 if pd2 else 'NEO'}s across {all_pos_peers['ticker'].nunique()} similarly-sized companies</strong> (only {n_narrow} in proxy peers, {n_pt} in {pt3})."
                        else:
                            peers = narrow_peers  # Use what we have
                            if n_narrow > 0:
                                st.markdown(f'<div style="background:#f8f6f3;border:1px solid #d4a017;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.78rem;color:#78350f;margin:0.3rem 0;">\u2139\uFE0F Limited peer data: {n_narrow} {pd2 if pd2 else "NEO"}s available.</div>', unsafe_allow_html=True)
                else:
                    # Custom mode — widen to similarly-sized companies
                    wide_ps_c, _, _ = build_mcap_wide_peers(df, stk3, cd3, pos, MIN_PEERS)
                    all_pos_peers = wide_ps_c[wide_ps_c['position']==pos]
                    n_all = len(all_pos_peers[all_pos_peers['total_comp'].notna()])
                    if n_all >= MIN_PEERS:
                        peers = all_pos_peers
                        widened = True
                        widen_desc = f"Widened to <strong>{n_all} {pd2 if pd2 else 'NEO'}s across {all_pos_peers['ticker'].nunique()} similarly-sized companies</strong> (only {n_narrow} in custom peer group)."
                    else:
                        peers = narrow_peers
                n_pos = len(peers[peers['total_comp'].notna()])
                if widened and widen_desc:
                    st.markdown(f'<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.78rem;color:#92400e;margin:0.3rem 0;">\U0001F504 {widen_desc}</div>', unsafe_allow_html=True)
                cols = st.columns(5)
                for i, (f, l) in enumerate([('base_salary','Base Salary'),('cash_bonus_incentive','Cash Bonus/Incentive'),('stock_based_comp','Non-Cash Equity \u00B9'),('total_comp','Total Compensation')]):
                    v = er[f]; p = percentile_rank(v, peers[f]); med = peers[f].median(); n = len(peers[f].dropna())
                    with cols[i]: st.markdown(render_pct_card(v, p, l, med=med, n=n, is_ext=ie, is_partial=ip), unsafe_allow_html=True)
                # All Other Comp — computed, displayed but NOT benchmarked
                with cols[4]:
                    _oc_sal = er.get('base_salary') or 0 if pd.notna(er.get('base_salary')) else 0
                    _oc_bon = er.get('cash_bonus_incentive') or 0 if pd.notna(er.get('cash_bonus_incentive')) else 0
                    _oc_stk = er.get('stock_based_comp') or 0 if pd.notna(er.get('stock_based_comp')) else 0
                    _oc_tot = er.get('total_comp') or 0 if pd.notna(er.get('total_comp')) else 0
                    _oc_val = max(0, _oc_tot - _oc_sal - _oc_bon - _oc_stk)
                    _oc_color = "#64748b"
                    st.markdown(f'<div style="padding:0.7rem;background:#f8fafc;border-radius:8px;border-left:3px solid {_oc_color};">'
                        f'<div style="font-size:0.68rem;text-transform:uppercase;color:#64748b;">All Other Comp \u00B2</div>'
                        f'<div style="font-size:1.05rem;font-weight:700;color:#0f172a;">{fmt_dollars(_oc_val)}</div>'
                        f'<div style="font-size:0.58rem;color:#94a3b8;margin-top:6px;line-height:1.4;">Includes perquisites, retirement contributions, tax gross-ups, relocation, personal use of aircraft, etc.</div>'
                        f'</div>', unsafe_allow_html=True)
                nk = f"cv_n_{stk3}_{er['position']}_{er['last_name']}_{idx}"
                if nk not in st.session_state: st.session_state[nk] = None
                pos_btn_label = pd2 if pd2 else er['first_name'] + ' ' + er['last_name']
                peer_key = f"show_peers_{stk3}_{pos}_{idx}"
                eb1, eb2, eb_spacer = st.columns([2, 2, 5])
                with eb1:
                    if st.button(f"Generate {pos_btn_label} Analysis", key=f"cv_b_{nk}", use_container_width=True, type="secondary"):
                        with st.spinner("Generating..."):
                            _wide_df = None
                            if widened:
                                _wide_df, _, _ = build_mcap_wide_peers(df, stk3, cd3, pos, MIN_PEERS)
                            st.session_state[nk] = gen_exec(er, peers_only, df, ret_data, peers_only, widened=widened, wide_peers_df=_wide_df)
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

        with tab_board:
            # Reduce spacing between components.html iframes in the board tab
            st.markdown("""<style>
                .stHtml { margin-bottom: -2rem !important; padding-bottom: 0 !important; }
                .stHtml + .stHtml { margin-top: -1.5rem !important; }
                .stMarkdown + .stHtml { margin-top: -1rem !important; }
                .stHtml + .stMarkdown { margin-top: -1.5rem !important; }
                .stHtml + .stHorizontalBlock { margin-top: -1.5rem !important; }
            </style>""", unsafe_allow_html=True)
            
            # Load director comp data
            dir_df = load_director_comp()
            
            if dir_df.empty or stk3 not in dir_df['ticker'].values:
                st.markdown(f"""
                <div style="background:#f8f6f3;border:1px solid #e2e8f0;border-radius:10px;padding:2rem 2.5rem;margin:1rem 0;text-align:center;">
                    <div style="font-size:1.5rem;margin-bottom:0.5rem;">\U0001F3DB\uFE0F</div>
                    <div style="font-size:1.1rem;font-weight:600;color:#1a365d;margin-bottom:0.5rem;">Board of Directors Compensation</div>
                    <div style="font-size:0.9rem;color:#475569;line-height:1.6;max-width:500px;margin:0 auto;">
                        Director compensation data for <strong>{cn3}</strong> is being processed. Check back soon.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                co_dirs = dir_df[dir_df['ticker'] == stk3].copy()
                
                # ============================================================
                # QC RULES — Management Director Validation
                # ============================================================
                # Rule 1: Build set of executive last names from exec_comp for this ticker
                _exec_last_names = set()
                if not df.empty:
                    _tk_execs = df[df['ticker'] == stk3]
                    for _, ex in _tk_execs.iterrows():
                        ln = (ex.get('last_name') or '').strip().lower()
                        if ln:
                            _exec_last_names.add(ln)
                
                # Rule 2: If director is flagged MGMT but their last name is NOT in exec_comp → reclassify as INDEP
                for idx, d in co_dirs.iterrows():
                    if not d.get('is_independent', True):  # is MGMT
                        dir_last = d['director_name'].split()[-1].lower()
                        if dir_last not in _exec_last_names:
                            co_dirs.at[idx, 'is_independent'] = True
                
                # Rule 3: MGMT directors get zero board comp (executives don't receive separate board pay)
                for idx, d in co_dirs.iterrows():
                    if not d.get('is_independent', True):  # is MGMT
                        co_dirs.at[idx, 'fees_earned_cash'] = None
                        co_dirs.at[idx, 'stock_awards'] = None
                        co_dirs.at[idx, 'option_awards'] = None
                        co_dirs.at[idx, 'all_other_comp'] = None
                        co_dirs.at[idx, 'total_comp'] = None
                
                # Rule 4: MGMT directors cannot serve on Audit/Comp/Nom-Gov (enforced in chip rendering below)
                # ============================================================
                
                # Board Snapshot metrics
                n_dirs = len(co_dirs)
                n_independent = int(co_dirs['is_independent'].sum()) if 'is_independent' in co_dirs.columns else 0
                indep_pct = round(n_independent / n_dirs * 100) if n_dirs > 0 else 0
                n_with_comp = int(co_dirs['total_comp'].notna().sum())
                avg_total = co_dirs['total_comp'].dropna().mean()
                median_total = co_dirs['total_comp'].dropna().median()
                avg_cash = co_dirs['fees_earned_cash'].dropna().mean()
                avg_stock = co_dirs['stock_awards'].dropna().mean()
                total_board_comp = co_dirs['total_comp'].dropna().sum()
                
                # Avg age and tenure
                ages = co_dirs['age'].dropna()
                avg_age = int(ages.mean()) if len(ages) > 0 else "—"
                tenures = co_dirs['director_since'].dropna()
                avg_tenure = int(2025 - tenures.mean()) if len(tenures) > 0 else "—"
                
                # Find chair and lead independent
                chair_name = ""
                lead_ind_name = ""
                for _, d in co_dirs.iterrows():
                    if d.get('is_board_chair'): chair_name = d['director_name']
                    if d.get('is_lead_independent'): lead_ind_name = d['director_name']
                
                # Collect unique committees (exclude management directors from independence-required committees)
                _INDEP_ONLY_COMMS = {'Audit', 'Compensation', 'Nominating/Governance'}
                # First pass: count committee members across all directors
                _raw_comm_counts = {}
                for _, d in co_dirs.iterrows():
                    comms = d.get('committees_list', []) if 'committees_list' in d.index else []
                    is_ind = d.get('is_independent', False)
                    for c in comms:
                        if not is_ind and c in _INDEP_ONLY_COMMS:
                            continue
                        _raw_comm_counts[c] = _raw_comm_counts.get(c, 0) + 1
                # Only show committees with 2+ members (filter scraper noise)
                _valid_comms = {c for c, n in _raw_comm_counts.items() if n >= 2}
                all_comms = {c: {'members': n, 'chair': None} for c, n in _raw_comm_counts.items() if c in _valid_comms}
                
                # ---- SECTION 1: BOARD SNAPSHOT (6 metrics) ----
                # Built as HTML string, rendered together with roster below
                snapshot_html = f"""
                <div style="margin:0.5rem 0 0.5rem 0;">
                    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:0.8rem;">
                        <div>
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Board Size</div>
                            <div style="font-size:1.3rem;font-weight:700;color:#1e293b;">{n_dirs}</div>
                        </div>
                        <div>
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Independent</div>
                            <div style="font-size:1.3rem;font-weight:700;color:#1e293b;">{n_independent} of {n_dirs}</div>
                            <div style="font-size:0.7rem;color:#94a3b8;">{indep_pct}%</div>
                        </div>
                        <div>
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Avg Age</div>
                            <div style="font-size:1.3rem;font-weight:700;color:#1e293b;">{avg_age}</div>
                        </div>
                        <div>
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Avg Tenure</div>
                            <div style="font-size:1.3rem;font-weight:700;color:#1e293b;">{avg_tenure} yrs</div>
                        </div>
                        <div>
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Median Total Comp</div>
                            <div style="font-size:1.3rem;font-weight:700;color:#1e293b;">{"${:,.0f}".format(median_total) if pd.notna(median_total) else "—"}</div>
                        </div>
                        <div>
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Committees</div>
                            <div style="font-size:1.3rem;font-weight:700;color:#1e293b;">{len(all_comms)}</div>
                        </div>
                    </div>
                </div>
                <hr style="border:none;border-top:1px solid #e2e8f0;margin:0.8rem 0;">
                <div style="font-size:1rem;font-weight:700;color:#1e293b;margin:0 0 0.5rem 0;font-family:Georgia,serif;">Board of Directors</div>
                """
                
                # ---- SECTION 2: DIRECTOR ROSTER ----
                
                # Build roster rows with committee chips and alternating shading
                roster_rows = []
                agg_cash = 0
                agg_stock = 0
                agg_total = 0
                
                sorted_dirs = co_dirs.sort_values('total_comp', ascending=False, na_position='last')
                for row_idx, (_, d) in enumerate(sorted_dirs.iterrows()):
                    name = d['director_name']
                    age_str = str(int(d['age'])) if pd.notna(d.get('age')) else "—"
                    since_str = str(int(d['director_since'])) if pd.notna(d.get('director_since')) else "—"
                    is_mgmt = not d.get('is_independent', False)
                    
                    # Badge HTML
                    badges = []
                    if is_mgmt:
                        badges.append('<span style="background:#fef3c7;color:#92400e;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:600;">MGMT</span>')
                    else:
                        badges.append('<span style="background:#ecfdf5;color:#065f46;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:600;">INDEP</span>')
                    if d.get('is_lead_independent'):
                        badges.append('<span style="background:#fffbeb;color:#92400e;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:600;">LEAD</span>')
                    if d.get('is_board_chair'):
                        badges.append('<span style="background:#fffbeb;color:#92400e;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:600;">CHAIR</span>')
                    badge_html = " ".join(badges)
                    
                    cash = f"${d['fees_earned_cash']:,.0f}" if pd.notna(d.get('fees_earned_cash')) else "—"
                    stock = f"${d['stock_awards']:,.0f}" if pd.notna(d.get('stock_awards')) else "—"
                    total = f"${d['total_comp']:,.0f}" if pd.notna(d.get('total_comp')) else "—"
                    total_weight = "font-weight:700;" if pd.notna(d.get('total_comp')) else "color:#cbd5e1;"
                    
                    if pd.notna(d.get('fees_earned_cash')): agg_cash += d['fees_earned_cash']
                    if pd.notna(d.get('stock_awards')): agg_stock += d['stock_awards']
                    # Use total_comp if available, otherwise sum components
                    if pd.notna(d.get('total_comp')):
                        agg_total += d['total_comp']
                    else:
                        row_total = sum(v for v in [d.get('fees_earned_cash'), d.get('stock_awards'), d.get('option_awards'), d.get('all_other_comp')] if pd.notna(v))
                        if row_total > 0: agg_total += row_total
                    
                    # Committee chips with ★ for chairs
                    comms = d.get('committees_list', []) if 'committees_list' in d.index else []
                    # Management directors cannot serve on Audit/Comp/Nom-Gov (NYSE/NASDAQ rules)
                    if is_mgmt:
                        comms = [c for c in comms if c not in _INDEP_ONLY_COMMS]
                    # Only show committees with 2+ members (filter scraper noise)
                    comms = [c for c in comms if c in _valid_comms]
                    comm_chips = []
                    for c in comms:
                        abbrev = c.replace("Nominating/Governance", "Nom/Gov").replace("Compensation", "Comp")
                        # TODO: chair detection per committee (need committee_chairs in DB)
                        comm_chips.append(f'<span style="display:inline-block;background:#f1f5f9;color:#475569;font-size:0.65rem;padding:1px 5px;border-radius:3px;margin:1px 2px;">{abbrev}</span>')
                    comm_html = "".join(comm_chips) if comm_chips else '<span style="color:#cbd5e1;">—</span>'
                    
                    # Row background: amber tint for management, alternating for others
                    if is_mgmt:
                        bg = "background:rgba(254,243,199,0.3);"
                    elif row_idx % 2 == 0:
                        bg = "background:white;"
                    else:
                        bg = "background:rgba(248,250,252,0.5);"
                    
                    roster_rows.append(f"""
                    <tr style="border-bottom:1px solid #f1f5f9;{bg}">
                        <td style="padding:7px 10px;"><div style="font-weight:600;color:#1e293b;font-size:0.85rem;">{name}</div></td>
                        <td style="padding:7px 6px;">{badge_html}</td>
                        <td style="padding:7px 6px;text-align:center;color:#64748b;font-size:0.85rem;">{age_str}</td>
                        <td style="padding:7px 6px;text-align:center;color:#64748b;font-size:0.85rem;">{since_str}</td>
                        <td style="padding:7px 8px;">{comm_html}</td>
                        <td style="padding:7px 10px;text-align:right;font-size:0.85rem;color:#334155;">{cash}</td>
                        <td style="padding:7px 10px;text-align:right;font-size:0.85rem;color:#334155;">{stock}</td>
                        <td style="padding:7px 10px;text-align:right;font-size:0.85rem;{total_weight}color:#1e293b;">{total}</td>
                    </tr>""")
                
                # Aggregate footer row
                agg_row = f"""
                <tr style="border-top:2px solid #1e293b;background:#1e293b;">
                    <td style="padding:10px 10px;font-weight:700;color:white;font-size:0.85rem;" colspan="5">Aggregate Board Compensation</td>
                    <td style="padding:10px 10px;text-align:right;font-weight:700;color:white;font-size:0.85rem;">${agg_cash:,.0f}</td>
                    <td style="padding:10px 10px;text-align:right;font-weight:700;color:white;font-size:0.85rem;">${agg_stock:,.0f}</td>
                    <td style="padding:10px 10px;text-align:right;font-weight:800;color:white;font-size:0.9rem;">${agg_total:,.0f}</td>
                </tr>"""
                
                hdr_style = "padding:8px 10px;font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                roster_table_html = f"""
                <div style="overflow-x:auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
                <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
                    <thead>
                        <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
                            <th style="{hdr_style}text-align:left;">Director</th>
                            <th style="{hdr_style}text-align:left;">Role</th>
                            <th style="{hdr_style}text-align:center;">Age</th>
                            <th style="{hdr_style}text-align:center;">Since</th>
                            <th style="{hdr_style}text-align:left;">Committees</th>
                            <th style="{hdr_style}text-align:right;">Cash</th>
                            <th style="{hdr_style}text-align:right;">Equity</th>
                            <th style="{hdr_style}text-align:right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(roster_rows)}
                    </tbody>
                    <tfoot>
                        {agg_row}
                    </tfoot>
                </table>
                </div>
                <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;font-style:italic;">
                    Source: FY{FY_YEAR} DEF 14A proxy filing
                </div>
                """
                roster_table_html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">{snapshot_html}{roster_table_html}</div>"""
                table_height = max(250, 150 + (len(roster_rows) + 1) * 40)
                components.html(roster_table_html, height=table_height, scrolling=True)
                
                # ---- SECTIONS 3+4 COMBINED: COMMITTEE + FEE SCHEDULE ----
                # Single render to eliminate Streamlit iframe gaps
                
                comm_section_html = ""
                if all_comms:
                    top_comms = sorted(all_comms.items(), key=lambda x: x[1]['members'], reverse=True)[:4]
                    n_comm_cols = min(len(top_comms), 4)
                    comm_cards = []
                    for comm_name, comm_data in top_comms:
                        abbrev = comm_name.replace("Nominating/Governance", "Nom/Gov")
                        comm_cards.append(f"""
                        <div style="border:1px solid #e2e8f0;border-radius:8px;padding:1rem;">
                            <div style="font-size:0.85rem;font-weight:700;color:#1e293b;margin-bottom:0.5rem;">{abbrev} Committee</div>
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                <span style="font-size:0.75rem;color:#64748b;">Members</span>
                                <span style="font-size:0.85rem;font-weight:600;color:#334155;">{comm_data['members']}</span>
                            </div>
                        </div>""")
                    grid_cols = f"repeat({n_comm_cols},1fr)"
                    comm_section_html = f"""
                    <div style="font-size:1rem;font-weight:700;color:#1e293b;margin:0 0 0.5rem 0;font-family:Georgia,serif;">Committee Structure</div>
                    <div style="display:grid;grid-template-columns:{grid_cols};gap:0.75rem;margin-bottom:1rem;">
                        {"".join(comm_cards)}
                    </div>"""
                
                # Section 4: Fee Schedule
                _fs_df = load_fee_schedule()
                _co_fs = _fs_df[_fs_df['ticker'] == stk3].iloc[0].to_dict() if not _fs_df.empty and stk3 in _fs_df['ticker'].values else {}
                import math
                for _k, _v in list(_co_fs.items()):
                    if isinstance(_v, float) and (math.isnan(_v) or _v == 0):
                        _co_fs[_k] = None
                    elif isinstance(_v, float):
                        _co_fs[_k] = int(_v)
                
                fee_section_html = ""
                peer_bar_html = ""
                if _co_fs and any(_co_fs.get(k) for k in ['cash_retainer','equity_retainer','total_retainer']):
                    _board_peer_tks = set(proxy_tickers) if proxy_tickers else set()
                    _peer_fs = _fs_df[_fs_df['ticker'].isin(_board_peer_tks)] if _board_peer_tks and not _fs_df.empty else pd.DataFrame()
                    for _col in ['cash_retainer','equity_retainer','total_retainer','lead_director_premium','chair_premium','audit_chair','comp_chair','nomgov_chair']:
                        if _col in _peer_fs.columns:
                            _peer_fs[_col] = pd.to_numeric(_peer_fs[_col], errors='coerce')
                    
                    def _fs_pctl(df, key, val):
                        if df.empty or not val: return ""
                        vals = df[key].dropna()
                        vals = vals[vals > 0]
                        if len(vals) < 2: return ""
                        rank = (vals < val).sum() / len(vals) * 100
                        return f"<span style='font-size:0.7rem;color:#64748b;'>{rank:.0f}%ile</span>"
                    
                    cash_r = _co_fs.get('cash_retainer')
                    eq_r = _co_fs.get('equity_retainer')
                    tot_r = _co_fs.get('total_retainer')
                    lead_p = _co_fs.get('lead_director_premium')
                    chair_p = _co_fs.get('chair_premium')
                    eq_vehicle = _co_fs.get('equity_vehicle', '') or ''
                    eq_vesting = _co_fs.get('equity_vesting', '') or ''
                    
                    # Fallback: derive missing retainers from actual director_comp data
                    # (fee schedule scraper may have missed the dollar amount)
                    _indep_dirs = co_dirs[co_dirs['is_independent'] == True] if not co_dirs.empty else pd.DataFrame()
                    _dirs_with_comp = _indep_dirs[_indep_dirs['total_comp'].notna() & (_indep_dirs['total_comp'] > 0)] if not _indep_dirs.empty else pd.DataFrame()
                    if not eq_r and not _dirs_with_comp.empty:
                        _eq_vals = _dirs_with_comp['stock_awards'].dropna()
                        _eq_vals = _eq_vals[_eq_vals > 0]
                        if len(_eq_vals) >= 2:
                            # Use mode (most common value) since retainers are usually uniform
                            eq_r = int(_eq_vals.mode().iloc[0]) if not _eq_vals.mode().empty else int(_eq_vals.median())
                    if not tot_r and cash_r and eq_r:
                        tot_r = cash_r + eq_r
                    elif not tot_r and not _dirs_with_comp.empty:
                        _tot_vals = _dirs_with_comp['total_comp'].dropna()
                        _tot_vals = _tot_vals[_tot_vals > 0]
                        if len(_tot_vals) >= 2:
                            tot_r = int(_tot_vals.mode().iloc[0]) if not _tot_vals.mode().empty else int(_tot_vals.median())
                    if not cash_r and tot_r and eq_r:
                        cash_r = tot_r - eq_r
                    
                    pct_eq = (eq_r / tot_r * 100) if eq_r and tot_r and tot_r > 0 else 0
                    
                    retainer_html = ""
                    if cash_r:
                        retainer_html += f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Cash Retainer</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${cash_r:,} {_fs_pctl(_peer_fs, "cash_retainer", cash_r)}</span></div>'
                    if eq_r:
                        retainer_html += f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Equity Retainer</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${eq_r:,} {_fs_pctl(_peer_fs, "equity_retainer", eq_r)}</span></div>'
                    if tot_r:
                        retainer_html += f'<div style="border-top:1px solid #e2e8f0;padding-top:6px;margin-top:4px;display:flex;justify-content:space-between;"><span style="font-size:0.85rem;font-weight:600;color:#1e293b;">Total Retainer</span><span style="font-size:0.85rem;font-weight:800;color:#1e293b;">${tot_r:,} {_fs_pctl(_peer_fs, "total_retainer", tot_r)}</span></div>'
                    
                    eq_detail = ""
                    if eq_vehicle or eq_vesting:
                        parts = [p for p in [eq_vehicle, f"{eq_vesting} vest" if eq_vesting else "", f"{pct_eq:.0f}% equity" if pct_eq > 0 else ""] if p]
                        eq_detail = f'<div style="font-size:0.7rem;color:#94a3b8;margin-top:6px;">{"&nbsp;|&nbsp;".join(parts)}</div>'
                    
                    premium_html = ""
                    if lead_p:
                        premium_html += f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Lead Independent Director</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${lead_p:,}</span></div>'
                    if chair_p:
                        premium_html += f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Chair of the Board</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${chair_p:,}</span></div>'
                    
                    comm_chair_html = ""
                    for label, key in [('Audit Chair', 'audit_chair'), ('Compensation Chair', 'comp_chair'), ('Nom/Gov Chair', 'nomgov_chair')]:
                        v = _co_fs.get(key)
                        if v:
                            comm_chair_html += f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">{label}</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${v:,}</span></div>'
                    
                    # Peer stats for committee chairs
                    peer_comm_chair_html = ""
                    if not _peer_fs.empty and len(_peer_fs) >= 2:
                        for label, key in [('Audit Chair', 'audit_chair'), ('Comp Chair', 'comp_chair'), ('Nom/Gov Chair', 'nomgov_chair')]:
                            vals = _peer_fs[key].dropna()
                            vals = vals[vals > 0]
                            if len(vals) >= 2:
                                peer_comm_chair_html += f"""<div style="margin-bottom:4px;">
                                    <div style="font-size:0.8rem;line-height:1.6;">
                                        <span style="font-size:0.75rem;color:#475569;font-weight:600;">{label}:</span>
                                        &nbsp;<span style="color:#94a3b8;">25th</span> <span style="font-weight:600;color:#64748b;">${vals.quantile(0.25):,.0f}</span>
                                        &nbsp;&nbsp;<span style="color:#94a3b8;">Med</span> <span style="font-weight:700;color:#1e293b;">${vals.median():,.0f}</span>
                                        &nbsp;&nbsp;<span style="color:#94a3b8;">75th</span> <span style="font-weight:600;color:#64748b;">${vals.quantile(0.75):,.0f}</span>
                                    </div></div>"""
                    
                    comm_member_html = ""
                    for label, key in [('Audit Member', 'audit_member'), ('Compensation Member', 'comp_member'), ('Nom/Gov Member', 'nomgov_member')]:
                        v = _co_fs.get(key)
                        if v:
                            comm_member_html += f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">{label}</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${v:,}</span></div>'
                    
                    # Peer stats
                    peer_stats_html = ""
                    peer_lead_premium_html = ""
                    if not _peer_fs.empty and len(_peer_fs) >= 2:
                        for label, key in [('Cash Retainer', 'cash_retainer'), ('Equity Retainer', 'equity_retainer'), ('Total Retainer', 'total_retainer')]:
                            vals = _peer_fs[key].dropna()
                            vals = vals[vals > 0]
                            if len(vals) >= 2:
                                peer_stats_html += f"""
                                <div style="margin-bottom:4px;">
                                    <div style="font-size:0.75rem;font-weight:600;color:#1e293b;margin-bottom:4px;border-bottom:1px solid #cbd5e1;padding-bottom:3px;">{label}</div>
                                    <div style="font-size:0.8rem;line-height:1.6;">
                                        <span style="color:#94a3b8;">25th</span> <span style="font-weight:600;color:#64748b;">${vals.quantile(0.25):,.0f}</span>
                                        &nbsp;&nbsp;<span style="color:#94a3b8;">Med</span> <span style="font-weight:700;color:#1e293b;">${vals.median():,.0f}</span>
                                        &nbsp;&nbsp;<span style="color:#94a3b8;">75th</span> <span style="font-weight:600;color:#64748b;">${vals.quantile(0.75):,.0f}</span>
                                    </div>
                                </div>"""
                        # Lead Director Premium — goes into Leadership Premiums box, not peer benchmarks
                        _lead_vals = _peer_fs['lead_director_premium'].dropna()
                        _lead_vals = _lead_vals[_lead_vals > 0]
                        if len(_lead_vals) >= 2:
                            peer_lead_premium_html = f"""<div style="margin-bottom:4px;">
                                    <div style="font-size:0.8rem;line-height:1.6;">
                                        <span style="font-size:0.75rem;color:#475569;font-weight:600;">Lead Director:</span>
                                        &nbsp;<span style="color:#94a3b8;">25th</span> <span style="font-weight:600;color:#64748b;">${_lead_vals.quantile(0.25):,.0f}</span>
                                        &nbsp;&nbsp;<span style="color:#94a3b8;">Med</span> <span style="font-weight:700;color:#1e293b;">${_lead_vals.median():,.0f}</span>
                                        &nbsp;&nbsp;<span style="color:#94a3b8;">75th</span> <span style="font-weight:600;color:#64748b;">${_lead_vals.quantile(0.75):,.0f}</span>
                                    </div></div>"""
                    
                    # Right panel — company's own premiums and committee retainers only
                    # (peer benchmarks go in the peer benchmarks box below)
                    right_content = ""
                    if premium_html:
                        right_content += f'<div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.8rem;">Leadership Premiums</div>{premium_html}'
                    if comm_chair_html:
                        sep = "0.8rem" if premium_html else "0"
                        right_content += f'<div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin:{sep} 0 0.6rem 0;">Committee Chair Retainers</div>{comm_chair_html}'
                    if comm_member_html:
                        right_content += f'<div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin:0.8rem 0 0.6rem 0;">Committee Member Retainers</div>{comm_member_html}'
                    
                    if right_content:
                        right_panel = f'<div style="border:1px solid #e2e8f0;border-radius:8px;padding:1rem;">{right_content}</div>'
                    else:
                        right_panel = f"""<div style="border:1px solid #e2e8f0;border-radius:8px;padding:1rem;">
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.8rem;">Board Summary</div>
                            <div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Directors with Comp</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">{n_with_comp} of {n_dirs}</span></div>
                            <div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Aggregate Board Cost</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${agg_total:,.0f}</span></div>
                        </div>"""
                    
                    # Peer bar with footnote
                    if peer_stats_html:
                        _peers_with_data = _peer_fs[_peer_fs['total_retainer'].notna() & (_peer_fs['total_retainer'] > 0)]['ticker'].tolist() if not _peer_fs.empty else []
                        _peers_with = sorted(_peers_with_data)
                        _peers_without = sorted(_board_peer_tks - set(_peers_with))
                        fn_parts = []
                        if _peers_with:
                            fn_parts.append("Included: " + ", ".join(_peers_with))
                        if _peers_without:
                            fn_parts.append("No fee data: " + ", ".join(_peers_without))
                        footnote = '<div style="font-size:0.65rem;color:#94a3b8;margin-top:8px;font-style:italic;">Proxy peer group: ' + " &nbsp;|&nbsp; ".join(fn_parts) + '. Use Custom Peer Group to add comparison companies.</div>'
                        _premiums_combined = peer_lead_premium_html + peer_comm_chair_html
                        _premiums_section = ''
                        if _premiums_combined:
                            _premiums_section = f'<div style="border-top:1px solid #e2e8f0;margin-top:0.8rem;padding-top:0.8rem;"><div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">Premiums</div><div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:0.5rem;">{_premiums_combined}</div></div>'
                        peer_bar_html = f"""
                        <div style="border:1px solid #e2e8f0;border-radius:8px;padding:1rem 1.2rem;margin-top:1rem;">
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.8rem;">Peer Benchmarks ({len(_peers_with)} companies)</div>
                            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:1rem;">
                            {peer_stats_html}
                            </div>
                            {_premiums_section}
                            {footnote}
                        </div>"""
                    
                    fee_section_html = f"""
                    <div style="font-size:1rem;font-weight:700;color:#1e293b;margin:0 0 0.5rem 0;font-family:Georgia,serif;">Director Compensation Program</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
                        <div style="border:1px solid #e2e8f0;border-radius:8px;padding:1rem;">
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.8rem;">Annual Retainers</div>
                            {retainer_html}
                            {eq_detail}
                        </div>
                        {right_panel}
                    </div>
                    {peer_bar_html}
                    """
                
                elif n_with_comp > 0:
                    pct_cash = (avg_cash / avg_total * 100) if avg_total and avg_total > 0 else 0
                    pct_stock = (avg_stock / avg_total * 100) if avg_total and avg_total > 0 else 0
                    chair_row = f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Board Chair</span><span style="font-size:0.85rem;font-weight:600;color:#1e293b;">{chair_name.split()[-1]}</span></div>' if chair_name else ""
                    lead_row = f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Lead Independent</span><span style="font-size:0.85rem;font-weight:600;color:#1e293b;">{lead_ind_name.split()[-1]}</span></div>' if lead_ind_name else ""
                    fee_section_html = f"""
                    <div style="font-size:1rem;font-weight:700;color:#1e293b;margin:0 0 0.5rem 0;font-family:Georgia,serif;">Director Compensation Program</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
                        <div style="border:1px solid #e2e8f0;border-radius:8px;padding:1rem;">
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.8rem;">Annual Retainers (Avg)</div>
                            <div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Cash Retainer</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${avg_cash:,.0f}</span></div>
                            <div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Equity Retainer</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${avg_stock:,.0f}</span></div>
                            <div style="border-top:1px solid #e2e8f0;padding-top:6px;margin-top:4px;display:flex;justify-content:space-between;"><span style="font-size:0.85rem;font-weight:600;color:#1e293b;">Total Retainer</span><span style="font-size:0.85rem;font-weight:800;color:#1e293b;">${avg_total:,.0f}</span></div>
                            <div style="font-size:0.7rem;color:#94a3b8;margin-top:6px;">Cash: {pct_cash:.0f}% &nbsp;|&nbsp; Equity: {pct_stock:.0f}%</div>
                        </div>
                        <div style="border:1px solid #e2e8f0;border-radius:8px;padding:1rem;">
                            <div style="font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.8rem;">Board Summary</div>
                            <div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Directors with Comp</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">{n_with_comp} of {n_dirs}</span></div>
                            <div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.85rem;color:#475569;">Aggregate Board Cost</span><span style="font-size:0.85rem;font-weight:700;color:#1e293b;">${agg_total:,.0f}</span></div>
                            {chair_row}{lead_row}
                        </div>
                    </div>
                    """
                
                # Single combined render for sections 3+4
                _source_note = f'<div style="font-size:0.65rem;color:#94a3b8;margin-top:0.3rem;font-style:italic;">Source: SEC DEF 14A proxy filing | FY{FY_YEAR}</div>'
                combined_34 = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">{comm_section_html}{fee_section_html}{_source_note}</div>"""
                _h34 = 10
                if comm_section_html: _h34 += 85
                if fee_section_html: _h34 += 190
                if _co_fs and any(_co_fs.get(k) for k in ['audit_chair','comp_chair','nomgov_chair']): _h34 += 70
                if _co_fs and any(_co_fs.get(k) for k in ['audit_member','comp_member','nomgov_member']): _h34 += 50
                if peer_bar_html: _h34 += 180
                if peer_comm_chair_html: _h34 += 80
                _h34 += 40  # source note + bottom margin
                components.html(combined_34, height=_h34, scrolling=False)
                
                # ---- SECTION 5: ACTION BUTTONS ----
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    board_ai_btn = st.button("\U0001F4CB Generate Board Compensation Analysis", key="board_ai_btn", use_container_width=True)
                    board_peer_btn = st.button("\U0001F4CA Peer Board Comparison", key="board_peer_btn", use_container_width=True)
                with btn_col2:
                    board_league_btn = st.button("\U0001F3C6 Board Comp League Tables", key="board_league_btn", use_container_width=True)
                    _cik_val = cd3['cik'].iloc[0] if 'cik' in cd3.columns else ""
                    _cik_str = str(_cik_val).zfill(10) if _cik_val else ""
                    _proxy_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={_cik_str}&type=DEF+14A&dateb=&owner=include&count=5"
                    st.link_button("\U0001F4C4 View Proxy Filing", _proxy_url, use_container_width=True)
                
                # ---- Board League Tables handler ----
                if board_league_btn:
                    # Build league table from director_comp across peer group
                    _league_dirs = dir_df.copy()
                    if peer_tickers:
                        _league_dirs = _league_dirs[_league_dirs['ticker'].isin(list(peer_tickers) + [stk3])]
                    else:
                        _league_dirs = _league_dirs[_league_dirs['property_type'] == pt3] if 'property_type' in _league_dirs.columns else _league_dirs
                    
                    if not _league_dirs.empty:
                        # Aggregate by company: avg total director comp
                        _board_agg = _league_dirs[_league_dirs['is_independent'] == True].groupby(['ticker', 'company_name']).agg(
                            n_directors=('director_name', 'count'),
                            avg_comp=('total_comp', 'mean'),
                            median_comp=('total_comp', 'median'),
                            total_board_cost=('total_comp', 'sum'),
                        ).reset_index().dropna(subset=['avg_comp'])
                        _board_agg = _board_agg.sort_values('avg_comp', ascending=False)
                        
                        league_rows = []
                        for rank, (_, row) in enumerate(_board_agg.iterrows(), 1):
                            is_target = row['ticker'] == stk3
                            bg = "background:#fffbeb;font-weight:700;" if is_target else ("background:#f8fafc;" if rank % 2 == 0 else "")
                            marker = " ◄" if is_target else ""
                            league_rows.append(f"""
                            <tr style="border-bottom:1px solid #f1f5f9;{bg}">
                                <td style="padding:6px 10px;font-size:0.8rem;color:#64748b;text-align:center;">{rank}</td>
                                <td style="padding:6px 10px;font-size:0.85rem;font-weight:{'700' if is_target else '500'};color:#1e293b;">{row['company_name']}{marker}</td>
                                <td style="padding:6px 10px;font-size:0.8rem;color:#64748b;text-align:center;">{row['ticker']}</td>
                                <td style="padding:6px 10px;font-size:0.85rem;text-align:center;color:#334155;">{int(row['n_directors'])}</td>
                                <td style="padding:6px 10px;font-size:0.85rem;text-align:right;color:#334155;">${row['avg_comp']:,.0f}</td>
                                <td style="padding:6px 10px;font-size:0.85rem;text-align:right;font-weight:600;color:#1e293b;">${row['total_board_cost']:,.0f}</td>
                            </tr>""")
                        
                        lhdr = "padding:8px 10px;font-size:0.65rem;color:#1e293b;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                        league_html = f"""
                        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
                        <div style="font-size:1rem;font-weight:700;color:#1e293b;margin:0 0 0.5rem 0;font-family:Georgia,serif;">🏆 Board Compensation League Tables</div>
                        <div style="overflow-x:auto;">
                        <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
                            <thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
                                <th style="{lhdr}text-align:center;width:40px;">Rank</th>
                                <th style="{lhdr}text-align:left;">Company</th>
                                <th style="{lhdr}text-align:center;">Ticker</th>
                                <th style="{lhdr}text-align:center;">Indep. Dirs</th>
                                <th style="{lhdr}text-align:right;">Avg Comp</th>
                                <th style="{lhdr}text-align:right;">Total Board Cost</th>
                            </tr></thead>
                            <tbody>{"".join(league_rows)}</tbody>
                        </table>
                        </div>
                        <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;font-style:italic;">Independent directors only | ◄ = selected company</div>
                        </div>"""
                        league_height = max(300, 80 + len(league_rows) * 36)
                        components.html(league_html, height=league_height, scrolling=True)
                    else:
                        st.info("No peer director compensation data available for league table.")
                
                # ---- Peer Board Comparison handler ----
                if board_peer_btn:
                    _peer_dirs = dir_df.copy()
                    if peer_tickers:
                        _peer_dirs = _peer_dirs[_peer_dirs['ticker'].isin(list(peer_tickers) + [stk3])]
                    else:
                        _peer_dirs = _peer_dirs[_peer_dirs['property_type'] == pt3] if 'property_type' in _peer_dirs.columns else _peer_dirs
                    
                    _indep_only = _peer_dirs[_peer_dirs['is_independent'] == True]
                    if not _indep_only.empty:
                        _peer_board_stats = _indep_only.groupby('ticker').agg(
                            board_size=('director_name', 'count'),
                            avg_age=('age', 'mean'),
                            avg_tenure_since=('director_since', 'mean'),
                            avg_comp=('total_comp', 'mean'),
                            total_cost=('total_comp', 'sum'),
                        ).reset_index()
                        _peer_board_stats['avg_tenure'] = 2025 - _peer_board_stats['avg_tenure_since']
                        
                        # Target company stats
                        _target = _peer_board_stats[_peer_board_stats['ticker'] == stk3]
                        _peers = _peer_board_stats[_peer_board_stats['ticker'] != stk3]
                        
                        if not _target.empty and not _peers.empty:
                            t = _target.iloc[0]
                            
                            def pctile_str(val, series):
                                if pd.isna(val) or series.dropna().empty: return "—"
                                rank = (series.dropna() < val).sum() / len(series.dropna()) * 100
                                return f"P{int(rank)}"
                            
                            comp_items = [
                                ("Board Size", f"{int(t['board_size'])}", pctile_str(t['board_size'], _peers['board_size'])),
                                ("Avg Director Age", f"{int(t['avg_age'])}" if pd.notna(t['avg_age']) else "—", pctile_str(t['avg_age'], _peers['avg_age'])),
                                ("Avg Tenure", f"{int(t['avg_tenure'])} yrs" if pd.notna(t['avg_tenure']) else "—", pctile_str(t['avg_tenure'], _peers['avg_tenure'])),
                                ("Avg Director Comp", f"${t['avg_comp']:,.0f}" if pd.notna(t['avg_comp']) else "—", pctile_str(t['avg_comp'], _peers['avg_comp'])),
                                ("Total Board Cost", f"${t['total_cost']:,.0f}" if pd.notna(t['total_cost']) else "—", pctile_str(t['total_cost'], _peers['total_cost'])),
                            ]
                            
                            comp_rows = ""
                            for label, val, pct in comp_items:
                                comp_rows += f"""
                                <tr style="border-bottom:1px solid #f1f5f9;">
                                    <td style="padding:8px 12px;font-size:0.85rem;color:#475569;">{label}</td>
                                    <td style="padding:8px 12px;font-size:0.85rem;font-weight:700;color:#1e293b;text-align:right;">{val}</td>
                                    <td style="padding:8px 12px;font-size:0.8rem;font-weight:600;color:#64748b;text-align:center;">{pct}</td>
                                </tr>"""
                            
                            peer_html = f"""
                            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
                            <div style="font-size:1rem;font-weight:700;color:#1e293b;margin:0 0 0.5rem 0;font-family:Georgia,serif;">📊 {cn3} vs. Peer Boards</div>
                            <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:0.5rem;">{len(_peers)} peer companies | Independent directors only</div>
                            <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
                                <thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
                                    <th style="padding:8px 12px;font-size:0.65rem;color:#64748b;font-weight:600;text-transform:uppercase;text-align:left;">Metric</th>
                                    <th style="padding:8px 12px;font-size:0.65rem;color:#64748b;font-weight:600;text-transform:uppercase;text-align:right;">{stk3}</th>
                                    <th style="padding:8px 12px;font-size:0.65rem;color:#64748b;font-weight:600;text-transform:uppercase;text-align:center;">Percentile</th>
                                </tr></thead>
                                <tbody>{comp_rows}</tbody>
                            </table>
                            </div>"""
                            components.html(peer_html, height=300, scrolling=False)
                        else:
                            st.info("Insufficient peer data for board comparison.")
                    else:
                        st.info("No independent director data available for peer comparison.")
                
                # ---- SECTION 6: AI BOARD ANALYSIS ----
                if board_ai_btn:
                    with st.spinner("Generating board compensation analysis..."):
                        # Build comprehensive board context for AI
                        _ai_dirs_info = []
                        for _, d in co_dirs.iterrows():
                            comms = []
                            try:
                                import json as _json2
                                raw = d.get('committees')
                                if isinstance(raw, str) and raw.startswith('['):
                                    comms = _json2.loads(raw)
                                elif isinstance(raw, list):
                                    comms = raw
                            except Exception:
                                pass
                            _ai_dirs_info.append({
                                'name': d['director_name'],
                                'age': int(d['age']) if pd.notna(d.get('age')) else None,
                                'since': int(d['director_since']) if pd.notna(d.get('director_since')) else None,
                                'independent': bool(d.get('is_independent', False)),
                                'is_chair': bool(d.get('is_board_chair', False)),
                                'is_lead': bool(d.get('is_lead_independent', False)),
                                'cash': d.get('fees_earned_cash') if pd.notna(d.get('fees_earned_cash')) else None,
                                'equity': d.get('stock_awards') if pd.notna(d.get('stock_awards')) else None,
                                'options': d.get('option_awards') if pd.notna(d.get('option_awards')) else None,
                                'total': d.get('total_comp') if pd.notna(d.get('total_comp')) else None,
                                'committees': comms,
                                'departed': bool(d.get('is_departed', False)),
                            })
                        
                        # Build peer board comparison data
                        peer_board_lines = []
                        _peer_tickers = []
                        if not dir_df.empty:
                            # Get peer tickers from the same peer set used in exec tab
                            try:
                                _pg = load_proxy_peers()
                                _co_peers = _pg[_pg['ticker'] == stk3]
                                _peer_tickers = _co_peers[_co_peers['peer_ticker'].notna()]['peer_ticker'].unique().tolist()
                            except Exception:
                                pass
                            if not _peer_tickers:
                                # Fall back to same property type
                                _peer_tickers = dir_df[(dir_df['property_type'] == pt3) & (dir_df['ticker'] != stk3)]['ticker'].unique().tolist()
                            
                            for ptk in _peer_tickers[:15]:
                                pd_dirs = dir_df[dir_df['ticker'] == ptk]
                                if pd_dirs.empty:
                                    continue
                                pd_indep = pd_dirs[pd_dirs['is_independent'] == True]
                                pd_with_comp = pd_indep[pd_indep['total_comp'] > 0]
                                pd_n = len(pd_dirs)
                                pd_n_indep = len(pd_indep)
                                pd_med = pd_with_comp['total_comp'].median() if not pd_with_comp.empty else 0
                                pd_agg = pd_with_comp['total_comp'].sum() if not pd_with_comp.empty else 0
                                pd_cash_med = pd_with_comp['fees_earned_cash'].median() if not pd_with_comp.empty and 'fees_earned_cash' in pd_with_comp.columns else 0
                                pd_equity_med = pd_with_comp['stock_awards'].median() if not pd_with_comp.empty and 'stock_awards' in pd_with_comp.columns else 0
                                # Chair/Lead premiums
                                pd_chair = pd_dirs[pd_dirs['is_board_chair'] == True]
                                pd_chair_comp = pd_chair['total_comp'].iloc[0] if not pd_chair.empty and pd.notna(pd_chair['total_comp'].iloc[0]) else None
                                pd_lead = pd_dirs[pd_dirs['is_lead_independent'] == True]
                                pd_lead_comp = pd_lead['total_comp'].iloc[0] if not pd_lead.empty and pd.notna(pd_lead['total_comp'].iloc[0]) else None
                                # Committees
                                pd_comms = set()
                                for _, pdd in pd_dirs.iterrows():
                                    try:
                                        raw = pdd.get('committees')
                                        if isinstance(raw, str) and raw.startswith('['):
                                            pd_comms.update(_json2.loads(raw))
                                        elif isinstance(raw, list):
                                            pd_comms.update(raw)
                                    except Exception:
                                        pass
                                
                                line = f"  {ptk}: {pd_n} dirs, {pd_n_indep} indep, med=${pd_med:,.0f}, cash=${pd_cash_med:,.0f}, equity=${pd_equity_med:,.0f}, agg=${pd_agg:,.0f}"
                                if pd_chair_comp: line += f", chair=${pd_chair_comp:,.0f}"
                                if pd_lead_comp: line += f", lead=${pd_lead_comp:,.0f}"
                                line += f", {len(pd_comms)} comms"
                                peer_board_lines.append(line)
                        
                        peer_board_str = chr(10).join(peer_board_lines) if peer_board_lines else "  No peer board data available"
                        n_peer_boards = len(peer_board_lines)
                        
                        # Calculate key differentials for the prompt
                        # Chair premium
                        chair_dir = next((d for d in _ai_dirs_info if d['is_chair']), None)
                        lead_dir = next((d for d in _ai_dirs_info if d['is_lead']), None)
                        indep_dirs = [d for d in _ai_dirs_info if d['independent'] and not d['is_chair'] and not d['is_lead'] and d.get('total')]
                        reg_med = np.median([d['total'] for d in indep_dirs]) if indep_dirs else None
                        
                        chair_premium = ""
                        if chair_dir and chair_dir.get('total') and reg_med:
                            premium = chair_dir['total'] - reg_med
                            chair_premium = f"\nChair Premium: ${premium:,.0f} above regular member median (${chair_dir['total']:,.0f} vs ${reg_med:,.0f})"
                        lead_premium = ""
                        if lead_dir and lead_dir.get('total') and reg_med:
                            premium = lead_dir['total'] - reg_med
                            lead_premium = f"\nLead Independent Premium: ${premium:,.0f} above regular member median (${lead_dir['total']:,.0f} vs ${reg_med:,.0f})"
                        
                        # Cash/equity split
                        cash_vals = [d['cash'] for d in _ai_dirs_info if d.get('cash') and d['independent']]
                        equity_vals = [d['equity'] for d in _ai_dirs_info if d.get('equity') and d['independent']]
                        avg_cash = np.mean(cash_vals) if cash_vals else 0
                        avg_equity = np.mean(equity_vals) if equity_vals else 0
                        total_mix = avg_cash + avg_equity
                        mix_str = f"Cash/Equity Mix: {avg_cash/total_mix*100:.0f}% cash / {avg_equity/total_mix*100:.0f}% equity" if total_mix > 0 else ""
                        
                        # Fetch enrichment data (same sources as exec analysis)
                        _cik = co_d['cik'].iloc[0] if 'cik' in co_d.columns else None
                        _say_on_pay = fetch_say_on_pay(cn3, _cik, FY_YEAR + 1) if _cik else None
                        _inst_owners = fetch_institutional_ownership(cn3, _cik, FY_YEAR) if _cik else None
                        _proxy_alerts = fetch_proxy_advisory_alerts(cn3, _cik, FY_YEAR + 1) if _cik else None
                        
                        board_enrichment = ""
                        board_sources = [f"DEF 14A Proxy Statement, FY{FY_YEAR}, SEC EDGAR"]
                        
                        if _say_on_pay:
                            board_enrichment += f"\n\nSAY-ON-PAY VOTE: {_say_on_pay['approval_pct']}% approval ({_say_on_pay['votes_for']:,} For / {_say_on_pay['votes_against']:,} Against)"
                            if _say_on_pay['approval_pct'] < 70:
                                board_enrichment += " ⚠ LOW APPROVAL"
                            board_sources.append(f"8-K Voting Results (Item 5.07), SEC EDGAR")
                        
                        if _proxy_alerts:
                            board_enrichment += "\n\nPROXY ADVISORY ALERTS:"
                            for alert in _proxy_alerts[:3]:
                                advisory = []
                                if alert.get('has_iss'): advisory.append('ISS')
                                if alert.get('has_glass_lewis'): advisory.append('Glass Lewis')
                                adv_str = ' & '.join(advisory) if advisory else 'Advisory'
                                board_enrichment += f"\n  [{alert['date']}] {adv_str}: {'AGAINST' if alert.get('against') else 'noted'}"
                            board_sources.append("DEFA14A Supplemental Proxy filings, SEC EDGAR")
                        
                        if _inst_owners:
                            board_enrichment += "\n\nINSTITUTIONAL OWNERSHIP:"
                            for o in _inst_owners[:5]:
                                board_enrichment += f"\n  {o['institution']}: {o['pct']}%"
                            board_sources.append("Beneficial Ownership disclosure from DEF 14A, SEC EDGAR")
                        
                        board_sources.append(f"Velarion peer director compensation database ({n_peer_boards} peer companies)")
                        sources_footnote = chr(10).join(f"  {i+1}. {s}" for i, s in enumerate(board_sources))
                        
                        _ai_context = f"""Company: {cn3} ({stk3}) | {pt3} | Mkt Cap ${co_d['market_cap'].iloc[0]/1e9:.2f}B

BOARD COMPOSITION:
  Board Size: {n_dirs} directors | Independent: {n_independent} ({indep_pct}%)
  Avg Age: {avg_age} | Avg Tenure: {avg_tenure} yrs
  Committees: {len(all_comms)} ({', '.join(sorted(all_comms))})
  Chair: {chair_name or "N/A"} | Lead Independent: {lead_ind_name or "N/A"}

COMPENSATION PROGRAM:
  Median Independent Director Comp: {"${:,.0f}".format(median_total) if pd.notna(median_total) else "N/A"}
  Aggregate Board Cost (all directors): ${agg_total:,.0f}
  {mix_str}{chair_premium}{lead_premium}

INDIVIDUAL DIRECTORS:
"""
                        for di in _ai_dirs_info:
                            role = "INDEP" if di['independent'] else "MGMT"
                            if di['is_chair']: role += " CHAIR"
                            if di['is_lead']: role += " LEAD"
                            if di['departed']: role += " [DEPARTED]"
                            comms_str = f" | Committees: {', '.join(di['committees'])}" if di['committees'] else ""
                            cash_str = f"cash=${di['cash']:,.0f}" if di.get('cash') else "cash=N/A"
                            eq_str = f"equity=${di['equity']:,.0f}" if di.get('equity') else "equity=N/A"
                            _ai_context += f"  {di['name']}: {role} | age={di['age']}, since={di['since']} | {cash_str}, {eq_str}, total=${di['total']:,.0f}{comms_str}\n" if di.get('total') else f"  {di['name']}: {role} | age={di['age']}, since={di['since']} | no comp data{comms_str}\n"
                        
                        _ai_context += f"""
PEER BOARD BENCHMARKING ({n_peer_boards} companies):
{peer_board_str}
{board_enrichment}
"""
                        
                        try:
                            import anthropic
                            client = anthropic.Anthropic()
                            _board_prompt = f"""You are a senior board compensation consultant (like Ferguson Partners or Pearl Meyer) preparing a confidential benchmarking analysis for a compensation committee. This should match the depth and rigor of a professional consulting engagement.

{_ai_context}

CRITICAL FORMAT INSTRUCTIONS: Include these section markers on their own line before each section.

[SECTION:COMPOSITION]
<h4>Board Composition & Governance</h4>
Board size vs peer median, independence ratio vs peers, average age and tenure, committee structure. If any director has tenure >15 years, note potential entrenchment concern. If average age >70 or <55, note the outlier. If independence ratio <67%, flag it. Compare number of committees to peer median. (3-4 sentences)

[SECTION:PROGRAM]
<h4>Director Compensation Program</h4>
Median director comp vs peer group (percentile, % above/below). Cash/equity mix vs peer median mix — is the company more cash-heavy or equity-heavy? Board Chair premium vs peer chair premiums. Lead Independent Director premium vs peers. Comment on whether compensation structure incentivizes alignment with shareholders (higher equity = better alignment). Aggregate board cost vs peer aggregate. (4-5 sentences)

[SECTION:PREMIUMS]
<h4>Committee & Leadership Premiums</h4>
Analyze committee chair premiums if detectable from the data (Audit chairs typically command the highest premium, followed by Comp, then Nom/Gov). Compare leadership premiums (Chair, Lead Independent) to peer companies. If a director serves on 3+ committees, note the workload premium question. If any director's comp is significantly above or below the median, explain why (leadership role, committee load, partial year). (3-4 sentences)

[SECTION:WATCH]
<h4>Board Considerations</h4>
Based on the data: flag 2-3 items the comp committee should be prepared to address. Examples: say-on-pay concerns, ISS/Glass Lewis attention, board refreshment needs (age/tenure concentration), comp competitiveness vs peers (risk of director attrition if below market), governance optics if above market. If institutional ownership data is available, note implications for proxy voting. Frame as "the committee should be prepared to discuss..." (2-3 sentences)

[SECTION:SOURCES]
<h4>Sources</h4>
{sources_footnote}

No markdown (no asterisks, bold, headers, bullets). Plain flowing paragraphs only. No title above the first section. Write in a professional, consulting-report tone — confident, data-driven, with specific numbers throughout. Reference peer comparisons frequently.

CRITICAL: Only use data explicitly provided above. Do not invent numbers, meeting counts, or fee schedules not shown in the data."""
                            
                            response = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=2000,
                                messages=[{"role": "user", "content": _board_prompt}]
                            )
                            analysis_text = clean_ai(response.content[0].text)
                            
                            # Parse sections and render with styled formatting
                            import re as _re2
                            section_pattern = r'\[SECTION:(COMPOSITION|PROGRAM|PREMIUMS|WATCH|SOURCES)\]'
                            parts = _re2.split(section_pattern, analysis_text)
                            
                            st.markdown(f'<div style="border-left:5px solid #b8860b;background:linear-gradient(135deg,#fffbeb 0%,#fef3c7 100%);border:1px solid #f59e0b33;border-radius:8px;padding:1.5rem;margin:1rem 0;">', unsafe_allow_html=True)
                            st.markdown(f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#92400e;font-weight:700;margin-bottom:0.75rem;">\U0001F4CB Board Compensation Analysis \u2014 {cn3}</div>', unsafe_allow_html=True)
                            
                            idx = 0
                            while idx < len(parts):
                                text = parts[idx].strip()
                                if text and text not in ('COMPOSITION', 'PROGRAM', 'PREMIUMS', 'WATCH', 'SOURCES'):
                                    st.markdown(f'<div style="font-size:0.88rem;color:#334155;line-height:1.7;">{text}</div>', unsafe_allow_html=True)
                                elif text == 'SOURCES':
                                    if idx + 1 < len(parts):
                                        src_html = parts[idx+1].strip()
                                        st.markdown(f'<div style="margin-top:1rem;padding:0.8rem;background:#f8f6f3;border:1px solid #e2e0db;border-radius:6px;font-size:0.78rem;color:#64748b;">{src_html}</div>', unsafe_allow_html=True)
                                        idx += 1
                                elif text in ('COMPOSITION', 'PROGRAM', 'PREMIUMS', 'WATCH'):
                                    if idx + 1 < len(parts):
                                        st.markdown(f'<div style="font-size:0.88rem;color:#334155;line-height:1.7;">{parts[idx+1].strip()}</div>', unsafe_allow_html=True)
                                        idx += 1
                                idx += 1
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"AI analysis error: {str(e)[:200]}")

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
