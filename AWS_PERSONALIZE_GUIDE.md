# AWS Personalize: A Beginner's Guide

## Overview: What Are We Trying to Do?

**Goal**: Use machine learning to rank causes by how much each donor cares about them.

**Why?**: So you can personalize outreach—show ENVIRONMENT to donors who care about the environment, EDUCATION to those who care about education, etc.

**How?**: AWS Personalize learns patterns from your donor behavior history, then predicts rankings for each donor.

---

## The Full Pipeline (6 Steps)

### **Step 1: Prepare Your Data**

You provide CSV files with donor information.

**Required files:**

1. **Donors (USERS)**
```csv
USER_ID,EMAIL,INTEREST_TAG,LTV,LOYALTY_LEVEL,SOURCE
user_0,donor_0@example.com,ENVIRONMENT,32,NEW,FACEBOOK
user_1,donor_1@example.com,EDUCATION,180,REGULAR,ORGANIC
user_2,donor_2@example.com,DISASTER_RELIEF,40,NEW,SMS
```

What each column means:
- `USER_ID`: Unique identifier for the donor (e.g., donor database ID)
- `EMAIL`: Contact info (optional for Personalize, but helpful for you)
- `INTEREST_TAG`: What cause they're interested in (ENVIRONMENT, EDUCATION, etc.)
- `LTV` (Lifetime Value): How much they've donated (dollars)
- `LOYALTY_LEVEL`: Are they new, regular, or lapsed?
- `SOURCE`: How they found you (FACEBOOK, ORGANIC, SMS, EMAIL)

