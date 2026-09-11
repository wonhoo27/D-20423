from datetime import datetime, timedelta
import zoneinfo
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. 스트림릿 기본 설정 및 타이틀
# ---------------------------------------------------------
st.set_page_config(
    page_title="박스오피스 순위 조회", page_icon="🎬", layout="wide"
)

st.title("🎬 일별 박스오피스 순위 조회")


# ---------------------------------------------------------
# 2. 한국 시간 기준 '어제' 날짜 계산 함수
# ---------------------------------------------------------
def get_yesterday_date_kst():
    # 배포 서버의 시계가 해외 기준일 수 있으므로 한국 표준시(Asia/Seoul)를 명시적으로 지정합니다.
    kst_zone = zoneinfo.ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst_zone)
    return (now_kst - timedelta(days=1)).date()


yesterday_date = get_yesterday_date_kst()

# ---------------------------------------------------------
# 3. 달력(date_input)으로 조회 날짜 선택
# ---------------------------------------------------------
# 기본값은 어제, 가장 늦게 선택할 수 있는 날짜(max_value)도 어제로 제한합니다.
selected_date = st.date_input(
    label="📅 조회할 날짜를 선택하세요 (최대 어제까지 선택 가능)",
    value=yesterday_date,
    max_value=yesterday_date,
)

# KOBIS API 규격에 맞는 YYYYMMDD 형태 문자열 생성
target_date = selected_date.strftime("%Y%m%d")


# ---------------------------------------------------------
# 4. KOBIS API 데이터 불러오기 함수 (캐싱 적용)
# ---------------------------------------------------------
# st.cache_data를 이용해 동일한 날짜 요청은 1시간(3600초) 동안 API를 재호출하지 않고 저장된 데이터를 사용합니다.
@st.cache_data(ttl=3600)
def fetch_box_office_data(api_key, date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": date_str}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------
# 5. Secrets에서 API 키 불러오기 및 예외 처리
# ---------------------------------------------------------
if "KOBIS_KEY" not in st.secrets or not st.secrets["KOBIS_KEY"]:
    st.error("🚨 API 인증키(KOBIS_KEY)가 설정되지 않았습니다.")
    st.info(
        """
    **확인해야 할 사항:**
    1. Streamlit Cloud의 앱 설정 메뉴에서 `Secrets` 항목을 엽니다.
    2. `KOBIS_KEY = "발급받은_인증키"` 형태로 등록했는지 확인해 주세요.
    """
    )
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# 선택한 날짜의 데이터 불러오기 실행
data, network_error = fetch_box_office_data(api_key, target_date)


# ---------------------------------------------------------
# 6. API 응답 및 데이터 유효성 검사
# ---------------------------------------------------------
# 1) 네트워크 통신 실패 처리
if network_error:
    st.error("🚨 서버 통신 실패!")
    st.warning(f"상세 에러 내용: {network_error}")
    st.info(
        "네트워크 연결 상태를 확인하시거나 KOBIS API 서버 상태를 점검해 주세요."
    )
    st.stop()

# 2) KOBIS에서 faultInfo(인증키 오류 등)가 전달된 경우 처리
if "faultInfo" in data:
    st.error("🚨 API 인증 및 요청 오류가 발생했습니다.")
    fault = data["faultInfo"]
    st.warning(f"오류 메시지: {fault.get('message', '알 수 없는 오류')}")
    st.info(
        """
    **확인해야 할 사항:**
    1. Secrets에 입력한 KOBIS API 키가 정확한지 확인해 주세요.
    2. KOBIS 개발자 센터에서 키가 활성화되어 있는지 확인해 주세요.
    """
    )
    st.stop()

# 3) 영화 목록 추출 및 비어있는지 검사
box_office_result = data.get("boxOfficeResult", {})
daily_list = box_office_result.get("dailyBoxOfficeList", [])

if not daily_list:
    st.info("ℹ️ 그날은 아직 집계 전입니다.")
    st.stop()


# ---------------------------------------------------------
# 7. 데이터 전처리 (문자열 -> 숫자 변환 및 가공)
# ---------------------------------------------------------
df = pd.DataFrame(daily_list)

# 숫자로 변환할 컬럼 지정
numeric_cols = [
    "rank",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "rankInten",
    "showCnt",
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)


# 순위 증감 기호 및 화살표 표현 함수
def format_rank_change(change_value):
    if change_value > 0:
        return f"🔺 +{change_value}"  # 빨간 위 화살표 (순위 상승)
    elif change_value < 0:
        return f"🔹 {change_value}"  # 파란 아래 화살표 (순위 하강)
    else:
        return "-"  # 변동 없음


# 전날 대비 순위 증감 텍스트 생성
df["rank_change_text"] = df["rankInten"].apply(format_rank_change)

# 누적 관객 100만 명(1,000,000) 이상인 경우 영화명에 🏆 이모지 추가
df["display_movie_nm"] = df.apply(
    lambda row: f"🏆 {row['movieNm']}"
    if row["audiAcc"] >= 1000000
    else row["movieNm"],
    axis=1,
)


# ---------------------------------------------------------
# 8. 1위 영화 지표 카드 (Metrics) 시각화
# ---------------------------------------------------------
top_movie = df[df["rank"] == 1].iloc[0]

st.markdown("---")
st.subheader(f"🥇 선택한 날짜의 1위: {top_movie['display_movie_nm']}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="당일 관객수", value=f"{top_movie['audiCnt']:,} 명")

with col2:
    st.metric(label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명")

with col3:
    st.metric(label="스크린수", value=f"{top_movie['scrnCnt']:,} 개")


# ---------------------------------------------------------
# 9. 관객수 상위 5편 막대그래프 시각화
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📊 관객수 상위 5개 영화")

top5_df = df.head(5)[["movieNm", "audiCnt"]].copy()
top5_df.rename(
    columns={"movieNm": "영화명", "audiCnt": "당일 관객수"}, inplace=True
)

st.bar_chart(data=top5_df, x="영화명", y="당일 관객수")


# ---------------------------------------------------------
# 10. 전체 순위표 (Table) 출력
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📋 전체 순위 목록")

# 화면에 보여줄 컬럼 지정 및 이름 변경
display_df = df[
    [
        "rank",
        "rank_change_text",
        "display_movie_nm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]
].copy()
display_df.columns = [
    "순위",
    "순위 증감",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수",
]

# 숫자에 천 단위 쉼표(,) 포맷팅을 적용하여 테이블 출력
st.dataframe(
    display_df.style.format(
        {"관객수": "{:,}", "누적관객": "{:,}", "스크린수": "{:,}"}
    ),
    use_container_width=True,
    hide_index=True,
)
