import json
import os
import re
import time
import random
from datetime import datetime, timedelta
from groq import Groq
from faker import Faker

fake   = Faker()
client = Groq(api_key="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")
MODEL = "openai/gpt-oss-20b"

OUTPUT_DIR = "full_dataset"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMPANY = "Veltrix Systems"

LEADERSHIP = [
    ("Robert", "CTO"),
    ("Susan", "VP Engineering"),
    ("Ananya", "VP Product"),
    ("Marcus", "CFO"),
]

HR_TEAM = [
    ("Janice", "HR Manager"),
    ("Lindsey", "Talent Acquisition Lead"),
]

CLIENT_SUCCESS = [("Cheryl", "Customer Success Lead")]

PROJECTS = [
    {
        "id":          "orion",
        "name":        "Project Orion",
        "description": "Real-time payment gateway integration replacing the legacy batch-processing system",
        "domain":      "payments",
        "start_date":  "2026-01-12",
        "team": [
            ("Arjun",  "Backend Developer"),
            ("Priya",  "Engineering Manager"),
            ("Karan",  "QA Lead"),
            ("Meera",  "Frontend Developer"),
            ("Rahul",  "DevOps Engineer"),
            ("Sarah",  "Product Manager"),
            ("Daniel", "Product Designer"),
        ],
        "new_hire": ("Maya Thompson", "Backend Developer"),
        "new_hire_start": "2026-01-30",
        "vendor": "OmniPay",
        "budget": "$8,000",
        "timeline_weeks": 12,
        "stages": [
            {"pct": 8,  "event": "Project kickoff. 12-week timeline set. Evaluating OmniPay vs SecurePay as payment provider."},
            {"pct": 17, "event": "OmniPay selected (1.8% fee vs SecurePay 2.3%). Event-driven microservice architecture finalised. Daniel delivers UI mockups."},
            {"pct": 25, "event": "Maya Thompson joins as Backend Developer. Paired with Arjun for ramp-up. HR onboarding complete in 2 days."},
            {"pct": 33, "event": "Core payment service development begins. Maya resolves env setup issue with Arjun's help. Weekly rotating code reviews (Arjun/Priya)."},
            {"pct": 42, "event": "BLOCKER: OmniPay sandbox credentials misconfigured. 3-day delay. QA start pushed from 15th to 18th. Maya reassigned to transaction logging."},
            {"pct": 50, "event": "Blocker resolved. Integration testing started. 20% testing complete. Maya fixes payment token expiration bug."},
            {"pct": 58, "event": "BUGS FOUND: ORION-123 (refund amount calc) and ORION-124 (payment gateway config). Priya escalates to Robert and Susan. Maya assigned ORION-124."},
            {"pct": 67, "event": "Both bugs fixed and QA verified. Test coverage 92%, target 95%. Staging deployment scheduled for next morning 10am EST. Sarah updates Cheryl."},
            {"pct": 75, "event": "Staging deployment successful. Full regression pass clean. Production deployment targeted next sprint Oct 15. Maya formally signed off as ramped up."},
        ],
    },
    {
        "id":          "atlas",
        "name":        "Project Atlas",
        "description": "Customer support ticketing platform migration from legacy tool to HelpStack",
        "domain":      "customer-support",
        "start_date":  "2026-02-02",
        "team": [
            ("Vikram", "Backend Developer"),
            ("Naomi",  "Engineering Manager"),
            ("Felix",  "QA Lead"),
            ("Olga",   "Frontend Developer"),
        ],
        "new_hire": ("Tariq Hassan", "Frontend Developer"),
        "new_hire_start": "2026-02-23",
        "vendor": "HelpStack",
        "budget": "$15,000",
        "timeline_weeks": 10,
        "stages": [
            {"pct": 10, "event": "Project kickoff. Evaluating HelpStack vs DeskWise. 10-week timeline. Budget $15,000."},
            {"pct": 20, "event": "HelpStack selected over DeskWise (better webhook support despite DeskWise being cheaper). API rate limit 500 req/min confirmed sufficient for 200 tickets/day."},
            {"pct": 30, "event": "Tariq Hassan joins as Frontend Developer. 3-day laptop delay from hardware shipping. Naomi pairs Tariq with Olga for first 2 weeks."},
            {"pct": 40, "event": "Webhook integration 35% done. 7 of 12 event types implemented. Team chooses exponential backoff for retries over fixed-interval."},
            {"pct": 48, "event": "INCIDENT: HelpStack 6-hour API outage blocks testing. 1.5-day delay estimated. Naomi escalates to HelpStack support. Decision: no vendor switch for single outage."},
            {"pct": 56, "event": "BUG: Customer email mismapping during ticket sync — 8% of test tickets affected, none in production. Tariq assigned first solo fix. Naomi escalates to Robert given data sensitivity."},
            {"pct": 64, "event": "Bug fixed. Timeline slips 4 days total (outage + bug). Revised completion April 17 (from April 13). Naomi proactively informs leadership."},
            {"pct": 75, "event": "Staging complete and stable. Tariq recognised for ramping up fast and fixing critical bug solo. Susan approves keeping revised April 17 date vs rushing."},
        ],
    },
    {
        "id":          "nova",
        "name":        "Project Nova",
        "description": "Internal analytics dashboard replacing 12 separate spreadsheets with a unified real-time reporting platform",
        "domain":      "analytics",
        "start_date":  "2026-01-20",
        "team": [
            ("Deepa",   "Data Engineer"),
            ("Sanjay",  "Engineering Manager"),
            ("Pooja",   "Frontend Developer"),
            ("Ravi",    "QA Lead"),
            ("Sneha",   "Product Manager"),
        ],
        "new_hire": ("Carlos Mendez", "Data Analyst"),
        "new_hire_start": "2026-02-10",
        "vendor": "Tableau Embedded",
        "budget": "$22,000",
        "timeline_weeks": 16,
        "stages": [
            {"pct": 6,  "event": "Kickoff. Replace 12 spreadsheets (Finance, HR, Ops, Sales, Engineering). 16-week timeline. Budget $22,000. Sanjay leads."},
            {"pct": 13, "event": "Data schema design complete. 47 distinct KPIs identified across 6 departments. Tableau Embedded chosen over Power BI (better API flexibility)."},
            {"pct": 20, "event": "Carlos Mendez joins as Data Analyst. MBA background. Paired with Deepa for ramp-up on the data pipeline."},
            {"pct": 28, "event": "ETL pipeline 60% complete. Finance and HR data connectors live. Sales connector blocked pending CRM access approval from Marcus (CFO)."},
            {"pct": 35, "event": "CRM access granted after 5-day wait. Sales connector complete. All 6 data sources now feeding into the pipeline. Real-time refresh set to every 15 minutes."},
            {"pct": 43, "event": "Dashboard UI prototype delivered by Pooja. Finance team review: 3 requested KPI changes (gross margin calculation, headcount rollup, budget variance display)."},
            {"pct": 51, "event": "KPI changes implemented. Ravi's QA team begins data accuracy testing. 2 data discrepancies found in the HR headcount connector (holiday leave exclusion bug)."},
            {"pct": 62, "event": "Headcount bug fixed. Sneha demos to Ananya (VP Product) and Marcus. Both approve. Ananya requests one addition: executive summary email digest daily at 8am."},
            {"pct": 75, "event": "Email digest feature built and tested. Full dataset accuracy at 99.2% vs source spreadsheets. Staging deployment complete. Production rollout scheduled for next sprint."},
        ],
    },
    {
        "id":          "sentinel",
        "name":        "Project Sentinel",
        "description": "Zero-trust security audit and IAM (Identity and Access Management) overhaul across all internal systems",
        "domain":      "security",
        "start_date":  "2026-01-08",
        "team": [
            ("Donna",   "Security Lead"),
            ("Willie",  "Engineering Manager"),
            ("Sasha",   "Compliance Officer"),
            ("Patrick", "DevOps Engineer"),
        ],
        "new_hire": ("Yuki Tanaka", "Security Analyst"),
        "new_hire_start": "2026-02-01",
        "vendor": "Okta",
        "budget": "$35,000",
        "timeline_weeks": 20,
        "stages": [
            {"pct": 5,  "event": "Kickoff. External audit flagged 3 critical gaps: outdated SSO, no MFA enforcement, 47 over-privileged service accounts. 20-week remediation timeline. Budget $35,000."},
            {"pct": 12, "event": "Okta selected as IAM provider (vs Azure AD — better API for programmatic access provisioning). Donna leads. Patrick handles infrastructure migration."},
            {"pct": 20, "event": "Yuki Tanaka joins as Security Analyst. Former SOC analyst background. Assigned to audit the 47 service accounts and reduce to least-privilege model."},
            {"pct": 28, "event": "Yuki reduces 47 over-privileged service accounts to 12 (74% reduction). MFA enforcement policy drafted and reviewed by Sasha for compliance alignment."},
            {"pct": 38, "event": "ISSUE: MFA rollout blocked by 3 legacy systems incompatible with Okta (billing system, warehouse management, and the payroll tool). Willie escalates to Robert."},
            {"pct": 46, "event": "Robert approves emergency $8,000 additional budget for legacy system adapters. Patrick begins building SAML bridge for billing system (first of three)."},
            {"pct": 55, "event": "SAML bridge for billing complete and tested. Warehouse management adapter 50% done. Payroll tool adapter design in progress. Yuki completes quarterly access review — 0 violations found."},
            {"pct": 64, "event": "All 3 adapters complete. MFA now enforced across 100% of internal systems. Sasha submits compliance report to external auditor for re-verification."},
            {"pct": 75, "event": "External auditor confirms all 3 critical gaps resolved. Sentinel status: AUDIT PASSED. Donna presents final report to Robert and Susan. Project 75% done — ongoing monitoring phase begins."},
        ],
    },
    {
        "id":          "phoenix",
        "name":        "Project Phoenix",
        "description": "Full migration of legacy on-premise infrastructure to AWS cloud (EC2, RDS, S3, CloudFront)",
        "domain":      "infrastructure",
        "start_date":  "2025-12-01",
        "start_note":  "started Dec 2025, ongoing",
        "team": [
            ("Ravi",     "DevOps Lead"),
            ("Kamala",   "Engineering Manager"),
            ("Ben",      "Backend Developer"),
            ("Preethi",  "QA Lead"),
        ],
        "new_hire": ("Lior Cohen", "Cloud Engineer"),
        "new_hire_start": "2026-01-15",
        "vendor": "AWS",
        "budget": "$120,000",
        "timeline_weeks": 36,
        "stages": [
            {"pct": 8,  "event": "Kickoff Dec 2025. Migrate 14 on-prem servers to AWS. 36-week timeline. Budget $120,000. Kamala leads. Critical constraint: zero production downtime."},
            {"pct": 15, "event": "Architecture finalized. Blue-green deployment strategy chosen over big-bang migration (zero-downtime requirement). AWS Landing Zone configured."},
            {"pct": 22, "event": "Lior Cohen joins Jan 2026 as Cloud Engineer. Former AWS Solutions Architect. Immediately leads the VPC design and network security group configuration."},
            {"pct": 30, "event": "Dev and staging environments migrated to AWS. First 3 of 14 servers live on EC2. RDS cluster (PostgreSQL 15) provisioned and running. Cost tracking started: $4,200/month vs $11,000/month on-prem."},
            {"pct": 40, "event": "INCIDENT: RDS storage auto-scaling misconfiguration caused 22-minute performance degradation in staging. No production impact. Lior fixes config. Post-mortem completed."},
            {"pct": 48, "event": "8 of 14 servers migrated. S3 bucket structure complete. Data transfer costs higher than estimated: $2,100 vs $800 projected. Marcus (CFO) notified. Still within overall budget."},
            {"pct": 57, "event": "CloudFront CDN live. Page load times improved 340ms on average in testing. Preethi's QA team begins load testing at 3x normal traffic. All 8 migrated servers pass."},
            {"pct": 67, "event": "11 of 14 servers migrated. Remaining 3 are the highest-risk (database primary, auth service, payment processor). Kamala schedules migration for low-traffic Sunday window 2am-6am."},
            {"pct": 75, "event": "12 of 14 servers on AWS. Final 2 (auth service, payment processor) scheduled for next sprint. Monthly AWS cost tracking: $6,800/month vs $11,000/month on-prem — 38% savings on track."},
        ],
    },
]

