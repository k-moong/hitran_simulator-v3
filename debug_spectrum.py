"""
스펙트럼 계산 디버깅
"""

import numpy as np
from data_handler.hitran_api import HitranAPI

def debug_hitran_data():
    print("=== HITRAN 데이터 디버깅 ===")
    
    # HITRAN 데이터 다운로드
    hitran_api = HitranAPI()
    hitran_data = hitran_api.download_molecule_data("H2O", 1500, 1520)
    
    if hitran_data is None:
        print("❌ 데이터가 없습니다")
        return
    
    print(f"✅ 데이터 개수: {len(hitran_data)}")
    print(f"✅ 데이터 컬럼들: {hitran_data.colnames}")
    
    # 처음 5개 라인 자세히 보기
    print("\n=== 처음 5개 라인 상세 정보 ===")
    for i in range(min(5, len(hitran_data))):
        line = hitran_data[i]
        print(f"라인 {i+1}:")
        print(f"  중심 주파수 (nu): {line['nu']:.4f} cm^-1")
        print(f"  선 강도 (sw): {line['sw']:.4e}")
        print(f"  공기 확장 (gamma_air): {line['gamma_air']:.4e}")
        print(f"  파장: {1e7/line['nu']:.2f} nm")
        print()
    
    # 주파수 범위 확인
    frequencies = [line['nu'] for line in hitran_data]
    print(f"✅ 주파수 범위: {min(frequencies):.1f} - {max(frequencies):.1f} cm^-1")
    print(f"✅ 파장 범위: {1e7/max(frequencies):.1f} - {1e7/min(frequencies):.1f} nm")
    
    # 강한 흡수선 찾기
    intensities = [line['sw'] for line in hitran_data]
    max_intensity = max(intensities)
    print(f"✅ 최대 선 강도: {max_intensity:.4e}")
    
    # 가장 강한 라인 찾기
    max_idx = intensities.index(max_intensity)
    strongest_line = hitran_data[max_idx]
    print(f"✅ 가장 강한 라인:")
    print(f"   주파수: {strongest_line['nu']:.4f} cm^-1")
    print(f"   파장: {1e7/strongest_line['nu']:.2f} nm")
    print(f"   강도: {strongest_line['sw']:.4e}")

if __name__ == "__main__":
    debug_hitran_data()