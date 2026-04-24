# 🔬 HITRAN Simulator vs HITRAN-PC 5.0 - 추가 기능 리스트

## 🚀 **우선순위 1: 핵심 물리 모델링**

### 📊 **Cross-Section 계산 기능**
- [ ] **Collision-Induced Absorption (CIA)** 모델링
  - H2-H2, H2-He, N2-N2, O2-O2 등 collision pairs
  - 온도 의존성 cross-section 계산
  - 현재: 없음 → 추가 필요

- [ ] **Continuum 흡수 모델**
  - Self-continuum (H2O-H2O) 
  - Foreign-continuum (H2O-N2, H2O-air)
  - MT_CKD 연속체 모델 통합
  - 현재: 없음 → 추가 필요

- [ ] **Rayleigh/Mie 산란**
  - 분자 Rayleigh 산란
  - 에어로졸 Mie 산란
  - 산란 계수 계산
  - 현재: 없음 → 추가 필요

### 🌡️ **고급 온도 모델링**
- [ ] **Non-LTE (Local Thermodynamic Equilibrium) 효과**
  - 상층 대기 조건 (>70km)
  - Vibrational temperature vs Rotational temperature
  - 현재: LTE만 지원 → Non-LTE 추가 필요

- [ ] **Temperature-dependent Line Mixing**
  - CO2 밴드에서 중요한 효과
  - 현재: 개별 라인만 → Line mixing 추가 필요

## 🔧 **우선순위 2: 데이터베이스 확장**

### 📂 **다중 데이터베이스 지원**
- [ ] **GEISA 데이터베이스** 연동
- [ ] **PNNL (Pacific Northwest National Laboratory)** 데이터
- [ ] **JPL (Jet Propulsion Laboratory)** 분자 스펙트럼
- [ ] **CDMS (Cologne Database for Molecular Spectroscopy)**
- [ ] **ExoMol** 데이터베이스 (고온 스펙트럼)

### 🧪 **추가 분자 종류**
- [ ] **Isotopologues 확장**
  - 현재: 주요 동위원소만 → 모든 동위원소 추가
- [ ] **Hot bands** 지원
- [ ] **Forbidden transitions** 계산

## 🎯 **우선순위 3: 전문적 분석 도구**

### 📈 **스펙트럼 분석 기능**
- [ ] **Line fitting algorithms**
  - Voigt profile fitting
  - Multi-line fitting
  - Background subtraction
  - 현재: 기본적 피팅만 → 고급 피팅 추가

- [ ] **Equivalent width 계산**
- [ ] **Column density 추출**
- [ ] **Mixing ratio 역산 (retrieval)**

### 🔬 **실험 조건 모델링**
- [ ] **Instrument Line Shape (ILS) 함수**
  - FTIR 분광기 ILS
  - Laser 분광기 linewidth
  - 현재: 기본 분해능만 → ILS 추가

- [ ] **Apodization 함수들**
  - Boxcar, Triangular, Happ-Genzel 등
  - 현재: 없음 → 추가 필요

- [ ] **Field of view (FOV) 효과**
- [ ] **Multiple scattering**

## 📊 **우선순위 4: 고급 시각화**

### 🎨 **전문적 플롯 기능**
- [ ] **Contour plots** (압력-온도 다이어그램)
- [ ] **Stick spectrum** 표시
- [ ] **Residual analysis** 자동화
- [ ] **Band assignment** 자동 라벨링

### 📋 **리포트 생성**
- [ ] **LaTeX 수식** 지원 리포트
- [ ] **학술 논문용** 플롯 스타일
- [ ] **HITRAN citation** 자동 생성

## 🌐 **우선순위 5: API 및 배치 처리**

### 🔌 **API 인터페이스**
- [ ] **REST API** 서비스
- [ ] **Python package** 형태 배포
- [ ] **Batch processing** 스크립트
- [ ] **Command line interface (CLI)**

### 📁 **데이터 포맷 지원**
- [ ] **HITRAN .par 파일** 직접 읽기
- [ ] **NetCDF** 포맷 지원
- [ ] **HDF5** 포맷 지원

## 🧮 **우선순위 6: 계산 최적화**

### ⚡ **성능 개선**
- [ ] **GPU 가속** (CUDA/OpenCL)
- [ ] **Parallel processing** 강화
- [ ] **Caching system** 개선
- [ ] **Memory optimization**

### 🎛️ **수치 정확도**
- [ ] **Double precision** 계산
- [ ] **Numerical integration** 개선
- [ ] **Convergence criteria** 설정

## 🔧 **구현 우선순위 권장사항**

### 🥇 **1단계 (즉시 추가 가능)**
1. **Collision-Induced Absorption** - 큰 파장 영역에서 중요
2. **Line fitting algorithms** - 실험 데이터 분석 필수
3. **Column density 계산** - 정량분석 핵심

### 🥈 **2단계 (중기 개발)**
1. **Continuum absorption** - 수증기 스펙트럼 정확도 향상
2. **Multi-database 지원** - 데이터 신뢰성 증대
3. **Non-LTE 모델** - 상층 대기 연구용

### 🥉 **3단계 (장기 개발)**
1. **GPU 가속** - 대용량 계산 처리
2. **Full API 서비스** - 상용화 준비
3. **Scattering models** - 대기 복사 전달 모델 통합

---

## 📝 **즉시 구현 가능한 간단한 기능들**

- [ ] HITRAN 데이터 다운로드 진행률 표시
- [ ] 계산 결과 캐싱 개선
- [ ] 더 많은 파장 단위 지원 (cm⁻¹, μm, THz)
- [ ] 분자별 기본 농도 설정 개선
- [ ] 에러 메시지 개선 및 도움말 확장 