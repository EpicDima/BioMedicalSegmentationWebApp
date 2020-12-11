import sys
from threading import RLock
from typing import Optional

import albumentations as A
import numpy as np
import segmentation_models_pytorch as smp
import torch
from albumentations.pytorch.transforms import ToTensorV2


def get_mean_and_std(encoder: str = "timm-efficientnet-b3", encoder_weights: str = "noisy-student") -> tuple:
    preprocessing_params = smp.encoders.get_preprocessing_params(encoder, encoder_weights)
    return preprocessing_params["mean"], preprocessing_params["std"]


def transforms(image_size: int = 224, mean: tuple = None, std: tuple = None) -> A.Compose:
    return A.Compose([
        A.Resize(image_size, image_size),
        A.Normalize(mean=mean, std=std),
        ToTensorV2(True)
    ])


def predict_image(model: torch.nn.Module, device: torch.device, image: np.ndarray, transforms: A.Compose = None,
                  threshold: float = None, source_size: bool = False) -> np.ndarray:
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
    global model, device, mean, std
    if threshold is not None and (threshold < 0.0 or threshold > 1.0):
        threshold = None
    if source_size is None:
        source_size = False
    return predict_image_safe(model, device, image, transforms(224, mean, std), threshold, source_size)


def prepare_model() -> tuple:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mean, std = get_mean_and_std()
    model = torch.load("models/teb3_ns_unet_9665.pth", map_location=device).eval()
    return model, device, mean, std


lock = RLock()

model, device, mean, std = prepare_model()
