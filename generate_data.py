"""Generate a synthetic, deliberately messy loan-customer dataset (no real people)."""
import csv, random
from datetime import date, timedelta

random.seed(42)
N, N_DUPES = 5000, 250
FIRST = ["Kwame","Ama","Kofi","Abena","Yaw","Akosua","Kwesi","Efua","Nana","Esi","Kojo","Adwoa","Mensah","Selorm","Dela","Fiifi","Afia","Kwabena","Araba","Yaa"]
LAST = ["Mensah","Owusu","Boateng","Asante","Appiah","Addo","Sagoe","Quaye","Tetteh","Ofori","Amoah","Darko","Agyeman","Nkrumah","Lartey","Annan"]
REGIONS = {
    "Greater Accra": ["Greater Accra","greater accra","GREATER ACCRA","Gt Accra","Accra"],
    "Ashanti": ["Ashanti","ashanti","ASHANTI","Ashanti Region"],
    "Western": ["Western","western","WESTERN"],
    "Central": ["Central","central","Central Region"],
    "Eastern": ["Eastern","eastern","EASTERN"],
    "Northern": ["Northern","northern","NORTHERN"],
    "Volta": ["Volta","volta","Volta Region"],
}
STATUS = {"Active": ["Active","active ","ACTIVE"], "Closed": ["Closed","closed","CLOSED "], "Defaulted": ["Defaulted","defaulted","DEFAULTED"]}
PREFIX = ["24","54","55","20","50","27","26","59"]

def rand_date(a, b):
    return a + timedelta(days=random.randint(0, (b - a).days))

def fmt_date(d):
    k = random.random()
    if k < 0.55: return d.strftime("%Y-%m-%d")
    if k < 0.85: return d.strftime("%d/%m/%Y")
    return d.strftime("%d-%b-%Y")

def fmt_phone(p):
    k = random.random()
    if k < 0.4: return "0" + p
    if k < 0.65: return "+233" + p
    if k < 0.85: return f"0{p[:2]} {p[2:5]} {p[5:]}"
    return "233" + p

def fmt_amount(a):
    k = random.random()
    if k < 0.5: return str(a)
    if k < 0.8: return f"GHS {a:,.2f}"
    return f"{a:,}"

rows = []
for i in range(N):
    f, l = random.choice(FIRST), random.choice(LAST)
    name = f"{f} {l}"
    r = random.random()
    if r < 0.05: name = name.upper()
    elif r < 0.10: name = name.lower()
    elif r < 0.14: name = f"  {name}  "
    elif r < 0.145: name = ""
    dob = rand_date(date(1960,1,1), date(2003,12,31))
    if random.random() < 0.01: dob = rand_date(date(2012,1,1), date(2020,12,31))   # under 18
    dob_s = "31/02/1990" if random.random() < 0.01 else fmt_date(dob)               # impossible date
    phone = random.choice(PREFIX) + "".join(random.choice("0123456789") for _ in range(7))
    phone_s = fmt_phone(phone)
    if random.random() < 0.02: phone_s = phone[:5]                                  # truncated
    email = f"{f}.{l}{random.randint(1,99)}@{random.choice(['gmail.com','yahoo.com','outlook.com'])}".lower()
    r = random.random()
    if r < 0.06: email = ""
    elif r < 0.09: email = email.replace("@", "")
    region = random.choice(random.choice(list(REGIONS.values())))
    amt = random.randint(500, 50000)
    amt_s = fmt_amount(amt)
    r = random.random()
    if r < 0.02: amt_s = ""
    elif r < 0.03: amt_s = f"-{amt}"
    ld = rand_date(date(2022,1,1), date(2026,9,30))
    ld_s = "N/A" if random.random() < 0.01 else fmt_date(ld)
    if random.random() < 0.005: ld_s = "2030-01-15"                                  # future date
    status = random.choice(random.choice(list(STATUS.values())))
    score = str(random.randint(300, 850))
    r = random.random()
    if r < 0.05: score = ""
    elif r < 0.06: score = random.choice(["9999","-1","1200"])
    rows.append([f"CUST{i+1:05d}", name, dob_s, phone_s, email, region, amt_s, ld_s, status, score])

dupes = [list(random.choice(rows)) for _ in range(N_DUPES)]
for d in dupes:
    if random.random() < 0.3: d[1] = d[1].upper()      # same customer, different casing
rows += dupes
random.shuffle(rows)

with open("data/customers_raw.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["customer_id","full_name","date_of_birth","phone","email","region","loan_amount","loan_date","status","credit_score"])
    w.writerows(rows)
print(f"Wrote data/customers_raw.csv with {len(rows)} rows ({N} unique customers + {N_DUPES} duplicates)")
