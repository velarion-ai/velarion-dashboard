"""
Employment Agreement Comparison Engine
Velarion Company Intelligence

Fetches, extracts, and compares executive employment agreement terms
from SEC EDGAR filings. Produces structured comparison tables and
AI-powered legal advisory observations.

Usage:
    from employment_comparison import compare_employment_terms
    result = compare_employment_terms(
        subject_ticker="ARE",
        subject_position="CFO",
        peer_tickers=["EQR", "PLD", "BXP"],
        peer_position="CFO"
    )
"""

import requests
import re
import json
import time
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings("ignore")

SEC_HEADERS = {'User-Agent': 'Velarion Research andy@velarion.ai'}
import os
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# =====================================================
# HELPER: Extract executive name from exhibit description
# =====================================================
def extract_exec_name(desc):
    """Extract executive name from SEC exhibit description text."""
    m = re.search(
        r'(?:Company|Corporation)\s+and\s+'
        r'([A-Z][a-z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-z]+)+)'
        r'(?:\s*[,.]|\s+(?:Form|entered|effective|dated|N/A|filed)|$)',
        desc
    )
    return m.group(1).strip() if m else None


# =====================================================
# HELPER: Extract name from agreement opening text
# =====================================================
def extract_name_from_text(text):
    """Extract executive name from the opening paragraph of an agreement."""
    # "Dear Joel:" pattern
    dear = re.search(r'Dear\s+([A-Z][a-z]+)', text[:1000])
    if dear:
        return dear.group(1)
    # "between the Company and [Name]" pattern
    between = re.search(
        r'(?:Company|Corporation)\s+.*?and\s+'
        r'([A-Z][a-z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-z]+)+)',
        text[:2000]
    )
    if between:
        return between.group(1).strip()
    return None


# =====================================================
# STEP 1: Get CIK from ticker
# =====================================================
def get_cik_from_ticker(ticker):
    """Look up CIK from ticker via SEC EDGAR company tickers JSON."""
    resp = requests.get("https://www.sec.gov/files/company_tickers.json",
                        headers=SEC_HEADERS, timeout=10)
    data = resp.json()
    for entry in data.values():
        if entry['ticker'].upper() == ticker.upper():
            return str(entry['cik_str'])
    return None


# =====================================================
# STEP 2: Find the most recent 10-K or 10-Q
# =====================================================
def find_most_recent_periodic_filing(cik):
    """Find the most recent 10-K or 10-Q filing for a company.
    Returns (accession_number, form_type, filing_date, company_name)."""
    cik_padded = str(cik).zfill(10)
    resp = requests.get(f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
                        headers=SEC_HEADERS, timeout=10)
    if resp.status_code != 200:
        return None, None, None, None

    data = resp.json()
    company_name = data.get('name', '')
    recent = data['filings']['recent']

    for i in range(len(recent['form'])):
        form = recent['form'][i]
        if form in ('10-K', '10-Q', '10-K/A', '10-Q/A'):
            return (recent['accessionNumber'][i], form,
                    recent['filingDate'][i], company_name)

    return None, None, None, company_name


# =====================================================
# STEP 3: Find the main filing document filename
# =====================================================
def find_main_document(cik, accession):
    """Find the main 10-K/10-Q HTML document in a filing.
    Pattern: {ticker}-{date}.htm is typically the largest .htm file."""
    acc_clean = accession.replace('-', '')
    time.sleep(0.12)

    idx_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/index.json"
    resp = requests.get(idx_url, headers=SEC_HEADERS, timeout=10)
    if resp.status_code != 200:
        return None

    items = resp.json().get('directory', {}).get('item', [])

    # Find the largest .htm file that is NOT an exhibit or index
    best = None
    best_size = 0
    for item in items:
        name = item['name']
        name_lower = name.lower()
        if not name.endswith(('.htm', '.html')):
            continue
        if 'ex' in name_lower and re.search(r'ex\d', name_lower):
            continue
        if 'index' in name_lower:
            continue
        if name_lower.startswith('r') and re.match(r'^r\d+\.htm', name_lower):
            continue  # Skip XBRL R*.htm fragments

        size = int(str(item.get('size', '0')).replace(',', '') or 0)
        if size > best_size:
            best_size = size
            best = name

    return best


