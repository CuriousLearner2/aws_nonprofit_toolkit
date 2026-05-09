# Product Requirements Document (PRD): AWS Nonprofit Toolkit
**Version:** 1.1 | **Status:** Draft | **Owner:** CuriousLearner2

---

## 1. Executive Summary
Nonprofits face a "Cold Start" problem in donor acquisition: they lack the historical behavioral data required to train modern AI models. This toolkit provides high-fidelity synthetic data and the cloud infrastructure to bridge this gap, enabling optimized acquisition and retention campaigns from day one.

## 2. Core Requirements (The "Dual-Track" Vision)

### R1: High-Fidelity Data Simulation
*   **R1.1 Behavioral Bias:** Generate synthetic interaction streams with tunable "statistical bulges" (20-45%) to mimic real-world demographic preferences. 
    *   *Parameters:* Controlled via `--bias-ratio` (group size) and `CAUSE_BIAS_WEIGHT` (preference intensity).
*   **R1.2 Pareto Distribution:** Wealth and donation amounts must follow a Pareto distribution, ensuring **>80% of total value** is contributed by the VIP segment.
*   **R1.3 Scalability:** Support generation of 1,000,000+ interactions for deep ML training.

### R2: Human-Driven Acquisition (Track 1)
*   **R2.1 Seed Identification:** Allow managers to manually label VIP donors in a "Small Dataset" for Meta synchronization.
*   **R2.2 PII Protection:** Automatically SHA256 hash PII locally before cloud transmission.
*   **R2.3 Meta Integration:** Automated synchronization with Meta Custom Audiences.

### R3: ML-Driven Personalization (Track 2)
*   **R3.1 Behavioral Ingestion:** Sync high-volume interaction logs (Large Dataset) to Amazon S3.
*   **R3.2 Automated Inference:** Use Amazon Personalize to automatically segment donors based on inferred intent (e.g., "The Pragmatist" vs. "The Empath").

## 3. Success Metrics
*   **Signal Strength:** 20% to 45% statistical shift in primary preference.
*   **Wealth Distribution:** >80% of total donation value from the VIP segment.
*   **Sync Reliability:** 100% successful data delivery with exponential backoff handling.
*   **Marketing Impact:** Targeted **4x improvement** in initial conversion rates and ROAS.

## 4. Roadmap (Version 2)
*   **Value-Based Lookalikes (VBL):** Prioritizing digital twins of the highest-contributing donors.
*   **Continuous Feedback Loop:** Integrating real-world data from production databases.
*   **QuickSight Dashboard:** Visual "Donor Growth Command Center."
