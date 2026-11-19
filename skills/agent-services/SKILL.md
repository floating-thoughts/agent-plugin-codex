---
name: agent-services
description: Set up or troubleshoot agent-services in Codex. Check sign-in and hook review, find working methods and subagent routing advice, or explain and change agent-services settings when asked.
---

# agent-services in Codex

agent-services provides working methods and optional model and reasoning advice for Codex subagents through a remote MCP server. The plugin runs without a local helper process.

## Check setup

1. If `status` is available, call it. Report whether the sign-in is active, the license is valid, the organization has paused the service, and which methods setting is selected. If the tool is missing or reports a signed-out session, check that the plugin is enabled and point the user to sign-in below. An active status confirms the MCP connection. Hook review is a separate check.
2. For missing automatic methods or routing advice, ask the user to open **Review hooks** in the desktop composer or **Settings > Hooks**. In the CLI, use `/hooks`. Find the source `agent-services@agent-plugin-codex` and inspect the review state of its hooks. If review is pending, the user can review and trust the definitions they want to run. `setup` with `info hooks` describes what the service receives. Keep hook review and account settings under the user's control.
3. If the user previously installed `agent-services@agent-plugin`, Codex treats the install from `agent-plugin-codex` as a different hook source. Prior approvals apply to the old source. Review the current source even if the user already trusted the previous one. If both plugins are enabled, point out the duplicate and let the user choose which to keep enabled. An active sign-in can continue to be used.
4. Start a fresh Codex thread after installing, signing in, or reviewing hooks to verify that automatic methods arrive. The service sends methods once per thread when enabled. If hooks are unavailable and the user asks for the methods, use `lesson_lookup` for the relevant phase. For on-demand subagent advice, use `router_advice` when requested and follow the host's delegation and model-override rules.

## Install, update, and sign in

- Install with `codex plugin marketplace add floating-thoughts/agent-plugin-codex`, then `codex plugin add agent-services@agent-plugin-codex`. The desktop plugin UI can also install it from the configured marketplace.
- To update an existing installation, run `codex plugin marketplace upgrade agent-plugin-codex` to refresh the marketplace, then `codex plugin add agent-services@agent-plugin-codex` to install the refreshed package. Check **Review hooks** for new or changed definitions after the update.
- Sign in from the desktop plugin's connect action when available, or run `codex mcp login agent-services` in a terminal. The browser asks for an account email and one-time code. Sign in again if `status` reports an expired or missing sign-in. One account has one seat across the Codex and Claude Code plugins. Signing in on one ends the other sign-in.
- If `codex mcp list` shows a disabled or local-command `agent-services` entry, check for an older `[mcp_servers.agent-services]` entry in `~/.codex/config.toml`. A user-configured entry can shadow the bundled server. The user can remove an obsolete override with `codex mcp remove agent-services` and retry sign-in.
- `codex mcp logout agent-services` removes the locally stored sign-in. The server ends the sign-in when it is replaced, ended by an admin, or expires after 30 days unused or 90 days from sign-in.

## Tools and hook behavior

- `status`: check sign-in, license, organization pause, and methods choice.
- `lesson_lookup`: get methods for one phase (`plan`, `implement`, `test`, `review`, `deliver`, or `checkpoint`).
- `router_advice`: get model and reasoning advice for a `task_name` that starts with a task word.
- `checkpoint_advice`: check whether to compact the conversation.
- `setup`: read `methods preview` or `info hooks`.
- `setup_methods`: change the methods choice only when the user supplies their choice (`methods suggest`, `methods on`, `methods off`, `methods accept`, or `methods keep`).
- `setup_sharing`: read `sharing preview`, or apply `sharing off` when the user asks. Sharing turns on only with an explicit Yes on the sign-in page.

On Codex 0.169.1, the legacy `multi_agent` spawn hook matches `spawn_agent` and sends the turn ID. The `multi_agent_v2` hook matches `collaborationspawn_agent` and sends the task name. The service can return advice as a block reason on the first attempt. If Codex permits retrying, retry the same task with the parameters allowed by the host and the user's instructions. The plugin's advice does not grant permission to delegate or override a model.

If the service is unavailable, the hooks fail open. Codex can wait up to 5 seconds for a session, prompt, or spawn hook and up to 2 seconds for a model request usage hook. See [what the plugin sends](https://github.com/floating-thoughts/agent-plugin-codex/blob/main/DATA.md) before enabling hooks.
