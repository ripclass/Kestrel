import type { ReactNode } from "react";

import type { Persona, Role, Viewer } from "@/types/domain";

export function RoleGate({
  viewer,
  personas,
  roles,
  children,
  fallback = null,
}: {
  viewer: Viewer;
  personas?: Persona[];
  roles?: Role[];
  children: ReactNode;
  fallback?: ReactNode;
}) {
  if (personas && !personas.includes(viewer.persona)) {
    return fallback;
  }

  if (roles && !roles.includes(viewer.role)) {
    return fallback;
  }

  return children;
}
