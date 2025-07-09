"""
유틸리티 헬퍼 함수들
"""
import re
from typing import Optional, Tuple

def to_subscript(s: str) -> str:
    """숫자를 아래첨자로 변환"""
    sub_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    return s.translate(sub_map)

def to_superscript(s: str) -> str:
    """숫자를 위첨자로 변환"""
    sup_map = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
    return s.translate(sup_map)

def isotope_label(base: str, iso_code: str, mol_id: Optional[int] = None, iso_num: Optional[int] = None) -> str:
    """공식 HITRAN 동위원소 질량수 매핑 기반 분자식 변환"""
    from astroquery.hitran.core import HitranClass
    from constants import HITRAN_MOLECULES
    
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

def get_molecule_label(key: str) -> str:
    """분자 키로부터 한글명과 동위원소 표기를 포함한 라벨 생성"""
    from constants import HITRAN_MOLECULES
    info = HITRAN_MOLECULES[key]
    return f"{info['kor']} ({isotope_label(info['base'], info['iso_code'])})"

def calculate_resolution_info(wl_min: float, wl_max: float, num_points: int) -> Tuple[float, float]:
    """해상도 정보 계산"""
    wavelength_range = wl_max - wl_min
    resolution_nm = wavelength_range / num_points
    resolution_cm = resolution_nm * 1e-7  # nm to cm
    return resolution_nm, resolution_cm 