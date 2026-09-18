import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(
    page_title="영화 데이터 그래프 - 분포와 관계",
    page_icon="🎬",
    layout="wide"
)

# 데이터 로드 및 전처리 함수
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"
    df = pd.read_csv(url)
    
    # 장르: 세로막대 기호(|)로 구분된 경우 첫 번째 장르만 추출
    if 'genre' in df.columns:
        df['genre'] = df['genre'].astype(str).apply(lambda x: x.split('|')[0] if x and x != 'nan' else '기타')
        
    return df

st.title("🎬 영화 데이터 그래프 - 분포와 관계")
st.markdown("1년간 박스오피스 10위권에 든 영화 중 이 기간에 개봉한 **216편**의 분석 요약 정보입니다.")
st.write("---")

# 데이터 불러오기
try:
    df = load_data()
    
    # 원본 데이터 미리보기
    with st.expander("📄 원본 데이터 미리보기"):
        st.dataframe(df, use_container_width=True)

    # 1. 장르별 영화 편수 (플롯리 도넛 그래프)
    st.subheader("1. 장르별 영화 편수 분포")
    
    genre_counts = df['genre'].value_counts().reset_index()
    genre_counts.columns = ['장르', '영화 편수']
    
    fig_donut = px.pie(
        genre_counts,
        values='영화 편수',
        names='장르',
        hole=0.4,
        title="장르별 영화 편수 비율",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    # 마우스 호버 시 편수와 비율 표기
    fig_donut.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate="<b>장르: %{label}</b><br>편수: %{value}편<br>비율: %{percent}"
    )
    
    fig_donut.update_layout(
        margin=dict(t=50, b=20, l=20, r=20),
        legend_title="장르 목록"
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)
    
    # 설명 구역 (Container/Info Box)
    with st.container():
        st.info("💡 **이 그래프로 알 수 있는 것:** 박스오피스 상위권에 진입한 영화 중 특정 대표 장르(예: 드라마, 액션 등)가 차지하는 비중과 장르별 편수 분포를 한눈에 파악할 수 있습니다.")

    st.write("---")

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
