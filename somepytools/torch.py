from contextlib import contextmanager


try:
    import torch

    from .types import Model

    @contextmanager
    def infer(model: Model):
        """Fully turns model state to inference (and restores it in the end)"""
        status = model.training
        model.train(False)
        with torch.no_grad():
            try:
                yield None
            finally:
                model.train(status)

    def model_size(
        model: Model, trainable_only: bool = False, params_count: bool = False
    ) -> int:
        """Calculates size of PyTorch model.

        Args:
            model: Torch model to count parameters in.
            trainable_only: Flag to indicate whether to count only the learning parameters.
            params_count: if True - count only parameterls number, else size on disk

        Returns:
            Size of given model in bytes.
        """
        return sum(
            param.numel() if params_count else param.numel() * param.element_size()
            for param in model.parameters()
            if not trainable_only or param.requires_grad
        )

except ModuleNotFoundError:
    pass
