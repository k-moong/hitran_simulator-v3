"""
HITRAN 데이터와 스펙트럼 계산 통합 테스트
"""

import numpy as np
import matplotlib.pyplot as plt
from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator

def main():
    print("=== HITRAN CRDS 시뮬레이터 통합 테스트 ===")
    
    # 1. HITRAN 데이터 다운로드
    print("\n1단계: HITRAN 데이터 다운로드")
    hitran_api = HitranAPI()
    hitran_data = hitran_api.download_molecule_data("H2O", 1500, 1520)  # 작은 범위로 테스트
    
    if hitran_data is None:
        print("❌ 데이터 다운로드 실패")
        return
    
    # 2. 주파수 격자 생성
    print("\n2단계: 주파수 격자 생성")
    freq_min = 6580  # cm^-1 (약 1550nm)
    freq_max = 6650  # cm^-1 (약 1530nm)
    frequency_grid = np.linspace(freq_min, freq_max, 10000)  # 고해상도
    
    print(f"   주파수 범위: {freq_min}-{freq_max} cm^-1")
    print(f"   해상도: {(freq_max-freq_min)/len(frequency_grid):.6f} cm^-1")
    
    # 3. 스펙트럼 계산
    print("\n3단계: 스펙트럼 계산")
    calc = SpectrumCalculator()
    
    # CRDS 조건 설정
    spectrum = calc.calculate_absorption_spectrum(
        hitran_data=hitran_data,
        frequency_grid=frequency_grid,
        temperature=296.15,     # 23°C
        pressure=7.0,           # 7기압
        concentration=0.001,    # 0.1% = 1000ppm
        path_length=30000.0     # 30km
    )
    
    # 4. 그래프 그리기
    print("\n4단계: 그래프 생성")
    plt.figure(figsize=(12, 8))
    
    # 파장으로 변환
    wavelength_nm = 1e7 / spectrum['frequency']
    
    plt.subplot(2, 1, 1)
    plt.plot(wavelength_nm, spectrum['transmittance'])
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Transmittance')
    plt.title('H2O Transmittance Spectrum (7atm, 23°C, 1000ppm, 30km)')
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(wavelength_nm, spectrum['absorbance'])
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Absorbance')
    plt.title('H2O Absorption Spectrum')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('output/h2o_spectrum_test.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("✅ 통합 테스트 완료!")
    print("그래프가 저장되었습니다: output/h2o_spectrum_test.png")

if __name__ == "__main__":
    main()