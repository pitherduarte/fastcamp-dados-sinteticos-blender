import bpy
import math
import random
from pathlib import Path
from mathutils import Vector

BASE_DIR = Path(r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-dados-sinteticos-blender\card-09-objetos-reais\aula")
BLENDER_DIR = BASE_DIR / "blender"
DATASET_DIR = BASE_DIR / "dataset_caneca"
RESULTS_DIR = BASE_DIR / "resultados_caneca"
COUNTS = {"train": 80, "val": 20, "test": 10}
SEED = 42
LIMPAR_IMAGENS_ANTIGAS = True
RESOLUTION = 512

random.seed(SEED)


def find_object(name):
    obj = bpy.data.objects.get(name)
    if obj is not None:
        return obj
    normalized = name.lower().replace("_", "").replace("-", "").replace(" ", "")
    for candidate in bpy.data.objects:
        candidate_name = candidate.name.lower().replace("_", "").replace("-", "").replace(" ", "")
        if candidate_name == normalized or candidate_name.startswith(normalized):
            return candidate
    return None


def object_tree(root):
    if root is None:
        return []
    result = [root]
    stack = list(root.children)
    while stack:
        current = stack.pop()
        result.append(current)
        stack.extend(list(current.children))
    return result


def mesh_tree(root):
    return [obj for obj in object_tree(root) if obj.type == "MESH"]


def unique_objects(objects):
    result = []
    seen = set()
    for obj in objects:
        if obj is not None and obj.name not in seen:
            seen.add(obj.name)
            result.append(obj)
    return result


def remove_generated_objects():
    prefixes = (
        "CARD9_Backdrop",
        "CARD9_Key",
        "CARD9_Fill",
        "CARD9_Rim",
        "CARD9_Camera"
    )
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def set_socket(node, names, value):
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def make_material(name, color, roughness, metallic=0.0, transmission=0.0, ior=1.45):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is not None:
        set_socket(bsdf, ["Base Color"], color)
        set_socket(bsdf, ["Roughness"], roughness)
        set_socket(bsdf, ["Metallic"], metallic)
        set_socket(bsdf, ["Transmission Weight", "Transmission"], transmission)
        set_socket(bsdf, ["IOR"], ior)
    return material


def assign_material(obj, material):
    if obj is None or obj.type != "MESH":
        return
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def set_visible(root, visible):
    for obj in object_tree(root):
        obj.hide_render = not visible
        try:
            obj.hide_set(not visible)
        except Exception:
            pass


def set_level(level_name, levels):
    for root in levels.values():
        set_visible(root, False)
    if level_name != "empty":
        set_visible(levels[level_name], True)


def bounds(objects):
    points = []
    for obj in objects:
        if obj is None or obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        raise RuntimeError("Não foi possível calcular os limites da caneca.")
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_cube(name, location, dimensions, material, collection):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if collection not in obj.users_collection:
        for current_collection in list(obj.users_collection):
            current_collection.objects.unlink(obj)
        collection.objects.link(obj)
    assign_material(obj, material)
    return obj


def create_area_light(name, location, energy, size, color, target, collection):
    data = bpy.data.lights.new(name + "_Data", type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    point_at(obj, target)
    return obj


def create_camera(collection):
    data = bpy.data.cameras.new("CARD9_Camera_Data")
    camera = bpy.data.objects.new("CARD9_Camera", data)
    collection.objects.link(camera)
    data.type = "PERSP"
    data.lens = 62
    data.sensor_width = 36
    return camera


def configure_render(scene):
    engine_set = False
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = engine
            engine_set = True
            break
        except Exception:
            pass
    if not engine_set:
        raise RuntimeError("Nenhum motor de renderização compatível foi encontrado.")
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 12
    scene.render.film_transparent = False
    try:
        scene.render.use_file_extension = True
    except Exception:
        pass
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        pass
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scene.view_settings.look = "Medium High Contrast"
        except Exception:
            pass
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    try:
        scene.eevee.taa_render_samples = 64
        scene.eevee.use_gtao = True
        scene.eevee.gtao_distance = 3
        scene.eevee.gtao_factor = 1.25
        scene.eevee.use_soft_shadows = True
    except Exception:
        pass
    try:
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True
    except Exception:
        pass


def prepare_root(objects, collection):
    root = bpy.data.objects.get("CARD9_Mug_Root")
    if root is None:
        root = bpy.data.objects.new("CARD9_Mug_Root", None)
        collection.objects.link(root)
    root.rotation_euler = (0.0, 0.0, 0.0)
    root.location = (0.0, 0.0, 0.0)
    for obj in objects:
        if obj is None or obj == root:
            continue
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix
    return root


def vary_tea_color(material, rng):
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return
    color = (
        rng.uniform(0.12, 0.28),
        rng.uniform(0.018, 0.055),
        rng.uniform(0.003, 0.012),
        1.0
    )
    set_socket(bsdf, ["Base Color"], color)


def vary_background(material, rng):
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return
    value = rng.uniform(0.075, 0.14)
    color = (value, value * 1.06, value * 1.13, 1.0)
    set_socket(bsdf, ["Base Color"], color)


def place_camera(camera, target, scale, rng):
    azimuth = math.radians(rng.uniform(-52.0, 52.0))
    elevation = math.radians(rng.uniform(12.0, 28.0))
    distance = scale * rng.uniform(2.35, 2.75)
    horizontal = distance * math.cos(elevation)
    target_offset = Vector((
        rng.uniform(-0.035, 0.035) * scale,
        rng.uniform(-0.02, 0.02) * scale,
        rng.uniform(-0.035, 0.035) * scale
    ))
    look_target = target + target_offset
    camera.location = Vector((
        target.x + horizontal * math.sin(azimuth),
        target.y - horizontal * math.cos(azimuth),
        target.z + distance * math.sin(elevation)
    ))
    camera.data.lens = rng.uniform(58.0, 70.0)
    point_at(camera, look_target)


def render_image(scene, filepath):
    scene.render.filepath = str(filepath)
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)


scene = bpy.context.scene
configure_render(scene)
remove_generated_objects()

collection = bpy.data.collections.get("CARD9_CANECA_DATASET")
if collection is None:
    collection = bpy.data.collections.new("CARD9_CANECA_DATASET")
    scene.collection.children.link(collection)

glass_mug = find_object("Glass_Mug")
full_obj = find_object("Full")
half_obj = find_object("Half-Full")
mostly_obj = find_object("Mostly-Empty")

if not all((glass_mug, full_obj, half_obj, mostly_obj)):
    raise RuntimeError("Importe o arquivo tea_mug.fbx antes de executar este script.")

levels = {
    "mostly_empty": mostly_obj,
    "half_full": half_obj,
    "full": full_obj
}

level_meshes = unique_objects(mesh_tree(full_obj) + mesh_tree(half_obj) + mesh_tree(mostly_obj))
level_mesh_names = {obj.name for obj in level_meshes}
mug_meshes = [obj for obj in mesh_tree(glass_mug) if obj.name not in level_mesh_names]

if not mug_meshes:
    mug_meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name not in level_mesh_names and not obj.name.startswith("CARD9_")]

