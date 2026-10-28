import wordninja

# Words that should always stay uppercase
SPECIAL_WORDS = {
    "sql": "SQL",
    "qa": "QA",
    "hr": "HR",
    "sap": "SAP",
    "api": "API",
    "ios": "iOS",
    "ui": "UI",
    "ux": "UX",
    "php": "PHP",
    "rpa": "RPA",
    "etl": "ETL",
    "aws": "AWS",
    "ai": "AI",
    "ml": "ML",
    "bi": "BI",
    "dba": "DBA",
    "erp": "ERP",
    "crm": "CRM",
    "seo": "SEO",
    "sem": "SEM",
    "vpn": "VPN",
    "net": ".NET",
}

# Job names that wordninja doesn't split well
EXCEPTION_MAP = {
    "backenddeveloper": "Backend Developer",
    "frontenddeveloper": "Frontend Developer",
    "fullstackdeveloper": "Full Stack Developer",
    "callcenteragent": "Call Center Agent",
    "callcentermanager": "Call Center Manager",
    "callcentersupervisor": "Call Center Supervisor",
    "callcenterrepresentative": "Call Center Representative",
    "customersupportrepresentative": "Customer Support Representative",
    "customerservicerepresentative": "Customer Service Representative",
    "customerserviceassociate": "Customer Service Associate",
    "customerservicemanager": "Customer Service Manager",
    "servicedeskoperator": "Service Desk Operator",
    "itsupportspecialist": "IT Support Specialist",
    "informationtechnologyspecialist": "Information Technology Specialist",
    "informationtechnologymanager": "Information Technology Manager",
    "informationtechnologydirector": "Information Technology Director",
    "machinelearningengineer": "Machine Learning Engineer",
    "businessintelligencedeveloper": "Business Intelligence Developer",
    "softwarequalityassuranceengineer": "Software Quality Assurance Engineer",
    "qualityassuranceengineer": "Quality Assurance Engineer",
    "softwaretestingengineer": "Software Testing Engineer",
    "networksecurityengineer": "Network Security Engineer",
    "cloudsolutionsarchitect": "Cloud Solutions Architect",
    "customersupportrepresentative": "Customer Support Representative",
    "callcenteragent": "Call Center Agent",
}


def format_job_name(job_name: str) -> str:
    """
    Convert machine-readable labels into readable job titles.

    Examples:
    backenddeveloper -> Backend Developer
    sqldeveloper -> SQL Developer
    machinelearningengineer -> Machine Learning Engineer
    """

    key = job_name.lower().replace(" ", "")

    # Handle special job titles first
    if key in EXCEPTION_MAP:
        return EXCEPTION_MAP[key]

    # Split remaining words automatically
    words = wordninja.split(key)

    formatted = []

    for word in words:

        if word in SPECIAL_WORDS:
            formatted.append(SPECIAL_WORDS[word])
        else:
            formatted.append(word.capitalize())

    return " ".join(formatted)

 