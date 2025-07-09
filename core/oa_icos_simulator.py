"""
OA-ICOS (Off-Axis Integrated Cavity Output Spectroscopy) 시뮬레이터
실제 장비 스펙을 반영한 고정밀 분광기 시뮬레이션 기능을 포함합니다.
"""

import numpy as np
from scipy import constants
import warnings

class OAICOSSimulator:
    """
    OA-ICOS 분광기 시뮬레이터
    
    실제 장비 스펙:
    - 미러 반사율: 99.990% (R = 0.99990)
    - 캐비티 길이: 50 cm
    - 검출기: PWPR-2K-IN (0.75 mV RMS 노이즈)
    - 유효 광경로: ~10,000 cm (100 m)
    """
    
    def __init__(self):
        # 기본 파라미터 (실제 장비 스펙 기반)
        self.default_params = {
            'mirror_reflectivity': 0.99990,  # 99.990%
            'cavity_length': 50.0,  # cm
            'mirror_loss': 0.00001,  # 0.001%
            'detector_noise': 0.00075,  # PWPR-2K-IN: 0.75 mV RMS
            'baseline_drift': 0.0001,  # 0.01%
            'line_shape': 'Voigt',
            'enhancement_factor': None  # 자동 계산
        }
        
        # 물리 상수
        self.c = constants.c * 100  # cm/s
        self.h = constants.h  # J⋅s
        self.k = constants.k  # J/K
        
    def calculate_effective_path_length(self, mirror_reflectivity, cavity_length, mirror_loss=0.00001):
        """
        유효 광경로 계산
        
        Args:
            mirror_reflectivity (float): 미러 반사율 (0~1)
            cavity_length (float): 캐비티 길이 (cm)
            mirror_loss (float): 미러 손실율
            
        Returns:
            float: 유효 광경로 (cm)
        """
        # 총 손실율 계산
        total_loss = 1 - mirror_reflectivity + mirror_loss
        
        # 유효 광경로 = 캐비티 길이 / 총 손실율
        effective_path = cavity_length / total_loss
        
        return effective_path
    
    def calculate_enhancement_factor(self, mirror_reflectivity, cavity_length, mirror_loss=0.00001):
        """
        향상 계수 계산
        
        Returns:
            float: 향상 계수 (배)
        """
        effective_path = self.calculate_effective_path_length(mirror_reflectivity, cavity_length, mirror_loss)
        enhancement = effective_path / cavity_length
        return enhancement
    
    def simulate_oa_icos_spectrum(self, wavelength_grid, absorption_coeff, 
                                 mirror_reflectivity=0.99990, cavity_length=50.0,
                                 mirror_loss=0.00001, detector_noise=0.00075,
                                 baseline_drift=0.0001, line_shape='Voigt'):
        """
        OA-ICOS 스펙트럼 시뮬레이션
        
        Args:
            wavelength_grid (array): 파장 그리드 (nm)
            absorption_coeff (array): 흡수 계수 (cm⁻¹)
            mirror_reflectivity (float): 미러 반사율
            cavity_length (float): 캐비티 길이 (cm)
            mirror_loss (float): 미러 손실율
            detector_noise (float): 검출기 노이즈 레벨
            baseline_drift (float): 베이스라인 드리프트
            
        Returns:
            dict: 시뮬레이션 결과
        """
        # 유효 광경로 계산
        effective_path = self.calculate_effective_path_length(
            mirror_reflectivity, cavity_length, mirror_loss
        )
        
        # 향상 계수 계산
        enhancement_factor = self.calculate_enhancement_factor(
            mirror_reflectivity, cavity_length, mirror_loss
        )
        
        # OA-ICOS 흡광도 계산 (Beer-Lambert 법칙)
        # A = -log(I/I₀) = α × L
        oa_icos_absorption = absorption_coeff * effective_path / 100  # cm → m 변환
        
        # 검출기 노이즈 추가
        noise = np.random.normal(0, detector_noise, len(wavelength_grid))
        
        # 베이스라인 드리프트 추가 (선형 드리프트)
        drift = baseline_drift * np.linspace(0, 1, len(wavelength_grid))
        
        # 최종 OA-ICOS 신호
        oa_icos_signal = oa_icos_absorption + noise + drift
        
        # 결과 반환
        results = {
            'wavelength': wavelength_grid,
            'absorption_coefficient': absorption_coeff,
            'oa_icos_absorption': oa_icos_absorption,
            'oa_icos_signal': oa_icos_signal,
            'effective_path_length': effective_path,
            'enhancement_factor': enhancement_factor,
            'detector_noise': noise,
            'baseline_drift': drift,
            'parameters': {
                'mirror_reflectivity': mirror_reflectivity,
                'cavity_length': cavity_length,
                'mirror_loss': mirror_loss,
                'detector_noise': detector_noise,
                'baseline_drift': baseline_drift,
                'line_shape': line_shape
            }
        }
        
        return results
    
    def calculate_detection_limit(self, absorption_coeff, enhancement_factor, 
                                 detector_noise=0.00075, snr_threshold=3):
        """
        검출 한계 계산
        
        Args:
            absorption_coeff (array): 흡수 계수 (cm⁻¹)
            enhancement_factor (float): 향상 계수
            detector_noise (float): 검출기 노이즈
            snr_threshold (float): 신호대잡음비 임계값
            
        Returns:
            float: 검출 한계 (ppb)
        """
        # 최대 흡수 계수
        max_absorption = np.max(absorption_coeff)
        
        # 향상된 신호
        enhanced_signal = max_absorption * enhancement_factor
        
        # 검출 한계 = (노이즈 × SNR 임계값) / 향상된 신호
        detection_limit = (detector_noise * snr_threshold) / enhanced_signal
        
        return detection_limit
    
    def simulate_line_shape_effects(self, wavelength_grid, line_centers, line_intensities,
                                   line_widths, line_shape='Voigt', temperature=296.15,
                                   pressure=760.0):
        """
        Line Shape 효과 시뮬레이션
        
        Args:
            wavelength_grid (array): 파장 그리드
            line_centers (array): 선 중심 파장
            line_intensities (array): 선 강도
            line_widths (array): 선 폭
            line_shape (str): Line Shape 모델
            temperature (float): 온도 (K)
            pressure (float): 압력 (torr)
            
        Returns:
            array: Line Shape이 적용된 흡수 계수
        """
        from core.line_shape_calculator import LineShapeCalculator
        
        line_calc = LineShapeCalculator()
        absorption = np.zeros_like(wavelength_grid)
        
        for center, intensity, width in zip(line_centers, line_intensities, line_widths):
            # Line Shape 계산
            line_profile = line_calc.calculate_line_shape(
                wavelength_grid, center, width/2, width/2, line_shape
            )
            
            # 강도 스케일링
            absorption += intensity * line_profile
        
        return absorption
    
    def get_equipment_specs(self):
        """
        실제 장비 스펙 반환
        
        Returns:
            dict: 장비 스펙
        """
        specs = {
            'mirror_reflectivity': '99.990% (R = 0.99990)',
            'cavity_length': '50 cm',
            'effective_path_length': '~10,000 cm (100 m)',
            'enhancement_factor': '~200배',
            'detector': 'PWPR-2K-IN',
            'detector_noise': '0.75 mV RMS',
            'wavelength_range': '1.2 - 2.5 μm',
            'resolution': '< 0.001 cm⁻¹',
            'sensitivity': '10⁻⁹ - 10⁻¹² cm⁻¹'
        }
        return specs
    
    def validate_parameters(self, mirror_reflectivity, cavity_length, mirror_loss):
        """
        파라미터 유효성 검사
        
        Args:
            mirror_reflectivity (float): 미러 반사율
            cavity_length (float): 캐비티 길이
            mirror_loss (float): 미러 손실율
            
        Returns:
            bool: 유효성 여부
        """
        if not (0.99 <= mirror_reflectivity <= 0.99999):
            warnings.warn("미러 반사율은 0.99 ~ 0.99999 범위여야 합니다.")
            return False
        
        if not (1.0 <= cavity_length <= 200.0):
            warnings.warn("캐비티 길이는 1.0 ~ 200.0 cm 범위여야 합니다.")
            return False
        
        if not (0.0 <= mirror_loss <= 0.001):
            warnings.warn("미러 손실율은 0.0 ~ 0.001 범위여야 합니다.")
            return False
        
        return True 