all_relevant_meshes = unique_objects(mug_meshes + level_meshes)
minimum, maximum = bounds(all_relevant_meshes)
center = (minimum + maximum) / 2.0
size_vector = maximum - minimum
scale = max(size_vector.x, size_vector.y, size_vector.z, 0.05)
target = Vector((center.x, center.y, center.z + size_vector.z * 0.05))

root_candidates = [glass_mug, full_obj, half_obj, mostly_obj]
root = prepare_root(root_candidates, collection)

ceramic_material = make_material(
    "CARD9_Ceramic_White",
    (0.82, 0.84, 0.88, 1.0),
    0.22,
    metallic=0.0,
    transmission=0.0,
    ior=1.46
)
tea_material = make_material(
    "CARD9_Tea",
    (0.20, 0.035, 0.006, 1.0),
    0.18,
    metallic=0.0,
    transmission=0.06,
    ior=1.33
)
background_material = make_material(
    "CARD9_Background_Dark_Gray",
    (0.10, 0.11, 0.13, 1.0),
    0.86
)

for obj in mug_meshes:
    assign_material(obj, ceramic_material)
for obj in level_meshes:
    assign_material(obj, tea_material)

floor_z = minimum.z - scale * 0.045
back_y = center.y + scale * 2.0
side_x = center.x - scale * 2.25

