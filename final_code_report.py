from pathlib import Path
import duckdb

#Cleaning and transforming DEMO data from FAERS, then saving as Parquet

# Raw FAERS ASCII files directory
folder = Path("data/raw_ascii")
con = duckdb.connect("faers.duckdb")

demo_files = [
    folder / "DEMO25Q1.txt",
    folder / "DEMO25Q2.txt",
    folder / "DEMO25Q3.txt",
    folder / "DEMO25Q4.txt",
]

for f in demo_files:
    print(f.name, "var mı:", f.exists())

con.execute(f"""
CREATE OR REPLACE TABLE demo_all AS
SELECT *
FROM read_csv(
    { [f.as_posix() for f in demo_files] },
    delim='$',
    header=True,
    all_varchar=True,
    ignore_errors=True
)
""")

print("\n--- DEMO_ALL SATIR SAYISI ---")
print(con.execute("""
SELECT COUNT(*) AS total_rows
FROM demo_all
""").df())

print("\n--- DEMO_ALL KOLONLAR ---")
print(con.execute("""
DESCRIBE demo_all
""").df())

print("\n--- İLK 5 SATIR ---")
print(con.execute("""
SELECT *
FROM demo_all
LIMIT 5
""").df())

con.execute("""
CREATE OR REPLACE TABLE demo_final AS
WITH converted AS (
    SELECT
        primaryid,
        caseid,

        CASE
            WHEN TRY_CAST(age AS DOUBLE) IS NULL THEN NULL
            WHEN UPPER(TRIM(age_cod)) = 'YR' THEN TRY_CAST(age AS DOUBLE)
            WHEN UPPER(TRIM(age_cod)) = 'MON' THEN TRY_CAST(age AS DOUBLE) / 12
            WHEN UPPER(TRIM(age_cod)) = 'WK' THEN TRY_CAST(age AS DOUBLE) / 52
            WHEN UPPER(TRIM(age_cod)) = 'DY' THEN TRY_CAST(age AS DOUBLE) / 365
            WHEN UPPER(TRIM(age_cod)) = 'DEC' THEN TRY_CAST(age AS DOUBLE) * 10
            ELSE NULL
        END AS age_years,

        CASE
            WHEN TRY_CAST(wt AS DOUBLE) IS NULL THEN NULL
            WHEN UPPER(TRIM(wt_cod)) = 'KG' THEN TRY_CAST(wt AS DOUBLE)
            WHEN UPPER(TRIM(wt_cod)) IN ('LB', 'LBS') THEN TRY_CAST(wt AS DOUBLE) * 0.453592
            ELSE NULL
        END AS weight_kg,

        UPPER(TRIM(sex)) AS sex,

        COALESCE(
            NULLIF(UPPER(TRIM(occr_country)), ''),
            NULLIF(UPPER(TRIM(reporter_country)), '')
        ) AS country

    FROM demo_all
    WHERE primaryid IS NOT NULL
      AND caseid IS NOT NULL
)

SELECT *
FROM converted
WHERE age_years BETWEEN 0 AND 120
  AND (weight_kg IS NULL OR weight_kg BETWEEN 20 AND 300)
  AND sex IN ('M', 'F')
""")

print("\n--- DEMO_FINAL SATIR SAYISI ---")
print(con.execute("""
SELECT COUNT(*) AS n
FROM demo_final
""").df())

print("\n--- DEMO_FINAL İLK 5 SATIR ---")
print(con.execute("""
SELECT *
FROM demo_final
LIMIT 5
""").df())

print("\n--- DEMO_FINAL ÖZET ---")
print(con.execute("""
SELECT
    MIN(age_years) AS min_age,
    AVG(age_years) AS mean_age,
    MAX(age_years) AS max_age,
    MIN(weight_kg) AS min_weight,
    AVG(weight_kg) AS mean_weight,
    MAX(weight_kg) AS max_weight
FROM demo_final
""").df())

print("\n--- SEX DAĞILIMI ---")
print(con.execute("""
SELECT sex, COUNT(*) AS n
FROM demo_final
GROUP BY sex
ORDER BY n DESC
""").df())

print("\n--- COUNTRY TOP 10 ---")
print(con.execute("""
SELECT country, COUNT(*) AS n
FROM demo_final
GROUP BY country
ORDER BY n DESC
LIMIT 10
""").df())

con.execute("""
COPY demo_final
TO 'data/demo_final.parquet'
(FORMAT PARQUET)
""")

print("demo_final.parquet kaydedildi")

#Cleaning and transforming DRUG data from FAERS, then saving as Parquet

folder = Path("data/raw_ascii")
con = duckdb.connect("faers.duckdb")

drug_files = [
    folder / "DRUG25Q1.txt",
    folder / "DRUG25Q2.txt",
    folder / "DRUG25Q3.txt",
    folder / "DRUG25Q4.txt",
]

for f in drug_files:
    print(f.name, "var mı:", f.exists())

con.execute(f"""
CREATE OR REPLACE TABLE drug_all AS
SELECT *
FROM read_csv(
    {[f.as_posix() for f in drug_files]},
    delim='$',
    header=True,
    all_varchar=True,
    ignore_errors=True
)
""")


con.execute("""
CREATE OR REPLACE TABLE drug_ps AS
SELECT *
FROM drug_all
WHERE UPPER(TRIM(role_cod)) = 'PS'
""")

print("\n--- DRUG_PS SAYISI ---")
print(con.execute("""
SELECT COUNT(*) AS n
FROM drug_ps
""").df())

