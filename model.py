import sys
from threading import RLock
from typing import Optional

import albumentations as A
import numpy as np
import segmentation_models_pytorch as smp
import torch
from albumentations.pytorch.transforms import ToTensorV2


def get_mean_and_std(encoder: str = "timm-efficientnet-b3", encoder_weights: str = "noisy-student") -> tuple:
    """
    Gets the average and standard deviation for image normalization for a given encoder.

    Parameters
    ----------
    encoder : str
        The key (name) for getting a specific encoder.
    encoder_weights : str
        The key to obtain the weights of the encoder.

    Returns
    -------
    tuple
        Tuple of two elements to normalize the input images.
        The first element is the mean value, the second is the standard deviation.
        Elements are also tuples with three values.

    """
    preprocessing_params = smp.encoders.get_preprocessing_params(encoder, encoder_weights)
    return preprocessing_params["mean"], preprocessing_params["std"]


def prepare_model(model_path: str = "models/teb3_ns_unet_9665.pth") -> tuple:
    """
    Prepares the objects that are required for segmentation:
    - a neural network;
    - a device for computing;
    - the mean and standard deviation for the normalization of input images.

    Parameters
    ----------
    model_path : str
        Path to the file that is a pre-trained neural network.

    Returns
    -------
    tuple
        A tuple of four elements:
        - a neural network;
        - a device for computing;
        - a mean for the normalization of input images;
        - a standard deviation for the normalization of input images.

    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = torch.load(model_path, map_location=device).eval()
    return model, device, get_mean_and_std()


def transforms(image_size: int = 224, mean: tuple = None, std: tuple = None) -> A.Compose:
    """
    Returns a set of functions for performing transformations when preparing images before segmentation.

    Parameters
    ----------
    image_size : int
        Image size.
    mean : tuple
        The mean value for normalization.
    std : tuple
        The standard deviation for normalization.

    Returns
    -------
    albumentations.Compose
        List of functions that perform transformations on the image and mask
        that are wrapped in a special container.

    """
    return A.Compose([
        A.Resize(image_size, image_size),
        A.Normalize(mean=mean, std=std),
        ToTensorV2(True)
    ])


def predict_image(model: torch.nn.Module, device: torch.device, image: np.ndarray, transforms: A.Compose = None,
                  threshold: float = None, source_size: bool = False) -> np.ndarray:
    """
    Performs segmentation of vertebrae in the image and returns the resulting mask.

    This is a non-thread-safe function.

    Parameters
    ----------
    model : torch.nn.Module
        Neural network.
    device : torch.device
        Device for operation of a neural network (CPU, GPU, TPU, etc.).
    image : numpy.ndarray
        The original image in the format of a multidimensional array WxHx3.
        Where W is the width, H is the height, 3 is the number of color channels (RGB).
    transforms : A.Compose
        A set of transformations for the image before feeding it to the neural network.
    threshold : float
        The threshold for the mask.
    source_size : bool
        The need to return the mask to the original image size.

    Returns
    -------
    numpy.ndarray
        The result of segmentation in the form of a multidimensional array
        of size WxH, if source_size is true, otherwise 224x224 pixels.

    """
    to_source_size_transform = A.Resize(image.shape[0], image.shape[1])
    if transforms is not None:
        image = transforms(image=image)["image"]
    prediction = model(image.unsqueeze(dim=0).to(device))
    prediction = prediction.detach().cpu().sigmoid().numpy()
    if threshold is not None:
        prediction = np.float32(prediction > threshold)
    prediction = prediction[0][0]
    if source_size:
        return to_source_size_transform.apply(prediction)
    return prediction


def predict_image_safe(model: torch.nn.Module, device: torch.device, image: np.ndarray, transforms: A.Compose = None,
                       threshold: float = None, source_size: bool = False) -> Optional[np.ndarray]:
    """
    Performs segmentation of vertebrae in the image and returns the resulting mask.

    This is a thread-safe function that runs on a single thread at a single point in time.

    Parameters
    ----------
    model : torch.nn.Module
        Neural network.
    device : torch.device
        Device for operation of a neural network (CPU, GPU, TPU, etc.).
    image : numpy.ndarray
        The original image in the format of a multidimensional array WxHx3.
        Where W is the width, H is the height, 3 is the number of color channels (RGB).
    transforms : A.Compose
        A set of transformations for the image before feeding it to the neural network.
    threshold : float
        The threshold for the mask.
    source_size : bool
        The need to return the mask to the original image size.

    Returns
    -------
    Optional[numpy.ndarray]
        If an exception was thrown, returns None.
        Otherwise the return value is the result of segmentation in the form
        of a multidimensional array of size WxH, if source_size is true, otherwise 224x224 pixels.

    """
    global lock
    lock.acquire()
    try:
        return predict_image(model, device, image, transforms, threshold, source_size)
    except Exception as e:
        print(e, file=sys.stderr)
        return None
    finally:
        lock.release()


def predict(image: np.ndarray, threshold: float = None, source_size: bool = False) -> Optional[np.ndarray]:
    """
    Performs segmentation of vertebrae in the image and returns the resulting mask.

    The parameters (threshold, source_size) are checked for correctness
    and in case of incorrect values, the standard ones are used.

    Segmentation is performed in single-threaded mode.

    Parameters
    ----------
    image : numpy.ndarray
        The original image in the format of a multidimensional array WxHx3.
        Where W is the width, H is the height, 3 is the number of color channels (RGB).
    threshold : float
        The threshold for the mask.
    source_size : bool
        The need to return the mask to the original image size.

    Returns
    -------
    Optional[numpy.ndarray]
        If an exception was thrown, returns None.
        Otherwise the return value is the result of segmentation in the form
        of a multidimensional array of size WxH, if source_size is true, otherwise 224x224 pixels.

    """
    global model, device, mean, std
    if threshold is not None and (threshold < 0.0 or threshold > 1.0):
        threshold = None
    if source_size is None:
        source_size = False
    return predict_image_safe(model, device, image, transforms(224, mean, std), threshold, source_size)


lock = RLock()

model, device, (mean, std) = prepare_model()
