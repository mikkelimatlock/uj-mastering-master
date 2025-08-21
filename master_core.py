import librosa
import numpy as np
import os

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm

from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

def try_mp3_tags(file_path):
  try:
    # if there is metadata
    audio = MP3(file_path, ID3=EasyID3)
    return audio
  except Exception as e:
    print(f"Error reading ID3 tags: {e}")
    return None

def read_mp3_tags(file_path):
  if (audio := try_mp3_tags(file_path)) is not None:
    print(f"File name: {os.path.basename(file_path)}")
    print(f"{audio['artist'][0]} - {audio['title'][0]}")
  else:
    print(f"File name: {os.path.basename(file_path)}")
    
class AudioFile:
  def __init__(self, file_path):
    self.file_path = file_path
    # file name / song name
    if (audio := try_mp3_tags(self.file_path)) is not None:
      self.song_name = f"{audio['artist'][0]} - {audio['title'][0]}"
    else:
      self.song_name = os.path.basename(self.file_path)
 
    self.y, self.sr = librosa.load(file_path)
    # load automatically normalises everything to [-1.0, 1.0]
    # and that's alright
    self.y_mono = librosa.to_mono(self.y)
    self.max_amplitude = np.max(np.abs(self.y_mono))
    self.avg_amplitude = np.mean(np.abs(self.y_mono))
    self.bpm, _ = librosa.beat.beat_track(y=self.y_mono, sr=self.sr)
  
  def display_song_name(self):
    print(self.song_name)

  def get_amplitudes(self):
    return self.max_amplitude, self.avg_amplitude
  
  def get_bpm(self):
    return self.bpm
  
  def get_energy_levels_over_time(self, window = 10, hop = 2):
    """_summary_

    Args:
        window (int, optional): Length of rolling RMS window in seconds. Defaults to 10.
        hop (int, optional): Length of window hop in seconds. Defaults to 2.
    """
    # check if the window and hop are the same as before    
    if (not hasattr(self, 'window')) or ((self.window != window) or (self.hop != hop)):
      self.window, self.hop = window, hop
      # only calculate if not already calculated
      if not hasattr(self, 'rms_array'):
        # window and hop are in seconds
        window_samples = window * self.sr
        hop_samples = hop * self.sr
        
        # Calculate RMS over the rolling windows
        self.rms_array = librosa.feature.rms(y=self.y, frame_length=window_samples, hop_length=hop_samples)
  
  def _get_times(self):
    """Get time array for RMS data. Internal method for GUI integration."""
    if not hasattr(self, 'rms_array'):
      self.get_energy_levels_over_time()
    return librosa.frames_to_time(np.arange(self.rms_array.shape[1]), sr=self.sr, hop_length=self.hop*self.sr)
    
  def plot_energy_levels_over_time(self, display='window'):  
    """_summary_

    Args:
        display (str, optional): Option for where to display the plot. Defaults to 'window'.
                                 'window' - display in a pyplot window
                                 'gui' - for directing to the GUI (TBD)
    """
    if not hasattr(self, 'rms_array'):
      self.get_energy_levels_over_time()

    # Convert frame indices to time
    times = librosa.frames_to_time(np.arange(self.rms_array.shape[1]), sr=self.sr, hop_length=self.hop*self.sr)
    
    
    # Normalize RMS for color mapping
    # check maximum power to determine mastering headspace:
    # a -6 dBFS headroom should yield a max power of around 0.25
    # otherwise could go anywhere, but we take 0.6
    local_max_power = np.max(self.rms_array)
    if local_max_power > 0.3:
      norm = mcolors.Normalize(vmin=0, vmax=0.6)
      maxpower = 0.6
    else:
      norm = mcolors.Normalize(vmin=0, vmax=0.3)
      maxpower = 0.3
    
    # colour map
    cmap = cm.autumn
    
    # Plot
    if display == 'window':
      fig, ax = plt.subplots(figsize=(10, 4))
      ax.set_ylim(0., maxpower)
      for i in range(len(times)-1):
          ax.fill_between(times[i:i+2], 0, self.rms_array[0][i], color=cmap(norm(self.rms_array[0][i])), edgecolor='none')
      
      # Adding a colorbar to indicate the scale of RMS values
      sm = cm.ScalarMappable(cmap=cmap, norm=norm)
      sm.set_array([])
      cbar = plt.colorbar(sm, ax=ax, label='RMS Power')
      # cbar.ax.set_yticklabels([f"{x-60.0:.0f} dBFS" for x in cbar.get_ticks()])  # Adjust labels to show true dBFS values
      
      ax.set_ylabel('Power')
      ax.set_xlabel('Time')
      ax.set_title(f'{os.path.basename(self.file_path)}')

      plt.show(block=False)
      plt.pause(0.001)
      
    


