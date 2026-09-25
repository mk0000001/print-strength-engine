"""Screening capacity from a reconstructed section and a supplied allowable stress."""
from math import isfinite
from .process import settings as process_settings

GRAVITY=9.80665
VERSION='CAPACITY_SCENARIO_V4_GEOMETRY_QUALIFIED'
BASIS_ENVELOPE='SOLID_ENVELOPE_SECTION_TIMES_MATERIAL_REFERENCE'
BASIS_PROXY='GCODE_MATERIAL_EXTRUSION_PROXY_AREA_TIMES_MATERIAL_REFERENCE'
PATTERN_EFFICIENCY={'gyroid':.95,'honeycomb':.9,'tri-hexagon':.88,'cubic':.85,'adaptive':.8,'grid':.8,
                    'rectilinear':.75,'zigzag':.72,'line':.7,'lightning':.45,'concentric':.6}
# These are screening assumptions, not experimentally calibrated pattern factors.
# Aligned rectilinear retains the previous rectilinear-family assumption; it is
# not asserted to have the same directional strength as alternating rectilinear.
PATTERN_ALIASES={'trihexagon':'tri-hexagon','adaptivecubic':'adaptive','lines':'line',
                 'alignedrectilinear':'rectilinear'}
CORE_EXPONENT=1.4


def _number(value,maximum=1e9):
    try:value=float(value)
    except (TypeError,ValueError):return None
    return value if isfinite(value) and 0<value<=maximum else None


def _pattern_key(name):
    # Slicers vary separators and spelling; a substring is not an equivalent
    # pattern (notably adaptivecubic must not match cubic first).
    normalized=''.join(char for char in str(name or '').lower() if char not in '-_ ')
    key=PATTERN_ALIASES.get(normalized,normalized)
    return key if key in PATTERN_EFFICIENCY else None


def _pattern_efficiency(name):
    return PATTERN_EFFICIENCY.get(_pattern_key(name),.85)


