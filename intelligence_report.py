#!/usr/bin/env python3
"""
Velarion Intelligence Report Generator
========================================
Produces comprehensive company intelligence reports combining:
- Executive compensation analysis with peer benchmarking
- Board compensation & governance assessment
- Pay-for-performance alignment
- Macro/sector context (via AI with web search capability)
- Talent risk assessment
- Peer group evaluation
- Strategic recommendations

Usage (standalone):
    python intelligence_report.py HHH
    python intelligence_report.py HHH --format markdown
    python intelligence_report.py HHH --format docx

Usage (from dashboard):
    from intelligence_report import generate_report
    report = generate_report("HHH")
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ============================================================
# CONFIG
# ============================================================
SUPABASE_URL = "https://fhnffpgotkxxtwmwbizy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZobmZmcGdvdGt4eHR3bXdiaXp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEwNzAzNTEsImV4cCI6MjA4NjY0NjM1MX0.XU80VORX49loeJlbrq0w9hiGOUAN7fgEH6FPiF1E-GU"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

FY_YEAR = 2024
REPORT_DATE = datetime.now().strftime("%B %d, %Y")

POSITION_ORDER = {'CEO': 0, 'President': 1, 'CFO': 2, 'COO': 3, 'CIO': 4,
                  'General Counsel': 5, 'CAO': 6, 'CHRO': 7, 'EVP': 8, 'SVP': 9}


# ============================================================
# DATA HELPERS
# ============================================================
def sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    })
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def fmt_d(v):
    """Format dollar value."""
    if v is None or v == 0:
        return "—"
    return f"${v:,.0f}"


def fmt_pct(v):
    """Format percentage."""
    if v is None:
        return "N/A"
    return f"{v:.1f}%"


def percentile_rank(value, series):
    """Calculate percentile rank of value within series."""
    if value is None or len(series) == 0:
        return None
    below = sum(1 for x in series if x < value)
    equal = sum(1 for x in series if x == value)
    return round((below + equal * 0.5) / len(series) * 100)


def ordinal(n):
    if n is None:
        return "N/A"
    n = int(n)
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ============================================================
# DATA ASSEMBLY
# ============================================================
def assemble_data(ticker: str) -> Dict:
    """
    Pull all available data for a company into a structured payload.
    Returns a dict with all data needed for the Intelligence Report.
    """
    data = {"ticker": ticker, "assembled_at": REPORT_DATE}

    # ── 1. EXECUTIVE COMPENSATION ──
    execs = sb_get(f"exec_comp?select=*&ticker=eq.{ticker}&order=total_comp.desc")
    if not execs:
        return None
    data["company_name"] = execs[0].get("company_name", ticker)
    data["property_type"] = execs[0].get("property_type", "")
    data["hq"] = f"{execs[0].get('hq_city', '')}, {execs[0].get('hq_state', '')}"
    data["market_cap"] = execs[0].get("market_cap")
    data["cik"] = execs[0].get("cik")
    data["fiscal_year"] = FY_YEAR

    # Sort by position
    execs.sort(key=lambda x: POSITION_ORDER.get(x.get('position', ''), 99))
    data["executives"] = []
    for e in execs:
        data["executives"].append({
            "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
            "position": e.get("position", ""),
            "base_salary": e.get("base_salary"),
            "cash_bonus": e.get("cash_bonus_incentive"),
            "stock_comp": e.get("stock_based_comp"),
            "other_comp": e.get("other_comp"),
            "total_comp": e.get("total_comp"),
        })

    # ── 2. PROXY PEER GROUP ──
    peers_raw = sb_get(f"proxy_peer_groups?select=peer_name_as_disclosed,peer_ticker,in_universe&ticker=eq.{ticker}")
    data["proxy_peers"] = []
    peer_tickers = []
    for p in peers_raw:
        pt = p.get("peer_ticker")
        if pt:
            peer_tickers.append(pt)
        data["proxy_peers"].append({
            "name": p.get("peer_name_as_disclosed", ""),
            "ticker": pt,
            "in_universe": p.get("in_universe", False),
        })

    # ── 3. PEER EXECUTIVE COMP (for benchmarking) ──
    if peer_tickers:
        tk_list = ",".join(f"eq.{t}" for t in peer_tickers)
        # Use or() filter for multiple tickers
        peer_filter = f"ticker=in.({','.join(peer_tickers)})"
        peer_execs = sb_get(f"exec_comp?select=ticker,company_name,position,total_comp,base_salary,cash_bonus_incentive,stock_based_comp&{peer_filter}&order=ticker")
    else:
        peer_execs = []
    data["peer_execs"] = peer_execs

    # Compute peer percentiles for each executive
    for exec_data in data["executives"]:
        pos = exec_data["position"]
        peer_totals = [pe.get("total_comp") for pe in peer_execs if pe.get("position") == pos and pe.get("total_comp")]
        peer_salaries = [pe.get("base_salary") for pe in peer_execs if pe.get("position") == pos and pe.get("base_salary")]
        peer_bonuses = [pe.get("cash_bonus_incentive") for pe in peer_execs if pe.get("position") == pos and pe.get("cash_bonus_incentive")]
        peer_stocks = [pe.get("stock_based_comp") for pe in peer_execs if pe.get("position") == pos and pe.get("stock_based_comp")]

        exec_data["peer_count"] = len(peer_totals)
        exec_data["total_pctile"] = percentile_rank(exec_data["total_comp"], peer_totals)
        exec_data["salary_pctile"] = percentile_rank(exec_data["base_salary"], peer_salaries)
        exec_data["bonus_pctile"] = percentile_rank(exec_data["cash_bonus"], peer_bonuses)
        exec_data["stock_pctile"] = percentile_rank(exec_data["stock_comp"], peer_stocks)

        if peer_totals:
            exec_data["peer_total_median"] = sorted(peer_totals)[len(peer_totals) // 2]
            exec_data["peer_total_25th"] = sorted(peer_totals)[len(peer_totals) // 4]
            exec_data["peer_total_75th"] = sorted(peer_totals)[3 * len(peer_totals) // 4]
        else:
            exec_data["peer_total_median"] = None
            exec_data["peer_total_25th"] = None
            exec_data["peer_total_75th"] = None

        # Comp mix
        total = exec_data["total_comp"] or 0
        if total > 0:
            exec_data["pct_salary"] = round((exec_data["base_salary"] or 0) / total * 100)
            exec_data["pct_bonus"] = round((exec_data["cash_bonus"] or 0) / total * 100)
            exec_data["pct_equity"] = round((exec_data["stock_comp"] or 0) / total * 100)
        else:
            exec_data["pct_salary"] = exec_data["pct_bonus"] = exec_data["pct_equity"] = 0

    # ── 4. BOARD / DIRECTOR COMPENSATION ──
    directors = sb_get(f"director_comp?select=*&ticker=eq.{ticker}&is_departed=is.false&order=total_comp.desc")
    data["directors"] = []
    for d in directors:
        comms = d.get("committees") or []
        if isinstance(comms, str):
            try:
                comms = json.loads(comms)
            except:
                comms = []
        data["directors"].append({
            "name": d.get("director_name", ""),
            "is_independent": d.get("is_independent", False),
            "is_board_chair": d.get("is_board_chair", False),
            "is_lead_independent": d.get("is_lead_independent", False),
            "is_not_standing": d.get("is_not_standing", False),
            "is_newly_elected": d.get("is_newly_elected", False),
            "age": d.get("age"),
            "since": d.get("director_since"),
            "committees": comms,
            "cash": d.get("fees_earned_cash"),
            "equity": d.get("stock_awards"),
            "total": d.get("total_comp"),
        })

    # ── 5. FEE SCHEDULE ──
    fee_sched = sb_get(f"director_fee_schedule?select=*&ticker=eq.{ticker}")
    data["fee_schedule"] = fee_sched[0] if fee_sched else {}

    # Peer fee schedules
    if peer_tickers:
        peer_fees = sb_get(f"director_fee_schedule?select=*&ticker=in.({','.join(peer_tickers)})")
    else:
        peer_fees = []
    data["peer_fee_schedules"] = peer_fees

    # ── 6. STOCK RETURNS ──
    try:
        import yfinance as yf

        company_stock = yf.Ticker(ticker)
        hist = company_stock.history(period="3y")
        sp500 = yf.Ticker("^GSPC").history(period="3y")

        def compute_returns(hist_df):
            if hist_df.empty:
                return {}
            now = hist_df['Close'].iloc[-1]
            ytd_start = hist_df[hist_df.index >= f"{datetime.now().year}-01-01"]
            r = {}
            if len(ytd_start) > 1:
                r["ytd"] = (now / ytd_start['Close'].iloc[0] - 1) * 100
            if len(hist_df) >= 252:
                r["1yr"] = (now / hist_df['Close'].iloc[-252] - 1) * 100
            if len(hist_df) >= 756:
                r["3yr"] = (now / hist_df['Close'].iloc[-756] - 1) * 100
            r["current_price"] = now
            return r

        data["stock_returns"] = compute_returns(hist)
        data["sp500_returns"] = compute_returns(sp500)

        # Peer returns
        peer_returns = {}
        for pt in peer_tickers[:15]:  # Limit to avoid rate limits
            try:
                ph = yf.Ticker(pt).history(period="1y")
                if not ph.empty:
                    now = ph['Close'].iloc[-1]
                    if len(ph) >= 252:
                        peer_returns[pt] = (now / ph['Close'].iloc[-252] - 1) * 100
            except:
                continue
        data["peer_returns"] = peer_returns

    except Exception as e:
        data["stock_returns"] = {}
        data["sp500_returns"] = {}
        data["peer_returns"] = {}

    # ── 7. GOVERNANCE METRICS ──
    current_board = [d for d in data["directors"] if not d["is_not_standing"]]
    comp_board = [d for d in data["directors"] if not d["is_newly_elected"]]

    data["governance"] = {
        "board_size": len(current_board),
        "independent": sum(1 for d in current_board if d["is_independent"]),
        "pct_independent": round(sum(1 for d in current_board if d["is_independent"]) / max(len(current_board), 1) * 100),
        "avg_tenure": round(sum(datetime.now().year - (d["since"] or datetime.now().year) for d in current_board if d["since"]) / max(sum(1 for d in current_board if d["since"]), 1), 1),
        "avg_age": round(sum(d["age"] for d in current_board if d["age"]) / max(sum(1 for d in current_board if d["age"]), 1)),
        "newly_elected": sum(1 for d in data["directors"] if d["is_newly_elected"]),
        "not_standing": sum(1 for d in data["directors"] if d["is_not_standing"]),
        "committees": list(set(
            re.sub(r'\s*\(Chair\)', '', c).strip()
            for d in current_board
            for c in d["committees"]
            if c
        )),
        "aggregate_board_comp": sum(d["total"] or 0 for d in comp_board),
    }

    return data


# ============================================================
# PROMPT CONSTRUCTION
# ============================================================
def build_data_payload(data: Dict) -> str:
    """Convert assembled data into a structured text payload for the AI prompt."""
    lines = []

    # Company profile
    lines.append(f"COMPANY: {data['company_name']} ({data['ticker']})")
    lines.append(f"Sector/Property Type: {data['property_type']}")
    lines.append(f"Headquarters: {data['hq']}")
    mcap = data.get('market_cap')
    lines.append(f"Market Cap: ${mcap/1e9:.2f}B" if mcap else "Market Cap: N/A")
    lines.append(f"Fiscal Year: {data['fiscal_year']}")
    lines.append("")

    # Executive comp
    lines.append("═══ EXECUTIVE COMPENSATION ═══")
    for e in data["executives"]:
        total = e['total_comp'] or 0
        pctile = f"{ordinal(e['total_pctile'])} pctile" if e['total_pctile'] is not None else "N/A"
        med = fmt_d(e['peer_total_median'])
        lines.append(f"  {e['name']}, {e['position']}: Total {fmt_d(total)} ({pctile} vs {e['peer_count']} peers, median {med})")
        lines.append(f"    Salary {fmt_d(e['base_salary'])} ({ordinal(e['salary_pctile'])}) | Bonus {fmt_d(e['cash_bonus'])} ({ordinal(e['bonus_pctile'])}) | Equity {fmt_d(e['stock_comp'])} ({ordinal(e['stock_pctile'])})")
        lines.append(f"    Mix: {e['pct_salary']}% salary / {e['pct_bonus']}% bonus / {e['pct_equity']}% equity")
    lines.append("")

    # Stock returns
    sr = data.get("stock_returns", {})
    sp = data.get("sp500_returns", {})
    pr = data.get("peer_returns", {})
    lines.append("═══ STOCK PERFORMANCE ═══")
    lines.append(f"  {data['ticker']}: YTD {fmt_pct(sr.get('ytd'))} | 1-Year {fmt_pct(sr.get('1yr'))} | 3-Year {fmt_pct(sr.get('3yr'))}")
    lines.append(f"  S&P 500: YTD {fmt_pct(sp.get('ytd'))} | 1-Year {fmt_pct(sp.get('1yr'))} | 3-Year {fmt_pct(sp.get('3yr'))}")
    if pr:
        peer_1yr = [v for v in pr.values() if v is not None]
        if peer_1yr:
            peer_med = sorted(peer_1yr)[len(peer_1yr) // 2]
            lines.append(f"  Peer Median 1-Year Return: {fmt_pct(peer_med)} ({len(peer_1yr)} peers)")
            co_1yr = sr.get('1yr')
            if co_1yr is not None:
                alpha = co_1yr - peer_med
                lines.append(f"  Alpha vs Peers: {'+' if alpha >= 0 else ''}{fmt_pct(alpha)}")
    lines.append("")

    # Board composition
    gov = data.get("governance", {})
    lines.append("═══ BOARD COMPOSITION & GOVERNANCE ═══")
    lines.append(f"  Board Size: {gov.get('board_size', 0)} | Independent: {gov.get('independent', 0)} ({gov.get('pct_independent', 0)}%)")
    lines.append(f"  Avg Tenure: {gov.get('avg_tenure', 0)} yrs | Avg Age: {gov.get('avg_age', 0)}")
    lines.append(f"  Committees: {', '.join(gov.get('committees', []))}")
    lines.append(f"  Newly Elected: {gov.get('newly_elected', 0)} | Not Standing for Re-election: {gov.get('not_standing', 0)}")
    lines.append(f"  Aggregate Board Comp: {fmt_d(gov.get('aggregate_board_comp'))}")
    lines.append("")

    # Director details
    lines.append("═══ DIRECTORS ═══")
    for d in data["directors"]:
        flags = []
        if d["is_board_chair"]: flags.append("CHAIR")
        if d["is_lead_independent"]: flags.append("LEAD")
        if d["is_independent"]: flags.append("INDEP")
        else: flags.append("MGMT")
        if d["is_not_standing"]: flags.append("NOT STANDING")
        if d["is_newly_elected"]: flags.append("NEW")
        comms = ", ".join(d["committees"]) if d["committees"] else "None"
        lines.append(f"  {d['name']} [{', '.join(flags)}] Age:{d.get('age','—')} Since:{d.get('since','—')} Comp:{fmt_d(d['total'])} Committees:{comms}")
    lines.append("")

    # Fee schedule
    fs = data.get("fee_schedule", {})
    if fs:
        lines.append("═══ FEE SCHEDULE ═══")
        for key in ['cash_retainer', 'equity_retainer', 'total_retainer', 'lead_director_premium',
                     'chair_premium', 'audit_chair_premium', 'comp_chair_premium', 'nomgov_chair_premium']:
            val = fs.get(key)
            if val:
                lines.append(f"  {key.replace('_', ' ').title()}: {fmt_d(val)}")
        lines.append("")

    # Peer fee schedule benchmarks
    pfs = data.get("peer_fee_schedules", [])
    if pfs:
        lines.append("═══ PEER FEE SCHEDULE BENCHMARKS ═══")
        for key in ['cash_retainer', 'equity_retainer', 'total_retainer']:
            vals = [p.get(key) for p in pfs if p.get(key)]
            if vals:
                vals.sort()
                med = vals[len(vals) // 2]
                p25 = vals[len(vals) // 4]
                p75 = vals[3 * len(vals) // 4]
                co_val = fs.get(key)
                pctl = percentile_rank(co_val, vals) if co_val else None
                lines.append(f"  {key.replace('_', ' ').title()}: 25th {fmt_d(p25)} | Median {fmt_d(med)} | 75th {fmt_d(p75)}{f' | Company: {fmt_d(co_val)} ({ordinal(pctl)})' if co_val else ''}")
        lines.append("")

    # Proxy peer group
    lines.append("═══ PROXY PEER GROUP ═══")
    for p in data["proxy_peers"]:
        lines.append(f"  {p['name']} ({p.get('ticker','—')}) | In DB: {p.get('in_universe', False)}")
    lines.append("")

    return "\n".join(lines)


def build_report_prompt(data: Dict, payload: str) -> str:
    """Build the master prompt for the Intelligence Report."""

    company = data["company_name"]
    ticker = data["ticker"]
    prop_type = data["property_type"]

    prompt = f"""You are a senior executive compensation and governance consultant at a top-tier advisory firm. You have been retained to produce a CONFIDENTIAL Board Intelligence Report for {company} ({ticker}).