def analyze_track_librosa(file_path):
  # Load the audio file
  # y is the audio time series and sr is the sampling rate
  y, sr = librosa.load(file_path)

  # Calculate the maximum amplitude
  # Librosa's load function normalizes the audio to [-1, 1], so we scale it back
  max_amplitude = np.max(np.abs(y))
  # Average amplitude
  avg_amplitude = np.mean(np.abs(y))
  
  # Convert max amplitude to dBFS
  max_amplitude_dBFS = librosa.amplitude_to_db([max_amplitude], ref=1.0)
  avg_amplitude_dBFS = librosa.amplitude_to_db([avg_amplitude], ref=1.0)

  # Calculate RMS in dB
  S, phase = librosa.magphase(librosa.stft(y))
  rms_stft = librosa.feature.rms(S=S)
  rms = librosa.feature.rms(y=y)
  avg_power_dBFS_stft = 20 * np.log10(np.mean(rms_stft))
  avg_power_dBFS = 20 * np.log10(np.mean(rms))

  return max_amplitude_dBFS[0], avg_amplitude_dBFS[0], avg_power_dBFS, avg_power_dBFS_stft

def plot_macro_time_power_graph(file_path):
    # Load the audio file
    y, sr = librosa.load(file_path, mono=True)

    # Define the window and hop length
    # 10 seconds window and 1 second hop
    window_length = int(sr * 10)  # 10 seconds in samples
    hop_length = int(sr * 1)  # 1 second in samples

    # Calculate RMS over the rolling windows
    rms = librosa.feature.rms(y=y, frame_length=window_length, hop_length=hop_length)

    # Convert frame indices to time
    times = librosa.frames_to_time(np.arange(rms.shape[1]), sr=sr, hop_length=hop_length)

    # Normalize RMS for color mapping
    norm = mcolors.Normalize(vmin=0, vmax=0.4)

    # Choose a colormap
    cmap = cm.autumn

    # Plot
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_ylim(0., 0.4)
    for i in range(len(times)-1):
        ax.fill_between(times[i:i+2], 0, rms[0][i], color=cmap(norm(rms[0][i])), edgecolor='none')
    
    # Adding a colorbar to indicate the scale of RMS values
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, label='RMS Power')
    # cbar.ax.set_yticklabels([f"{x-60.0:.0f} dBFS" for x in cbar.get_ticks()])  # Adjust labels to show true dBFS values
    
    ax.set_ylabel('Power')
    ax.set_xlabel('Time')
    # ax.set_title(f'{os.path.basename(file_path)}')
    # plt.ylabel('Power')
    # plt.xlabel('Time (s)')
    # plt.title(f'{os.path.basename(file_path)}')
    plt.show(block=False)
    plt.pause(0.001)



def find_mp3_files(directory):
    mp3_files = []
    # Walk through the directory
    for root, dirs, files in os.walk(directory):
        # Filter and append .mp3 files
        for file in files:
            if file.endswith(".mp3"):
                mp3_files.append(os.path.join(root, file))
    return mp3_files


if __name__ == '__main__':
  # Legacy batch processing mode - runs when master_core.py is executed directly
  # For GUI usage, run main.py instead
  
  print("Running legacy batch analysis mode...")
  print("For the new GUI interface, please run: python main.py")
  print()
  
  # Replace 'path/to/your/audiofile.mp3' with the path to your audio file
  file_path = []
  with open('./files.txt', 'r') as f:
    for line in f:
      if line[0] != '#' and line[0] != ';':
        file_path.append(line.strip())

  for file in file_path:
    # max_amplitude, avg_amplitude, avg_power, avg_power_stft = analyze_track_librosa(file)
    # # read_mp3_tags(file)
    # print(f"Maximum Amplitude: {max_amplitude:.2f} dBFS")
    # print(f"Average Amplitude: {avg_amplitude:.2f} dBFS")
    # print(f"Average Power: {avg_power:.2f} dBFS")
    # print(f"Average Power (STFT): {avg_power_stft:.2f} dBFS")
    currentsong = AudioFile(file)
    currentsong.display_song_name()
    print(f"BPM: {currentsong.get_bpm()}")
    currentsong.plot_energy_levels_over_time()
    # plot_macro_time_power_graph(file)

  plt.show()
