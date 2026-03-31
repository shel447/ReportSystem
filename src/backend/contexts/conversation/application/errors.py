from __future__ import annotations


class ConversationReplyError(Exception):
    """Soft conversation failure that should be surfaced as an assistant reply."""

