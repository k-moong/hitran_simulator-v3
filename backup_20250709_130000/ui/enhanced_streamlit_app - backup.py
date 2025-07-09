"""
HITRAN CRDS 시뮬레이터 - 단순화 버전 (전체 분자 지원)
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import io
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator

# 페이지 설정
st.set_page_config(
    page_title="HITRAN CRDS Simulator Enhanced",
    page_icon="🌟",
    layout="wide"
)

# HITRAN 전체 분자 목록 (분자 ID와 함께)
HITRAN_MOLECULES = {
    # 주요 대기 성분
    "H2O": {"id": 1, "name": "물", "category": "주요 대기 성분", "common": True},
    "CO2": {"id": 2, "name": "이산화탄소", "category": "주요 대기 성분", "common": True},
    "O3": {"id": 3, "name": "오존", "category": "주요 대기 성분", "common": True},
    "N2O": {"id": 4, "name": "아산화질소", "category": "주요 대기 성분", "common": True},
    "CO": {"id": 5, "name": "일산화탄소", "category": "주요 대기 성분", "common": True},
    "CH4": {"id": 6, "name": "메탄", "category": "주요 대기 성분", "common": True},
    "O2": {"id": 7, "name": "산소", "category": "주요 대기 성분", "common": True},
    "NO": {"id": 8, "name": "일산화질소", "category": "질소 화합물", "common": True},
    "SO2": {"id": 9, "name": "이산화황", "category": "황 화합물", "common": True},
    "NO2": {"id": 10, "name": "이산화질소", "category": "질소 화합물", "common": True},
    "NH3": {"id": 11, "name": "암모니아", "category": "질소 화합물", "common": True},
    "HNO3": {"id": 12, "name": "질산", "category": "질소 화합물", "common": True},
    
    # 할로겐 화합물
    "OH": {"id": 13, "name": "하이드록실", "category": "라디칼", "common": False},
    "HF": {"id": 14, "name": "플루오르화수소", "category": "할로겐 화합물", "common": False},
    "HCl": {"id": 15, "name": "염화수소", "category": "할로겐 화합물", "common": False},
    "HBr": {"id": 16, "name": "브롬화수소", "category": "할로겐 화합물", "common": False},
    "HI": {"id": 17, "name": "요오드화수소", "category": "할로겐 화합물", "common": False},
    "ClO": {"id": 18, "name": "염소 산화물", "category": "할로겐 화합물", "common": False},
    "OCS": {"id": 19, "name": "황화카르보닐", "category": "황 화합물", "common": False},
    "H2CO": {"id": 20, "name": "포름알데히드", "category": "유기 화합물", "common": False},
    "HOCl": {"id": 21, "name": "차아염소산", "category": "할로겐 화합물", "common": False},
    "N2": {"id": 22, "name": "질소", "category": "주요 대기 성분", "common": False},
    "HCN": {"id": 23, "name": "시안화수소", "category": "유기 화합물", "common": False},
    "CH3Cl": {"id": 24, "name": "염화메틸", "category": "할로겐 화합물", "common": False},
    "H2O2": {"id": 25, "name": "과산화수소", "category": "산소 화합물", "common": False},
    "C2H2": {"id": 26, "name": "아세틸렌", "category": "유기 화합물", "common": False},
    "C2H6": {"id": 27, "name": "에탄", "category": "유기 화합물", "common": False},
    "PH3": {"id": 28, "name": "포스핀", "category": "인 화합물", "common": False},
    
    # CFC 및 HCFC
    "COF2": {"id": 29, "name": "플루오르화카르보닐", "category": "할로겐 화합물", "common": False},
    "SF6": {"id": 30, "name": "육플루오르화황", "category": "황 화합물", "common": False},
    "H2S": {"id": 31, "name": "황화수소", "category": "황 화합물", "common": False},
    "HCOOH": {"id": 32, "name": "개미산", "category": "유기 화합물", "common": False},
    "HO2": {"id": 33, "name": "하이드로퍼옥실", "category": "라디칼", "common": False},
    "O": {"id": 34, "name": "산소 원자", "category": "라디칼", "common": False},
    "ClONO2": {"id": 35, "name": "염소질산", "category": "할로겐 화합물", "common": False},
    "NO+": {"id": 36, "name": "질산 이온", "category": "이온", "common": False},
    "HOBr": {"id": 37, "name": "차아브롬산", "category": "할로겐 화합물", "common": False},
    "C2H4": {"id": 38, "name": "에틸렌", "category": "유기 화합물", "common": False},
    "CH3OH": {"id": 39, "name": "메탄올", "category": "유기 화합물", "common": False},
    "CH3Br": {"id": 40, "name": "브롬화메틸", "category": "할로겐 화합물", "common": False},
    "CH3CN": {"id": 41, "name": "아세토니트릴", "category": "유기 화합물", "common": False},
    "CF4": {"id": 42, "name": "사플루오르화탄소", "category": "할로겐 화합물", "common": False},
    "C4H2": {"id": 43, "name": "다이아세틸렌", "category": "유기 화합물", "common": False},
    "HC3N": {"id": 44, "name": "시아노아세틸렌", "category": "유기 화합물", "common": False},
    "H2": {"id": 45, "name": "수소", "category": "주요 대기 성분", "common": False},
    "CS": {"id": 46, "name": "황화탄소", "category": "황 화합물", "common": False},
    "SO3": {"id": 47, "name": "삼산화황", "category": "황 화합물", "common": False},
    "C2N2": {"id": 48, "name": "시안겐", "category": "유기 화합물", "common": False},
    "COCl2": {"id": 49, "name": "포스겐", "category": "할로겐 화합물", "common": False},
    "SO": {"id": 50, "name": "황 산화물", "category": "황 화합물", "common": False},
}

# 분자 카테고리 정의
MOLECULE_CATEGORIES = {
    "주요 대기 성분": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "주요 대기 성분"],
    "유기 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "유기 화합물"],
    "할로겐 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "할로겐 화합물"],
    "질소 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "질소 화합물"],
    "황 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "황 화합물"],
    "라디칼": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "라디칼"],
    "인 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "인 화합물"],
    "산소 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "산소 화합물"],
    "이온": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "이온"],
}

# 파장 대역 바로가기 정보
WAVELENGTH_SHORTCUTS = {
    "NIR_H2O_1": {"min": 1350, "max": 1400, "description": "H2O 1차 배음대"},
    "NIR_H2O_2": {"min": 1500, "max": 1600, "description": "H2O 2차 배음대"},  
    "NIR_H2O_3": {"min": 1850, "max": 1950, "description": "H2O 3차 배음대"},
    "NIR_CH4": {"min": 1630, "max": 1680, "description": "CH4 2ν3 대역"},
    "NIR_CO2": {"min": 2000, "max": 2100, "description": "CO2 조합대역"},
    "NIR_NH3": {"min": 1500, "max": 1600, "description": "NH3 2ν1 대역"},
    "MIR_H2O": {"min": 2500, "max": 3000, "description": "H2O 기본 진동"},
    "MIR_CO2": {"min": 4200, "max": 4400, "description": "CO2 ν3 대역"},
    "MIR_CH4": {"min": 3200, "max": 3400, "description": "CH4 ν3 대역"},
    "MIR_N2O": {"min": 4400, "max": 4600, "description": "N2O ν3 대역"},
    "MIR_HCl": {"min": 2800, "max": 3000, "description": "HCl 기본 진동"},
    "MIR_HF": {"min": 3900, "max": 4100, "description": "HF 기본 진동"},
    "MIR_CO": {"min": 2100, "max": 2200, "description": "CO 기본 진동"},
    "MIR_NO": {"min": 1800, "max": 2000, "description": "NO 기본 진동"},
    "MIR_SO2": {"min": 1100, "max": 1400, "description": "SO2 ν1,ν3 대역"},
}

# Session State 초기화
if 'calculation_results' not in st.session_state:
    st.session_state.calculation_results = None
if 'calculation_params' not in st.session_state:
    st.session_state.calculation_params = None

# 제목
st.title("🌟 HITRAN CRDS Simulator Enhanced")
st.markdown("**전체 HITRAN 분자 지원 및 프리셋 관리**")

# 사이드바 - 파라미터 설정
with st.sidebar:
    st.header("📊 시뮬레이션 파라미터")
    
    # 분자 선택 (단순화)
    st.subheader("🧪 분자 선택")
    
    # 분자 선택 방법
    selection_method = st.radio(
        "선택 방법:",
        ["카테고리별", "자주 사용", "전체 목록", "검색"],
        index=0
    )
    
    selected_molecules = []
    
    if selection_method == "카테고리별":
        # 카테고리 선택
        selected_category = st.selectbox("분자 카테고리", list(MOLECULE_CATEGORIES.keys()))
        available_mols = MOLECULE_CATEGORIES[selected_category]
        
        selected_molecules = st.multiselect(
            f"{selected_category} ({len(available_mols)}개)",
            available_mols,
            default=available_mols[:3] if len(available_mols) >= 3 else available_mols,
            format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})"
        )
    
    elif selection_method == "자주 사용":
        # 자주 사용하는 분자
        common_molecules = [mol for mol, info in HITRAN_MOLECULES.items() if info["common"]]
        
        selected_molecules = st.multiselect(
            f"자주 사용하는 분자 ({len(common_molecules)}개)",
            common_molecules,
            default=["H2O", "CO2", "CH4"],
            format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})"
        )
    
    elif selection_method == "전체 목록":
        # 전체 분자 목록
        all_molecules = list(HITRAN_MOLECULES.keys())
        
        selected_molecules = st.multiselect(
            f"전체 분자 목록 ({len(all_molecules)}개)",
            all_molecules,
            default=["H2O"],
            format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})",
            help="최대 15개까지 선택 가능합니다."
        )
    
    elif selection_method == "검색":
        # 검색 기능
        search_term = st.text_input("분자 검색", placeholder="분자명 또는 화학식 입력")
        
        if search_term:
            # 검색 결과 필터링
            filtered_molecules = []
            for mol, info in HITRAN_MOLECULES.items():
                if (search_term.lower() in mol.lower() or 
                    search_term.lower() in info["name"].lower()):
                    filtered_molecules.append(mol)
            
            if filtered_molecules:
                selected_molecules = st.multiselect(
                    f"검색 결과 ({len(filtered_molecules)}개)",
                    filtered_molecules,
                    format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})"
                )
            else:
                st.info("검색 결과가 없습니다.")
        else:
            st.info("검색어를 입력하세요.")
    
    # 선택된 분자 표시
    if selected_molecules:
        st.success(f"✅ {len(selected_molecules)}개 분자 선택됨")
        
        # 너무 많은 분자 선택 방지
        if len(selected_molecules) > 15:
            st.warning("⚠️ 너무 많은 분자가 선택되었습니다. 15개까지만 선택해주세요.")
            selected_molecules = selected_molecules[:15]
    
    # 파장 범위
    st.subheader("📏 파장 범위 (nm)")
    
    # 파장 바로가기
    shortcut_expander = st.expander("🔗 파장 대역 바로가기")
    with shortcut_expander:
        for shortcut_id, shortcut_data in WAVELENGTH_SHORTCUTS.items():
            if st.button(f"{shortcut_data['description']}", key=f"shortcut_{shortcut_id}"):
                st.session_state.wavelength_min = shortcut_data['min']
                st.session_state.wavelength_max = shortcut_data['max']
                st.rerun()
    
    # 파장 입력
    col1, col2 = st.columns(2)
    with col1:
        wavelength_min = st.number_input(
            "최소", 
            value=getattr(st.session_state, 'wavelength_min', 1500), 
            min_value=100, 
            max_value=50000, 
            step=1
        )
    with col2:
        wavelength_max = st.number_input(
            "최대", 
            value=getattr(st.session_state, 'wavelength_max', 1520), 
            min_value=100, 
            max_value=50000, 
            step=1
        )
    
    # 물리 조건
    st.subheader("🌡️ 물리 조건")
    
    temperature = st.number_input(
        "온도 (K)", 
        value=296.15, 
        min_value=200.0, 
        max_value=400.0, 
        step=0.1,
        format="%.2f"
    )
    
    pressure_torr = st.number_input(
        "압력 (torr)", 
        value=760.0,
        min_value=1.0, 
        max_value=15000.0, 
        step=1.0,
        format="%.1f"
    )
    
    path_length_m = st.number_input(
        "경로 길이 (m)", 
        value=1000.0,
        min_value=1.0, 
        max_value=50000.0, 
        step=1.0,
        format="%.0f"
    )
    
    # 분자별 농도 설정
    molecule_concentrations = {}
    if selected_molecules:
        st.subheader("🧪 분자별 농도 (ppb)")
        
        # 농도 입력 방식 선택
        conc_method = st.radio(
            "농도 입력 방식",
            ["개별 설정", "일괄 설정"],
            index=0
        )
        
        if conc_method == "일괄 설정":
            # 일괄 농도 설정
            bulk_concentration = st.number_input(
                "모든 분자 농도 (ppb)",
                value=1000.0,
                min_value=0.1,
                max_value=10000000.0,
                step=0.1,
                format="%.1f"
            )
            
            for molecule in selected_molecules:
                molecule_concentrations[molecule] = bulk_concentration
                
            st.info(f"모든 분자: {bulk_concentration:.1f} ppb")
        
        else:
            # 개별 농도 설정
            for molecule in selected_molecules:
                mol_info = HITRAN_MOLECULES[molecule]
                
                # 기본 농도 설정 (일반적인 대기 농도 기준)
                if molecule == "H2O":
                    default_conc = 10000.0
                elif molecule == "CO2":
                    default_conc = 400000.0
                elif molecule == "CH4":
                    default_conc = 1800.0
                elif molecule == "N2O":
                    default_conc = 330.0
                elif molecule == "CO":
                    default_conc = 100.0
                else:
                    default_conc = 100.0
                
                concentration = st.number_input(
                    f"{molecule} ({mol_info['name']})",
                    value=default_conc,
                    min_value=0.1,
                    max_value=10000000.0,
                    step=0.1,
                    format="%.1f",
                    key=f"conc_{molecule}",
                    help=f"카테고리: {mol_info['category']}"
                )
                molecule_concentrations[molecule] = concentration
    
    # 계산 버튼
    st.markdown("---")
    calculate_button = st.button("🧮 혼합 스펙트럼 계산", type="primary", use_container_width=True)
    
    # 결과 초기화 버튼
    if st.session_state.calculation_results is not None:
        clear_button = st.button("🗑️ 결과 초기화", type="secondary", use_container_width=True)
        if clear_button:
            st.session_state.calculation_results = None
            st.session_state.calculation_params = None
            st.rerun()

# 단위 변환
pressure_atm = pressure_torr / 760.0
path_length_km = path_length_m / 1000.0

# 메인 화면
col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("📋 현재 설정")
    st.write(f"**선택된 분자:** {len(selected_molecules)}개")
    
    if selected_molecules:
        # 카테고리별 분자 분류
        categories_used = {}
        for mol in selected_molecules:
            cat = HITRAN_MOLECULES[mol]["category"]
            if cat not in categories_used:
                categories_used[cat] = []
            categories_used[cat].append(mol)
        
        for cat, mols in categories_used.items():
            st.write(f"  - **{cat}:** {', '.join(mols)}")
    
    st.write(f"**온도:** {temperature} K ({temperature-273.15:.1f}°C)")
    st.write(f"**압력:** {pressure_torr:.1f} torr ({pressure_atm:.2f} atm)")
    st.write(f"**경로 길이:** {path_length_m:.0f} m ({path_length_km:.1f} km)")
    st.write(f"**파장 범위:** {wavelength_min}-{wavelength_max} nm")
    
    if selected_molecules and molecule_concentrations:
        st.subheader("🧪 분자별 농도")
        
        # 농도 요약 통계
        total_conc = sum(molecule_concentrations.values())
        st.metric("총 농도", f"{total_conc:.1f} ppb", f"{total_conc/1000:.3f} ppm")
        
        # 모든 분자 표시 (상위 10개까지)
        sorted_molecules = sorted(selected_molecules, 
                                key=lambda x: molecule_concentrations.get(x, 0), 
                                reverse=True)
        
        for i, molecule in enumerate(sorted_molecules[:10]):
            conc_ppb = molecule_concentrations.get(molecule, 0)
            conc_ppm = conc_ppb / 1000.0
            st.write(f"**{molecule}:** {conc_ppb:.1f} ppb ({conc_ppm:.3f} ppm)")
        
        if len(selected_molecules) > 10:
            with st.expander(f"나머지 {len(selected_molecules)-10}개 분자 보기"):
                for molecule in sorted_molecules[10:]:
                    conc_ppb = molecule_concentrations.get(molecule, 0)
                    conc_ppm = conc_ppb / 1000.0
                    st.write(f"**{molecule}:** {conc_ppb:.1f} ppb ({conc_ppm:.3f} ppm)")

# 계산 실행
with col1:
    if calculate_button and selected_molecules:
        if wavelength_min >= wavelength_max:
            st.error("❌ 최소 파장이 최대 파장보다 작아야 합니다!")
        elif len(selected_molecules) > 15:
            st.error("❌ 최대 15개 분자까지만 선택할 수 있습니다!")
        else:
            # 진행 표시
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 주파수 격자 생성
                freq_min = 1e7 / wavelength_max
                freq_max = 1e7 / wavelength_min
                frequency_grid = np.linspace(freq_min, freq_max, 5000)
                
                # 각 분자별 스펙트럼 계산
                hitran_api = HitranAPI()
                calc = SpectrumCalculator()
                
                individual_spectra = {}
                combined_absorption = np.zeros_like(frequency_grid)
                failed_molecules = []
                
                for i, molecule in enumerate(selected_molecules):
                    progress = int(20 + (i / len(selected_molecules)) * 60)
                    status_text.text(f"📥 {molecule} ({HITRAN_MOLECULES[molecule]['name']}) 데이터 다운로드 중... ({i+1}/{len(selected_molecules)})")
                    progress_bar.progress(progress)
                    
                    # HITRAN 데이터 다운로드
                    try:
                        hitran_data = hitran_api.download_molecule_data(molecule, wavelength_min, wavelength_max)
                        
                        if hitran_data is not None and len(hitran_data) > 0:
                            # 개별 스펙트럼 계산
                            concentration = molecule_concentrations[molecule] / 1e9  # ppb to 몰분율
                            
                            spectrum = calc.calculate_absorption_spectrum(
                                hitran_data=hitran_data,
                                frequency_grid=frequency_grid,
                                temperature=temperature,
                                pressure=pressure_atm,
                                concentration=concentration,
                                path_length=path_length_m,
                                molecule=molecule
                            )
                            
                            individual_spectra[molecule] = spectrum
                            combined_absorption += spectrum['absorption_coeff']
                        else:
                            failed_molecules.append(molecule)
                    
                    except Exception as e:
                        failed_molecules.append(molecule)
                        st.warning(f"⚠️ {molecule} 처리 중 오류: {str(e)}")
                
                # 성공한 분자가 있는 경우에만 계속 진행
                if individual_spectra:
                    # 혼합 스펙트럼 계산
                    status_text.text("🧮 혼합 스펙트럼 계산 중...")
                    progress_bar.progress(80)
                    
                    combined_transmittance = np.exp(-combined_absorption * path_length_m)
                    combined_absorbance = -np.log10(combined_transmittance)
                    wavelength_nm = 1e7 / frequency_grid
                    
                    # 분자별 기여도 계산
                    contribution_data = []
                    for molecule, spectrum in individual_spectra.items():
                        max_abs = np.max(spectrum['absorbance'])
                        avg_abs = np.mean(spectrum['absorbance'])
                        mol_info = HITRAN_MOLECULES[molecule]
                        
                        contribution_data.append({
                            '분자': molecule,
                            '한국명': mol_info['name'],
                            '카테고리': mol_info['category'],
                            '최대 흡광도': f"{max_abs:.6f}",
                            '평균 흡광도': f"{avg_abs:.6f}",
                            '농도 (ppb)': f"{molecule_concentrations[molecule]:.1f}",
                            '기여율': f"{(max_abs / np.max(combined_absorbance) * 100):.1f}%" if np.max(combined_absorbance) > 0 else "0%"
                        })
                    
                    # Session State에 결과 저장
                    st.session_state.calculation_results = {
                        'individual_spectra': individual_spectra,
                        'combined_transmittance': combined_transmittance,
                        'combined_absorbance': combined_absorbance,
                        'wavelength_nm': wavelength_nm,
                        'combined_absorption': combined_absorption,
                        'contribution_data': contribution_data,
                        'failed_molecules': failed_molecules,
                        'total_lines': sum(len(hitran_api.download_molecule_data(mol, wavelength_min, wavelength_max) or []) 
                                         for mol in individual_spectra.keys())
                    }
                    
                    # 파라미터도 저장
                    st.session_state.calculation_params = {
                        'selected_molecules': selected_molecules.copy(),
                        'successful_molecules': list(individual_spectra.keys()),
                        'wavelength_min': wavelength_min,
                        'wavelength_max': wavelength_max,
                        'temperature': temperature,
                        'pressure_torr': pressure_torr,
                        'pressure_atm': pressure_atm,
                        'path_length_m': path_length_m,
                        'path_length_km': path_length_km,
                        'molecule_concentrations': molecule_concentrations.copy()
                    }
                    
                    progress_bar.progress(100)
                    status_text.text("✅ 혼합 스펙트럼 계산 완료!")
                    
                    if failed_molecules:
                        st.warning(f"⚠️ {len(failed_molecules)}개 분자에서 데이터를 찾을 수 없었습니다: {', '.join(failed_molecules)}")
                    
                else:
                    st.error("❌ 선택한 파장 범위에서 사용 가능한 분자 데이터가 없습니다!")
                    progress_bar.empty()
                    status_text.empty()
                
            except Exception as e:
                st.error(f"❌ 에러 발생: {str(e)}")
                progress_bar.empty()
                status_text.empty()
    
    elif calculate_button and not selected_molecules:
        st.warning("⚠️ 분석할 분자를 선택해주세요!")
    
    elif not selected_molecules:
        st.info("👈 왼쪽에서 분자를 선택하고 조건을 설정하세요!")
        
        # HITRAN 분자 데이터베이스 정보
        st.subheader("🧬 HITRAN 분자 데이터베이스")
        
        # 카테고리별 분자 수
        category_stats = {}
        for mol, info in HITRAN_MOLECULES.items():
            cat = info["category"]
            if cat not in category_stats:
                category_stats[cat] = 0
            category_stats[cat] += 1
        
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        
        with col_stats1:
            st.metric("총 분자 수", len(HITRAN_MOLECULES))
        
        with col_stats2:
            st.metric("카테고리 수", len(category_stats))
        
        with col_stats3:
            common_count = len([mol for mol, info in HITRAN_MOLECULES.items() if info["common"]])
            st.metric("자주 사용", common_count)
        
        # 카테고리별 분자 수 차트
        st.subheader("📊 카테고리별 분자 분포")
        cat_df = pd.DataFrame([
            {"카테고리": cat, "분자 수": count}
            for cat, count in category_stats.items()
        ])
        st.bar_chart(cat_df.set_index("카테고리"))
        
        # 자주 사용하는 분자들 미리보기
        st.subheader("⭐ 자주 사용하는 분자들")
        common_molecules = [mol for mol, info in HITRAN_MOLECULES.items() if info["common"]]
        common_preview = []
        for mol in common_molecules[:8]:
            info = HITRAN_MOLECULES[mol]
            common_preview.append({
                "분자": mol,
                "한국명": info['name'],
                "카테고리": info['category']
            })
        
        common_df = pd.DataFrame(common_preview)
        st.dataframe(common_df, use_container_width=True)

# 저장된 결과 표시
if st.session_state.calculation_results is not None:
    results = st.session_state.calculation_results
    params = st.session_state.calculation_params
    
    with col1:
        # 그래프 생성
        st.subheader("📊 스펙트럼 결과")
        
        # 성공한 분자 정보
        successful_molecules = params['successful_molecules']
        failed_molecules = results.get('failed_molecules', [])
        
        if failed_molecules:
            st.warning(f"⚠️ 데이터 없음: {', '.join(failed_molecules)}")
        
        st.success(f"✅ 성공적으로 계산된 분자: {len(successful_molecules)}개")
        
        # 색상 팔레트
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan',
                 'magenta', 'yellow', 'navy', 'maroon', 'lime']
        
        # Plotly 그래프 생성
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('개별 분자 흡광도', '혼합 투과율', '혼합 흡광도'),
            vertical_spacing=0.08
        )
        
        # 1. 개별 분자 흡광도
        for i, (molecule, spectrum) in enumerate(results['individual_spectra'].items()):
            mol_info = HITRAN_MOLECULES[molecule]
            fig.add_trace(
                go.Scatter(
                    x=results['wavelength_nm'],
                    y=spectrum['absorbance'],
                    mode='lines',
                    name=f'{molecule} ({mol_info["name"]})',
                    line=dict(color=colors[i % len(colors)], width=1),
                    hovertemplate=f'<b>{molecule}</b><br>파장: %{{x:.1f}} nm<br>흡광도: %{{y:.6f}}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 2. 혼합 투과율
        fig.add_trace(
            go.Scatter(
                x=results['wavelength_nm'],
                y=results['combined_transmittance'],
                mode='lines',
                name='혼합 투과율',
                line=dict(color='black', width=2),
                hovertemplate='파장: %{x:.1f} nm<br>투과율: %{y:.6f}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 3. 혼합 흡광도
        fig.add_trace(
            go.Scatter(
                x=results['wavelength_nm'],
                y=results['combined_absorbance'],
                mode='lines',
                name='혼합 흡광도',
                line=dict(color='darkred', width=2),
                hovertemplate='파장: %{x:.1f} nm<br>흡광도: %{y:.6f}<extra></extra>'
            ),
            row=3, col=1
        )
        
        # 레이아웃 설정
        fig.update_layout(
            height=900,
            title=f"혼합 가스 스펙트럼 ({len(successful_molecules)}개 분자)",
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )
        
        fig.update_xaxes(title_text="파장 (nm)", row=3, col=1)
        fig.update_yaxes(title_text="흡광도", row=1, col=1)
        fig.update_yaxes(title_text="투과율", row=2, col=1)
        fig.update_yaxes(title_text="흡광도", row=3, col=1)
       
        # 그래프 표시
        st.plotly_chart(fig, use_container_width=True)
       
        # 결과 분석
        st.subheader("📈 분석 결과")
       
        col_a, col_b, col_c, col_d = st.columns(4)
       
        with col_a:
            st.metric("성공한 분자", f"{len(successful_molecules)}")
       
        with col_b:
            st.metric("총 HITRAN 라인 수", f"{results['total_lines']:,}")
       
        with col_c:
            st.metric("최소 투과율", f"{np.min(results['combined_transmittance']):.6f}")
       
        with col_d:
            st.metric("최대 흡광도", f"{np.max(results['combined_absorbance']):.6f}")
       
        # 분자별 기여도
        st.subheader("🔍 분자별 기여도")
        df = pd.DataFrame(results['contribution_data'])
        
        # 기여율 순으로 정렬
        df['기여율_숫자'] = df['기여율'].str.rstrip('%').astype(float)
        df = df.sort_values('기여율_숫자', ascending=False).drop('기여율_숫자', axis=1)
        
        st.dataframe(df, use_container_width=True)
       
        # 스펙트럼 간섭 분석
        if len(results['individual_spectra']) > 1:
            st.subheader("⚠️ 스펙트럼 간섭 분석")
            overlap_threshold = 0.001
            
            overlap_regions = []
            for i in range(len(results['wavelength_nm'])):
                overlapping_molecules = []
                for molecule, spectrum in results['individual_spectra'].items():
                    if spectrum['absorbance'][i] > overlap_threshold:
                        overlapping_molecules.append(molecule)
               
                if len(overlapping_molecules) > 1:
                    overlap_regions.append({
                        '파장 (nm)': f"{results['wavelength_nm'][i]:.1f}",
                        '간섭 분자': ', '.join(overlapping_molecules),
                        '간섭 수': len(overlapping_molecules),
                        '간섭 강도': 'High' if len(overlapping_molecules) > 3 else 'Medium'
                    })
           
            if overlap_regions:
                # 중복 제거 및 그룹화
                overlap_summary = {}
                for region in overlap_regions:
                    key = region['간섭 분자']
                    if key not in overlap_summary:
                        overlap_summary[key] = {
                            '간섭 분자': key,
                            '간섭 수': region['간섭 수'],
                            '간섭 강도': region['간섭 강도'],
                            '발생 횟수': 0
                        }
                    overlap_summary[key]['발생 횟수'] += 1
               
                st.warning(f"🔍 {len(overlap_summary)}가지 유형의 스펙트럼 간섭이 발견되었습니다.")
                overlap_df = pd.DataFrame(list(overlap_summary.values()))
                overlap_df = overlap_df.sort_values('간섭 수', ascending=False)
                st.dataframe(overlap_df, use_container_width=True)
            else:
                st.success("✅ 선택한 파장 범위에서 심각한 스펙트럼 간섭이 발견되지 않았습니다.")
       
        # 데이터 내보내기 섹션
        st.subheader("📁 데이터 내보내기")
       
        col_download1, col_download2, col_download3 = st.columns(3)
       
        with col_download1:
            # 스펙트럼 데이터 CSV
            spectrum_data = {
                'Wavelength_nm': results['wavelength_nm'],
                'Combined_Transmittance': results['combined_transmittance'],
                'Combined_Absorbance': results['combined_absorbance']
            }
           
            for molecule, spectrum in results['individual_spectra'].items():
                spectrum_data[f'{molecule}_Transmittance'] = spectrum['transmittance']
                spectrum_data[f'{molecule}_Absorbance'] = spectrum['absorbance']
           
            spectrum_df = pd.DataFrame(spectrum_data)
            csv_data = spectrum_df.to_csv(index=False)
           
            st.download_button(
                label="📊 스펙트럼 데이터 (CSV)",
                data=csv_data,
                file_name=f"spectrum_data_{len(successful_molecules)}molecules_{params['wavelength_min']}-{params['wavelength_max']}nm.csv",
                mime="text/csv"
            )
       
        with col_download2:
            # 계산 조건 요약
            summary_text = f"""HITRAN CRDS 시뮬레이션 결과 요약
