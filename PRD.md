# Product Requirements Document (PRD): AWS Nonprofit Toolkit
**Version:** 1.1 | **Status:** Draft | **Owner:** CuriousLearner2

---

## 1. Executive Summary
Nonprofits face a "Cold Start" problem in donor acquisition: they lack the historical behavioral data required to train modern AI models (Meta Lookalikes and Amazon Personalize). This toolkit provides high-fidelity synthetic data and the cloud infrastructure to bridge this gap, enabling nonprofits to launch optimized acquisition and retention campaigns from day one.

## 2. Target Audience
*   **Nonprofit Growth Managers:** Responsible for donor acquisition and ROAS.
*   **Data Engineers/DevOps:** Responsible for deploying the cloud infrastructure and PII masking.
*   **Development Directors:** Interested in high-level donor archetypes and VIP stewardship.

## 3. Core Requirements (The "Dual-Track" Vision)

### R1: High-Fidelity Data Simulation
*   **R1.1 Behavioral Bias:** The system must generate synthetic interaction streams with tunable "statistical bulges" (20-45%) to mimic real-world demographic preferences.
*   **R1.2 Pareto Distribution:** Wealth and donation amounts must follow a Pareto distribution (80/20 rule) to simulate realistic VIP donor segments.
*   **R1.3 Scalability:** Support generation of up to 1,000,000+ interactions for deep ML training.

### R2: Human-Driven Acquisition (Track 1)
*   **R2.1 Seed Identification:** Allow managers to manually label VIP donors in a "Small Dataset" for Meta synchronization.
*   **R2.2 PII Protection:** Automatically SHA256 hash emails and phone numbers before they leave the local environment.
*   **R2.3 Meta Integration:** Automated synchronization with Meta Custom Audiences via the Graph API.

### R3: ML-Driven Personalization (Track 2)
*   **R3.1 Behavioral Ingestion:** Sync high-volume interaction logs (Large Dataset) to Amazon S3 for ML training.
*   **R3.2 Automated Inference:** Use Amazon Personalize to automatically segment donors based on inferred intent (e.g., "The Pragmatist" vs. "The Empath").
*   **R3.3 Content Mapping:** Provide a mechanism to map ML segments to specific email templates (Amazon SES).

### R4: Cloud Infrastructure
*   **R4.1 Serverless Orchestration:** Deploy core logic as AWS Lambda functions triggered by S3 events.
*   **R4.2 Analytics Layer:** Provide Amazon Athena schemas for SQL-based "Bulge Detection" in the data lake.
*   **R4.3 Monitoring:** Track sync success rates and statistical signal strength via CloudWatch.

## 4. Success Metrics
*   **Signal Strength:** >20% delta in Group A vs Group B preference.
*   **Compliance:** Zero unhashed PII records in the cloud.
*   **Marketing Impact:** Targeted **4x improvement** in initial conversion rates (e.g., 0.8% to 3.2%) and a **400% increase in ROAS** through high-signal targeting.

## 5. Roadmap (Version 2)
*   **Value-Based Lookalikes (VBL):** Providing Meta with a "Value Column" (Lifetime Value - LTV) to prioritize finding twins of the highest-contributing donors, targeting a 25% reduction in CPA.
*   **Continuous Feedback Loop:** Integrating real-world donation data from production databases (e.g., Supabase) back into the interaction stream to improve ML accuracy.
*   **QuickSight Dashboard:** Launching a visual "Donor Growth Command Center" to track ROAS, signal strength, and archetype distribution in real-time.
