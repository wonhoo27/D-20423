import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import statsmodels.api as sm
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

    return ols_model, feature_cols, metrics, coef_df, train_df, test_df


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

    X_input = pd.DataFrame(
        [[1.0] + [row[c] for c in feature_cols]],
        columns=["const"] + feature_cols,
    )
    pred_result = model.get_prediction(X_input).summary_frame(alpha=0.05)

    pred_log = float(pred_result["mean"].iloc[0])
    pi_low_log = float(pred_result["obs_ci_lower"].iloc[0])
    pi_high_log = float(pred_result["obs_ci_upper"].iloc[0])

    return {
        "pred_dollar": np.exp(pred_log),
        "pred_log": pred_log,
        "pi_dollar": (np.exp(pi_low_log), np.exp(pi_high_log)),
    }


# 데이터 로드 및 학습 실행
model, feature_cols, metrics, coef_df, train_df, test_df = load_and_train()

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
    ["🔮 실시간 가격 시뮬레이터", "📋 데이터 전처리 파이프라인 상세", "📊 회귀 계수 및 프리미엄 분석"]
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
# TAB 2: 데이터 전처리 파이프라인 상세 기록
# ---------------------------------------------------------
with tab2:
    st.subheader("1. 단계별 데이터 정제(Data Cleaning) 이력")
    st.markdown(
        "원본 `diamonds.csv`(**53,940행 × 10열**)에서 물리적 오류 및 중복 데이터를 제거하여 "
        "최종 **53,772행 × 21열**의 학습 데이터셋을 구축했습니다."
    )

    p_col1, p_col2 = st.columns([1.2, 1], gap="large")

    with p_col1:
        cleaning_steps = pd.DataFrame(
            {
                "단계": [
                    "0. 원본 데이터 로드",
                    "1. 완전 중복 행 제거",
                    "2. 물리적 치수 0 오류 제거",
                    "3. 비정상 치수 극단치 제거",
                    "4. Train 세트 (80% 층화 분할)",
                    "5. Test 세트 (20% 층화 분할)",
                ],
                "처리 기준": [
                    "diamonds.csv 초기 적재 (결측치 0건 확인)",
                    "모든 열 값이 동일한 중복 레코드 제거 (keep='first')",
                    "가로(x), 세로(y), 높이(z) 중 하나라도 0mm인 행 제거",
                    "y > 30mm (58.9mm, 31.8mm) 및 z > 30mm (31.8mm) 입력 오류 제거",
                    "log_price 10분위수(Decile) 기준 층화 추출 (random_state=42)",
                    "log_price 10분위수(Decile) 기준 층화 추출 (random_state=42)",
                ],
                "제거 건수": ["-", "-146건", "-19건", "-3건", "-", "-"],
                "잔여 데이터 수": ["53,940행", "53,794행", "53,775행", "53,772행", "43,017행", "10,755행"],
            }
        )
        st.dataframe(cleaning_steps, use_container_width=True, hide_index=True)

    with p_col2:
        fig_funnel = go.Figure(
            go.Funnel(
                y=[
                    "원본 데이터",
                    "중복 제거 후",
                    "치수 0 제거 후",
                    "극단치 제거 후 (최종)",
                    "Train (80%)",
                    "Test (20%)",
                ],
                x=[53940, 53794, 53775, 53772, 43017, 10755],
                textinfo="value+percent initial",
            )
        )
        fig_funnel.update_layout(
            title="전처리 및 데이터 분할 단계별 표본 수 변화",
            height=340,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    st.divider()
    st.subheader("2. 피처 엔지니어링 및 변수 변환 명세")

    fe_df = pd.DataFrame(
        {
            "구분": [
                "타겟 변수 변환",
                "핵심 수치형 변환",
                "다중공선성 변수 제거",
                "세공 비율 변수 유지",
                "Cut 원-핫 인코딩",
                "Color 원-핫 인코딩",
                "Clarity 원-핫 인코딩",
            ],
            "원본 변수": [
                "price ($326 ~ $18,823)",
                "carat (0.20 ~ 5.01ct)",
                "x, y, z (mm 단위 치수)",
                "depth (%), table (%)",
                "cut (5개 등급)",
                "color (7개 등급)",
                "clarity (8개 등급)",
            ],
            "변환 후 변수 (총 21열)": [
                "log_price = ln(price)",
                "log_carat = ln(carat)",
                "제거 (Dropped)",
                "depth, table (원본 유지)",
                "cut_Good ~ cut_Ideal (4개)",
                "color_I ~ color_D (6개)",
                "clarity_SI2 ~ clarity_IF (7개)",
            ],
            "적용 근거 및 통계적 효과": [
                "우측 꼬리 비대칭 분포 정규화, 등급별 비율(%) 효과 반영, 음수 예측 방지",
                "carat과 price 간 지수적 곡선 관계를 선형 직선(Elasticity)으로 변환",
                "carat과 상관계수 r > 0.95 및 VIF > 1,000으로 극심한 다중공선성 유발",
                "세공 비율 세부 수치 반영 (단, OLS 적합 결과 p > 0.2로 독립 영향은 미미)",
                "최하위 기준(Fair) 제외(drop_first=True)로 더미 변수 함정(완전 공선성) 방지",
                "최하위 기준(J) 제외(drop_first=True) — J→D 순으로 무색에 가까울수록 고가",
                "최하위 기준(I1) 제외(drop_first=True) — I1→IF 순으로 내포물이 적을수록 고가",
            ],
        }
    )
    st.dataframe(fe_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("3. 8:2 층화 분할(Stratified Split) 타겟 분포 검증")
    st.markdown(
        "고가 다이아몬드(`$15,000` 이상)가 한쪽 세트에 치우치지 않도록 `log_price`를 **10분위수(Decile)**로 나눈 뒤 "
        "층화 추출을 적용했습니다."
    )

    s_col1, s_col2 = st.columns([1.3, 1], gap="large")

    with s_col1:
        dist_df = pd.concat(
            [
                pd.DataFrame({"Dataset": "Train (80%, n=43,017)", "log_price": train_df["log_price"]}),
                pd.DataFrame({"Dataset": "Test (20%, n=10,755)", "log_price": test_df["log_price"]}),
            ],
            ignore_index=True,
        )
        fig_split = px.histogram(
            dist_df,
            x="log_price",
            color="Dataset",
            barmode="overlay",
            histnorm="probability density",
            nbins=50,
            opacity=0.55,
            title="Train vs. Test 세트 타겟(log_price) 확률 밀도 분포 비교",
        )
        fig_split.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_split, use_container_width=True)

    with s_col2:
        train_dollar = np.exp(train_df["log_price"])
        test_dollar = np.exp(test_df["log_price"])
        stat_comp = pd.DataFrame(
            {
                "통계 지표": [
                    "표본 수 (행)",
                    "log_price 평균",
                    "log_price 표준편차",
                    "달러($) 환산 평균",
                    "달러($) 환산 중앙값",
                    "달러($) 환산 최댓값",
                ],
                "Train 세트 (80%)": [
                    f"{len(train_df):,}건",
                    f"{train_df['log_price'].mean():.4f}",
                    f"{train_df['log_price'].std():.4f}",
                    f"${train_dollar.mean():,.2f}",
                    f"${train_dollar.median():,.2f}",
                    f"${train_dollar.max():,.2f}",
                ],
                "Test 세트 (20%)": [
                    f"{len(test_df):,}건",
                    f"{test_df['log_price'].mean():.4f}",
                    f"{test_df['log_price'].std():.4f}",
                    f"${test_dollar.mean():,.2f}",
                    f"${test_dollar.median():,.2f}",
                    f"${test_dollar.max():,.2f}",
                ],
            }
        )
        st.dataframe(stat_comp, use_container_width=True, hide_index=True)

    with st.expander("최종 전처리 완료 데이터 샘플 미리보기 (Train 상위 10행, 21개 피처)"):
        st.dataframe(train_df.head(10), use_container_width=True)

# ---------------------------------------------------------
# TAB 3: 회귀 계수 및 프리미엄 분석
# ---------------------------------------------------------
with tab3:
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