print("\n--- HEDEF İLAÇLAR ---")
print(con.execute("""
SELECT
    UPPER(TRIM(drugname)) AS drugname,
    COUNT(*) AS n
FROM drug_ps
WHERE UPPER(TRIM(drugname)) IN (
    'OZEMPIC',
    'TRULICITY',
    'MOUNJARO'
)
GROUP BY UPPER(TRIM(drugname))
ORDER BY n DESC
""").df())

con.execute("""
CREATE OR REPLACE TABLE single_ps_cases AS
SELECT primaryid
FROM drug_ps
GROUP BY primaryid
HAVING COUNT(*) = 1
""")

print("\n--- SINGLE PS CASES ---")

print(con.execute("""
SELECT COUNT(*) AS n
FROM single_ps_cases
""").df())

print("\n--- TEK PS HEDEF İLAÇLAR ---")
print(con.execute("""
SELECT
    UPPER(TRIM(d.drugname)) AS drugname,
    COUNT(*) AS n
FROM drug_ps d
JOIN single_ps_cases s
ON d.primaryid = s.primaryid
WHERE UPPER(TRIM(d.drugname)) IN (
    'OZEMPIC',
    'TRULICITY',
    'MOUNJARO'
)
GROUP BY UPPER(TRIM(d.drugname))
ORDER BY n DESC
""").df())

con.execute("""
CREATE OR REPLACE TABLE drug_target_raw AS
SELECT
    d.primaryid,
    UPPER(TRIM(d.drugname)) AS drugname,
    d.dose_amt,
    UPPER(TRIM(d.dose_unit)) AS dose_unit,
    UPPER(TRIM(d.dose_vbm)) AS dose_vbm
FROM drug_ps d
JOIN single_ps_cases s
ON d.primaryid = s.primaryid
WHERE UPPER(TRIM(d.drugname)) IN (
    'OZEMPIC',
    'TRULICITY',
    'MOUNJARO'
)
""")

con.execute("""
CREATE OR REPLACE TABLE drug_counts AS
SELECT
    primaryid,
    COUNT(*) AS total_drugs,
    SUM(CASE WHEN UPPER(TRIM(role_cod)) <> 'PS' THEN 1 ELSE 0 END) AS num_concomitant_drugs
FROM drug_all
GROUP BY primaryid
""")

con.execute("""
CREATE OR REPLACE TABLE drug_target_clean AS
SELECT
    primaryid,
    drugname,

    CASE
        WHEN TRY_CAST(dose_amt AS DOUBLE) IS NULL THEN NULL
        WHEN dose_unit = 'MG' THEN TRY_CAST(dose_amt AS DOUBLE)
        WHEN dose_unit = 'G' THEN TRY_CAST(dose_amt AS DOUBLE) * 1000
        WHEN dose_unit IN ('MCG', 'UG') THEN TRY_CAST(dose_amt AS DOUBLE) / 1000
        ELSE NULL
    END AS dose_mg

FROM drug_target_raw
""")

con.execute("""
CREATE OR REPLACE TABLE drug_final AS
SELECT
    t.primaryid,
    t.drugname,
    t.dose_mg,
    c.num_concomitant_drugs
FROM drug_target_clean t
LEFT JOIN drug_counts c
ON t.primaryid = c.primaryid
""")

print("\n--- DRUG_FINAL SAYILAR ---")
print(con.execute("""
SELECT drugname, COUNT(*) AS n
FROM drug_final
GROUP BY drugname
ORDER BY n DESC
""").df())

print("\n--- DRUG_FINAL ÖZET ---")
print(con.execute("""
SELECT
    drugname,
    COUNT(*) AS total,
    SUM(CASE WHEN dose_mg IS NULL THEN 1 ELSE 0 END) AS null_dose,
    AVG(dose_mg) AS mean_dose,
    MIN(dose_mg) AS min_dose,
    MAX(dose_mg) AS max_dose,
    AVG(num_concomitant_drugs) AS mean_concomitant
FROM drug_final
GROUP BY drugname
ORDER BY drugname
""").df())

con.execute("""
CREATE OR REPLACE TABLE drug_final AS
SELECT
    primaryid,
    drugname,

    CASE
        WHEN drugname = 'OZEMPIC' 
             AND dose_mg BETWEEN 0.25 AND 2.0 THEN dose_mg

        WHEN drugname = 'TRULICITY' 
             AND dose_mg BETWEEN 0.75 AND 4.5 THEN dose_mg

        WHEN drugname = 'MOUNJARO' 
             AND dose_mg BETWEEN 2.5 AND 15.0 THEN dose_mg

        ELSE NULL
    END AS dose_mg_clean,

    num_concomitant_drugs

FROM drug_final
""")

print(con.execute("""
SELECT
    drugname,
    COUNT(*) AS total,
    SUM(CASE WHEN dose_mg_clean IS NULL THEN 1 ELSE 0 END) AS null_dose_clean,
    AVG(dose_mg_clean) AS mean_dose_clean,
    MIN(dose_mg_clean) AS min_dose_clean,
    MAX(dose_mg_clean) AS max_dose_clean,
    AVG(num_concomitant_drugs) AS mean_concomitant
FROM drug_final
GROUP BY drugname
ORDER BY drugname
""").df())

con.execute("""
CREATE OR REPLACE TABLE drug_final AS
SELECT
    primaryid,
    drugname,
    dose_mg_clean AS dose_mg,
    num_concomitant_drugs
FROM drug_final
""")
print(con.execute("""
SELECT *
FROM drug_final
LIMIT 5
""").df())

