/**
 * Pi-custom chat client scaffold.
 * Calls geoagent HTTP session API only — no local model inference.
 */
export type FinalAnswerPayload = {
  final_answer: Record<string, unknown>;
  events: Array<Record<string, unknown>>;
  schema_ok: boolean;
  tool_call_parse_rate: number;
};

function apiBase(baseUrl?: string): string {
  return (baseUrl ?? process.env.GEOAGENT_API_BASE_URL ?? "http://127.0.0.1:8088").replace(
    /\/$/,
    "",
  );
}

export async function askSwarm(
  question: string,
  baseUrl?: string,
): Promise<FinalAnswerPayload> {
  const response = await fetch(`${apiBase(baseUrl)}/v1/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(`ask_swarm failed: ${response.status}`);
  }
  return (await response.json()) as FinalAnswerPayload;
}

/** Return SSE/event list from the last ask payload (no extra round-trip). */
export function showTrace(payload: FinalAnswerPayload): Array<Record<string, unknown>> {
  return payload.events ?? [];
}