You have access to web search to research current market conditions, company news, sector trends, and macro factors. USE WEB SEARCH to find:
1. Recent news about {company} ({ticker}) — earnings, M&A, leadership changes, activist activity
2. Current conditions in the {prop_type} sector — demand trends, supply, cap rates, occupancy
3. Macro environment — Fed policy, interest rates, inflation, unemployment, GDP growth
4. Any recent say-on-pay controversies, ISS/Glass Lewis recommendations for {company} or peers
5. Geopolitical or regulatory factors affecting {prop_type} companies

After researching, produce the report using BOTH your research findings AND the quantitative data below.

══════════════════════════════════════════
QUANTITATIVE DATA (from FY{FY_YEAR} proxy filings, current as of {REPORT_DATE})
══════════════════════════════════════════
{payload}
══════════════════════════════════════════

PRODUCE THE FOLLOWING REPORT:

# {company} ({ticker}) — Board Intelligence Report
**Confidential | Prepared {REPORT_DATE} | FY{FY_YEAR} Data**

---

## I. EXECUTIVE SUMMARY
3-4 paragraphs synthesizing the key findings across ALL dimensions — compensation positioning, governance quality, pay-for-performance alignment, sector context, and strategic risks. This should read like a partner's cover letter to the board. Lead with the most important finding. End with the top 3 priorities for the compensation committee.