FORMATS = {
    "slack": {
        "style": "Slack messages: short, informal, abbreviations (btw/lmk/asap), occasional emoji, no subject lines. Multiple short messages per person is realistic.",
        "avg_msgs": 12,
    },
    "whatsapp": {
        "style": "WhatsApp: very casual, typos ok, short bursts, sometimes 2-3 consecutive messages from same person before reply, mobile-first tone.",
        "avg_msgs": 10,
    },
    "email": {
        "style": "Email thread: Subject line in first message, Re: Subject for replies. Formal greeting, sign-off with name. Full sentences. More context than chat.",
        "avg_msgs": 6,
    },
    "meeting_transcript": {
        "style": "Meeting transcript: format as 'Speaker Name: [dialogue]' on each line. Include natural speech patterns, interruptions noted as '[crosstalk]', timestamps every few exchanges like '[00:03:45]'. Realistic meeting flow with agenda, discussion, action items.",
        "avg_msgs": 20,
    },
    "status_report": {
        "style": "Weekly status report document: formal, structured with sections (Executive Summary, Progress This Week, Blockers, Next Steps, Metrics). Written by the PM or EM for leadership consumption.",
        "avg_msgs": 1,
    },
    "hr_communication": {
        "style": "HR communication: professional, empathetic tone. Could be an onboarding email, performance review note, policy clarification, or inter-HR planning message.",
        "avg_msgs": 4,
    },
}


