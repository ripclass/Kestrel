drop policy if exists rules_org on rules;

create policy rules_org on rules
  for all
  using (org_id = auth_org_id() or is_system = true)
  with check (org_id = auth_org_id() or is_system = true);
