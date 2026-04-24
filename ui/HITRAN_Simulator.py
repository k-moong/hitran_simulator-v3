"""
HITRAN CRDS Simulator 메인 실행 파일 (Streamlit UI)
"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import sys
import os
import re
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.oa_icos_simulator import OAICOSSimulator
from core.line_shape_calculator import LineShapeCalculator
from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator
from constants import HITRAN_MOLECULES, WAVELENGTH_SHORTCUTS, DEFAULT_CONCENTRATIONS

# 새로운 기능 모듈들
from ui.components.data_upload import upload_experimental_data, overlay_experimental_data, export_results
from ui.components.line_info import create_interactive_spectrum_with_tooltips, show_line_details_panel, create_advanced_line_analysis
from ui.components.parameter_sweep import show_parameter_sweep_panel, run_parameter_sweep, visualize_sweep_results

# CIA 모듈
try:
    from ui.components.cia_component import (
        show_cia_settings, calculate_cia_contribution, show_cia_analysis, 
        combine_cia_with_line_absorption, show_cia_info, create_cia_demo
    )
    CIA_ENABLED = True
except ImportError as e:
    print(f"⚠️ CIA 모듈 로딩 실패: {e}")
    CIA_ENABLED = False

# --- 유틸 함수들 (최상단에 한 번만 정의) ---
def to_subscript(s):
    """숫자를 아래첨자로 변환"""
    sub_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    return s.translate(sub_map)

def to_superscript(s):
    """숫자를 위첨자로 변환"""
    sup_map = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
    return s.translate(sup_map)

def isotope_label(base, iso_code, mol_id=None, iso_num=None):
    """공식 HITRAN 동위원소 질량수 매핑 기반 분자식 변환"""
    from astroquery.hitran.core import HitranClass
    
    # mol_id, iso_num이 없으면 HITRAN_MOLECULES에서 추출
    if mol_id is None or iso_num is None:
        for k, v in HITRAN_MOLECULES.items():
            if v['base'] == base and str(v['iso_code']) == str(iso_code):
                mol_id = v['id']
                iso_num = v['iso']
                break
    
    # 공식 매핑에서 iso_name 추출
    if mol_id is not None and iso_num is not None:
        iso_info = HitranClass.ISO.get((mol_id, iso_num))
        if iso_info:
            iso_name = iso_info[1]  # 예: (12C)H4, (13C)H4, (16O)2 등
            # (12C)H4 → ¹²CH₄, (13C)H4 → ¹³CH₄ 등으로 변환
            def repl(m):
                mass, atom = m.groups()
                return to_superscript(mass) + atom
            # (12C) → ¹²C, (16O) → ¹⁶O 등 변환
            label = re.sub(r'\((\d+)([A-Z][a-z]?)\)', repl, iso_name)
            # 아래첨자 변환 (H4 → H₄)
            label = re.sub(r'([A-Z][a-z]?)(\d+)', lambda m: m.group(1)+to_subscript(m.group(2)), label)
            return label
    # 매핑 없으면 fallback
    return f"{base}({iso_code})"

def get_molecule_label(key):
    """분자 키로부터 한글명과 동위원소 표기를 포함한 라벨 생성"""
    info = HITRAN_MOLECULES[key]
    return f"{info['kor']} ({isotope_label(info['base'], info['iso_code'])})"

# --- UI 함수들 ---
def show_sidebar():
    st.sidebar.header("⚙️ 시뮬레이션 설정")
    spectrometer_mode = st.sidebar.radio(
        "분광기 종류", ["🌟 기본 HITRAN", "🔬 분광기"], index=0)
    mode = st.sidebar.radio("📊 분석 모드", ["🧪 혼합 스펙트럼", "📈 농도별 분석"], index=0)
    temp = st.sidebar.number_input("온도 (K)", value=296.15, min_value=200.0, max_value=400.0)
    wl_min = st.sidebar.number_input(
        "파장 최소 (nm)", 
        value=1390.0, 
        min_value=100.0, 
        max_value=1000000.0,
        help="HITRAN 데이터베이스는 100nm ~ 1,000,000nm (1mm) 범위를 지원합니다"
    )
    wl_max = st.sidebar.number_input(
        "파장 최대 (nm)", 
        value=1395.0, 
        min_value=100.0, 
        max_value=1000000.0,
        help="HITRAN 데이터베이스는 100nm ~ 1,000,000nm (1mm) 범위를 지원합니다"
    )

    # 해상도 설정 추가
    st.sidebar.subheader("🔬 해상도 설정")
    resolution_mode = st.sidebar.radio(
        "해상도 모드",
        ["⚡ 빠른 (3000 포인트)", "🎯 표준 (10000 포인트)", "🔬 고해상도 (30000 포인트)", "🚀 최대 해상도 (100000 포인트)"],
        index=1,
        help="해상도가 높을수록 정확하지만 계산 시간이 오래 걸립니다"
    )
    
    # 해상도별 포인트 수 매핑
    resolution_points = {
        "⚡ 빠른 (3000 포인트)": 3000,
        "🎯 표준 (10000 포인트)": 10000,
        "🔬 고해상도 (30000 포인트)": 30000,
        "🚀 최대 해상도 (100000 포인트)": 100000
    }
    
    num_points = resolution_points[resolution_mode]
    
    # 해상도 정보 표시
    wavelength_range = wl_max - wl_min
    resolution_nm = wavelength_range / num_points
    resolution_cm = resolution_nm * 1e-7  # nm to cm
    
    st.sidebar.info(f"""
    **해상도 정보:**
    - 포인트 수: {num_points:,}개
    - 파장 해상도: {resolution_nm:.6f} nm
    - 주파수 해상도: {resolution_cm:.6f} cm⁻¹
    """)

    # Matrix Gas 설정
    st.sidebar.subheader("🌬️ Matrix Gas 설정")
    matrix_gases = {
        "Air": {"name": "공기 (Air)", "molar_mass": 28.97, "broadening_factor": 1.0, "humidity": "자연습도", "composition": "N2 + O2 + H2O + trace gases"},
        "CDA": {"name": "청정건조공기 (Clean Dry Air)", "molar_mass": 28.97, "broadening_factor": 0.96, "humidity": "< 1 ppm H2O", "composition": "N2 (78%) + O2 (21%) only"},
        "N2": {"name": "질소 (N₂)", "molar_mass": 28.01, "broadening_factor": 0.95, "humidity": "무수", "composition": "N2 (99.999%)"},
        "O2": {"name": "산소 (O₂)", "molar_mass": 32.00, "broadening_factor": 1.1, "humidity": "무수", "composition": "O2 (99.999%)"},
        "He": {"name": "헬륨 (He)", "molar_mass": 4.00, "broadening_factor": 0.3, "humidity": "무수", "composition": "He (99.999%)"},
        "H2": {"name": "수소 (H₂)", "molar_mass": 2.02, "broadening_factor": 0.4, "humidity": "무수", "composition": "H2 (99.999%)"},
        "Ar": {"name": "아르곤 (Ar)", "molar_mass": 39.95, "broadening_factor": 0.8, "humidity": "무수", "composition": "Ar (99.999%)"},
        "CO2": {"name": "이산화탄소 (CO₂)", "molar_mass": 44.01, "broadening_factor": 1.2, "humidity": "무수", "composition": "CO2 (99.999%)"},
        "Zero_Air": {"name": "제로에어 (Zero Air)", "molar_mass": 28.97, "broadening_factor": 0.98, "humidity": "< 0.1 ppm H2O", "composition": "N2 + O2 + trace removal"}
    }
    
    matrix_gas = st.sidebar.selectbox(
        "Matrix Gas 종류",
        list(matrix_gases.keys()),
        index=1,  # CDA가 두 번째이므로 기본값으로 설정
        format_func=lambda x: matrix_gases[x]["name"],
        help="Matrix gas는 압력 확산과 선 이동에 영향을 줍니다"
    )
    
    # 압력 설정 (총 압력)
    col1, col2 = st.sidebar.columns(2)
    with col1:
        total_pressure = st.number_input("총 압력 (torr)", value=760.0, min_value=1.0, max_value=15000.0)
    with col2:
        # Matrix gas 정보 표시
        matrix_info = matrix_gases[matrix_gas]
        st.info(f"""
        **선택된 Matrix Gas:**
        - {matrix_info['name']}
        - 확산 계수: {matrix_info['broadening_factor']}x
        - 수분: {matrix_info['humidity']}
        """)
    
    # 고급 Matrix Gas 설정
    with st.sidebar.expander("🔬 고급 Matrix Gas 설정"):
        enable_pressure_broadening = st.checkbox("압력 확산 효과 적용", value=True)
        enable_line_shifting = st.checkbox("선 이동 효과 적용", value=False, help="고압에서 중요")
        
        if enable_pressure_broadening:
            broadening_enhancement = st.slider(
                "확산 강화 계수", 
                min_value=0.5, 
                max_value=2.0, 
                value=1.0, 
                step=0.1,
                help="1.0 = 표준, >1.0 = 더 넓은 선폭"
            )
        else:
            broadening_enhancement = 1.0
            
        if enable_line_shifting:
            line_shift_coeff = st.number_input(
                "선 이동 계수 (cm⁻¹/atm)",
                min_value=-0.01,
                max_value=0.01,
                value=0.0,
                format="%.4f",
                help="양수: 고주파 이동, 음수: 저주파 이동"
            )
        else:
            line_shift_coeff = 0.0
    
    # Matrix gas 정보를 다른 함수에서 사용할 수 있도록 저장
    matrix_gas_params = {
        'gas_type': matrix_gas,
        'total_pressure_torr': total_pressure,
        'broadening_factor': matrix_info['broadening_factor'],
        'broadening_enhancement': broadening_enhancement,
        'enable_pressure_broadening': enable_pressure_broadening,
        'enable_line_shifting': enable_line_shifting,
        'line_shift_coeff': line_shift_coeff,
        'molar_mass': matrix_info['molar_mass'],
        'humidity': matrix_info['humidity'],
        'composition': matrix_info['composition']
    }

    # OA-ICOS 파라미터 (OA-ICOS 모드 선택시에만 표시)
    oa_icos_params = None
    path = 1000.0  # 기본값
    if spectrometer_mode == "🔬 분광기":
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔬 분광기 파라미터")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            mirror_reflectivity = st.number_input(
                "미러 반사율", min_value=0.99000, max_value=0.99999, value=0.99990, step=0.00001, format="%.5f")
        with col2:
            cavity_length = st.number_input(
                "캐비티 길이 (cm)", min_value=1.0, max_value=200.0, value=50.0)
        mirror_loss = st.sidebar.number_input(
            "미러 손실율", min_value=0.0, max_value=0.001, value=0.00001, format="%.6f")
        detector_noise = st.sidebar.number_input(
            "검출기 노이즈 레벨", min_value=0.0, max_value=0.01, value=0.00075, format="%.5f")
        baseline_drift = st.sidebar.number_input(
            "베이스라인 드리프트", min_value=0.0, max_value=0.001, value=0.0001, format="%.6f")
        line_shape_options = {
            "Voigt (추천)": "도플러 + 압력 확산 조합 (일반적 조건)",
            "Gaussian": "도플러 확산 지배적 (저압 < 0.1 atm)",
            "Lorentzian": "압력 확산 지배적 (고압 > 10 atm)",
            "Hartmann-Tran": "모든 물리적 효과 포함 (최고 정확도)"
        }
        line_shape = st.sidebar.selectbox(
            "Line Shape 모델",
            options=list(line_shape_options.keys()),
            index=0,
            help="스펙트럼 선형 모델을 선택하세요"
        )
        st.sidebar.caption(f"📖 {line_shape_options[line_shape]}")
        oa_icos_params = {
            'mirror_reflectivity': mirror_reflectivity,
            'cavity_length': cavity_length,
            'mirror_loss': mirror_loss,
            'detector_noise': detector_noise,
            'baseline_drift': baseline_drift,
            'line_shape': line_shape.split()[0]  # 실제 모델명만
        }
        path = st.sidebar.number_input("광경로 (m)", min_value=10.0, max_value=2000.0, value=1000.0)
    else:
        # 기본 HITRAN 모드
        path = st.sidebar.number_input("경로 길이 (m)", value=1000.0, min_value=1.0, max_value=50000.0)

    # 분자 선택 (동위원소 포함, 그룹핑)
    all_molecules = list(HITRAN_MOLECULES.keys())
    
    # base별 그룹핑
    grouped = defaultdict(list)
    for k in all_molecules:
        grouped[HITRAN_MOLECULES[k]['base']].append(k)
    group_labels = {b: HITRAN_MOLECULES[ks[0]]['kor']+f" ({b})" for b, ks in grouped.items()}

    # 1단계: 여러 분자(base) 멀티셀렉트
    base_molecules = sorted(set([HITRAN_MOLECULES[k]['base'] for k in all_molecules]), key=lambda b: HITRAN_MOLECULES[[k for k in all_molecules if HITRAN_MOLECULES[k]['base']==b][0]]['kor'])
    base_kor_map = {b: HITRAN_MOLECULES[[k for k in all_molecules if HITRAN_MOLECULES[k]['base']==b][0]]['kor'] for b in base_molecules}

    if mode == "🧪 혼합 스펙트럼":
        selected_bases = st.sidebar.multiselect(
            "분자 선택 (최대 10개까지 선택 가능)", 
            base_molecules, 
            default=["H2O", "CO2", "CH4"], 
            format_func=lambda b: f"{base_kor_map[b]} ({b})",
            max_selections=10,
            help="여러 분자를 동시에 선택할 수 있습니다. 성능을 위해 최대 10개까지 선택 가능합니다."
        )
        # 각 분자별 농도 입력(ppb)
        base_concentrations = {}
        for base in selected_bases:
            default_ppb = DEFAULT_CONCENTRATIONS.get(base, 10.0)
            base_concentrations[base] = st.sidebar.number_input(f"농도 (ppb) - {base_kor_map[base]}", min_value=0.0, value=float(default_ppb), step=1.0, format="%.1f")
    else:
        # 농도별 분석 모드에서는 한 분자만 선택
        selected_bases = st.sidebar.selectbox("분자 선택", base_molecules, index=0, format_func=lambda b: f"{base_kor_map[b]} ({b})")
        base_concentrations = None

    # 2단계: 각 분자별 동위원소 멀티셀렉트
    selected_isos = []
    iso_to_base = {}
    if mode == "🧪 혼합 스펙트럼":
        if selected_bases:  # None 체크 추가
            for base in selected_bases:
                iso_keys = [k for k in all_molecules if HITRAN_MOLECULES[k]['base'] == base]
                major_iso_key = [k for k in iso_keys if HITRAN_MOLECULES[k]['iso'] == 1]
                
                def iso_label(key):
                    info = HITRAN_MOLECULES[key]
                    label = isotope_label(info['base'], info['iso_code'], info['id'], info['iso'])
                    if key in major_iso_key:
                        return f"★ {label} [대표]"
                    return label
                
                iso_keys_sorted = major_iso_key + [k for k in iso_keys if k not in major_iso_key]
                selected = st.sidebar.multiselect(
                    f"동위원소 선택 ({base_kor_map[base]})",
                    iso_keys_sorted,
                    default=major_iso_key,
                    format_func=iso_label,
                    max_selections=5,
                    help="여러 동위원소를 동시에 선택할 수 있습니다. 대표 동위원소는 별표와 [대표]로 강조됩니다. 성능을 위해 최대 5개까지 선택 가능합니다."
                )
                for iso in selected:
                    selected_isos.append(iso)
                    iso_to_base[iso] = base
    else:
        # 농도별 분석 모드: 한 분자만, 동위원소도 하나만 선택
        iso_keys = [k for k in all_molecules if HITRAN_MOLECULES[k]['base'] == selected_bases]
        major_iso_key = [k for k in iso_keys if HITRAN_MOLECULES[k]['iso'] == 1]
        
        def iso_label(key):
            info = HITRAN_MOLECULES[key]
            label = isotope_label(info['base'], info['iso_code'], info['id'], info['iso'])
            if key in major_iso_key:
                return f"★ {label} [대표]"
            return label
        
        iso_keys_sorted = major_iso_key + [k for k in iso_keys if k not in major_iso_key]
        selected = st.sidebar.selectbox(
            f"동위원소 선택 ({base_kor_map[selected_bases]})",
            iso_keys_sorted,
            index=0,
            format_func=iso_label,
            help="동위원소를 선택하세요. 대표 동위원소는 별표와 [대표]로 강조됩니다."
        )
        selected_isos.append(selected)
        iso_to_base[selected] = selected_bases
    
    # molecules, molecule 변수에 맞게 할당
    if mode == "🧪 혼합 스펙트럼":
        molecules = selected_isos
        molecule = None
        c_min = c_max = c_steps = None
        # 농도 매핑 전달 - base_concentrations가 None이 아닐 때만 처리
        molecule_concentrations = {}
        if base_concentrations and selected_isos:
            molecule_concentrations = {iso: base_concentrations[iso_to_base[iso]] for iso in selected_isos}
    else:
        molecule = selected_isos[0] if selected_isos else None
        c_min = st.sidebar.number_input("농도 최소 (ppb)", value=10.0, min_value=0.1)
        c_max = st.sidebar.number_input("농도 최대 (ppb)", value=5000.0, min_value=0.1)
        c_steps = st.sidebar.slider("단계 수", 3, 20, 10)
        molecules = None
        molecule_concentrations = None
    
    # CIA 설정 추가
    if CIA_ENABLED:
        cia_config = show_cia_settings()
    else:
        cia_config = None
    
    return spectrometer_mode, mode, temp, wl_min, wl_max, molecules, molecule, c_min, c_max, c_steps, oa_icos_params, path, matrix_gas_params, molecule_concentrations, num_points, cia_config

def run_simulation(spectrometer_mode, mode, temp, wl_min, wl_max, molecules, molecule=None, c_min=None, c_max=None, c_steps=None, oa_icos_params=None, path=1000.0, matrix_gas_params=None, molecule_concentrations=None, num_points=10000, cia_config=None):
    """시뮬레이션 실행 함수 (혼합/농도별 분석, OA-ICOS/기본 모드, Matrix Gas 효과 지원)"""
    api = HitranAPI()
    calc = SpectrumCalculator()
    oa_icos_sim = OAICOSSimulator() if spectrometer_mode == "🔬 분광기" else None
    results = {}
    freq_min = 1e7 / wl_max
    freq_max = 1e7 / wl_min
    freq_grid = np.linspace(freq_min, freq_max, num_points)
    wl_grid = 1e7 / freq_grid
    
    # Matrix Gas 압력 적용
    pressure_atm = matrix_gas_params['total_pressure_torr'] / 760.0 if matrix_gas_params else 1.0
    
    if mode == "🧪 혼합 스펙트럼" and molecules:
        # 성능 경고 메시지
        if len(molecules) > 5:
            st.warning(f"⚠️ **성능 주의**: {len(molecules)}개의 분자를 선택했습니다. 계산 시간이 오래 걸릴 수 있습니다.")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        combined_abs = np.zeros_like(freq_grid)
        for mol in molecules:
            molecule_label = get_molecule_label(mol)
            data = api.download_molecule_data(mol, wl_min, wl_max)
            if data is None or (hasattr(data, 'empty') and data.empty) or (hasattr(data, '__len__') and len(data) == 0):
                st.warning(f"⚠️ {molecule_label} : 해당 파장 범위에 스펙트럼 데이터가 없습니다.")
                continue
            
            # 농도 처리 - molecule_concentrations가 dict인 경우
            if isinstance(molecule_concentrations, dict) and mol in molecule_concentrations:
                concentration = molecule_concentrations[mol] / 1e9  # ppb to mole fraction
            else:
                concentration = 1000e-9  # 기본값 1000 ppb
            
            spec = calc.calculate_absorption_spectrum(
                data, freq_grid, temp, pressure_atm, concentration, path, mol,
                progress_bar=progress_bar, status_text=status_text, molecule_label=molecule_label
            )
            spec['wavelength'] = wl_grid
            results[mol] = spec
            combined_abs += spec['absorption_coeff']
                
            # OA-ICOS 시뮬레이션 (모드가 선택된 경우)
            if oa_icos_sim and oa_icos_params:
                # oa_icos_params에서 필요한 값들을 개별적으로 추출
                mirror_reflectivity = oa_icos_params.get('mirror_reflectivity', 0.99990)
                cavity_length = oa_icos_params.get('cavity_length', 50.0)
                mirror_loss = oa_icos_params.get('mirror_loss', 0.00001)
                detector_noise = oa_icos_params.get('detector_noise', 0.00075)
                baseline_drift = oa_icos_params.get('baseline_drift', 0.0001)
                line_shape = oa_icos_params.get('line_shape', 'Voigt')
                
                oa_icos_result = oa_icos_sim.simulate_oa_icos_spectrum(
                    spec['wavelength'], spec['absorption_coeff'],
                    mirror_reflectivity, cavity_length, mirror_loss, detector_noise, baseline_drift, line_shape
                )
                results[f"{mol}_oa_icos"] = oa_icos_result
        progress_bar.empty()
        status_text.empty()
        
        # 기본 혼합 스펙트럼
        results['combined'] = {
            'transmittance': np.exp(-combined_abs * path),
            'absorbance': -np.log10(np.exp(-combined_abs * path))
        }
        
        # OA-ICOS 혼합 스펙트럼 (모드가 선택된 경우)
        if oa_icos_sim and oa_icos_params:
            combined_spectrum = {
                'absorption_coeff': combined_abs,
                'wavelength': wl_grid
            }
            # oa_icos_params에서 필요한 값들을 개별적으로 추출
            mirror_reflectivity = oa_icos_params.get('mirror_reflectivity', 0.99990)
            cavity_length = oa_icos_params.get('cavity_length', 50.0)
            mirror_loss = oa_icos_params.get('mirror_loss', 0.00001)
            detector_noise = oa_icos_params.get('detector_noise', 0.00075)
            baseline_drift = oa_icos_params.get('baseline_drift', 0.0001)
            line_shape = oa_icos_params.get('line_shape', 'Voigt')
            
            oa_icos_combined = oa_icos_sim.simulate_oa_icos_spectrum(
                wl_grid, combined_abs,
                mirror_reflectivity, cavity_length, mirror_loss, detector_noise, baseline_drift, line_shape
            )
            results['combined_oa_icos'] = oa_icos_combined
    elif mode == "📈 농도별 분석" and molecule and c_min is not None and c_max is not None and c_steps is not None:
        progress_bar = st.progress(0)
        status_text = st.empty()
        concs_array = np.linspace(c_min, c_max, c_steps)
        molecule_label = get_molecule_label(molecule)
        data = api.download_molecule_data(molecule, wl_min, wl_max)
        if data is None or (hasattr(data, 'empty') and data.empty) or (hasattr(data, '__len__') and len(data) == 0):
            st.warning(f"⚠️ {molecule_label} : 해당 파장 범위에 스펙트럼 데이터가 없습니다.")
        else:
            max_abs = []
            oa_icos_max_abs = []
            for idx, c in enumerate(concs_array):
                spec = calc.calculate_absorption_spectrum(
                    data, freq_grid, temp, pressure_atm, c/1e9, path, molecule,
                    progress_bar=progress_bar, status_text=status_text, molecule_label=molecule_label
                )
                spec['wavelength'] = wl_grid
                results[c] = spec
                if isinstance(spec, dict) and 'absorbance' in spec:
                    max_abs.append(np.max(spec['absorbance']))
                else:
                    max_abs.append(0.0)  # 기본값
                
                # OA-ICOS 시뮬레이션 (모드가 선택된 경우)
                if oa_icos_sim and oa_icos_params:
                    # oa_icos_params에서 필요한 값들을 개별적으로 추출
                    mirror_reflectivity = oa_icos_params.get('mirror_reflectivity', 0.99990)
                    cavity_length = oa_icos_params.get('cavity_length', 50.0)
                    mirror_loss = oa_icos_params.get('mirror_loss', 0.00001)
                    detector_noise = oa_icos_params.get('detector_noise', 0.00075)
                    baseline_drift = oa_icos_params.get('baseline_drift', 0.0001)
                    line_shape = oa_icos_params.get('line_shape', 'Voigt')
                    
                    oa_icos_result = oa_icos_sim.simulate_oa_icos_spectrum(
                        spec['wavelength'], spec['absorption_coeff'],
                        mirror_reflectivity, cavity_length, mirror_loss, detector_noise, baseline_drift, line_shape
                    )
                    results[f"{c}_oa_icos"] = oa_icos_result
                    oa_icos_max_abs.append(np.max(oa_icos_result['oa_icos_signal']))
            
            # 기본 선형성 분석
            if len(max_abs) > 1:
                slope, intercept, r_value, _, _ = stats.linregress(concs_array, max_abs)
                results['analysis'] = {
                    'concentrations': concs_array,
                    'max_absorbances': max_abs,
                    'r_squared': float(r_value ** 2),
                    'slope': float(slope),
                    'intercept': float(intercept)
                }
            
            # OA-ICOS 선형성 분석 (모드가 선택된 경우)
            if oa_icos_sim and oa_icos_params and len(oa_icos_max_abs) > 1:
                slope_oa, intercept_oa, r_value_oa, _, _ = stats.linregress(concs_array, oa_icos_max_abs)
                results['oa_icos_analysis'] = {
                    'concentrations': concs_array,
                    'max_absorbances': oa_icos_max_abs,
                    'r_squared': float(r_value_oa ** 2),
                    'slope': float(slope_oa),
                    'intercept': float(intercept_oa)
                }
        progress_bar.empty()
        status_text.empty()
    
    # CIA (Collision-Induced Absorption) 계산 추가
    if CIA_ENABLED and cia_config and cia_config['enabled']:
        try:
            # 농도 딕셔너리 구성
            concentrations_dict = {}
            if isinstance(molecule_concentrations, dict):
                for mol, conc in molecule_concentrations.items():
                    # 분자명을 CIA에서 사용하는 형식으로 변환
                    if mol == 'H2O':
                        concentrations_dict['H2O'] = conc
                    elif mol == 'CO2':
                        concentrations_dict['CO2'] = conc
                    elif mol == 'CH4':
                        concentrations_dict['CH4'] = conc
                    elif mol == 'N2O':
                        concentrations_dict['N2O'] = conc
                    elif mol == 'CO':
                        concentrations_dict['CO'] = conc
                    elif mol == 'O2':
                        concentrations_dict['O2'] = conc
                    elif mol == 'NO':
                        concentrations_dict['NO'] = conc
            
            # 대기 구성 요소 기본값 추가 (CIA 계산에 필요)
            concentrations_dict.setdefault('N2', 780000000)  # 78% in ppb
            concentrations_dict.setdefault('O2', 210000000)  # 21% in ppb
            concentrations_dict.setdefault('H2', 500)  # 기본 H2 농도 in ppb
            concentrations_dict.setdefault('He', 5240)  # 기본 He 농도 in ppb
            
            cia_results = calculate_cia_contribution(
                cia_config, wl_grid, temp, concentrations_dict, pressure_atm, path
            )
            
            if cia_results:
                results['cia'] = cia_results
                st.success(f"✅ CIA 계산 완료: {len(cia_results)}개 분자 쌍")
                
        except Exception as e:
            st.warning(f"⚠️ CIA 계산 중 오류: {e}")
    
    return results, wl_grid

def show_results(results, wl_grid, mode, molecule=None, spectrometer_mode=None, oa_icos_params=None, matrix_gas_params=None, molecule_concentrations=None):
    """결과 시각화 함수 (혼합/농도별 분석, OA-ICOS 성능 지표, Matrix Gas 정보 지원)"""
    
    # OA-ICOS 모드일 때 상단에 성능 지표 표시
    if spectrometer_mode == "🔬 분광기" and oa_icos_params:
        oa_icos_sim = OAICOSSimulator()
        params = oa_icos_params
        effective_path = oa_icos_sim.calculate_effective_path_length(
            params['mirror_reflectivity'], params['cavity_length'], params['mirror_loss']
        )
        enhancement_factor = effective_path / params['cavity_length']
        
        st.subheader("🔬 OA-ICOS 성능 지표 + Line Shape")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("유효 광경로", f"{effective_path:.1f} cm")
        with col2:
            st.metric("향상 인수", f"{enhancement_factor:.0f}x")
        with col3:
            st.metric("미러 반사율", f"{params['mirror_reflectivity']:.5f}")
        with col4:
            st.metric("레이저 선폭", f"{params['laser_linewidth']:.6f} cm⁻¹")
        with col5:
            line_shape_display = params.get('line_shape', 'Voigt (추천)')
            st.metric("Line Shape", line_shape_display.split()[0])
    
    # Matrix Gas 정보 표시
    if matrix_gas_params:
        st.subheader("🌬️ Matrix Gas 조건")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Matrix Gas", matrix_gas_params['gas_type'])
        with col2:
            st.metric("총 압력", f"{matrix_gas_params['total_pressure_torr']:.1f} torr")
        with col3:
            broadening_status = "ON" if matrix_gas_params['enable_pressure_broadening'] else "OFF"
            st.metric("압력 확산", broadening_status)
        with col4:
            line_shift_status = "ON" if matrix_gas_params['enable_line_shifting'] else "OFF"
            st.metric("선 이동", line_shift_status)
    
    if mode == "🧪 혼합 스펙트럼":
        st.subheader("📊 혼합 스펙트럼 결과")
        
        # Line Shape 정보 표시 (OA-ICOS 모드인 경우)
        if spectrometer_mode == "🔬 분광기" and oa_icos_params:
            line_shape_used = oa_icos_params.get('line_shape', 'Voigt (추천)')
            st.info(f"🌊 **적용된 Line Shape**: {line_shape_used}")
        
        # OA-ICOS 모드인 경우 2단 그래프, 기본 모드인 경우 1단 그래프
        is_oa_icos = spectrometer_mode == "🔬 분광기"
        rows = 2 if is_oa_icos else 1
        
        subplot_titles = ['개별 분자 스펙트럼']
        if is_oa_icos:
            subplot_titles.append('기본 HITRAN vs OA-ICOS 비교')
        
        fig = make_subplots(rows=rows, cols=1, 
                           subplot_titles=subplot_titles,
                           vertical_spacing=0.15)
        
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        # 개별 분자 스펙트럼
        for i, (mol, spec) in enumerate(results.items()):
            if mol in ['combined', 'combined_oa_icos', 'cia'] or mol.endswith('_oa_icos'):
                continue
            
            # 안전한 키 접근 - absorbance 키가 있는지 확인
            if isinstance(spec, dict) and 'absorbance' in spec:
                fig.add_trace(
                    go.Scatter(x=wl_grid, y=spec['absorbance'],
                              name=get_molecule_label(mol),
                              line=dict(color=colors[i % len(colors)])),
                    row=1, col=1
                )
            else:
                print(f"⚠️ {mol}: 'absorbance' 키가 없거나 잘못된 데이터 구조입니다.")
                if isinstance(spec, dict):
                    print(f"   사용 가능한 키들: {list(spec.keys())}")
                else:
                    print(f"   데이터 타입: {type(spec)}")
        
        # OA-ICOS 비교 (모드가 선택된 경우)
        if is_oa_icos and 'combined_oa_icos' in results:
            # 기본 vs OA-ICOS 혼합 스펙트럼 비교
            if 'combined' in results and isinstance(results['combined'], dict) and 'absorbance' in results['combined']:
                fig.add_trace(
                    go.Scatter(x=wl_grid, y=results['combined']['absorbance'],
                              name='기본 HITRAN (혼합)', 
                              line=dict(color='darkblue', width=3, dash='solid')),
                    row=2, col=1
                )
            fig.add_trace(
                go.Scatter(x=wl_grid, y=results['combined_oa_icos']['absorbance'],
                          name=f'OA-ICOS 향상 (혼합, {line_shape_used})', 
                          line=dict(color='darkred', width=3, dash='solid')),
                row=2, col=1
            )
        
        # 축 레이블 설정
        fig.update_xaxes(title_text="파장 (nm)", row=rows, col=1)
        fig.update_yaxes(title_text="흡광도", row=1, col=1)
        if is_oa_icos:
            fig.update_yaxes(title_text="흡광도 (혼합 스펙트럼)", row=2, col=1)
        
        # 레이아웃 설정
        fig.update_layout(
            height=600 if is_oa_icos else 400, 
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    elif mode == "📈 농도별 분석" and molecule:
        st.subheader(f"📈 {get_molecule_label(molecule)} 농도별 분석 결과")
        
        # Line Shape 정보 표시 (OA-ICOS 모드인 경우)
        is_oa_icos = spectrometer_mode == "🔬 분광기"
        if is_oa_icos and oa_icos_params:
            line_shape_used = oa_icos_params.get('line_shape', 'Voigt (추천)')
            st.info(f"🌊 **적용된 Line Shape**: {line_shape_used}")
        
        if is_oa_icos:
            # OA-ICOS 모드: 2x2 레이아웃
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("기본 HITRAN")
                # 농도별 스펙트럼 (기본)
                fig1 = go.Figure()
                colors = ['darkblue', 'blue', 'lightblue', 'green', 'yellow', 'orange', 'red', 'darkred']
                
                for i, (c, spec) in enumerate(results.items()):
                    if c in ['analysis', 'oa_icos_analysis', 'cia'] or c.endswith('_oa_icos'):
                        continue
                    
                    # 안전한 키 접근
                    if isinstance(spec, dict) and 'absorbance' in spec:
                        color_idx = int(i * (len(colors)-1) / (len([k for k in results.keys() if not k.endswith('_oa_icos') and k not in ['analysis', 'oa_icos_analysis', 'cia']])-1))
                        fig1.add_trace(
                            go.Scatter(x=wl_grid, y=spec['absorbance'],
                                      name=f'{c:.1f} ppb',
                                      line=dict(color=colors[color_idx]))
                        )
                
                fig1.update_layout(title="농도별 스펙트럼 (기본)", xaxis_title="파장 (nm)", 
                                  yaxis_title="흡광도", height=400)
                st.plotly_chart(fig1, use_container_width=True)
                
                # 선형성 분석 (기본)
                if 'analysis' in results:
                    fig2 = go.Figure()
                    analysis = results['analysis']
                    fig2.add_trace(
                        go.Scatter(x=analysis['concentrations'], y=analysis['max_absorbances'],
                                  mode='markers', name='데이터', marker=dict(size=10, color='blue'))
                    )
                    
                    x_fit = np.linspace(analysis['concentrations'][0], analysis['concentrations'][-1], 100)
                    y_fit = analysis['slope'] * x_fit + analysis['intercept']
                    fig2.add_trace(
                        go.Scatter(x=x_fit, y=y_fit, mode='lines',
                                  name=f"R² = {analysis['r_squared']:.5f}",
                                  line=dict(color='blue', dash='dash'))
                    )
                    
                    fig2.update_layout(title="선형성 (기본)", xaxis_title="농도 (ppb)",
                                      yaxis_title="최대 흡광도", height=400)
                    st.plotly_chart(fig2, use_container_width=True)
            
            with col2:
                st.subheader(f"OA-ICOS 향상 ({line_shape_used})")
                # 농도별 스펙트럼 (OA-ICOS)
                oa_icos_results = {k: v for k, v in results.items() if k.endswith('_oa_icos')}
                if oa_icos_results:
                    fig3 = go.Figure()
                    
                    for i, (c, oa_spec) in enumerate(oa_icos_results.items()):
                        # 안전한 키 접근
                        if isinstance(oa_spec, dict) and 'absorbance' in oa_spec:
                            color_idx = int(i * (len(colors)-1) / (len(oa_icos_results)-1))
                            fig3.add_trace(
                                go.Scatter(x=wl_grid, y=oa_spec['absorbance'],
                                          name=f'{c.replace("_oa_icos", "")} ppb',
                                      line=dict(color=colors[color_idx]))
                        )
                    
                    fig3.update_layout(title=f"농도별 스펙트럼 (OA-ICOS + {line_shape_used})", 
                                      xaxis_title="파장 (nm)", 
                                      yaxis_title="흡광도", height=400)
                    st.plotly_chart(fig3, use_container_width=True)
                
                # 선형성 분석 (OA-ICOS)
                if 'oa_icos_analysis' in results:
                    fig4 = go.Figure()
                    oa_analysis = results['oa_icos_analysis']
                    fig4.add_trace(
                        go.Scatter(x=oa_analysis['concentrations'], y=oa_analysis['max_absorbances'],
                                  mode='markers', name='데이터', marker=dict(size=10, color='red'))
                    )
                    
                    x_fit_oa = np.linspace(oa_analysis['concentrations'][0], oa_analysis['concentrations'][-1], 100)
                    y_fit_oa = oa_analysis['slope'] * x_fit_oa + oa_analysis['intercept']
                    fig4.add_trace(
                        go.Scatter(x=x_fit_oa, y=y_fit_oa, mode='lines',
                                  name=f"R² = {oa_analysis['r_squared']:.5f}",
                                  line=dict(color='red', dash='dash'))
                    )
                    
                    fig4.update_layout(title=f"선형성 (OA-ICOS + {line_shape_used})", 
                                      xaxis_title="농도 (ppb)",
                                      yaxis_title="최대 흡광도", height=400)
                    st.plotly_chart(fig4, use_container_width=True)
        
        else:
            # 기본 모드: 기존과 동일한 2열 레이아웃
            col1, col2 = st.columns(2)
            
            with col1:
                # 농도별 스펙트럼
                fig1 = go.Figure()
                colors = ['darkblue', 'blue', 'lightblue', 'green', 'yellow', 'orange', 'red', 'darkred']
                
                for i, (c, spec) in enumerate(results.items()):
                    if c in ['analysis', 'cia']:
                        continue
                    
                    # 안전한 키 접근
                    if isinstance(spec, dict) and 'absorbance' in spec:
                        color_idx = int(i * (len(colors)-1) / (len(results)-2))
                        fig1.add_trace(
                            go.Scatter(x=wl_grid, y=spec['absorbance'],
                                      name=f'{c:.1f} ppb',
                                      line=dict(color=colors[color_idx]))
                        )
                
                fig1.update_layout(title="농도별 스펙트럼", xaxis_title="파장 (nm)", 
                                  yaxis_title="흡광도", height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # 선형성 분석
                if 'analysis' in results:
                    fig2 = go.Figure()
                    
                    analysis = results['analysis']
                    fig2.add_trace(
                        go.Scatter(x=analysis['concentrations'], y=analysis['max_absorbances'],
                                  mode='markers', name='데이터', marker=dict(size=10, color='red'))
                    )
                    
                    # 회귀선
                    x_fit = np.linspace(analysis['concentrations'][0], analysis['concentrations'][-1], 100)
                    y_fit = analysis['slope'] * x_fit + analysis['intercept']
                    fig2.add_trace(
                        go.Scatter(x=x_fit, y=y_fit, mode='lines',
                                  name=f"R² = {analysis['r_squared']:.5f}",
                                  line=dict(color='blue', dash='dash'))
                    )
                    
                    fig2.update_layout(title="농도-흡광도 선형성", xaxis_title="농도 (ppb)",
                                      yaxis_title="최대 흡광도", height=400)
                    st.plotly_chart(fig2, use_container_width=True)
        
        # 분석 결과 비교 (Line Shape 효과 포함)
        st.subheader("📊 선형성 분석 결과 + Line Shape 효과")
        
        if is_oa_icos and 'oa_icos_analysis' in results:
            # OA-ICOS vs 기본 비교
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🌟 기본 HITRAN**")
                analysis = results['analysis']
                subcol1, subcol2, subcol3, subcol4 = st.columns(4)
                with subcol1:
                    st.metric("R²", f"{analysis['r_squared']:.6f}")
                with subcol2:
                    st.metric("기울기", f"{analysis['slope']:.2e}")
                with subcol3:
                    st.metric("절편", f"{analysis['intercept']:.2e}")
                with subcol4:
                    detection_limit = 3 * 0.001 / analysis['slope'] if analysis['slope'] > 0 else 0
                    st.metric("검출한계 (3σ)", f"{detection_limit:.1f} ppb")
            
            with col2:
                st.markdown(f"**🔬 OA-ICOS 향상 ({line_shape_used})**")
                oa_analysis = results['oa_icos_analysis']
                subcol1, subcol2, subcol3, subcol4 = st.columns(4)
                with subcol1:
                    st.metric("R²", f"{oa_analysis['r_squared']:.6f}")
                with subcol2:
                    st.metric("기울기", f"{oa_analysis['slope']:.2e}")
                with subcol3:
                    st.metric("절편", f"{oa_analysis['intercept']:.2e}")
                with subcol4:
                    oa_detection_limit = 3 * 0.001 / oa_analysis['slope'] if oa_analysis['slope'] > 0 else 0
                    st.metric("검출한계 (3σ)", f"{oa_detection_limit:.1f} ppb")
            
            # 향상 효과 요약 (Line Shape 정보 포함)
            if analysis['slope'] > 0 and oa_analysis['slope'] > 0:
                sensitivity_improvement = oa_analysis['slope'] / analysis['slope']
                detection_improvement = detection_limit / oa_detection_limit if oa_detection_limit > 0 else float('inf')
                
                st.markdown("---")
                st.subheader(f"🚀 OA-ICOS + {line_shape_used} 향상 효과")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("감도 향상", f"{sensitivity_improvement:.1f}배")
                with col2:
                    st.metric("검출한계 개선", f"{detection_improvement:.1f}배")
                with col3:
                    if oa_icos_params and 'mirror_reflectivity' in oa_icos_params:
                        enhancement_factor = 1 / (1 - oa_icos_params['mirror_reflectivity'])
                        st.metric("이론적 향상", f"{enhancement_factor:.0f}배")
                    else:
                        st.metric("이론적 향상", "N/A")
                with col4:
                    st.metric("Line Shape", line_shape_used.split()[0])
        
        else:
            # 기본 모드 결과
            if 'analysis' in results:
                analysis = results['analysis']
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("R²", f"{analysis['r_squared']:.6f}")
                with col2:
                    st.metric("기울기", f"{analysis['slope']:.2e}")
                with col3:
                    st.metric("절편", f"{analysis['intercept']:.2e}")
                with col4:
                    detection_limit = 3 * 0.001 / analysis['slope'] if analysis['slope'] > 0 else 0
                    st.metric("검출한계 (3σ)", f"{detection_limit:.1f} ppb")


def show_line_shape_comparison():
    """Line Shape 모델 비교 시뮬레이션"""
    st.markdown("---")
    with st.expander("🌊 Line Shape 모델 비교 시뮬레이션"):
        st.markdown("**다양한 Line Shape 모델의 효과를 비교해보세요**")
        
        # 간단한 Line Shape 비교 데모
        demo_x = np.linspace(-2, 2, 1000)
        demo_x0 = 0
        demo_gamma_L = 0.3
        demo_gamma_G = 0.4
        
        line_calc = LineShapeCalculator()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Line Shape 파라미터**")
            demo_gamma_L = st.slider("압력 확산 (γₗ)", 0.1, 1.0, 0.3, 0.1)
            demo_gamma_G = st.slider("도플러 확산 (γᵍ)", 0.1, 1.0, 0.4, 0.1)
        
        with col2:
            # Line Shape 비교 그래프
            fig_demo = go.Figure()
            
            shapes = {
                "Voigt": "red",
                "Gaussian": "blue", 
                "Lorentzian": "green",
                "Hartmann-Tran": "orange"
            }
            
            for shape_name, color in shapes.items():
                y_demo = line_calc.calculate_line_shape(demo_x, demo_x0, demo_gamma_L, demo_gamma_G, shape_name)
                fig_demo.add_trace(
                    go.Scatter(x=demo_x, y=y_demo, name=shape_name, line=dict(color=color, width=2))
                )
            
            fig_demo.update_layout(
                title="Line Shape 모델 비교",
                xaxis_title="주파수 오프셋",
                yaxis_title="정규화된 강도",
                height=300
            )
            st.plotly_chart(fig_demo, use_container_width=True, key="line_shape_demo")
        
        st.markdown("""
        **각 모델의 특징:**
        - **Voigt**: 가장 일반적, 도플러+압력 확산 조합
        - **Gaussian**: 저압 조건, 도플러 확산 지배적
        - **Lorentzian**: 고압 조건, 압력 확산 지배적  
        - **Hartmann-Tran**: 최고 정확도, 모든 물리적 효과 포함
        """)

def main():
    st.set_page_config(page_title="HITRAN Simulator (2025-07-09)", page_icon="🔬", layout="wide")
    st.title("🔬 HITRAN Simulator (2025-07-09)")

    spectrometer_mode, mode, temp, wl_min, wl_max, molecules, molecule, c_min, c_max, c_steps, oa_icos_params, path, matrix_gas_params, molecule_concentrations, num_points, cia_config = show_sidebar()
    # 설정 요약 한 줄로 표시
    summary = f"모드: {spectrometer_mode}, 분석: {mode}, 온도: {temp}K, 파장: {wl_min}~{wl_max} nm, 경로: {path:.1f}m, 해상도: {num_points:,} 포인트"
    if oa_icos_params:
        summary += f", 미러 R: {oa_icos_params['mirror_reflectivity']}, 캐비티: {oa_icos_params['cavity_length']}cm, 손실: {oa_icos_params['mirror_loss']}, 노이즈: {oa_icos_params['detector_noise']}, 드리프트: {oa_icos_params['baseline_drift']}, Line Shape: {oa_icos_params['line_shape']}"
    if matrix_gas_params:
        summary += f", Matrix Gas: {matrix_gas_params['gas_type']}, 압력: {matrix_gas_params['total_pressure_torr']:.1f} torr"
    st.info(summary)
    if mode == "🧪 혼합 스펙트럼":
        st.info(f"분자: {', '.join(molecules) if molecules else '선택 없음'}")
    else:
        st.info(f"분자: {molecule}, 농도: {c_min}~{c_max} ppb ({c_steps}단계)")
    if matrix_gas_params:
        st.info(f"Matrix Gas: {matrix_gas_params['gas_type']}, 압력: {matrix_gas_params['total_pressure_torr']:.1f} torr")

    # 예시: OA-ICOS 시뮬레이터 사용
    # oa_icos_sim = OAICOSSimulator() # 이 부분 삭제
    # st.write("OA-ICOS 기본 파라미터:", oa_icos_sim.default_params) # 이 부분 삭제

    # 예시: Line Shape 비교
    st.subheader("🌊 Line Shape 모델 비교 예시")
    demo_x = np.linspace(-2, 2, 1000)
    demo_gamma_L = 0.3
    demo_gamma_G = 0.4
    line_calc = LineShapeCalculator()
    fig_demo = go.Figure()
    for shape_name, color in zip(["Voigt", "Gaussian", "Lorentzian", "Hartmann-Tran"], ["red", "blue", "green", "orange"]):
        y_demo = line_calc.calculate_line_shape(demo_x, 0, demo_gamma_L, demo_gamma_G, shape_name)
        fig_demo.add_trace(go.Scatter(x=demo_x, y=y_demo, name=shape_name, line=dict(color=color, width=2)))
    fig_demo.update_layout(title="Line Shape 모델 비교", xaxis_title="주파수 오프셋", yaxis_title="정규화된 강도", height=300)
    st.plotly_chart(fig_demo, use_container_width=True, key="main_line_shape_demo")

    btn_text = "🧮 혼합 스펙트럼 계산" if mode == "🧪 혼합 스펙트럼" else "📈 농도별 분석 실행"
    if st.button(btn_text, type="primary"):
        with st.spinner('계산 중...'):
            results, wl_grid = run_simulation(spectrometer_mode, mode, temp, wl_min, wl_max, molecules, molecule, c_min, c_max, c_steps, oa_icos_params, path, matrix_gas_params, molecule_concentrations, num_points, cia_config)
            
            # session state에 결과 저장 (내보내기 기능용)
            st.session_state.simulation_results = results
            st.session_state.wl_grid = wl_grid
            st.session_state.mode = mode
            st.session_state.wavelength_min = wl_min
            st.session_state.wavelength_max = wl_max
            
            show_results(results, wl_grid, mode, molecule, spectrometer_mode, oa_icos_params, matrix_gas_params, molecule_concentrations)

    # 새로운 고급 기능들
    st.markdown("---")
    st.subheader("🚀 고급 분석 기능")
    
    # 탭으로 기능 분리
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📁 실험 데이터", "📋 라인 분석", "🌡️ 파라미터 스윕", "🌊 CIA 분석", "💾 내보내기"])
    
    with tab1:
        # 실험 데이터 업로드 및 오버레이
        experimental_data = upload_experimental_data()
        if experimental_data is not None and 'results' in locals():
            overlay_experimental_data(results, experimental_data, wl_grid, type('Config', (), {
                'mode': mode,
                'wavelength_min': wl_min,
                'wavelength_max': wl_max
            })())
    
    with tab2:
        # 라인 정보 분석
        if 'results' in locals() and results:
            # 라인 데이터 준비 (시뮬레이션 결과를 라인 데이터로 변환)
            line_data = {}
            molecule_info = {'name': molecule if molecule else 'Mixed', 'temperature': temp}
            
            for key, result in results.items():
                if isinstance(result, dict) and 'absorbance' in result:
                    line_data[key] = result
            
            # 인터랙티브 스펙트럼
            if line_data:
                fig_interactive = create_interactive_spectrum_with_tooltips(wl_grid, results, line_data, molecule_info)
                st.plotly_chart(fig_interactive, use_container_width=True)
                
                # 라인 상세 정보
                show_line_details_panel(line_data, molecule_info)
                
                # 고급 라인 분석
                create_advanced_line_analysis(results, wl_grid, line_data, molecule_info)
    
    with tab3:
        # 파라미터 스윕 분석
        if molecule:  # 단일 분자일 때만 스윕 가능
            sweep_config = show_parameter_sweep_panel()
            
            if st.button("🌡️ 파라미터 스윕 실행", type="secondary"):
                if sweep_config:
                    with st.spinner('파라미터 스윕 계산 중...'):
                        api = HitranAPI()
                        calc = SpectrumCalculator()
                        sweep_results = run_parameter_sweep(
                            sweep_config, molecule, wl_min, wl_max, path, num_points, api, calc
                        )
                        visualize_sweep_results(sweep_results, sweep_config, molecule)
        else:
            st.info("💡 파라미터 스윕은 단일 분자 분석 모드에서만 사용 가능합니다.")
    
    with tab4:
        # CIA (Collision-Induced Absorption) 분석
        if CIA_ENABLED:
            show_cia_info()
            
            if 'cia' in st.session_state.get('simulation_results', {}):
                cia_results = st.session_state.simulation_results['cia']
                wl_grid = st.session_state.get('wl_grid', [])
                
                if cia_results and len(wl_grid) > 0:
                    total_cia = show_cia_analysis(cia_results, wl_grid)
                    
                    # CIA와 분자 라인 비교
                    st.subheader("🔍 CIA vs 분자 라인 비교")
                    
                    # 분자 흡수와 CIA 흡수 비교 그래프
                    fig_compare = go.Figure()
                    
                    # 분자 라인 흡수 추가
                    total_molecular = np.zeros_like(wl_grid)
                    for mol, spec in st.session_state.simulation_results.items():
                        if mol not in ['cia', 'combined', 'combined_oa_icos'] and not mol.endswith('_oa_icos'):
                            if isinstance(spec, dict) and 'absorbance' in spec:
                                total_molecular += spec['absorbance']
                    
                    if len(total_molecular) > 0:
                        fig_compare.add_trace(go.Scatter(
                            x=wl_grid,
                            y=total_molecular,
                            name="분자 라인 흡수",
                            line=dict(color='blue', width=2)
                        ))
                    
                    # CIA 흡수 추가
                    if total_cia is not None and len(total_cia) > 0:
                        fig_compare.add_trace(go.Scatter(
                            x=wl_grid,
                            y=total_cia,
                            name="CIA 흡수",
                            line=dict(color='red', width=2)
                        ))
                        
                        # 합계 표시
                        if len(total_molecular) > 0:
                            combined_total = total_molecular + total_cia
                            fig_compare.add_trace(go.Scatter(
                                x=wl_grid,
                                y=combined_total,
                                name="총 흡수 (라인 + CIA)",
                                line=dict(color='purple', width=3, dash='dash')
                            ))
                    
                    fig_compare.update_layout(
                        title="분자 라인 흡수 vs CIA 흡수 비교",
                        xaxis_title="파장 (nm)",
                        yaxis_title="흡수도",
                        height=500,
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig_compare, use_container_width=True)
                    
                    # CIA 기여도 정량 분석
                    if len(total_molecular) > 0 and total_cia is not None:
                        total_signal = np.sum(total_molecular)
                        total_cia_signal = np.sum(total_cia)
                        cia_contribution = (total_cia_signal / (total_signal + total_cia_signal)) * 100 if (total_signal + total_cia_signal) > 0 else 0
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("분자 라인 기여도", f"{100 - cia_contribution:.1f}%")
                        with col2:
                            st.metric("CIA 기여도", f"{cia_contribution:.1f}%")
                        with col3:
                            ratio = total_cia_signal / total_signal if total_signal > 0 else 0
                            st.metric("CIA/라인 비율", f"{ratio:.3f}")
                else:
                    st.info("💡 CIA 결과가 없습니다. CIA 옵션을 활성화하고 시뮬레이션을 다시 실행하세요.")
            else:
                st.info("💡 CIA 분석을 위해 시뮬레이션을 먼저 실행하세요.")
                
                # CIA 데모 기능
                st.markdown("---")
                create_cia_demo()
        else:
            st.error("❌ CIA 모듈을 사용할 수 없습니다. 의존성을 확인하세요.")
    
    with tab5:
        # 결과 내보내기
        if ('simulation_results' in st.session_state and st.session_state.simulation_results and 
            'wl_grid' in st.session_state and st.session_state.wl_grid is not None):
            config = type('Config', (), {
                'mode': st.session_state.get('mode', '기본 모드'),
                'wavelength_min': st.session_state.get('wavelength_min', wl_min),
                'wavelength_max': st.session_state.get('wavelength_max', wl_max)
            })()
            export_results(st.session_state.simulation_results, st.session_state.wl_grid, config)
        else:
            st.info("💡 시뮬레이션을 먼저 실행한 후 내보내기 기능을 사용하세요.")
            if 'simulation_results' in st.session_state:
                st.write("🔍 디버그 정보:")
                st.write(f"- simulation_results 존재: {'simulation_results' in st.session_state}")
                st.write(f"- wl_grid 존재: {'wl_grid' in st.session_state}")
                if 'wl_grid' in st.session_state:
                    st.write(f"- wl_grid 길이: {len(st.session_state.wl_grid) if st.session_state.wl_grid else 0}")

    # Line Shape 비교 시뮬레이션
    show_line_shape_comparison()

    # 하단 정보
    st.markdown("---")
    st.markdown("**🔬 HITRAN CRDS Simulator (고급 기능 추가)** | 실험 데이터 오버레이 + 라인 분석 + 파라미터 스윕 + 내보내기")

if __name__ == "__main__":
    main() 