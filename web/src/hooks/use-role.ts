"use client";

import type { Persona, Role } from "@/types/domain";

export function useRole(role: Role, persona: Persona) {
  return {
    isRegulator: persona !== "bank_camlco",
    isDirector: persona === "bfiu_director",
    canManage: role === "admin" || role === "manager" || role === "superadmin",
  };
}
