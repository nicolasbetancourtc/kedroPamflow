""" 
Utilities for Acoustic Indices Computation

This module provides functions and classes to compute various acoustic indices
from audio signals. It includes preprocessing functions, a class for computing
acoustic indices, and parallel processing capabilities.
"""

import os
import concurrent.futures
import pandas as pd
import logging
from maad import sound, features, util

# Set up logging
logger = logging.getLogger(__name__)

#%%
class AcousticIndices:
    """
    Class to compute acoustic indices from a spectrogram.
    This class encapsulates the functionality to compute various acoustic indices
    from a spectrogram. It takes the audio signal, spectrogram, time and frequency
    vectors, and parameters as input. The indices can be computed using the
    corresponding methods.
    Attributes
    ----------
    s : 1d numpy array
        Acoustic data (audio signal).
    Sxx : 2d numpy array of floats
        Amplitude spectrogram computed with maad.sound.spectrogram mode='amplitude'.
    tn : 1d ndarray of floats
        Time vector with temporal indices of spectrogram.
    fn : 1d ndarray of floats
        Frequency vector with temporal indices of spectrogram.
    params : dict
        Parameters for computing acoustic indices. The keys are the names of the
        indices to be computed, and the values are the corresponding parameters.
    Methods
    -------
    compute_ACI(params)
        Compute Acoustic Complexity Index (ACI).
    compute_ADI(params)
        Compute Acoustic Diversity Index (ADI).
    compute_BI(params)
        Compute Bioacoustics Index (BI).
    compute_Hf(params)
        Compute Frequency Entropy (Hf).
    compute_Ht(params)
        Compute Temporal Entropy (Ht).
    compute_H(params)
        Compute Acoustic Entropy (H).
    compute_NDSI(params)
        Compute Normalized Difference Soundscape Index (NDSI).
    compute_NP(params)
        Compute Number of Peaks (NP).
    compute_RMS(params)
        Compute Root Mean Square (RMS).
    compute_SC(params)
        Compute Spectral Cover (SC).
    compute_selected_indices()
        Compute only selected indices based on parameters.
    _convert_lists_to_tuples(data)
        Recursively convert all lists in a dictionary to tuples.
    """
    def __init__(self, s, Sxx, tn, fn, params):
        self.s = s
        self.Sxx = Sxx
        self.tn = tn
        self.fn = fn
        self.params = self._convert_lists_to_tuples(params)

        # Convert spectrogram scales once to avoid redundancy
        self.Sxx_power = Sxx**2
        self.Sxx_dB = util.amplitude2dB(Sxx)

    def compute_ACI(self, params):
        """Compute Acoustic Complexity Index (ACI)."""
        return features.acoustic_complexity_index(self.Sxx)[2]

    def compute_ADI(self, params):
        """Compute Acoustic Complexity Index (ACI)."""
        return features.acoustic_diversity_index(self.Sxx, self.fn, **params)

    def compute_BI(self, params):
        """Compute Bioacoustics Index (BI)."""
        return features.bioacoustics_index(self.Sxx, self.fn, **params)
    
    def compute_Hf(self, params):
        """Compute Frequency Entropy (Hf)."""
        return features.frequency_entropy(self.Sxx_power)[0]
    
    def compute_Ht(self, params):
        """Compute Temporal Entropy (Ht)."""
        return features.temporal_entropy(self.s)
    
    def compute_H(self, params):
        """Compute Acoustic Entropy (H)."""
        Hf = features.frequency_entropy(self.Sxx_power)[0]
        Ht = features.temporal_entropy(self.s)
        return Hf * Ht

    def compute_NDSI(self, params):
        """Compute Normalized Difference Soundscape Index (NDSI)."""
        return features.soundscape_index(self.Sxx_power, self.fn, **params)[0]
    
    def compute_NP(self, params):
        """Compute Number of Peaks (NP)."""
        return features.number_of_peaks(self.Sxx_power, self.fn, **params)

    def compute_RMS(self, params):
        """Compute Root Mean Square (RMS)."""
        return util.rms(self.s)
    
    def compute_SC(self, params):
        """Compute Spectral Cover (SC)."""
        return features.spectral_cover(self.Sxx_dB, self.fn, **params)[0]

    def _convert_lists_to_tuples(self, data):
        """Recursively convert all lists in a dictionary to tuples."""
        if isinstance(data, dict):
            return {key: self._convert_lists_to_tuples(value) for key, value in data.items()}
        elif isinstance(data, list):
            return tuple(self._convert_lists_to_tuples(item) for item in data)
        else:
            return data

    def compute_selected_indices(self):
        """Compute only selected indices based on parameters."""
        if not isinstance(self.params, dict):
            raise ValueError("Expected self.params to be a dictionary.")

        results = {}
        for index in self.params.keys():
            method_name = f"compute_{index}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                results[index] = method(self.params[index])
            else:
                logger.info(f"Warning: Method {method_name} not found in class.")

        return pd.Series(results)

