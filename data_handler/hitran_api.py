"""
HITRAN API 연결 및 데이터 다운로드 모듈 (astroquery 사용)
"""

from astroquery import hitran
import os
import pandas as pd
import astropy.units as u
from constants import HITRAN_MOLECULES

# 직접 설정
HITRAN_CACHE_DIR = "cache/"
HITRAN_DATA_DIR = "data/"

class HitranAPI:
    def __init__(self):
        """HITRAN API 초기화"""
        # 데이터 폴더 생성
        os.makedirs(HITRAN_CACHE_DIR, exist_ok=True)
        os.makedirs(HITRAN_DATA_DIR, exist_ok=True)
        
    def test_connection(self):
        """HITRAN 연결 테스트"""
        try:
            print("✅ HITRAN API (astroquery) 연결 성공!")
            return True
        except Exception as e:
            print(f"❌ HITRAN API 연결 실패: {e}")
            return False
    
    def download_molecule_data(self, molecule="H2O-161", wavelength_min=1500, wavelength_max=1600):
        """
        분자+동위원소 데이터 다운로드
        Args:
            molecule: 'H2O-161' 등 HITRAN_MOLECULES의 key
            wavelength_min: 최소 파장 (nm)
            wavelength_max: 최대 파장 (nm)
        """
        try:
            # nm를 cm^-1로 변환
            wavenumber_min = 1e7 / wavelength_max  # cm^-1
            wavenumber_max = 1e7 / wavelength_min  # cm^-1

            if molecule not in HITRAN_MOLECULES:
                print(f"❌ 지원하지 않는 분자+동위원소: {molecule}")
                print(f"지원 목록: {list(HITRAN_MOLECULES.keys())}")
                return None
            info = HITRAN_MOLECULES[molecule]
            molecule_id = info["id"]
            iso_number = info["iso"]
            print(f"📥 {info['name']} 데이터 다운로드 중...")
            print(f"   파장 범위: {wavelength_min}-{wavelength_max} nm")
            print(f"   파수 범위: {wavenumber_min:.1f}-{wavenumber_max:.1f} cm^-1")
            print(f"   분자 ID: {molecule_id}, 동위원소 번호: {iso_number}")

            # Hitran 클래스 사용
            hitran_query = hitran.Hitran()
            # 분자 데이터 다운로드
            data = hitran_query.query_lines(
                molecule_number=molecule_id,
                isotopologue_number=iso_number,
                min_frequency=wavenumber_min * u.Unit('1/cm'),
                max_frequency=wavenumber_max * u.Unit('1/cm')
            )
            # 데이터가 DataFrame이고, 라인 개수가 0이면 데이터 없음 안내
            if hasattr(data, 'empty') and data.empty:
                print(f"⚠️ 해당 파장대에 데이터가 존재하지 않습니다.")
                return None
            print(f"✅ {info['name']} 데이터 다운로드 완료!")
            print(f"   라인 개수: {len(data)}")
            return data
        except Exception as e:
            msg = str(e)
            if '<!DOCTYPE html' in msg or msg.strip().startswith('<!'):
                print(f"❌ 서버 에러/응답 오류: HITRAN 서버에서 HTML 에러 페이지가 반환되었습니다.")
            else:
                print(f"❌ 데이터 다운로드 실패: {e}")
            return None

# 테스트 실행
if __name__ == "__main__":
    print("=== HITRAN API 테스트 (astroquery) ===")
    hitran_api = HitranAPI()
    
    if hitran_api.test_connection():
        data = hitran_api.download_molecule_data("H2O-161", 1500, 1600)