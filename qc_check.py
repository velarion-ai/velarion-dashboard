"""
Velarion Data Quality Check
Run periodically to flag data issues in exec_comp table.

Usage:
    python qc_check.py

Requires SUPABASE_URL and SUPABASE_KEY in .streamlit/secrets.toml or environment.
"""

import os
import re
import sys
import pandas as pd
from datetime import datetime

def get_supabase_creds():
    """Get Supabase credentials from secrets or environment."""
    url = os.environ.get('SUPABASE_URL', '')
    key = os.environ.get('SUPABASE_KEY', '')
    if not url:
        try:
            import toml
            secrets = toml.load('.streamlit/secrets.toml')
            url = secrets.get('SUPABASE_URL', '')
            key = secrets.get('SUPABASE_KEY', '')
        except Exception:
            pass
    if not url:
        try:
            with open('app.py') as f:
                content = f.read()
            m = re.search(r'SUPABASE_URL\s*=\s*["\']([^"\']+)', content)
            if m: url = m.group(1)
            m = re.search(r'SUPABASE_KEY\s*=\s*["\']([^"\']+)', content)
            if m: key = m.group(1)
        except Exception:
            pass
    return url, key


def load_exec_comp(sb):
    """Load all exec_comp data with pagination."""
    all_data = []
    offset = 0
    while True:
        result = sb.table('exec_comp').select(
            'ticker,company_name,first_name,last_name,position,'
            'base_salary,cash_bonus_incentive,stock_based_comp,total_comp,'
            'comp_source'
        ).range(offset, offset + 999).execute()
        if result.data:
            all_data.extend(result.data)
        if not result.data or len(result.data) < 1000:
            break
        offset += 1000
    df = pd.DataFrame(all_data)
    for col in ['base_salary', 'cash_bonus_incentive', 'stock_based_comp', 'total_comp']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def check_missing_salaries(df):
    """Flag executives with >$1M total comp but $0 or null salary."""
    suspect = df[
        (df['total_comp'] > 1_000_000) &
        ((df['base_salary'].isna()) | (df['base_salary'] == 0))
    ].copy()
    # Exclude legitimately externally managed (no stock awards)
    suspect = suspect[
        ~((suspect['comp_source'].isin(['external_manager', 'externally_managed'])) &
          ((suspect['stock_based_comp'].isna()) | (suspect['stock_based_comp'] == 0)))
    ]
    return suspect


def check_misclassified_external(df):
    """Flag companies marked external_manager but with individual stock awards > $100K."""
    ext = df[df['comp_source'].isin(['external_manager', 'externally_managed'])].copy()
    misclassified = ext[ext['stock_based_comp'] > 100_000]
    return misclassified


def check_outlier_comp(df):
    """Flag externally managed companies with suspiciously high individual comp (>$10M)."""
    ext = df[df['comp_source'].isin(['external_manager', 'externally_managed'])].copy()
    outliers = ext[ext['total_comp'] > 10_000_000]
    return outliers


def check_zero_total_comp(df):
    """Flag executives where total comp is 0 or null but other fields have values."""
    has_components = (
        (df['base_salary'] > 0) |
        (df['cash_bonus_incentive'] > 0) |
        (df['stock_based_comp'] > 0)
    )
    zero_total = df[has_components & ((df['total_comp'].isna()) | (df['total_comp'] == 0))]
    return zero_total


def check_comp_math(df):
    """Flag executives where component sum significantly exceeds total comp."""
    valid = df[df['total_comp'] > 0].copy()
    valid['component_sum'] = (
        valid['base_salary'].fillna(0) +
        valid['cash_bonus_incentive'].fillna(0) +
        valid['stock_based_comp'].fillna(0)
    )
    # Component sum should not exceed total comp by more than 5%
    over = valid[valid['component_sum'] > valid['total_comp'] * 1.05]
    return over


# ============================================================
# Known externally managed companies (RMR Group, etc.)
# These legitimately have no individual comp — management fees
# are paid to the external manager entity.
# ============================================================
KNOWN_EXTERNAL_MANAGERS = {
    'ILPT': 'RMR Group',
    'SEVN': 'RMR Group',
    'DHC': 'RMR Group',
    'SVC': 'RMR Group',
    'OPI': 'RMR Group',
    'ACRE': 'Ares Management',
    'ARI': 'Apollo Global',
    'BXMT': 'Blackstone',
    'CMTG': 'Claros/Mack',
    'KREF': 'KKR',
    'PMT': 'PennyMac',
    'AOMR': 'Angel Oak',
    'AHT': 'Ashford Inc.',
    'BHR': 'Ashford Inc.',
}

# Companies incorrectly flagged as external_manager — need re-scrape
KNOWN_MISCLASSIFIED = {
    'OHI': 'Has real individual comp — CEO $13.5M with $10.8M stock awards',
    'BEEP': 'Has real individual comp — CEO $2.9M in stock awards',
    'PSTL': 'Has real individual comp — CEO $385K stock + $3.3M total',
}

# Companies needing salary re-scrape (direct employees with $0 salary)
NEEDS_SALARY_RESCRAPE = {
    'OHI': 'CEO Pickett ~$900K-1M salary per proxy CD&A',
    'LEN': 'CEO Stuart Miller $25M total but $0 salary',
    'OUT': 'CEO Jeremy Male $7.2M total but $0 salary',
}


