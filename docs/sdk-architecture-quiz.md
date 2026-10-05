# Architecture Quiz

Six levels. Each level adds one layer. Try to answer before you open the answer.

Study first: [sdk-architecture.md](sdk-architecture.md).

---

## Level 1: The four boxes

```mermaid
flowchart LR
    A["App"] --> S["SDK"] --> R["Runtime"] --> M["Model API"]
    M -.-> R -.-> S -.-> A
```

**Q1.1** Name the four boxes in order, from your code to the model.

<details><summary>Answer</summary>

App → SDK → Runtime → Model API.
</details>

**Q1.2** Which box runs the agent loop?

<details><summary>Answer</summary>

The runtime. The SDK only connects to it and carries messages.
</details>

**Q1.3** Is the SDK an LLM wrapper? Why or why not?

<details><summary>Answer</summary>

No. The SDK controls an agent runtime. The runtime plans, calls tools, and talks to the model. Your app never calls the model directly.
</details>

---

## Level 2: Inside the SDK

```mermaid
flowchart TD
    CC["CopilotClient"] --> CS["CopilotSession"]
    CS --> JR["JSON-RPC 2.0"] --> TL["Transport"]
```

**Q2.1** What is the job of `CopilotClient`? What is the job of `CopilotSession`?

<details><summary>Answer</summary>

- Client: connects to the runtime and manages its lifecycle. Creates and resumes sessions.
- Session: one live agent workspace. It holds context, model, tools, the permission handler, and event listeners.
</details>

**Q2.2** Can one client have many sessions?

<details><summary>Answer</summary>

Yes. One client, many sessions. Each user or task should get its own session.
</details>

**Q2.3** What format do the SDK and the runtime use to talk? What carries it by default?

<details><summary>Answer</summary>

JSON-RPC 2.0. By default it goes over stdio to a CLI process that the SDK starts.
</details>

---

## Level 3: Request and response

```mermaid
sequenceDiagram
    App->>SDK: send_and_wait(prompt)
    SDK->>Runtime: session.send
    Runtime-->>SDK: session.event ...
    Runtime-->>SDK: session.event: session.idle
    SDK-->>App: final message
```

**Q3.1** Name the one runtime-to-SDK message type that carries all events.

<details><summary>Answer</summary>

`session.event`. Text, tool activity, errors, and idle all arrive this way.
</details>

**Q3.2** Which event tells you the turn has finished?

<details><summary>Answer</summary>

`session.idle`.
</details>

**Q3.3** What is the difference between `send()` and `send_and_wait()`?

<details><summary>Answer</summary>

- `send()` sends the prompt and returns at once. You watch events to see progress and the end.
- `send_and_wait()` sends, then waits for `session.idle`. It returns the last assistant message. It can return `None` if no message came.
</details>

**Q3.4** You want text to appear word by word. What do you need?

<details><summary>Answer</summary>

Set `streaming=True` on the session. Then handle `assistant.message_delta` events.
</details>

---

## Level 4: Tools and permissions

```mermaid
flowchart LR
    M["Model: I want a tool"] --> P{"Permission handler"}
    P -->|"approve"| T["Run tool"] --> M2["Model continues"]
    P -->|"deny"| M2
```

**Q4.1** Who decides if a tool may run: the model, the runtime, or your app?

<details><summary>Answer</summary>

Your app, through the permission handler. The model only asks.
</details>

**Q4.2** A built-in tool (such as reading a file) and your custom Python tool. Where does each one run?

<details><summary>Answer</summary>

- Built-in tool: inside the runtime process.
- Custom tool: in your Python process. The runtime sends `external_tool.requested`. The SDK calls your handler. The SDK sends the result back with `session.tools.handlePendingToolCall`.
</details>

**Q4.3** After a tool runs, does the turn end?

<details><summary>Answer</summary>

Not always. The result goes back to the model. The model can answer, ask for another tool, or finish. The turn ends at `session.idle`.
</details>

