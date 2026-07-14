import pandas as pd
from unittest.mock import MagicMock

from cogn_os.ml.evaluate import evaluate_model


def test_evaluate_model_computes_correct_metrics_for_known_predictions():
    # Hand-constructed case where the confusion matrix is known exactly:
    # y_true = [0,0,0,1,1,1], y_pred = [0,0,1,1,1,0]
    # -> TN=2, FP=1, FN=1, TP=2
    # precision = TP/(TP+FP) = 2/3, recall = TP/(TP+FN) = 2/3
    y_test = pd.Series([0, 0, 0, 1, 1, 1])
    fake_pipeline = MagicMock()
    fake_pipeline.predict.return_value = [0, 0, 1, 1, 1, 0]

    result = evaluate_model(fake_pipeline, x_test=pd.DataFrame({"a": range(6)}), y_test=y_test, model_name="fake")

    assert result.true_negatives == 2
    assert result.false_positives == 1
    assert result.false_negatives == 1
    assert result.true_positives == 2
    assert result.precision == round(2 / 3, 4)
    assert result.recall == round(2 / 3, 4)


def test_evaluate_model_handles_perfect_predictions():
    y_test = pd.Series([0, 1, 0, 1])
    fake_pipeline = MagicMock()
    fake_pipeline.predict.return_value = [0, 1, 0, 1]

    result = evaluate_model(fake_pipeline, x_test=pd.DataFrame({"a": range(4)}), y_test=y_test, model_name="fake")

    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0


def test_evaluate_model_handles_no_positive_predictions_without_error():
    # zero_division=0 must prevent a crash/warning-as-error when the
    # model never predicts the positive class.
    y_test = pd.Series([0, 1, 0, 1])
    fake_pipeline = MagicMock()
    fake_pipeline.predict.return_value = [0, 0, 0, 0]

    result = evaluate_model(fake_pipeline, x_test=pd.DataFrame({"a": range(4)}), y_test=y_test, model_name="fake")

    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.true_positives == 0


def test_to_dict_includes_model_name():
    y_test = pd.Series([0, 1])
    fake_pipeline = MagicMock()
    fake_pipeline.predict.return_value = [0, 1]

    result = evaluate_model(fake_pipeline, x_test=pd.DataFrame({"a": range(2)}), y_test=y_test, model_name="logistic_regression")

    assert result.to_dict()["model_name"] == "logistic_regression"