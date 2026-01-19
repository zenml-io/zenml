# Documentation Guidelines for AI Agents

This file provides guidance for AI agents working with ZenML documentation.

## GitBook URL Structure

ZenML uses GitBook for documentation. The URL structure does **not** directly mirror the file system structure.

### Key Rules

1. **Pro docs live under `/pro/`**: Files in `docs/book/getting-started/zenml-pro/` are served at `https://docs.zenml.io/pro/...`

2. **URLs follow TOC hierarchy, not file paths**: The `toc.md` file determines the URL structure. Child pages are nested under their parent's URL path.

   Example from `zenml-pro/toc.md`:
   ```
   ## Deployments
   * [Scenarios](scenarios.md)
     * [SaaS](saas-deployment.md)
     * [Self-hosted](self-hosted-deployment.md)
   ```

   This creates:
   - `scenarios.md` → `https://docs.zenml.io/pro/deployments/scenarios`
   - `self-hosted-deployment.md` → `https://docs.zenml.io/pro/deployments/scenarios/self-hosted-deployment`

   Note: `self-hosted-deployment.md` is nested under `scenarios/` in the URL because it's a child of Scenarios in the TOC.

3. **Cross-section links require absolute URLs**: When linking from OSS docs to Pro docs (or vice versa), use absolute `https://docs.zenml.io/...` URLs. Relative links only work reliably within the same TOC section.

### Common URL Patterns

| File Location | URL |
|--------------|-----|
| `docs/book/getting-started/zenml-pro/README.md` | `https://docs.zenml.io/pro` |
| `docs/book/getting-started/zenml-pro/workspaces.md` | `https://docs.zenml.io/pro/core-concepts/workspaces` |
| `docs/book/getting-started/zenml-pro/roles.md` | `https://docs.zenml.io/pro/access-management/roles` |
| `docs/book/how-to/secrets/secrets.md` | `https://docs.zenml.io/how-to/secrets/secrets` |

### Verifying URLs

Before committing documentation changes with absolute URLs:
1. Check if the URL exists by fetching it (WebFetch tool or browser)
2. Look at existing working links in the codebase for the same section
3. Consult the relevant `toc.md` file to understand the hierarchy

### Link Checker

The CI runs an absolute link checker. If you see 404 errors for `docs.zenml.io` URLs, the URL structure likely changed (common after docs reorganizations) and needs updating.
