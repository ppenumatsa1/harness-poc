# Copilot SDK Architecture

## 1. The story

- Your app is the **manager**.
- The runtime is the **worker**.
- The SDK is the **phone line** between them.

## 2. SDK communication architecture

Adapted from [DeepWiki](https://deepwiki.com/github/copilot-sdk/1-overview). Checked against the installed Python SDK.

```mermaid
flowchart TD
    subgraph APP["Application space"]
        UAC["Your application code"]
    end

    subgraph SDK["SDK space: Python copilot package"]
        CC["CopilotClient"]
        CS["CopilotSession"]
        subgraph RPCT["RPC and transport"]
            JR["JSON-RPC 2.0 protocol"]
            TL["Transport: stdio, TCP, or in-process"]
        end
    end

    subgraph SYS["System process space"]
        NRL["Native runtime library: in-process mode"]
        CLI["Copilot CLI binary: server mode"]
    end

    subgraph EXT["External services"]
        GH["GitHub Copilot API"]
        BYOK["Custom LLM providers: OpenAI, Azure, Anthropic, Ollama"]
    end

    UAC -->|"instantiates"| CC
    CC -->|"creates"| CS
    CS -->|"send / resume RPC"| JR
    JR -->|"marshals"| TL
    TL -->|"JSON-RPC"| CLI
    TL -.->|"FFI"| NRL
    CC -.->|"loads"| NRL
    CC -->|"manages lifecycle"| CLI
    CLI --> GH
    NRL --> GH
    CLI -.->|"optional: BYOK"| BYOK
```

How to read it, top to bottom:

1. Your code creates a `CopilotClient`. The client creates `CopilotSession` objects.
2. A session sends JSON-RPC 2.0 messages. The transport carries them.
3. Default path: the client starts the CLI binary and talks over stdio. Solid arrows.
4. Experimental path: the client loads `runtime.node` into your process with FFI (`ctypes`). Dotted arrows.
5. The runtime calls GitHub Copilot API. With BYOK, it calls your own provider instead.

Events come back the same path, in reverse. Section 3 shows them.

## 3. One request, end to end

```mermaid
sequenceDiagram
    participant App as Your app
    participant SDK as Python SDK
    participant RT as Runtime
    participant API as Model API
    App->>SDK: send_and_wait(prompt)
    SDK->>RT: session.send
    RT->>API: context + prompt
    API-->>RT: answer or tool request
    opt Model asks for a tool
        RT-->>SDK: session.event: permission.requested
        SDK->>App: permission handler
        App-->>SDK: approve or deny
        SDK->>RT: session.permissions.handlePendingPermissionRequest
        RT->>RT: run tool if approved
        RT->>API: tool result
        API-->>RT: answer
    end
    RT-->>SDK: session.event: assistant.message
    RT-->>SDK: session.event: session.idle
    SDK-->>App: final response
```

Key rule: **your app decides permission, not the model.**

## 4. Wire messages

| Direction | Message | Purpose |
|---|---|---|
| SDK → runtime | `session.create` | Make a session |
| SDK → runtime | `session.send` | Send a prompt |
| Runtime → SDK | `session.event` | All events: text, tools, idle, errors |
| SDK → runtime | `session.permissions.handlePendingPermissionRequest` | Reply: approve or deny |
| SDK → runtime | `session.tools.handlePendingToolCall` | Reply: custom tool result |

Verified in the installed SDK: `copilot/client.py`, `copilot/session.py`, `copilot/generated/rpc.py`.

## 5. Remember

| Term | Meaning |
|---|---|
| Client | Connection to the runtime |
| Session | One live agent workspace |
| Runtime | The agent engine |
| Event | A status report from the runtime |
| Tool | A capability the agent can use |
| Permission handler | Your safety gate |

More views (deployment, auth, sessions): [sdk-architecture-views.md](sdk-architecture-views.md).

## Sources

- [Setup paths and architecture](https://github.com/github/copilot-sdk/blob/main/docs/setup/choosing-a-setup-path.md)
- [Python SDK README](https://github.com/github/copilot-sdk/blob/main/python/README.md)
- [Getting started](https://github.com/github/copilot-sdk/blob/main/docs/getting-started.md)
- [DeepWiki overview](https://deepwiki.com/github/copilot-sdk/1-overview) (inspiration; may lag the repo)
