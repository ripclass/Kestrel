import { createClient } from "@supabase/supabase-js";

const required = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"];
const missing = required.filter((key) => !process.env[key]);

if (missing.length) {
  console.error(`Missing required environment variables: ${missing.join(", ")}`);
  process.exit(1);
}

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY,
  {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  },
);

const users = [
  {
    // Enso platform-operator account — the login identity for the
    // cross-tenant pilot-health console at /platform (PR #16). Access is
    // gated by the KESTREL_PLATFORM_OPERATORS env allow-list, which must
    // contain this email on BOTH Render (engine) and Vercel (web). Sits in
    // the BFIU regulator org purely so the in-app shell has somewhere to
    // land; the platform-ops gate itself is email-based and org-independent.
    // The password MUST be supplied via OPS_OPERATOR_PASSWORD — this is the
    // most privileged account in the system, so no default is baked into the
    // repo. The entry is skipped at run time if the env var is absent.
    email: process.env.OPS_OPERATOR_EMAIL ?? "ops@kestrelfin.com",
    password: process.env.OPS_OPERATOR_PASSWORD,
    email_confirm: true,
    user_metadata: {
      org_id: "9c111111-1111-4111-8111-111111111111",
      full_name: "Kestrel Platform Operator",
      role: "admin",
      persona: "bfiu_director",
      designation: "Platform Operator, Enso Intelligence",
      org_type: "regulator",
    },
    app_metadata: {
      org_id: "9c111111-1111-4111-8111-111111111111",
      role: "admin",
      persona: "bfiu_director",
      org_type: "regulator",
    },
  },
  {
    email: process.env.BFIU_DIRECTOR_EMAIL ?? "director@kestrel-bfiu.test",
    password: process.env.BFIU_DIRECTOR_PASSWORD ?? "Kestrel!BFIU!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c111111-1111-4111-8111-111111111111",
      full_name: "Farhana Sultana",
      role: "admin",
      persona: "bfiu_director",
      designation: "Director, BFIU",
      org_type: "regulator",
    },
    app_metadata: {
      org_id: "9c111111-1111-4111-8111-111111111111",
      role: "admin",
      persona: "bfiu_director",
      org_type: "regulator",
    },
  },
  {
    email: process.env.BFIU_ANALYST_EMAIL ?? "analyst@kestrel-bfiu.test",
    password: process.env.BFIU_ANALYST_PASSWORD ?? "Kestrel!Analyst!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c111111-1111-4111-8111-111111111111",
      full_name: "Sadia Rahman",
      role: "analyst",
      persona: "bfiu_analyst",
      designation: "Deputy Director, Intelligence Analysis",
      org_type: "regulator",
    },
    app_metadata: {
      org_id: "9c111111-1111-4111-8111-111111111111",
      role: "analyst",
      persona: "bfiu_analyst",
      org_type: "regulator",
    },
  },
  {
    email: process.env.BANK_CAMLCO_EMAIL ?? "camlco@kestrel-sonali.test",
    password: process.env.BANK_CAMLCO_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Mahmudul Karim",
      role: "manager",
      persona: "bank_camlco",
      designation: "Chief AML Compliance Officer",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "manager",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // Bank filer demo persona — the "goAML replacement" tier seat. Provisioned
    // against BRAC Bank (the marquee multi-bank-seed prospect distinct from
    // Sonali) so it doesn't collide with the camlco demo workspace.
    email: process.env.BANK_FILER_EMAIL ?? "filer@kestrel-brac.test",
    password: process.env.BANK_FILER_PASSWORD ?? "Kestrel!Filer!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c333333-3333-4333-8333-333333333333",
      full_name: "Tahmid Khan",
      role: "analyst",
      persona: "bank_filer",
      designation: "BFIU Reporting Officer, BRAC Bank",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c333333-3333-4333-8333-333333333333",
      role: "analyst",
      persona: "bank_filer",
      org_type: "bank",
    },
  },
  {
    // Sonali SPO — Ramprosad Das. Admin-tier seat for the Sonali pilot demo
    // (May 18, 2026). Sits alongside Mahmudul Karim (manager/Deputy CAMLCO).
    // Hand the password directly to Ramprosad face-to-face; rotate after
    // the pilot agreement is signed.
    email: process.env.SONALI_SPO_EMAIL ?? "ramprosad@kestrel-sonali.test",
    password: process.env.SONALI_SPO_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Ramprosad Das",
      role: "admin",
      persona: "bank_camlco",
      designation: "SPO, AML Compliance, Sonali Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "admin",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // Sonali AML Unit Head — manager-role seat covering the operational floor
    // (section heads, daily triage oversight). Demonstrates the manager
    // seat tier alongside the admin (Ramprosad) and Deputy CAMLCO (Mahmudul).
    email: process.env.SONALI_UNITHEAD_EMAIL ?? "unithead@kestrel-sonali.test",
    password: process.env.SONALI_UNITHEAD_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Ferdous Akhter",
      role: "manager",
      persona: "bank_camlco",
      designation: "AML Unit Head, Sonali Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "manager",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // Sonali AML Investigator — analyst-role seat. The bulk seat that handles
    // daily alert triage + STR drafting + case investigation.
    email: process.env.SONALI_ANALYST1_EMAIL ?? "analyst1@kestrel-sonali.test",
    password: process.env.SONALI_ANALYST1_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Tahsina Begum",
      role: "analyst",
      persona: "bank_camlco",
      designation: "AML Investigator, Sonali Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "analyst",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // Sonali Case Officer — analyst-role seat focused on case ownership +
    // dissemination preparation. Same role tier as Investigator but separate
    // operational function.
    email: process.env.SONALI_ANALYST2_EMAIL ?? "analyst2@kestrel-sonali.test",
    password: process.env.SONALI_ANALYST2_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Kabir Hossain",
      role: "analyst",
      persona: "bank_camlco",
      designation: "Case Officer, Sonali Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "analyst",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // Sonali Internal Audit — viewer-role read-only seat. Used by SBU/audit
    // staff who consume the AML team's outputs but cannot mutate. Pattern
    // generalises to any bank's audit / compliance committee tier.
    email: process.env.SONALI_AUDIT_EMAIL ?? "audit@kestrel-sonali.test",
    password: process.env.SONALI_AUDIT_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Nazma Sultana",
      role: "viewer",
      persona: "bank_camlco",
      designation: "Internal Audit, Sonali Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "viewer",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // Sonali Senior Officer — Mahbubur Rahman. Real Sonali pilot team member
    // named by Ramprosad (May 20, 2026). Senior Officer grade → manager role
    // (operational oversight; can run scans). Seat is provisioned but stays
    // dark until Ramprosad chooses to reveal Kestrel to the wider team.
    email: process.env.SONALI_MAHBUBUR_EMAIL ?? "mahbubur@kestrel-sonali.test",
    password: process.env.SONALI_MAHBUBUR_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Mahbubur Rahman",
      role: "manager",
      persona: "bank_camlco",
      designation: "Senior Officer, AML Compliance, Sonali Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "manager",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // Sonali Officer — Md. Saifur Rahman. Real Sonali pilot team member named
    // by Ramprosad (May 20, 2026). Officer grade → analyst role (daily triage
    // + STR drafting; cannot upload raw extracts). Seat provisioned but stays
    // dark until Ramprosad reveals Kestrel to the wider team.
    email: process.env.SONALI_SAIFUR_EMAIL ?? "saifur@kestrel-sonali.test",
    password: process.env.SONALI_SAIFUR_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Md. Saifur Rahman",
      role: "analyst",
      persona: "bank_camlco",
      designation: "Officer, AML Compliance, Sonali Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "analyst",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // Sonali IT / Data Integration Owner — placeholder name pending the real
    // IT contact from Ramprosad. manager role: scan upload requires manager+,
    // so this is the seat that owns data ingestion into the Sonali workspace.
    // Deliberately the sole seat that touches raw extracts — analysts only see
    // processed alerts/entities/cases, which preserves IT's data-custodian
    // gatekeeper role. Role-based email so it survives an IT staff change.
    email: process.env.SONALI_IT_EMAIL ?? "it@kestrel-sonali.test",
    password: process.env.SONALI_IT_PASSWORD ?? "Kestrel!Sonali!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      full_name: "Imran Hossain",
      role: "manager",
      persona: "bank_camlco",
      designation: "Data Integration Owner (IT), Sonali Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c222222-2222-4222-8222-222222222222",
      role: "manager",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // City Bank CAMLCO demo persona — second commercial Pro-tier prospect
    // alongside Sonali. Distinct workspace so City Bank pitch shows their own
    // bank name in the operator panel.
    email: process.env.CITY_CAMLCO_EMAIL ?? "camlco@kestrel-city.test",
    password: process.env.CITY_CAMLCO_PASSWORD ?? "Kestrel!City!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      full_name: "Nashid Karim",
      role: "manager",
      persona: "bank_camlco",
      designation: "Chief AML Compliance Officer",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      role: "manager",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // City Bank Head of MLTFPD — Jahedul Islam. Admin seat (City's actual
    // CAMLCO-tier role; sits above Arif/Tafazzal/Shakib in MLTFPD). Backup
    // demo seat for the 2026-05-19 meeting in case he attends.
    email: process.env.CITY_JAHEDUL_EMAIL ?? "jahedul@kestrel-city.test",
    password: process.env.CITY_JAHEDUL_PASSWORD ?? "Kestrel!City!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      full_name: "Jahedul Islam",
      role: "admin",
      persona: "bank_camlco",
      designation: "Head of Money Laundering & Terrorist Financing Prevention Division, City Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      role: "admin",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // City Bank ML&TFPD demo seat — Arif Ahmed. Sr. Manager, Monitoring &
    // Compliance. Attending the 2026-05-19 City pilot demo. Manager-tier
    // bank_camlco; manager seat (admin tier belongs to Jahedul as the
    // Head of MLTFPD).
    email: process.env.CITY_ARIF_EMAIL ?? "arif@kestrel-city.test",
    password: process.env.CITY_ARIF_PASSWORD ?? "Kestrel!City!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      full_name: "Arif Ahmed",
      role: "manager",
      persona: "bank_camlco",
      designation: "Sr. Manager, Monitoring & Compliance, ML&TFPD, City Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      role: "manager",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // City Bank ML&TFPD demo seat — Md. Tafazzal Hossain. Senior Manager.
    email: process.env.CITY_TAFAZZAL_EMAIL ?? "tafazzal@kestrel-city.test",
    password: process.env.CITY_TAFAZZAL_PASSWORD ?? "Kestrel!City!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      full_name: "Md. Tafazzal Hossain",
      role: "manager",
      persona: "bank_camlco",
      designation: "Senior Manager, MLTFPD, City Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      role: "manager",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
  {
    // City Bank ML&TFPD demo seat — Shakib Tahsin Rahim. Senior Manager.
    email: process.env.CITY_SHAKIB_EMAIL ?? "shakib@kestrel-city.test",
    password: process.env.CITY_SHAKIB_PASSWORD ?? "Kestrel!City!2026",
    email_confirm: true,
    user_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      full_name: "Shakib Tahsin Rahim",
      role: "manager",
      persona: "bank_camlco",
      designation: "Senior Manager, MLTFPD, City Bank PLC",
      org_type: "bank",
    },
    app_metadata: {
      org_id: "9c666666-6666-4666-8666-666666666666",
      role: "manager",
      persona: "bank_camlco",
      org_type: "bank",
    },
  },
];

