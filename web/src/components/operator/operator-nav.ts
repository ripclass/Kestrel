import type { OperatorRole } from "@/lib/auth";

export interface OperatorNavItem {
  label: string;
  href: string;
  section: string;
  /** Roles that see this module. `owner` always sees everything. */
  roles: OperatorRole[];
  /** Built but not yet shipped — rendered disabled with a "planned" tag. */
  planned?: boolean;
}

/**
 * Operator-console navigation. Role gating implements the access matrix in
 * docs/internal/operations-readiness.md §6 — `owner` sees every module;
 * other roles see their subset. Planned modules are shown (so the shape of
 * the console is visible) but disabled.
 */
const NAV: OperatorNavItem[] = [
  {
    section: "Pilots",
    label: "Pilot health",
    href: "/platform",
    roles: ["owner", "operations", "engineer", "aml", "ml", "sales"],
  },
  {
    section: "Pilots",
    label: "Tenants",
    href: "/platform/tenants",
    roles: ["owner", "operations", "engineer", "devops"],
  },
  {
    section: "Pilots",
    label: "Signup requests",
    href: "/platform/signups",
    roles: ["owner", "operations", "sales"],
  },
  {
    section: "Platform",
    label: "System health",
    href: "/platform/system",
    roles: ["owner", "operations", "engineer", "ml", "devops"],
  },
  {
    section: "Platform",
    label: "Audit",
    href: "/platform/audit",
    roles: ["owner", "operations", "engineer", "aml", "ml"],
    planned: true,
  },
  {
    section: "Growth",
    label: "Sovereign / AI ops",
    href: "/platform/sovereign",
    roles: ["owner", "ml"],
    planned: true,
  },
  {
    section: "Growth",
    label: "On-prem deployments",
    href: "/platform/onprem",
    roles: ["owner", "operations", "engineer", "devops"],
    planned: true,
  },
  {
    section: "Growth",
    label: "Billing & revenue",
    href: "/platform/billing",
    roles: ["owner"],
    planned: true,
  },
  {
    section: "Admin",
    label: "Team & access",
    href: "/platform/team",
    roles: ["owner"],
    planned: true,
  },
];

export function operatorNavFor(role: OperatorRole): OperatorNavItem[] {
  return NAV.filter((item) => role === "owner" || item.roles.includes(role));
}

/** Section order for rendering. */
export const OPERATOR_NAV_SECTIONS = ["Pilots", "Platform", "Growth", "Admin"];
