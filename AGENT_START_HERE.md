# 🚀 Agent Start Here

**New to this project?** Read this first. It's your roadmap.

---

## TL;DR

This toolkit runs a **dual-track nonprofit growth engine**:
- **Track 1 (Acquisition):** Find new donors using Meta lookalike audiences
- **Track 2 (Retention):** Keep donors engaged using AWS Personalize AI rankings

Both tracks are orchestrated by **Google Antigravity agents** for autonomous execution.

**Current Status:** Track 1 lookalike populating | Track 2 ready for model training

---

## 30-Second Project Overview

### What It Does
1. **Track 1:** Uploads your best VIP donors to Meta → Meta finds 100k+ similar people → you run ads to them
2. **Track 2:** Analyzes your donor behavior history → trains AI model → ranks all donors by engagement → you personalize outreach

### Technology Stack
- **Framework:** Google Antigravity SDK (v0.1.0) for autonomous agents
- **Track 1:** Meta Marketing API (Lookalike Audiences)
- **Track 2:** AWS Personalize (ML-based donor ranking)
- **Infrastructure:** S3, IAM, boto3

### Architecture
```
NonprofitOrchestrator (Central Agent)
├── AcquisitionAgent (Track 1 - Meta pipeline)
└── PersonalizationAgent (Track 2 - Personalize pipeline)
```

---

## Current Project State (2026-05-21)

### Track 1: Acquisition (Finding New Donors)

**Status:** 🟡 Lookalike Building

- ✅ Seed audience created: `VIP_Donors_US_Only` (200 US-based donors)
- ✅ Lookalike audience created: `Lookalike (1%) US`
- ⏳ **Status:** Currently populating (2-4 hours)
- 📍 **Location:** Meta Ads Manager (Sandbox account)
- **Next Step:** Monitor lookalike completion, then use for ad campaigns

**Code Relevant to Track 1:**
- `aws_nonprofit_toolkit/agents/acquisition_agent.py` - The agent
- `aws_nonprofit_toolkit/meta_growth_engine.py` - Underlying utilities
- `QUICKSTART.md` - Section "Track 1: The Acquisition Track"

---

### Track 2: Personalization (Keeping Donors Engaged)

**Status:** 🟢 Infrastructure Ready | ⏳ Ready for Model Training

**What's Complete:**
- ✅ Schema defined (USER_ID, ITEM_ID, TIMESTAMP, EVENT_TYPE)
- ✅ Dataset group created (ACTIVE)
- ✅ Interactions dataset created (ACTIVE)
- ✅ Data imported (500 donor interactions, ACTIVE)
- ✅ IAM role & bucket policy configured

**What's Next (Priority Order):**
1. **Train recommender model** (~10-15 min)
   - Input: Imported interaction dataset
   - Output: Trained model ARN

2. **Generate batch inference** (~5-10 min)
   - Input: Trained model + donor list
   - Output: Ranked donor list with engagement scores

3. **Extract donor segments** (~5 min)
   - Input: Rankings
   - Output: Segmented donors (High/Medium/Low engagement)

**Code Relevant to Track 2:**
- `aws_nonprofit_toolkit/agents/personalization_agent.py` - The agent
- `aws_nonprofit_toolkit/personalize_sync.py` - Data upload
- `aws_nonprofit_toolkit/personalize_batch_inference.py` - Batch prediction
- `aws_nonprofit_toolkit/personalize_segmentation.py` - Segment extraction

---

## Quick Navigation

### For Understanding the Project
1. **High-level architecture?** → `PIPELINE_ARCHITECTURE.md`
2. **How to run it?** → `QUICKSTART.md`
3. **Operations/deployment?** → `OPERATIONS_GUIDE.md`
4. **Agent design?** → Memory file: `agent_architecture_refactor.md`
5. **What's the plan?** → `ROADMAP.md` (phases, timeline, strategy)

### For Track 1 (Acquisition/Meta)
- **Next step:** Check Meta Ads Manager for lookalike status
- **Code to review:** `acquisition_agent.py`, `meta_growth_engine.py`
- **Detailed docs:** `QUICKSTART.md` Section 2

### For Track 2 (Retention/Personalize)
- **Next step:** Train recommender model (see section below)
- **Code to review:** `personalization_agent.py`, `personalize_*.py` scripts
- **Detailed docs:** `QUICKSTART.md` Section 3 + `PIPELINE_ARCHITECTURE.md` Section 5
- **Current status:** Memory file: `track2_actual_status.md`
- **Technical context:** Memory file: `track2_context_for_agent.md`

