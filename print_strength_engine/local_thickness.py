"""Finished-part thin-region screening from outer contours; not FEA or failure load."""
import math
VERSION='LOCAL_OUTER_ENVELOPE_V2_SECTION'
AXIS_NAMES=('Z','Y','X')


def section_metrics(solid,part,spacing,threshold_mm,axis=None):
    """Minimum net section perpendicular to the region principal axis."""
    import numpy as np
    # The load axis follows the whole connected region, never a sampling bucket.
    axis=int(np.argmax(np.ptp(part,axis=0))) if axis is None else int(axis)
    pad=int(math.ceil(threshold_mm/spacing))+1
    low=np.maximum(part.min(axis=0)-pad,0);high=np.minimum(part.max(axis=0)+pad+1,solid.shape)
    window=solid[low[0]:high[0],low[1]:high[1],low[2]:high[2]]
    counts=window.sum(axis=tuple(i for i in range(3) if i!=axis))
    stations=np.flatnonzero(counts>0)
    if not len(stations):return None
    start=max(0,int(part.min(axis=0)[axis])-int(low[axis]));end=min(len(counts)-1,int(part.max(axis=0)[axis])-int(low[axis]))
    inside=stations[(stations>=start)&(stations<=end)]
    if not len(inside):inside=stations
    station=int(inside[np.argmin(counts[inside])])
    cells=np.argwhere(np.take(window,station,axis=axis))
    if not len(cells):return None
    area=float(len(cells))*spacing*spacing
    offsets=(cells-cells.mean(axis=0))*spacing
    modulus=None
    for column in range(offsets.shape[1]):
        distance=float(np.abs(offsets[:,column]).max())
        if distance<=0:continue
        second=float((offsets[:,column]**2).sum())*spacing*spacing
        value=second/distance
        modulus=value if modulus is None else min(modulus,value)
    return {'min_section_area_mm2':round(area,4),'section_normal_axis':AXIS_NAMES[axis],
            'section_modulus_mm3':round(modulus,4) if modulus else None,
            'section_station_mm':round(float((int(low[axis])+station+.5)*spacing),3),
            'section_basis':'MIN_SOLID_VOXEL_COUNT_PERPENDICULAR_TO_PRINCIPAL_AXIS'}


def screen_solid(solid,origin_xyz,spacing_mm,*,threshold_mm=2.4,max_candidates=6):
    import numpy as np
    from scipy import ndimage as ndi
    spacing=float(spacing_mm)
    if spacing<=0 or not math.isfinite(spacing):raise ValueError('INVALID_GRID_SPACING')
    solid=np.asarray(solid,dtype=bool)
    if solid.ndim!=3 or solid.size>4_000_000:raise ValueError('LOCAL_GEOMETRY_GRID_LIMIT')
    base={'version':VERSION,'status':'NO_THIN_REGION_DETECTED','candidates':[],
          'resolution_mm':spacing,'threshold_mm':threshold_mm,'basis':'OUTER_CONTOUR_ENVELOPE_DISTANCE_RIDGE',
          'is_failure_prediction':False,'support_included':False,'confidence':'GEOMETRIC_SCREENING',
          'limitations':['Outer-envelope thickness is a voxel proxy; this does not model infill bonding or failure load.',
                         'Thickness uncertainty is at least one voxel plus contour/line-width uncertainty.',
                         'Load direction, restraints, stress concentration, anisotropy and fatigue are not solved.']}
    if not solid.any():return {**base,'status':'NO_MODEL_ENVELOPE'}
    distance=ndi.distance_transform_edt(np.pad(solid,1),sampling=spacing)[1:-1,1:-1,1:-1].astype(np.float32)
    maximum=ndi.maximum_filter(distance,size=3,mode='constant')
    ridge=solid&(distance>=maximum-1e-5)&(distance>0)&(2*distance<=threshold_mm+1e-5)
    del maximum
    # Only medial ridges qualify: ordinary surfaces of a thick solid are not thin sections.
    grown=ndi.binary_dilation(ridge)&solid
    labels,count=ndi.label(grown,structure=np.ones((3,3,3),dtype=bool))
    objects=ndi.find_objects(labels);candidates=[]
    overall_span=max(np.asarray(solid.shape)*spacing);bin_mm=max(10.,overall_span/8)
    for label,slices in enumerate(objects,1):
        if slices is None:continue
        local=np.argwhere((labels[slices]==label)&ridge[slices])
        if len(local)<8:continue
        points=local+np.array([s.start for s in slices])
        axis=int(np.argmax(np.ptp(points,axis=0)));bins=np.floor((points[:,axis]-points[:,axis].min())*spacing/bin_mm).astype(int)
        for bucket in np.unique(bins):
            part=points[bins==bucket]
            if len(part)<8:continue
            span=(np.ptp(part,axis=0)+1)*spacing
            if max(span)<3:continue
            thickness=2*distance[tuple(part.T)]
            proxy=float(np.percentile(thickness,25))
            if max(span)/max(proxy,spacing)<3:continue
            median=np.median(part,axis=0)
            eligible=np.flatnonzero(thickness<=proxy+1e-5)
            index=int(eligible[np.argmin(np.sum((part[eligible]-median)**2,axis=1))])
            proxy=float(thickness[index])
            position=(np.asarray(origin_xyz)+(part[index][::-1]+.5)*spacing).tolist()
            low=(np.asarray(origin_xyz)+part.min(axis=0)[::-1]*spacing).tolist()
            high=(np.asarray(origin_xyz)+(part.max(axis=0)[::-1]+1)*spacing).tolist()
            candidates.append({'kind':'LOCAL_THIN_SECTION','position_mm':position,'z_mm':position[2],
                'bounds_mm':[[float(a),float(b)] for a,b in zip(low,high)],'thickness_proxy_mm':round(proxy,3),
                'extent_mm':span[::-1].tolist(),'ridge_voxels':len(part),'resolution_mm':spacing,
                'reason':'THIN_FINISHED_PART_ENVELOPE','load_capacity_n':None,
                'screening_score':float(max(span)/max(proxy,spacing))})
            section=section_metrics(solid,part,spacing,threshold_mm,axis)
            if section:candidates[-1].update(section)
    ordered=sorted(candidates,key=lambda c:(c['thickness_proxy_mm'],-c['screening_score'],-c['ridge_voxels']))
    chosen=[]
    for c in ordered:
        if any(math.dist(c['position_mm'],p['position_mm'])<max(5.,bin_mm*.7) for p in chosen):continue
        c.update(rank=len(chosen)+1,region_id=f"local-thin-{len(chosen)+1}");chosen.append(c)
        if len(chosen)>=max_candidates:break
    return {**base,'status':'THIN_REGIONS_FOUND' if chosen else base['status'],'candidates':chosen,
            'occupied_voxels':int(solid.sum()),'medial_thin_voxels':int(ridge.sum()),'component_count':count}


