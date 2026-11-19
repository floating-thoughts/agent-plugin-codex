"""Verify onboarding and hook review in the installed Codex runtime.

Run with `python tests/check_codex.py` and `codex` on PATH. Uses a temporary
Codex profile and a local marketplace. No sign-in or model request is needed.
"""

import json
import os
from pathlib import Path
from queue import Queue
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = "agent-services@agent-plugin-codex"
PREVIOUS_PLUGIN = "agent-services@agent-plugin"
MARKETPLACE = ".agents/plugins/marketplace.json"
MANIFEST = ".codex-plugin/plugin.json"
FILES = [MARKETPLACE, MANIFEST, ".mcp.json", "hooks/hooks.json", "skills/agent-services/SKILL.md"]


def read_catalog(marketplace, env):
    with subprocess.Popen(
        ["codex", "app-server"], cwd=marketplace, env=env, text=True, encoding="utf-8",
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ) as process:
        responses = Queue()

        def read_responses():
            for line in process.stdout:
                message = json.loads(line)
                if "result" in message or "error" in message:
                    responses.put(message)

        Thread(target=read_responses, daemon=True).start()

        def send(message):
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()

        def request(id_, method, params):
            send({"id": id_, "method": method, "params": params})
            response = responses.get(timeout=15)
            assert response.get("id") == id_ and "error" not in response, response
            return response["result"]

        try:
            request(1, "initialize", {
                "clientInfo": {"name": "agent-services-test", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True},
            })
            send({"method": "initialized"})
            plugin = request(2, "plugin/read", {
                "pluginName": "agent-services", "marketplacePath": str(marketplace / MARKETPLACE),
            })["plugin"]
            entries = request(3, "hooks/list", {"cwds": [str(marketplace)]})["data"]
            return plugin, [hook for entry in entries for hook in entry["hooks"]]
        finally:
            process.terminate()
            process.wait(timeout=5)


def write_review_state(config, hooks, plugin_id):
    with config.open("a", encoding="utf-8") as file:
        for hook in hooks:
            key = hook["key"].replace(PLUGIN + ":", plugin_id + ":", 1)
            declaration, _, content = hook["currentHash"].partition("/")
            file.write(f'\n[hooks.state."{key}"]\ntrusted_hash = "{declaration}"\n')
            if content:
                file.write(f'trusted_content_hash = "{content}"\n')


def check_codex():
    with TemporaryDirectory(prefix="agent-services-") as directory:
        marketplace = Path(directory) / "marketplace"
        profile = Path(directory) / "profile"
        profile.mkdir()
        env = dict(os.environ, CODEX_HOME=str(profile))
        for name in FILES:
            target = marketplace / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

        commands = [["marketplace", "add", str(marketplace)], ["add", PLUGIN]]
        for command in commands:
            subprocess.run(["codex", "plugin", *command, "--json"], env=env,
                           capture_output=True, check=True, timeout=30)

        plugin, hooks = read_catalog(marketplace, env)
        onboarding = plugin["onboardingSkill"]
        assert onboarding and onboarding["name"] == "agent-services:agent-services", plugin
        assert plugin["mcpServers"] == ["agent-services"], plugin
        assert len(hooks) == 5 and all(hook["pluginId"] == PLUGIN for hook in hooks), hooks
        assert {hook["trustStatus"] for hook in hooks} == {"untrusted"}, hooks

        config = profile / "config.toml"
        write_review_state(config, hooks, PREVIOUS_PLUGIN)
        _, hooks = read_catalog(marketplace, env)
        assert len(hooks) == 5 and {hook["trustStatus"] for hook in hooks} == {"untrusted"}, hooks

        write_review_state(config, hooks, PLUGIN)
        _, hooks = read_catalog(marketplace, env)
        assert len(hooks) == 5 and {hook["trustStatus"] for hook in hooks} == {"trusted"}, hooks
    print("Codex loads the onboarding skill and applies review to the current marketplace only")


if __name__ == "__main__":
    check_codex()
