# Pipeline Architecture: From Cold-Start to Automated Scale
**A Guide to Human-Labeling vs. ML-Inference for Nonprofit Growth**

This document outlines the two distinct data tracks within the AWS Nonprofit Toolkit: the **Acquisition Pipeline** (for finding new donors) and the **Personalization Pipeline** (for retaining existing ones).

---

## 1. The Acquisition Pipeline (Small Dataset)
**Goal:** Finding "Digital Twins" of your best supporters.
**Focus:** Identity and Quality.

### A. The Input: `small_nonprofit_users.csv`
This dataset contains high-level information about your donors (Email, City, Interest Tags).

### B. The Labeling: Human-Driven (Surgical)
*   **The Process:** A nonprofit manager or a CRM rule manually identifies "VIPs."
*   **The Signal:** You decide who is a high-value donor based on your organizational goals (e.g., "Gave > $500" or "Influential Community Leader").
*   **Why Human?** At the start, you don't have enough data for an AI to know who a VIP is. Human intuition and simple business rules are the most accurate way to "seed" the system.

### C. The Service: Meta Lookalike Audiences
*   We upload these **Human-Labeled VIPs** to Meta.
*   Meta’s AI analyzes their millions of social signals to find new people who share the same characteristics.
*   **Result:** A massive audience of potential new donors who "look like" your best existing ones.

---

## 2. The Personalization Pipeline (Large Dataset)
**Goal:** Maximizing the Lifetime Value (LTV) of every donor.
**Focus:** Behavior and Intent.

### A. The Input: `large_nonprofit_interactions.csv`
This dataset is a "stream" of events. Every click, every read, and every "forward" is recorded here as a raw log.

### B. The Labeling: ML-Driven (Inference)
*   **The Process:** **Amazon Personalize** (Machine Learning) reads the raw logs.
*   **The Signal:** The AI "infers" the donor's archetype by spotting patterns too complex for humans to see. It doesn't need you to tell it who is "Eco-Conscious"; it notices that "User 123" always clicks on carbon-offset stories and labels them automatically.
*   **Why ML?** Once you have thousands of donors and millions of clicks, a human can no longer keep up. The AI takes over the labeling at scale.

### C. The Service: Amazon Personalize
*   We feed the raw stream into Amazon Personalize.
*   The service creates **User Segments** (e.g., "The Pragmatist," "The Empath").
*   **Result:** Personalized email campaigns (via Amazon SES) that send the right story to the right person at the right time.

---

## 3. The Growth Flywheel: How they Connect
The power of the toolkit is that the **Small Dataset grows into the Large Dataset** in a continuous loop:

1.  **SEED (Human):** You label 200 VIPs in the **Small Dataset**.
2.  **SCALE (Meta):** Meta uses that seed to bring in **2,000 new donors** via ads.
3.  **STREAM (Activity):** Those 2,000 new donors start clicking and interacting with your content.
4.  **REVEAL (Large):** Their activity creates the **Large Dataset**.
5.  **PERSONALIZE (ML):** Amazon Personalize reads that dataset and ensures those 2,000 donors stay engaged for years, turning them into your next generation of VIPs.

---

## 4. Infrastructure Mapping

| Feature | Acquisition Track (Meta) | Personalization Track (AWS) |
| :--- | :--- | :--- |
| **Dataset** | `small_nonprofit_users.csv` | `large_nonprofit_interactions.csv` |
| **Labeling Method** | **Human/Manual** (CRM Rules) | **Machine Learning** (Inferred) |
| **AWS Orchestrator** | **AWS Lambda** (Syncing to Meta) | **Amazon Athena** (Analyzing Stream) |
| **AI "Brain"** | Meta Lookalike AI | Amazon Personalize |
| **Output** | New Cold Leads (Meta Ads) | Personalized Nurture (Email) |

---
**Summary:** The Acquisition pipeline brings them in the door using your **intuition**; the Personalization pipeline keeps them there using **machine learning**.