## II. MACRO & SECTOR CONTEXT
Analyze the current operating environment for {prop_type} companies. Cover:
- Interest rate environment and impact on capital-intensive real estate
- Sector-specific fundamentals (demand, supply, occupancy, rent growth, cap rate trends)
- Secular vs cyclical factors (e.g., AI/data center demand for industrial, remote work for office, demographic shifts for residential)
- How this macro context should inform compensation decisions (e.g., should the comp committee reward alpha generation in a tough market? Is the sector headwind or tailwind?)
- Has the company outperformed peers even if the broad market or sector has underperformed? That's alpha and should be recognized.

## III. EXECUTIVE COMPENSATION ANALYSIS
For each Named Executive Officer:
- Percentile positioning for total comp and each element
- Whether positioning is appropriate given role, tenure, company size, and performance
- Comp mix health — is the equity/cash split aligned with peers and with long-term incentive goals?
- Year-over-year trajectory if discernible
- Specific risks: below-market = flight risk; above-market without performance justification = say-on-pay risk
- CEO pay ratio context

## IV. PAY-FOR-PERFORMANCE ALIGNMENT
This is the most scrutinized section by ISS, Glass Lewis, and institutional shareholders:
- Company TSR vs peer TSR vs S&P 500 (1yr and 3yr)
- Alpha analysis: is the company generating excess returns vs peers?
- CEO comp percentile vs TSR percentile — is there a gap? How large?
- Comp growth vs TSR growth trajectory
- Say-on-pay risk assessment based on quantitative alignment
- Recommend specific actions if misalignment exists

