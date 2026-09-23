"""Separated internal constriction candidates; geometric screening, not failure prediction."""
from math import ceil,isfinite
from statistics import median

SCREENING_VERSION='INTERNAL_CONSTRICTIONS_V2'


def rank_layers(profile,exclude_end_layers=2,max_candidates=6):
    empty={'screening_version':SCREENING_VERSION,'weak_candidates':[],'weakest_section':None,'axis':'Z',
           'basis':'INTERNAL_AREA_RELATIVE_TO_BOTH_NEIGHBORHOODS','status':'INSUFFICIENT_PROFILE'}
    if profile.get('incomplete'):return {**empty,'reason':'PROFILE_TRUNCATED'}
    rows=[]
    for row in profile.get('layers') or []:
        try:z=float(row['z_mm']);volume=float(row['volume_mm3'])
        except (KeyError,TypeError,ValueError):continue
        if isfinite(z) and isfinite(volume) and volume>0:rows.append((z,volume,row.get('layer_number')))
    rows.sort(key=lambda row:row[0]);n=len(rows)
    if n<2*exclude_end_layers+3:return {**empty,'reason':'TOO_FEW_MODEL_LAYERS'}
    gaps=[b[0]-a[0] for a,b in zip(rows,rows[1:])];positive=[h for h in gaps if h>0]
    if not positive:return {**empty,'reason':'LAYER_HEIGHT_UNAVAILABLE'}
    nominal=median(positive);areas=[];heights=[]
    for i,row in enumerate(rows):
        h=gaps[i-1] if i and 0<gaps[i-1]<=2*nominal else nominal
        heights.append(h);areas.append(row[1]/h)
    total=sum(r[1] for r in rows);above=total;remaining=[]
    for row in rows:above-=row[1];remaining.append(max(0,above/total))
    windows=sorted({min(60,max(2,round(n*.025))),min(180,max(4,round(n*.075)))})
    candidates=[];terminal_rejected=0
    for i in range(max(2,exclude_end_layers),n-max(2,exclude_end_layers)):
        comparisons=[]
        for window in windows:
            left=areas[max(0,i-window):i];right=areas[i+1:min(n,i+window+1)]
            if len(left)<window or len(right)<window:continue
            reference=min(median(left),median(right))
            comparisons.append((areas[i]/reference,reference,window))
        if not comparisons:continue
        ratio,reference,window=min(comparisons)
        if ratio>=.98:continue
        # This is a relevance heuristic, not a calculation of the load carried above.
        if remaining[i]<.02:terminal_rejected+=1;continue
        candidates.append({'_index':i,'z_mm':rows[i][0],'layer_number':rows[i][2],
            'material_area_proxy_mm2':areas[i],'observed_model_volume_mm3':rows[i][1],
            'layer_height_for_proxy_mm':heights[i],'neighbor_area_proxy_mm2':reference,
            'relative_area_ratio':ratio,'material_above_fraction':remaining[i],
            'neighborhood_layers':window,'reason':'INTERNAL_LOCAL_CONSTRICTION' if ratio<.85 else 'MILD_LOCAL_CONSTRICTION'})
    separation=max(3,ceil(n*.035));selected=[]
    for candidate in sorted(candidates,key=lambda row:(row['relative_area_ratio'],row['material_area_proxy_mm2'],row['z_mm'])):
        if any(abs(candidate['_index']-other['_index'])<separation for other in selected):continue
        selected.append(candidate)
        if len(selected)>=max_candidates:break
    for rank,candidate in enumerate(selected,1):
        candidate.pop('_index');candidate.update(rank=rank,region_id=f"neck-{rank}")
    return {**empty,'status':'GEOMETRIC_CANDIDATE_ONLY' if selected else 'NO_DISTINCT_INTERNAL_CONSTRICTION',
            'weakest_section':selected[0] if selected else None,'weak_candidates':selected,'evaluated_layers':n,
            'terminal_candidates_excluded':terminal_rejected,
            'screening_parameters':{'minimum_narrowing_fraction':.02,'minimum_material_above_fraction':.02,
                                    'candidate_separation_layers':separation,'max_candidates':max_candidates,'neighborhood_windows':windows},
            'limitations':['Ranking compares model extrusion-volume/height against neighboring layers; it is not a load-capacity ranking.',
                           'End-feature filtering and neighborhood sizes are screening heuristics, not validated physical thresholds.',
                           'Load direction, restraints, separate objects, XY load paths, notches and bonding are not resolved.']}
