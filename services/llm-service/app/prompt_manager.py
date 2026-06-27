import json
import logging
import os
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class PromptManager:
    """Manages prompt templates: loading from files, caching, and variable substitution."""

    def __init__(self, templates_dir: Optional[str] = None):
        self.templates_dir = Path(templates_dir or settings.PROMPT_TEMPLATES_DIR)
        self._registry: dict[str, str] = {}
        self._load_templates()

    def _load_templates(self):
        """Load all .txt template files from the templates directory."""
        if not self.templates_dir.exists():
            logger.warning("Templates directory not found: %s", self.templates_dir)
            return
        for filepath in self.templates_dir.glob("*.txt"):
            name = filepath.stem
            try:
                self._registry[name] = filepath.read_text(encoding="utf-8")
                logger.info("Loaded prompt template: %s", name)
            except Exception as exc:
                logger.error("Failed to load template %s: %s", name, exc)

    def get_template(self, name: str) -> str:
        """Get a raw template by name."""
        if name not in self._registry:
            raise KeyError(f"Prompt template '{name}' not found. Available: {list(self._registry.keys())}")
        return self._registry[name]

    def render(self, name: str, **variables) -> str:
        """Render a template with variable substitution.

        Supports both simple {var} and complex nested objects.
        Variables that are dicts or lists are serialized to pretty JSON.
        """
        template = self.get_template(name)
        formatted_vars = {}
        for key, value in variables.items():
            if isinstance(value, (dict, list)):
                formatted_vars[key] = json.dumps(value, indent=2, default=str)
            elif isinstance(value, (int, float, bool)):
                formatted_vars[key] = str(value)
            elif value is None:
                formatted_vars[key] = "N/A"
            else:
                formatted_vars[key] = str(value)

        try:
            return template.format(**formatted_vars)
        except KeyError as exc:
            logger.error("Missing variable in template '%s': %s", name, exc)
            raise ValueError(f"Missing variable in template '{name}': {exc}") from exc

    def register(self, name: str, template: str):
        """Register a new template programmatically."""
        self._registry[name] = template
        logger.info("Registered prompt template: %s", name)

    def list_templates(self) -> list[str]:
        """List all available template names."""
        return list(self._registry.keys())

    def reload(self):
        """Reload all templates from disk."""
        self._registry.clear()
        self._load_templates()


# Module-level singleton
_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    global _manager
    if _manager is None:
        _manager = PromptManager()
    return _manager
