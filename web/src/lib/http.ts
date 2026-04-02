export type ErrorPayload = {
  detail?: string;
};

export async function readResponsePayload<T>(response: Response): Promise<T | ErrorPayload> {
  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text) as T | ErrorPayload;
  } catch {
    return { detail: text };
  }
}

export function detailFromPayload(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail;
    }
  }
  return fallback;
}
