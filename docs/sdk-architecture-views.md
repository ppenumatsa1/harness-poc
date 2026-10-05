# Copilot SDK Architecture: More Views

Extra views. We update or delete these as we learn.
Start with [sdk-architecture.md](sdk-architecture.md).

## A. Inside the runtime

```mermaid
flowchart LR
    RPC["JSON-RPC server"] --> AUTH["Authentication"]
    RPC --> SM["Session manager"]
    SM --> LOOP["Agent loop"]
    AUTH --> MP["Model provider"]
    LOOP --> MP
    LOOP --> TOOLS["Tool dispatch"]
```

## B. Who owns what

```mermaid
flowchart LR
    subgraph APP["Your app owns"]
        a1["User login + authorization"]
        a2["Tool permission policy"]
        a3["UI and business data"]
    end
    subgraph SDK["SDK owns"]
        s1["Runtime connection"]
        s2["Typed requests + events"]
    end
    subgraph RT["Runtime owns"]
        r1["Sessions"]
        r2["Agent loop"]
        r3["Model calls + tool runs"]
    end
```

## C. One client, many sessions

```mermaid
flowchart TD
    C["CopilotClient"] --> S1["Session A: user 1"]
    C --> S2["Session B: user 2"]
    C --> S3["Session C: background task"]
```

Keep users in separate sessions. Do not share context.

## D. Where the runtime runs (Python)

```mermaid
flowchart TD
    Q{"Who starts the runtime?"}
    Q -->|"SDK, automatic"| D["Managed default: stdio"]
    Q -->|"SDK, my binary"| L["for_stdio / for_tcp with path"]
    Q -->|"Already running"| U["for_uri: external server"]
    Q -->|"Inside my process"| F["for_inprocess: FFI, experimental"]
    D --> X["This lab"]
    U --> Y["Backend services"]
```

## E. Authentication vs authorization

```mermaid
flowchart LR
    subgraph AUTHN["Authentication: runtime"]
        n1["Signed-in CLI user"]
        n2["GitHub token / OAuth"]
        n3["BYOK API key"]
    end
    subgraph AUTHZ["Authorization: your app"]
        z1["Can this user run this action?"]
        z2["Can this tool touch this data?"]
    end
```

- Authentication = how the runtime gets model access.
- Authorization = what your user may do. You build this.
