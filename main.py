import streamlit as st
import pandas as pd
import plotly.express as px

# -------------------------------------------------------------------
# [1. 데이터 불러오기 및 캐싱]
# -------------------------------------------------------------------
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/keep-growing-park/data-science/refs/heads/main/dataset/kobis_1year_boxoffice.csv"
    df = pd.read_csv(url)
    
    # 컬럼 이름 양옆의 공백 제거 (예: '순위 ' -> '순위')
    df.columns = df.columns.str.strip()
    
    # ---------------------------------------------------------------
    # [2. 데이터 전처리]
    # ---------------------------------------------------------------
    # 1) 결측치가 포함된 행 삭제
    df = df.dropna()
    
    # 2) "기준일자" 컬럼을 datetime 형식으로 변환
    df["기준일자"] = pd.to_datetime(df["기준일자"])
    
    # 3) 기준일자 오름차순 정렬
    df = df.sort_values(by="기준일자")
    
    return df

# 페이지 기본 설정
st.set_page_config(page_title="KOBIS 박스오피스 대시보드", layout="wide")
st.title("🎬 KOBIS 박스오피스 데이터 분석 앱")

# 데이터 로드
df = load_data()

# -------------------------------------------------------------------
# [3. 영화 선택 및 필터링]
# -------------------------------------------------------------------
st.sidebar.header("🔍 검색 옵션")

# 전체 영화 목록 (누적관객수 내림차순 정렬)
movie_order = (
    df.groupby("영화명")["누적관객수"]
    .max()
    .sort_values(ascending=False)
    .index
    .tolist()
)

# 1) 사이드바 개별 영화 선택 드롭다운 (탭 1, 탭 2에서 사용)
selected_movie = st.sidebar.selectbox("영화를 선택하세요", movie_order)
filtered_df = df[df["영화명"] == selected_movie]

# 2) [수정된 부분] TOP 10 20일 이상 진입 영화 필터링 (KeyError 방지)
# '순위' 컬럼이 있으면 해당 컬럼을 사용하고, 없으면 '순위글자' 등을 확인하거나
# 박스오피스 데이터 특성상 모든 데이터가 daily TOP 10으로 구성되어 있으므로 전체 데이터 기준으로 일수를 셉니다.
if "순위" in df.columns:
    df["순위_숫자"] = pd.to_numeric(df["순위"], errors="coerce")
    top10_daily = df[df["순위_숫자"] <= 10]
elif "순위글자" in df.columns:
    df["순위_숫자"] = pd.to_numeric(df["순위글자"], errors="coerce")
    top10_daily = df[df["순위_숫자"] <= 10]
else:
    # 순위 컬럼이 없는 경우, 데이터 자체가 이미 일별 TOP 10 데이터셋이므로 전체 df 사용
    top10_daily = df

# 영화별 등장 일수(데이터에 포함된 날짜 수) 계산
top10_counts = top10_daily.groupby("영화명")["기준일자"].nunique()
eligible_movies = top10_counts[top10_counts >= 20].index

# 조건(20일 이상 등장)을 만족하는 영화 중 누적관객수 상위 5개 선별
top5_qualified_movies = (
    df[df["영화명"].isin(eligible_movies)]
    .groupby("영화명")["누적관객수"]
    .max()
    .sort_values(ascending=False)
    .head(5)
    .index
    .tolist()
)

# 상위 5개 영화 전체 데이터 필터링
top5_df = df[df["영화명"].isin(top5_qualified_movies)]

# -------------------------------------------------------------------
# [4. 구역 분할 및 시각화]
# -------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "일별 관객 수 추이 (선 그래프)", 
    "누적 관객 수 추이 (영역 차트)", 
    "장기 흥행 TOP 5 영화 비교 (다중 선 그래프)"
])

# [첫 번째 그래프: 일별 관객수 선그래프]
with tab1:
    st.subheader(f"📈 '{selected_movie}' 일별 관객 수 변화")
    
    fig_line = px.line(
        filtered_df,
        x="기준일자",
        y="해당일관객수",
        title=f"{selected_movie} - 기준일자별 해당일관객수",
        labels={"기준일자": "날짜", "해당일관객수": "일일 관객 수"},
        markers=True
    )
    
    st.plotly_chart(fig_line, use_container_width=True)
    st.info(f"💡 **이 그래프로 알 수 있는 것:** {selected_movie}의 개봉 초기 관객 수 집중 현상과 상영 기간 동안의 일별 흥행 추이를 확인할 수 있습니다.")

# [두 번째 그래프: 누적 관객수 영역차트]
with tab2:
    st.subheader(f"📊 '{selected_movie}' 누적 관객 수 변화")
    
    fig_area = px.area(
        filtered_df,
        x="기준일자",
        y="누적관객수",
        title=f"{selected_movie} - 기준일자별 누적관객수",
        labels={"기준일자": "날짜", "누적관객수": "누적 관객 수"}
    )
    
    st.plotly_chart(fig_area, use_container_width=True)
    st.info(f"💡 **이 그래프로 알 수 있는 것:** 시간 경과에 따른 {selected_movie}의 총 누적 관객 수 증가 기울기와 최종 흥행 스케일을 한눈에 파악할 수 있습니다.")

# [세 번째 그래프: 다중 선그래프]
with tab3:
    st.subheader("🏆 박스오피스 20일 이상 등재 영화 중 누적관객수 TOP 5 비교")
    
    fig_top5 = px.line(
        top5_df,
        x="기준일자",
        y="누적관객수",
        color="영화명",
        title="장기 흥행(20일 이상 등재) 상위 5개 영화의 누적관객수 추이",
        labels={"기준일자": "날짜", "누적관객수": "누적 관객 수", "영화명": "영화 제목"}
    )
    
    st.plotly_chart(fig_top5, use_container_width=True)
    st.info("💡 **이 그래프로 알 수 있는 것:** 일시적 반짝 흥행이 아닌 최소 20일 이상 박스오피스를 지킨 장기 흥행작 5편의 누적 관객 수 수렴 및 성장 속도를 비교할 수 있습니다.")
