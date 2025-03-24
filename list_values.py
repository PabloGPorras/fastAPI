ORGANIZATIONS_LIST = ["FRM"]
SUB_ORGANIZATION_LIST = [
    "First Party & Fraud App", 
    "Identity", 
    "Other",
    "Servicing/ Recoveries/ Governance & Implementations",
    "Transactional",
]                         
LINE_OF_BUSINESS_LIST = [
    "Credit", 
    "Debit",
    "Deposits -IB",
    "Deposits -OB",
    "DPL",
    "Other"
]

TEAM_LIST = [
    "ATO",
    "Authentication",
    "CIP",
    "CnC",
    "CNP",
    "CPP",
    "CPT",
    "Disputes",
    "FPF",
    "FRAP",
    "Implementations",
    "Money Movement",
    "Other",
    "Policy & SafeSpend"
]

DECISION_ENGINE_LIST = [
    "ACDE",
    "ACH DE - FA",
    "Auth Central",
    "BAEL",
    "CDE - FA",
    "Deflections",
    "DPL ODE",
    "EXOD - Bal+",
    "FCMS",
    "Flex Auth",
    "GBG",
    "ID Risk - Auth DM",
    "Luminate",
    "MM Limits",
    "N/A",
    "ODE",
    "Payments Hold - Kitenet",
    "SRC",
    "TMX"
]

EFFORT_LIST = ["BAU", "EXPEDITED"]
ROLES_OPTIONS = ["FS_Manager", "FS_Analyst", "FS_Director","IMPL_Manager", "IMPL_Specialist", "IMPL_Director","Admin"]
REQUEST_EXTRA_COLUMNS = ["request_type","organization", "sub_organization", "line_of_business", "team", "decision_engine", "effort", "requester"]
REQUEST_STATUS_LIST = ["PENDING APPROVAL", "PENDING GOVERNANCE", "COMPLETED","PENDING UAT TABLE DETAIL", "GOVERNANCE REJECTED", "USER REJECTED"]
REQUEST_TYPE_LIST = ["RULE_DEPLOYMENT", "PENDING GOVERNANCE", "COMPLETED","PENDING UAT TABLE DETAIL", "GOVERNANCE REJECTED", "USER REJECTED"]
YES_NO_LIST = ["-- Select One --","YES", "NO"]

SUB_REQUEST_TYPE_LIST = [
    "Rule",
    "Derived Attribute",
    "Lookup List"
]

RULE_STATUS_LIST = [
    "Active",
    "InActive",
]

BENIFIT_TYPE_LIST = [
    "-- Select One --",
    "Continuous Improvement",
    "Fraud Loss Reduction",
    "OpsX and Customer Exp",
    "Call rate Reduction",
    "Expense Reduction",
    "Queue Rate Reduction",
    "Compliance",
    "Challenge Rate Reduction",
]

ASSET_STATUS_LIST = [
    "ACTIVE",
    "RETIRED",
]

BUSINESS_PROCESS_LIST = [
    "-- Select One --",
    "Market/Sell Products and Services", 
    "Origination/Onboarding New Accounts", 
    "Servicing/Account Maintenance",
    "Deliver Products or Services",
    "Transaction Routing/Execution",
    "Perform Settlement and Closing Activities",
    "Collections",
    "Recoveries",
    "Manage Finance Accounting and Taxation",
    "Manage Capital, Funding, and Liquidity",
    "Manage Physical Assets and Facilities",
    "Manage Compliance Legal/ Governance and Audit",
    "Manage Risk Programs" 
    ]

EUC_TYPE_LIST = [
    "-- Select One --",
    "External Reporting",
    "Transactional/Customer Facing",
    "Management Reporting",
    "Internal Operations"
]

RISK_RATING_LIST = [
    "-- Select One --",
    "Critical",
    "High",
    "Moderate",
    "Low"
]

FREQUENCY_OF_USE_LIST = [
    "-- Select One --",
    "Adhoc",
    "Real-time",
    "Quater Hour",
    "Half Hour",
    "Hourly",
    "Multiple Times Daily",
    "Daily",
    "Weekly",
    "Bi-Weekly",
    "Monthly",
    "Bi-Monthly",
    "Quarterly",
    "Annually"
    "CRON"
]

DECISION_TYPE_LIST = [
    "-- Select One --",
    "Allow",
    "Approve",
    "Challenge",
    "Cleared",
    "Declined",
    "Deny",
    "Expedite",
    "Extended Hold",
    "Fail",
    "High",
    "Low",
    "Medium",
    "Pass",
    "Refer",
    "Refer for Approval",
    "Refer for Decline",
    "Refer for Review (RR)",
    "Reject",
    "Reject - Fraud",
    "Reject - CIP",
    "Review",
    "Standard",
    "Other",
]