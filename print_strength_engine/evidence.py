"""Curated primary observations, never a strength-transfer or calibration model.

Sources were checked in reports/strength-empirical-validation-20260925.md.
Keep test property, conditions and derivation attached to every numeric value.
"""
from copy import deepcopy

VERSION = 'PRIMARY_LITERATURE_COMPARISONS_V1'

_CATALOG = [
    {
        'source_id': 'S050', 'doi': '10.3390/ma16134574',
        'source_url': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10342851/fullTextXML',
        'locator': 'Methods/Table 4; Results/Table 6; conclusion',
        'property': 'tensile_strength', 'material_family': 'PLA',
        'material_grade': 'PrimaSelect PLA PRO', 'comparison_variable': 'layer_height_mm',
        'source_context': {'printer': 'Wanhao Duplicator i3 Plus', 'nozzle_c': 210,
                           'bed_c': 60, 'speed_mm_s': 50, 'speed_basis': 'PRINT_SETTING',
                           'infill_percent': 75, 'pattern': 'cubic', 'wall_thickness_mm': .6,
                           'top_bottom_thickness_mm': .6, 'annealing': 'none',
                           'test_standard': 'ASTM D638-14 Type I',
                           'load_axis_relative_to_build': None, 'moisture_condition': None},
        'observations': [
            {'layer_height_mm': .1, 'value_mpa': 32.15,
             'value_kind': 'DERIVED_FROM_REPORTED_VALUES', 'derivation': '33.37 - 1.22 MPa',
             'sd_mpa': None, 'n': None},
            {'layer_height_mm': .2, 'value_mpa': 30.07,
             'value_kind': 'REPORTED', 'sd_mpa': None, 'n': None}],
        'observed_ratio': 30.07 / 32.15, 'ratio_definition': '0.2 mm / 0.1 mm, unannealed',
        'statistical_comparison': 'DISPERSION_NOT_VERIFIED',
        'limitations': ['0.1 mm baseline is derived from rounded reported values.',
                        'Load axis and replicate dispersion were not verified.',
                        'Reported print speed is not a measured commanded-speed median.',
                        'Do not apply this ratio to another grade, part, or process.'],
    },
    {
        'source_id': 'S088', 'doi': '10.3390/app10093170',
        'source_url': 'https://www.mdpi.com/2076-3417/10/9/3170',
        'locator': 'Methods; Table 3 experimental UTS columns (not datasheet columns)',
        'property': 'tensile_strength', 'material_family': 'PEI',
        'material_grade': 'ULTEM 9085', 'comparison_variable': 'orientation',
        'source_context': {'printer': 'Fortus 450mc', 'infill_percent': 100,
                           'walls': 3, 'line_width_mm': .508, 'air_gap_mm': 0,
                           'raster_angles_deg': [-45, 45],
                           'test_standard': 'ASTM D638-14 Type I',
                           'crosshead_speed_mm_min': 5, 'nozzle_c': None,
                           'layer_height_mm': None, 'speed_mm_s': None},
        'observations': [
            {'orientation': 'XY', 'load_axis': 'X', 'value_mpa': 65.9,
             'sd_mpa': .7, 'n': 5, 'tukey_subset': 'b', 'value_kind': 'REPORTED'},
            {'orientation': 'XZ', 'load_axis': 'X', 'value_mpa': 73.,
             'sd_mpa': 1.3, 'n': 5, 'tukey_subset': 'b', 'value_kind': 'REPORTED'}],
        'observed_ratio': 65.9 / 73., 'ratio_definition': 'XY / XZ',
        'statistical_comparison': 'SAME_TUKEY_GROUP',
        'limitations': ['Orientation labels retain largest-face plane as well as longitudinal axis.',
                        'Different means in the same Tukey group do not establish statistical significance.',
                        'These observations do not validate a material reference or transfer model.'],
    },
]

for _family, _mean, _sd, _n in [('PLA', 25.74, 1.03, 10), ('ABS', 23.01, 1.63, 10), ('PC', 30.16, 1.64, 9)]:
    _CATALOG.append({
        'source_id': 'S028', 'doi': '10.1016/j.jmrt.2022.12.147',
        'source_url': 'https://doi.org/10.1016/j.jmrt.2022.12.147', 'locator': 'Table 2',
        'property': 'interlayer_shear_strength', 'material_family': _family,
        'material_grade': None, 'comparison_variable': None,
        'source_context': {'test_method': 'necking-shaped pure shear', 'print_surface_angle_deg': 90,
                           'printer': None, 'nozzle_c': None, 'layer_height_mm': None,
                           'speed_mm_s': None, 'infill_percent': None},
        'observations': [{'value_mpa': _mean, 'sd_mpa': _sd, 'n': _n, 'value_kind': 'REPORTED'}],
        'observed_ratio': None, 'ratio_definition': None,
        'statistical_comparison': 'REPORTED_MEAN_AND_STANDARD_DEVIATION',
        'limitations': ['Interlayer shear cannot be substituted for Z tensile or bending strength.',
                        'Grade and deposition conditions have not been independently verified.'],
    })


def literature_comparisons(target_context, *, property_name='tensile_strength'):
    """Return same-family observations with applicability gaps, never a factor.

    Callers must request shear explicitly. Exact grade text is only an identity
    match; it does not establish matching test conditions or validated transfer.
    No material family is inferred from a slicer profile or an unknown grade.
    """
    target = deepcopy(target_context) if isinstance(target_context, dict) else {}
    family = str(target.get('material_family') or '').strip().upper()
    grade = str(target.get('material_grade') or '').strip().casefold()
    rows = []
    for entry in _CATALOG:
        if entry['material_family'] != family or entry['property'] != property_name:
            continue
        row = deepcopy(entry)
        source_grade = str(row['material_grade'] or '').strip().casefold()
        row.update({'evidence_version': VERSION, 'status': 'LITERATURE_COMPARISON_ONLY',
                    'confidence': 'OBSERVATIONS_VERIFIED_TRANSFER_UNVALIDATED',
                    'applied': False, 'is_prediction': False, 'transfer_factor': None,
                    'material_match': 'EXACT_GRADE_NAME_ONLY' if grade and source_grade == grade
                                      else 'SAME_FAMILY_NOT_GRADE_MATCH',
                    'target_context': deepcopy(target), 'condition_mismatches': [],
                    'unknown_conditions': []})
        for key, source_value in row['source_context'].items():
            target_value = target.get(key)
            if source_value is None or target_value is None:
                row['unknown_conditions'].append(key)
            elif source_value != target_value:
                row['condition_mismatches'].append({'field': key, 'source': source_value, 'target': target_value})
        variable = row['comparison_variable']
        if variable:
            observed = [o[variable] for o in row['observations']]
            row['target_within_observed_levels'] = target.get(variable) in observed
            row['applicability'] = ('OBSERVED_LEVEL_ONLY_NOT_VALIDATED_TRANSFER'
                                    if row['target_within_observed_levels'] else
                                    'TARGET_LEVEL_UNKNOWN' if target.get(variable) is None else
                                    'OUTSIDE_OBSERVED_LEVELS')
            if not row['target_within_observed_levels']:
                row['observed_ratio'] = None
        else:
            row['applicability'] = 'PROPERTY_OBSERVATION_ONLY'
        rows.append(row)
    return rows
