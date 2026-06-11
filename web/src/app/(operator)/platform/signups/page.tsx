import { PageFrame } from "@/components/common/page-frame";
import { SignupRequests } from "@/components/operator/signup-requests";
import { requirePlatformOperator } from "@/lib/auth";

export default async function SignupRequestsPage() {
  await requirePlatformOperator();
  return (
    <PageFrame
      eyebrow="Operator · Signup requests"
      title="Bank workspace requests"
      description="Vetting queue for /signup/bank. Nothing is provisioned until you approve: check the institution against the Bangladesh Bank scheduled-bank list and confirm the contact's email domain belongs to that bank. Approval creates the organization and sends the requester a magic-link admin invite."
    >
      <SignupRequests />
    </PageFrame>
  );
}
