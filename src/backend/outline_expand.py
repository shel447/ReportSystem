from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .domain.reporting.services import OutlineExpansionService


def expand_outline(outline: List[Any], input_params: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    expansion = OutlineExpansionService().expand(outline, input_params)
    return expansion.nodes, expansion.warnings