def run_qc():
    """Run all QC checks and print report."""
    from supabase import create_client

    url, key = get_supabase_creds()
    if not url:
        print("ERROR: Cannot find Supabase credentials")
        sys.exit(1)

    sb = create_client(url, key)
    df = load_exec_comp(sb)
    print(f"Velarion Data Quality Check — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Total executives in database: {len(df)}")
    print(f"Total companies: {df['ticker'].nunique()}")
    print("=" * 70)

    # Check 1: Missing salaries
    missing_sal = check_missing_salaries(df)
    print(f"\n🔴 HIGH COMP / $0 SALARY ({len(missing_sal)} executives)")
    print("   Rule: total_comp > $1M and base_salary is 0 or null")
    print("   (excludes legitimately ext. managed with no stock awards)")
    if not missing_sal.empty:
        for _, r in missing_sal.sort_values(['ticker', 'position']).iterrows():
            flag = " ⚠️ KNOWN" if r['ticker'] in NEEDS_SALARY_RESCRAPE else ""
            print(f"   {r['ticker']:6s} {r['first_name']} {r['last_name']:20s} "
                  f"{str(r['position']):12s} Total: ${r['total_comp']:>12,.0f}  "
                  f"Source: {r.get('comp_source','')}{flag}")
    else:
        print("   ✅ None found")

    # Check 2: Misclassified external managers
    misclass = check_misclassified_external(df)
    # Filter to only companies NOT in known external managers
    misclass_real = misclass[~misclass['ticker'].isin(KNOWN_EXTERNAL_MANAGERS)]
    print(f"\n🔴 LIKELY MISCLASSIFIED AS EXTERNAL MANAGER ({len(misclass_real)} executives)")
    print("   Rule: comp_source=external_manager but stock_based_comp > $100K")
    print("   (excludes known external managers like RMR, Blackstone, etc.)")
    if not misclass_real.empty:
        for _, r in misclass_real.sort_values('ticker').iterrows():
            flag = " ⚠️ KNOWN" if r['ticker'] in KNOWN_MISCLASSIFIED else ""
            print(f"   {r['ticker']:6s} {r['first_name']} {r['last_name']:20s} "
                  f"Stock: ${r['stock_based_comp']:>12,.0f}  "
                  f"Total: ${r['total_comp'] or 0:>12,.0f}{flag}")
    else:
        print("   ✅ None found")

    # Check 3: Outlier external manager comp
    outliers = check_outlier_comp(df)
    print(f"\n🟡 EXT. MANAGED WITH >$10M INDIVIDUAL COMP ({len(outliers)} executives)")
    print("   Likely management fees misattributed as individual comp")
    if not outliers.empty:
        for _, r in outliers.sort_values('ticker').iterrows():
            mgr = KNOWN_EXTERNAL_MANAGERS.get(r['ticker'], '?')
            print(f"   {r['ticker']:6s} {r['first_name']} {r['last_name']:20s} "
                  f"Total: ${r['total_comp']:>12,.0f}  Manager: {mgr}")
    else:
        print("   ✅ None found")

    # Check 4: Zero total comp with components
    zero_total = check_zero_total_comp(df)
    print(f"\n🟡 ZERO TOTAL COMP WITH NON-ZERO COMPONENTS ({len(zero_total)} executives)")
    if not zero_total.empty:
        for _, r in zero_total.head(10).iterrows():
            print(f"   {r['ticker']:6s} {r['first_name']} {r['last_name']:20s} "
                  f"Salary: ${r['base_salary'] or 0:>10,.0f}  "
                  f"Bonus: ${r['cash_bonus_incentive'] or 0:>10,.0f}  "
                  f"Total: ${r['total_comp'] or 0:>10,.0f}")
        if len(zero_total) > 10:
            print(f"   ... and {len(zero_total) - 10} more")
    else:
        print("   ✅ None found")

    # Check 5: Component sum > total comp
    math_err = check_comp_math(df)
    print(f"\n🟡 COMPONENT SUM EXCEEDS TOTAL COMP ({len(math_err)} executives)")
    if not math_err.empty:
        for _, r in math_err.head(10).iterrows():
            csum = (r['base_salary'] or 0) + (r['cash_bonus_incentive'] or 0) + (r['stock_based_comp'] or 0)
            print(f"   {r['ticker']:6s} {r['first_name']} {r['last_name']:20s} "
                  f"Components: ${csum:>12,.0f}  Total: ${r['total_comp']:>12,.0f}")
        if len(math_err) > 10:
            print(f"   ... and {len(math_err) - 10} more")
    else:
        print("   ✅ None found")

    # Summary
    print("\n" + "=" * 70)
    total_issues = len(missing_sal) + len(misclass_real) + len(outliers) + len(zero_total) + len(math_err)
    print(f"TOTAL ISSUES: {total_issues}")
    print(f"\nRE-SCRAPE QUEUE:")
    for tk, reason in NEEDS_SALARY_RESCRAPE.items():
        print(f"   {tk}: {reason}")
    for tk, reason in KNOWN_MISCLASSIFIED.items():
        if tk not in NEEDS_SALARY_RESCRAPE:
            print(f"   {tk}: {reason}")
    print()


if __name__ == '__main__':
    run_qc()