con.execute("""
COPY drug_final
TO 'data/drug_final.parquet'
(FORMAT PARQUET)
""")

print("drug_final.parquet kaydedildi")

#Cleaning and transforming REAC data from FAERS, then saving as Parquet

folder = Path("data/raw_ascii")
con = duckdb.connect("faers.duckdb")

reac_files = [
    folder / "REAC25Q1.txt",
    folder / "REAC25Q2.txt",
    folder / "REAC25Q3.txt",
    folder / "REAC25Q4.txt",
]

for f in reac_files:
    print(f.name, "var mı:", f.exists())

con.execute(f"""
CREATE OR REPLACE TABLE reac_all AS
SELECT *
FROM read_csv(
    {[f.as_posix() for f in reac_files]},
    delim='$',
    header=True,
    all_varchar=True,
    ignore_errors=True
)
""")

print("\n--- REAC_ALL SATIR SAYISI ---")
print(con.execute("""
SELECT COUNT(*) AS n
FROM reac_all
""").df())

print("\n--- REAC_ALL KOLONLAR ---")
print(con.execute("""
DESCRIBE reac_all
""").df())

con.execute("""
CREATE OR REPLACE TABLE reac_clean AS
SELECT DISTINCT
    primaryid,
    UPPER(TRIM(pt)) AS pt
FROM reac_all
WHERE primaryid IS NOT NULL
  AND pt IS NOT NULL
  AND TRIM(pt) <> ''
""")

print("\n--- REAC_CLEAN SAYISI ---")
print(con.execute("""
SELECT COUNT(*) AS n
FROM reac_clean
""").df())

print("\n--- REAC_CLEAN TOP 20 EVENT ---")
print(con.execute("""
SELECT pt, COUNT(*) AS n
FROM reac_clean
GROUP BY pt
ORDER BY n DESC
LIMIT 20
""").df())

con.execute("""
CREATE OR REPLACE TABLE reac_final AS
SELECT
    r.primaryid,
    r.pt
FROM reac_clean r
JOIN drug_final d
ON r.primaryid = d.primaryid
""")

print("\n--- REAC_FINAL SAYISI ---")
print(con.execute("""
SELECT COUNT(*) AS n
FROM reac_final
""").df())

print("\n--- HEDEF İLAÇLARDA TOP 20 EVENT ---")
print(con.execute("""
SELECT pt, COUNT(*) AS n
FROM reac_final
GROUP BY pt
ORDER BY n DESC
LIMIT 20
""").df())

con.execute("""
CREATE OR REPLACE TABLE reac_summary AS
SELECT
    primaryid,
    COUNT(*) AS num_reactions
FROM reac_final
GROUP BY primaryid
""")

print("\n--- NUM_REACTIONS ÖZET ---")
print(con.execute("""
SELECT
    MIN(num_reactions) AS min_reactions,
    AVG(num_reactions) AS mean_reactions,
    MAX(num_reactions) AS max_reactions
FROM reac_summary
""").df())

for drug in ["OZEMPIC", "TRULICITY", "MOUNJARO"]:
    print(f"\n--- {drug} TOP 15 EVENT ---")
    print(con.execute(f"""
    SELECT r.pt, COUNT(*) AS n
    FROM reac_final r
    JOIN drug_final d ON r.primaryid = d.primaryid
    WHERE d.drugname = '{drug}'
    GROUP BY r.pt
    ORDER BY n DESC
    LIMIT 15
    """).df())

    con.execute("""
COPY reac_final
TO 'data/reac_final.parquet'
(FORMAT PARQUET)
""")

con.execute("""
COPY reac_summary
TO 'data/reac_summary.parquet'
(FORMAT PARQUET)
""")

print("REAC parquet dosyaları kaydedildi")

#Creating final_case_analysis table by joining demo_final, drug_final, and reac_summary, then saving as Parquet

folder = Path("data")
con = duckdb.connect("faers_analysis.duckdb")

con.execute(f"""
CREATE OR REPLACE TABLE demo_final AS
SELECT *
FROM read_parquet('{(folder / "demo_final.parquet").as_posix()}')
""")

con.execute(f"""
CREATE OR REPLACE TABLE drug_final AS
SELECT *
FROM read_parquet('{(folder / "drug_final.parquet").as_posix()}')
""")

con.execute(f"""
CREATE OR REPLACE TABLE reac_final AS
SELECT *
FROM read_parquet('{(folder / "reac_final.parquet").as_posix()}')
""")

con.execute(f"""
CREATE OR REPLACE TABLE reac_summary AS
SELECT *
FROM read_parquet('{(folder / "reac_summary.parquet").as_posix()}')
""")

print("Parquet tabloları yüklendi.")
print(con.execute("SELECT COUNT(*) AS n FROM demo_final").df())
print(con.execute("SELECT COUNT(*) AS n FROM drug_final").df())
print(con.execute("SELECT COUNT(*) AS n FROM reac_final").df())
print(con.execute("SELECT COUNT(*) AS n FROM reac_summary").df())

