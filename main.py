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
    
    # 장르: 결측값 처리 후 세로막대 기호(|)의 첫 번째 장르만 추출
    if 'genre' in df.columns:
        df['genre'] = df['genre'].fillna('기타').astype(str).apply(lambda x: x.split('|')[0] if x else '기타')
        
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
    
    # 1번 설명 구역
    with st.container():
        st.info("💡 **이 그래프로 알 수 있는 것:** 박스오피스 상위권에 진입한 영화 중 특정 대표 장르(예: 드라마, 액션 등)가 차지하는 비중과 장르별 편수 분포를 한눈에 파악할 수 있습니다.")

    st.write("---")

    # 2. 장르 및 영화별 총 관객 수 (트리맵 그래프)
    st.subheader("2. 장르 및 영화별 총 관객 수 분포")

    fig_treemap = px.treemap(
        df,
        path=['genre', 'movieNm'],
        values='total_audi',
        color='genre',
        title="장르 및 영화별 총 관객 수 (칸 크기 = 총 관객 수)",
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    # 마우스 호버 시 영화명과 총 관객 표기
    fig_treemap.update_traces(
        hovertemplate="<b>영화명: %{label}</b><br>총 관객 수: %{value:,.0f}명"
    )

    fig_treemap.update_layout(
        margin=dict(t=50, b=20, l=20, r=20)
    )

    st.plotly_chart(fig_treemap, use_container_width=True)

    # 2번 설명 구역
    with st.container():
        st.info("💡 **이 그래프로 알 수 있는 것:** 어떤 장르가 흥행 규모가 큰지, 그리고 각 장르 내에서 어떤 개별 영화가 총 관객 수의 대부분을 견인했는지 흥행 비중과 기여도를 한눈에 비교할 수 있습니다.")

    st.write("---")

    # 3. 총 관객 수 히스토그램
    st.subheader("3. 총 관객 수(total_audi) 분포")

    fig_hist = px.histogram(
        df,
        x='total_audi',
        nbins=30,
        title="총 관객 수 분포 히스토그램",
        color_discrete_sequence=['#42A5F5']
    )

    fig_hist.update_traces(
        marker_line_color='white',
        marker_line_width=1,
        hovertemplate="<b>관객 수 구간: %{x:,.0f}명</b><br>영화 수: %{y}편"
    )

    fig_hist.update_layout(
        xaxis_title="총 관객 수 (명)",
        yaxis_title="영화 편수 (개)",
        margin=dict(t=50, b=20, l=20, r=20)
    )

    st.plotly_chart(fig_hist, use_container_width=True)

    # 3번 통계 데이터 계산
    max_row = df.loc[df['total_audi'].idxmax()]
    max_movie_name = max_row['movieNm']
    max_movie_audi = max_row['total_audi']

    # 3번 설명 구역
    with st.container():
        st.info(
            f"💡 **이 그래프로 알 수 있는 것:** 대부분의 영화는 **총 관객 수 100만 명 미만(주로 50만 명 안팎)**의 낮은 구간에 집중되어 있어 양극화 현상이 뚜렷하며, "
            f"가장 관객이 많은 영화는 **'{max_movie_name}'**(총 {max_movie_audi:,.0f}명)임을 알 수 있습니다."
        )

    st.write("---")

    # 4. 개봉일 스크린 수 vs 총 관객 수 (산점도 그래프)
    st.subheader("4. 개봉일 스크린 수와 총 관객 수의 관계")

    fig_scatter = px.scatter(
        df,
        x='first_scrn',
        y='total_audi',
        color='genre',
        hover_name='movieNm',
        title="개봉일 스크린 수(first_scrn) vs 총 관객 수(total_audi)",
        color_discrete_sequence=px.colors.qualitative.Set1
    )

    fig_scatter.update_traces(
        marker=dict(size=9, opacity=0.8),
        hovertemplate="<b>영화명: %{hovertext}</b><br>장르: %{fullData.name}<br>개봉일 스크린 수: %{x:,.0f}개<br>총 관객 수: %{y:,.0f}명"
    )

    fig_scatter.update_layout(
        xaxis_title="개봉일 스크린 수 (개)",
        yaxis_title="총 관객 수 (명)",
        legend_title="장르",
        margin=dict(t=50, b=20, l=20, r=20)
    )

    st.plotly_chart(fig_scatter, use_container_width=True)

    # 4번 설명 구역
    with st.container():
        st.info("💡 **이 그래프로 알 수 있는 것:** 개봉일 스크린 수가 많을수록 총 관객 수도 증가하는 양의 상관관계를 확인할 수 있으며, 동일한 스크린 수 대비 장르나 작품에 따른 흥행성 차이도 함께 파악할 수 있습니다.")

    st.write("---")

    # 5. 영화 10편 이상 장르의 총 관객 수 박스플롯
    st.subheader("5. 주요 장르별 총 관객 수 박스플롯 (영화 10편 이상)")

    # 영화 10편 이상인 장르 필터링
    genre_counts_series = df['genre'].value_counts()
    major_genres = genre_counts_series[genre_counts_series >= 10].index.tolist()
    df_major = df[df['genre'].isin(major_genres)]

    fig_box = px.box(
        df_major,
        x='genre',
        y='total_audi',
        color='genre',
        points='outliers',
        hover_name='movieNm',
        title="10편 이상 개봉 장르별 총 관객 수 분포 및 이상치(대흥행작)",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    # 이상치 및 데이터 포인트 마우스 호버 표기
    fig_box.update_traces(
        hovertemplate="<b>영화명: %{hovertext}</b><br>장르: %{x}<br>총 관객 수: %{y:,.0f}명"
    )

    fig_box.update_layout(
        xaxis_title="장르",
        yaxis_title="총 관객 수 (명)",
        showlegend=False,
        margin=dict(t=50, b=20, l=20, r=20)
    )

    st.plotly_chart(fig_box, use_container_width=True)

    # 5번 설명 구역
    with st.container():
        st.info("💡 **이 그래프로 알 수 있는 것:** 영화 편수가 10편 이상인 주요 장르 간 흥행 실적의 중앙값과 범위를 비교할 수 있으며, 박스 위쪽의 상자 밖 점(이상치)을 통해 장르 전체 평균을 크게 상회하는 초대형 흥행작을 식별할 수 있습니다.")

    st.write("---")

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
