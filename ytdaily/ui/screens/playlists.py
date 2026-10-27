"""
Playlist management screen using generic item manager.
"""

from ytdaily.core.state import StateManager
from ytdaily.ui.screens.channels import manage_items


def manage_playlists(state: StateManager) -> None:
    """Manage playlists screen."""
    manage_items(
        state=state,
        item_type="Playlist",
        items_dict=state.playlists,
        id_label="playlist or collection URL",
        id_example="e.g. YouTube, TikTok, or other media playlist URL",
    )