con.execute("""
CREATE OR REPLACE TABLE final_case_analysis AS
SELECT
    d.primaryid,
    d.caseid,

    dr.drugname,
    dr.dose_mg,
    dr.num_concomitant_drugs,

    d.age_years,
    d.weight_kg,
    d.sex,
    d.country,

    rs.num_reactions,

    CASE 
        WHEN EXISTS (
            SELECT 1
            FROM reac_final r
            WHERE r.primaryid = d.primaryid
              AND r.pt = 'NAUSEA'
        )
        THEN 1 ELSE 0
    END AS nausea_binary,

    CASE 
        WHEN EXISTS (
            SELECT 1
            FROM reac_final r
            WHERE r.primaryid = d.primaryid
              AND r.pt = 'VOMITING'
        )
        THEN 1 ELSE 0
    END AS vomiting_binary,

    CASE 
        WHEN EXISTS (
            SELECT 1
            FROM reac_final r
            WHERE r.primaryid = d.primaryid
              AND r.pt = 'DIARRHOEA'
        )
        THEN 1 ELSE 0
    END AS diarrhoea_binary

FROM demo_final d
JOIN drug_final dr
ON d.primaryid = dr.primaryid
JOIN reac_summary rs
ON d.primaryid = rs.primaryid
""")

print("\n--- FINAL CASE ANALYSIS ---")
print(con.execute("""
SELECT COUNT(*) AS n
FROM final_case_analysis
""").df())

print(con.execute("""
SELECT drugname, COUNT(*) AS n
FROM final_case_analysis
GROUP BY drugname
ORDER BY n DESC
""").df())

print(con.execute("""
SELECT *
FROM final_case_analysis
LIMIT 5
""").df())

print("\n--- NAUSEA ORANI ---")
print(con.execute("""
SELECT
    drugname,
    COUNT(*) AS total_cases,
    SUM(nausea_binary) AS nausea_cases,
    AVG(nausea_binary) AS nausea_rate
FROM final_case_analysis
GROUP BY drugname
ORDER BY drugname
""").df())

con.execute("""
COPY final_case_analysis
TO 'data/final_case_analysis.parquet'
(FORMAT PARQUET)
""")

print("final_case_analysis.parquet kaydedildi")


# EDA GRAPHS 

import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_parquet(
    "data/final_case_analysis.parquet"
)

reac = pd.read_parquet(
    "data/reac_final.parquet"
)

print("\n--- FINAL DATASET ---")
print(df.shape)
print(df.head())


# =========================================================
# GRAPH 1 — DRUG DISTRIBUTION
# Supports: RQ4, RQ5, ANOVA
# =========================================================

drug_counts = df["drugname"].value_counts().reset_index()
drug_counts.columns = ["drugname", "n"]

plt.figure(figsize=(7, 5))

plt.bar(drug_counts["drugname"], drug_counts["n"])

plt.xlabel("Drug")
plt.ylabel("Number of Cases")
plt.title("Distribution of Selected GLP-1 Drug Reports")

for i, value in enumerate(drug_counts["n"]):
    plt.text(i, value, str(value), ha="center", va="bottom")

