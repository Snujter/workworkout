import vlc
import random
from pathlib import Path
from typing import Optional


class SoundService:
    """
    A long-lived service for audio playback.
    Not a 'Context' as it doesn't represent a UI state.
    """

    def __init__(self, directory: str = "sounds"):
        # Using Path objects is more modern and safer than os.path
        self.directory = Path(directory)

        # Initialize VLC with flags to keep it silent in a TUI
        self._instance = vlc.Instance("--no-video --quiet")
        self._player = self._instance.media_player_new()

    def _get_mp3_files(self) -> list[Path]:
        """Internal helper to refresh the list of available sounds."""
        if not self.directory.exists():
            return []
        return list(self.directory.glob("*.mp3"))

    def play_random(self) -> Optional[Path]:
        """
        Plays a random sound.
        Returns the Path of the file played, or None if no sound was played.
        """
        files = self._get_mp3_files()
        if not files:
            return None

        chosen_file = random.choice(files)

        # vlc.Media needs a string path
        media = self._instance.media_new(str(chosen_file))
        self._player.set_media(media)

        # play() is non-blocking
        if self._player.play() == -1:
            return None

        return chosen_file

    def stop(self) -> None:
        """Stops current playback."""
        self._player.stop()

    def is_playing(self) -> bool:
        """Returns True if audio is currently outputting."""
        return bool(self._player.is_playing())