# =====================================================
# STEP 4: Parse exhibit index for employment agreements
# =====================================================
def parse_exhibit_index(cik, accession, filing_text):
    """Parse the exhibit index section of a 10-K/10-Q to find employment agreements.
    Returns list of dicts with exhibit info."""

    # Find exhibit section
    exhibit_start = None
    for pattern in ['Exhibit\nNumber', 'EXHIBIT INDEX', 'INDEX TO EXHIBITS',
                    'EXHIBITS AND FINANCIAL', 'Exhibit Number']:
        idx = filing_text.find(pattern)
        if idx > 0:
            exhibit_start = idx
            break

    if not exhibit_start:
        # Search for first "10.1" in back half
        for m in re.finditer(r'(?:^|\n)\s*10\.\d+', filing_text[len(filing_text)//2:]):
            exhibit_start = len(filing_text)//2 + m.start()
            break

    if not exhibit_start:
        return []

    exhibit_text = filing_text[exhibit_start:exhibit_start + 25000]
    lines = exhibit_text.split('\n')

    employment_keywords = [
        'employment agreement', 'executive employment', 'severance agreement',
        'separation agreement', 'change in control', 'change-in-control',
    ]

    agreements = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        ex_match = re.match(r'^(10\.\d+)\s*(.*)', line)
        if ex_match:
            ex_num = ex_match.group(1)
            desc_parts = [ex_match.group(2).strip()] if ex_match.group(2).strip() else []

            j = i + 1
            while j < min(i + 15, len(lines)):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                if re.match(r'^\d+\.', next_line):
                    break
                desc_parts.append(next_line)
                j += 1

            full_desc = ' '.join(desc_parts).strip()
            desc_lower = full_desc.lower()

            is_employment = any(kw in desc_lower for kw in employment_keywords)
            if is_employment:
                name = extract_exec_name(full_desc)
                is_full = ('amended and restated' in desc_lower and
                           'letter amendment' not in desc_lower)
                is_amendment = ('letter amendment' in desc_lower or
                                ('amendment' in desc_lower and 'restated' not in desc_lower))
                filed_herewith = ('filed herewith' in desc_lower or
                                  'n/a' in desc_lower[-60:].lower())

                # Extract original filing reference
                orig_form = orig_date = None
                form_match = re.search(
                    r'Form\s+([\w-]+(?:/A)?)\s+(\w+\s+\d+,?\s*\d{4})', full_desc)
                if form_match:
                    orig_form = form_match.group(1)
                    orig_date = form_match.group(2)

                agreements.append({
                    'exhibit_number': f"EX-{ex_num}",
                    'description': full_desc[:350],
                    'executive_name': name,
                    'is_full_agreement': is_full,
                    'is_amendment': is_amendment,
                    'is_original': not is_full and not is_amendment,
                    'filed_herewith': filed_herewith,
                    'original_form': orig_form,
                    'original_date': orig_date,
                    'filing_accession': accession,
                    'cik': cik,
                })

            i = j
        else:
            i += 1

    return agreements


# =====================================================
# STEP 5: Find a specific filing by form type and date
# =====================================================
def find_filing_by_form_and_date(cik, target_form, target_date_str):
    """Find a filing accession number by form type and filing date string.
    Searches both recent and older filing archives."""
    cik_padded = str(cik).zfill(10)
    resp = requests.get(f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
                        headers=SEC_HEADERS, timeout=10)
    data = resp.json()

    # Parse target date
    months = {'January': '01', 'February': '02', 'March': '03', 'April': '04',
              'May': '05', 'June': '06', 'July': '07', 'August': '08',
              'September': '09', 'October': '10', 'November': '11', 'December': '12'}

    date_match = re.search(r'(\w+)\s+(\d+),?\s*(\d{4})', target_date_str)
    if not date_match:
        return None

    month = months.get(date_match.group(1), '01')
    day = date_match.group(2).zfill(2)
    year = date_match.group(3)
    target_int = int(f"{year}{month}{day}")

    def search_filings(filing_data):
        for i in range(len(filing_data.get('form', []))):
            form = filing_data['form'][i]
            filed = filing_data['filingDate'][i]
            if form.replace('/A', '') != target_form.replace('/A', ''):
                continue
            filed_int = int(filed.replace('-', ''))
            if abs(filed_int - target_int) < 6:
                return filing_data['accessionNumber'][i]
        return None

    # Search recent filings
    result = search_filings(data['filings']['recent'])
    if result:
        return result

    # Search older filing archives
    for older_file in data.get('filings', {}).get('files', []):
        time.sleep(0.12)
        older_resp = requests.get(
            f"https://data.sec.gov/submissions/{older_file['name']}",
            headers=SEC_HEADERS, timeout=10)
        if older_resp.status_code == 200:
            result = search_filings(older_resp.json())
            if result:
                return result

    return None


# =====================================================
# STEP 6: Fetch exhibit text from a filing
# =====================================================
def fetch_exhibit_text(cik, accession, exhibit_number):
    """Fetch the full text of an exhibit from a specific filing.
    Returns (text, url) or (None, None)."""
    acc_clean = accession.replace('-', '')
    time.sleep(0.12)

    idx_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/index.json"
    resp = requests.get(idx_url, headers=SEC_HEADERS, timeout=10)
    if resp.status_code != 200:
        return None, None

    items = resp.json().get('directory', {}).get('item', [])
    ex_num_clean = exhibit_number.replace('EX-', '').replace('.', '')

    # Strategy 1: Match by exhibit number in filename
    for item in items:
        name = item['name'].lower()
        if name.endswith(('.htm', '.html')) and 'ex' in name:
            fn_num = re.search(r'ex[- ]?(\d+)', name)
            if fn_num and fn_num.group(1) == ex_num_clean:
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{item['name']}"
                time.sleep(0.12)
                doc_resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
                if doc_resp.status_code == 200:
                    soup = BeautifulSoup(doc_resp.text, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                    text = re.sub(r'\s+', ' ', text).strip()
                    text = re.sub(r'^.*?(?:EXHIBIT\s+\d+\.\d+|EX-\d+\.\d+)\s*(?:Document)?\s*',
                                  '', text, count=1)
                    return text, url

    # Strategy 2: Check all exhibit files for employment agreement content
    for item in items:
        name = item['name'].lower()
        if name.endswith(('.htm', '.html')) and 'ex' in name and 'index' not in name:
            size = int(str(item.get('size', '0')).replace(',', '') or 0)
            if size > 5000:
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{item['name']}"
                time.sleep(0.12)
                doc_resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
                if doc_resp.status_code == 200:
                    soup = BeautifulSoup(doc_resp.text, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                    if 'employment agreement' in text[:3000].lower():
                        text = re.sub(r'\s+', ' ', text).strip()
                        text = re.sub(
                            r'^.*?(?:EXHIBIT\s+\d+\.\d+|EX-\d+\.\d+)\s*(?:Document)?\s*',
                            '', text, count=1)
                        return text, url

    return None, None


# =====================================================
# STEP 7: Get the best agreement for an executive
# =====================================================
def get_best_agreement_for_exec(cik, agreements, exec_name):
    """Given the list of parsed agreements, find and fetch the best one.
    Prefers 'Amended and Restated' over originals. Follows references to older filings."""

    exec_agreements = [a for a in agreements if a['executive_name'] == exec_name]
    if not exec_agreements:
        return None, None

    # Prefer full "Amended and Restated" agreements
    full = [a for a in exec_agreements if a['is_full_agreement']]
    originals = [a for a in exec_agreements if a['is_original']]
    target = full[-1] if full else (originals[-1] if originals else exec_agreements[-1])

    # If filed herewith, fetch from current filing
    if target['filed_herewith']:
        return fetch_exhibit_text(cik, target['filing_accession'], target['exhibit_number'])

    # Otherwise, follow the reference to the original filing
    if target['original_form'] and target['original_date']:
        ref_acc = find_filing_by_form_and_date(cik, target['original_form'],
                                                target['original_date'])
        if ref_acc:
            return fetch_exhibit_text(cik, ref_acc, target['exhibit_number'])

    return None, None


# =====================================================
# STEP 8: AI extraction of structured terms
# =====================================================
EXTRACTION_SYSTEM = """You are a senior employment attorney. Extract employment agreement terms into JSON. If a term is not addressed, use null. Return ONLY valid JSON — no markdown, no backticks, no explanation."""

EXTRACTION_SCHEMA = """{
  "executive_name": "full name",
  "position": "title",
  "agreement_date": "date",
  "effective_date": "date",
  "base_salary": number,
  "bonus_target_pct": number or null,
  "guaranteed_bonus": number or null,
  "signing_bonus": number or null,
  "signing_equity_shares": number or null,
  "signing_equity_value": number or null,
  "signing_equity_type": "RSU/PSU/Options" or null,
  "make_whole_equity_shares": number or null,
  "make_whole_equity_value": number or null,
  "relocation_allowance": number or null,
  "severance_multiple": decimal,
  "severance_base": "description",
  "severance_includes_bonus": true/false,
  "pro_rata_bonus": true/false,
  "benefits_continuation_months": number,
  "outplacement": true/false,
  "equity_treatment_termination": "description",
  "notice_period_months": number or null,
  "cic_multiple": decimal,
  "cic_base": "description",
  "cic_trigger": "single/double/modified double",
  "cic_equity_acceleration": "full/pro-rata/none",
  "cic_benefits_months": number or null,
  "non_compete_months": number or null,
  "non_compete_scope": "description" or null,
  "non_solicit_months": number or null,
  "non_solicit_scope": "description" or null,
  "good_reason_triggers": ["list"],
  "good_reason_cure_days": number,
  "clawback_type": "description" or null,
  "clawback_details": "description" or null,
  "excise_tax_treatment": "gross-up/best-net cutback/none specified",
  "term_type": "fixed/at-will/evergreen",
  "term_years": number or null,
  "auto_renewal": true/false,
  "auto_renewal_period": "description" or null,
  "confidentiality": true/false
}"""


def extract_terms_via_ai(agreement_text):
    """Send agreement text to Claude for structured term extraction.
    Returns parsed dict or None."""
    user_msg = f"Extract key terms:\n\n{agreement_text[:45000]}\n\nJSON:\n{EXTRACTION_SCHEMA}"

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "system": EXTRACTION_SYSTEM,
            "messages": [{"role": "user", "content": user_msg}]
        },
        timeout=60
    )

    if resp.status_code != 200:
        return None

    result = resp.json()['content'][0]['text']
    clean = result.strip().replace('```json', '').replace('```', '').strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return None


# =====================================================
# STEP 9: AI comparison and observations
# =====================================================
COMPARISON_SYSTEM = """You are a senior executive compensation attorney preparing a confidential employment agreement comparison for a board compensation committee. Your client is the SUBJECT COMPANY (marked with ★).

Produce TWO sections:

SECTION 1: COMPARISON TABLE
Create a markdown table comparing ALL material terms side by side. Rows:
- Base Salary
- Bonus Target (% of base)
- Severance Multiple & Base
- CIC Multiple & Trigger
- Equity Treatment (Termination w/o Cause)
- Equity Treatment (CIC)
- Non-Compete
- Non-Solicitation
- Good Reason Triggers (summarize count and key items)
- Cure Period
- Benefits Continuation
- Clawback
- 280G Excise Tax Treatment
- Agreement Term
- Signing/Make-Whole Equity
- Confidentiality

Subject company column first, highlighted with ★.

SECTION 2: OBSERVATIONS & RECOMMENDATIONS
Write 5-7 paragraphs covering:
1. **Market Positioning**: Where the subject company stands on each major term vs peers. Be specific.
2. **Strengths**: Well-structured or company-favorable provisions.
3. **Weaknesses & Gaps**: Missing provisions, below-market terms, governance risk.
4. **Out-of-Market Provisions**: Anything unusual in either direction.
5. **Renewal Recommendations**: Specific, actionable items for the next renewal. Prioritize.
6. **Risk Flags**: Provisions that could draw ISS, proxy advisor, or activist scrutiny.
7. **Missing Terms**: Standard provisions absent from the subject agreement that peers include.

Be direct, specific, and reference peer data for every observation. This should read like a $25,000 legal advisory memo."""


def generate_comparison(subject_label, subject_terms, peer_labels_terms):
    """Generate AI-powered comparison table and observations.
    subject_label: e.g. "ARE — Marc E. Binda (CFO)"
    subject_terms: dict of extracted terms
    peer_labels_terms: dict of {label: terms_dict}
    Returns markdown string."""

    all_terms = {f"{subject_label} ★": subject_terms}
    all_terms.update(peer_labels_terms)

    peer_list = "\n".join([f"PEER: {label}" for label in peer_labels_terms.keys()])

    user_msg = f"""SUBJECT: {subject_label} ★
{peer_list}

EXTRACTED TERMS:
{json.dumps(all_terms, indent=2)}"""

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000,
            "system": COMPARISON_SYSTEM,
            "messages": [{"role": "user", "content": user_msg}]
        },
        timeout=120
    )

    if resp.status_code != 200:
        return f"Error generating comparison: {resp.status_code}"

    return resp.json()['content'][0]['text']


