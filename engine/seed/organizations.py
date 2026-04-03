from dataclasses import dataclass


@dataclass(slots=True)
class OrganizationSeed:
    id: str
    name: str
    slug: str
    org_type: str
    bank_code: str | None = None


def build_organizations() -> list[OrganizationSeed]:
    return [
        OrganizationSeed("9c111111-1111-4111-8111-111111111111", "Bangladesh Financial Intelligence Unit", "bfiu", "regulator"),
        OrganizationSeed("9c222222-2222-4222-8222-222222222222", "Sonali Bank PLC", "sonali-bank", "bank", "SONALI"),
        OrganizationSeed("9c333333-3333-4333-8333-333333333333", "BRAC Bank PLC", "brac-bank", "bank", "BRAC"),
        OrganizationSeed("9c444444-4444-4444-8444-444444444444", "Dutch-Bangla Bank PLC", "dutch-bangla-bank", "bank", "DBBL"),
        OrganizationSeed("9c555555-5555-4555-8555-555555555555", "Islami Bank Bangladesh PLC", "islami-bank", "bank", "IBBL"),
        OrganizationSeed("9c666666-6666-4666-8666-666666666666", "City Bank PLC", "city-bank", "bank", "CITY"),
        OrganizationSeed("9c777777-7777-4777-8777-777777777777", "bKash Limited", "bkash", "mfs", "BKASH"),
    ]
