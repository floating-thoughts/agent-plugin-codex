"""Static checks for this Codex plugin package. Run: python tests/check_package.py (repo root as cwd or as the first argument)."""
import json, re, sys, pathlib
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent); fails = []
def ok(c, m): (None if c else fails.append(m))
j = {p: json.loads((R / p).read_text(encoding="utf-8")) for p in
     [".codex-plugin/plugin.json", ".mcp.json", "hooks/hooks.json", ".agents/plugins/marketplace.json"]}
man = j[".codex-plugin/plugin.json"]
ok(man["name"] == "agent-services" and re.fullmatch(r"\d+\.\d+\.\d+(-beta\.\d+)?", man["version"]), "manifest name/version")
ok(man["skills"] == "./skills/" and
   man["extensions"]["com.openai"]["onboardingSkill"] == "./skills/agent-services/SKILL.md",
   "manifest exposes the agent-services skill for setup")
ok(man["mcpServers"] == "./.mcp.json" and man["hooks"] == "./hooks/hooks.json",
   "manifest references the bundled MCP and hook definitions")
ok(all("agent-plugin-codex" in man["interface"][k] for k in ("websiteURL", "privacyPolicyURL", "termsOfServiceURL")), "manifest URLs")
for k in ("privacyPolicyURL", "termsOfServiceURL"):
    ok((R / man["interface"][k].rsplit("/blob/main/", 1)[1]).exists(), f"{k} target file exists")
srv = j[".mcp.json"]["mcpServers"]["agent-services"]
ok(srv == {"type": "http", "url": "https://svc.yzcanadianholdings.com/mcp", "oauth": {"clientId": "agent-services-codex"}}, ".mcp.json")
mk = j[".agents/plugins/marketplace.json"]
ok(mk["plugins"][0]["name"] == man["name"] and "version" not in mk["plugins"][0], "marketplace entry")
H = j["hooks/hooks.json"]["hooks"]
expect = {
 "SessionStart": [(None, "hook_session", {"event": "SessionStart"}, 5)],
 "UserPromptSubmit": [(None, "hook_session", {"event": "UserPromptSubmit"}, 5)],
 "PreToolUse": [("collaborationspawn_agent", "hook_spawn", {"v": "v2", "task": "${tool_input.task_name}"}, 5),
                ("spawn_agent", "hook_spawn", {"v": "v1", "turn": "${turn_id}"}, 5)],
 "PostModelRequest": [(None, "hook_usage", {"model": "${model}", "status": "${status}", "usage": "${token_usage}"}, 2)],
}
ok(set(H) == set(expect), "hook events")
allowed = {"${tool_input.task_name}", "${turn_id}", "${model}", "${status}", "${token_usage}"}
for ev, groups in H.items():
    got = [(g.get("matcher"), h["tool"], h["input"], h["timeout"]) for g in groups for h in g["hooks"]]
    ok(got == expect.get(ev), f"{ev} hooks exact")
    for g in groups:
        m = g.get("matcher")
        # Codex 0.169.1 treats plain alphanumeric and underscore names as exact matches.
        ok(m is None or re.fullmatch(r"[A-Za-z0-9_|]+", m), f"{ev} matcher {m} is exact")
        for h in g["hooks"]:
            ok(h["type"] == "mcp_tool" and h["server"] == "agent-services", f"{ev} handler type/server")
            ok(set(h) <= {"type", "server", "tool", "input", "timeout", "statusMessage"}, f"{ev} handler keys valid for mcp_tool")
            for v in h["input"].values():
                for ph in re.findall(r"\$\{[^}]*\}", v): ok(ph in allowed, f"placeholder {ph}")
sk = (R / "skills/agent-services/SKILL.md").read_text(encoding="utf-8")
ok(sk.startswith("---\nname: agent-services\ndescription: "), "skill frontmatter")
tools = {"status", "lesson_lookup", "router_advice", "checkpoint_advice", "setup", "setup_methods", "setup_sharing"}
named = set(re.findall(r"^- `([a-z_]+)`:", sk, re.M)); ok(named <= tools and named, f"skill tool names {named - tools}")
ok("upgrade agent-plugin-codex" in sk and mk["name"] == "agent-plugin-codex", "skill upgrade command matches marketplace name")
print("FAIL:\n" + "\n".join(fails) if fails else "all checks passed"); sys.exit(1 if fails else 0)
