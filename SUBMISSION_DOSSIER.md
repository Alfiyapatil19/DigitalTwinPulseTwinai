# PHASE 1 OFFICIAL SUBMISSION DOSSIER
**Happiest Health: Reimagining and Reforming Healthcare in India Summit - 2026**  
*Digital Twin Challenge: Proof-of-Concept Prototype Submission*

---

## 1. Team & Institutional Details

* **Project Title:** PULSE-TWIN 2026: An In-Silico Metabolic Digital Twin for Proactive Glycemic Forecasting & Clinical Intervention in Type 2 Diabetes
* **Team Name:** `patilalfiya1`
* **Team Leader:** Alfiya Patil
* **College / University:** AISSMS Institute of Information Technology (AISSMS IOIT), Pune, Maharashtra, India
* **Incubator / Centre of Excellence:** AISSMS IOIT Innovation & Incubation Cell
* **Demo Video Link:** [https://youtu.be/chsFYVFtefM](https://youtu.be/chsFYVFtefM)

---

## 2. Project Title & Executive Summary

### Title:
**PULSE-TWIN 2026: Clinical Metabolic Digital Twin Platform**

### Executive Summary:
PULSE-TWIN 2026 is an in-silico Digital Twin platform engineered to transform diabetes management in India from reactive symptom treatment to proactive physiological forecasting. By executing algorithmic data fusion between **static Electronic Health Records** (108 Synthea C-CDA XML clinical histories) and **high-frequency dynamic wearable streams** (15,731 time-series readings combining Continuous Glucose Monitors and Empatica E4 multi-sensor telemetry), the platform constructs an individualized virtual replica of the patient's unique metabolic state. A trained champion **XGBoost Regressor ($R^2 = 0.987$, $\text{RMSE} = 1.43\text{ mg/dL}$)** forecasts interstitial blood glucose trajectories 30 minutes in advance, proactively triggering **American Diabetes Association (ADA)** risk alerts for impending hypoglycemia crashes ($<54\text{ mg/dL}$) and hyperglycemic spikes ($>180\text{ mg/dL}$). Clinicians can interact with the patient twin via an interactive **Doctor Clinical Dashboard** and a **Whole-Body Metabolic Twin Interface**, utilizing a "What-If" clinical sandbox to simulate meals, insulin boluses, and exercise before adjusting real-world treatment protocols.

---

## 3. Problem Statement & Healthcare Use Case

### The Indian Healthcare Context:
India is widely recognized as the **"Diabetes Capital of the World"**, with over **101 million individuals living with Type 2 Diabetes** and an additional **136 million pre-diabetic individuals** (ICMR-INDIAB study). 

### The Clinical Problem:
Current diabetes care in India is predominantly **reactive and episodic**:
1. **Infrequent Diagnostic Snapshots:** Patients visit outpatient clinics once every 3–6 months for fasting blood glucose and HbA1c tests, missing daily acute glycemic fluctuations.
2. **Fatal Hypoglycemia Crashes:** Severe nocturnal hypoglycemia ($<54\text{ mg/dL}$) causes neuroglycopenic symptoms, loss of consciousness, cardiac arrhythmias, and irreversible brain trauma.
3. **Postprandial Glycemic Surges:** Traditional Indian diets rich in refined carbohydrates (polished white rice, refined wheat flour) cause erratic postprandial spikes ($>200\text{ mg/dL}$), driving microvascular complications (diabetic retinopathy, chronic kidney disease, neuropathy).
4. **Physician Burnout:** India has approximately 1 endocrinologist for every 100,000 diabetic patients. Physicians lack tools to simulate how lifestyle modifications or insulin dosage alterations will impact a specific patient's physiology before writing a prescription.

### The Digital Twin Solution:
PULSE-TWIN establishes a continuous virtual replica of the patient:
* **Proactive Prediction:** Predicts glucose trajectories 30 minutes ahead, giving the patient or doctor actionable warning time to consume fast-acting carbohydrates or adjust basal delivery.
* **Personalized Endocrine Profile:** Models patient-specific Insulin Sensitivity Factors (ISF: $40\text{--}60\text{ mg/dL/U}$) and Insulin-to-Carbohydrate Ratios (ICR: $10\text{--}15\text{ g/U}$).
* **What-If Clinical Sandbox:** Enables doctors to run risk-free in-silico trials (testing meal carbs, insulin units, and physical activity) on the digital twin.

---

## 4. Technical Stack, AI/ML Architecture & Frameworks

### Technology Stack Matrix:
| Layer | Technologies & Tools | Purpose |
|:---|:---|:---|
| **Backend & API** | Python 3.10+, Flask RESTful Service, PyMySQL | High-performance asynchronous REST endpoints, session routing |
| **Database** | MySQL 8.0 Relational Engine (InnoDB) | Normalized schema for patients, SNOMED conditions, RxNorm meds, and 15k+ time-series IoT records |
| **Data Ingestion** | Python `xml.etree.ElementTree`, Pandas, NumPy | Repeatable, idempotent C-CDA XML parser and GlucoBench CSV ingestion pipeline |
| **AI / ML Framework** | XGBoost 2.0+, Scikit-Learn 1.4+, Joblib | Gradient-boosted decision tree regressor, temporal lag & velocity feature engineering |
| **Clinical Rules Engine** | Python ADA Decision Support Module | Clinical classification for Level 1/2 Hypo, Hyper, and rate-of-change alerts |
| **Frontend UI** | HTML5, Modern Vanilla CSS3, JavaScript (ES6+), Chart.js 4.4 | Glassmorphism dashboard, multi-signal synchronized time-series curves, responsive layouts |
| **Hardware Emulation** | SVG Vector Hologram, CSS Neon Shaders | Dynamic metabolic avatar, smartwatch & continuous sensor patch mockups |

### Algorithmic ML Architecture:
1. **19-Dimensional Feature Engineering Pipeline:**
   * **Temporal Autoregressive Lags:** $G(t)$, $G(t-5\text{m})$, $G(t-15\text{m})$, $G(t-30\text{m})$, 1-hour rolling mean.
   * **Glycemic Dynamics:** First-derivative velocity ($\frac{\Delta G}{\Delta t}$) and second-derivative acceleration ($\frac{\Delta^2 G}{\Delta t^2}$).
   * **Multi-Modal Wearable Telemetry:** Heart Rate (BPM), Skin Temperature (°C), Galvanic Skin Response (GSR $\mu\text{S}$), Sympathetic Stress Index (1–5).
   * **Static Patient Physiology:** Baseline HbA1c (%), Patient Age, Weight (kg), Insulin-to-Carb Ratio (ICR), Insulin Sensitivity (ISF).
2. **Model Evaluation & Generalization:**
   * Trained on subjects `U001`–`U008` ($12,596$ readings) and tested strictly on **held-out unseen subjects `U009`–`U010`** ($3,105$ readings) to prevent data leakage.
   * **Champion Model:** **XGBoost Regressor**
     * **Root Mean Squared Error (RMSE):** **$1.432\text{ mg/dL}$**
     * **Mean Absolute Error (MAE):** **$1.049\text{ mg/dL}$**
     * **Coefficient of Determination ($R^2$):** **$0.9873$**
     * **Clarke Error Grid Clinical Accuracy:** **100.0% Zone A** (Zero clinically erroneous predictions).

---

## 5. Minimum 20-Minute Demonstration & Video Recording Script

> **Delivery Guidance:** Record this presentation using PowerPoint / OBS / Zoom, displaying the live web application running at `http://127.0.0.1:5000/`. Upload as an Unlisted YouTube link and provide the URL in your submission portal.

### Video Timeline & Minute-by-Minute Script:

* **[00:00 – 03:00] Slide Presentation: Problem Statement & Vision**
  * Introduce the team, college, and incubator.
  * Frame the Indian diabetes crisis (101M diabetics, episodic care, acute nocturnal hypoglycemia).
  * Introduce the Digital Twin concept: moving from reactive episodic snapshots to real-time proactive in-silico simulation.
* **[03:00 – 06:00] Architectural Overview & Data Provenance**
  * Walk through the two heterogeneous data streams:
    * Static EHR: Synthea 108 HL7 C-CDA XML files with SNOMED-CT diagnoses and RxNorm medications.
    * Dynamic Wearables: 15,731 Kaggle GlucoBench and Empatica E4 multi-sensor rows.
  * Show the database schema (`patients`, `conditions`, `medications`, `twin_profiles`, `glucose_readings`).
  * Emphasize compliance with DPDP Act 2023 and HIPAA (100% synthetic/open-source).
* **[06:00 – 10:00] Machine Learning Engine & Benchmark Walkthrough**
  * Explain the 19-dimensional feature engineering pipeline (lags, velocity, accelerometry, wearable fusion).
  * Present the model benchmark table comparing XGBoost vs. Ridge Regression vs. Random Forest.
  * Highlight the Clarke Error Grid result: 100% in Zone A (clinically safe).
  * Discuss model safety boundaries and clinical limitations (CGM sensor lag, unannounced carbs).
* **[10:00 – 14:30] Live Prototype Demo: Doctor Clinical Dashboard (`/`)**
  * Open browser to `http://127.0.0.1:5000/`.
  * Show the Patient Cohort browser (108 patients, searching, viewing SNOMED-CT conditions and RxNorm prescriptions).
  * Click **"Auto-Stream"** to demonstrate real-time sensor ticks updating glucose and wearable curves.
  * Demonstrate an impending hypoglycemia event and show how the **ADA Proactive Alert** fires with the Rule of 15 recommendation.
  * Open the **"What-If" Simulation Sandbox**: simulate a 45g carbohydrate meal, an insulin bolus correction, and physical exercise; observe the forecasted curve update in real time.
* **[14:30 – 18:00] Live Prototype Demo: Whole-Body Metabolic Twin (`/metabolic-twin`)**
  * Navigate to the Whole-Body Metabolic Twin interface.
  * Show the synchronized Smartwatch (`105 mg/dL ↗`) and Continuous Sensor Patch hardware framing.
  * Explain the holographic anatomical avatar highlighting the Brain (circadian axis), Liver (glycogenolysis), Pancreas ($\beta$-cell ISF), and Muscles (GLUT4 uptake).
  * Show the 24-hour Circadian Rhythm sleep clock, activity waveform, and personalized AI recommendations.
  * Change patients in the selector to prove dynamic database-backed responsiveness across the cohort.
* **[18:00 – 20:00] Conclusion, Impact for India & Q&A Readiness**
  * Summarize clinical benefits: potential to prevent hypoglycemic emergencies and assist endocrinologists in outpatient clinics across tier-2/3 Indian cities.
  * Outline Phase 2 roadmap: automated closed-loop insulin pump integration and vernacular voice-enabled telemedicine alerts.
  * Thank the jury and Happiest Health Summit organizers.

---

## 6. Open-Source License Details

The PULSE-TWIN 2026 platform is licensed under the **MIT Open-Source License**, permitting open academic evaluation, clinical research, and non-commercial development:

```
MIT License
Copyright (c) 2026 Pulse-Twin Project Team
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```
*(Full license text available in the project root file `LICENSE`).*

---

## 7. System Architecture Diagram

```mermaid
flowchart TD
    subgraph DataSources["Heterogeneous Clinical & IoT Data Streams"]
        Synthea["Synthea Synthetic EHR Records<br/>(108 HL7 C-CDA XML Files)"]
        GlucoBench["Kaggle GlucoBench CGM Dataset<br/>(15,731 Time-Series Rows)"]
        Wearables["Wearable Physiological Telemetry<br/>(Empatica E4: HR, TEMP, GSR, Steps)"]
    end

    subgraph Ingestion["Idempotent Data Ingestion Pipeline"]
        SynParser["Synthea XML Parser<br/>(Demographics, SNOMED, RxNorm)"]
        CGMParser["GlucoBench CSV Batch Importer<br/>(Data Validation & Lag Extraction)"]
        TwinPairing["Twin Association Layer<br/>(Explicit Device-to-Patient Pairing)"]
    end

    subgraph Database["MySQL Relational Schema (digital_twin_db)"]
        T_Patients[("`patients` (108 records)")]
        T_Conditions[("`conditions` (3,517 records)")]
        T_Meds[("`medications` (3,841 records)")]
        T_Twins[("`twin_profiles` (108 profiles)")]
        T_Readings[("`glucose_readings` (15,731 records)")]
    end

    subgraph ML["Predictive ML & Decision Support Engine"]
        Features["19-Dim Feature Vector Pipeline<br/>(CGM Lags, Velocity, Acceleration, IoT)"]
        XGBoost["Champion XGBoost Regressor<br/>(RMSE: 1.43 mg/dL, R²: 0.987, Zone A: 100%)"]
        ADA["ADA Clinical Decision Support<br/>(Hypo < 54 mg/dL, Hyper > 180 mg/dL)"]
    end

    subgraph WebServices["Flask RESTful API Layer (app.py)"]
        API_Patients["/api/patients - Cohort Directory"]
        API_Telemetry["/api/twins/id/telemetry - Historical TIR"]
        API_Tick["/api/twins/id/tick - Live Stream & Forecast"]
        API_Sandbox["/api/twins/id/simulate-event - What-If Sandbox"]
        API_Alerts["/api/alerts - Vital Signs Monitoring Center"]
    end

    subgraph UserInterfaces["Dual Clinical User Interfaces"]
        UI_Dashboard["Doctor Clinical Dashboard ('/')<br/>Cohort Browser, Multi-Signal Curves, Sandbox"]
        UI_Metabolic["Whole-Body Metabolic Twin ('/metabolic-twin')<br/>Holographic Avatar, Smartwatch Sync, Circadian Clock"]
    end

    Synthea --> SynParser
    GlucoBench --> CGMParser
    Wearables --> TwinPairing

    SynParser --> T_Patients
    SynParser --> T_Conditions
    SynParser --> T_Meds
    CGMParser --> T_Readings
    TwinPairing --> T_Twins

    T_Readings --> Features
    T_Twins --> Features
    Features --> XGBoost
    XGBoost --> ADA

    T_Patients --> API_Patients
    T_Readings --> API_Telemetry
    ADA --> API_Tick
    API_Tick --> API_Sandbox
    T_Readings --> API_Alerts

    API_Patients --> UI_Dashboard
    API_Telemetry --> UI_Dashboard
    API_Tick --> UI_Dashboard
    API_Sandbox --> UI_Dashboard
    API_Tick --> UI_Metabolic
    API_Alerts --> UI_Dashboard
```

---

## 8. Presentation Master Slide Deck Outline (10-Slide PPT Format)

| Slide # | Slide Title | Key Content & Bullet Points | Visual Element |
|:---:|:---|:---|:---|
| **1** | **Title & Team** | • PULSE-TWIN 2026: Clinical Metabolic Digital Twin Platform<br>• Happiest Health Summit 2026, Bengaluru<br>• Team Name, College & Incubator Affiliation | Summit Logo & High-Tech Hologram Header |
| **2** | **The Crisis: Diabetes in India** | • 101 Million Diabetics + 136 Million Pre-Diabetics<br>• The Fatal Flaw: Reactive, episodic care (3-month HbA1c tests)<br>• Danger: Acute nocturnal hypoglycemia crashes & unchecked postprandial surges | Map of India with Diabetes Prevalence Statistics |
| **3** | **The Solution: In-Silico Digital Twin** | • Continuous virtual patient replica tracking real-time physiology<br>• Dynamic fusion of static hospital EHRs + high-frequency wearable IoT<br>• Proactive forecasting 30 minutes before adverse events occur | Conceptual Diagram: Real Patient $\longleftrightarrow$ Virtual Twin |
| **4** | **System Architecture & Data Streams** | • Stream 1: 108 Synthea C-CDA XML Records (SNOMED-CT, RxNorm)<br>• Stream 2: 15,731 GlucoBench & Empatica E4 Readings (HR, Temp, GSR)<br>• Explicit Pairing Bridge: Zero ID collision assumption | System Architecture Flowchart |
| **5** | **The AI Engine & 19-Dim Feature Pipeline** | • Inputs: CGM Lags ($t, t-5, t-15, t-30$), Velocity, Acceleration, HR, GSR, ISF, ICR<br>• Rigorous Testing: Trained on $U001\text{--}U008$, tested exclusively on unseen $U009\text{--}U010$<br>• Model Comparison: XGBoost vs. Ridge vs. Random Forest | Feature Importance Horizontal Bar Chart |
| **6** | **Clinical Performance Benchmarks** | • RMSE: **$1.43\text{ mg/dL}$** \| MAE: **$1.05\text{ mg/dL}$** \| $R^2$: **$0.987$**<br>• **Clarke Error Grid Analysis: 100% in Zone A** (Clinically Safe)<br>• Transparent Clinical Limitations (CGM sensor lag, unannounced meals) | Clarke Error Grid & Metrics Benchmark Table |
| **7** | **Doctor Clinical Dashboard (`/`)** | • Cohort-wide monitoring across 108 patients<br>• Real-time sensor stream simulation with live Chart.js curves<br>• ADA Clinical Alerts (Level 2 Severe Hypo $<54\text{ mg/dL}$ & Rule of 15 guidance) | Screenshot of Doctor Clinical Dashboard |
| **8** | **The "What-If" Simulation Sandbox** | • Clinicians test interventions before administering to patients<br>• Meal Ingestion ($20\text{g}, 45\text{g}, 75\text{g}$ carbohydrates)<br>• Insulin Boluses ($2\text{U}, 4\text{U}, 7\text{U}$), Physical Exercise, and Acute Stress | Screenshot of Interactive Sandbox in Action |
| **9** | **Whole-Body Metabolic Twin Interface (`/metabolic-twin`)** | • Holographic metabolic avatar showing organ dynamics<br>• Smartwatch synchronization (`105 mg/dL ↗`)<br>• 24h Circadian sleep dial & personalized AI lifestyle recommendations | Screenshot of Tablet & Watch Metabolic View |
| **10** | **Clinical Impact, Compliance & Next Steps** | • 100% DPDP Act 2023 & HIPAA Compliant (Synthetic & Open-source)<br>• Scalable to Indian Tier-2/3 clinics with outpatient telemedicine<br>• Phase 2: Automated closed-loop artificial pancreas integration | Roadmap Timeline & Thank You Callout |