def screen_contour_layers(layers,bounds,*,resolution_mm=.4,max_voxels=4_000_000,progress=None,cancelled=None):
    import numpy as np
    import shapely
    from shapely.geometry import Polygon,LineString
    low=np.array([v[0] for v in bounds],dtype=float);high=np.array([v[1] for v in bounds],dtype=float)
    if not np.isfinite([low,high]).all() or (high<=low).any():raise ValueError('INVALID_MODEL_BOUNDS')
    spacing=float(resolution_mm)
    while int(np.prod(np.ceil((high-low)/spacing).astype(int)+6))>max_voxels:spacing*=1.1
    if spacing>1:return {'version':VERSION,'status':'RESOLUTION_LIMIT','candidates':[],'resolution_mm':spacing,'support_included':False}
    origin=low-3*spacing;shape=(np.ceil((high-low)/spacing).astype(int)+6)[::-1]
    solid=np.zeros(tuple(shape),dtype=bool)
    xs=origin[0]+(np.arange(shape[2])+.5)*spacing
    ys=origin[1]+(np.arange(shape[1])+.5)*spacing
    def raster_into(target,geometry,parity=False):
        # Outside the exact geometry bounds contains_xy is always false. Keep
        # the original grid coordinates (including boundary rounding) unchanged.
        if geometry.is_empty:return
        x0,y0,x1,y1=geometry.bounds
        left=np.searchsorted(xs,x0,side='left')
        right=np.searchsorted(xs,x1,side='right')
        bottom=np.searchsorted(ys,y0,side='left')
        top=np.searchsorted(ys,y1,side='right')
        if left>=right or bottom>=top:return
        mask=shapely.contains_xy(geometry,xs[None,left:right],ys[bottom:top,None])
        view=target[bottom:top,left:right]
        if parity:view^=mask
        else:view|=mask
    mapping=[];closed_count=open_count=invalid_count=0
    for index,row in enumerate(layers):
        if cancelled and cancelled():raise RuntimeError('ANALYSIS_CANCELLED')
        if progress and index%20==0:progress(index)
        parity=np.zeros((len(ys),len(xs)),dtype=bool);walls=np.zeros_like(parity)
        for run_index,run in enumerate(row.get('runs',[])):
            if run_index%32==0 and cancelled and cancelled():raise RuntimeError('ANALYSIS_CANCELLED')
            points=run['points'];width=float(run['width_mm'])
            if len(points)<2 or not .02<=width<=5:continue
            line=LineString(points)
            if len(points)>=4 and math.dist(points[0],points[-1])<=max(.05,width*.5):
                polygon=Polygon(points)
                if polygon.area>width*width:
                    if not polygon.is_valid:invalid_count+=1;polygon=shapely.make_valid(polygon)
                    raster_into(parity,polygon,parity=True);closed_count+=1
                else:open_count+=1
            else:open_count+=1
            raster_into(walls,line.buffer(width/2,cap_style=2,join_style=2))
        plane=parity|walls
        z=float(row['z_mm']);h=float(row.get('height_mm') or .2)
        start=max(0,int(math.floor((z-h-origin[2])/spacing)))
        end=min(shape[0]-1,int(math.floor((z-origin[2]-1e-8)/spacing)))
        for zi in range(start,end+1):solid[zi]|=plane
        mapping.append((z,row['layer_number']))
    result=screen_solid(solid,origin.tolist(),spacing)
    for candidate in result['candidates']:
        candidate['layer_number']=min(mapping,key=lambda row:abs(row[0]-candidate['z_mm']))[1]
    result.update(coverage={'outer_layer_count':len(mapping),'closed_contours':closed_count,'open_runs':open_count,'repaired_contours':invalid_count},
                  grid_shape_zyx=[int(v) for v in shape],geometry_basis='EVEN_ODD_OUTER_WALL_ENVELOPE_WITH_LINE_WIDTH_BUFFER',
                  infill_voids_ignored=True,estimated_not_measured=True)
    return result
