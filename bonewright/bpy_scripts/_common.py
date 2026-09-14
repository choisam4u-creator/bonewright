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


def import_mesh(path: str, facing: str = "auto", keep_armature: bool = False, quad: bool = False):
    """어떤 파일이 와도 '리깅할 메시 하나'로 만든다: 스킨된 메시는 REST 자세로 굽고 아마추어·엠프티·보조 구체를 버린다.
    조각을 합치고, cm 단위면 m 로, 좌우 중심을 x=0 으로, 앞이 +Y 면 -Y 로 돌린다. 정규화 내용은 IMPORT_INFO 에 남긴다."""
    from mathutils import Vector, Matrix
    M = Matrix.Identity(4)   # 정규화(크기·중심·방향)를 하나의 행렬로 모은다 — 원본 뼈대를 같은 공간으로 옮길 때 쓴다
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
    # 본에 통째로 붙은 부품(로봇 팔·머리, 저폴리 캐릭터의 머리)도 캐릭터다 — 스킨된 메시만 고르면 robot_expressive 는 손만,
    # quat_pp_43j 는 머리 없이 리깅됐다(벤치 238%·머리 22cm 의 원인). 단 손·손가락 본에 붙은 것은 들고 있는 소품(총·칼)으로 보고 뺀다
    HAND_WORDS = ("hand", "finger", "thumb", "index", "middle", "ring", "pinky", "palm", "wrist", "weapon", "socket", "prop", "grip")
    def _held(m):
        return m.parent_type == "BONE" and any(w in m.parent_bone.lower() for w in HAND_WORDS)
    def _on_armature(m):
        p = m.parent
        while p is not None:
            if p.type == "ARMATURE": return True
            p = p.parent
        return False
    attached = [m for m in meshes if m not in skinned and _on_armature(m) and not _held(m)]
    attached_names = [m.name for m in attached] if skinned else []   # join 뒤에는 오브젝트가 사라져 이름을 못 읽는다
    # 붙은 부품이 '몸의 빈 자리를 채우는 구조'(43j 의 머리, 로봇의 팔다리)인지 '장식'(사슴뿔·어깨 갑옷)인지 가른다:
    # 부품이 붙은 본 머리 주변(스킨 메시 키의 12%)에 스킨된 정점이 이미 많으면 장식 → 스키닝에는 넣되 랜드마크 분석에서는 뺀다
    # (정점 그룹 bw_attachment, analyze 가 제외). 사슴뿔을 키에 넣으면 사족 정규화가 통째로 밀린다(Stag 59→75cm 로 확인)
    attachment_roles = {}
    if skinned and attached:
        from mathutils import Vector as _V
        sk_pts = [m.matrix_world @ v.co for m in skinned for v in m.data.vertices]
        zs_ = [q.z for q in sk_pts]; H_ = (max(zs_) - min(zs_)) if zs_ else 1.0; R_ = 0.12 * H_
        for m in attached:
            arm_ = m.parent
            while arm_ is not None and arm_.type != "ARMATURE": arm_ = arm_.parent
            if m.parent_type == "BONE" and arm_ is not None and m.parent_bone in arm_.data.bones:
                hb = arm_.matrix_world @ arm_.data.bones[m.parent_bone].head_local
            else:
                hb = m.matrix_world.translation
            near = sum(1 for q in sk_pts if (q - hb).length < R_)
            role = "decor" if near >= 20 else "structural"
            attachment_roles[m.name] = {"bone": m.parent_bone if m.parent_type == "BONE" else None, "near": near, "role": role}
            if role == "decor":
                g = m.vertex_groups.new(name="bw_attachment"); g.add(list(range(len(m.data.vertices))), 1.0, "REPLACE")
    if skinned:
        meshes = skinned + attached   # 스킨된 메시가 있으면 그것과 본에 붙은 부품만 캐릭터로 본다(내보내기가 남긴 보조 구체·프로브·가구 제외)
    if not meshes:
        raise ValueError("메시 오브젝트가 없다")
    # 굽기: 모디파이어(아마추어 포함)를 적용하고 부모에서 떼어낸다 → 그 뒤 아마추어·엠프티·제외된 메시 삭제
    for m in meshes:
        bpy.ops.object.select_all(action="DESELECT"); m.select_set(True); bpy.context.view_layer.objects.active = m
        mw = m.matrix_world.copy()
        bpy.ops.object.convert(target="MESH")
        m.parent = None; m.matrix_world = mw
    dropped = [o.name for o in new if o.type == "MESH" and o not in meshes]
    keep = set(meshes) | (set(arms) if keep_armature else set())
    # glTF 가져오기는 Y-up → Z-up 회전을 '루트 엠프티'에 넣는다. 그 엠프티를 지우면 자식(아마추어)이 옛 축에 남는다
    # (벤치마크에서 mannequiny 정답 뼈대가 통째로 90도 누워 153cm 오차로 나왔다) → 지우기 전에 월드 행렬을 떠 둔다
    saved = {a.name: a.matrix_world.copy() for a in arms} if keep_armature else {}
    for o in list(new):
        if o.name in bpy.data.objects and o not in keep:
            bpy.data.objects.remove(o)
    for a in (arms if keep_armature else []):
        if a.name in bpy.data.objects:
            a.parent = None; a.matrix_world = saved[a.name]
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
        obj.scale = (unit, unit, unit); bpy.ops.object.transform_apply(scale=True); M = Matrix.Scale(unit, 4) @ M
        vs = [v.co for v in obj.data.vertices]; zmin, zmax = min(v.z for v in vs), max(v.z for v in vs); H = zmax - zmin
    # 좌우 중심을 x=0 으로
    xmin, xmax = min(v.x for v in vs), max(v.x for v in vs); off_x = (xmin + xmax) / 2
    if abs(off_x) > 1e-4:
        obj.location.x -= off_x; bpy.ops.object.transform_apply(location=True); M = Matrix.Translation((-off_x, 0, 0)) @ M
    # 앞뒤: 발은 앞으로 뻗는다. 바닥 8% 띠의 y 무게중심이 발목 띠(12~18%)보다 키의 2% 이상 +Y 쪽이면 앞이 +Y 로 본다.
    # facing="auto" 면 그때 Z 축으로 180도 돌려 앞을 -Y(Rigify 메타리그 방향)로 맞춘다. "neg-y"/"pos-y" 로 강제할 수 있다
    foot = [v.y for v in vs if v.z < zmin + H * 0.08]; ankle = [v.y for v in vs if zmin + H * 0.12 < v.z < zmin + H * 0.18]
    hint = "+Y" if foot and ankle and (sum(foot) / len(foot) - sum(ankle) / len(ankle)) > H * 0.02 else "-Y"
    if quad:   # 사족은 앞뒤 양쪽에 발이 있어 위 규칙이 흔들린다 → 머리 위치로 판정한다(자산 10종 정답 대조 10/10)
        from _quad import front_dir_from_mesh
        fd = front_dir_from_mesh(vs, zmin, H)
        if fd is not None:
            hint = "+Y" if fd > 0 else "-Y"
    flip = (facing == "pos-y") or (facing == "auto" and hint == "+Y")
    if flip:
        # glTF 가져오기는 회전 모드를 쿼터니언으로 두므로 rotation_euler 대입은 무시된다 → 행렬로 돌린다
        from mathutils import Matrix
        obj.matrix_world = Matrix.Rotation(3.141592653589793, 4, "Z") @ obj.matrix_world
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        M = Matrix.Rotation(3.141592653589793, 4, "Z") @ M
        vs = [v.co for v in obj.data.vertices]
    # 앞뒤 중심: 다리 구간(키의 10~40%) 정점의 y 중앙값을 0 으로(가방·머리카락이 있어도 다리는 몸 축에 있다). 바닥은 z=0
    legs = sorted(v.y for v in vs if zmin + H * 0.10 < v.z < zmin + H * 0.40) or sorted(v.y for v in vs)
    off_y = legs[len(legs) // 2]
    obj.location.y -= off_y; obj.location.z -= zmin; bpy.ops.object.transform_apply(location=True)
    M = Matrix.Translation((0, -off_y, -zmin)) @ M
    for a in (arms if keep_armature else []):   # 원본 뼈대를 메시와 같은 공간으로
        a.matrix_world = M @ a.matrix_world
    zmin = 0.0
    # glTF/FBX/OBJ 는 면마다 정점이 갈라져 들어오는 경우가 많다 → 겹친 정점을 합쳐야 자동 가중치(Bone Heat)가 풀린다
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=max(0.0001, H * 0.00005)); bpy.ops.object.mode_set(mode="OBJECT")
    IMPORT_INFO.update({"meshes_used": len(meshes), "meshes_attached": attached_names[:10], "attachments": attachment_roles,
                        "meshes_dropped": dropped[:10], "had_armature": len(arms), "unit_scale": unit,
                        "offset_x": round(off_x, 4), "offset_y": round(off_y, 4), "ground_shift": True, "foot_direction_hint": hint, "facing": facing, "rotated_180": flip,
                        "matrix": [list(row) for row in M]})
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
