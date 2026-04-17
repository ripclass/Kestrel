import type { Persona, Role, Viewer } from "@/types/domain";

export interface NavItem {
  label: string;
  href: string;
  section: string;
  personas?: Persona[];
  roles?: Role[];
}

const navItems: NavItem[] = [
  { section: "Overview", label: "Overview", href: "/overview" },
  { section: "Intelligence Tools", label: "Investigate", href: "/investigate" },
  { section: "Intelligence Tools", label: "Intelligence", href: "/intelligence/entities" },
  { section: "Intelligence Tools", label: "Disseminations", href: "/intelligence/disseminations" },
  { section: "Intelligence Tools", label: "Saved queries", href: "/intelligence/saved-queries" },
  { section: "Intelligence Tools", label: "Diagram builder", href: "/investigate/diagram" },
  { section: "Intelligence Tools", label: "New subject", href: "/intelligence/entities/new" },
  { section: "Operations", label: "STRs", href: "/strs" },
  { section: "Operations", label: "Alerts", href: "/alerts" },
  { section: "Operations", label: "Cases", href: "/cases" },
  { section: "Operations", label: "Exchange", href: "/iers" },
  { section: "Operations", label: "Scan", href: "/scan", personas: ["bank_camlco"] },
  { section: "Command", label: "National", href: "/reports/national", personas: ["bfiu_director", "bfiu_analyst"] },
  { section: "Command", label: "Compliance", href: "/reports/compliance", personas: ["bfiu_director", "bank_camlco"] },
  { section: "Command", label: "Trends", href: "/reports/trends", personas: ["bfiu_director"] },
  { section: "Command", label: "Statistics", href: "/reports/statistics", personas: ["bfiu_director", "bfiu_analyst"] },
  { section: "Command", label: "Export", href: "/reports/export" },
  { section: "Admin", label: "Settings", href: "/admin", roles: ["admin", "manager", "superadmin"] },
  { section: "Admin", label: "Team", href: "/admin/team", roles: ["admin", "manager", "superadmin"] },
  { section: "Admin", label: "Rules", href: "/admin/rules", roles: ["admin", "manager", "superadmin"] },
  { section: "Admin", label: "Match definitions", href: "/admin/match-definitions", roles: ["admin", "manager", "superadmin"] },
  { section: "Admin", label: "Reference tables", href: "/admin/reference-tables", roles: ["admin", "manager", "superadmin"] },
  { section: "Admin", label: "Schedules", href: "/admin/schedules", roles: ["admin", "superadmin"] },
  { section: "Admin", label: "API Keys", href: "/admin/api-keys", roles: ["admin", "manager", "superadmin"] },
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
