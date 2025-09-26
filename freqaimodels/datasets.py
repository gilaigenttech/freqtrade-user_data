import torch
from torch.utils.data import Dataset


class WindowDataset(Dataset):
    """
    A PyTorch Dataset for creating sliding window sequences for LSTM training.
    This dataset takes input features and labels and creates sequences of a specified window size.
    """

    def __init__(self, x, y, window_size=5):
        """
        Initialize the WindowDataset.

        Args:
            x (torch.Tensor): Input features tensor
            y (torch.Tensor): Target values tensor  
            window_size (int): Size of the sliding window for sequence creation
        """
        self.x = x
        self.y = y
        self.window_size = window_size
        
        # Ensure we have enough data for at least one window
        if len(x) < window_size:
            raise ValueError(f"Dataset length {len(x)} is smaller than window_size {window_size}")

    def __len__(self):
        """Return the number of samples in the dataset."""
        return len(self.x) - self.window_size + 1

    def __getitem__(self, idx):
        """
        Get a single sample from the dataset.
        
        Args:
            idx (int): Index of the sample to retrieve
            
        Returns:
            tuple: (sequence, target) where sequence is a window of input features
                   and target is the corresponding label
        """
        if idx + self.window_size > len(self.x):
            raise IndexError(f"Index {idx} with window_size {self.window_size} exceeds dataset length {len(self.x)}")
            
        # Create a sequence from idx to idx + window_size
        sequence = self.x[idx:idx + self.window_size]
        
        # The target is typically the label at the end of the window
        target = self.y[idx + self.window_size - 1]
        
        return sequence, target