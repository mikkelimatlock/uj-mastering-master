import os

import librosa
import numpy as np

from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

from font_manager import safe_title


def _try_mp3_tags(file_path):
  try:
    return MP3(file_path, ID3=EasyID3)
  except Exception:
    return None


class AudioFile:
  def __init__(self, file_path):
    self.file_path = file_path
    audio = _try_mp3_tags(self.file_path)
    artist = audio.get('artist', [None])[0] if audio is not None else None
    title = audio.get('title', [None])[0] if audio is not None else None
    if artist and title:
      self.song_name = safe_title(f"{artist} - {title}")
    else:
      self.song_name = safe_title(os.path.basename(self.file_path))

    # librosa.load normalises to [-1.0, 1.0]
    self.y, self.sr = librosa.load(file_path)
    self.y_mono = librosa.to_mono(self.y)
    self.max_amplitude = np.max(np.abs(self.y_mono))
    self.avg_amplitude = np.mean(np.abs(self.y_mono))
    self.bpm, _ = librosa.beat.beat_track(y=self.y_mono, sr=self.sr)

  def get_bpm(self):
    # librosa.beat.beat_track returns numpy array - extract scalar value
    if isinstance(self.bpm, np.ndarray):
      return float(self.bpm[0]) if len(self.bpm) > 0 else 0.0
    return float(self.bpm)

  def get_energy_levels_over_time(self, window=10, hop=2):
    """Compute rolling RMS power.

    Args:
        window: Rolling window length in seconds.
        hop: Hop length in seconds.
    """
    if (not hasattr(self, 'window')) or (self.window != window) or (self.hop != hop):
      self.window, self.hop = window, hop
      if not hasattr(self, 'rms_array'):
        window_samples = window * self.sr
        hop_samples = hop * self.sr
        self.rms_array = librosa.feature.rms(
            y=self.y, frame_length=window_samples, hop_length=hop_samples
        )

  def get_times(self):
    """Time-axis values matching the RMS frames."""
    if not hasattr(self, 'rms_array'):
      self.get_energy_levels_over_time()
    return librosa.frames_to_time(
        np.arange(self.rms_array.shape[1]), sr=self.sr, hop_length=self.hop * self.sr
    )