=================================

계산 일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

분석 조건:
- 선택 분자: {len(params['selected_molecules'])}개 (성공: {len(successful_molecules)}개)
- 성공한 분자: {', '.join(successful_molecules)}
"""
            
            if failed_molecules:
                summary_text += f"- 실패한 분자: {', '.join(failed_molecules)}\n"
            
            summary_text += f"""
- 온도: {params['temperature']} K ({params['temperature']-273.15:.1f}°C)
- 압력: {params['pressure_torr']:.1f} torr ({params['pressure_atm']:.2f} atm)
- 경로 길이: {params['path_length_m']:.0f} m ({params['path_length_km']:.1f} km)
- 파장 범위: {params['wavelength_min']}-{params['wavelength_max']} nm

분자별 농도:
"""
            for molecule in successful_molecules:
                conc_ppb = params['molecule_concentrations'].get(molecule, 0)
                mol_info = HITRAN_MOLECULES[molecule]
                summary_text += f"- {molecule} ({mol_info['name']}): {conc_ppb:.1f} ppb ({conc_ppb/1000:.3f} ppm)\n"
           
            summary_text += f"\n총 농도: {sum(params['molecule_concentrations'][mol] for mol in successful_molecules):.1f} ppb\n"
            
            summary_text += f"""
분석 결과:
- 최소 투과율: {np.min(results['combined_transmittance']):.6f}
- 최대 흡광도: {np.max(results['combined_absorbance']):.6f}
- 총 HITRAN 라인 수: {results['total_lines']:,}

