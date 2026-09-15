from math import isfinite
from statistics import median


def weakest_layer_candidate(profile, *, exclude_end_layers=2):
    """Rank interior Z interfaces using observed model extrusion volume.

    The volume/height ratio is a material-area proxy. It does not resolve
    perimeter topology, void connectivity, stress concentration or load path.
    No failure load or MPa strength may be inferred from this function alone.
    """
    from .candidates import rank_layers
    return rank_layers(profile,exclude_end_layers)

def weakest_section(sections, force_n, moment_nmm=0):
    """First local limit under uniform axial force and a supplied moment.

    Sections must be reconstructed by the caller. This is a net-section
    screening model, not FEA, buckling, fatigue or crack propagation.
    """
    force_n=float(force_n); moment_nmm=float(moment_nmm)
    if not isfinite(force_n) or force_n<=0 or not isfinite(moment_nmm):
        raise ValueError('POSITIVE_TENSILE_LOAD_REQUIRED')
    candidates=[]
    for section in sections:
        area=float(section['area_mm2'])
        strength=float(section['allowable_mpa'])
        if not all(isfinite(x) and x>0 for x in (area,strength)):
            raise ValueError('INVALID_SECTION')
        stress=force_n/area
        if moment_nmm:
            modulus=float(section['section_modulus_mm3'])
            if not isfinite(modulus) or modulus<=0: raise ValueError('INVALID_SECTION_MODULUS')
            stress+=abs(moment_nmm)/modulus
        candidates.append({'section_id':section['id'],'position_mm':section.get('position_mm'),
                           'stress_mpa':stress,'failure_index':stress/strength,
                           'load_multiplier_to_limit':strength/stress})
    if not candidates: raise ValueError('SECTIONS_REQUIRED')
    weakest=max(candidates,key=lambda x:x['failure_index'])
    return {'status':'NET_SECTION_SCREENING','weakest_section':weakest,
            'capacity_at_proportional_loading_n':force_n*weakest['load_multiplier_to_limit'],
            'limitations':['Supplied section geometry and allowable stress must be validated.',
                           'No stress concentrations, interlayer delamination, buckling, creep or fatigue model.']}