create_cube(
    "CARD9_Backdrop_Floor",
    (center.x, center.y + scale * 0.25, floor_z),
    (scale * 6.0, scale * 6.0, scale * 0.08),
    background_material,
    collection
)
create_cube(
    "CARD9_Backdrop_Back",
    (center.x, back_y, center.z + scale * 1.45),
    (scale * 6.0, scale * 0.08, scale * 3.8),
    background_material,
    collection
)
create_cube(
    "CARD9_Backdrop_Side",
    (side_x, center.y + scale * 0.2, center.z + scale * 1.45),
    (scale * 0.08, scale * 5.2, scale * 3.8),
    background_material,
    collection
)

scene.world.use_nodes = True
world_background = scene.world.node_tree.nodes.get("Background")
if world_background is not None:
    world_background.inputs["Color"].default_value = (0.008, 0.010, 0.014, 1.0)
    world_background.inputs["Strength"].default_value = 0.10

energy = max(18.0, 520.0 * scale * scale)
light_distance = scale * 3.0
light_size = scale * 2.2

key_light = create_area_light(
    "CARD9_Key",
    target + Vector((-light_distance * 0.85, -light_distance * 0.95, light_distance * 0.9)),
    energy,
    light_size,
    (1.0, 0.88, 0.76),
    target,
    collection
)
fill_light = create_area_light(
    "CARD9_Fill",
    target + Vector((light_distance * 0.85, -light_distance * 0.45, light_distance * 0.25)),
    energy * 0.42,
    light_size * 1.15,
    (0.58, 0.72, 1.0),
    target,
    collection
)
rim_light = create_area_light(
    "CARD9_Rim",
    target + Vector((light_distance * 0.15, light_distance * 0.85, light_distance * 0.95)),
    energy * 0.62,
    light_size,
    (0.72, 0.84, 1.0),
    target,
    collection
)

camera = create_camera(collection)
camera.data.clip_start = max(scale * 0.01, 0.001)
camera.data.clip_end = max(scale * 100.0, 100.0)
scene.camera = camera

BLENDER_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

if LIMPAR_IMAGENS_ANTIGAS:
    for image_path in DATASET_DIR.rglob("*.png"):
        image_path.unlink()

classes = ["empty", "mostly_empty", "half_full", "full"]
preview_rng = random.Random(SEED)
set_level("full", levels)
root.rotation_euler = (0.0, 0.0, math.radians(8.0))
place_camera(camera, target, scale, preview_rng)
render_image(scene, RESULTS_DIR / "preview_caneca.png")

image_counter = 0
for split, count in COUNTS.items():
    for class_name in classes:
        class_dir = DATASET_DIR / split / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        for index in range(count):
            image_counter += 1
            rng = random.Random(SEED + image_counter * 97)
            set_level(class_name, levels)
            root.rotation_euler = (
                math.radians(rng.uniform(-2.5, 2.5)),
                math.radians(rng.uniform(-2.5, 2.5)),
                math.radians(rng.uniform(-22.0, 22.0))
            )
            vary_tea_color(tea_material, rng)
            vary_background(background_material, rng)
            key_light.data.energy = energy * rng.uniform(0.86, 1.14)
            fill_light.data.energy = energy * 0.42 * rng.uniform(0.84, 1.16)
            rim_light.data.energy = energy * 0.62 * rng.uniform(0.84, 1.16)
            place_camera(camera, target, scale, rng)
            filepath = class_dir / f"{class_name}_{index:04d}.png"
            render_image(scene, filepath)
            print(f"[CARD9] {split}/{class_name}/{index + 1}/{count}")

set_level("full", levels)
root.rotation_euler = (0.0, 0.0, 0.0)
place_camera(camera, target, scale, random.Random(SEED))

blend_path = BLENDER_DIR / "card9_caneca_aula.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

print("[CARD9] CONCLUÍDO")
print(f"Arquivo Blender: {blend_path}")
print(f"Dataset: {DATASET_DIR}")
print(f"Preview: {RESULTS_DIR / 'preview_caneca.png'}")
print(f"Total de imagens: {sum(COUNTS.values()) * len(classes)}")
