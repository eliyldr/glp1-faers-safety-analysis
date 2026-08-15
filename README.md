# Comparative Safety and Tolerability Analysis of GLP-1 Receptor Agonists
## Real-World Pharmacovigilance Study Using FDA FAERS (2025 Q1–Q4)

### Project Overview
This study presents a comparative, real-world pharmacovigilance analysis of three widely prescribed Glucagon-Like Peptide-1 (GLP-1) receptor agonists: **Ozempic (semaglutide)**, **Mounjaro (tirzepatide)**, and **Trulicity (dulaglutide)**. Utilizing the United States Food and Drug Administration's Adverse Event Reporting System (FDA FAERS) quarterly data from 2025 (Q1–Q4), multi-million-row raw administrative records were extracted, standardized, and curated into an analytical cohort of **27,771 unique patient cases** using DuckDB[cite: 4, 5].

* **Academic Institution:** Middle East Technical University (METU), Department of Statistics[cite: 4]
* **Course:** STAT 250 Applied Statistics (Spring 2025–2026)[cite: 4]
* **Instructor:** Prof. Dr. Berna Burçak Başbuğ Erkan[cite: 4]

---

### Research Questions and Statistical Methodology

1. **Demographic Profile and Age Comparisons**
   - **One-Sample t-Test:** Evaluated whether the mean age of Ozempic users deviates from the clinical reference baseline of 60 years ($\bar{x} = 62.05$, $p < 0.001$)[cite: 4].
   - **Welch’s Two-Sample t-Test:** Compared age distributions between Ozempic and Trulicity cohorts, adjusting for unequal variances confirmed via Levene's test ($p < 0.001$)[cite: 4].

2. **Gastrointestinal Tolerability (Nausea Incidence)**
   - **One-Sample Proportion Test (with Continuity Correction):** Tested the observed nausea rate among Ozempic users against the hypothesized 20% clinical trial baseline ($\hat{p} = 19.67\%$, $\chi^2 = 0.4792$, $p = 0.4886$)[cite: 4].
   - **Two-Sample Proportion Test:** Assessed differences in nausea reporting proportions between Ozempic (19.67%) and Trulicity (21.28%) cohorts ($\chi^2 = 2.943$, $p = 0.08625$)[cite: 4].

3. **Body Weight Disparities Across Cohorts**
   - **One-Way ANOVA:** Assessed differences in mean body weight across the three treatment cohorts ($F(2, 5243) = 44.629$, $p < 0.001$)[cite: 4].
   - **Tukey’s HSD Post-Hoc Analysis:** Identified significantly higher mean body weights in Trulicity users (~108.80 kg) relative to both Mounjaro and Ozempic cohorts ($p < 0.001$)[cite: 4].

4. **Adverse Event Volume and Sex Interaction**
   - **Two-Way Factorial ANOVA:** Analyzed the main effects of drug type ($F = 1235.885$, $p < 0.001$), biological sex ($F = 111.193$, $p < 0.001$), and their interaction ($F = 6.834$, $p = 0.001$) on reported adverse event counts[cite: 4].

5. **Multivariable Determinants of Reporting Complexity**
   - **Multiple Linear Regression (OLS):** Evaluated the independent effects of drug type, age, body weight, and concomitant medication counts on log-transformed adverse event reporting ($R^2 = 0.154$, $F(5, 5240) = 191.0$, $p < 0.001$)[cite: 4]. Polypharmacy demonstrated a significant positive association ($\beta = 0.020$, $p < 0.001$)[cite: 4].

---

### Computational Stack and Implementation

* **Database Engine and Data Engineering:** DuckDB (used for out-of-core merging, filtering primary suspect cases, and standardizing dosage/demographic metrics across multi-gigabyte files)[cite: 4, 5].
* **Statistical Computing:** Python (`statsmodels`, `scipy.stats`, `pandas`) and R (`arrow`, `dplyr`, base `prop.test`)[cite: 3, 5].
* **Diagnostics:** Residual normality tests (Shapiro-Wilk, D’Agostino-Pearson), Levene’s tests for homoscedasticity, Q-Q plots, and residual-versus-fitted analyses[cite: 4, 5].

---

### Data Availability Notice
Due to volume (>10 GB raw data) and licensing restrictions, the underlying raw ASCII quarterly files and full analytical Parquet tables are not hosted in this repository[cite: 4, 5]. The data can be downloaded from the [FDA FAERS Public Dashboard / Quarterly Data Files](https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers/fda-adverse-event-reporting-system-faers-latest-quarterly-data-files). The execution script `final_code_report.py` provides the end-to-end pipeline required to reproduce the dataset from raw source files[cite: 5].

---

### Project Documentation
The complete written academic report is available in this repository:
* [`Stat 250 Project Report Group 21.pdf`](./Stat%20250%20Project%20Report%20Group%2021.pdf)[cite: 4]

### Contributors (Group 21)
* Begüm Somay (2552396)[cite: 4]
* Elif Yıldırım (2613099)[cite: 4]
* Zeynep Gökçe Abaş (2663888)[cite: 4]
* Rabia Görünmez (2612083)[cite: 4]
