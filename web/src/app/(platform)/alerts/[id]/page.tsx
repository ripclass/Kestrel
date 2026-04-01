import { notFound } from "next/navigation";

import { AlertDetail } from "@/components/alerts/alert-detail";
import { PageFrame } from "@/components/common/page-frame";
import { alerts } from "@/lib/demo";

export default async function AlertPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const alert = alerts.find((item) => item.id === id);

  if (!alert) {
    notFound();
  }

  return (
    <PageFrame
      eyebrow="Alert detail"
      title={alert.title}
      description={alert.description}
    >
      <AlertDetail alert={alert} />
    </PageFrame>
  );
}
