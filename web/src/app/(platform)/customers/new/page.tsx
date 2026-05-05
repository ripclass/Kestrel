import { PageFrame } from "@/components/common/page-frame";
import { CustomerOnboardForm } from "@/components/customers/customer-onboard-form";
import { requireRole } from "@/lib/auth";

export default async function NewCustomerPage() {
  await requireRole("manager", "admin", "superadmin", "analyst");
  return (
    <PageFrame
      eyebrow="KYC / CDD · Onboard"
      title="Onboard a customer"
      description="Submit a name + identifiers; Kestrel screens the customer and (for businesses) each beneficial owner against the shared sanctions / PEP / adverse-media pool inline. The composed risk score drives the kyc_status returned in the response."
    >
      <CustomerOnboardForm />
    </PageFrame>
  );
}
