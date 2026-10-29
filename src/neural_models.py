from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


EpochCallback = Callable[[int, int, float, float], None]


class MLPForecaster(nn.Module):
    def __init__(self, input_length: int, output_length: int, hidden_size: int, dropout: float):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_length, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, output_length),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.network(values)


class CNNForecaster(nn.Module):
    def __init__(self, output_length: int, hidden_size: int, kernel_size: int, dropout: float):
        super().__init__()
        padding = kernel_size // 2
        self.features = nn.Sequential(
            nn.Conv1d(1, hidden_size, kernel_size=kernel_size, padding=padding),
            nn.ReLU(),
            nn.Conv1d(hidden_size, hidden_size, kernel_size=kernel_size, padding=padding),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(8),
            nn.Flatten(),
            nn.Dropout(dropout),
        )
        self.output = nn.Linear(hidden_size * 8, output_length)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.output(self.features(values.unsqueeze(1)))


class RecurrentForecaster(nn.Module):
    def __init__(
        self,
        kind: str,
        output_length: int,
        hidden_size: int,
        num_layers: int,
        dropout: float,
    ):
        super().__init__()
        recurrent_dropout = dropout if num_layers > 1 else 0.0
        recurrent_class = nn.LSTM if kind == "LSTM" else nn.GRU
        self.recurrent = recurrent_class(
            input_size=1,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=recurrent_dropout,
        )
        self.output = nn.Linear(hidden_size, output_length)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        sequence_output, _ = self.recurrent(values.unsqueeze(-1))
        return self.output(sequence_output[:, -1, :])


@dataclass
class NeuralOutput:
    validation_predictions: np.ndarray
    test_predictions: np.ndarray
    history: pd.DataFrame
    fit_seconds: float
    predict_seconds: float


def _create_model(
    model_name: str,
    input_length: int,
    output_length: int,
    parameters: dict[str, object],
) -> nn.Module:
    hidden_size = int(parameters.get("hidden_size", 64))
    dropout = float(parameters.get("dropout", 0.1))
    if model_name == "MLP":
        return MLPForecaster(input_length, output_length, hidden_size, dropout)
    if model_name == "1D CNN":
        return CNNForecaster(
            output_length=output_length,
            hidden_size=hidden_size,
            kernel_size=int(parameters.get("kernel_size", 3)),
            dropout=dropout,
        )
    if model_name in {"LSTM", "GRU"}:
        return RecurrentForecaster(
            kind=model_name,
            output_length=output_length,
            hidden_size=hidden_size,
            num_layers=int(parameters.get("num_layers", 1)),
            dropout=dropout,
        )
    raise ValueError(f"不支持的神经网络：{model_name}")


def train_neural_model(
    model_name: str,
    train_X: np.ndarray,
    train_y: np.ndarray,
    validation_X: np.ndarray,
    validation_y: np.ndarray,
    test_X: np.ndarray,
    parameters: dict[str, object],
    epoch_callback: EpochCallback | None = None,
) -> NeuralOutput:
    torch.manual_seed(42)
    np.random.seed(42)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    device = torch.device("cpu")
    epochs = int(parameters.get("epochs", 20))
    batch_size = int(parameters.get("batch_size", 64))
    learning_rate = float(parameters.get("learning_rate", 0.001))
    patience = int(parameters.get("patience", 5))

    model = _create_model(model_name, train_X.shape[1], train_y.shape[1], parameters).to(device)
    loss_function = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    generator = torch.Generator().manual_seed(42)
    loader = DataLoader(
        TensorDataset(
            torch.as_tensor(train_X, dtype=torch.float32),
            torch.as_tensor(train_y, dtype=torch.float32),
        ),
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        generator=generator,
    )
    validation_features = torch.as_tensor(validation_X, dtype=torch.float32, device=device)
    validation_targets = torch.as_tensor(validation_y, dtype=torch.float32, device=device)

    history_rows: list[dict[str, float | int]] = []
    best_state = deepcopy(model.state_dict())
    best_validation_loss = float("inf")
    epochs_without_improvement = 0
    fit_start = perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        loss_total = 0.0
        sample_total = 0
        for batch_X, batch_y in loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            predictions = model(batch_X)
            loss = loss_function(predictions, batch_y)
            loss.backward()
            optimizer.step()
            loss_total += float(loss.item()) * len(batch_X)
            sample_total += len(batch_X)

        training_loss = loss_total / max(sample_total, 1)
        model.eval()
        with torch.no_grad():
            validation_loss = float(loss_function(model(validation_features), validation_targets).item())
        history_rows.append(
            {"epoch": epoch, "training_loss": training_loss, "validation_loss": validation_loss}
        )
        if epoch_callback is not None:
            epoch_callback(epoch, epochs, training_loss, validation_loss)

        if validation_loss < best_validation_loss - 1e-8:
            best_validation_loss = validation_loss
            best_state = deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if patience > 0 and epochs_without_improvement >= patience:
                break

    fit_seconds = perf_counter() - fit_start
    model.load_state_dict(best_state)
    model.eval()
    predict_start = perf_counter()
    with torch.no_grad():
        validation_predictions = model(validation_features).cpu().numpy()
        test_predictions = model(
            torch.as_tensor(test_X, dtype=torch.float32, device=device)
        ).cpu().numpy()
    predict_seconds = perf_counter() - predict_start
    return NeuralOutput(
        validation_predictions=validation_predictions,
        test_predictions=test_predictions,
        history=pd.DataFrame(history_rows),
        fit_seconds=fit_seconds,
        predict_seconds=predict_seconds,
    )
