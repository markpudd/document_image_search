#!/usr/bin/env python3
"""
Centralized configuration loader for Document Image Search projects.

This module provides utilities to load environment variables from .env files,
searching both the local directory and parent directories (up to the project root).

Usage:
    from config_loader import load_config
    load_config()  # Loads from local .env or parent .env files

This allows projects to use either:
1. A top-level .env file in the project root (shared configuration)
2. A local .env file in their own directory (project-specific configuration)
3. Both (local .env takes precedence)
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_config(start_path=None):
    """
    Load environment variables from .env files.

    Searches for .env files in the following order:
    1. Current directory (or start_path if provided)
    2. Parent directories up to the project root

    Local .env files take precedence over parent .env files.

    Args:
        start_path: Optional starting directory (defaults to current file's directory)
    """
    if start_path is None:
        # Use the calling script's directory
        import inspect
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        start_path = Path(caller_frame.f_globals['__file__']).parent
    else:
        start_path = Path(start_path)

    current_path = start_path.resolve()
    loaded_files = []

    # Search up the directory tree for .env files
    max_levels = 5  # Prevent infinite loops
    for _ in range(max_levels):
        env_file = current_path / '.env'
        if env_file.exists():
            # Load with override=False so local variables take precedence
            load_dotenv(env_file, override=False)
            loaded_files.append(str(env_file))

        # Check if we've reached the project root (contains .git or is filesystem root)
        if (current_path / '.git').exists() or current_path == current_path.parent:
            break

        current_path = current_path.parent

    if loaded_files:
        return loaded_files
    else:
        # Still try to load from current directory as fallback
        load_dotenv(override=False)
        return []


def get_project_root():
    """
    Find the project root directory (where .git exists or top-level directory).

    Returns:
        Path to project root directory
    """
    current_path = Path.cwd()

    max_levels = 10
    for _ in range(max_levels):
        if (current_path / '.git').exists():
            return current_path

        if current_path == current_path.parent:
            # Reached filesystem root
            return current_path

        current_path = current_path.parent

    return Path.cwd()


if __name__ == "__main__":
    # Test the config loader
    print("Testing configuration loader...")
    print(f"Current directory: {Path.cwd()}")
    print(f"Project root: {get_project_root()}")
    print()

    loaded = load_config()
    if loaded:
        print(f"Loaded {len(loaded)} .env file(s):")
        for f in loaded:
            print(f"  - {f}")
    else:
        print("No .env files found")

    # Show some example configuration values (without revealing secrets)
    print("\nSample configuration (presence check):")
    sample_vars = [
        'AI_PROVIDER',
        'ANTHROPIC_API_KEY',
        'OPENAI_API_KEY',
        'ELASTICSEARCH_HOST',
        'ELASTICSEARCH_INDEX'
    ]

    for var in sample_vars:
        value = os.getenv(var)
        if value:
            # Show only first/last chars for API keys
            if 'API_KEY' in var or 'PASSWORD' in var:
                if len(value) > 8:
                    masked = f"{value[:4]}...{value[-4:]}"
                else:
                    masked = "****"
                print(f"  {var}: {masked}")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: <not set>")
