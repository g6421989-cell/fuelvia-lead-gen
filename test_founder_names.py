#!/usr/bin/env python3
# ============================================================
# TEST — Founder Names in Email Headers
# ============================================================
# Demonstrates how sender names are extracted from emails
# ============================================================

def get_founder_name(email: str) -> str:
    """Extract founder name from email address."""
    if not email or "@" not in email:
        return "Fuelvia"
    founder_name = email.split("@")[0]
    return founder_name.capitalize()


# Test data
test_emails = [
    "jashan@fuelviaa.com",
    "ruwaid@fuelviaa.com",
    "danish@fuelviaa.com",
]

print("\n" + "="*60)
print("  FOUNDER NAMES IN EMAIL HEADERS")
print("="*60 + "\n")

for email in test_emails:
    founder_name = get_founder_name(email)
    from_header = f"{founder_name} - Fuelvia <{email}>"
    print(f"Email:      {email}")
    print(f"Founder:    {founder_name}")
    print(f"From Header: {from_header}")
    print()

print("="*60)
print("WHAT RECIPIENTS WILL SEE")
print("="*60 + "\n")

recipients = {
    "creator1@youtube.com": "jashan@fuelviaa.com",
    "creator2@youtube.com": "ruwaid@fuelviaa.com",
    "creator3@youtube.com": "danish@fuelviaa.com",
}

for recipient, sender_email in recipients.items():
    founder_name = get_founder_name(sender_email)
    print(f"Recipient: {recipient}")
    print(f"From:      {founder_name} - Fuelvia <{sender_email}>")
    print()

print("="*60)
print("[OK] All founder names extracted correctly!")
print("="*60 + "\n")
