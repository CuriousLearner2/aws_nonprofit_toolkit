# ⚡ Quick Start Guide

Follow these steps to execute the **Dual-Track Pipeline** strategy.

---

## 0. Understanding the Problem

Nonprofits face two core challenges:

1. **Finding new donors** (Acquisition): You have your best donors. How do you find MORE people like them?
2. **Keeping existing donors engaged** (Retention): Of all your donors, which ones are most likely to give again? Which ones need targeted outreach?

This toolkit solves BOTH problems using two different approaches.

---

## 1. Setup

### Create `.env` File

The `.env` file stores your credentials. It must be placed in the `aws_nonprofit_toolkit` directory (the main toolkit folder).

1. **Navigate to the toolkit directory:**
   ```bash
   cd aws_nonprofit_toolkit
   ```

2. **Create `.env` from the example:**
   ```bash
   cp .env.example .env
   ```

3. **Edit the `.env` file** and add your Meta and AWS credentials:
   - `META_ACCESS_TOKEN` - Your Meta System User token
   - `META_AD_ACCOUNT_ID` - Your production ad account ID  
   - `META_SANDBOX_AD_ACCOUNT_ID` - Your sandbox ad account ID
   - AWS credentials (if using Personalize track)

**File location:** `/path/to/aws_nonprofit_toolkit/.env`

**Important:** Never commit this file to git (it's in `.gitignore`). Keep your credentials private.

---

## 2. Track 1: The Acquisition Track (Finding New Donors)

**The Problem**: You have 50 amazing VIP donors. You want to find 100,000 more people just like them.

**How it Works**:
1. You tell the toolkit: "Here are my best 50 VIP donors" (just their emails)
2. The toolkit sends their profile to Meta (Facebook/Instagram parent company)
3. Meta's AI finds 100,000+ people similar to your VIPs — same age, interests, giving patterns, location, etc.
4. You can now run Facebook/Instagram ads ONLY to these lookalike prospects
5. Result: You're advertising only to people most likely to become donors

**Real Example**:
- Seed audience: 50 art museum donors who donated $10k+ in the last year
- Meta lookalike: ~150,000 people in the US with similar demographics and interests
- Ad spend: $5,000 to target just the lookalikes
- Expected new donors: 50-100 from this lookalike pool (much better than random targeting)

**How to Run Track 1**:

1.  **Generate Seed**: Create 2,000 synthetic donors.
    ```bash
    python3 generate_datasets.py --count 2000 --bias-ratio 0.25
    ```
2.  **Sync to Meta (Dry Run)**: Verify your credentials and PII hashing without making a live call.
    ```bash
    python3 meta_growth_engine.py --audience-name "VIP_Seed_Test" --dry-run
    ```
3.  **Sync to Meta (Live)**: Create the audience in your Meta Ad Manager.
    ```bash
    python3 meta_growth_engine.py --audience-name "Donor VIPs Fall 2026"
    ```

**When to use**: When you want to find new donors. Launch campaigns once per month/quarter.

---

## 3. Track 2: The Personalization Track (Keeping Donors Engaged)

**The Problem**: You send emails to 5,000 donors, but only 10% open them. Which 500 people are most likely to open your next email? Which ones should get a call instead of an email?

**How it Works**:
1. You give the toolkit your historical data: "These donors opened emails, attended events, clicked donation links"
2. The toolkit trains an AI model that learns: "Donors like person X tend to open emails on Tuesday evenings"
3. The model ranks your entire donor base by engagement probability
4. Result: You know who to call, who to email, and when to contact them for maximum response

**Real Example**:
- You have 5,000 donors with 2 years of email/event/donation history
- Track 2 analyzes this data and identifies patterns: "Donors aged 55+ are 3x more likely to donate if contacted by phone. Donors aged 25-35 engage most via social media."
- You segment your donors accordingly
- Instead of sending the same email to everyone, you personalize outreach
- Result: 25% higher engagement, 15% more donations

**How to Run Track 2**:

1.  **Validate Behavioral Signal**: Verify the data is strong enough for ML.
    ```bash
    python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv
    ```
2.  **Sync to AWS Personalize**: Upload the data to train the model.
    ```bash
    python3 personalize_sync.py --dataset datasets/large_nonprofit_interactions.csv
    ```

**When to use**: When you want to improve engagement and retention. Run this quarterly as you collect more donor data.

---

## 4. How the Tracks Work Together

| Aspect | Track 1 (Acquisition) | Track 2 (Retention) |
|--------|----------------------|-------------------|
| **Goal** | Find new donors | Keep existing donors engaged |
| **Input Data** | Your best 50-100 donors (seed) | 2+ years of donor behavior |
| **Output** | 100k+ lookalike prospects | Ranked donor list by engagement |
| **Action** | Run ads to lookalikes | Send personalized outreach |
| **Timeframe** | Monthly/quarterly campaigns | Ongoing personalization |
| **Technology** | Meta's AI (lookalikes) | AWS Machine Learning (ranking) |

**Complete Workflow Example**:
1. Month 1: Run Track 1 → Find 100k lookalike prospects → Launch Facebook ads
2. Month 2-3: New donors from ads join your list
3. Quarter 2: Run Track 2 → Analyze behavior of all 5,100 donors → Personalize outreach
4. Month 4+: Use Track 2 insights to retain the new cohort from Track 1

For a deep dive into the technology, see **[PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md)**.