#%% 
def preprocess_audio_file(path_audio, params):
    """
    Preprocess audio file by resampling and filtering.
    Parameters
    ----------
    path_audio : str
        Path to the audio file.
    params : dict
        Parameters for preprocessing, including target sampling frequency,
        filter type, filter cut-off frequency, filter order, and spectrogram parameters.
    Returns
    -------
    s : 1d numpy array
        Resampled audio signal.
    Sxx : 2d numpy array
        Amplitude spectrogram.
    tn : 1d ndarray of floats
        Time vector with temporal indices of spectrogram.
    fn : 1d ndarray of floats
        Frequency vector with temporal indices of spectrogram.
    """
    
    # Load parameters
    target_fs = params["target_fs"]
    filter_type = params["filter_type"]
    filter_cut = params["filter_cut"]
    filter_order = params["filter_order"]
    nperseg = params["nperseg"]
    noverlap = params["noverlap"]

    # load audio
    s, fs = sound.load(path_audio)
    s = sound.resample(s, fs, target_fs, res_type="scipy_poly")
    if filter_type is not None:
        s = sound.select_bandwidth(
            s, target_fs, ftype=filter_type, fcut=filter_cut, forder=filter_order
        )

    # Compute the amplitude spectrogram and acoustic indices
    Sxx, tn, fn, _ = sound.spectrogram(
        s, target_fs, nperseg=nperseg, noverlap=noverlap, mode="amplitude")
    
    return s, Sxx, tn, fn
    
# %%
def compute_acoustic_indices_single_file(
    path_audio,
    params_preprocess=None,
    params_indices=None,
    verbose=True,
):
    """
    Compute acoustic indices for a single audio file.
    Parameters
    ----------
    path_audio : str
        Path to the audio file.
    params_preprocess : dict
        Parameters for preprocessing, including target sampling frequency,
        filter type, filter cut-off frequency, filter order, and spectrogram parameters.
    params_indices : dict
        Parameters for computing acoustic indices.
    verbose : bool
        If True, print progress messages.
    Returns
    -------
    df_indices_file : pd.DataFrame
        Acoustic indices for the audio file.
    """
    if verbose:
        print(f"Processing file {path_audio}", end="\r")
    
    # Preprocess audio file
    s, Sxx, tn, fn = preprocess_audio_file(path_audio, params_preprocess)
    
    # Compute acoustic indices
    indices_computer = AcousticIndices(s, Sxx, tn, fn, params_indices)
    df_indices_file = indices_computer.compute_selected_indices()

    return df_indices_file

#%%
def validate_n_jobs(n_jobs):
    """
    Validate and normalize the n_jobs parameter.
    
    Parameters
    ----------
    n_jobs : int or None
        Number of jobs to run in parallel. -1 means using all available CPU cores.
    
    Returns
    -------
    int
        Validated number of jobs.
    
    Raises
    ------
    ValueError
        If n_jobs is invalid (e.g., 0 or negative other than -1).
    """
    if n_jobs is None:
        return 1
    if n_jobs == -1:
        return os.cpu_count()
    if n_jobs <= 0:
        raise ValueError("n_jobs must be a positive integer or -1 for all cores.")
    return n_jobs

# %%

# %% Parellel computing
def compute_indices_parallel(
    data, params_preprocess, params_indices, n_jobs=-1
):
    """
    Compute acoustic indices in parallel for a list of audio files.
    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing metadata of media files, including file paths.
    params_preprocess : dict
        Parameters for preprocessing, including target sampling frequency,
        filter type, filter cut-off frequency, filter order, and spectrogram parameters.
    params_indices : dict
        Parameters for computing acoustic indices.
    n_jobs : int
        Number of parallel jobs to run. If -1, use all available CPU cores.
    Returns
    -------
    df_out : pd.DataFrame
        DataFrame containing the computed acoustic indices for all audio files.
    """
    n_jobs = validate_n_jobs(n_jobs)

    # Use concurrent.futures for parallel execution
    files = data[["filePath", "mediaID"]].to_dict(orient="records")
    with concurrent.futures.ProcessPoolExecutor(max_workers=n_jobs) as executor:
        # Use submit for each task
        futures = {
            executor.submit(
                compute_acoustic_indices_single_file,
                file["filePath"],
                params_preprocess,
                params_indices,
                verbose=True,
            ): file["mediaID"]
            for file in files
        }

        # Get results when tasks are completed
        results = []
        for future in concurrent.futures.as_completed(futures):
            media_id = futures[future]
            try:
                result = future.result()
                result["mediaID"] = media_id
                results.append(result)

            except Exception as e:
                logger.error(f"Error processing file {media_id}: {e}")

    return pd.DataFrame(results)
