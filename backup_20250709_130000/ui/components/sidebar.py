"""
사이드바 컴포넌트
"""
import streamlit as st
from collections import defaultdict
from typing import Tuple, Optional, Dict, List

from ui.models.config import SimulationConfig, MatrixGasConfig, OAICOSConfig
from ui.utils.helpers import calculate_resolution_info
from constants import HITRAN_MOLECULES, DEFAULT_CONCENTRATIONS

def create_matrix_gas_config() -> MatrixGasConfig:
    """Matrix Gas 설정 생성"""
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
    
    return MatrixGasConfig(
        gas_type=matrix_gas,
        total_pressure_torr=total_pressure,
        broadening_factor=matrix_info['broadening_factor'],
        broadening_enhancement=broadening_enhancement,
        enable_pressure_broadening=enable_pressure_broadening,
        enable_line_shifting=enable_line_shifting,
        line_shift_coeff=line_shift_coeff,
        molar_mass=matrix_info['molar_mass'],
        humidity=matrix_info['humidity'],
        composition=matrix_info['composition']
    )

def create_oa_icos_config() -> Optional[OAICOSConfig]:
    """OA-ICOS 설정 생성"""
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
    
    return OAICOSConfig(
        mirror_reflectivity=mirror_reflectivity,
        cavity_length=cavity_length,
        mirror_loss=mirror_loss,
        detector_noise=detector_noise,
        baseline_drift=baseline_drift,
        line_shape=line_shape.split()[0]  # 실제 모델명만
    )

def select_molecules(mode: str) -> Tuple[Optional[List[str]], Optional[str], Optional[Dict[str, float]]]:
    """분자 선택"""
    all_molecules = list(HITRAN_MOLECULES.keys())
    
    # base별 그룹핑
    grouped = defaultdict(list)
    for k in all_molecules:
        grouped[HITRAN_MOLECULES[k]['base']].append(k)
    
    # 1단계: 여러 분자(base) 멀티셀렉트
    base_molecules = sorted(set([HITRAN_MOLECULES[k]['base'] for k in all_molecules]), 
                           key=lambda b: HITRAN_MOLECULES[[k for k in all_molecules if HITRAN_MOLECULES[k]['base']==b][0]]['kor'])
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
            base_concentrations[base] = st.sidebar.number_input(
                f"농도 (ppb) - {base_kor_map[base]}", 
                min_value=0.0, value=float(default_ppb), step=1.0, format="%.1f"
            )
        
        # 2단계: 각 분자별 동위원소 멀티셀렉트
        selected_isos = []
        iso_to_base = {}
        if selected_bases:
            for base in selected_bases:
                iso_keys = [k for k in all_molecules if HITRAN_MOLECULES[k]['base'] == base]
                major_iso_key = [k for k in iso_keys if HITRAN_MOLECULES[k]['iso'] == 1]
                
                def iso_label(key):
                    info = HITRAN_MOLECULES[key]
                    from ui.utils.helpers import isotope_label
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
        
        # 농도 매핑 전달
        molecule_concentrations = {}
        if base_concentrations and selected_isos:
            molecule_concentrations = {iso: base_concentrations[iso_to_base[iso]] for iso in selected_isos}
        
        return selected_isos, None, molecule_concentrations
        
    else:
        # 농도별 분석 모드: 한 분자만, 동위원소도 하나만 선택
        selected_bases = st.sidebar.selectbox(
            "분자 선택", base_molecules, index=0, 
            format_func=lambda b: f"{base_kor_map[b]} ({b})"
        )
        
        iso_keys = [k for k in all_molecules if HITRAN_MOLECULES[k]['base'] == selected_bases]
        major_iso_key = [k for k in iso_keys if HITRAN_MOLECULES[k]['iso'] == 1]
        
        def iso_label(key):
            info = HITRAN_MOLECULES[key]
            from ui.utils.helpers import isotope_label
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
        
        return None, selected, None

def show_sidebar() -> SimulationConfig:
    """사이드바 표시 및 설정 반환"""
    st.sidebar.header("⚙️ 시뮬레이션 설정")
    
    # 기본 설정
    spectrometer_mode = st.sidebar.radio("분광기 종류", ["🌟 기본 HITRAN", "🔬 분광기"], index=0)
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

    # 해상도 설정
    st.sidebar.subheader("🔬 해상도 설정")
    resolution_mode = st.sidebar.radio(
        "해상도 모드",
        ["⚡ 빠른 (3000 포인트)", "🎯 표준 (10000 포인트)", "🔬 고해상도 (30000 포인트)", "🚀 최대 해상도 (100000 포인트)"],
        index=1,
        help="해상도가 높을수록 정확하지만 계산 시간이 오래 걸립니다"
    )
    
    resolution_points = {
        "⚡ 빠른 (3000 포인트)": 3000,
        "🎯 표준 (10000 포인트)": 10000,
        "🔬 고해상도 (30000 포인트)": 30000,
        "🚀 최대 해상도 (100000 포인트)": 100000
    }
    
    num_points = resolution_points[resolution_mode]
    
    # 해상도 정보 표시
    resolution_nm, resolution_cm = calculate_resolution_info(wl_min, wl_max, num_points)
    
    st.sidebar.info(f"""
    **해상도 정보:**
    - 포인트 수: {num_points:,}개
    - 파장 해상도: {resolution_nm:.6f} nm
    - 주파수 해상도: {resolution_cm:.6f} cm⁻¹
    """)

    # Matrix Gas 설정
    st.sidebar.subheader("🌬️ Matrix Gas 설정")
    matrix_gas = create_matrix_gas_config()

    # OA-ICOS 파라미터
    oa_icos_params = None
    path = 1000.0  # 기본값
    if spectrometer_mode == "🔬 분광기":
        oa_icos_params = create_oa_icos_config()
        path = st.sidebar.number_input("광경로 (m)", min_value=10.0, max_value=2000.0, value=1000.0)
    else:
        # 기본 HITRAN 모드
        path = st.sidebar.number_input("경로 길이 (m)", value=1000.0, min_value=1.0, max_value=50000.0)

    # 분자 선택
    molecules, molecule, molecule_concentrations = select_molecules(mode)
    
    # 농도별 분석 모드에서 농도 범위 설정
    c_min = c_max = c_steps = None
    if mode == "📈 농도별 분석":
        c_min = st.sidebar.number_input("농도 최소 (ppb)", value=10.0, min_value=0.1)
        c_max = st.sidebar.number_input("농도 최대 (ppb)", value=5000.0, min_value=0.1)
        c_steps = st.sidebar.slider("단계 수", 3, 20, 10)

    return SimulationConfig(
        spectrometer_mode=spectrometer_mode,
        mode=mode,
        temperature=temp,
        wavelength_min=wl_min,
        wavelength_max=wl_max,
        path_length=path,
        num_points=num_points,
        matrix_gas=matrix_gas,
        oa_icos=oa_icos_params,
        molecules=molecules,
        molecule=molecule,
        concentration_min=c_min,
        concentration_max=c_max,
        concentration_steps=c_steps,
        molecule_concentrations=molecule_concentrations
    ) 