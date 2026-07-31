"""Load protocol modules without importing Home Assistant."""

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
COMPONENTS = ROOT / "custom_components"
INTEGRATION = COMPONENTS / "denon_avr_diagnostics"

custom_components = ModuleType("custom_components")
custom_components.__path__ = [str(COMPONENTS)]
sys.modules.setdefault("custom_components", custom_components)

integration = ModuleType("custom_components.denon_avr_diagnostics")
integration.__path__ = [str(INTEGRATION)]
sys.modules.setdefault("custom_components.denon_avr_diagnostics", integration)