## V. BOARD COMPENSATION & GOVERNANCE
- Board comp vs peer benchmarks (total, cash/equity split, committee premiums)
- Are retainers competitive for attracting/retaining quality directors?
- Governance signals: independence ratio, avg tenure (too short = instability, too long = entrenchment), refreshment rate
- Committee structure adequacy — are there enough committees? Right people chairing?
- Director transitions — what do recent departures/additions signal about strategic direction?
- Any directors who appear to be over-committed (serving on too many boards)?

## VI. PEER GROUP EVALUATION
- Evaluate the proxy-disclosed peer group: are these companies truly comparable?
- Size fit (market cap within 0.5x - 2x?), sector fit, business model similarity
- Companies that appear to be missing or inappropriate
- How peer group composition affects benchmarking outcomes (does a poorly constructed peer group artificially inflate or deflate percentile rankings?)
- If the peer group skews large, it may make comp look low when it's actually appropriate for company size

## VII. TALENT RISK & RETENTION ASSESSMENT
- Which executives appear at highest flight risk based on comp positioning?
- Which executives may be over-compensated relative to performance and peers?
- Board refreshment — is there healthy turnover or concerning instability?
- Succession planning implications based on comp structure

## VIII. STRATEGIC RECOMMENDATIONS
5-7 specific, actionable recommendations for the compensation committee, prioritized by urgency:
- Each recommendation should cite the specific data point driving it
- Include expected impact (retention, shareholder perception, ISS rating, cost)
- Flag any recommendations that require immediate action vs next proxy cycle