2. **Interactions (What they've done)**
```csv
USER_ID,ITEM_ID,TIMESTAMP,EVENT_TYPE,REFERRED_BY
user_134,ENVIRONMENT,1774696405,DONATE,
user_172,ENVIRONMENT,1769229716,VIEW,
user_161,COMMUNITY_HEALTH,1777663371,VIEW,
user_3,ENVIRONMENT,1778486240,DONATE,
```

What each column means:
- `USER_ID`: Which donor (must match USERS file)
- `ITEM_ID`: Which cause (ENVIRONMENT, EDUCATION, DISASTER_RELIEF, etc.)
- `TIMESTAMP`: When did this happen (Unix timestamp)
- `EVENT_TYPE`: What did they do? (VIEW, DONATE, SIGNUP, CLICK, EMAIL_OPEN)
- `REFERRED_BY`: Where did the referral come from (optional)

**What I do**:
- Check file format is correct
- Upload to AWS S3 (cloud storage)
- Define schemas (tell AWS what each column means)

**Red flags**:
- ❌ Missing donor IDs
- ❌ Timestamps from 1970 or future dates
- ❌ Duplicate rows
- ❌ Empty columns

---

### **Step 2: Set Up Infrastructure in AWS Personalize**

**What this means**: Create a container that organizes your data.

Think of it like:
- You have a filing cabinet (Dataset Group)
- Inside are three drawers: Donors, Interactions, Causes
- Each drawer has a schema (labels for what data goes where)

**What happens**:
1. AWS creates a "Dataset Group" (container for your data)
2. Creates three "Datasets" inside:
   - USERS dataset (200 donors)
   - INTERACTIONS dataset (500 interactions)
   - ITEMS dataset (6 causes)
3. Imports your CSV data into each dataset
4. Indexes it (makes it searchable for training)

**Time**: ~5-10 minutes

**Cost**: Free

**Red flags**:
- ❌ Import job fails (usually due to S3 permissions)
- ❌ Data doesn't match schema
- ❌ Missing required columns

---

### **Step 3: Train a Model (LEARNING)**

**What this means**: AWS analyzes your historical data to learn patterns.

**Analogy**: 
- You're teaching AWS: "Here's 500 interactions from 200 donors. Learn what patterns predict their preferences."
- AWS studies the data and learns: "Donors from FACEBOOK who view ENVIRONMENT tend to also donate to EDUCATION."

**How it works**:

1. **Choose a Recipe** (algorithm)
   
   Different recipes solve different problems:
   
   | Recipe | What it does | Best for |
   |--------|-------------|----------|
   | **Recommendations** | "Which new causes should we suggest?" | Discovering new items |
   | **Personalized Ranking** | "Given these 6 causes, rank them for this donor" | Reordering a fixed list |
   | **Popularity** | "What's trending?" | Baseline (no personalization) |
   
   **Phase 1 choice**: Personalized Ranking v2
   - Why: You have a fixed set of 6 causes
   - Goal: Rank them by relevance for each donor

2. **Create a Solution** (configure the model)
   ```
   Solution Name: donor-ranking-v2
   Recipe: aws-personalized-ranking-v2
   Dataset Group: nonprofit-donors
   ```

3. **Train a Solution Version** (the actual learning)
   - AWS runs machine learning algorithms on your data
   - Finds patterns: "Users like this prefer causes like that"
   - Creates a trained model (file with learned knowledge)
   - **Time**: 10-30 minutes
   - **Cost**: Free (first 2 months)

**What the model learns**:
```
From data, it learns:
  "user_0 interacted with: ENVIRONMENT, EDUCATION"
  "user_1 interacted with: DISASTER_RELIEF, ANIMAL_RESCUE"
  ...
  "Users who care about ENVIRONMENT also care about CLEAN_WATER"
  
Conclusion:
  "For user_0, rank causes: ENVIRONMENT > CLEAN_WATER > ..."
```

**Red flags** (model quality issues):
- ❌ Training takes >1 hour (might be stuck)
- ❌ Model reports 0% coverage (not learning anything)
- ❌ All donors get identical scores (no differentiation)

---

### **Step 4: Get Predictions (INFERENCE)**

**What this means**: Use the trained model to predict rankings for donors.

**Analogy**:
- Step 3: Learning to cook by studying 100 recipes
- Step 4: Actually cooking a meal using what you learned

**How it works**:

**Input**: 
- The trained model from Step 3
- A list of donors to predict for
- For each donor: their causes to rank

**Question**: "For user_0, rank these 6 causes by relevance"

**Output**:
```json
{
  "userId": "user_0",
  "recommendedItems": ["DISASTER_RELIEF", "COMMUNITY_HEALTH", ...],
  "scores": [0.219, 0.188, ...]
}
```

Translation:
- user_0 should rank DISASTER_RELIEF first (score 0.219 = most relevant)
- COMMUNITY_HEALTH second (score 0.188)
- CLEAN_WATER last (score 0.138)

**Two ways to do inference**:

#### **Option A: Real-Time API (Campaign)**
```
├── Create a Campaign (deploy model as live API)
├── When needed, call GetRecommendations("user_0")
├── Get instant response: "For user_0, DISASTER_RELIEF is best"
├── Cost: ~$0.15-0.20/hour minimum (even if unused)
└── Use when: You need recommendations on-demand
```

#### **Option B: Batch Inference** ✓ (What we used)
```
├── Prepare input: All (user, cause) pairs
│   └── 200 users × 6 causes = 1,200 ranking requests
├── Upload to S3
├── Run batch job (asynchronous, in background)
├── Wait 10-15 minutes
├── Download results from S3
├── Cost: $0 (free tier)
└── Use when: You want to predict for many users at once
```

**Time**: 5-15 minutes (batch), instant (real-time)

**Red flags**:
- ❌ Predictions don't make business sense (random rankings)
- ❌ All donors get identical rankings (model didn't learn)
- ❌ S3 permission errors when writing results

---

### **Step 5: Parse Results & Extract Insights**

**What this means**: Convert raw predictions into actionable insights.

**Raw output** (from batch inference):
```json
{"userId": "user_0", "recommendedItems": ["DISASTER_RELIEF", ...], "scores": [0.219, ...]}
{"userId": "user_1", "recommendedItems": ["ANIMAL_RESCUE", ...], "scores": [0.215, ...]}
```

**Transformed into three views**:

#### **Option A: Engagement Scores**
```csv
USER_ID,ENGAGEMENT_SCORE,SEGMENT
user_0,35.4,LOW
user_1,35.3,LOW
user_2,42.1,LOW
```

**What it means**: Composite score (0-100) showing how engaged each donor is overall.

**Use case**: "Which donors should we contact most?"

#### **Option B: Cause Rankings** 
```csv
USER_ID,CAUSE_RANK,CAUSE,SCORE
user_0,1,DISASTER_RELIEF,0.219
user_0,2,COMMUNITY_HEALTH,0.188
user_0,3,ANIMAL_RESCUE,0.170
user_1,1,ANIMAL_RESCUE,0.215
user_1,2,ENVIRONMENT,0.173
```

**What it means**: For each donor, which causes rank highest.

**Use case**: "Personalize our email: Show DISASTER_RELIEF to user_0, ANIMAL_RESCUE to user_1"

#### **Option C: Segments**
```csv
SEGMENT,COUNT,DONOR_IDS
HIGH,47,"user_5; user_12; user_18; ..."
MEDIUM,89,"user_0; user_2; user_7; ..."
LOW,64,"user_3; user_4; user_6; ..."
```

**What it means**: Group donors by engagement level.

**Use case**: "Send different campaigns to HIGH vs LOW engagement donors"

---

### **Step 6: Take Action & Measure Results**

**Use predictions to personalize**:
```
For each donor, use their rankings:

user_0 → Show DISASTER_RELIEF first in email
user_1 → Show ANIMAL_RESCUE first in email
user_2 → Show EDUCATION first in email
```

**Measure impact**:
```
Before personalization:
  All donors see: "Support our causes!"
  Click rate: 5%

After personalization:
  user_0 sees: "Help with Disaster Relief"
  user_1 sees: "Support Animal Rescue"
  Click rate: 8%
  
Lift: +60% improvement
```

**Feedback loop**: If results are bad, revisit data quality (Step 1).

---

## Enriching Your Data Across Platforms

**Question**: Can I combine donor data from multiple sources (Gmail, website, SMS, Meta) to create richer profiles?

**Short answer**: Partially. Here's what you can and cannot do.

### **What You CAN'T Do** ❌

**Can't enrich Meta's data WITH your data**
- You cannot upload Gmail, website, SMS data INTO Meta's platform
- Meta doesn't accept third-party enrichment
- Their algorithm is proprietary; they don't want your data mixed in

**Can't access Meta user data to enrich**
- You can't download Meta user profiles
- You can't combine Meta data with your other sources
- Privacy regulations (GDPR, CCPA) prevent this
- It violates Meta's Terms of Service

### **What You CAN Do** ✓

#### **Option 1: Custom Audience Upload to Meta** (Limited)

```
Your Data:
  ├── Email list of donors
  ├── Phone numbers
  └── Customer IDs

Upload to Meta:
  └── Create "Custom Audience"
  
Meta matches:
  └── "These emails match 40% of our users"
  
Result:
  └── Can target them on Facebook ads
  └── But matched data doesn't flow back to you
```

**How it works**:
1. You upload your donor list (email, phone, hashed IDs)
2. Meta matches them to user accounts
3. You can target "your customers on Facebook"
4. Meta keeps the matching internal (one-way only)

**Limitation**: Data flows TO Meta for targeting, not back to you for enrichment.

#### **Option 2: Combine Data for YOUR OWN Analysis** ✓ (Recommended)

This is what you SHOULD do for Phase 2.

**Data sources you own**:
```
Your Data Sources:
  ├── Website visits (Google Analytics)
  ├── Email opens (Gmail API, Mailchimp, SendGrid)
  ├── SMS responses (Twilio, Postmark, carrier APIs)
  ├── Meta pixel data (ad clicks, conversions)
  ├── Donation records (your CRM/database)
  └── Phone calls (if tracked)

Combine into:
  └── Unified enriched donor profile
  
Use for:
  ├── AWS Personalize training ✓
  ├── Email personalization
  ├── SMS personalization
  └── Your own analytics
```

### **How to Practically Enrich Data** ✓

#### **Step 1: Identify Your Donor Across Platforms**

Use a common identifier (email, phone, or donor ID) to link data:

```
Donor: john@example.com

Google Analytics:
  └── Visited website 5 times, viewed ENVIRONMENT cause pages

Gmail/Email Platform:
  └── Opened 8 emails, clicked 3 links about EDUCATION

SMS (if opted-in):
  └── Opened 10 SMS, responded to 2 about DISASTER_RELIEF

Meta Pixel:
  └── Clicked ad twice (sourced from FACEBOOK)

CRM/Database:
  └── Donated $100, LTV = $250, Loyalty = REGULAR
```

#### **Step 2: Combine into Single Record**

Create a unified user profile:

```csv
USER_ID,EMAIL,WEBSITE_VISITS,EMAIL_OPENS,SMS_OPENS,META_CLICKS,DONATIONS,LTV,SOURCE
john_001,john@example.com,5,8,10,2,2,250,FACEBOOK
```

#### **Step 3: Create Enriched Interactions**

Instead of just one interaction type, track the platform:

```csv
USER_ID,ITEM_ID,TIMESTAMP,EVENT_TYPE,PLATFORM,WEIGHT
john_001,ENVIRONMENT,2026-05-20T10:00:00,EMAIL_OPEN,GMAIL,2.0
john_001,ENVIRONMENT,2026-05-19T14:30:00,WEBSITE_VIEW,WEBSITE,1.0
john_001,EDUCATION,2026-05-18T09:00:00,SMS_OPEN,SMS,2.0
john_001,DISASTER_RELIEF,2026-05-17T15:00:00,META_CLICK,META,1.5
john_001,ENVIRONMENT,2026-05-16T11:00:00,DONATE,DATABASE,5.0
```

#### **Step 4: Train AWS Personalize on Enriched Data**

```
Input: Interactions from 5 sources (Gmail + Website + SMS + Meta + DB)
Model learns: "John engages across channels. Prefers ENVIRONMENT. 
              Responds to EMAIL most, SMS second, web third."
Output: Personalized ranking + insight (which channel works best)
```

**Result**: Better model because it has MORE SIGNALS about each donor.

### **Why This Matters for Phase 2**

**Phase 1 had sparse data**: 500 interactions / 200 donors = 2.5 per donor ❌

**Phase 2 can be enriched**:
- Same 200 donors, but 5,000 interactions
- FROM MULTIPLE SOURCES
- Model learns: "This donor prefers ENVIRONMENT via EMAIL, EDUCATION via SMS"
- Much richer personalization

### **Legal & Privacy Considerations** ⚠️

Before enriching data, verify:

```
✓ GDPR Compliance (Europe):
  - Do you have legal basis to combine data?
  - Users gave informed consent for cross-platform tracking?

✓ CCPA Compliance (California):
  - Users have right to know what data you have
  - Must honor data deletion requests
  - Must clearly disclose data sharing

✓ Your Own Data:
  - Data you collect from your own platforms = yours
  - Website analytics, email opens, SMS = your data
  - Use freely for your own analysis

⚠️ Third-Party Data:
  - Buying/licensing data from other sources has restrictions
  - Verify licensing agreements allow your use case
  - May need additional consent

✓ Email Privacy Act (US):
  - Can track email opens if you sent the email
  - Can't access other people's email accounts

✓ SMS/RCS:
  - Requires explicit opt-in from users
  - Can only track responses they send to you
```

### **Summary: Meta vs AWS for Data Enrichment**

| Capability | Meta | AWS Personalize |
|-----------|------|-----------------|
| Share your data WITH Meta | ✓ Limited (Custom Audiences) | N/A |
| Get Meta data back | ✗ | N/A |
| Combine YOUR data sources | ✗ | ✓ YES |
| Train custom model on combined data | ✗ | ✓ YES |
| Use for personalization | ✗ | ✓ YES |

### **For Your Nonprofit: The Recommended Approach**

**Track 1 (Meta Acquisition)**:
```
Use Meta Lookalikes
  └── Meta handles audience discovery
```

**Track 2 (AWS Retention)**:
```
Combine ALL your data:
  ├── Website visits
  ├── Email opens
  ├── SMS responses
  ├── Meta click data
  └── Donation history

Train AWS Personalize:
  └── Get rankings + insights
```

**Result**: Better personalization because the model sees the full picture of each donor.

---

## Platforms & Tools for Data Enrichment

**Question**: How do I actually combine data from multiple sources? Do I need to hire engineers or buy expensive software?

**Short answer**: Depends on your nonprofit's size and budget. Here are three options.

### **Option A: Customer Data Platforms (CDPs)** 🏢

**What they are**: Software that automatically combines data from all your sources and handles legal compliance.

**Top CDPs** (reviewed for nonprofit use):

| Platform | Cost | Best for | Compliance Built-in |
|----------|------|----------|-------------------|
| **Segment** | $1,200-3,000/mo | Mid-size orgs, API flexibility | GDPR, CCPA ready |
| **mParticle** | $2,000-5,000/mo | Large orgs, heavy integration | GDPR, CCPA, HIPAA |
| **Tealium** | $500-10,000+/mo | Enterprise, data governance | GDPR, CCPA, strict |
| **Salesforce Data Cloud** | $500-5,000+/mo | If you use Salesforce | GDPR, CCPA, HIPAA |
| **Treasure Data** | $1,000-4,000/mo | Asia-Pacific focus | GDPR, CCPA ready |

**Pros** ✓:
- Automatic data combination (you just connect sources)
- Privacy/legal compliance built-in
- No engineering required
- Data quality checks included
- Works with AWS Personalize (can export directly)

**Cons** ✗:
- Expensive ($500-10,000/month is $6k-120k/year)
- Overkill for small nonprofits
- Requires learning their platform

**When to use**: If you have 10,000+ donors and multiple marketing channels actively running.

---

### **Option B: Email-First Platforms** 📧

**What they are**: Email/marketing platforms that also track website and SMS interactions.

**Top email-first platforms**:

| Platform | Cost | Integrations | Data Export |
|----------|------|--------------|------------|
| **Klaviyo** | Free-$1,250/mo | Website, SMS, forms | ✓ Export to CSV |
| **ActiveCampaign** | Free-$229/mo | Website, SMS, CRM | ✓ Export to CSV |
| **HubSpot** | Free-$3,200/mo | Website, SMS, forms | ✓ Export to CSV |
| **ConvertKit** | $25-$99/mo (creators) | Website only | ✓ Limited exports |

**Pros** ✓:
- Much cheaper ($0-3,000/month)
- Email-native (good if email is your primary channel)
- Some have free tiers
- Can export data as CSV for AWS Personalize
- Basic compliance built-in

**Cons** ✗:
- Not designed for data combination (you'll do it manually)
- Limited API access in free tiers
- Focused on email, not cross-platform
- You still need to handle compliance yourself

**When to use**: If email is your primary channel and you want to add SMS/web tracking. Start here if budget is tight.

---

### **Option C: DIY/Hybrid Approach** 🔧

**What it is**: Combine free/cheap tools yourself (Google Analytics, Mailchimp, Twilio, Meta Pixel, your database).

**Free & cheap tools**:

| Tool | Cost | What it tracks |
|------|------|--------|
| **Google Analytics** | Free | Website visits, pages, events |
| **Mailchimp** | Free-$400/mo | Email opens, clicks, list management |
| **Twilio SMS** | $0.01/SMS | SMS sends, opt-in/opt-out |
| **Meta Pixel** | Free | Ad clicks, conversions, referrers |
| **Your database** | Hosting cost | Donation history, LTV |

**Assembly process**:
```
1. Google Analytics → Export web events (weekly)
2. Mailchimp → Export email interactions (weekly)
3. Twilio → Get SMS log via API
4. Meta Pixel → Download conversion report
5. Database → Export donor transactions

Combine all → Single CSV
Upload to AWS Personalize
Train model
```

**Pros** ✓:
- Cheap ($0-500/month total)
- Full control over data
- Works with AWS Personalize
- No vendor lock-in

**Cons** ✗:
- Manual process (need to combine weekly)
- You handle all compliance yourself
- More error-prone (human mistakes)
- Requires technical person (even if just SQL)

**When to use**: If you have <5,000 donors and 1 person who knows SQL/Python.

---

### **Cost Comparison for 1,000 Donors**

| Approach | Monthly Cost | Annual Cost | Time Investment |
|----------|-------------|-----------|-----------------|
| **CDP** | $1,500-3,000 | $18k-36k | 40 hours setup |
| **Email-first** | $100-500 | $1.2k-6k | 20 hours setup + 4 hrs/week |
| **DIY/Hybrid** | $50-200 | $600-2.4k | 4 hours setup + 2 hrs/week |

---

### **What About Using Meta's Platform Suite (Facebook, Instagram, Messenger, WhatsApp)?**

**Question**: Can I just run my nonprofit on Facebook Pages + Instagram + Messenger + WhatsApp, and use that as my unified data platform?

**Short answer**: No. Meta's suite is excellent for **outreach** but doesn't work for **data enrichment**.

#### **Why Meta doesn't work for Track 2 data enrichment**:

**Instagram and Facebook Pages are social platforms, not websites**:
- They're places to post content and build community, not host your actual website
- You still need a separate website (Shopify, WordPress, Wix) for donations and donor info
- Instagram does NOT have "web pages" (it's social-only)

**Meta locks data in; you can't export engagement details**:

| What you want | What Meta gives | Problem |
|---|---|---|
| "John engaged with 5 ENVIRONMENT posts, 2 EDUCATION posts" | "John likes 47 posts, follows you, clicked 3 ads" | Detailed cause preference data stays in Meta |
| Donor interactions across channels | Only conversion events (donation = $X) | Can't see what caused interest |
| Engagement patterns for Personalize training | Facebook Insights dashboard (can't export) | Locked in Meta's system |

**Meta Pixel only tracks conversions, not engagement**:
```
Meta Pixel tells you:
  ✓ Person visited your website
  ✓ Person donated $50
  ✗ Person was interested in ENVIRONMENT
  ✗ Person clicked EDUCATION links
```

**The data flow is one-way TO Meta, not back to you**:
```
Your actions → Meta tracks → Meta builds lookalike audiences
             ↓
          (data stays here)
             ↓
         You get: "I matched your audience to X Facebook users"
         You DON'T get: "Here's engagement data for Personalize"
```

#### **What Meta IS great for** ✓

**Track 1 (Acquisition)**:
```
✓ Run Facebook/Instagram ads to your lookalike audiences
✓ Meta's algorithm optimizes who to show ads to
✓ You get donors, but not their preference data
✓ Perfect for: "Find more people like our existing donors"
```

**Messaging (one-way communication)**:
```
✓ Messenger for donor support 1:1 chats
✓ WhatsApp Business for SMS-like notifications
✓ Good for: "Reach supporters where they are"
✗ But: Doesn't feed into Personalize (it's just messaging)
```

#### **If you use Meta, you STILL need**:

```
1. Separate website (Shopify, WordPress, Wix)
   ├── Install Meta Pixel (for conversion tracking)
   └── Still need Google Analytics for visitor behavior

2. Email (Mailchimp or similar)
   └── Email opens/clicks won't sync from Meta

3. Your database (CRM)
   └── Donation history stays in your system

4. Manual data combination
   └── Just like Option C hybrid—combine all sources yourself
   └── Meta Pixel events feed in, but don't replace email/web/SMS tracking

Result: You've added Meta channel, but still doing manual data integration
```

#### **Bottom line**:

| Use Case | Meta | Other tools |
|----------|------|------------|
| **Track 1: Acquire new donors** | ✓✓✓ (lookalikes) | LinkedIn, Google ads |
| **Track 2: Enrich data for Personalize** | ✗ (data locked in) | RudderStack, email, analytics |
| **Stay in contact** | ✓ (Messenger/WhatsApp) | Email, SMS |
| **See what works** | ✗ (limited insights) | Google Analytics |

**Recommendation**: Use Meta for Track 1 (acquisition), but for Track 2 (data enrichment for Personalize), stick with Option C (hybrid) or RudderStack. Meta's engagement data isn't accessible for your own analysis.

---

### **Decision Framework: Which Should You Use?**

**Use CDP if**:
```
✓ You have 10,000+ donors
✓ Budget is $18k+/year
✓ Multiple teams need access
✓ Compliance is critical (HIPAA, financial data)
✓ You want "set it and forget it"
```

**Use Email-first if**:
```
✓ You have 1,000-10,000 donors
✓ Email is your primary channel
✓ Budget is $1.2k-6k/year
✓ You're comfortable with some manual export
✓ You use Klaviyo or HubSpot already
```

**Use DIY/Hybrid if**:
```
✓ You have <5,000 donors
✓ Budget is $600-2.4k/year
✓ You have one technical person
✓ You're okay with manual weekly pulls
✓ Data is not highly sensitive
```

---

### **Recommended Path for Nonprofits: Start Hybrid, Upgrade Later**

**Phase 1-2** (Current):
```
Budget: <$500/month
Tools: Google Analytics (free) + Mailchimp (free) + Twilio (pay-as-you-go) + your database
Process: Manual export weekly, combine, train
Result: Validate that personalization works
```

**Phase 3** (If Phase 1-2 succeeds):
```
If you see:
  ✓ 30%+ increase in engagement
  ✓ Better donor retention
  ✓ Positive ROI on personalization
  
Then upgrade to:
  - Email-first platform (Klaviyo): +$500/month
  - Or light CDP (Segment): +$1,500/month
```

**Why**: No point paying $18k/year for a CDP before proving the model works.

---

### **Privacy & Legal Compliance Checklist** ⚠️

**Before combining data, verify**:

#### **For US nonprofits**:
```
Email Privacy Act (federal law):
  ✓ Can you track emails you send? YES
  ✓ Unsubscribe link required? YES
  ✓ Can you access unopened emails? NO

CCPA (if donors in California):
  ✓ Users can request data deletion? YES
  ✓ Must disclose data sharing? YES
  ✓ Need privacy policy updated? YES

SMS/RCS (Twilio, carrier APIs):
  ✓ Opt-in required? YES (TCPA law)
  ✓ Can you text back? Only if they initiate
  ✓ Do not spam? Obvious but legally required

CAN-SPAM (marketing emails):
  ✓ Honest subject line? YES
  ✓ From address valid? YES
  ✓ Unsubscribe easy? YES
```

#### **For nonprofits serving other countries**:
```
GDPR (Europe):
  ✓ Legal basis to collect? (Consent/legitimate interest)
  ✓ Data processing agreement? (If using US vendors)
  ✓ Data retention policy? (Why you keep data)
  ✓ User rights (delete, export, correction)? YES

CASL (Canada):
  ✓ Consent to email? YES
  ✓ Compliance officer required? For some orgs
```

#### **Minimal Compliance Checklist for DIY Approach**:
```
□ Privacy policy mentions: "We combine data from email, website, SMS"
□ Privacy policy has: Data retention, deletion policy, user rights
□ Email footer has: Unsubscribe link (required by law)
□ SMS opt-in: Captured consent in database
□ Do not spam: Segment inactive users, honor unsubscribe
□ Data security: Encryption at rest, access controls
□ Annual review: Check for new regulations
```

**Cost to add**: Lawyer review ~$1-2k (do once/year for nonprofits)

---

### **Example: Nonprofit Implementing Hybrid Approach**

**Scenario**: You have 2,000 donors, tiny tech team.

**Week 1 Setup**:
```
1. Enable Google Analytics on website ($0)
   └── Track: page views, time on site, cause of interest

2. Use Mailchimp free tier ($0)
   └── Track: email opens, clicks, list membership

3. Add Twilio for SMS ($0 setup, pay per SMS)
   └── Track: SMS sends, opt-in status

4. Database exports
   └── Track: donation history, amounts, timing

5. Create weekly export script (Python, 2 hours)
   └── Combines all sources → single CSV
```

**Week 2 Training**:
```
Input: Combined CSV with 2,000 donors × 10 interactions each
Train: AWS Personalize model ($0 free tier)
Result: Rankings for each cause
```

**Week 3 Action**:
```
Output: CSV with "Show ENVIRONMENT to donor_123"
Action: Personalize email campaigns
Measure: Compare open rate before/after
```

**Monthly Maintenance** (2 hours/month):
```
Monday: Export GA data
Tuesday: Export Mailchimp data
Wednesday: Export Twilio data
Thursday: Combine all → single CSV
Friday: Retrain model with latest data
```

**Cost/month**: $20-100 (Twilio SMS charges)
**ROI**: If 5% increase in open rates = more engagement

---

## What Makes a High-Quality Dataset?

### **1. Sufficient Volume**

```
POOR:     500 interactions / 200 donors = 2.5 per donor ❌
GOOD:     5,000 interactions / 200 donors = 25 per donor ✓
EXCELLENT: 50,000 interactions / 200 donors = 250 per donor ✓✓
```

**Why**: Models need enough examples to learn patterns.

**Rule of thumb**: Minimum 5-10 interactions per donor, ideally 20+.

### **2. Signal Strength (Interaction Quality)**

**Problem**: Not all interactions are equal.

```
VIEW      (weak signal)    = "Maybe interested"
CLICK     (medium signal)  = "Interested"
DONATE    (strong signal)  = "Definitely interested"
```

**Fix**: Weight interactions by business value.

```python
# Before (all equal):
interaction_weight = 1.0

# After (value-weighted):
if event_type == "DONATE":
    interaction_weight = 5.0  # 5x more important
elif event_type == "CLICK":
    interaction_weight = 2.0
else:  # VIEW
    interaction_weight = 1.0
```

### **3. Diversity (Different Donors, Different Patterns)**

**Red flag from Phase 1**: All 200 donors scored 33.7-37.1 (identical).

**Good dataset**: Donors differ meaningfully.

```
Check:
  ❌ "All donors have 2-3 interactions"
  ✓ "Donors have 5-50 interactions (range)"
  
  ❌ "Everyone interacted with same 2 causes"
  ✓ "Donors prefer different causes"
  
  ❌ "One mega-donor skews everything"
  ✓ "Range of donation amounts ($10-$1000)"
```

**Why**: If all donors look the same, the model can't personalize.

### **4. Data Coverage (Across Items & Time)**

#### **Item Coverage**
```
❌ POOR:      Only 2 of 6 causes have interactions
✓ GOOD:      All 6 causes represented (each with 30+ interactions)
✓ EXCELLENT: All causes well-represented, even rare ones
```

#### **Temporal Coverage**
```
❌ POOR:      All interactions from one week
✓ GOOD:      Spread across 6+ months
✓ EXCELLENT: Represents seasonal variation (year-round data)
```

**Why**: Interactions should represent different time periods.

### **5. Data Quality (No Bad Data)**

**Check for these issues**:

```sql
-- Missing values
SELECT COUNT(*) FROM interactions WHERE USER_ID IS NULL;
-- Should be 0

-- Duplicates
SELECT USER_ID, ITEM_ID, TIMESTAMP, COUNT(*) 
FROM interactions 
GROUP BY USER_ID, ITEM_ID, TIMESTAMP 
HAVING COUNT(*) > 1;
-- Should be 0

-- Invalid timestamps
SELECT COUNT(*) FROM interactions 
WHERE TIMESTAMP < 0 OR TIMESTAMP > 9999999999;
-- Should be 0

-- Mismatched USER_IDs
SELECT COUNT(*) FROM interactions 
WHERE USER_ID NOT IN (SELECT USER_ID FROM users);
-- Should be 0
```

### **6. Representativeness**

**Question**: Does this data represent your actual donors?

```
❌ POOR:      Only test donors, not real data
✓ GOOD:      Sample of actual donors
✓ EXCELLENT: All donor segments (high/medium/low LTV, all sources)
```

**Why**: If training data is biased, predictions will be biased.

### **7. Business Validation (Ground Truth)**

**Question**: Can you validate predictions?

```
✓ "We tracked which donors responded to ENVIRONMENT emails"
✓ "We know actual donation amounts by cause"
✓ "We surveyed donors about their cause interests"
✗ "We have no idea what donors actually want"
```

**Why**: You need a way to check if predictions are correct.

---

## Data Quality Checklist

Before training, verify:

```
Volume
[ ] At least 5-10 interactions per donor
[ ] At least 50-100 interactions per cause
[ ] Total interactions >> number of donors

Signal
[ ] Interactions weighted by business value (DONATE > CLICK > VIEW)
[ ] Clear definition of what each event type means

Diversity
[ ] Donors have varied interaction patterns (not all identical)
[ ] Causes are preferred by different donors
[ ] Range of engagement levels (lurkers to power donors)

Coverage
[ ] All causes represented (not just 2 of 6)
[ ] All time periods covered (not just one month)
[ ] All donor segments represented

Quality
[ ] No missing values
[ ] No duplicate rows
[ ] No invalid timestamps (year 1900 or 2099)
[ ] USER_IDs in interactions match USERS file
[ ] ITEM_IDs in interactions exist
[ ] Consistent format (user_0 not USER_0 or user0)

Recency
[ ] Data is from last 6-12 months (not ancient history)
[ ] Includes recent activity

Representativeness
[ ] Reflects real donor base, not just test data
[ ] Includes all donation sources (FACEBOOK, ORGANIC, SMS, etc.)
[ ] Includes range of LTV (low, medium, high donors)

Ground Truth
[ ] Can validate: "Did predictions match actual behavior?"
[ ] Have metrics to measure success
```

---

## Common Problems & Solutions

### **Problem: All donors score identically (33.7-37.1)**

**Likely cause**: 
- Too little data (sparse interactions)
- All donors behave the same
- Model not learning patterns

**Solution**:
- Get more data (Phase 2: 5,000 interactions)
- Weight interactions (DONATE > VIEW)
- Check diversity: Do donors actually differ?
- Try different recipe (Recommendations vs Ranking)

### **Problem: Model reports 0% coverage**

**Likely cause**:
- Dataset too small
- Missing required columns
- Schema mismatch

**Solution**:
- Add more interactions
- Verify all required columns present
- Check schema definition

### **Problem: Batch inference takes >30 minutes**

**Likely cause**:
- AWS queue is backed up
- Very large dataset
- Infrastructure issue

**Solution**:
- Retry later
- Use smaller batch first (test with 100 users)
- Check AWS Personalize console for errors

### **Problem: S3 permission errors**

**Likely cause**:
- Bucket policy missing write permissions
- IAM role doesn't have S3 access

**Solution**:
- Add bucket policy for personalize.amazonaws.com
- Verify IAM role has S3 permissions
- Check bucket exists and is accessible

---

## Example: Good vs Poor Dataset

### **POOR Dataset** ❌
```
200 donors, 500 interactions (2.5 per donor)
  └── Too sparse

All from FACEBOOK source
  └── Biased (no ORGANIC, SMS)

Only 2 causes have interactions
  └── Incomplete coverage

One mega-donor with 400 interactions
  └── Skewed

All from March 2024
  └── Not representative

50 donors with 0 interactions
  └── Cold start users

All interactions identical (VIEW)
  └── No signal strength variation

RESULT: Model learns: "Just recommend anything, all donors are the same"
```

### **GOOD Dataset** ✓
```
5,000 donors, 50,000 interactions (10 per donor)
  └── Sufficient data

Balanced sources: FACEBOOK (40%), ORGANIC (35%), SMS (25%)
  └── Representative

All 6 causes well-represented (each 3,000-4,000 interactions)
  └── Complete coverage

Range: min 2, max 500, median 25 interactions per donor
  └── Realistic variance

Spread across 12 months
  └── Captures seasonality

All interactions weighted: DONATE (5x), CLICK (2x), VIEW (1x)
  └── Signal strength variation

RESULT: Model learns: "DISASTER_RELIEF donors differ from EDUCATION donors. Personalize accordingly."
```

---

## Next Steps

1. **Before Phase 2**: Run the data quality checklist above
2. **Analyze your 5,000 interactions**: Check distribution, diversity, coverage
3. **If data is good**: Proceed to Phase 2 training
4. **If data is poor**: Collect more interactions or improve signal weighting

**Questions to answer**:
- Do your donors actually have different preferences? (If not, why use personalization?)
- Is your interaction data rich enough (20+ per donor)?
- Can you validate that predictions match reality?

---

## Summary

| Step | What | Time | Cost | Outcome |
|------|------|------|------|---------|
| 1 | Prepare data (CSV files) | 1 hour | $0 | Clean data in S3 |
| 2 | Setup Personalize infrastructure | 10 min | $0 | Dataset group ready |
| 3 | Train model (Learn patterns) | 20-30 min | $0 | Trained model |
| 4 | Get predictions (Inference) | 10-15 min | $0 (batch) | Rankings for each donor |
| 5 | Extract insights (Parse results) | 5 min | $0 | CSV with scores/segments |
| 6 | Take action (Use predictions) | Ongoing | Varies | Personalized outreach |

**Total time for Phase 1**: ~1 hour + 60 minutes waiting  
**Total cost**: $0 (free tier)
