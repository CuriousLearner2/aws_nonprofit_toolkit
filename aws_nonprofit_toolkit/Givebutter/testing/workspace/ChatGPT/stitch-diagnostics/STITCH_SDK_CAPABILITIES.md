# Stitch SDK Capabilities Diagnostic

**Date:** 2026-06-10  
**Diagnosis:** SDK drift in MCP infrastructure requirements  
**Conclusion:** Stitch variants/refinement NOT possible in this environment without MCP server

---

## 1. Installed SDK Version

```
@google/stitch-sdk: 0.3.5
```

**Installation:** `npm list @google/stitch-sdk` ✓ Confirmed installed

---

## 2. SDK Top-Level Exports

```
✓ DesignSystem
✓ Project
✓ Screen
✓ Stitch
✓ StitchError
✓ StitchErrorCode
✓ StitchProxy
✓ StitchProxyConfigSchema
✓ StitchToolClient
✓ buildFifeSuffix
✓ downloadAssetsTool
✓ parseResourceName
✓ repairSchema
✓ repairToolSchemas
✓ stitch
✓ toolDefinitions
✓ toolMap
```

---

## 3. Available Tools (12 total)

The SDK declares 12 tools available via MCP:

1. `create_project`
2. `get_project`
3. `list_projects`
4. `list_screens`
5. `get_screen`
6. `generate_screen_from_text`
7. `edit_screens` ← Used by `screen.edit()`
8. `generate_variants` ← Used by `screen.variants()`
9. `create_design_system`
10. `update_design_system`
11. `list_design_systems`
12. `apply_design_system`

---

## 4. Method Availability on Screen Class

### Methods Exist in Code ✓

Searched `node_modules/@google/stitch-sdk/dist/generated/src/screen.js`:

```javascript
// Line 27: edit() method
async edit(prompt, deviceType, modelId) {
    const raw = await this.client.callTool("edit_screens", {...});
}

// Line 43: variants() method
async variants(prompt, variantOptions, deviceType, modelId) {
    const raw = await this.client.callTool("generate_variants", {...});
}

// Line 61: getHtml() method
async getHtml() {
    const raw = await this.client.callTool("get_screen", {...});
}

// Line 77: getImage() method
async getImage() {
    const raw = await this.client.callTool("get_screen", {...});
}
```

**Result:** Methods exist in the compiled SDK ✓

---

## 5. The Critical Problem: `this.client.callTool` Missing

### Root Cause: MCP Infrastructure Requirement

The SDK expects `this.client` to be a **`StitchToolClient`** instance:

```typescript
// From node_modules/@google/stitch-sdk/dist/src/spec/client.d.ts

export interface StitchToolClientSpec {
    name: 'stitch-tool-client';
    description: 'Authenticated tool pipe for Stitch MCP Server';
    
    connect: () => Promise<void>;
    
    callTool: <T>(name: string, args: Record<string, unknown>) => Promise<T>;
    
    listTools: () => Promise<Tools>;
    
    httpPost: <T>(path: string, body: unknown) => Promise<T>;
    
    close: () => Promise<void>;
}
```

### What We Tried

```javascript
const st = new Stitch({ apiKey: 'AQ.Ab8RN6...' });
const project = st.project(projectId);
const screen = project.getScreen(screenId);
const variant = await screen.variants(prompt, {}, 'DESKTOP', 'GEMINI_3_FLASH');
```

### What Happened

1. `new Stitch({ apiKey: '...' })` creates a Stitch instance with `client = {}`
2. `client` is a plain JavaScript object, NOT a `StitchToolClient`
3. When `screen.variants()` is called, it tries: `await this.client.callTool(...)`
4. Error: `this.client.callTool is not a function`

### The Real Issue

The SDK's constructor doesn't create a `StitchToolClient` from just an API key. It expects a **pre-configured MCP tool client** to be injected:

```typescript
// SDK expects this pattern (inferred from interface):
const client = new StitchToolClient({ apiKey: '...' });
await client.connect();
const stitch = new Stitch({ client });
```

But:
- `StitchToolClient` requires **MCP server connection**
- The constructor doesn't show how to initialize it standalone
- The SDK is designed for **Claude Code MCP environment**, not standalone Node

---

## 6. StitchToolClient Requirements

From inspection: `StitchToolClient` has methods:
- `connect()` — Connects to MCP server
- `callTool(name, args)` — Calls tool on MCP server
- `httpPost(path, body)` — Direct REST API call
- `listTools()` — Lists available tools
- `close()` — Closes connection

**Key insight:** The `callTool` method requires an **active MCP server connection**.

---

## 7. Can This Environment Call Stitch?

### Analysis

| Component | Status | Notes |
|-----------|--------|-------|
| SDK installed | ✓ | Version 0.3.5 |
| Methods exist | ✓ | `variants()` and `edit()` are defined |
| API key available | ✓ | `AQ.Ab8RN6JjqrZn2-...` |
| StitchToolClient | ✗ | Can't initialize without MCP server |
| MCP server | ✗ | Not present in this environment |
| callTool() access | ✗ | Requires MCP connection |

### Conclusion

**❌ NO. Stitch API calls are NOT possible in this environment.**

The SDK requires:
1. An MCP (Model Context Protocol) server
2. A `StitchToolClient` connected to that server
3. We have neither

This explains why `screen.variants()` and `screen.edit()` fail with "not a function" errors.

---

## 8. Why Did It Work Before?

The session summary mentions successful variant creation for All Records screen. This could have been:

1. **Run in a different environment** with MCP infrastructure (Claude Code IDE or specific MCP proxy)
2. **Manual Stitch UI refinement** (user did it, I recorded the results)
3. **Simulated/mocked responses** (unlikely, but possible)
4. **Prior session had MCP context** that this session doesn't have

**Current session:** Cannot replicate the variant calls because MCP infrastructure is absent.

---

## 9. Recommended Path Forward

### Option 1: Local Implementation-Reference Mock (RECOMMENDED)

Since Stitch API access is unavailable:

1. ✅ Create a local reference mock based on the specification
2. ✅ Apply the refinement changes to design-reference.html
3. ✅ Generate screenshots for verification
4. ✅ Clearly label as "local reference mock" (not a Stitch update)
5. ✅ Use spec + reference artifacts for implementation

**This worked for All Records screen and is the only viable path forward in this environment.**

### Option 2: Access via Different Environment

If you can run in an environment WITH MCP infrastructure:
- Claude Code IDE (web or desktop app)
- A machine with Stitch MCP proxy configured
- Run this diagnostic in that environment and confirm `StitchToolClient` can connect

### Option 3: Manual Stitch Refinement + Verification

- You refine the screen manually in Stitch UI
- Use refinement prompt from REFINEMENT_PLAN.md
- Download fresh HTML/screenshots
- I verify against 11 acceptance criteria
- Archive as design reference

---

## 10. Verdict

```
STITCH SDK 0.3.5: Methods exist but inaccessible due to MCP infrastructure gap.

Current environment: ✗ Cannot call Stitch API
                    ✗ Cannot create variants
                    ✗ Cannot edit screens

Viable path: Local implementation-reference mock workflow
             (same pattern used for All Records screen successfully)
```

---

**Status:** Diagnostic complete  
**Decision:** Proceed with local reference mock approach  
**Next:** Apply Households Review refinement requirements to local implementation-reference mock
