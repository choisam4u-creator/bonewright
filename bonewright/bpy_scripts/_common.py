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


def import_mesh(path: str):
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
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o not in before or (o.type == "MESH" and ext == ".blend")]
    if not meshes:
        raise ValueError("메시 오브젝트가 없다")
    # 여러 조각이면 하나로 합친다
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = "character"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # glTF/FBX/OBJ 는 면마다 정점이 갈라져 들어오는 경우가 많다 → 겹친 정점을 합쳐야 자동 가중치(Bone Heat)가 풀린다
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0001); bpy.ops.object.mode_set(mode="OBJECT")
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
