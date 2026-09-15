"""Literature-normalized infill comparisons; never a net-section load model."""
from math import isfinite

# Ben Amor, Chatti & Louhichi (2024), section 4.2, Table 6.
# Reported stress values for Raise3D Premium PLA. Other materials in that
# paper are NOT used to manufacture an unsupported infill curve.
PLA_POINTS=((10.,19.),(30.,21.),(60.,24.),(80.,27.),(100.,34.))
SOURCE='https://doi.org/10.35219/awet.2024.10'


def infill_response(material,density_percent,*,reference_mpa=None,pattern=None,walls=None):
    density=float(density_percent)
    if not isfinite(density) or not 0<=density<=100:raise ValueError('INVALID_INFILL_DENSITY')
    result={'status':'NO_MATCHING_STUDY','material':material,'infill_percent':density,
            'relative_strength_ratio':None,'comparison_mpa':None,'z_correction':None,
            'apply_to_material_area':False,'calibrated_to_current_part':False,
            'current_pattern':pattern,'current_walls':walls,'confidence':'LOW'}
    if material.upper()!='PLA':return result
    result.update(source_url=SOURCE,source_table='Table 6 / Section 4.2',study_material='Raise3D Premium PLA',
                  study_density_range_percent=[10,100],reference_density_percent=100,
                  method='PIECEWISE_LINEAR_INTERPOLATION_OF_WITHIN_STUDY_STRESS_RATIO',
                  matched_pattern_and_walls=False,
                  limitations=['Study-relative comparison; current pattern, walls, brand and conditioning are not calibrated.',
                               'Do not apply this ratio again to measured extruded material area.',
                               'No Z-direction, failure-load or safety-factor prediction is provided.'])
    if density<10:result['status']='OUTSIDE_STUDY_RANGE';return result
    measured=34.
    for (a,x),(b,y) in zip(PLA_POINTS,PLA_POINTS[1:]):
        if a<=density<=b:measured=x+(y-x)*(density-a)/(b-a);break
    ratio=measured/34.
    result.update(status='LITERATURE_COMPARISON',relative_strength_ratio=ratio,study_interpolated_stress_mpa=measured)
    if reference_mpa is not None:
        reference=float(reference_mpa)
        if not isfinite(reference) or reference<=0:raise ValueError('INVALID_REFERENCE_STRESS')
        result.update(basis_reference_mpa=reference,comparison_mpa=reference*ratio)
    return result
