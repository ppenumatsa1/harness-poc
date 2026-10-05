# Copilot SDK Components

Read [sdk-architecture.md](sdk-architecture.md) first.

## 1. Component map

```mermaid
mindmap
  root((Copilot SDK))
    CopilotClient
      start / stop
      connection mode
      auth token
    Session
      model
      instructions
      tools
      permission handler
      event listeners
    Runtime
      session manager
      agent loop
      model provider
    Events
      message delta
      assistant message
      tool events
      session idle
    Extensions
      custom tools
      custom agents
      MCP servers
```

## 2. Lifecycle

```mermaid
stateDiagram-v2
    [*] --> ClientCreated: CopilotClient()
    ClientCreated --> Started: start()
    Started --> SessionOpen: create_session()
    SessionOpen --> Working: send()
    Working --> SessionOpen: session.idle
    SessionOpen --> Started: disconnect()
    Started --> [*]: stop()
```

`async with` runs `start/stop` and `disconnect` for you.

## 3. One agent turn

```mermaid
flowchart LR
    P["Prompt"] --> M["Model thinks"]
    M -->|"needs tool"| G{"Permission?"}
    G -->|"yes"| T["Run tool"]
    G -->|"no"| M
    T --> M
    M -->|"done"| A["assistant.message"]
    A --> I["session.idle"]
```

A turn can loop many times before `session.idle`.

## 4. Configuration layers

```mermaid
flowchart TD
    APP["App: users, tenants, storage, UI"]
    CL["Client: connection, runtime path, auth"]
    SE["Session: model, tools, instructions, permissions"]
    MS["Message: prompt, attachments"]
    APP --> CL --> SE --> MS
```

Top layers live longer. Bottom layers change more often.

## 5. Three loops

```mermaid
flowchart LR
    subgraph L1["1. Conversation"]
        c1["send"] --> c2["answer"]
    end
    subgraph L2["2. Capability"]
        k1["tool request"] --> k2["approve / deny"]
    end
    subgraph L3["3. Observation"]
        o1["event"] --> o2["UI / log"]
    end
```

When a problem occurs, ask: which loop is it?

## 6. Quick reference

| Component | One line |
|---|---|
| `CopilotClient` | Opens the line to the runtime |
| Runtime | Runs the agent |
| JSON-RPC | Message format on the line |
| Session | One agent workspace |
| Event | A status report |
| Tool | Something the agent can do |
| Permission handler | Says yes or no to tools |
| Custom agent | A specialist inside a session |

## Sources

- [Python SDK README](https://github.com/github/copilot-sdk/blob/main/python/README.md)
- [Getting started](https://github.com/github/copilot-sdk/blob/main/docs/getting-started.md)
