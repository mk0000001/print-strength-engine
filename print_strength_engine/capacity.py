"""Screening capacity from a reconstructed section and a supplied allowable stress."""
from math import isfinite

GRAVITY=9.80665
BASIS='SOLID_ENVELOPE_SECTION_TIMES_MATERIAL_REFERENCE'


def _number(value,maximum=1e9):
    try:value=float(value)
    except (TypeError,ValueError):return None
    return value if isfinite(value) and 0<value<=maximum else None


def capacity_for_candidate(candidate,directional_mpa):
    """Axial and bending screening limits for one reconstructed thin section.

    This multiplies a geometric section by a caller-supplied material reference
    stress. It is not a measured breaking load and does not model infill,
    interlayer bonding, stress concentration, buckling, creep or fatigue.
    """
    if not isinstance(directional_mpa,dict):return None
    axis=str(candidate.get('section_normal_axis') or '').upper()
    if axis not in ('X','Y','Z'):return None
    area=_number(candidate.get('min_section_area_mm2'))
    allowable=_number(directional_mpa.get(axis),1e5)
    if area is None or allowable is None:return None
    modulus=_number(candidate.get('section_modulus_mm3'))
    axial=area*allowable
    return {'section_normal_axis':axis,'allowable_mpa':allowable,'section_area_mm2':area,
            'axial_capacity_n':axial,'axial_capacity_kgf':axial/GRAVITY,
            'bending_capacity_nmm':modulus*allowable if modulus else None,
            'section_modulus_mm3':modulus,'basis':BASIS,'is_measured':False,
            'assumes_solid_section':True,
            'limitations':['Section area comes from the outer-wall envelope and assumes a solid cross-section.',
                           'Sparse infill, interlayer bonding, notches and fatigue lower the real limit.',
                           'Bending limits require the load lever arm supplied by the reader.']}