분자별 기여도:
"""
            for data in results['contribution_data']:
                summary_text += f"- {data['분자']} ({data['한국명']}): 최대 흡광도 {data['최대 흡광도']}, 기여율 {data['기여율']}\n"
           
            st.download_button(
                label="📋 분석 요약 (TXT)",
                data=summary_text,
                file_name=f"analysis_summary_{len(successful_molecules)}molecules_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
       
        with col_download3:
            # 기여도 데이터 엑셀
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # 기본 정보
                info_df = pd.DataFrame({
                    '항목': ['온도 (K)', '압력 (torr)', '경로길이 (m)', '파장범위 (nm)', '성공 분자수', '총농도 (ppb)'],
                    '값': [params['temperature'], params['pressure_torr'], params['path_length_m'], 
                          f"{params['wavelength_min']}-{params['wavelength_max']}", 
                          len(successful_molecules),
                          sum(params['molecule_concentrations'][mol] for mol in successful_molecules)]
                })
                info_df.to_excel(writer, sheet_name='분석조건', index=False)
               
                # 기여도 데이터
                df.to_excel(writer, sheet_name='분자별기여도', index=False)
               
                # 스펙트럼 데이터 (샘플링)
                sample_spectrum = spectrum_df.iloc[::10]
                sample_spectrum.to_excel(writer, sheet_name='스펙트럼데이터', index=False)
                
                # 분자 정보
                mol_info_data = []
                for mol in successful_molecules:
                    info = HITRAN_MOLECULES[mol]
                    mol_info_data.append({
                        '분자식': mol,
                        '한국명': info['name'],
                        '카테고리': info['category'],
                        'HITRAN ID': info['id'],
                        '농도(ppb)': params['molecule_concentrations'][mol]
                    })
                
                mol_info_df = pd.DataFrame(mol_info_data)
                mol_info_df.to_excel(writer, sheet_name='분자정보', index=False)
           
            excel_data = excel_buffer.getvalue()
           
            st.download_button(
                label="📊 분석 데이터 (Excel)",
                data=excel_data,
                file_name=f"crds_analysis_{len(successful_molecules)}molecules_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # 추가 분석 도구
        st.subheader("🔧 추가 분석 도구")
        
        analysis_col1, analysis_col2 = st.columns(2)
        
        with analysis_col1:
            # 특정 파장에서의 분자별 기여도
            st.write("**특정 파장에서의 분자별 흡광도**")
            target_wavelength = st.number_input(
                "분석 파장 (nm)",
                value=float((params['wavelength_min'] + params['wavelength_max']) / 2),
                min_value=float(params['wavelength_min']),
                max_value=float(params['wavelength_max']),
                step=0.1,
                key="target_wavelength"
            )
            
            # 가장 가까운 파장 인덱스 찾기
            wavelength_idx = np.argmin(np.abs(results['wavelength_nm'] - target_wavelength))
            actual_wavelength = results['wavelength_nm'][wavelength_idx]
            
            st.write(f"실제 분석 파장: {actual_wavelength:.2f} nm")
            
            wavelength_analysis = []
            for molecule, spectrum in results['individual_spectra'].items():
                abs_value = spectrum['absorbance'][wavelength_idx]
                wavelength_analysis.append({
                    '분자': molecule,
                    '한국명': HITRAN_MOLECULES[molecule]['name'],
                    '흡광도': f"{abs_value:.8f}",
                    '기여율': f"{(abs_value / results['combined_absorbance'][wavelength_idx] * 100):.2f}%" if results['combined_absorbance'][wavelength_idx] > 0 else "0%"
                })
            
            wavelength_df = pd.DataFrame(wavelength_analysis)
            wavelength_df = wavelength_df.sort_values('흡광도', ascending=False, key=lambda x: x.str.replace('f', '').astype(float))
            st.dataframe(wavelength_df, use_container_width=True)
        
        with analysis_col2:
            # 농도 민감도 분석
            st.write("**농도 변화 시뮬레이션**")
            
            if successful_molecules:
                sensitivity_molecule = st.selectbox(
                    "분석할 분자",
                    successful_molecules,
                    key="sensitivity_mol"
                )
                
                conc_factor = st.slider(
                    "농도 배수",
                    min_value=0.1,
                    max_value=10.0,
                    value=1.0,
                    step=0.1,
                    key="conc_factor"
                )
                
                if sensitivity_molecule:
                    original_conc = params['molecule_concentrations'][sensitivity_molecule]
                    new_conc = original_conc * conc_factor
                    
                    # 새로운 농도에서의 최대 흡광도 예측 (선형 근사)
                    original_spectrum = results['individual_spectra'][sensitivity_molecule]
                    predicted_max_abs = np.max(original_spectrum['absorbance']) * conc_factor
                    
                    st.write(f"**{sensitivity_molecule} ({HITRAN_MOLECULES[sensitivity_molecule]['name']})**")
                    st.write(f"원래 농도: {original_conc:.1f} ppb")
                    st.write(f"새로운 농도: {new_conc:.1f} ppb")
                    st.write(f"예상 최대 흡광도: {predicted_max_abs:.8f}")
                    st.write(f"변화율: {((conc_factor - 1) * 100):+.1f}%")

        # 스펙트럼 품질 평가
        st.subheader("📏 스펙트럼 품질 평가")
        
        quality_col1, quality_col2, quality_col3 = st.columns(3)
        
        with quality_col1:
            # 신호 대 잡음비 추정
            signal_strength = np.max(results['combined_absorbance'])
            noise_estimate = np.std(results['combined_absorbance'][:100])
            snr = signal_strength / noise_estimate if noise_estimate > 0 else float('inf')
            
            st.metric("추정 S/N 비", f"{snr:.1f}", help="신호 강도 / 잡음 추정값")
        
        with quality_col2:
            # 스펙트럼 해상도
            wavelength_resolution = np.mean(np.diff(results['wavelength_nm']))
            st.metric("파장 해상도", f"{wavelength_resolution:.4f} nm", help="평균 파장 간격")
        
        with quality_col3:
            # 검출 한계 추정 (3σ 기준)
            detection_limit = 3 * noise_estimate
            st.metric("검출 한계 (3σ)", f"{detection_limit:.8f}", help="3시그마 기준 검출 한계")

        # 권장사항
        st.subheader("💡 측정 권장사항")
        
        recommendations = []
        
        # 신호 강도 기반 권장사항
        if signal_strength < 0.001:
            recommendations.append("🔍 신호가 매우 약합니다. 경로 길이를 늘리거나 농도를 높이는 것을 고려하세요.")
        elif signal_strength > 2.0:
            recommendations.append("⚠️ 신호가 매우 강합니다. 포화를 피하기 위해 경로 길이를 줄이거나 농도를 낮추세요.")
        
        # 간섭 기반 권장사항
        if len(results['individual_spectra']) > 1:
            max_overlap = 0
            for i in range(len(results['wavelength_nm'])):
                overlapping_count = sum(1 for _, spectrum in results['individual_spectra'].items() 
                                      if spectrum['absorbance'][i] > 0.001)
                max_overlap = max(max_overlap, overlapping_count)
            
            if max_overlap > 3:
                recommendations.append("🚨 심각한 스펙트럼 간섭이 예상됩니다. 파장 범위를 조정하거나 분자를 분리 측정하세요.")
            elif max_overlap > 2:
                recommendations.append("⚡ 스펙트럼 간섭이 있습니다. 고해상도 측정이나 다변량 분석을 고려하세요.")
        
        # 파장 범위 기반 권장사항
        wavelength_range = params['wavelength_max'] - params['wavelength_min']
        if wavelength_range < 10:
            recommendations.append("📏 파장 범위가 좁습니다. 더 넓은 범위에서 측정하면 더 많은 정보를 얻을 수 있습니다.")
        elif wavelength_range > 1000:
            recommendations.append("📐 파장 범위가 매우 넓습니다. 관심 영역에 집중하면 더 높은 해상도를 얻을 수 있습니다.")
        
        # 농도 기반 권장사항
        total_concentration = sum(params['molecule_concentrations'][mol] for mol in successful_molecules)
        if total_concentration < 100:
            recommendations.append("💨 전체 농도가 낮습니다. CRDS의 높은 감도를 활용한 장경로 측정을 고려하세요.")
        elif total_concentration > 100000:
            recommendations.append("🌫️ 전체 농도가 높습니다. 단경로 측정이나 샘플 희석을 고려하세요.")
        
        if recommendations:
            for rec in recommendations:
                st.info(rec)
        else:
            st.success("✅ 현재 설정이 적절합니다!")

# 하단 정보
st.markdown("---")
col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("**개발:** HITRAN CRDS Simulator v4.0 Simple")
    st.markdown("**특징:** 단순화된 UI, 전체 분자 지원")

with col_info2:
    st.markdown("**데이터:** HITRAN Database")
    st.markdown(f"**지원 분자:** {len(HITRAN_MOLECULES)}개")

with col_info3:
    st.markdown("**카테고리:** 9개 분류")
    st.markdown("**고급 분석:** 품질 평가, 민감도 분석")