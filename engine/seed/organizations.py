from dataclasses import dataclass


@dataclass(slots=True)
class OrganizationSeed:
    id: str
    name: str
    slug: str
    org_type: str


def build_organizations() -> list[OrganizationSeed]:
    return [
        OrganizationSeed("org-bfiu", "Bangladesh Financial Intelligence Unit", "bfiu", "regulator"),
        OrganizationSeed("org-sonali", "Sonali Bank PLC", "sonali-bank", "bank"),
        OrganizationSeed("org-brac", "BRAC Bank PLC", "brac-bank", "bank"),
        OrganizationSeed("org-dutchbangla", "Dutch-Bangla Bank PLC", "dutch-bangla-bank", "bank"),
        OrganizationSeed("org-islami", "Islami Bank Bangladesh PLC", "islami-bank", "bank"),
        OrganizationSeed("org-city", "City Bank PLC", "city-bank", "bank"),
        OrganizationSeed("org-bkash", "bKash Limited", "bkash", "mfs"),
    ]
