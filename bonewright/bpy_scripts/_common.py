"""bpy 스크립트 공통: 인자(JSON 파일) 읽기, 결과 JSON 쓰기, 메시 불러오기. Blender 안(bpy)에서만 실행된다."""
import bpy, json, os, sys


def args():
    """마지막 인자로 넘어온 JSON 파일을 읽는다."""
    with open(os.environ.get("BW_PARAMS") or sys.argv[-1], encoding="utf-8") as f:
        return json.load(f)


def done(result: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("BW_RESULT " + path)


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)


IMPORT_INFO = {}   # import_mesh 가 정규화한 내용(보고서용)


def import_mesh(path: str, facing: str = "auto"):
    """어떤 파일이 와도 '리깅할 메시 하나'로 만든다: 스킨된 메시는 REST 자세로 굽고 아마추어·엠프티·보조 구체를 버린다.
    조각을 합치고, cm 단위면 m 로, 좌우 중심을 x=0 으로, 앞이 +Y 면 -Y 로 돌린다. 정규화 내용은 IMPORT_INFO 에 남긴다."""
    from mathutils import Vector
    ext = os.path.splitext(path)[1].lower()
    before = set(bpy.data.objects)
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".blend":
        with bpy.data.libraries.load(path) as (src, dst):
            dst.objects = [n for n in src.objects]
        for o in dst.objects:
            if o is not None:
                bpy.context.scene.collection.objects.link(o)
    else:
        raise ValueError(f"지원하지 않는 형식: {ext}")
    new = [o for o in bpy.data.objects if o not in before or ext == ".blend"]
    arms = [o for o in new if o.type == "ARMATURE"]
    for a in arms:
        a.data.pose_position = "REST"   # 애니메이션 첫 프레임이 아니라 바인드 자세(A/T 포즈)로
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == "MESH"]
    skinned = [m for m in meshes if any(md.type == "ARMATURE" for md in m.modifiers)]
    if skinned:
        meshes = skinned   # 스킨된 메시가 있으면 그것만 캐릭터로 본다(내보내기가 남긴 보조 구체·프로브 제외)
    if not meshes:
        raise ValueError("메시 오브젝트가 없다")
    # 굽기: 모디파이어(아마추어 포함)를 적용하고 부모에서 떼어낸다 → 그 뒤 아마추어·엠프티·제외된 메시 삭제
    for m in meshes:
        bpy.ops.object.select_all(action="DESELECT"); m.select_set(True); bpy.context.view_layer.objects.active = m
        mw = m.matrix_world.copy()
        bpy.ops.object.convert(target="MESH")
        m.parent = None; m.matrix_world = mw
    dropped = [o.name for o in new if o.type == "MESH" and o not in meshes]
    for o in list(new):
        if o.name in bpy.data.objects and o not in meshes:
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = "character"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vs = [v.co for v in obj.data.vertices]
    zmin, zmax = min(v.z for v in vs), max(v.z for v in vs); H = zmax - zmin
    unit = 1.0
    if H > 20:      # cm 단위로 보인다(사람 키 1800 = mm 면 1.8 로 맞춘다)
        unit = 0.001 if H > 500 else 0.01
        obj.scale = (unit, unit, unit); bpy.ops.object.transform_apply(scale=True)
        vs = [v.co for v in obj.data.vertices]; zmin, zmax = min(v.z for v in vs), max(v.z for v in vs); H = zmax - zmin
    # 좌우 중심을 x=0 으로
    xmin, xmax = min(v.x for v in vs), max(v.x for v in vs); off_x = (xmin + xmax) / 2
    if abs(off_x) > 1e-4:
        obj.location.x -= off_x; bpy.ops.object.transform_apply(location=True)
    # 앞뒤: 발은 앞으로 뻗는다. 바닥 8% 띠의 y 무게중심이 발목 띠(12~18%)보다 키의 2% 이상 +Y 쪽이면 앞이 +Y 로 본다.
    # facing="auto" 면 그때 Z 축으로 180도 돌려 앞을 -Y(Rigify 메타리그 방향)로 맞춘다. "neg-y"/"pos-y" 로 강제할 수 있다
    foot = [v.y for v in vs if v.z < zmin + H * 0.08]; ankle = [v.y for v in vs if zmin + H * 0.12 < v.z < zmin + H * 0.18]
    hint = "+Y" if foot and ankle and (sum(foot) / len(foot) - sum(ankle) / len(ankle)) > H * 0.02 else "-Y"
    flip = (facing == "pos-y") or (facing == "auto" and hint == "+Y")
    if flip:
        # glTF 가져오기는 회전 모드를 쿼터니언으로 두므로 rotation_euler 대입은 무시된다 → 행렬로 돌린다
        from mathutils import Matrix
        obj.matrix_world = Matrix.Rotation(3.141592653589793, 4, "Z") @ obj.matrix_world
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        vs = [v.co for v in obj.data.vertices]
    # 앞뒤 중심: 다리 구간(키의 10~40%) 정점의 y 중앙값을 0 으로(가방·머리카락이 있어도 다리는 몸 축에 있다). 바닥은 z=0
    legs = sorted(v.y for v in vs if zmin + H * 0.10 < v.z < zmin + H * 0.40) or sorted(v.y for v in vs)
    off_y = legs[len(legs) // 2]
    obj.location.y -= off_y; obj.location.z -= zmin; bpy.ops.object.transform_apply(location=True)
    zmin = 0.0
    # glTF/FBX/OBJ 는 면마다 정점이 갈라져 들어오는 경우가 많다 → 겹친 정점을 합쳐야 자동 가중치(Bone Heat)가 풀린다
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=max(0.0001, H * 0.00005)); bpy.ops.object.mode_set(mode="OBJECT")
    IMPORT_INFO.update({"meshes_used": len(meshes), "meshes_dropped": dropped[:10], "had_armature": len(arms), "unit_scale": unit,
                        "offset_x": round(off_x, 4), "offset_y": round(off_y, 4), "ground_shift": True, "foot_direction_hint": hint, "facing": facing, "rotated_180": flip})
    return obj


def topology(obj):
    """조각 수·비매니폴드 모서리 수(자동 가중치 실패 예측용)."""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
    seen, parts = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        parts += 1; stack = [v]
        while stack:
            u = stack.pop()
            if u.index in seen:
                continue
            seen.add(u.index); stack.extend(e.other_vert(u) for e in u.link_edges)
    nm = sum(1 for e in bm.edges if not e.is_manifold); bm.free()
    return {"loose_parts": parts, "nonmanifold_edges": nm}


def mesh_stats(obj):
    from mathutils import Vector
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs, ys, zs = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
    return {"verts": len(vs), "faces": len(obj.data.polygons),
            "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)],
            "height": max(zs) - min(zs), "width": max(xs) - min(xs), "depth": max(ys) - min(ys)}
