import type { AgentEvent } from "./types";

/**
 * POST JSON and read the Server-Sent Events reply (EventSource cannot POST).
 * Throws if the stream ends before the agent's final "done" event.
 */
export async function streamEvents(
  url: string,
  body: unknown,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok || !resp.body) {
    const text = await resp.text().catch(() => "");
    throw new Error(`${resp.status} ${resp.statusText}: ${text.slice(0, 200)}`);
  }

  let sawDone = false;
  const handleFrame = (frame: string) => {
    for (const line of frame.split("\n")) {
      if (!line.startsWith("data:")) continue; // ignore comments and other SSE fields
      const event = JSON.parse(line.slice(5).trimStart()) as AgentEvent;
      if (event.type === "done") sawDone = true;
      onEvent(event);
    }
  };

  const reader = resp.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replace(/\r\n?/g, "\n");
    let cut: number;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      handleFrame(buffer.slice(0, cut));
      buffer = buffer.slice(cut + 2);
    }
  }
  if (buffer.trim()) handleFrame(buffer);
  if (!sawDone) throw new Error("The stream ended before the agent finished the turn.");
}
