from datetime import datetime, timedelta
import zoneinfo
import pandas as pd
import requests
import streamlit as st


# ---------------------------------------------------------
# 1. 스트림릿 기본 설정 및 타이틀
# ---------------------------------------------------------
st.set_page_config(
    page_title="어제 박스오피스 순위", page_icon="🎬", layout="wide"
)

st.title("🎬 어제의 박스오피스 순위")


# ---------------------------------------------------------
# 2. 한국 시간 기준 '어제' 날짜 계산 함수
# ---------------------------------------------------------
def get_yesterday_kst():
    # 배포 서버의 시계가 해외 기준일 수 있으므로 한국 표준시(Asia/Seoul)를 명시적으로 지정합니다.
    kst_zone = zoneinfo.ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst_zone)
    yesterday = now_kst - timedelta(days=1)
    # KOBIS API 규격에 맞게 YYYYMMDD 형태의 문자열로 변환합니다.
    return yesterday.strftime("%Y%m%d")


target_date = get_yesterday_kst()
# 사용자에게 보여줄 날짜 형식 (YYYY년 MM월 DD일)
formatted_date = datetime.strptime(target_date, "%Y%m%d").strftime(
    "%Y년 %m월 %d일"
)
st.subheader(f"📅 {formatted_date} 집계 기준")


# ---------------------------------------------------------
# 3. KOBIS API 데이터 불러오기 함수 (캐싱 적용)
# ---------------------------------------------------------
# st.cache_data를 이용해 동일한 날짜 요청은 1시간(3600초) 동안 API를 재호출하지 않고 저장된 데이터를 사용합니다.
@st.cache_data(ttl=3600)
def fetch_box_office_data(api_key, date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": date_str}

    try:
        response = requests.get(url, params=params, timeout=10)
        # 네트워크 오류 등으로 응답 코드가 200이 아닌 경우 예외 발생
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        # 통신 에러 발생 시 에러 메시지 반환
        return None, str(e)


# ---------------------------------------------------------
# 4. Secrets에서 API 키 불러오기 및 예외 처리
# ---------------------------------------------------------
# Streamlit Cloud의 Secrets에 등록된 KOBIS_KEY를 확인합니다.
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

# 데이터 불러오기 실행
data, network_error = fetch_box_office_data(api_key, target_date)


# ---------------------------------------------------------
# 5. API 응답 및 데이터 유효성 검사 (오류 상자 처리)
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
    st.warning("⚠️ 해당 날짜의 박스오피스 데이터가 비어 있습니다.")
    st.info(
        """
    **확인해야 할 사항:**
    1. KOBIS API 서비스 집계 일정에 따라 일시적으로 데이터가 제공되지 않을 수 있습니다.
    2. 잠시 후 다시 시도해 주세요.
    """
    )
    st.stop()


# ---------------------------------------------------------
# 6. 데이터 전처리 (문자열 -> 숫자 변환)
# ---------------------------------------------------------
df = pd.DataFrame(daily_list)

# 숫자로 변환해야 할 컬럼 지정
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
        # 문자열 숫자를 실제 숫자 타입(int)으로 변경 (변환 실패 시 0 처리)
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)


# ---------------------------------------------------------
# 7. 1위 영화 지표 카드 (Metrics) 시각화
# ---------------------------------------------------------
top_movie = df[df["rank"] == 1].iloc[0]

st.markdown("---")
st.subheader(f"🥇 오늘의 1위: {top_movie['movieNm']}")

# 3개의 컬럼으로 나누어 지표 카드 배치
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="어제 관객수", value=f"{top_movie['audiCnt']:,} 명")

with col2:
    st.metric(label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명")

with col3:
    st.metric(label="스크린수", value=f"{top_movie['scrnCnt']:,} 개")


# ---------------------------------------------------------
# 8. 관객수 상위 5편 막대그래프 시각화
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📊 관객수 상위 5개 영화")

# 상위 5개 데이터 추출 및 차트용 DataFrame 생성
top5_df = df.head(5)[["movieNm", "audiCnt"]].copy()
top5_df.rename(
    columns={"movieNm": "영화명", "audiCnt": "어제 관객수"}, inplace=True
)

# Streamlit 내장 막대그래프 (x축: 영화명, y축: 관객수)
st.bar_chart(data=top5_df, x="영화명", y="어제 관객수")


# ---------------------------------------------------------
# 9. 전체 순위표 (Table) 출력
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📋 전체 순위 목록")

# 화면에 보여줄 컬럼 선택 및 이름 변경
display_df = df[
    ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].copy()
display_df.columns = [
    "순위",
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
