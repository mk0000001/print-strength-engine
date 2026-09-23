"""Screening capacity from a reconstructed section and a supplied allowable stress."""
from math import isfinite
from .process import settings as process_settings

GRAVITY=9.80665
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


def capacity_for_candidate(candidate,directional_mpa,analysis=None,lever_mm=None):
    """Axial and bending screening limits for one reconstructed section.

    The supplied stress is multiplied by the section area and then reduced for
    the printed structure: sparse core, wall count and thin-wall notches. It is
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
    read=process_settings(analysis)
    infill=read['infill_percent'];walls=read['walls'] or 2.;width=read['line_width_mm'] or .4
    efficiency=_pattern_efficiency(read['pattern'])
    thickness=_number(candidate.get('thickness_proxy_mm') or candidate.get('layer_height_for_proxy_mm'))
    knockdown=1.;reasons=[]
    if not is_proxy and thickness and infill is not None:
        # Walls carry the load; the sparse core follows cellular-solid scaling.
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
                            'factor':round(structure,4)})
    if not is_proxy and thickness:
        # A section only a couple of bead widths thick fails at the bead valleys.
        shell_thickness=walls*width
        span=thickness/shell_thickness if shell_thickness else 6.
        notch=.35 if span<=2 else 1. if span>=6 else .35+.65*(span-2)/4
        if notch<1:
            knockdown*=notch
            reasons.append({'variable':'THIN_WALL_NOTCH','thickness_mm':thickness,
                            'shell_thickness_mm':round(shell_thickness,3),'factor':round(notch,4)})
    if is_proxy and axis=='Z' and infill is not None:
        # A layer proxy counts loose beads that are not a connected cross-section.
        cellular=max(.2,.4+.6*(infill/100.)**.5)
        knockdown*=cellular
        reasons.append({'variable':'SPARSE_LAYER_BONDING','infill_percent':infill,'factor':round(cellular,4)})
    allowable*=knockdown
    if is_proxy:
        # A layer proxy sums loose beads across the whole layer; it is not a connected
        # cross-section, so no force may be derived from it.
        return {'section_normal_axis':axis,'allowable_mpa':allowable,'section_area_mm2':area,
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
    axial=area*allowable
    bending=modulus*allowable if modulus else None
    lever=_number(lever_mm)
    # A thin section almost always meets a bending moment before a pure pull.
    bending_force=bending/lever if bending and lever else None
    governing=axial if bending_force is None else min(axial,bending_force)
    mode='AXIAL' if bending_force is None or axial<=bending_force else 'BENDING'
    basis=BASIS_PROXY if is_proxy else BASIS_ENVELOPE
    limitations=['Section area is a proxy from extruded material, not a connected net cross-section.'] if is_proxy else ['Section area comes from the outer-wall envelope.']
    limitations.extend(['Interlayer bonding, notches beyond the bead scale, fatigue and creep are not modelled.',
                        'The bending force assumes a point load at the quoted lever; a longer arm breaks it sooner.'])
    return {'section_normal_axis':axis,'allowable_mpa':allowable,'section_area_mm2':area,
            'axial_capacity_n':axial,'axial_capacity_kgf':axial/GRAVITY,
            'bending_capacity_nmm':bending,'bending_lever_mm':lever,
            'bending_force_n':bending_force,'bending_force_kgf':bending_force/GRAVITY if bending_force else None,
            'governing_capacity_n':governing,'governing_capacity_kgf':governing/GRAVITY,'governing_mode':mode,
            'section_modulus_mm3':modulus,'basis':basis,'is_measured':False,
            'assumes_solid_section':not is_proxy and not reasons,
            'section_knockdown':round(knockdown,4),'section_knockdown_reasons':reasons,
            'limitations':limitations}