def capacity_for_candidate(candidate,directional_mpa,analysis=None,lever_mm=None,*,reference_area_basis='UNKNOWN'):
    """Uncalibrated axial and bending scenarios for an envelope section.

    The supplied stress is multiplied by the section area and then reduced for
    an assumed printed structure: rectangular shell and sparse core. It is
    not a measured breaking load and models no fatigue, creep or buckling.
    """
    if not isinstance(directional_mpa,dict):return None
    axis=str(candidate.get('section_normal_axis') or candidate.get('axis') or 'Z').upper()
    if axis not in ('X','Y','Z'):return None
    area=_number(candidate.get('min_section_area_mm2'));is_proxy=False
    if area is None:
        area=_number(candidate.get('material_area_proxy_mm2'));is_proxy=True
    allowable=_number(directional_mpa.get(axis),1e5)
    if area is None or allowable is None:return None
    reference_stress=allowable
    if reference_area_basis not in ('UNKNOWN','GROSS_ENVELOPE','NET_MATERIAL','INTERLAYER_CONTACT'):
        raise ValueError('INVALID_STRESS_AREA_BASIS')
    area_basis_compatible=reference_area_basis in ('UNKNOWN','GROSS_ENVELOPE')
    read=process_settings(analysis)
    infill=read['infill_percent'];walls=read['walls'];width=read['line_width_mm']
    efficiency=1. if infill==100 else _pattern_efficiency(read['pattern'])
    thickness=_number(candidate.get('thickness_proxy_mm') or candidate.get('layer_height_for_proxy_mm'))
    knockdown=1.;reasons=[]
    structure_known=infill==100 or (infill is not None and walls is not None and width is not None and thickness is not None)
    if not is_proxy and thickness and infill is not None and walls is not None and width is not None:
        # Hypothetical rectangular shell/core, not measured deposited topology.
        core_width = max(0., area/thickness - 2*walls*width) if thickness else 0.
        core_thickness = max(0., thickness - 2*walls*width)
        core = core_width * core_thickness
        shell = max(0., area - core)
        structure=(shell+core*efficiency*(infill/100.)**CORE_EXPONENT)/area
        if structure<1:
            knockdown*=structure
            reasons.append({'variable':'SPARSE_CORE_AND_WALLS','infill_percent':infill,'pattern':read['pattern'],
                            'walls':walls,'pattern_efficiency':efficiency,
                            'pattern_efficiency_key':_pattern_key(read['pattern']),
                            'pattern_efficiency_fallback':_pattern_key(read['pattern']) is None,
                            'pattern_efficiency_basis':'ASSUMED_PATTERN_FAMILY_NOT_CALIBRATED',
                            'core_exponent':CORE_EXPONENT,'empirically_validated':False,
                            'factor':round(structure,4)})
    # Removed an uncalibrated notch multiplier that made additional walls weaker.
    # Layer-volume comparisons cannot identify bonding stress: no invented
    # density-to-weld multiplier is attached even when no force is displayed.
    allowable*=knockdown
    if is_proxy:
        # A layer proxy sums loose beads across the whole layer; it is not a connected
        # cross-section, so no force may be derived from it.
        return {'model_version':VERSION,'is_failure_prediction':False,'empirically_validated':False,
                'calibration_status':'NOT_A_MECHANICAL_CAPACITY','calibration_source_ids':[],
                'structure_model':'LAYER_EXTRUSION_VOLUME_PROXY',
                'calculation_status':'GEOMETRY_COMPARISON_ONLY','material_reference_mpa':reference_stress,
                'section_normal_axis':axis,'allowable_mpa':None,'section_area_mm2':area,
                'axial_capacity_n':None,'axial_capacity_kgf':None,
                'bending_capacity_nmm':None,'bending_lever_mm':None,
                'bending_force_n':None,'bending_force_kgf':None,
                'governing_capacity_n':None,'governing_capacity_kgf':None,
                'governing_mode':'LAYER_COMPARISON_ONLY',
                'section_modulus_mm3':None,'basis':BASIS_PROXY,'is_measured':False,
                'assumes_solid_section':False,
                'section_knockdown':round(knockdown,4),'section_knockdown_reasons':reasons,
                'limitations':['The area is the extruded material summed over the layer, not a connected cross-section.',
                               'Use it only to compare layers with each other; it yields no breaking force.']}
    modulus=_number(candidate.get('section_modulus_mm3'))
    axial=area*allowable if structure_known and area_basis_compatible else None
    # An area fraction cannot correct bending inertia: material position matters.
    # Without deposited-road reconstruction, only a nominal full-infill envelope
    # scenario has a usable modulus. A wall-only inferred rectangle is insufficient.
    bending=modulus*allowable if modulus and infill==100 and area_basis_compatible else None
    lever=_number(lever_mm)
    # Only the explicitly assumed moment arm defines this scenario.
    bending_force=bending/lever if bending and lever else None
    governing=min(axial,bending_force) if axial is not None and bending_force is not None else None
    mode=('AXIAL' if axial<=bending_force else 'BENDING') if governing is not None else 'INCOMPLETE_LOAD_CASE'
    basis=BASIS_PROXY if is_proxy else BASIS_ENVELOPE
    limitations=['Section area is a proxy from extruded material, not a connected net cross-section.'] if is_proxy else ['Section area comes from the outer-wall envelope.']
    limitations.extend(['Interlayer bonding, stress concentrations, fatigue and creep are not solved.',
                        'Nominal 100% infill does not establish zero voids or bonded contact area.',
                        'Coupon nominal stress is not intrinsic weld stress; no contact fraction is inferred.',
                        'Sparse axial reduction assumes a rectangular shell/core; it is not reconstructed deposited material.',
                        'Pattern multipliers and the core exponent are uncalibrated scenario assumptions.',
                        'Sparse/unknown infill bending is withheld because effective section inertia is unknown.',
                        'The bending force is a hypothetical point-load scenario, not a known restraint or failure load.'])
    return {'model_version':VERSION,'is_failure_prediction':False,'structure_settings':read,
            'reference_stress_area_basis':reference_area_basis,
            'section_geometry_status':'OUTER_ENVELOPE_ONLY',
            'effective_load_bearing_area_mm2':None,'bonded_contact_area_mm2':None,
            'solid_section_verified':False,
            'assessment_gaps':['VOID_AND_CONTACT_GEOMETRY_UNKNOWN',
                               'LOCAL_THERMAL_HISTORY_UNKNOWN',
                               'NOTCH_AND_CRACK_FAILURE_NOT_SOLVED',
                               'ACTUAL_LOAD_AND_RESTRAINTS_UNKNOWN'],
            'calibration_status':'UNVALIDATED_ENGINEERING_ASSUMPTION','calibration_source_ids':[],
            'structure_model':('UNKNOWN_STRUCTURE' if not structure_known else
                               'NOMINAL_FULL_INFILL_ENVELOPE' if infill==100 else 'ASSUMED_RECTANGULAR_SHELL_CORE'),
            'empirically_validated':False,'material_reference_mpa':reference_stress,
            'scenario_adjusted_stress_mpa':allowable if structure_known and area_basis_compatible else None,
            'prediction_interval_n':None,
            'validation':{'status':'NO_MATCHED_PART_FAILURE_TESTS','property':'AXIAL_TENSILE_SCENARIO',
                          'source_grade_transfer_validated':False,'process_transfer_validated':False,
                          'section_model_validated_against_printed_coupons':False,
                          'uncertainty_quantified':False},
            'calculation_status':('INCOMPATIBLE_STRESS_AREA_BASIS' if not area_basis_compatible else
                                  'UNCALIBRATED_SCENARIO' if structure_known else 'MISSING_STRUCTURE_SETTINGS'),
            'section_normal_axis':axis,'allowable_mpa':allowable,'section_area_mm2':area,
            'axial_capacity_n':axial,'axial_capacity_kgf':axial/GRAVITY if axial is not None else None,
            'bending_capacity_nmm':bending,'bending_lever_mm':lever,
            'bending_force_n':bending_force,'bending_force_kgf':bending_force/GRAVITY if bending_force else None,
            'governing_capacity_n':governing,'governing_capacity_kgf':governing/GRAVITY if governing is not None else None,'governing_mode':mode,
            'section_modulus_mm3':modulus,'basis':basis,'is_measured':False,
            'assumes_solid_section':infill==100,
            'section_knockdown':round(knockdown,4),'section_knockdown_reasons':reasons,
            'limitations':limitations}