plt.tight_layout()
plt.savefig(
    "figures/eda_1_drug_distribution.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# =========================================================
# GRAPH 2 — AGE DISTRIBUTION BY DRUG
# Supports: RQ1, RQ2
# =========================================================

drug_order = ["MOUNJARO", "OZEMPIC", "TRULICITY"]

age_data = [
    df.loc[df["drugname"] == drug, "age_years"].dropna()
    for drug in drug_order
]

plt.figure(figsize=(7, 5))

plt.boxplot(age_data, labels=drug_order, showfliers=False)

plt.xlabel("Drug")
plt.ylabel("Age (years)")
plt.title("Age Distribution by Drug")

plt.tight_layout()
plt.savefig(
    "figures/eda_2_age_by_drug.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# =========================================================
# GRAPH 3 — WEIGHT DISTRIBUTION BY DRUG
# Supports: Weight ANOVA
# =========================================================

weight_data = [
    df.loc[df["drugname"] == drug, "weight_kg"].dropna()
    for drug in drug_order
]

plt.figure(figsize=(7, 5))

plt.boxplot(weight_data, labels=drug_order, showfliers=False)

plt.xlabel("Drug")
plt.ylabel("Weight (kg)")
plt.title("Weight Distribution by Drug")

plt.tight_layout()
plt.savefig(
    "figures/eda_3_weight_by_drug.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# =========================================================
# GRAPH 4 — TOP 10 ADVERSE EVENTS
# Supports: RQ3, RQ4
# =========================================================

top_events = (
    reac["pt"]
    .value_counts()
    .head(10)
    .sort_values()
    .reset_index()
)

top_events.columns = ["pt", "n"]

plt.figure(figsize=(9, 5.5))

plt.barh(top_events["pt"], top_events["n"])

plt.xlabel("Number of Reports")
plt.ylabel("Adverse Event")
plt.title("Top 10 Reported Adverse Events")

for i, value in enumerate(top_events["n"]):
    plt.text(value, i, str(value), va="center")

plt.tight_layout()
plt.savefig(
    "figures/eda_4_top_adverse_events.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# =========================================================
# GRAPH 5 — NAUSEA RATE BY DRUG
# Supports: RQ3, RQ4
# =========================================================

nausea_rates = (
    df.groupby("drugname")["nausea_binary"]
    .mean()
    .reindex(drug_order)
    .reset_index()
)

nausea_rates["percent"] = nausea_rates["nausea_binary"] * 100

plt.figure(figsize=(7, 5))

plt.bar(nausea_rates["drugname"], nausea_rates["percent"])

plt.xlabel("Drug")
plt.ylabel("Nausea Rate (%)")
plt.title("Reported Nausea Rate by Drug")

for i, value in enumerate(nausea_rates["percent"]):
    plt.text(i, value, f"{value:.1f}%", ha="center", va="bottom")

plt.tight_layout()
plt.savefig(
    "figures/eda_5_nausea_rate_by_drug.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# =========================================================
# GRAPH 6 — NUM_REACTIONS BY DRUG
# Supports: RQ5, Two-way ANOVA
# =========================================================

reaction_data = [
    df.loc[df["drugname"] == drug, "num_reactions"].dropna()
    for drug in drug_order
]

plt.figure(figsize=(7, 5))

plt.boxplot(reaction_data, labels=drug_order, showfliers=False)

plt.xlabel("Drug")
plt.ylabel("Number of Reported Adverse Events")
plt.title("Adverse Event Count Distribution by Drug")

plt.tight_layout()
plt.savefig(
    "figures/eda_6_num_reactions_by_drug.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# =========================================================
# GRAPH 7 — NUM_REACTIONS BY DRUG AND SEX
# Supports: Two-way ANOVA
# =========================================================

mean_reactions_sex = (
    df.groupby(["drugname", "sex"])["num_reactions"]
    .mean()
    .reset_index()
)

pivot = mean_reactions_sex.pivot(
    index="drugname",
    columns="sex",
    values="num_reactions"
).reindex(drug_order)

pivot.plot(kind="bar", figsize=(8, 5))

plt.xlabel("Drug")
plt.ylabel("Mean Number of Adverse Events")
plt.title("Mean Adverse Event Count by Drug and Sex")
plt.xticks(rotation=0)

plt.tight_layout()
plt.savefig(
    "figures/eda_7_num_reactions_by_drug_sex.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.graphics.gofplots import qqplot


# -----------------------------
# Setup
# -----------------------------

OUTPUT_DIR = Path("stat250_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

df = pd.read_parquet("final_case_analysis.parquet")

print("Dataset shape:", df.shape)
print("Columns:")
print(df.columns.tolist())

# ============================================================
# QUESTION 1
# Is the mean age of Ozempic users different from 60 years?
# One-sample t-test
# ============================================================

print("\n" + "=" * 60)
print("QUESTION 1: ONE-SAMPLE T-TEST")
print("=" * 60)

# Select Ozempic users
ozempic = df[df["drugname"].astype(str).str.upper() == "OZEMPIC"].copy()
age = ozempic["age_years"].dropna()

# Reference value
mu0 = 60

# Descriptive statistics
n = len(age)
mean_age = age.mean()
sd_age = age.std(ddof=1)
se_age = sd_age / (n ** 0.5)

# One-sample t-test
t_stat, p_value = stats.ttest_1samp(age, popmean=mu0)

# 95% confidence interval
df_t = n - 1
t_critical = stats.t.ppf(0.975, df_t)
ci_low = mean_age - t_critical * se_age
ci_high = mean_age + t_critical * se_age

# Cohen's d, optional effect size
cohens_d = (mean_age - mu0) / sd_age

# Normality check
normality_stat, normality_p = stats.normaltest(age)

# Print results
print("Sample size:", n)
print("Mean age:", round(mean_age, 3))
print("Standard deviation:", round(sd_age, 3))
print("Standard error:", round(se_age, 3))
print("Reference mean:", mu0)
print("t-statistic:", round(t_stat, 3))
print("Degrees of freedom:", df_t)
print("p-value:", p_value)
print("95% confidence interval:", round(ci_low, 3), "-", round(ci_high, 3))
print("Cohen's d:", round(cohens_d, 3))
print("Normality test p-value:", normality_p)

# Save Q1 table
q1_table = pd.DataFrame({
    "Statistic": [
        "Drug group",
        "Variable",
        "Reference mean",
        "Sample size",
        "Sample mean",
        "Standard deviation",
        "Standard error",
        "t-statistic",
        "Degrees of freedom",
        "p-value",
        "95% CI lower",
        "95% CI upper",
        "Cohen's d",
        "Normality test p-value"
    ],
    "Value": [
        "Ozempic",
        "age_years",
        mu0,
        n,
        mean_age,
        sd_age,
        se_age,
        t_stat,
        df_t,
        p_value,
        ci_low,
        ci_high,
        cohens_d,
        normality_p
    ]
})

q1_table.to_csv(OUTPUT_DIR / "q1_one_sample_ttest_results.csv", index=False)

# Figure 1: Histogram
plt.figure(figsize=(8, 5))
plt.hist(age, bins=30)
plt.axvline(mu0, linestyle="--", linewidth=2, label="Reference age = 60")
plt.axvline(mean_age, linestyle="-", linewidth=2, label=f"Sample mean = {mean_age:.2f}")
plt.xlabel("Age in years")
plt.ylabel("Frequency")
plt.title("Age Distribution of Ozempic Users")
plt.legend()
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "q1_ozempic_age_histogram.png", dpi=300)
plt.close()

# Figure 2: Q-Q plot
plt.figure(figsize=(6, 6))
qqplot(age, line="s", ax=plt.gca())
plt.title("Q-Q Plot of Ozempic Users' Age")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "q1_ozempic_age_qqplot.png", dpi=300)
plt.close()

# ============================================================
# QUESTION 2
# TWO-SAMPLE T-TEST (AGE: OZEMPIC VS TRULICITY)
# ============================================================

import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_parquet("data/final_case_analysis.parquet")

df['drugname'] = df['drugname'].str.upper()
df['sex'] = df['sex'].str.upper()

df_q1 = df[df['drugname'].isin(['OZEMPIC', 'TRULICITY'])].dropna(subset=['age_years', 'drugname'])
ozempic_age = df_q1[df_q1['drugname'] == 'OZEMPIC']['age_years']
trulicity_age = df_q1[df_q1['drugname'] == 'TRULICITY']['age_years']

shapiro_ozempic = stats.shapiro(ozempic_age.head(5000))
shapiro_trulicity = stats.shapiro(trulicity_age.head(5000))
levene_age = stats.levene(ozempic_age, trulicity_age)
t_test_age = stats.ttest_ind(ozempic_age, trulicity_age, equal_var=False)

print("==================================================")
print("QUESTION 2: TWO-SAMPLE T-TEST (AGE: OZEMPIC VS TRULICITY)")
print("==================================================")
print("Shapiro-Wilk Normality Test (Ozempic):", shapiro_ozempic)
print("Shapiro-Wilk Normality Test (Trulicity):", shapiro_trulicity)
print("Levene's Variance Equality Test:", levene_age)
print("Welch's T-Test Result:", t_test_age)
print("==================================================\n")

fig1, ax1 = plt.subplots(figsize=(7, 6))
sns.boxplot(x='drugname', y='age_years', data=df_q1, palette='Set2', ax=ax1)
ax1.set_title('Age Distribution by Drug')
ax1.set_xlabel('Drug')
ax1.set_ylabel('Age (years)')
plt.tight_layout()
plt.savefig("figures/age_distribution_boxplot.png")
plt.close()

df_q2 = df[df['drugname'].isin(['MOUNJARO', 'OZEMPIC', 'TRULICITY'])].dropna(subset=['num_reactions', 'drugname', 'sex'])

model = ols('num_reactions ~ C(drugname) + C(sex) + C(drugname):C(sex)', data=df_q2).fit()
anova_table = sm.stats.anova_lm(model, typ=2)

#Q3 AND Q4 ANALYSIS WERE MADE BY R.


# =========================================================
# RQ5 — MULTIPLE LINEAR REGRESSION ANALYSIS
# Which factors are associated with the number
# of reported adverse events among
# Ozempic, Trulicity, and Mounjaro cases?
# =========================================================

import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf


df = pd.read_parquet(
    "data/final_case_analysis.parquet"
)

print("\n--- DATASET PREVIEW ---")
print(df.head())

print("\n--- DATASET SHAPE ---")
print(df.shape)


reg_df = df[
    [
        "num_reactions",
        "drugname",
        "age_years",
        "weight_kg",
        "num_concomitant_drugs"
    ]
].dropna()

print("\n--- REGRESSION DATASET SHAPE ---")
print(reg_df.shape)


reg_df["drugname"] = reg_df["drugname"].astype("category")

# Set MOUNJARO as reference category
reg_df["drugname"] = reg_df["drugname"].cat.reorder_categories(
    ["MOUNJARO", "OZEMPIC", "TRULICITY"],
    ordered=True
)
# =========================================================
# MULTIPLE LINEAR REGRESSION MODEL
# =========================================================

model = smf.ols(
    "num_reactions ~ C(drugname) + age_years + weight_kg + num_concomitant_drugs",
    data=reg_df
).fit()

# =========================================================
# PRINT MODEL SUMMARY
# =========================================================

print("\n--- REGRESSION SUMMARY ---")
print(model.summary())

# =========================================================
# CREATE COEFFICIENT DATAFRAME
# =========================================================

coef_df = pd.DataFrame({
    "variable": model.params.index,
    "coef": model.params.values,
    "ci_low": model.conf_int()[0].values,
    "ci_high": model.conf_int()[1].values,
    "p_value": model.pvalues.values
})

# Remove intercept
coef_df = coef_df[
    coef_df["variable"] != "Intercept"
]

# Rename variables for plotting
coef_df["variable"] = coef_df["variable"].replace({
    "C(drugname)[T.OZEMPIC]": "Ozempic vs Mounjaro",
    "C(drugname)[T.TRULICITY]": "Trulicity vs Mounjaro",
    "age_years": "Age",
    "weight_kg": "Weight",
    "num_concomitant_drugs": "Concomitant drugs"
})

# Sort by coefficient size
coef_df = coef_df.sort_values("coef")

# =========================================================
# PRINT COEFFICIENT TABLE
# =========================================================

print("\n--- COEFFICIENT TABLE ---")
print(coef_df)

# =========================================================
# CREATE REGRESSION COEFFICIENT PLOT
# =========================================================

plt.figure(figsize=(9, 5.5))

plt.errorbar(
    coef_df["coef"],
    coef_df["variable"],
    xerr=[
        coef_df["coef"] - coef_df["ci_low"],
        coef_df["ci_high"] - coef_df["coef"]
    ],
    fmt="o",
    capsize=5,
    linewidth=2,
    markersize=7
)

# Zero reference line
plt.axvline(
    0,
    linestyle="--",
    linewidth=1.5
)

# Labels
plt.xlabel("Regression Coefficient", fontsize=12)
plt.ylabel("Predictor", fontsize=12)

# Title
plt.title(
    "Regression Coefficients for Predictors of\nReported Adverse Event Counts",
    fontsize=14,
    pad=15
)

# Grid
plt.grid(
    axis="x",
    linestyle=":",
    alpha=0.5
)

plt.tight_layout()

plt.savefig(
    "figures/regression_coefficient_plot.png",
    dpi=300,
    bbox_inches="tight"
)

print("\n--- GRAPH SAVED ---")
print(
    "figures/regression_coefficient_plot.png"
)

plt.show()

# =========================================================
# QUESTION 6 — ONE-WAY ANOVA FOR WEIGHT


from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.graphics.gofplots import qqplot

# Output folder
OUT = Path("q3_weight_anova_outputs")
OUT.mkdir(exist_ok=True)

# Read data
# Put final_case_analysis.parquet in the same folder as this script.
df = pd.read_parquet("final_case_analysis.parquet")

# Keep only variables needed for this question and remove missing weights
weight_data = df[["drugname", "weight_kg"]].dropna().copy()
weight_data["drugname"] = weight_data["drugname"].astype("category")

print("QUESTION 3: ONE-WAY ANOVA FOR WEIGHT")
print("Research question: Do mean patient weights differ among Mounjaro, Ozempic, and Trulicity users?")
print("Total non-missing observations used:", len(weight_data))

# Missing weight information by drug
missing_table = df.groupby("drugname")["weight_kg"].agg(
    total_cases="size",
    non_missing_weight="count"
).reset_index()
missing_table["missing_weight"] = missing_table["total_cases"] - missing_table["non_missing_weight"]
missing_table["missing_percent"] = 100 * missing_table["missing_weight"] / missing_table["total_cases"]
missing_table.to_csv(OUT / "q3_weight_missing_by_drug.csv", index=False)

# Descriptive statistics
desc = weight_data.groupby("drugname", observed=False)["weight_kg"].agg(
    count="count",
    mean="mean",
    std="std",
    median="median",
    min="min",
    max="max"
).reset_index()
desc.to_csv(OUT / "q3_weight_descriptives_by_drug.csv", index=False)

print("\nDescriptive statistics by drug:")
print(desc.round(3))

# One-way ANOVA
model = smf.ols("weight_kg ~ C(drugname)", data=weight_data).fit()
anova_table = anova_lm(model)
anova_table.to_csv(OUT / "q3_weight_one_way_anova.csv")

print("\nOne-way ANOVA table:")
print(anova_table)

# Assumption checks
# Levene test for equal variances
groups = [group["weight_kg"].values for _, group in weight_data.groupby("drugname", observed=False)]
levene_stat, levene_p = stats.levene(*groups, center="median")

# Normality test on residuals
resid = model.resid
normal_stat, normal_p = stats.normaltest(resid)

assumptions = pd.DataFrame({
    "Assumption check": ["Levene test for equal variances", "Residual normality test"],
    "Statistic": [levene_stat, normal_stat],
    "p-value": [levene_p, normal_p]
})
assumptions.to_csv(OUT / "q3_weight_assumption_checks.csv", index=False)

print("\nAssumption checks:")
print(assumptions)

# Tukey multiple comparisons among drug groups
tukey = pairwise_tukeyhsd(
    endog=weight_data["weight_kg"],
    groups=weight_data["drugname"],
    alpha=0.05
)
print("\nTukey multiple comparisons:")
print(tukey)

tukey_table = pd.DataFrame(
    data=tukey._results_table.data[1:],
    columns=tukey._results_table.data[0]
)
tukey_table.to_csv(OUT / "q3_weight_tukey_comparisons.csv", index=False)

# Graph 1: Boxplot
order = list(desc["drugname"].astype(str))
plt.figure(figsize=(8, 5))
plt.boxplot(
    [weight_data.loc[weight_data["drugname"].astype(str) == drug, "weight_kg"] for drug in order],
    tick_labels=order,
    showfliers=False
)
plt.xlabel("Drug name")
plt.ylabel("Weight (kg)")
plt.title("Distribution of Patient Weight by Drug Group")
plt.tight_layout()
plt.savefig(OUT / "q3_weight_boxplot_by_drug.png", dpi=300)
plt.close()

# Graph 2: Means with 95% confidence intervals
plot_desc = desc.copy()
plot_desc["se"] = plot_desc["std"] / (plot_desc["count"] ** 0.5)
plot_desc["ci_error"] = stats.t.ppf(0.975, plot_desc["count"] - 1) * plot_desc["se"]

plt.figure(figsize=(8, 5))
plt.errorbar(
    plot_desc["drugname"].astype(str),
    plot_desc["mean"],
    yerr=plot_desc["ci_error"],
    fmt="o",
    capsize=5
)
plt.xlabel("Drug name")
plt.ylabel("Mean weight (kg)")
plt.title("Mean Patient Weight by Drug Group with 95% CI")
plt.tight_layout()
plt.savefig(OUT / "q3_weight_mean_ci_by_drug.png", dpi=300)
plt.close()

# Graph 3: Q-Q plot of residuals
plt.figure(figsize=(6, 6))
qqplot(resid, line="s", ax=plt.gca())
plt.title("Q-Q Plot of ANOVA Residuals for Weight")
plt.tight_layout()
plt.savefig(OUT / "q3_weight_residual_qqplot.png", dpi=300)
plt.close()

# Graph 4: residuals vs fitted
plt.figure(figsize=(7, 5))
plt.scatter(model.fittedvalues, resid, alpha=0.25, s=8)
plt.axhline(0, linestyle="--", linewidth=1)
plt.xlabel("Fitted values")
plt.ylabel("Residuals")
plt.title("Residuals vs Fitted Values for Weight ANOVA")
plt.tight_layout()
plt.savefig(OUT / "q3_weight_residuals_vs_fitted.png", dpi=300)
plt.close()

print("\nAll tables and figures were saved in:", OUT.resolve())

# ============================================================
# QUESTION 7
# Does num_reactions differ by drug type, sex, and interaction?
# Two-way ANOVA + Tukey multiple comparisons
# ============================================================

print("\n" + "=" * 60)
print("QUESTION 2: TWO-WAY ANOVA")
print("=" * 60)

anova_data = df[["num_reactions", "drugname", "sex"]].dropna().copy()

# Make sure factors are categorical
anova_data["drugname"] = anova_data["drugname"].astype("category")
anova_data["sex"] = anova_data["sex"].astype("category")

# Create combined group name for boxplot
anova_data["drug_sex"] = (
    anova_data["drugname"].astype(str) + "_" + anova_data["sex"].astype(str)
)

# Descriptive statistics by drug and sex
desc_table = anova_data.groupby(["drugname", "sex"])["num_reactions"].agg(
    count="count",
    mean="mean",
    std="std",
    median="median",
    min="min",
    max="max"
).reset_index()

print("\nDescriptive statistics by drug and sex:")
print(desc_table.round(3))

desc_table.to_csv(OUTPUT_DIR / "q2_descriptive_statistics_by_drug_sex.csv", index=False)

# Two-way ANOVA model
# This corresponds to:
# num_reactions ~ drugname + sex + drugname * sex

model = smf.ols(
    "num_reactions ~ C(drugname) * C(sex)",
    data=anova_data
).fit()

anova_table = anova_lm(model)

print("\nTwo-way ANOVA table:")
print(anova_table)

anova_table.to_csv(OUTPUT_DIR / "q2_two_way_anova_table.csv")

# Assumption checks

# 1. Levene's test for equality of variances
groups_for_levene = [
    group["num_reactions"].values
    for name, group in anova_data.groupby(["drugname", "sex"])
]

levene_stat, levene_p = stats.levene(*groups_for_levene, center="median")

print("\nLevene test for equality of variances:")
print("Levene statistic:", levene_stat)
print("p-value:", levene_p)

# 2. Normality test of residuals
residuals = model.resid
normal_resid_stat, normal_resid_p = stats.normaltest(residuals)

print("\nResidual normality test:")
print("Normality statistic:", normal_resid_stat)
print("p-value:", normal_resid_p)

assumption_table = pd.DataFrame({
    "Assumption check": [
        "Levene test for equal variances",
        "Residual normality test"
    ],
    "Statistic": [
        levene_stat,
        normal_resid_stat
    ],
    "p-value": [
        levene_p,
        normal_resid_p
    ]
})

assumption_table.to_csv(OUTPUT_DIR / "q2_assumption_checks.csv", index=False)

# Tukey multiple comparisons among drug groups
# This is used because the drug effect is significant.

tukey_drug = pairwise_tukeyhsd(
    endog=anova_data["num_reactions"],
    groups=anova_data["drugname"],
    alpha=0.05
)

print("\nTukey multiple comparisons among drug groups:")
print(tukey_drug)

# Save Tukey table
tukey_table = pd.DataFrame(
    data=tukey_drug._results_table.data[1:],
    columns=tukey_drug._results_table.data[0]
)

tukey_table.to_csv(OUTPUT_DIR / "q2_tukey_drug_comparisons.csv", index=False)


# -----------------------------
# Graphs for Question 2
# -----------------------------

# Figure 3: Interaction plot
means = anova_data.groupby(["drugname", "sex"])["num_reactions"].mean().reset_index()

plt.figure(figsize=(8, 5))

for sex_group in means["sex"].unique():
    temp = means[means["sex"] == sex_group]
    plt.plot(
        temp["drugname"].astype(str),
        temp["num_reactions"],
        marker="o",
        linewidth=2,
        label=f"Sex = {sex_group}"
    )

plt.xlabel("Drug name")
plt.ylabel("Mean number of reported reactions")
plt.title("Interaction Plot: Drug Type and Sex")
plt.legend()
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "q2_interaction_plot.png", dpi=300)
plt.close()

# Figure 4: Boxplot by drug-sex group
group_order = sorted(anova_data["drug_sex"].unique())

plt.figure(figsize=(10, 5))
plt.boxplot(
    [anova_data.loc[anova_data["drug_sex"] == group, "num_reactions"] for group in group_order],
    tick_labels=group_order,
    showfliers=False
)

plt.xlabel("Drug-Sex group")
plt.ylabel("Number of reported adverse events")
plt.title("Distribution of Reported Adverse Events by Drug-Sex Group")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "q2_boxplot_drug_sex.png", dpi=300)
plt.close()

# Figure 5: Residual Q-Q plot for ANOVA
plt.figure(figsize=(6, 6))
qqplot(residuals, line="s", ax=plt.gca())
plt.title("Q-Q Plot of ANOVA Residuals")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "q2_anova_residual_qqplot.png", dpi=300)
plt.close()

# Figure 6: Residuals vs fitted values
plt.figure(figsize=(7, 5))
plt.scatter(model.fittedvalues, residuals, alpha=0.25, s=8)
plt.axhline(0, linestyle="--", linewidth=1)
plt.xlabel("Fitted values")
plt.ylabel("Residuals")
plt.title("ANOVA Residuals vs Fitted Values")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "q2_residuals_vs_fitted.png", dpi=300)
plt.close()


# -----------------------------
# Final message
# -----------------------------

print("\n" + "=" * 60)
print("Analysis completed.")
print("All tables and figures were saved in this folder:")
print(OUTPUT_DIR.resolve())
print("=" * 60)