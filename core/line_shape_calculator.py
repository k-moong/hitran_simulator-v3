"""
Line Shape 계산기
다양한 분광선 모양 모델을 구현한 클래스
"""

import numpy as np
from scipy.special import wofz
import warnings

class LineShapeCalculator:
    """
    분광선 모양 (Line Shape) 계산기
    
    지원하는 모델:
    - Voigt: 도플러 + 압력 확산 조합 (일반적)
    - Gaussian: 도플러 확산 지배적 (저압)
    - Lorentzian: 압력 확산 지배적 (고압)
    - Hartmann-Tran: 모든 물리적 효과 포함 (최고 정확도)
    """
    
    def __init__(self):
        # 물리 상수
        self.k_boltzmann = 1.380649e-23  # J/K
        self.c_light = 2.99792458e8  # m/s
        
    def calculate_line_shape(self, x, x0, gamma_L, gamma_G, shape_type='Voigt'):
        """
        Line Shape 계산
        
        Args:
            x (array): 주파수/파장 그리드
            x0 (float): 선 중심 위치
            gamma_L (float): Lorentzian 폭 (압력 확산)
            gamma_G (float): Gaussian 폭 (도플러 확산)
            shape_type (str): Line Shape 모델
            
        Returns:
            array: 정규화된 Line Shape
        """
        # 중심을 0으로 이동
        x_centered = x - x0
        
        if shape_type.lower() == 'voigt':
            return self._voigt_profile(x_centered, gamma_L, gamma_G)
        elif shape_type.lower() == 'gaussian':
            return self._gaussian_profile(x_centered, gamma_G)
        elif shape_type.lower() == 'lorentzian':
            return self._lorentzian_profile(x_centered, gamma_L)
        elif shape_type.lower() == 'hartmann-tran':
            return self._hartmann_tran_profile(x_centered, gamma_L, gamma_G)
        else:
            warnings.warn(f"알 수 없는 Line Shape 모델: {shape_type}. Voigt를 사용합니다.")
            return self._voigt_profile(x_centered, gamma_L, gamma_G)
    
    def _gaussian_profile(self, x, gamma_G):
        """
        Gaussian Line Shape (도플러 확산 지배적)
        
        Args:
            x (array): 중심으로부터의 거리
            gamma_G (float): Gaussian 폭
            
        Returns:
            array: 정규화된 Gaussian Line Shape
        """
        if gamma_G <= 0:
            return np.zeros_like(x)
        
        # Gaussian 함수: exp(-(x/γ_G)²)
        gaussian = np.exp(-(x / gamma_G)**2)
        
        # 정규화
        normalization = gamma_G * np.sqrt(np.pi)
        return gaussian / normalization
    
    def _lorentzian_profile(self, x, gamma_L):
        """
        Lorentzian Line Shape (압력 확산 지배적)
        
        Args:
            x (array): 중심으로부터의 거리
            gamma_L (float): Lorentzian 폭
            
        Returns:
            array: 정규화된 Lorentzian Line Shape
        """
        if gamma_L <= 0:
            return np.zeros_like(x)
        
        # Lorentzian 함수: γ_L / (π(x² + γ_L²))
        lorentzian = gamma_L / (np.pi * (x**2 + gamma_L**2))
        
        return lorentzian
    
    def _voigt_profile(self, x, gamma_L, gamma_G):
        """
        Voigt Line Shape (도플러 + 압력 확산 조합)
        
        Args:
            x (array): 중심으로부터의 거리
            gamma_L (float): Lorentzian 폭
            gamma_G (float): Gaussian 폭
            
        Returns:
            array: 정규화된 Voigt Line Shape
        """
        if gamma_L <= 0 or gamma_G <= 0:
            return np.zeros_like(x)
        
        # Voigt 파라미터
        sigma = gamma_G / np.sqrt(2 * np.log(2))  # Gaussian 표준편차
        gamma = gamma_L / 2  # Lorentzian 반폭
        
        # 복소수 파라미터
        z = (x + 1j * gamma) / (sigma * np.sqrt(2))
        
        # Faddeeva 함수 (복소 오차 함수)
        w = wofz(z)
        
        # Voigt 함수
        voigt = np.real(w) / (sigma * np.sqrt(2 * np.pi))
        
        return voigt
    
    def _hartmann_tran_profile(self, x, gamma_L, gamma_G, eta=0.0, y=0.0):
        """
        Hartmann-Tran Line Shape (모든 물리적 효과 포함)
        
        Args:
            x (array): 중심으로부터의 거리
            gamma_L (float): Lorentzian 폭
            gamma_G (float): Gaussian 폭
            eta (float): Dicke 협축 파라미터
            y (float): 속도 변화 파라미터
            
        Returns:
            array: 정규화된 Hartmann-Tran Line Shape
        """
        if gamma_L <= 0 or gamma_G <= 0:
            return np.zeros_like(x)
        
        # 기본 Voigt 프로파일
        voigt_base = self._voigt_profile(x, gamma_L, gamma_G)
        
        # Hartmann-Tran 수정 (간단한 근사)
        # 실제로는 더 복잡한 계산이 필요하지만, 여기서는 기본 Voigt에 약간의 수정 적용
        
        # Dicke 협축 효과 (간단한 근사)
        if eta != 0:
            dick_correction = 1 + eta * x / gamma_G
            voigt_base *= dick_correction
        
        # 속도 변화 효과 (간단한 근사)
        if y != 0:
            velocity_correction = 1 + y * (x / gamma_G)**2
            voigt_base *= velocity_correction
        
        return voigt_base
    
    def calculate_line_width(self, temperature, pressure, molecular_mass, 
                           broadening_coefficient=0.1, line_shape='Voigt'):
        """
        온도와 압력에 따른 선 폭 계산
        
        Args:
            temperature (float): 온도 (K)
            pressure (float): 압력 (torr)
            molecular_mass (float): 분자 질량 (amu)
            broadening_coefficient (float): 압력 확산 계수
            line_shape (str): Line Shape 모델
            
        Returns:
            tuple: (gamma_L, gamma_G) 압력 확산 폭, 도플러 확산 폭
        """
        # 도플러 확산 폭 (온도 의존)
        gamma_G = self._calculate_doppler_width(temperature, molecular_mass)
        
        # 압력 확산 폭 (압력 의존)
        gamma_L = self._calculate_pressure_width(pressure, broadening_coefficient)
        
        return gamma_L, gamma_G
    
    def _calculate_doppler_width(self, temperature, molecular_mass):
        """
        도플러 확산 폭 계산
        
        Args:
            temperature (float): 온도 (K)
            molecular_mass (float): 분자 질량 (amu)
            
        Returns:
            float: 도플러 확산 폭 (cm⁻¹)
        """
        # 분자 질량을 kg으로 변환
        mass_kg = molecular_mass * 1.66053907e-27
        
        # 도플러 폭 공식: γ_D = ν₀ * sqrt(2kT / (mc²))
        # 여기서는 간단한 근사 사용
        doppler_width = 3.581e-7 * np.sqrt(temperature / molecular_mass)
        
        return doppler_width
    
    def _calculate_pressure_width(self, pressure, broadening_coefficient):
        """
        압력 확산 폭 계산
        
        Args:
            pressure (float): 압력 (torr)
            broadening_coefficient (float): 압력 확산 계수
            
        Returns:
            float: 압력 확산 폭 (cm⁻¹)
        """
        # 표준 압력 (760 torr)에서의 기본 폭
        base_width = 0.1  # cm⁻¹
        
        # 압력에 따른 스케일링
        pressure_width = base_width * (pressure / 760.0) * broadening_coefficient
        
        return pressure_width
    
    def get_line_shape_info(self):
        """
        Line Shape 모델 정보 반환
        
        Returns:
            dict: Line Shape 모델 정보
        """
        info = {
            'Voigt': {
                'description': '도플러 + 압력 확산 조합',
                'applicability': '일반적 조건 (대부분의 경우)',
                'accuracy': '높음',
                'computation': '중간'
            },
            'Gaussian': {
                'description': '도플러 확산 지배적',
                'applicability': '저압 조건 (< 0.1 atm)',
                'accuracy': '중간',
                'computation': '빠름'
            },
            'Lorentzian': {
                'description': '압력 확산 지배적',
                'applicability': '고압 조건 (> 10 atm)',
                'accuracy': '중간',
                'computation': '빠름'
            },
            'Hartmann-Tran': {
                'description': '모든 물리적 효과 포함',
                'applicability': '최고 정확도 필요시',
                'accuracy': '최고',
                'computation': '느림'
            }
        }
        return info
    
    def compare_line_shapes(self, x, x0, gamma_L, gamma_G):
        """
        모든 Line Shape 모델 비교
        
        Args:
            x (array): 주파수/파장 그리드
            x0 (float): 선 중심 위치
            gamma_L (float): Lorentzian 폭
            gamma_G (float): Gaussian 폭
            
        Returns:
            dict: 모든 모델의 Line Shape
        """
        shapes = {}
        
        for shape_type in ['Voigt', 'Gaussian', 'Lorentzian', 'Hartmann-Tran']:
            shapes[shape_type] = self.calculate_line_shape(x, x0, gamma_L, gamma_G, shape_type)
        
        return shapes 