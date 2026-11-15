"""Business logic of the ML API, one module per responsibility. The ML itself is ml/fs_ml (never copied here), so the
features are built exactly as in training."""
import sys

from ..config import settings

if str(settings.ml_package_dir) not in sys.path:
    sys.path.insert(0, str(settings.ml_package_dir))