def call_llm(prompt: str, temperature: float = 0.85, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            raw = "".join(ch for ch in raw if ch == "\n" or ch == "\t" or ord(ch) >= 32)
            return raw
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err:
                import re as re_mod
                wait_match = re_mod.search(r'try again in (\d+)m(\d+)', err)
                wait = int(wait_match.group(1)) * 60 + int(wait_match.group(2)) + 10 if wait_match else 150
                print(f"    Rate limit. Waiting {wait}s...")
                time.sleep(wait)
            elif attempt < retries - 1:
                time.sleep(3)
            else:
                raise
    raise RuntimeError("Max retries exceeded")


def safe_json(raw: str) -> list:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [{"sender": "System", "text": raw}]
    except json.JSONDecodeError:
        return [{"sender": "System", "text": raw[:2000]}]


def gen_chat(project: dict, stage: dict, fmt: str, base_time: datetime) -> list:
    """Generate a Slack or WhatsApp conversation for a project stage."""
    team_str = ", ".join(f"{n} ({r})" for n, r in project["team"])
    style    = FORMATS[fmt]["style"]

    # Decide which team members are active this stage
    all_members = project["team"][:]
    if stage["pct"] >= int(project.get("new_hire_start", "2099")[-5:-3] or 99):
        all_members.append(project["new_hire"])

    active = random.sample(all_members, min(4, len(all_members)))
    participants_str = ", ".join(f"{n} ({r})" for n, r in active)

    prompt = f"""Generate a realistic {fmt} conversation for {COMPANY}.

PROJECT: {project['name']} — {project['description']}
CURRENT STAGE ({stage['pct']}% complete): {stage['event']}

PARTICIPANTS IN THIS CONVERSATION: {participants_str}
FULL TEAM FOR CONTEXT: {team_str}

Style: {style}

The conversation should feel natural and reference specific facts from the stage description (names, numbers, dates, decisions). State facts concretely so they are retrievable later.

Generate {FORMATS[fmt]['avg_msgs']} messages. Output ONLY a valid JSON array:
[{{"sender": "Name", "text": "message"}}, ...]
"""
    raw    = call_llm(prompt)
    msgs   = safe_json(raw)
    result = []
    t      = base_time
    for msg in msgs:
        gap = random.randint(1, 15)
        t  += timedelta(minutes=gap)
        result.append({"sender": msg.get("sender","?"), "text": msg.get("text",""), "timestamp": t.strftime("%Y-%m-%d %H:%M:%S")})
    return result


def gen_email_thread(project: dict, stage: dict, base_time: datetime) -> list:
    team_str = ", ".join(f"{n} ({r})" for n, r in project["team"])
    active   = random.sample(project["team"], min(3, len(project["team"])))
    participants_str = ", ".join(f"{n} ({r})" for n, r in active)

    prompt = f"""Generate a realistic internal email thread for {COMPANY}.

PROJECT: {project['name']} — {project['description']}
CURRENT STAGE ({stage['pct']}% complete): {stage['event']}

PARTICIPANTS: {participants_str}
FULL TEAM: {team_str}

Style: {FORMATS['email']['style']}

Include a subject line in the first email. Subsequent messages use "Re: [subject]".
Reference specific facts, numbers, names, and decisions from the stage description.

Generate {FORMATS['email']['avg_msgs']} email exchanges. Output ONLY a valid JSON array:
[{{"sender": "Name", "text": "full email content including subject and sign-off"}}, ...]
"""
    raw    = call_llm(prompt)
    msgs   = safe_json(raw)
    result = []
    t      = base_time
    for msg in msgs:
        gap = random.randint(30, 180)
        t  += timedelta(minutes=gap)
        if t.hour >= 18:
            t = t.replace(hour=random.randint(8,11), minute=0) + timedelta(days=1)
        result.append({"sender": msg.get("sender","?"), "text": msg.get("text",""), "timestamp": t.strftime("%Y-%m-%d %H:%M:%S")})
    return result


def gen_meeting_transcript(project: dict, stage: dict, base_time: datetime) -> list:
    """Generate a realistic meeting transcript for a project stage."""
    team_str = ", ".join(f"{n} ({r})" for n, r in project["team"])
    active   = random.sample(project["team"], min(5, len(project["team"])))
    participants_str = ", ".join(f"{n} ({r})" for n, r in active)

    meeting_types = [
        "weekly stand-up", "sprint planning", "technical design review",
        "stakeholder update", "retrospective", "blocker resolution call",
        "QA review meeting", "leadership status update", "architecture walkthrough",
    ]
    meeting_type = random.choice(meeting_types)

    prompt = f"""Generate a realistic {meeting_type} meeting transcript for {COMPANY}.

PROJECT: {project['name']} — {project['description']}
CURRENT STAGE ({stage['pct']}% complete): {stage['event']}

ATTENDEES: {participants_str}
FULL PROJECT TEAM FOR CONTEXT: {team_str}

Format: Plain text transcript, NOT JSON.
Use this format for each turn:
[MM:SS] Speaker Name: dialogue

Start with a brief agenda. Include realistic meeting dynamics — questions, 
clarifications, one person getting interrupted, someone asking for action items 
at the end. End with clear action items and owners.

Ground every discussion in the specific facts from the stage description.
Make numbers, names, decisions, and dates explicit. Generate a 15-20 minute 
meeting transcript with natural pauses and cross-talk.
"""
    text = call_llm(prompt, temperature=0.8)

    # Return as single document record
    return [{"sender": "TRANSCRIPT", "text": text, "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S")}]


