from config import CALENDAR_LINK, SENDER_NAME, COMPANY_NAME, INSTAGRAM


def get_initial_email(lead_data):
    channel_name = lead_data.get("channel_name", "your channel")
    niche = lead_data.get("niche", "your space")
    subject = f"Quick question about {channel_name}"
    body = f"""Hey,

I came across {channel_name} and noticed you're building a presence in the {niche} space.

I work with founders and coaches who are serious about turning their personal brand into a lead generation machine — not just posting for vanity metrics.

We handle the full stack: video editing, scripting, strategy, and Instagram management. Our clients typically see quality content go from inconsistent to 20-25 polished pieces per month.

If you're looking to scale your content without hiring full-time staff, I'd love to show you how we do it.

Book a quick 15-min call here: {CALENDAR_LINK}

Best,
{SENDER_NAME}
{COMPANY_NAME}
{INSTAGRAM}"""
    return subject, body


def get_followup_1(lead_data):
    channel_name = lead_data.get("channel_name", "your channel")
    subject = f"Re: Quick question about {channel_name}"
    body = f"""Hey,

Just following up on my email from yesterday.

Most founders I work with are either:
1. Creating content themselves and burning out
2. Hiring cheap editors and getting mediocre results
3. Inconsistent posting because they don't have a system

If any of this sounds familiar, let's talk.

15 minutes: {CALENDAR_LINK}

- {SENDER_NAME}"""
    return subject, body


def get_followup_2(lead_data):
    channel_name = lead_data.get("channel_name", "your channel")
    subject = f"Last check - {channel_name}"
    body = f"""Hey,

Last email from me — I know inboxes get busy.

If you're serious about turning your content into a lead generation system (not just likes), I'd love to show you our process.

We work with B2B founders and coaches on monthly retainers — full editing, strategy, and account management.

If that's interesting, grab a time here: {CALENDAR_LINK}

Otherwise, no worries. Best of luck with the channel.

- {SENDER_NAME}
{COMPANY_NAME}"""
    return subject, body
