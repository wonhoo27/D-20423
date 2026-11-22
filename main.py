import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import statsmodels.api as sm
from scipy import stats
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)

# 페이지 설정
st.set_page_config(
    page_title="다이아몬드 가격 예측 OLS 분석 대시보드",
    page_icon="💎",
    layout="wide",
)

CUT_ORDER = ["Fair", "Good", "Very Good", "Premium", "Ideal"]
COLOR_ORDER = ["J", "I", "H", "G", "F", "E", "D"]
CLARITY_ORDER = ["I1", "SI2", "SI1", "VS2", "VS1", "VVS2", "VVS1", "IF"]


def resolve_data_path(filename: str) -> str:
    """data/ 폴더 또는 루트 경로에서 데이터 파일을 자동으로 탐색합니다."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "data", filename),
        os.path.join(base_dir, filename),
        os.path.join("data", filename),
        filename,
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"'{filename}' 파일을 찾을 수 없습니다. 현재 디렉토리 파일 목록: {os.listdir(base_dir)}"
    )


@st.cache_resource
def load_and_train():
    train_path = resolve_data_path("diamonds_train.csv")
    test_path = resolve_data_path("diamonds_test.csv")

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    feature_cols = [c for c in train_df.columns if c != "log_price"]

    X_train = sm.add_constant(train_df[feature_cols])
    y_train = train_df["log_price"]
    X_test = sm.add_constant(test_df[feature_cols], has_constant="add")
    y_test = test_df["log_price"]

    ols_model = sm.OLS(y_train, X_train).fit()

    pred_test_log = ols_model.predict(X_test)
    pred_test_dollar = np.exp(pred_test_log)
    y_test_dollar = np.exp(y_test)
    resid_test = y_test - pred_test_log

    metrics = {
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "r2_log": float(r2_score(y_test, pred_test_log)),
        "rmse_log": float(np.sqrt(mean_squared_error(y_test, pred_test_log))),
        "r2_dollar": float(r2_score(y_test_dollar, pred_test_dollar)),
        "rmse_dollar": float(np.sqrt(mean_squared_error(y_test_dollar, pred_test_dollar))),
        "mae_dollar": float(mean_absolute_error(y_test_dollar, pred_test_dollar)),
        "mape_dollar": float(mean_absolute_percentage_error(y_test_dollar, pred_test_dollar) * 100),
    }

    coef_df = pd.DataFrame(
        {
            "변수명": ols_model.params.index,
            "회귀계수 (β)": ols_model.params.values,
            "표준오차": ols_model.bse.values,
            "t-통계량": ols_model.tvalues.values,
            "p-value": ols_model.pvalues.values,
            "가격 상승률 (%)": (np.exp(ols_model.params.values) - 1) * 100,
        }
    )

    test_eval = pd.DataFrame(
        {
            "carat": np.exp(test_df["log_carat"].values),
            "log_carat": test_df["log_carat"].values,
            "actual_log": y_test.values,
            "fitted_log": pred_test_log.values,
            "resid_log": resid_test.values,
            "actual_dollar": y_test_dollar.values,
            "pred_dollar": pred_test_dollar.values,
        }
    )
    test_eval["abs_err_dollar"] = np.abs(test_eval["actual_dollar"] - test_eval["pred_dollar"])
    test_eval["ape_pct"] = test_eval["abs_err_dollar"] / test_eval["actual_dollar"] * 100

    return ols_model, feature_cols, metrics, coef_df, test_eval


def predict_single_diamond(model, feature_cols, carat, depth, table, cut, color, clarity):
    row = {col: 0.0 for col in feature_cols}
    row["log_carat"] = np.log(carat)
    row["depth"] = float(depth)
    row["table"] = float(table)

    if cut != "Fair":
        row[f"cut_{cut}"] = 1.0
    if color != "J":
        row[f"color_{color}"] = 1.0
    if clarity !=