async function findUserByEmail(email) {
  let page = 1;
  const perPage = 200;

  while (true) {
    const { data, error } = await supabase.auth.admin.listUsers({ page, perPage });
    if (error) {
      throw error;
    }

    const batch = data?.users ?? [];
    const matched = batch.find((user) => user.email?.toLowerCase() === email.toLowerCase());
    if (matched) {
      return matched;
    }

    if (batch.length < perPage) {
      return null;
    }

    page += 1;
  }
}

async function ensureUser(definition) {
  const existing = await findUserByEmail(definition.email);

  if (existing) {
    const { error } = await supabase.auth.admin.updateUserById(existing.id, {
      email: definition.email,
      password: definition.password,
      user_metadata: definition.user_metadata,
      app_metadata: definition.app_metadata,
      email_confirm: definition.email_confirm,
    });

    if (error) {
      throw error;
    }

    console.log(`updated ${definition.email}`);
    return;
  }

  const { error } = await supabase.auth.admin.createUser(definition);
  if (error) {
    throw error;
  }

  console.log(`created ${definition.email}`);
}

for (const definition of users) {
  if (!definition.password) {
    // No password supplied (e.g. OPS_OPERATOR_PASSWORD unset). Skip rather
    // than abort so the demo-seat workflow is unaffected.
    console.warn(`skipped ${definition.email} — no password supplied via env`);
    continue;
  }
  await ensureUser(definition);
}

console.log("bootstrap complete");
