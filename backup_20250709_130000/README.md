# 🔬 HITRAN CRDS Simulator

고해상도 분광학 시뮬레이션을 위한 HITRAN 데이터베이스 기반 CRDS (Cavity Ring-Down Spectroscopy) 시뮬레이터입니다.

## 🌟 주요 기능

### 📊 시뮬레이션 모드
- **🧪 혼합 스펙트럼**: 여러 분자 동시 분석
- **📈 농도별 분석**: 농도-흡광도 선형성 분석

### 🔬 분광기 모드
- **🌟 기본 HITRAN**: 표준 흡수 스펙트럼
- **🔬 OA-ICOS**: Off-Axis Integrated Cavity Output Spectroscopy

### 🌊 Line Shape 모델
- **Voigt**: 도플러 + 압력 확산 조합 (추천)
- **Gaussian**: 도플러 확산 지배적 (저압)
- **Lorentzian**: 압력 확산 지배적 (고압)
- **Hartmann-Tran**: 모든 물리적 효과 포함 (최고 정확도)

### 🌬️ Matrix Gas 지원
- Air, CDA, N2, O2, He, H2, Ar, CO2, Zero Air
- 압력 확산 및 선 이동 효과
- 고급 압력 설정

### 🔬 해상도 설정
- ⚡ 빠른 (3,000 포인트)
- 🎯 표준 (10,000 포인트)
- 🔬 고해상도 (30,000 포인트)
- 🚀 최대 해상도 (100,000 포인트)

## 🚀 설치 및 실행

### 1. 환경 설정
```bash
# 가상환경 생성
python -m venv hitran_env

# 가상환경 활성화 (Windows)
hitran_env\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source hitran_env/bin/activate
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 실행
```bash
# 리팩토링된 버전 (권장)
streamlit run ui/HITRAN_Simulator_Refactored.py

# 기존 버전
streamlit run ui/HITRAN_Simulator.py
```

## 📁 프로젝트 구조

```
hitran_crds_simulator_v2/
├── 📁 ui/                          # 사용자 인터페이스
│   ├── 📁 components/              # UI 컴포넌트
│   │   ├── sidebar.py              # 사이드바 설정
│   │   ├── simulation_engine.py    # 시뮬레이션 엔진
│   │   └── visualization.py        # 시각화 컴포넌트
│   ├── 📁 models/                  # 데이터 모델
│   │   └── config.py               # 설정 데이터 클래스
│   ├── 📁 utils/                   # 유틸리티
│   │   └── helpers.py              # 헬퍼 함수들
│   ├── HITRAN_Simulator.py         # 기존 메인 파일
│   └── HITRAN_Simulator_Refactored.py  # 리팩토링된 메인 파일
├── 📁 core/                        # 핵심 계산 모듈
│   ├── line_shape_calculator.py    # Line Shape 계산
│   └── oa_icos_simulator.py        # OA-ICOS 시뮬레이터
├── 📁 data_handler/                # 데이터 처리
│   └── hitran_api.py               # HITRAN API 클라이언트
├── 📁 spectrum_calc/               # 스펙트럼 계산
│   └── absorption.py               # 흡수 스펙트럼 계산
├── 📁 cache/                       # 캐시 데이터
├── 📁 output/                      # 출력 파일
├── constants.py                    # 상수 정의
└── README.md                       # 프로젝트 문서
```

## 🎯 사용법

### 1. 기본 설정
1. **분광기 종류** 선택 (기본 HITRAN / OA-ICOS)
2. **분석 모드** 선택 (혼합 스펙트럼 / 농도별 분석)
3. **온도** 설정 (200-400K)
4. **파장 범위** 설정 (100nm-1,000,000nm)

### 2. 해상도 설정
- **⚡ 빠른**: 빠른 계산, 낮은 정확도
- **🎯 표준**: 균형잡힌 성능 (권장)
- **🔬 고해상도**: 높은 정확도, 느린 계산
- **🚀 최대 해상도**: 최고 정확도, 매우 느린 계산

### 3. 분자 선택
- **혼합 스펙트럼**: 최대 10개 분자 동시 선택
- **농도별 분석**: 1개 분자 선택
- **동위원소**: 각 분자별 동위원소 선택 가능

### 4. Matrix Gas 설정
- **기본 설정**: Gas 종류, 총 압력
- **고급 설정**: 압력 확산, 선 이동 효과

### 5. OA-ICOS 설정 (분광기 모드)
- **미러 반사율**: 0.99000-0.99999
- **캐비티 길이**: 1-200cm
- **Line Shape 모델**: Voigt, Gaussian, Lorentzian, Hartmann-Tran

## 📊 결과 해석

### 혼합 스펙트럼
- 개별 분자 스펙트럼
- 혼합 스펙트럼
- OA-ICOS 향상 효과 (분광기 모드)

### 농도별 분석
- 농도-흡광도 선형성
- R² 값 (선형성 지표)
- 검출한계 (3σ)
- OA-ICOS 향상 효과

## 🔧 기술 스택

- **Python**: 3.8+
- **Streamlit**: 웹 인터페이스
- **Plotly**: 인터랙티브 시각화
- **NumPy/SciPy**: 수치 계산
- **Astroquery**: HITRAN 데이터베이스 접근
- **Pandas**: 데이터 처리

## 📈 성능 정보

### 해상도별 성능
| 해상도 모드 | 포인트 수 | 파장 해상도 | 계산 시간 | 메모리 사용량 |
|------------|-----------|-------------|-----------|---------------|
| ⚡ 빠른 | 3,000 | ~0.0017 nm | 빠름 | 낮음 |
| 🎯 표준 | 10,000 | ~0.0005 nm | 보통 | 보통 |
| 🔬 고해상도 | 30,000 | ~0.0002 nm | 느림 | 높음 |
| 🚀 최대 | 100,000 | ~0.00005 nm | 매우 느림 | 매우 높음 |

### OA-ICOS 향상 효과
- **유효 광경로**: 50cm → 10,000cm+ (200배 향상)
- **감도 향상**: 100-1000배
- **검출한계**: ppb → ppt 수준

## 🐛 문제 해결

### 일반적인 문제
1. **HITRAN 데이터 없음**: 파장 범위 확인
2. **계산 시간 오래**: 해상도 낮추기
3. **메모리 부족**: 분자 수 줄이기

### 로그 확인
```bash
# Streamlit 로그 확인
streamlit run ui/HITRAN_Simulator_Refactored.py --logger.level debug
```

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

MIT License

## 📞 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해주세요.

---

**🔬 HITRAN CRDS Simulator** - 고해상도 분광학 시뮬레이션의 새로운 표준 