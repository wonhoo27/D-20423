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


@st.cache_resource
def load_and_train():
    train_df = pd.read_csv("data/diamonds_train.csv")
    test_df = pd.read_csv("data/diamonds_test.csv")

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
    if clarity != "I1":
        row[f"clarity_{clarity}"] = 1.0

    X_input = pd.DataFrame([[1.0] + [row[c] for c in feature_cols]], columns=["const"] + feature_cols)
    pred_result = model.get_prediction(X_input).summary_frame(alpha=0.05)

    pred_log = float(pred_result["mean"].iloc[0])
    ci_low_log = float(pred_result["mean_ci_lower"].iloc[0])
    ci_high_log = float(pred_result["mean_ci_upper"].iloc[0])
    pi_low_log = float(pred_result["obs_ci_lower"].iloc[0])
    pi_high_log = float(pred_result["obs_ci_upper"].iloc[0])

    return {
        "pred_dollar": np.exp(pred_log),
        "pred_log": pred_log,
        "ci_dollar": (np.exp(ci_low_log), np.exp(ci_high_log)),
        "pi_dollar": (np.exp(pi_low_log), np.exp(pi_high_log)),
    }


# 데이터 로드 및 학습 실행
model, feature_cols, metrics, coef_df, test_eval = load_and_train()

