"""
ETL pipeline: Extract -> Transform (clean + validate) -> Load
Source : data/customers_raw.csv (messy loan-customer data)
Target : SQLite database output/customers.db
         - clean_customers   : validated records
         - rejected_records  : records that failed a critical rule, with reasons
         - etl_run_log       : row counts for every run (audit trail)
"""
import re, sqlite3, os
from datetime import datetime, date
import pandas as pd

RAW = "data/customers_raw.csv"
DB = "output/customers.db"
TODAY = date(2026, 10, 20)
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]
REGION_MAP = {"gt accra": "Greater Accra", "accra": "Greater Accra", "ashanti region": "Ashanti",
              "central region": "Central", "volta region": "Volta"}
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$")

# ---------------- EXTRACT ----------------
def extract():
    return pd.read_csv(RAW, dtype=str, keep_default_na=False)

# ---------------- TRANSFORM helpers ----------------
def parse_date(s):
    s = s.strip()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None

def clean_amount(s):
    s = re.sub(r"[^\d.\-]", "", s)          # drop 'GHS', commas, spaces
    try:
        return float(s)
    except ValueError:
        return None

def clean_phone(s):
    d = re.sub(r"\D", "", s)                # digits only
    if d.startswith("233") and len(d) == 12: d = d[3:]
    elif d.startswith("0") and len(d) == 10: d = d[1:]
    return "+233" + d if len(d) == 9 else None

def clean_region(s):
    s = s.strip().lower()
    return REGION_MAP.get(s, s.title())

def transform(raw):
    stats = {"raw_rows": len(raw)}
    df = raw.copy()

    # 1. Standardise text (trim whitespace, consistent case)
    df["full_name"] = df["full_name"].str.strip().str.title()
    df["status"] = df["status"].str.strip().str.title()
    df["region"] = df["region"].apply(clean_region)
    df["email"] = df["email"].str.strip().str.lower()

    # 2. Remove duplicates (same customer_id) - keep first occurrence
    df["_key"] = df["customer_id"].str.strip().str.upper()
    before = len(df)
    df = df.drop_duplicates(subset="_key", keep="first").drop(columns="_key")
    stats["duplicates_removed"] = before - len(df)

    # 3. Convert types / standardise formats
    df["dob"] = df["date_of_birth"].apply(parse_date)
    df["loan_dt"] = df["loan_date"].apply(parse_date)
    df["loan_amount_ghs"] = df["loan_amount"].apply(clean_amount)
    df["phone_std"] = df["phone"].apply(clean_phone)
    df["score"] = pd.to_numeric(df["credit_score"], errors="coerce")
    stats["date_formats_standardised"] = int((df["date_of_birth"].str.strip() != "").sum())
    stats["phones_standardised"] = int(df["phone_std"].notna().sum())

    # 4. Validate: critical rules -> reject; soft rules -> flag
    reasons = {i: [] for i in df.index}
    flags = {i: [] for i in df.index}
    for i, r in df.iterrows():
        if not r["full_name"]: reasons[i].append("missing name")
        if pd.isna(r["dob"]) or r["dob"] is None: reasons[i].append("invalid date of birth")
        else:
            age = (TODAY - r["dob"]).days / 365.25
            if age < 18: reasons[i].append("under 18")
            elif age > 100: reasons[i].append("age over 100")
        if pd.isna(r["loan_dt"]) or r["loan_dt"] is None: reasons[i].append("invalid loan date")
        elif r["loan_dt"] > TODAY: reasons[i].append("loan date in future")
        if pd.isna(r["loan_amount_ghs"]): reasons[i].append("missing loan amount")
        elif r["loan_amount_ghs"] <= 0: reasons[i].append("non-positive loan amount")
        if pd.isna(r["phone_std"]): reasons[i].append("invalid phone")
        if r["email"] == "": flags[i].append("missing email")
        elif not EMAIL_RE.match(r["email"]): flags[i].append("invalid email")
        if pd.isna(r["score"]): flags[i].append("missing credit score")
        elif not 300 <= r["score"] <= 850: flags[i].append("credit score out of range")

    df["reject_reason"] = [", ".join(reasons[i]) for i in df.index]
    df["quality_flag"] = [", ".join(flags[i]) for i in df.index]
    rejected = df[df["reject_reason"] != ""].copy()
    clean = df[df["reject_reason"] == ""].copy()

    # soft-rule failures are nulled out rather than loaded as bad values
    bad_email = clean["quality_flag"].str.contains("invalid email|missing email")
    clean.loc[bad_email, "email"] = None
    bad_score = clean["quality_flag"].str.contains("score")
    clean.loc[bad_score, "score"] = None

    stats.update(clean_rows=len(clean), rejected_rows=len(rejected),
                 flagged_rows=int((clean["quality_flag"] != "").sum()))
    stats["reject_breakdown"] = (rejected["reject_reason"].str.split(", ").explode().value_counts().to_dict())
    stats["flag_breakdown"] = (clean["quality_flag"][clean["quality_flag"] != ""].str.split(", ").explode().value_counts().to_dict())

    clean_out = pd.DataFrame({
        "customer_id": clean["customer_id"].str.strip().str.upper(),
        "full_name": clean["full_name"],
        "date_of_birth": clean["dob"].astype(str),
        "phone": clean["phone_std"],
        "email": clean["email"],
        "region": clean["region"],
        "loan_amount_ghs": clean["loan_amount_ghs"],
        "loan_date": clean["loan_dt"].astype(str),
        "status": clean["status"],
        "credit_score": clean["score"],
        "quality_flag": clean["quality_flag"],
    })
    rej_out = rejected[["customer_id", "full_name", "date_of_birth", "phone", "loan_amount", "loan_date", "reject_reason"]]
    return clean_out, rej_out, stats

# ---------------- LOAD ----------------
def load(clean, rejected, stats):
    os.makedirs("output", exist_ok=True)
    if os.path.exists(DB): os.remove(DB)
    con = sqlite3.connect(DB)
    clean.to_sql("clean_customers", con, index=False)
    rejected.to_sql("rejected_records", con, index=False)
    pd.DataFrame([{
        "run_time": datetime.now().isoformat(timespec="seconds"),
        "raw_rows": stats["raw_rows"], "duplicates_removed": stats["duplicates_removed"],
        "rejected_rows": stats["rejected_rows"], "loaded_rows": stats["clean_rows"],
    }]).to_sql("etl_run_log", con, index=False)
    con.commit(); con.close()
    clean.to_csv("output/customers_clean.csv", index=False)
    rejected.to_csv("output/customers_rejected.csv", index=False)

if __name__ == "__main__":
    raw = extract()
    print(f"EXTRACT  : {len(raw)} rows read")
    clean, rejected, stats = transform(raw)
    load(clean, rejected, stats)
    print(f"TRANSFORM: {stats['duplicates_removed']} duplicates removed, "
          f"{stats['rejected_rows']} rejected, {stats['flagged_rows']} flagged")
    print(f"LOAD     : {stats['clean_rows']} clean rows loaded into {DB}")
    print("\nReject reasons:"); [print(f"  {k}: {v}") for k, v in stats["reject_breakdown"].items()]
    print("Flags on loaded rows:"); [print(f"  {k}: {v}") for k, v in stats["flag_breakdown"].items()]
