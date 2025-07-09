"""
유틸리티 함수 단위 테스트
"""
import pytest
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.utils.helpers import to_subscript, to_superscript, isotope_label, get_molecule_label, calculate_resolution_info

class TestHelpers:
    """유틸리티 함수 테스트 클래스"""
    
    def test_to_subscript(self):
        """아래첨자 변환 테스트"""
        assert to_subscript("123") == "₁₂₃"
        assert to_subscript("0") == "₀"
        assert to_subscript("9") == "₉"
        assert to_subscript("") == ""
    
    def test_to_superscript(self):
        """위첨자 변환 테스트"""
        assert to_superscript("123") == "¹²³"
        assert to_superscript("0") == "⁰"
        assert to_superscript("9") == "⁹"
        assert to_superscript("-") == "⁻"
        assert to_superscript("+") == "⁺"
        assert to_superscript("") == ""
    
    def test_isotope_label(self):
        """동위원소 라벨 생성 테스트"""
        # 기본 테스트
        label = isotope_label("H2O", "161")
        assert isinstance(label, str)
        assert len(label) > 0
        
        # mol_id, iso_num이 있는 경우
        label = isotope_label("CO2", "626", mol_id=2, iso_num=1)
        assert isinstance(label, str)
        assert len(label) > 0
    
    def test_get_molecule_label(self):
        """분자 라벨 생성 테스트"""
        # 실제 존재하는 분자 키로 테스트
        from constants import HITRAN_MOLECULES
        
        # 첫 번째 분자로 테스트
        first_key = list(HITRAN_MOLECULES.keys())[0]
        label = get_molecule_label(first_key)
        assert isinstance(label, str)
        assert len(label) > 0
        
        # 두 번째 분자로 테스트
        if len(HITRAN_MOLECULES) > 1:
            second_key = list(HITRAN_MOLECULES.keys())[1]
            label = get_molecule_label(second_key)
            assert isinstance(label, str)
            assert len(label) > 0
    
    def test_calculate_resolution_info(self):
        """해상도 정보 계산 테스트"""
        wl_min, wl_max = 1390.0, 1395.0
        num_points = 10000
        
        resolution_nm, resolution_cm = calculate_resolution_info(wl_min, wl_max, num_points)
        
        # 결과 검증
        assert isinstance(resolution_nm, float)
        assert isinstance(resolution_cm, float)
        assert resolution_nm > 0
        assert resolution_cm > 0
        
        # 계산 정확성 검증
        expected_resolution_nm = (wl_max - wl_min) / num_points
        assert abs(resolution_nm - expected_resolution_nm) < 1e-10
        
        # cm 변환 검증
        expected_resolution_cm = expected_resolution_nm * 1e-7
        assert abs(resolution_cm - expected_resolution_cm) < 1e-10
    
    def test_calculate_resolution_info_edge_cases(self):
        """해상도 정보 계산 엣지 케이스 테스트"""
        # 동일한 파장
        resolution_nm, resolution_cm = calculate_resolution_info(1390.0, 1390.0, 1000)
        assert resolution_nm == 0.0
        assert resolution_cm == 0.0
        
        # 포인트 수가 1인 경우
        resolution_nm, resolution_cm = calculate_resolution_info(1390.0, 1395.0, 1)
        assert resolution_nm == 5.0
        assert resolution_cm == 5e-7

if __name__ == "__main__":
    pytest.main([__file__]) 