**Q4.4** What happens if you give no permission handler?

<details><summary>Answer</summary>

Permission requests come as events and stay pending. Your app must resolve them some other way. For safe code, always give a handler.
</details>

---

## Level 5: Deployment shapes

```mermaid
flowchart TD
    Q{"Where is the runtime?"}
    Q --> A["Managed stdio: SDK starts it"]
    Q --> B["TCP: SDK starts it on a port"]
    Q --> C["URI: already running elsewhere"]
    Q --> D["In-process: FFI, experimental"]
```

**Q5.1** Which shape does `CopilotClient()` use with no options?

<details><summary>Answer</summary>

Managed stdio. The SDK downloads a pinned runtime, starts it, and stops it.
</details>

**Q5.2** You run a web backend with many servers. Which shape fits best?

<details><summary>Answer</summary>

URI: connect to a runtime server that runs on its own. Use `RuntimeConnection.for_uri(...)`.
</details>

**Q5.3** What changes with BYOK? What stays the same?

<details><summary>Answer</summary>

- Changes: the runtime calls your own model provider with your key, not the GitHub Copilot API.
- Same: the app, SDK, sessions, events, tools, and permissions.
</details>

---

## Level 6: Put it all together

**Q6.1** Trace this request from start to end. Name each component and message.

> A user types "What files are in this folder?" in your web app. The agent must use a file-list tool.

<details><summary>Answer</summary>

1. Web app checks the user and picks that user's session.
2. App calls `session.send(...)`.
3. SDK sends `session.send` (JSON-RPC 2.0) over the transport.
4. Runtime adds the prompt to the session context and calls the model API.
5. Model asks for a file-list tool.
6. Runtime sends `session.event` with `permission.requested`.
7. SDK calls your permission handler. Your app approves.
8. SDK sends the decision back with `session.permissions.handlePendingPermissionRequest`.
9. Runtime runs the tool and gives the result to the model.
10. Model writes the answer. Runtime sends `assistant.message`, then `session.idle`.
11. SDK routes the events. App shows the answer.
</details>

**Q6.2** Two users share one client. What must you keep separate? Whose job is it?

<details><summary>Answer</summary>

- Keep separate: sessions, context, credentials, working folders, tools, and data.
- Your app's job. The SDK gives you isolated sessions. Your app decides who gets which session and what they may do.
</details>

**Q6.3** Authentication vs authorization. Which one does the runtime do? Which one do you build?

<details><summary>Answer</summary>

- Authentication (how the runtime gets model access: CLI login, token/OAuth, BYOK): runtime and SDK config.
- Authorization (what this user may do): you build it in your app.
</details>

**Q6.4** The UI freezes and no answer shows. Which of the three loops do you check, and in what order?

<details><summary>Answer</summary>

1. **Capability loop**: is a permission or tool request pending with no reply?
2. **Observation loop**: are you listening for events? Did a `session.error` arrive?
3. **Conversation loop**: did the send reach the runtime? Is the runtime alive?
</details>

---

## Common mix-ups (from your answers)

| Mix-up | Correct model |
|---|---|
| "The SDK manages many clients" | One client = one runtime connection. One client → many sessions. |
| "`CopilotSession` is the session manager" | The session manager is inside the runtime. `CopilotSession` is your handle to one session. |
| "`session.event.idle`" | The notification is `session.event`. Inside it, the event type is `session.idle`. |
| "`send` is sync, `send_and_wait` is async" | Both are async (`await`). `send` returns at once. `send_and_wait` waits for `session.idle`. |
| "Streaming = just turn it on" | `streaming=True` **and** handle `assistant.message_delta`. |

```mermaid
flowchart LR
    N["session.event (envelope)"] --> T1["assistant.message_delta"]
    N --> T2["assistant.message"]
    N --> T3["tool / permission events"]
    N --> T4["session.error"]
    N --> T5["session.idle = turn done"]
```