def gen_status_report(project: dict, stage: dict, base_time: datetime) -> list:
    """Generate a structured weekly status report."""
    # Find the PM or EM
    author = next(
        (f"{n} ({r})" for n, r in project["team"] if "Manager" in r or "PM" in r),
        project["team"][0][0]
    )

    prompt = f"""Write a weekly project status report for {COMPANY} leadership.

PROJECT: {project['name']} — {project['description']}
REPORT DATE: {base_time.strftime("%B %d, %Y")}
AUTHOR: {author}
CURRENT STAGE ({stage['pct']}% complete): {stage['event']}
TEAM: {", ".join(f"{n} ({r})" for n, r in project["team"])}
VENDOR: {project['vendor']} | BUDGET: {project['budget']} | TIMELINE: {project['timeline_weeks']} weeks

Write a formal status report with these exact sections:
## Executive Summary
## Progress This Week
## Key Metrics
## Blockers and Risks
## Next Week's Plan
## Budget Status

Be specific — include names, percentages, dates, bug IDs, decisions made.
This should read like a real weekly report sent to the CTO and VP Engineering.
"""
    text = call_llm(prompt, temperature=0.6)
    return [{"sender": author, "text": text, "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S")}]


def gen_hr_communication(project: dict, stage: dict, base_time: datetime) -> list:
    """Generate HR-related communication around the new hire joining."""
    if stage["pct"] < 20 or stage["pct"] > 45:
        return []  # HR comms only around new hire onboarding stages

    new_hire_name, new_hire_role = project["new_hire"]
    hr_person   = random.choice(HR_TEAM)
    manager     = next((f"{n} ({r})" for n, r in project["team"] if "Manager" in r), project["team"][0][0])

    hr_scenarios = [
        f"onboarding checklist and first-week schedule for {new_hire_name}",
        f"welcome email to {new_hire_name} from HR",
        f"manager check-in after {new_hire_name}'s first week",
        f"30-day onboarding survey results for {new_hire_name}",
        f"IT access request coordination for {new_hire_name}",
    ]
    scenario = random.choice(hr_scenarios)

    prompt = f"""Generate realistic HR communication for {COMPANY}.

CONTEXT: {new_hire_name} recently joined as {new_hire_role} on {project['name']}.
START DATE: {project['new_hire_start']}
SCENARIO: {scenario}
PROJECT STAGE: {stage['event']}
HR PERSON: {hr_person[0]} ({hr_person[1]})
HIRING MANAGER: {manager}

Style: {FORMATS['hr_communication']['style']}

Generate {FORMATS['hr_communication']['avg_msgs']} messages as a JSON array:
[{{"sender": "Name", "text": "message content"}}, ...]

Make it feel authentic — reference the specific project, role, and stage details.
"""
    raw    = call_llm(prompt)
    msgs   = safe_json(raw)
    result = []
    t      = base_time
    for msg in msgs:
        gap = random.randint(20, 240)
        t  += timedelta(minutes=gap)
        if t.hour >= 18:
            t = t.replace(hour=9, minute=0) + timedelta(days=1)
        result.append({"sender": msg.get("sender","?"), "text": msg.get("text",""), "timestamp": t.strftime("%Y-%m-%d %H:%M:%S")})
    return result


