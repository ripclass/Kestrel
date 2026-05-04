import type { Persona, Role, Viewer } from "@/types/domain";

export interface NavItem {
  label: string;
  href: string;
  section: string;
  personas?: Persona[];
  roles?: Role[];
  /** goAML-equivalent vocabulary — rendered as the link's title tooltip. */
  aka?: string;
}

const navItems: NavItem[] = [
  { section: "Overview", label: "Overview", href: "/overview", aka: "Home / Dashboard (goAML)" },
  { section: "Intelligence Tools", label: "Investigate", href: "/investigate", aka: "Analysis / Catalogue Search (goAML)" },
  { section: "Intelligence Tools", label: "Catalogue", href: "/investigate/catalogue", aka: "Catalogue Search (goAML)" },
  { section: "Intelligence Tools", label: "Intelligence", href: "/intelligence/entities", aka: "Intel (goAML)" },
  { section: "Intelligence Tools", label: "Cross-bank", href: "/intelligence/cross-bank", aka: "Cross-institution overlap (Kestrel-native)" },
  { section: "Intelligence Tools", label: "Disseminations", href: "/intelligence/disseminations", aka: "Disseminated Transaction Lookup (goAML)" },
  { section: "Intelligence Tools", label: "Saved queries", href: "/intelligence/saved-queries", aka: "Profiles (goAML Intel)" },
  { section: "Intelligence Tools", label: "Diagram builder", href: "/investigate/diagram", aka: "Create Diagram (goAML)" },
  { section: "Intelligence Tools", label: "New subject", href: "/intelligence/entities/new", aka: "New Subjects — Account / Person / Entity (goAML)" },
  { section: "Operations", label: "STRs", href: "/strs", aka: "Reports — STR/SAR/CTR/IER/TBML (goAML)" },
  { section: "Operations", label: "Alerts", href: "/alerts", aka: "Alerts (goAML)" },
  { section: "Operations", label: "Cases", href: "/cases", aka: "Business Processes (goAML)" },
  { section: "Operations", label: "Exchange", href: "/iers", aka: "Information Exchange Request (goAML)" },
  { section: "Operations", label: "Scan", href: "/scan", personas: ["bank_camlco"], aka: "Detection / Matching Executions (goAML)" },
  { section: "Command", label: "National", href: "/reports/national", personas: ["bfiu_director", "bfiu_analyst"], aka: "Reports (goAML)" },
  { section: "Command", label: "Compliance", href: "/reports/compliance", personas: ["bfiu_director", "bank_camlco"], aka: "Reports — Compliance (goAML)" },
  { section: "Command", label: "Trends", href: "/reports/trends", personas: ["bfiu_director"], aka: "Reports — Trend Analysis (goAML)" },
  { section: "Command", label: "Statistics", href: "/reports/statistics", personas: ["bfiu_director", "bfiu_analyst"], aka: "Statistics menu (goAML)" },
  { section: "Command", label: "Export", href: "/reports/export", aka: "File — PDF / Excel / XML Export (goAML)" },
  { section: "Admin", label: "Settings", href: "/admin", roles: ["admin", "manager", "superadmin"], aka: "Management (goAML)" },
  { section: "Admin", label: "Team", href: "/admin/team", roles: ["admin", "manager", "superadmin"], aka: "User / Role Maintenance (goAML)" },
  { section: "Admin", label: "Rules", href: "/admin/rules", roles: ["admin", "manager", "superadmin"], aka: "Matching — System Rules (goAML Intel)" },
  { section: "Admin", label: "Match definitions", href: "/admin/match-definitions", roles: ["admin", "manager", "superadmin"], aka: "Match Definitions / Executions (goAML Intel)" },
  { section: "Admin", label: "Reference tables", href: "/admin/reference-tables", roles: ["admin", "manager", "superadmin"], aka: "Reference Tables / Lookup Master (goAML)" },
  { section: "Admin", label: "Schedules", href: "/admin/schedules", roles: ["admin", "superadmin"], aka: "Scheduled Processes (goAML Management)" },
  { section: "Admin", label: "API Keys", href: "/admin/api-keys", roles: ["admin", "manager", "superadmin"], aka: "Integration Credentials" },
];

export function getNavigation(viewer: Viewer) {
  return navItems.filter((item) => {
    if (item.personas && !item.personas.includes(viewer.persona)) {
      return false;
    }
    if (item.roles && !item.roles.includes(viewer.role)) {
      return false;
    }
    return true;
  });
}
