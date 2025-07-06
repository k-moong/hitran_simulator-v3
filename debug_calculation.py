"""
스펙트럼 계산 과정 디버깅
"""

import numpy as np
from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator

def debug_calculation():
    print("=== 스펙트럼 계산 과정 디버깅 ===")
    
    # HITRAN 데이터 다운로드
    hitran_api = HitranAPI()
    hitran_data = hitran_api.download_molecule_data("H2O", 1500, 1520)
    
    # 주파수 격자 (작은 범위로 테스트)
    freq_min = 6648  # 가장 강한 라인 근처
    freq_max = 6650
    frequency_grid = np.linspace(freq_min, freq_max, 1000)
    
    print(f"주파수 범위: {freq_min}-{freq_max} cm^-1")
    print(f"가장 강한 라인: 6648.88 cm^-1")
    
    # 계산기 초기화
    calc = SpectrumCalculator()
    
    # 가장 강한 라인만 가지고 테스트
    strongest_line = None
    max_intensity = 0
    
    for line in hitran_data:
        if line['sw'] > max_intensity:
            max_intensity = line['sw']
            strongest_line = line
    
    print(f"\n=== 가장 강한 라인 정보 ===")
    print(f"중심 주파수: {strongest_line['nu']:.4f} cm^-1")
    print(f"선 강도: {strongest_line['sw']:.4e}")
    print(f"공기 확장: {strongest_line['gamma_air']:.4e}")
    
    # 한 라인만으로 계산 테스트
    print(f"\n=== 단일 라인 계산 테스트 ===")
    
    # 파라미터들
    temperature = 296.15
    pressure = 7.0
    concentration = 0.001
    path_length = 30000.0
    molecular_mass = 18.015
    
    # 도플러 폭 계산
    gamma_d = calc.calculate_doppler_width(strongest_line['nu'], temperature, molecular_mass)
    print(f"도플러 폭: {gamma_d:.6e} cm^-1")
    
    # 로렌츠 폭 계산
    gamma_l = calc.calculate_lorentz_width(strongest_line['gamma_air'], pressure, temperature)
    print(f"로렌츠 폭: {gamma_l:.6e} cm^-1")
    
    # Voigt 프로파일 계산
    line_shape = calc.voigt_profile(frequency_grid, strongest_line['nu'], gamma_l, gamma_d)
    print(f"Voigt 프로파일 최대값: {np.max(line_shape):.6e}")
    
    # 흡수 계수 계산
    absorption_coeff = strongest_line['sw'] * concentration * line_shape
    print(f"흡수 계수 최대값: {np.max(absorption_coeff):.6e}")
    
    # 투과율 계산
    transmittance = np.exp(-absorption_coeff * path_length)
    print(f"투과율 최소값: {np.min(transmittance):.6f}")
    print(f"투과율 최대값: {np.max(transmittance):.6f}")
    
    # 흡광도 계산
    absorbance = -np.log10(transmittance)
    print(f"흡광도 최대값: {np.max(absorbance):.6f}")
    
    # 간단한 그래프
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=(10, 6))
    wavelength_nm = 1e7 / frequency_grid
    
    plt.subplot(2, 1, 1)
    plt.plot(wavelength_nm, transmittance)
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Transmittance')
    plt.title('Single Line Test - Transmittance')
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(wavelength_nm, absorbance)
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Absorbance')
    plt.title('Single Line Test - Absorbance')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('output/debug_single_line.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    debug_calculation()