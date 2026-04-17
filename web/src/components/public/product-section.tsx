import type { ReactNode } from "react";

import { DossierMock, ExplanationMock, NetworkMock } from "./product-mocks";

function Block({
  eyebrow,
  title,
  body,
  visual,
  reversed,
}: {
  eyebrow: string;
  title: string;
  body: string;
  visual: ReactNode;
  reversed?: boolean;
}) {
  return (
    <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
      <div className={`space-y-4 ${reversed ? "lg:order-2" : ""}`}>
        <p className="text-xs uppercase tracking-[0.28em] text-primary">{eyebrow}</p>
        <h3 className="text-2xl font-semibold tracking-tight text-white lg:text-3xl">{title}</h3>
        <p className="text-base leading-relaxed text-slate-300">{body}</p>
      </div>
      <div className={reversed ? "lg:order-1" : ""}>
        <div className="rounded-[1.75rem] border border-white/10 bg-white/[0.03] p-4 backdrop-blur-sm">
          {visual}
        </div>
      </div>
    </div>
  );
}

export function ProductSection() {
  return (
    <section id="product" className="border-b border-white/5">
      <div className="mx-auto w-full max-w-7xl space-y-24 px-6 py-24 lg:px-10">
        <div className="max-w-3xl space-y-4">
          <p className="text-xs uppercase tracking-[0.28em] text-primary">The product</p>
          <h2 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
            A live intelligence layer, not a filing cabinet.
          </h2>
          <p className="text-base leading-relaxed text-slate-300">
            Every subject, every connection, every alert — resolved, scored, and explained the moment
            a report lands. Here&apos;s what that looks like in practice.
          </p>
        </div>

        <Block
          eyebrow="One identifier, one complete picture"
          title="Search once. See every bank that has ever flagged the subject."
          body="Type an account number, a phone, an NID, a wallet, or a name. Kestrel returns every report that mentions it, every institution that flagged it, and every connected entity — scored and ranked for an analyst to work, not a clerk to sort."
          visual={<DossierMock />}
        />

        <Block
          reversed
          eyebrow="Network graphs, rendered automatically"
          title="Watch the money move across wallets, devices, and banks."
          body="Every entity opens with a two-hop network graph — accounts, phones, wallets, devices, shared counterparties. What goAML makes an analyst draw by hand, Kestrel renders the moment a subject is opened."
          visual={<NetworkMock />}
        />

        <Block
          eyebrow="Explainable risk, not a black box"
          title="Every alert shows its work — rule by rule, weight by weight."
          body="When a cross-bank match fires, Kestrel explains it: which rules hit, how heavily each one weighed, and the exact transactions, timestamps, and amounts that triggered them. Every alert is audit-ready before an analyst opens it."
          visual={<ExplanationMock />}
        />
      </div>
    </section>
  );
}