CRITICAL INSTRUCTIONS:
- Write for a board audience — sophisticated but concise. No jargon without context.
- Every claim must be supported by a specific data point from the quantitative data or your web research.
- Do NOT invent data. If something is unknown, say so.
- Be willing to deliver uncomfortable findings — boards need honesty, not cheerleading.
- Use the macro and sector context to frame compensation decisions, not just describe them.
- The tone should be that of a trusted advisor speaking candidly to the board in executive session.
- Format with clear headers, subheaders where useful, and bold key findings for scannability.
- Use ★ to flag critical findings that need immediate attention.
"""

    return prompt


# ============================================================
# REPORT GENERATION
# ============================================================
def generate_report(ticker: str, use_web_search: bool = True) -> Optional[str]:
    """
    Generate a full Intelligence Report for a company.
    Returns markdown-formatted report text.
    """
    print(f"[Intelligence Report] Assembling data for {ticker}...")
    data = assemble_data(ticker)
    if not data:
        return f"Error: No data found for {ticker}"

    payload = build_data_payload(data)
    prompt = build_report_prompt(data, payload)

    print(f"[Intelligence Report] Data assembled. {len(data['executives'])} execs, {len(data['directors'])} directors, {len(data['proxy_peers'])} peers")
    print(f"[Intelligence Report] Generating report via Claude...")

    # Build API request
    api_body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
    }

    # Add web search tool if enabled
    if use_web_search:
        api_body["tools"] = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
            }
        ]

    payload_json = json.dumps(api_body).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload_json,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        usage = result.get("usage", {})
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        cost = (in_tok * 3 / 1_000_000) + (out_tok * 15 / 1_000_000)

        # Extract text from response (may have interleaved tool_use and text blocks)
        report_text = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                report_text += block["text"]

        print(f"[Intelligence Report] Done. {in_tok:,} in / {out_tok:,} out tokens. Cost: ${cost:.2f}")
        return report_text

    except Exception as e:
        return f"Error generating report: {e}"


def generate_report_data(ticker: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Return both the assembled data and the report text.
    Useful for the dashboard which needs both for display.
    """
    data = assemble_data(ticker)
    if not data:
        return None, f"Error: No data found for {ticker}"

    payload = build_data_payload(data)
    prompt = build_report_prompt(data, payload)

    # Same API call logic as generate_report
    api_body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }

    payload_json = json.dumps(api_body).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload_json,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())

        report_text = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                report_text += block["text"]

        return data, report_text

    except Exception as e:
        return data, f"Error generating report: {e}"


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python intelligence_report.py TICKER [--no-web]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    use_web = "--no-web" not in sys.argv

    report = generate_report(ticker, use_web_search=use_web)

    if report:
        # Save to file
        fname = f"{ticker}_intelligence_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(fname, "w") as f:
            f.write(report)
        print(f"\nReport saved to {fname}")
        print(f"\n{'='*60}")
        print(report[:2000])
        print(f"\n... ({len(report):,} chars total)")