STAGE_FORMAT_MAP = {
    (0,  20): (["slack", "email"],             ["whatsapp", "hr_communication"]),
    (20, 40): (["slack", "email", "whatsapp"], ["meeting_transcript", "hr_communication"]),
    (40, 60): (["slack", "email", "meeting_transcript"], ["whatsapp", "status_report"]),
    (60, 80): (["slack", "email", "status_report"],      ["meeting_transcript", "whatsapp"]),
}

def formats_for_stage(pct: int) -> list:
    for (lo, hi), (always, optional) in STAGE_FORMAT_MAP.items():
        if lo <= pct < hi:
            return always + random.sample(optional, 1)
    return ["slack", "email"]


def generate_full_dataset(sleep_between: float = 1.2):
    all_docs = []
    doc_counter = 0

    for project in PROJECTS:
        print(f"\n{'='*60}")
        print(f"  Project: {project['name']}")
        print(f"  {project['description']}")
        print(f"{'='*60}")

        base_date = datetime.strptime(project["start_date"], "%Y-%m-%d")
        history   = "Project just starting."

        for stage in project["stages"]:
            pct    = stage["pct"]
            fmts   = formats_for_stage(pct)
            # Advance the date roughly 1-3 days per stage step
            base_date += timedelta(days=random.randint(3, 8))

            print(f"\n  [{pct}%] {stage['event'][:70]}...")
            print(f"  Formats: {', '.join(fmts)}")

            for fmt in fmts:
                try:
                    if fmt == "slack":
                        messages = gen_chat(project, stage, "slack", base_date)
                    elif fmt == "whatsapp":
                        messages = gen_chat(project, stage, "whatsapp", base_date + timedelta(hours=2))
                    elif fmt == "email":
                        messages = gen_email_thread(project, stage, base_date + timedelta(hours=1))
                    elif fmt == "meeting_transcript":
                        messages = gen_meeting_transcript(project, stage, base_date + timedelta(hours=3))
                    elif fmt == "status_report":
                        messages = gen_status_report(project, stage, base_date + timedelta(hours=5))
                    elif fmt == "hr_communication":
                        messages = gen_hr_communication(project, stage, base_date)
                        if not messages:
                            continue
                    else:
                        continue

                    if not messages:
                        continue

                    doc_id = f"{project['id']}_{pct}pct_{fmt}_{doc_counter:04d}"
                    participants = list(set(m["sender"] for m in messages if m["sender"] != "TRANSCRIPT"))

                    record = {
                        "doc_id":           doc_id,
                        "conversation_id":  doc_id,
                        "project":          project["name"],
                        "project_id":       project["id"],
                        "domain":           project["domain"],
                        "format":           fmt,
                        "platform":         fmt,
                        "stage_title":      stage["event"][:80],
                        "completion_pct":   pct,
                        "participants":     participants,
                        "team":             [n for n, _ in project["team"]],
                        "new_hire":         project["new_hire"][0],
                        "vendor":           project["vendor"],
                        "budget":           project["budget"],
                        "messages":         messages,
                        "metadata": {
                            "source":         "generated",
                            "format":         fmt,
                            "project":        project["name"],
                            "completion_pct": pct,
                            "stage_event":    stage["event"],
                        }
                    }
                    all_docs.append(record)

                    # Save individually
                    fname = f"{OUTPUT_DIR}/{project['id']}_{fmt}_{pct}pct_{doc_counter:04d}.json"
                    with open(fname, "w") as f:
                        json.dump(record, f, indent=2)

                    # Save combined after every document
                    with open(f"{OUTPUT_DIR}/_all_documents.json", "w") as f:
                        json.dump(all_docs, f, indent=2)

                    print(f"    ✓ {fmt} ({len(messages)} messages) → {fname.split('/')[-1]}")
                    doc_counter += 1

                except Exception as e:
                    print(f"    ✗ {fmt} FAILED: {e}")
                    with open(f"{OUTPUT_DIR}/_failed.log", "a") as f:
                        f.write(f"{project['id']} {pct}% {fmt}: {e}\n")

                time.sleep(sleep_between)

            history = stage["event"] 

    print(f"\n{'='*60}")
    print(f"  DONE: {len(all_docs)} documents across {len(PROJECTS)} projects")
    print(f"  Formats: email, slack, whatsapp, meeting transcript, status report, HR")
    print(f"  Output: {OUTPUT_DIR}/_all_documents.json")
    print(f"{'='*60}")
    return all_docs