---

## Running the Next Task: Track 2 Model Training

### 1. Verify Prerequisites
```bash
# Check that import is ACTIVE
cd aws_nonprofit_toolkit
python3 verify_pipeline.py  # (Note: Track 1 verification has API issues; focus on AWS Personalize)
```

### 2. Create & Train Model
```python
import boto3

personalize = boto3.client('personalize', region_name='us-east-1')

# Create solution
solution = personalize.create_solution(
    name='donor-engagement-model',
    datasetGroupArn='arn:aws:personalize:us-east-1:684039303576:dataset-group/nonprofit-donors-1779321550',
    recipeArn='arn:aws:personalize:us-east-1:personalize::recipe/aws-user-personalization'
)

# Train solution version
version = personalize.create_solution_version(solutionArn=solution['solutionArn'])
print(f'Training: {version['solutionVersionArn']}')
print('Wait 10-15 minutes for training to complete...')
```

### 3. Monitor Training
```bash
# Check status in AWS Console or via:
python3 -c "
import boto3
personalize = boto3.client('personalize', region_name='us-east-1')
# Replace ARN below with your solution version ARN
result = personalize.describe_solution_version(solutionVersionArn='<your-arn>')
print(f'Status: {result['solutionVersion']['status']}')
"
```

### 4. Once Training Complete
- Run `personalize_batch_inference.py` to generate predictions
- Run `personalize_segmentation.py` to extract donor segments
- See `QUICKSTART.md` Phase 3-4 for details

---

## Project Layout

```
aws_nonprofit_toolkit/
├── agents/                          # NEW: Autonomous agents
│   ├── orchestrator.py              # Central coordinator
│   ├── acquisition_agent.py         # Track 1 agent
│   └── personalization_agent.py     # Track 2 agent
├── datasets/                        # Sample data
│   ├── small_nonprofit_*.csv
│   └── large_nonprofit_*.csv
├── aws_nonprofit_toolkit/           # Utilities
│   ├── personalize_*.py             # Track 2 scripts
│   ├── meta_growth_engine.py        # Track 1 scripts
│   └── personalize_schema.json
├── .env                             # Credentials (local only)
├── QUICKSTART.md                    # How to run both tracks
├── PIPELINE_ARCHITECTURE.md         # Technical design
├── OPERATIONS_GUIDE.md              # Deployment guide
└── AGENT_START_HERE.md              # <-- YOU ARE HERE
```

---

## Key Decisions & Context

### Why Antigravity Agents?
- **Modularity:** Each track is independent; can run separately or together
- **Async/Await:** Non-blocking, production-ready patterns
- **State Management:** Orchestrator handles Track 1→Track 2 handoff
- **Extensibility:** Easy to add new agents or pipeline stages

### Why Two Tracks?
- **Track 1 (Acquisition):** Finds new donors at scale (Meta's AI)
- **Track 2 (Retention):** Keeps existing donors engaged (AWS ML)
- **Flywheel:** New donors from Track 1 become data for Track 2

### Current Constraints
- **Track 1:** Lookalike is populating (manual wait for status)
- **Track 2:** Awaiting model training (next automated phase)
- **Cost:** All operations within AWS free tier limits

---

## Troubleshooting & Support

### Track 1 Issues
- Lookalike stuck for >4 hours? Check Meta Ads Manager for error message
- Token invalid? Verify `.env` has fresh `META_ACCESS_TOKEN`

### Track 2 Issues
- Import job failed? Check IAM role has S3 access + bucket policy is set
- Training slow? Monitor AWS Personalize console; training time varies with data size

### Questions?
- Architecture: See `PIPELINE_ARCHITECTURE.md`
- Operations: See `OPERATIONS_GUIDE.md`
- Running: See `QUICKSTART.md`
- Agent Design: See memory file `agent_architecture_refactor.md` (in `.claude/projects/.../memory/`)

---

## Success Criteria (For This Session)

- [ ] Understand the dual-track architecture
- [ ] Know where Track 1 (Acquisition) is in its lifecycle
- [ ] Know where Track 2 (Retention) is and what's next
- [ ] Successfully train Track 2 recommender model
- [ ] Generate batch inference predictions
- [ ] Extract donor engagement segments

---

**Ready?** Start with Task 1: [Verify Track 2 Prerequisites & Train Model](#running-the-next-task-track-2-model-training)
