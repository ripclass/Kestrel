import type { Persona, Role } from "@/types/domain";

export interface DatabaseProfileRow {
  id: string;
  org_id: string;
  full_name: string;
  role: Role;
  persona: Persona;
  designation: string | null;
}
