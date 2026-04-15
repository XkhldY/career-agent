#!/usr/bin/env python3
"""
Setup script for Google ADK with internet search agent.
Creates a virtual environment, installs ADK, and sets up a search-enabled agent.
"""

import os
import subprocess
import sys
from pathlib import Path

VENV_DIR = ".venv"
AGENT_DIR = "search_agent"
PYTHON_MIN_VERSION = (3, 10)


def check_python_version():
    """Ensure Python 3.10+ is available."""
    if sys.version_info < PYTHON_MIN_VERSION:
        print(f"Error: Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}+ required.")
        print(f"Current version: {sys.version}")
        sys.exit(1)


def create_venv():
    """Create virtual environment if it doesn't exist."""
    if Path(VENV_DIR).exists():
        print(f"Virtual environment already exists at {VENV_DIR}")
        return
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    print(f"Created {VENV_DIR}")


def get_venv_python():
    """Get path to venv Python executable."""
    if sys.platform == "win32":
        return Path(VENV_DIR) / "Scripts" / "python.exe"
    return Path(VENV_DIR) / "bin" / "python"


def get_venv_pip():
    """Get path to venv pip executable."""
    if sys.platform == "win32":
        return Path(VENV_DIR) / "Scripts" / "pip.exe"
    return Path(VENV_DIR) / "bin" / "pip"


def install_adk():
    """Install google-adk in the virtual environment."""
    pip = get_venv_pip()
    print("Installing google-adk...")
    subprocess.run([str(pip), "install", "google-adk"], check=True)
    print("google-adk installed successfully")


def create_agent_project():
    """Create the search agent project structure."""
    agent_path = Path(AGENT_DIR)
    agent_path.mkdir(exist_ok=True)

    agent_py = agent_path / "agent.py"
    if not agent_py.exists():
        agent_py.write_text(AGENT_CODE, encoding="utf-8")
        print(f"Created {agent_py}")
    else:
        print(f"{agent_py} already exists, skipping")

    init_py = agent_path / "__init__.py"
    init_py.touch()
    print(f"Created {init_py}")


def create_root_env():
    """Create a single .env.example at project root; all agents use it."""
    root = Path(__file__).resolve().parent
    env_file = root / ".env"
    env_example = root / ".env.example"
    if not env_file.exists():
        if not env_example.exists():
            env_example.write_text('GOOGLE_API_KEY="your-api-key-here"\n', encoding="utf-8")
            print(f"Created {env_example} - copy to .env and add your API key")
    else:
        print(f"{env_file} already exists")


AGENT_CODE = '''"""
Search agent with Google ADK - uses internet search to answer questions.
Requires: GOOGLE_API_KEY in .env (get one at https://aistudio.google.com/app/apikey)
"""

from google.adk.agents import Agent
from google.adk.tools import google_search

# google_search is a pre-built tool - only works with Gemini 2 models
# Note: This tool must be used alone (cannot combine with other tools in same agent)
root_agent = Agent(
    name="search_agent",
    model="gemini-2.0-flash",
    description="Agent that answers questions using Google Search.",
    instruction=(
        "You are a helpful research assistant. Use Google Search to find "
        "current, accurate information. Answer questions about news, weather, "
        "facts, and anything that requires up-to-date web data."
    ),
    tools=[google_search],
)
'''


def print_next_steps():
    """Print instructions for the user."""
    activate_cmd = f"source {VENV_DIR}/bin/activate" if sys.platform != "win32" else f"{VENV_DIR}\\Scripts\\activate"
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print(f"  1. Activate the venv:  {activate_cmd}")
    print(f"  2. Add your API key to .env (project root)")
    print("     Get one at: https://aistudio.google.com/app/apikey")
    print(f"  3. Run the agent:       adk run {AGENT_DIR}")
    print("     Or web UI:           adk web --port 8000")
    print("=" * 60)


def main():
    check_python_version()
    create_venv()
    install_adk()
    create_agent_project()
    create_root_env()
    print_next_steps()


if __name__ == "__main__":
    main()