# =====================================================
# MASTER FUNCTION: Full pipeline
# =====================================================
def fetch_agreements_for_company(ticker, target_position=None):
    """Fetch and extract employment agreement terms for a company.
    
    Args:
        ticker: Stock ticker (e.g. "ARE")
        target_position: Optional position filter (e.g. "CEO", "CFO")
    
    Returns:
        dict: {exec_name: {terms_dict}} for each executive found
    """
    # Get CIK
    cik = get_cik_from_ticker(ticker)
    if not cik:
        return {}

    # Find most recent periodic filing
    acc, form, filed, company_name = find_most_recent_periodic_filing(cik)
    if not acc:
        return {}

    # Find the main document
    main_doc = find_main_document(cik, acc)
    if not main_doc:
        return {}

    # Fetch and parse the filing
    acc_clean = acc.replace('-', '')
    time.sleep(0.12)
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{main_doc}"
    resp = requests.get(filing_url, headers=SEC_HEADERS, timeout=30)
    if resp.status_code != 200:
        return {}

    soup = BeautifulSoup(resp.text, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)

    # Parse exhibit index
    agreements = parse_exhibit_index(cik, acc, text)
    if not agreements:
        return {}

    # Get unique executive names
    exec_names = list(set(a['executive_name'] for a in agreements if a['executive_name']))

    results = {}
    for name in exec_names:
        agreement_text, url = get_best_agreement_for_exec(cik, agreements, name)
        if not agreement_text or len(agreement_text) < 1000:
            continue

        # Check if this is a substantial agreement (not just a letter amendment)
        has_terms = any(kw in agreement_text.lower() for kw in
                        ['severance', 'termination without cause', 'change in control'])
        if not has_terms:
            continue

        terms = extract_terms_via_ai(agreement_text)
        if terms:
            label = f"{ticker} — {terms.get('executive_name', name)} ({terms.get('position', 'Executive')})"
            results[label] = terms
            time.sleep(1)  # Rate limit between AI calls

    return results


