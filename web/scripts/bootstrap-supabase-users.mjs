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
  await ensureUser(definition);
}

console.log("bootstrap complete");
