export const ACCESS_EMAIL = "access@kestrel.bd";

const DEFAULT_SUBJECT = "Kestrel access request";

const DEFAULT_BODY = [
  "Hello Kestrel team,",
  "",
  "I would like to request access to the Kestrel platform.",
  "",
  "Name:",
  "Organisation:",
  "Designation:",
  "Email:",
  "Phone:",
  "Intended use:",
  "",
  "Thank you.",
].join("\n");

export function accessRequestMailto(options?: { subject?: string; body?: string }): string {
  const subject = encodeURIComponent(options?.subject ?? DEFAULT_SUBJECT);
  const body = encodeURIComponent(options?.body ?? DEFAULT_BODY);
  return `mailto:${ACCESS_EMAIL}?subject=${subject}&body=${body}`;
}