# 상단 헤더 및 핵심 성능 요약
st.title("💎 다이아몬드 가격 예측 선형 회귀(OLS) 분석 대시보드")
st.caption(
    f"정제 데이터 53,772건 (8:2 층화 분할 — Train {metrics['train_rows']:,}건 / Test {metrics['test_rows']:,}건) | "
    "Log-Log 다중선형회귀 모델"
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Test 설명력 (R² - Log)", f"{metrics['r2_log']:.4f}")
m2.metric("Test 설명력 (R² - Dollar)", f"{metrics['r2_dollar']:.4f}")
m3.metric("평균 절대 오차 (MAE)", f"${metrics['mae_dollar']:,.2f}")
m4.metric("평균 백분율 오차 (MAPE)", f"{metrics['mape_dollar']:.2f}%")

st.divider()

tab1, tab2, tab3 = st.tabs(
    ["🔮 실시간 가격 시뮬레이터", "📊 회귀 계수 및 프리미엄 분석", "🔬 잔차 진단 및 오차 분석"]
)

# ---------------------------------------------------------
# TAB 1: 실시간 가격 시뮬레이터
# ---------------------------------------------------------
with tab1:
    st.subheader("다이아몬드 스펙 입력 및 예측 가격 산출")
    col_in, col_out = st.columns([1, 1.3], gap="large")

    with col_in:
        carat = st.slider("중량 (Carat)", min_value=0.20, max_value=5.00, value=1.00, step=0.01)
        cut = st.select_slider("세공 등급 (Cut)", options=CUT_ORDER, value="Ideal")
        color = st.select_slider("색상 등급 (Color: J 최하 → D 최상)", options=COLOR_ORDER, value="G")
        clarity = st.select_slider("투명도 등급 (Clarity: I1 최하 → IF 최상)", options=CLARITY_ORDER, value="VS2")

        with st.expander("세부 세공 비율 조정 (Depth / Table)"):
            depth = st.slider("Depth (%)", min_value=43.0, max_value=79.0, value=61.8, step=0.1)
            table = st.slider("Table (%)", min_value=43.0, max_value=95.0, value=57.0, step=0.5)

    res = predict_single_diamond(model, feature_cols, carat, depth, table, cut, color, clarity)

    with col_out:
        st.markdown("### 예측 결과")
        st.metric(
            label=f"{carat:.2f}ct | {cut} | Color {color} | {clarity} 예상 시장가",
            value=f"${res['pred_dollar']:,.2f}",
            delta=f"캐럿당 단가: ${res['pred_dollar'] / carat:,.2f} / ct",
        )
        st.info(
            f"**95% 개별 예측 구간 (Prediction Interval):** "
            f"**${res['pi_dollar'][0]:,.2f} ~ ${res['pi_dollar'][1]:,.2f}**\n\n"
            f"- 로그 예측값 (`log_price`): `{res['pred_log']:.4f}` → `np.exp()` 역변환 적용"
        )

        # 동일 스펙 기준 캐럿 변화에 따른 가격 곡선 시각화
        carat_grid = np.linspace(0.2, 3.0, 60)
        grid_prices = [
            predict_single_diamond(model, feature_cols, c, depth, table, cut, color, clarity)["pred_dollar"]
            for c in carat_grid
        ]
        fig_curve = go.Figure()
        fig_curve.add_trace(
            go.Scatter(x=carat_grid, y=grid_prices, mode="lines", name="등급 고정 가격 곡선", line=dict(width=3))
        )
        fig_curve.add_trace(
            go.Scatter(
                x=[carat],
                y=[res["pred_dollar"]],
                mode="markers",
                name="현재 선택 스펙",
                marker=dict(size=12, color="red"),
            )
        )
        fig_curve.update_layout(
            title="선택 등급 기준 캐럿(Carat) 증가에 따른 비선형 가격 상승 곡선",
            xaxis_title="Carat (중량)",
            yaxis_title="예측 가격 ($)",
            height=330,
            margin=dict(l=20, r=20, t=45, b=20),
        )
        st.plotly_chart(fig_curve, use_container_width=True)

# ---------------------------------------------------------
# TAB 2: 회귀 계수 및 프리미엄 분석
# ---------------------------------------------------------
with tab2:
    st.subheader("범주형 등급별 기준 대비 가격 프리미엄 (%)")
    st.markdown(
        "타겟(`log_price`)에 로그 변환이 적용되어, 회귀 계수($\\beta$)는 각 최하위 기준 등급(`Fair`, `J`, `I1`) 대비 "
        "**가격 상승률($(e^\\beta - 1) \\times 100\\%$)**을 나타냅니다."
    )

    c1, c2, c3 = st.columns(3)

    for col_box, prefix, title in [
        (c1, "cut_", "Cut 등급 프리미엄 (기준: Fair)"),
        (c2, "color_", "Color 등급 프리미엄 (기준: J)"),
        (c3, "clarity_", "Clarity 등급 프리미엄 (기준: I1)"),
    ]:
        sub = coef_df[coef_df["변수명"].str.startswith(prefix)].copy()
        sub["등급"] = sub["변수명"].str.replace(prefix, "", regex=False)
        fig_bar = px.bar(
            sub,
            x="등급",
            y="가격 상승률 (%)",
            text=sub["가격 상승률 (%)"].map(lambda v: f"+{v:.1f}%"),
            title=title,
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(height=360, margin=dict(l=10, r=10, t=45, b=20))
        col_box.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### 전체 OLS 회귀 계수 상세표")
    st.dataframe(
        coef_df.style.format(
            {
                "회귀계수 (β)": "{:.4f}",
                "표준오차": "{:.4f}",
                "t-통계량": "{:.2f}",
                "p-value": "{:.4e}",
                "가격 상승률 (%)": "{:+.2f}%",
            }
        ),
        use_container_width=True,
    )

# ---------------------------------------------------------
# TAB 3: 잔차 진단 및 오차 분석
# ---------------------------------------------------------
with tab3:
    st.subheader("테스트 세트(n = 10,755) 잔차 진단 및 구간별 오차")

    sample_eval = test_eval.sample(n=min(3000, len(test_eval)), random_state=42)

    r_col1, r_col2 = st.columns(2)

    with r_col1:
        fig_res = px.scatter(
            sample_eval,
            x="fitted_log",
            y="resid_log",
            opacity=0.35,
            labels={"fitted_log": "예측값 (Fitted log_price)", "resid_log": "잔차 (Actual - Predicted)"},
            title="Residuals vs. Fitted Values (선형성 및 등분산성 점검)",
        )
        fig_res.add_hline(y=0, line_dash="dash", line_color="red")
        fig_res.update_layout(height=380)
        st.plotly_chart(fig_res, use_container_width=True)

    with r_col2:
        fig_hist = px.histogram(
            test_eval,
            x="resid_log",
            nbins=60,
            labels={"resid_log": "잔차 (log_price)"},
            title=f"잔차 분포 (왜도: {stats.skew(test_eval['resid_log']):.2f}, 초과 첨도: {stats.kurtosis(test_eval['resid_log']):.2f})",
        )
        fig_hist.add_vline(x=0, line_dash="dash", line_color="red")
        fig_hist.update_layout(height=380)
        st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("### 캐럿 크기 구간별 실제 예측 오차 요약")
    bins = [0, 0.5, 1.0, 1.5, 2.0, 6.0]
    labels = ["< 0.5ct", "0.5 ~ 1.0ct", "1.0 ~ 1.5ct", "1.5 ~ 2.0ct", "2.0ct +"]
    test_eval["캐럿 구간"] = pd.cut(test_eval["carat"], bins=bins, labels=labels)

    seg_df = (
        test_eval.groupby("캐럿 구간", observed=False)
        .agg(
            표본수=("carat", "count"),
            로그_잔차_평균=("resid_log", "mean"),
            로그_잔차_표준편차=("resid_log", "std"),
            달러_MAE=("abs_err_dollar", "mean"),
            평균_오차율_MAPE=("ape_pct", "mean"),
        )
        .reset_index()
    )
    st.dataframe(
        seg_df.style.format(
            {
                "표본수": "{:,}",
                "로그_잔차_평균": "{:+.4f}",
                "로그_잔차_표준편차": "{:.4f}",
                "달러_MAE": "${:,.2f}",
                "평균_오차율_MAPE": "{:.2f}%",
            }
        ),
        use_container_width=True,
    )
