import streamlit as st
import pandas as pd
import plotly.express as px

# -------------------------------------------------------------------
# [1. 데이터 불러오기 및 캐싱]
# -------------------------------------------------------------------
# @st.cache_data를 사용하면 데이터를 한 번 불러온 후 메모리에 저장(캐싱)하여
# 앱이 새로고침되거나 다시 실행되어도 매번 데이터를 다운로드하지 않습니다.
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/keep-growing-park/data-science/refs/heads/main/dataset/kobis_1year_boxoffice.csv"
    df = pd.read_csv(url)
    
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
# [3. 영화 선택 기능 (사이드바)]
# -------------------------------------------------------------------
st.sidebar.header("🔍 검색 옵션")

# 누적관객수 최대값을 기준으로 중복 없이 영화 목록 정렬
# (각 영화의 가장 높은 누적관객수를 구한 뒤 내림차순 정렬)
movie_order = (
    df.groupby("영화명")["누적관객수"]
    .max()
    .sort_values(ascending=False)
    .index
    .tolist()
)

# 사이드바 드롭다운 메뉴 생성 (기본값: 가장 누적관객수가 높은 영화)
selected_movie = st.sidebar.selectbox("영화를 선택하세요", movie_order)

# 선택된 영화의 데이터만 필터링
filtered_df = df[df["영화명"] == selected_movie]

# -------------------------------------------------------------------
# [4. 구역 분할 및 시각화]
# -------------------------------------------------------------------
# 탭을 활용하여 2개의 그래프 구역을 분할
tab1, tab2 = st.tabs(["일별 관객 수 추이 (선 그래프)", "누적 관객 수 추이 (영역 차트)"])

# [첫 번째 그래프: 일별 관객수 선그래프]
with tab1:
    st.subheader(f"📈 '{selected_movie}' 일별 관객 수 변화")
    
    # Plotly 선 그래프 생성
    fig_line = px.line(
        filtered_df,
        x="기준일자",
        y="해당일관객수",
        title=f"{selected_movie} - 기준일자별 해당일관객수",
        labels={"기준일자": "날짜", "해당일관객수": "일일 관객 수"},
        markers=True
    )
    
    # 스트림릿 화면에 그래프 출력
    st.plotly_chart(fig_line, use_container_width=True)
    
    # 그래프 해석 문구 자리
    st.info(f"💡 **이 그래프로 알 수 있는 것:** {selected_movie}의 개봉 초기 관객 수 집중 현상과 상영 기간 동안의 일별 흥행 추이를 확인할 수 있습니다.")

# [두 번째 그래프: 누적 관객수 영역차트]
with tab2:
    st.subheader(f"📊 '{selected_movie}' 누적 관객 수 변화")
    
    # Plotly 영역차트(Area Chart) 생성
    fig_area = px.area(
        filtered_df,
        x="기준일자",
        y="누적관객수",
        title=f"{selected_movie} - 기준일자별 누적관객수",
        labels={"기준일자": "날짜", "누적관객수": "누적 관객 수"}
    )
    
    # 스트림릿 화면에 그래프 출력
    st.plotly_chart(fig_area, use_container_width=True)
    
    # 그래프 해석 문구 자리
    st.info(f"💡 **이 그래프로 알 수 있는 것:** 시간 경과에 따른 {selected_movie}의 총 누적 관객 수 증가 기울기와 최종 흥행 스케일을 한눈에 파악할 수 있습니다.")
