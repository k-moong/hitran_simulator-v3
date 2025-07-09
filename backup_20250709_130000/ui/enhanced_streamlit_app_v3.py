"""
HITRAN CRDS 시뮬레이터 v3 - OA-ICOS 분광기 시뮬레이션 추가 (Line Shape 기능 포함)
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from scipy.special import wofz  # Line Shape 계산용 추가
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator
from constants import HITRAN_MOLECULES, MOLECULE_CATEGORIES, WAVELENGTH_SHORTCUTS, DEFAULT_CONCENTRATIONS

# Line Shape 계산 클래스 추가
class LineShapeCalculator:
    """Line Shape 계산을 위한 클래스"""
    
    @staticmethod
    def voigt_profile(x, x0, gamma_L, gamma_G):
        """Voigt profile: convolution of Lorentzian and Gaussian"""
        sigma = gamma_G / np.sqrt(2 * np.log(2))
        z = ((x - x0) + 1j * gamma_L) / (sigma * np.sqrt(2))
        return np.real(wofz(z)) / (sigma * np.sqrt(2 * np.pi))
    
    @staticmethod
    def gaussian_profile(x, x0, gamma_G):
        """Gaussian profile (Doppler broadening)"""
        sigma = gamma_G / (2 * np.sqrt(2 * np.log(2)))
        return (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - x0) / sigma) ** 2)
    
    @staticmethod
    def lorentzian_profile(x, x0, gamma_L):
        """Lorentzian profile (pressure/natural broadening)"""
        return (gamma_L / np.pi) / ((x - x0) ** 2 + gamma_L ** 2)
    
    @staticmethod
    def hartmann_tran_profile(x, x0, gamma_L, gamma_G, eta=0):
        """Simplified Hartmann-Tran profile (approximation)"""
        base_voigt = LineShapeCalculator.voigt_profile(x, x0, gamma_L, gamma_G)
        asymmetry = eta * (x - x0) * base_voigt
        return base_voigt + asymmetry
    
    @staticmethod
    def calculate_line_shape(x, x0, gamma_L, gamma_G, shape_type):
        """Calculate line shape based on selected model"""
        if shape_type.startswith("Voigt"):
            return LineShapeCalculator.voigt_profile(x, x0, gamma_L, gamma_G)
        elif shape_type.startswith("Gaussian"):
            return LineShapeCalculator.gaussian_profile(x, x0, gamma_G)
        elif shape_type.startswith("Lorentzian"):
            return LineShapeCalculator.lorentzian_profile(x, x0, gamma_L)
        elif shape_type.startswith("Hartmann-Tran"):
            return LineShapeCalculator.hartmann_tran_profile(x, x0, gamma_L, gamma_G)
        else:
            return LineShapeCalculator.voigt_profile(x, x0, gamma_L, gamma_G)

# OA-ICOS 시뮬레이터 클래스 (Line Shape 기능 추가)
class OAICOSSimulator:
    """OA-ICOS (Off-Axis Integrated Cavity Output Spectroscopy) 시뮬레이터"""
    
    def __init__(self):
        self.default_params = {
            'mirror_reflectivity': 0.9999,
            'cavity_length': 50.0,
            'laser_linewidth': 0.001,
            'mirror_loss': 0.00001,
            'detector_noise': 0.001,
            'baseline_drift': 0.0001,
            'line_shape': 'Voigt (추천)'  # Line Shape 기본값 추가
        }
        self.line_shape_calc = LineShapeCalculator()
    
    def calculate_effective_path_length(self, mirror_reflectivity, cavity_length, mirror_loss=0):
        """유효 광경로 길이 계산: L_eff = L / (1 - R + Loss)"""
        effective_reflectivity = mirror_reflectivity - mirror_loss
        if effective_reflectivity >= 1:
            effective_reflectivity = 0.9999
        
        path_length = cavity_length / (1 - effective_reflectivity)
        return path_length
    
    def apply_laser_linewidth_broadening(self, wavenumbers, spectrum, linewidth, line_shape='Voigt (추천)'):
        """레이저 선폭에 의한 스펙트럼 브로드닝 (선택된 Line Shape 적용)"""
        if linewidth <= 0 or len(spectrum) < 10:
            return spectrum
        
        # 파수를 파장으로 변환하여 간격 계산
        wl_grid = 1e7 / wavenumbers  # nm
        avg_spacing = np.mean(np.abs(np.diff(wl_grid)))
        
        # Line Shape 파라미터 계산
        gamma_L = linewidth * 0.1  # 압력 확산 (경험적)
        gamma_G = linewidth * 0.7  # 도플러 확산 (경험적)
        
        # 커널 크기 계산
        sigma_eff = max(gamma_L, gamma_G)
        kernel_size = max(3, int(10 * sigma_eff / avg_spacing))
        if kernel_size >= len(spectrum):
            return spectrum
        
        # Line Shape에 따른 커널 생성
        center_idx = kernel_size // 2
        x_kernel = np.linspace(-5*sigma_eff, 5*sigma_eff, kernel_size)
        x0 = 0  # 중심 주파수
        
        # 선택된 Line Shape로 커널 계산
        kernel = self.line_shape_calc.calculate_line_shape(
            x_kernel, x0, gamma_L, gamma_G, line_shape
        )
        kernel /= np.sum(kernel)  # 정규화
        
        broadened_spectrum = np.convolve(spectrum, kernel, mode='same')
        return broadened_spectrum
    
    def apply_matrix_gas_effects(self, wavenumbers, spectrum, matrix_params, temp, target_molecule="", line_shape='Voigt (추천)'):
        """Matrix gas 효과 적용 (압력 확산, 선 이동 등) - Line Shape 반영"""
        result = spectrum.copy()
        
        if not matrix_params['enable_pressure_broadening'] and not matrix_params['enable_line_shifting']:
            return result
        
        # 압력을 atm 단위로 변환
        pressure_atm = matrix_params['total_pressure_torr'] / 760.0
        
        # 압력 확산 효과 (Line Shape 적용)
        if matrix_params['enable_pressure_broadening']:
            total_broadening = (
                matrix_params['broadening_factor'] * 
                matrix_params['broadening_enhancement'] * 
                pressure_atm
            )
            
            if total_broadening > 0 and len(wavenumbers) > 10:
                avg_spacing = np.mean(np.abs(np.diff(wavenumbers)))
                
                # Line Shape 파라미터
                gamma_L = total_broadening * 0.8  # 압력 확산이 지배적
                gamma_G = total_broadening * 0.3  # 도플러 확산
                
                sigma_eff = max(gamma_L, gamma_G)
                kernel_size = max(3, int(10 * sigma_eff / avg_spacing))
                
                if kernel_size < len(result):
                    x_kernel = np.linspace(-5*sigma_eff, 5*sigma_eff, kernel_size)
                    
                    # 선택된 Line Shape로 확산 커널 계산
                    broadening_kernel = self.line_shape_calc.calculate_line_shape(
                        x_kernel, 0, gamma_L, gamma_G, line_shape
                    )
                    broadening_kernel /= np.sum(broadening_kernel)
                    
                    result = np.convolve(result, broadening_kernel, mode='same')
        
        # 선 이동 효과
        if matrix_params['enable_line_shifting'] and abs(matrix_params['line_shift_coeff']) > 0:
            shift_amount = matrix_params['line_shift_coeff'] * pressure_atm
            if abs(shift_amount) > 0.001:
                pass  # 간단한 구현을 위해 생략
        
        return result
    
    def add_instrument_effects(self, spectrum, params):
        """기기 효과 추가 (노이즈, 드리프트 등)"""
        result = spectrum.copy()
        
        # 검출기 노이즈 (가우시안 노이즈)
        if params['detector_noise'] > 0:
            noise = np.random.normal(0, params['detector_noise'], len(spectrum))
            result += noise
        
        # 베이스라인 드리프트 (선형 드리프트)
        if params['baseline_drift'] > 0:
            drift = np.linspace(0, params['baseline_drift'], len(spectrum))
            result += drift
        
        return result
    
    def simulate_oa_icos_spectrum(self, absorption_spectrum, params=None, matrix_params=None, temp=296.15):
        """
        OA-ICOS 스펙트럼 시뮬레이션 (Matrix gas 효과 + Line Shape 포함)
        """
        if params is None:
            params = self.default_params.copy()
        
        # Line Shape 정보 추출
        line_shape = params.get('line_shape', 'Voigt (추천)')
        
        # 기본 스펙트럼에서 필요한 데이터 추출
        if 'absorption_coeff' in absorption_spectrum:
            abs_coeff = absorption_spectrum['absorption_coeff']
        elif 'absorbance' in absorption_spectrum:
            abs_coeff = absorption_spectrum['absorbance'] / np.log10(np.e)
        else:
            raise ValueError("흡수 계수 또는 흡광도 데이터가 필요합니다")
        
        # Matrix gas 효과 적용 (Line Shape 포함)
        if matrix_params:
            wavenumbers = 1e7 / absorption_spectrum.get('wavelength', np.linspace(1000, 2000, len(abs_coeff)))
            abs_coeff = self.apply_matrix_gas_effects(wavenumbers, abs_coeff, matrix_params, temp, line_shape=line_shape)
        
        # 유효 광경로 길이 계산
        effective_path = self.calculate_effective_path_length(
            params['mirror_reflectivity'], 
            params['cavity_length'],
            params['mirror_loss']
        )
        
        # OA-ICOS 향상 효과 적용
        enhancement_factor = effective_path / params['cavity_length']
        enhanced_abs_coeff = abs_coeff * enhancement_factor
        
        # 투과율 계산 (Beer-Lambert law)
        transmission = np.exp(-enhanced_abs_coeff * params['cavity_length'])
        
        # 레이저 선폭 브로드닝 적용 (Line Shape 포함)
        if 'wavelength' in absorption_spectrum:
            wl_grid = absorption_spectrum['wavelength']
            freq_grid = 1e7 / wl_grid
            broadened_transmission = self.apply_laser_linewidth_broadening(
                freq_grid, transmission, params['laser_linewidth'], line_shape
            )
        else:
            broadened_transmission = transmission
        
        # 기기 효과 추가
        final_transmission = self.add_instrument_effects(broadened_transmission, params)
        
        # 결과값들이 물리적으로 유효한 범위에 있도록 제한
        final_transmission = np.clip(final_transmission, 1e-10, 1.0)
        
        # 흡광도로 변환
        absorbance = -np.log10(final_transmission)
        
        return {
            'transmission': final_transmission,
            'absorbance': absorbance,
            'enhanced_abs_coeff': enhanced_abs_coeff,
            'effective_path_length': effective_path,
            'enhancement_factor': enhancement_factor,
            'line_shape_used': line_shape  # 사용된 Line Shape 정보 추가
        }

# 페이지 설정
st.set_page_config(page_title="HITRAN CRDS Simulator v3", page_icon="🔬", layout="wide")

# Session State 초기화
if 'results' not in st.session_state:
    st.session_state.results = None

# 제목
st.title("🔬 HITRAN CRDS Simulator v3 with OA-ICOS + Line Shape")

# 사이드바 - 모든 설정
with st.sidebar:
    st.header("⚙️ 시뮬레이션 설정")
    
    # 0. 분광기 모드 선택
    st.subheader("🔬 분광기 모드")
    spectrometer_mode = st.radio(
        "분광기 종류", 
        ["🌟 기본 HITRAN", "🔬 OA-ICOS 분광기"], 
        index=0,
        help="OA-ICOS 모드는 실제 분광기 특성을 반영합니다"
    )
    
    # OA-ICOS 파라미터 (OA-ICOS 모드 선택시에만 표시)
    oa_icos_params = None
    path = None
    
    if spectrometer_mode == "🔬 OA-ICOS 분광기":
        st.markdown("---")
        st.subheader("🔬 OA-ICOS 파라미터")
        
        # 미러 반사율 - 숫자 입력으로 변경
        col1, col2 = st.columns(2)
        with col1:
            mirror_reflectivity = st.number_input(
                "미러 반사율", 
                min_value=0.99000, 
                max_value=0.99999, 
                value=0.99990,
                step=0.00001,
                format="%.5f",
                help="예: 0.99990 = 99.990%"
            )
        with col2:
            st.markdown("**반사율 참고값**")
            st.markdown("- 99.000% → 100배 향상")
            st.markdown("- 99.900% → 1,000배")  
            st.markdown("- 99.990% → 10,000배")
            st.markdown("- 99.999% → 100,000배")
        
        # 캐비티 길이
        cavity_length = st.number_input(
            "캐비티 길이 (cm)", 
            min_value=1.0, 
            max_value=200.0, 
            value=50.0,
            help="물리적 거울 간 거리"
        )
        
        # Line Shape 선택 추가
        st.subheader("🌊 Line Shape 모델")
        line_shape_options = {
            "Voigt (추천)": "도플러 + 압력 확산 조합 (일반적 조건)",
            "Gaussian": "도플러 확산 지배적 (저압 < 0.1 atm)",
            "Lorentzian": "압력 확산 지배적 (고압 > 10 atm)",
            "Hartmann-Tran": "모든 물리적 효과 포함 (최고 정확도)"
        }
        
        line_shape = st.selectbox(
            "모델 선택",
            options=list(line_shape_options.keys()),
            index=0,
            help="스펙트럼 선형 모델을 선택하세요"
        )
        
        st.caption(f"📖 {line_shape_options[line_shape]}")
        
        # 고급 설정 (유효 광경로 계산 전에 먼저 정의)
        with st.expander("🔧 고급 설정"):
            mirror_loss = st.number_input(
                "미러 손실율", 
                min_value=0.0, 
                max_value=0.001, 
                value=0.00001,
                format="%.6f"
            )
            
            detector_noise = st.number_input(
                "검출기 노이즈 레벨", 
                min_value=0.0, 
                max_value=0.01, 
                value=0.00075,  # 0.75 mV RMS 기준
                format="%.5f",
                help="PWPR-2K-IN: 0.75 mV RMS"
            )
            
            baseline_drift = st.number_input(
                "베이스라인 드리프트", 
                min_value=0.0, 
                max_value=0.001, 
                value=0.0001,
                format="%.6f"
            )
        
        # 유효 광경로 자동 계산 및 표시 (모든 입력값이 정의된 후)
        oa_icos_sim_temp = OAICOSSimulator()
        effective_path_preview = oa_icos_sim_temp.calculate_effective_path_length(
            mirror_reflectivity, cavity_length, mirror_loss
        )
        enhancement_factor_preview = effective_path_preview / cavity_length
        
        # 디버그 정보 추가
        st.info(f"""
        **📏 자동 계산된 유효 경로**
        - 미러 반사율: {mirror_reflectivity:.5f}
        - 미러 손실: {mirror_loss:.6f}
        - 실제 반사율: {mirror_reflectivity - mirror_loss:.5f}
        - 캐비티 길이: {cavity_length:.1f} cm
        - 유효 광경로: **{effective_path_preview:.1f} cm** ({effective_path_preview/100:.1f} m)
        - 향상 인수: **{enhancement_factor_preview:.0f}배**
        - **Line Shape**: {line_shape}
        - 계산식: {cavity_length:.1f} / (1 - {mirror_reflectivity - mirror_loss:.5f}) = {effective_path_preview:.1f} cm
        """)
        
        # 실제 계산에 사용할 경로 길이 설정 (미터 단위)
        path = effective_path_preview / 100  # cm to m
        
        # 레이저 선폭 - 실제 측정값 반영
        laser_linewidth = st.number_input(
            "레이저 선폭 (cm⁻¹)", 
            min_value=0.00001, 
            max_value=0.1, 
            value=0.00007,  # 2 MHz ≈ 0.00007 cm⁻¹
            format="%.6f",
            help="NLK1E5GAAA: 2 MHz ≈ 0.00007 cm⁻¹"
        )
        
        # OA-ICOS 파라미터 딕셔너리 (Line Shape 포함)
        oa_icos_params = {
            'mirror_reflectivity': mirror_reflectivity,
            'cavity_length': cavity_length,
            'laser_linewidth': laser_linewidth,
            'mirror_loss': mirror_loss,
            'detector_noise': detector_noise,
            'baseline_drift': baseline_drift,
            'line_shape': line_shape  # Line Shape 정보 추가
        }
    
    st.markdown("---")
    
    # 1. 모드 선택
    mode = st.radio("📊 분석 모드", ["🧪 혼합 스펙트럼", "📈 농도별 분석"], index=0)
    
    st.markdown("---")
    
    # 2. 공통 파라미터
    st.subheader("🌡️ 물리 조건")
    temp = st.number_input("온도 (K)", value=296.15, min_value=200.0, max_value=400.0)
    
    # Matrix Gas 설정 추가
    st.subheader("🌬️ Matrix Gas 설정")
    
    # Matrix gas 선택
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
    
    matrix_gas = st.selectbox(
        "Matrix Gas 종류",
        list(matrix_gases.keys()),
        index=1,  # CDA가 두 번째이므로 기본값으로 설정
        format_func=lambda x: matrix_gases[x]["name"],
        help="Matrix gas는 압력 확산과 선 이동에 영향을 줍니다"
    )
    
    # 압력 설정 (총 압력)
    col1, col2 = st.columns(2)
    with col1:
        total_pressure = st.number_input("총 압력 (torr)", value=760.0, min_value=1.0, max_value=15000.0)
        
        # 스마트 Line Shape 추천 시스템 (OA-ICOS 모드일 때만)
        if spectrometer_mode == "🔬 OA-ICOS 분광기":
            pressure_atm = total_pressure / 760.0
            if pressure_atm < 0.1:
                recommended = "Gaussian"
                reason = f"저압 조건 ({pressure_atm:.3f} atm)에서는 도플러 확산이 지배적"
            elif pressure_atm > 10:
                recommended = "Lorentzian"
                reason = f"고압 조건 ({pressure_atm:.1f} atm)에서는 압력 확산이 지배적"
            else:
                recommended = "Voigt (추천)"
                reason = f"일반 압력 조건 ({pressure_atm:.2f} atm)에서는 혼합 효과가 중요"
            
            if not line_shape.startswith(recommended.split()[0]):
                st.info(f"💡 **추천**: {recommended}\n📝 {reason}")
    
    with col2:
        # Matrix gas 정보 표시
        matrix_info = matrix_gases[matrix_gas]
        st.info(f"""
        **선택된 Matrix Gas:**
        - {matrix_info['name']}
        - 구성: {matrix_info['composition']}
        - 분자량: {matrix_info['molar_mass']} g/mol
        - 확산 계수: {matrix_info['broadening_factor']}x
        - 수분: {matrix_info['humidity']}
        """)
    
    # 고급 Matrix Gas 설정
    with st.expander("🔬 고급 Matrix Gas 설정"):
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
    
    # CDA/Zero Air 사용시 특별 안내
    if matrix_gas == 'CDA':
        st.success(f"""
        ✅ **Clean Dry Air (CDA) 선택됨**
        - **순수 구성**: N2 (78.1%) + O2 (20.9%) **만 존재**
        - **완전 제거**: H2O, CO2, Ar, 기타 모든 trace gases
        - **수분**: < 1 ppm H2O (완전 건조)
        - **표준 조건**: 분광학 교정/측정 표준
        """)
    elif matrix_gas == 'Zero_Air':
        st.success(f"""
        ✅ **Zero Air 선택됨**
        - 베이스라인/영점 측정용
        - 극도로 순수한 N2 + O2
        - 모든 trace gases 제거
        - 수분: < 0.1 ppm H2O
        """)
    elif matrix_gas == 'Air':
        st.warning("""
        ⚠️ **일반 공기 선택됨**  
        - **포함**: H2O (가변), CO2 (~400ppm), Ar (~1%), trace gases
        - **수분 변동**: 상대습도에 따라 수백~수만 ppm 변화
        - **간섭**: H2O, CO2 흡수선으로 인한 스펙트럼 복잡화
        - **권장**: 정밀 측정시 CDA 사용
        """)
    
    # 경로 길이는 분광기 모드에 따라 다르게 처리
    if spectrometer_mode == "🌟 기본 HITRAN":
        path = st.number_input("경로 길이 (m)", value=1000.0, min_value=1.0, max_value=50000.0)
    
    # 경로 길이 최종 확인
    if path is None:
        path = 1000.0  # 기본값
    
    # 3. 파장 범위 - 1392nm 레이저 최적화
    st.subheader("📏 파장 범위 (nm)")
    col1, col2 = st.columns(2)
    with col1:
        wl_min = st.number_input("최소", value=1390.0, min_value=100.0, max_value=50000.0)
    with col2:
        wl_max = st.number_input("최대", value=1395.0, min_value=100.0, max_value=50000.0)
    
    # 1392nm 레이저 추천 설정
    if st.button("🔬 1392nm 레이저 최적 설정"):
        st.session_state.wl_min = 1390.0
        st.session_state.wl_max = 1395.0
        st.rerun()
    
    with st.expander("파장 바로가기"):
        # 1392nm 설정 추가
        if st.button("🎯 1392nm ±3nm (H2O 영역)"):
            st.session_state.wl_min = 1389.0
            st.session_state.wl_max = 1395.0
            st.rerun()
        
        for name, data in list(WAVELENGTH_SHORTCUTS.items())[:4]:  # 주요 4개만
            if st.button(data['description']):
                st.session_state.wl_min = data['min']
                st.session_state.wl_max = data['max']
                st.rerun()
    
    st.markdown("---")
    
    # 4. 모드별 설정
    if mode == "🧪 혼합 스펙트럼":
        st.subheader("🧪 분자 선택")
        
        # 모든 분자 표시
        all_molecules = list(HITRAN_MOLECULES.keys())
        molecules = st.multiselect(
            f"분자 선택 (총 {len(all_molecules)}개)",
            all_molecules,
            default=["H2O", "CO2", "CH4"],
            format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})",
            help="최대 15개까지 선택 가능합니다"
        )
        
        if len(molecules) > 15:
            st.warning("⚠️ 최대 15개까지만 선택 가능합니다.")
            molecules = molecules[:15]
        
        # 농도 설정
        if molecules:
            st.subheader("💨 농도 (ppb)")
            use_same = st.checkbox("모든 분자 동일 농도", value=False)
            
            concs = {}
            if use_same:
                same_conc = st.number_input("농도", value=1000.0, min_value=0.1)
                for mol in molecules:
                    concs[mol] = same_conc
            else:
                for mol in molecules:
                    concs[mol] = st.number_input(
                        f"{mol}", 
                        value=DEFAULT_CONCENTRATIONS.get(mol, 100.0),
                        min_value=0.1,
                        key=f"c_{mol}"
                    )
    
    else:  # 농도별 분석
        st.subheader("🧪 분자 선택")
        all_molecules = list(HITRAN_MOLECULES.keys())
        molecule = st.selectbox(
            f"분석할 분자 (총 {len(all_molecules)}개)",
            all_molecules,
            format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})",
            index=all_molecules.index("CH4") if "CH4" in all_molecules else 0
        )
        
        st.subheader("📊 농도 범위")
        c_min = st.number_input("최소 (ppb)", value=10.0, min_value=0.1)
        c_max = st.number_input("최대 (ppb)", value=5000.0, min_value=0.1)
        c_steps = st.slider("단계 수", 3, 20, 10)
    
    # 5. 실행 버튼
    st.markdown("---")
    btn_text = "🧮 혼합 스펙트럼 계산" if mode == "🧪 혼합 스펙트럼" else "📈 농도별 분석 실행"
    calc_btn = st.button(btn_text, type="primary", use_container_width=True)

# 메인 화면 - 결과
if calc_btn:
    if wl_min >= wl_max:
        st.error("❌ 파장 범위를 확인하세요!")
    else:
        with st.spinner('계산 중...'):
            # API 초기화
            api = HitranAPI()
            calc = SpectrumCalculator()
            
            # OA-ICOS 시뮬레이터 초기화 (필요시)
            oa_icos_sim = None
            if spectrometer_mode == "🔬 OA-ICOS 분광기":
                oa_icos_sim = OAICOSSimulator()
            
            # 주파수 격자
            freq_min = 1e7 / wl_max
            freq_max = 1e7 / wl_min
            freq_grid = np.linspace(freq_min, freq_max, 3000)
            wl_grid = 1e7 / freq_grid
            
            if mode == "🧪 혼합 스펙트럼" and molecules:
                # 혼합 스펙트럼 계산
                results = {'spectra': {}, 'oa_icos_spectra': {}, 'combined': None, 'oa_icos_combined': None}
                combined_abs = np.zeros_like(freq_grid)
                
                progress = st.progress(0)
                for i, mol in enumerate(molecules):
                    progress.progress((i+1)/len(molecules))
                    
                    data = api.download_molecule_data(mol, wl_min, wl_max)
                    if data is not None and len(data) > 0:
                        spec = calc.calculate_absorption_spectrum(
                            data, freq_grid, temp, matrix_gas_params['total_pressure_torr']/760.0, 
                            concs[mol]/1e9, path, mol
                        )
                        spec['wavelength'] = wl_grid  # 파장 정보 추가
                        results['spectra'][mol] = spec
                        combined_abs += spec['absorption_coeff']
                        
                        # OA-ICOS 시뮬레이션 (모드가 선택된 경우)
                        if oa_icos_sim:
                            oa_icos_result = oa_icos_sim.simulate_oa_icos_spectrum(
                                spec, oa_icos_params, matrix_gas_params, temp
                            )
                            results['oa_icos_spectra'][mol] = oa_icos_result
                
                # 기본 혼합 스펙트럼
                results['combined'] = {
                    'transmittance': np.exp(-combined_abs * path),
                    'absorbance': -np.log10(np.exp(-combined_abs * path))
                }
                
                # OA-ICOS 혼합 스펙트럼 (모드가 선택된 경우)
                if oa_icos_sim:
                    combined_spectrum = {
                        'absorption_coeff': combined_abs,
                        'wavelength': wl_grid
                    }
                    oa_icos_combined = oa_icos_sim.simulate_oa_icos_spectrum(
                        combined_spectrum, oa_icos_params, matrix_gas_params, temp
                    )
                    results['oa_icos_combined'] = oa_icos_combined
                
                results['wavelength'] = wl_grid
                results['spectrometer_mode'] = spectrometer_mode
                results['oa_icos_params'] = oa_icos_params
                results['matrix_gas_params'] = matrix_gas_params
                st.session_state.results = ('mix', results)
                
            elif mode == "📈 농도별 분석":
                # 농도별 분석
                if c_min >= c_max:
                    st.error("❌ 농도 범위를 확인하세요!")
                else:
                    concs_array = np.linspace(c_min, c_max, c_steps)
                    results = {'spectra': {}, 'oa_icos_spectra': {}, 'analysis': {}, 'oa_icos_analysis': {}}
                    
                    # HITRAN 데이터 다운로드
                    data = api.download_molecule_data(molecule, wl_min, wl_max)
                    
                    if data is not None and len(data) > 0:
                        max_abs = []
                        oa_icos_max_abs = []
                        progress = st.progress(0)
                        
                        for i, c in enumerate(concs_array):
                            progress.progress((i+1)/c_steps)
                            spec = calc.calculate_absorption_spectrum(
                                data, freq_grid, temp, matrix_gas_params['total_pressure_torr']/760.0,
                                c/1e9, path, molecule
                            )
                            spec['wavelength'] = wl_grid  # 파장 정보 추가
                            results['spectra'][c] = spec
                            max_abs.append(np.max(spec['absorbance']))
                            
                            # OA-ICOS 시뮬레이션 (모드가 선택된 경우)
                            if oa_icos_sim:
                                oa_icos_result = oa_icos_sim.simulate_oa_icos_spectrum(
                                    spec, oa_icos_params, matrix_gas_params, temp
                                )
                                results['oa_icos_spectra'][c] = oa_icos_result
                                oa_icos_max_abs.append(np.max(oa_icos_result['absorbance']))
                        
                        # 기본 선형성 분석
                        slope, intercept, r_value, _, _ = stats.linregress(concs_array, max_abs)
                        results['analysis'] = {
                            'concentrations': concs_array,
                            'max_absorbances': max_abs,
                            'r_squared': r_value**2,
                            'slope': slope,
                            'intercept': intercept
                        }
                        
                        # OA-ICOS 선형성 분석 (모드가 선택된 경우)
                        if oa_icos_sim and oa_icos_max_abs:
                            slope_oa, intercept_oa, r_value_oa, _, _ = stats.linregress(concs_array, oa_icos_max_abs)
                            results['oa_icos_analysis'] = {
                                'concentrations': concs_array,
                                'max_absorbances': oa_icos_max_abs,
                                'r_squared': r_value_oa**2,
                                'slope': slope_oa,
                                'intercept': intercept_oa
                            }
                        
                        results['wavelength'] = wl_grid
                        results['molecule'] = molecule
                        results['spectrometer_mode'] = spectrometer_mode
                        results['oa_icos_params'] = oa_icos_params
                        results['matrix_gas_params'] = matrix_gas_params
                        st.session_state.results = ('conc', results)

# 결과 표시
if st.session_state.results:
    result_type, results = st.session_state.results
    
    # OA-ICOS 모드일 때 상단에 성능 지표 표시 (Line Shape 정보 포함)
    if results.get('spectrometer_mode') == "🔬 OA-ICOS 분광기" and results.get('oa_icos_params'):
        oa_icos_sim = OAICOSSimulator()
        params = results['oa_icos_params']
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
    if results.get('matrix_gas_params'):
        matrix_params = results['matrix_gas_params']
        st.subheader("🌬️ Matrix Gas 조건")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Matrix Gas", matrix_params['gas_type'])
        with col2:
            st.metric("총 압력", f"{matrix_params['total_pressure_torr']:.1f} torr")
        with col3:
            broadening_status = "ON" if matrix_params['enable_pressure_broadening'] else "OFF"
            st.metric("압력 확산", broadening_status)
        with col4:
            line_shift_status = "ON" if matrix_params['enable_line_shifting'] else "OFF"
            st.metric("선 이동", line_shift_status)
    
    if result_type == 'mix':
        st.subheader("📊 혼합 스펙트럼 결과")
        
        # Line Shape 정보 표시 (OA-ICOS 모드인 경우)
        if results.get('spectrometer_mode') == "🔬 OA-ICOS 분광기" and results.get('oa_icos_params'):
            line_shape_used = results['oa_icos_params'].get('line_shape', 'Voigt (추천)')
            st.info(f"🌊 **적용된 Line Shape**: {line_shape_used}")
        
        # OA-ICOS 모드인 경우 2단 그래프, 기본 모드인 경우 1단 그래프
        is_oa_icos = results.get('spectrometer_mode') == "🔬 OA-ICOS 분광기"
        rows = 2 if is_oa_icos else 1
        
        subplot_titles = ['개별 분자 스펙트럼']
        if is_oa_icos:
            subplot_titles.append('기본 HITRAN vs OA-ICOS 비교')
        
        fig = make_subplots(rows=rows, cols=1, 
                           subplot_titles=subplot_titles,
                           vertical_spacing=0.15)
        
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        # 개별 분자 스펙트럼
        for i, (mol, spec) in enumerate(results['spectra'].items()):
            fig.add_trace(
                go.Scatter(x=results['wavelength'], y=spec['absorbance'],
                          name=f"{mol} ({HITRAN_MOLECULES[mol]['name']})",
                          line=dict(color=colors[i % len(colors)])),
                row=1, col=1
            )
        
        # OA-ICOS 비교 (모드가 선택된 경우)
        if is_oa_icos and 'oa_icos_combined' in results:
            # 기본 vs OA-ICOS 혼합 스펙트럼 비교
            fig.add_trace(
                go.Scatter(x=results['wavelength'], y=results['combined']['absorbance'],
                          name='기본 HITRAN (혼합)', 
                          line=dict(color='darkblue', width=3, dash='solid')),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=results['wavelength'], y=results['oa_icos_combined']['absorbance'],
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
        
    else:  # 농도별 분석
        st.subheader(f"📈 {results['molecule']} 농도별 분석 결과")
        
        # Line Shape 정보 표시 (OA-ICOS 모드인 경우)
        is_oa_icos = results.get('spectrometer_mode') == "🔬 OA-ICOS 분광기"
        if is_oa_icos and results.get('oa_icos_params'):
            line_shape_used = results['oa_icos_params'].get('line_shape', 'Voigt (추천)')
            st.info(f"🌊 **적용된 Line Shape**: {line_shape_used}")
        
        if is_oa_icos:
            # OA-ICOS 모드: 2x2 레이아웃
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("기본 HITRAN")
                # 농도별 스펙트럼 (기본)
                fig1 = go.Figure()
                colors = ['darkblue', 'blue', 'lightblue', 'green', 'yellow', 'orange', 'red', 'darkred']
                
                for i, (c, spec) in enumerate(results['spectra'].items()):
                    color_idx = int(i * (len(colors)-1) / (len(results['spectra'])-1))
                    fig1.add_trace(
                        go.Scatter(x=results['wavelength'], y=spec['absorbance'],
                                  name=f'{c:.1f} ppb',
                                  line=dict(color=colors[color_idx]))
                    )
                
                fig1.update_layout(title="농도별 스펙트럼 (기본)", xaxis_title="파장 (nm)", 
                                  yaxis_title="흡광도", height=400)
                st.plotly_chart(fig1, use_container_width=True)
                
                # 선형성 분석 (기본)
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
                if 'oa_icos_spectra' in results:
                    fig3 = go.Figure()
                    
                    for i, (c, oa_spec) in enumerate(results['oa_icos_spectra'].items()):
                        color_idx = int(i * (len(colors)-1) / (len(results['oa_icos_spectra'])-1))
                        fig3.add_trace(
                            go.Scatter(x=results['wavelength'], y=oa_spec['absorbance'],
                                      name=f'{c:.1f} ppb',
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
                
                for i, (c, spec) in enumerate(results['spectra'].items()):
                    color_idx = int(i * (len(colors)-1) / (len(results['spectra'])-1))
                    fig1.add_trace(
                        go.Scatter(x=results['wavelength'], y=spec['absorbance'],
                                  name=f'{c:.1f} ppb',
                                  line=dict(color=colors[color_idx]))
                    )
                
                fig1.update_layout(title="농도별 스펙트럼", xaxis_title="파장 (nm)", 
                                  yaxis_title="흡광도", height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # 선형성 분석
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
                    enhancement_factor = 1 / (1 - results['oa_icos_params']['mirror_reflectivity'])
                    st.metric("이론적 향상", f"{enhancement_factor:.0f}배")
                with col4:
                    st.metric("Line Shape", line_shape_used.split()[0])
        
        else:
            # 기본 모드 결과
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

# Line Shape 비교 시뮬레이션 (추가 기능)
if st.session_state.results and st.session_state.results[1].get('spectrometer_mode') == "🔬 OA-ICOS 분광기":
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
            st.plotly_chart(fig_demo, use_container_width=True)
        
        st.markdown("""
        **각 모델의 특징:**
        - **Voigt**: 가장 일반적, 도플러+압력 확산 조합
        - **Gaussian**: 저압 조건, 도플러 확산 지배적
        - **Lorentzian**: 고압 조건, 압력 확산 지배적  
        - **Hartmann-Tran**: 최고 정확도, 모든 물리적 효과 포함
        """)

# 하단 정보
st.markdown("---")
st.markdown("**🔬 HITRAN CRDS Simulator v3** | OA-ICOS 분광기 + Line Shape 시뮬레이션 | 실제 장비 스펙 반영")