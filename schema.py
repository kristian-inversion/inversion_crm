SCHEMA = {
    "Name": {"type": "title"},  # main title field

    "Company/Org": {"type": "rich_text"},
    "One-liner": {"type": "rich_text"},
    "Role/Title": {"type": "rich_text"},
    "Location": {"type": "rich_text"},

    # "Tags": {"type": "multi_select", "options": ["Angel in Labs", "Bank", "BD", "Crypto", "Data & Analytics", "Deal", "Fintech", "Founder/CEO", "Investor", "Investor in Labs", "Legal", "Media", "Operating Partner", "PE", "PR", "Product", "Quarterly Updates", "Recruiter", "SAB/IC", "SPV", "Telecom", "Treasury Management", "VC"]},

    "Notes": {"type": "rich_text"},

    # Skipping CRM Tasks since it's a relation, not plain data
    # Skipping Last Edited Time (Notion handles automatically)

    "Introduced By": {"type": "rich_text"},
    "Sub CRM": {"type": "select", "options": ["Capital Partners"]}
}