def compare_employment_terms(subject_ticker, subject_position,
                              peer_tickers, peer_position=None):
    """Full pipeline: fetch agreements, extract terms, generate comparison.
    
    Args:
        subject_ticker: The company being analyzed (e.g. "ARE")
        subject_position: Position to focus on (e.g. "CFO")
        peer_tickers: List of peer company tickers
        peer_position: Position at peer companies (defaults to subject_position)
    
    Returns:
        str: Markdown comparison report
    """
    if peer_position is None:
        peer_position = subject_position

    # Fetch subject company agreements
    subject_terms = fetch_agreements_for_company(subject_ticker, subject_position)
    if not subject_terms:
        return "Could not find employment agreements for the subject company."

    # Find the best match for the target position
    subject_label = None
    subject_data = None
    for label, terms in subject_terms.items():
        pos = (terms.get('position', '') or '').lower()
        if subject_position.lower() in pos:
            subject_label = label
            subject_data = terms
            break
    if not subject_data:
        # Fall back to first executive found
        subject_label = list(subject_terms.keys())[0]
        subject_data = list(subject_terms.values())[0]

    # Fetch peer agreements
    peer_all = {}
    for ticker in peer_tickers:
        peer_terms = fetch_agreements_for_company(ticker, peer_position)
        for label, terms in peer_terms.items():
            pos = (terms.get('position', '') or '').lower()
            if peer_position.lower() in pos:
                peer_all[label] = terms
                break
        else:
            # Fall back to first executive
            if peer_terms:
                first_label = list(peer_terms.keys())[0]
                peer_all[first_label] = list(peer_terms.values())[0]

    if not peer_all:
        return "Could not find employment agreements for any peer companies."

    # Generate comparison
    return generate_comparison(subject_label, subject_data, peer_all)


# =====================================================
# CLI test
# =====================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        print(f"Fetching agreements for {ticker}...")
        results = fetch_agreements_for_company(ticker)
        for label, terms in results.items():
            print(f"\n{label}:")
            for k, v in terms.items():
                if v is not None:
                    print(f"  {k}: {v}")
    else:
        print("Usage: python employment_comparison.py TICKER")
        print("  e.g. python employment_comparison.py ARE")