def print_stats(docs: list):
    from collections import Counter
    print(f"\n{'─'*50}")
    print("DATASET STATISTICS")
    print(f"{'─'*50}")
    print(f"Total documents:  {len(docs)}")
    total_msgs = sum(len(d["messages"]) for d in docs)
    total_words = sum(len(m["text"].split()) for d in docs for m in d["messages"])
    print(f"Total messages:   {total_msgs:,}")
    print(f"Total words:      {total_words:,}")
    print(f"Est. tokens:      {int(total_words * 1.3):,}")
    print(f"Est. chunks(512): {int(total_words * 1.3 // 512)}")
    print()
    fmt_counts = Counter(d["format"] for d in docs)
    print("By format:")
    for fmt, count in sorted(fmt_counts.items()):
        print(f"  {fmt:<22} {count:>4} docs")
    print()
    proj_counts = Counter(d["project"] for d in docs)
    print("By project:")
    for proj, count in sorted(proj_counts.items()):
        print(f"  {proj:<30} {count:>4} docs")
    print(f"{'─'*50}")


if __name__ == "__main__":
    print(f"Generating full multi-format dataset for {COMPANY}")
    print(f"Projects: {len(PROJECTS)} | Formats: email, slack, whatsapp, transcript, status report, HR")
    print(f"Output: ./{OUTPUT_DIR}/\n")

    docs = generate_full_dataset(sleep_between=1.2)
    print_stats(docs)