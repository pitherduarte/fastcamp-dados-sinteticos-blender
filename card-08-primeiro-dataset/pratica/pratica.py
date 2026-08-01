import bpy
import math
import random

from mathutils import Euler
from pathlib import Path


output_path = Path(
    r"pasta pessoal"
)

blend_path = Path(
    r"pasta pessoal"

obj_names = ["Estrela", "Coracao", "ConeTransito"]

obj_renders_per_split = [
    ("train", 30),
    ("val", 10),
    ("test", 5)
]


def cleanup_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)

    for block in bpy.data.curves:
        if block.users == 0:
            bpy.data.curves.remove(block)

    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

    for block in bpy.data.lights:
        if block.users == 0:
            bpy.data.lights.remove(block)

    for block in bpy.data.cameras:
        if block.users == 0:
            bpy.data.cameras.remove(block)


def make_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    principled = mat.node_tree.nodes["Principled BSDF"]
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = 0.35
    principled.inputs["Specular"].default_value = 0.45
    return mat


def get_family_objects(root):
    objects = [root]

    for child in root.children:
        objects.extend(get_family_objects(child))

    return objects


def set_family_hide_render(root, hide):
    for obj in get_family_objects(root):
        obj.hide_render = hide


def create_backdrop():
    mesh = bpy.data.meshes.new("BackdropMesh")

    verts = [
        (-4.0, -4.0, 0.0),
        (4.0, -4.0, 0.0),
        (4.0, 4.0, 0.0),
        (-4.0, 4.0, 0.0),
        (-4.0, -4.0, 5.0),
        (4.0, -4.0, 5.0),
        (4.0, 4.0, 5.0),
        (-4.0, 4.0, 5.0),
    ]

    faces = [
        (0, 1, 2, 3),
        (0, 3, 7, 4),
        (3, 2, 6, 7),
    ]

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("Backdrop", mesh)
    bpy.context.collection.objects.link(obj)

    mat = make_material("BackdropMaterial", (0.72, 0.72, 0.72, 1.0))
    obj.data.materials.append(mat)

    return obj


def create_star():
    outer_r = 0.75
    inner_r = 0.32
    verts = []

    for i in range(10):
        angle = math.radians(90) + i * math.pi / 5.0
        r = outer_r if i % 2 == 0 else inner_r
        x = math.cos(angle) * r
        y = math.sin(angle) * r
        verts.append((x, y))

    curve = bpy.data.curves.new("EstrelaCurve", type="CURVE")
    curve.dimensions = "2D"
    curve.fill_mode = "BOTH"
    curve.extrude = 0.14
    curve.bevel_depth = 0.008

    spline = curve.splines.new("POLY")
    spline.points.add(len(verts) - 1)

    for i, (x, y) in enumerate(verts):
        spline.points[i].co = (x, y, 0.0, 1.0)

    spline.use_cyclic_u = True

    obj = bpy.data.objects.new("Estrela", curve)
    bpy.context.collection.objects.link(obj)
    obj.location = (0.0, 0.0, 0.45)

    return obj


def create_heart():
    points = []

    for i in range(160):
        t = 2 * math.pi * i / 160.0
        x = 16 * (math.sin(t) ** 3)
        y = (
            13 * math.cos(t)
            - 5 * math.cos(2 * t)
            - 2 * math.cos(3 * t)
            - math.cos(4 * t)
        )

        points.append((x / 24.0, (y / 24.0) + 0.06))

    curve = bpy.data.curves.new("CoracaoCurve", type="CURVE")
    curve.dimensions = "2D"
    curve.fill_mode = "BOTH"
    curve.extrude = 0.14
    curve.bevel_depth = 0.008

    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)

    for i, (x, y) in enumerate(points):
        spline.points[i].co = (x, y, 0.0, 1.0)

    spline.use_cyclic_u = True

    obj = bpy.data.objects.new("Coracao", curve)
    bpy.context.collection.objects.link(obj)
    obj.location = (0.0, 0.0, 0.45)
    obj.scale = (0.82, 0.82, 0.82)

    return obj


def create_traffic_cone():
    root = bpy.data.objects.new("ConeTransito", None)
    root.empty_display_type = "PLAIN_AXES"
    root.location = (0.0, 0.0, 0.0)
    bpy.context.collection.objects.link(root)

    cone_body_mat = make_material("ConeBodyMat", (0.90, 0.36, 0.04, 1.0))
    cone_band_mat = make_material("ConeBandMat", (0.95, 0.95, 0.95, 1.0))
    cone_base_mat = make_material("ConeBaseMat", (0.06, 0.06, 0.06, 1.0))

    bpy.ops.mesh.primitive_cone_add(
        vertices=32,
        radius1=0.42,
        radius2=0.10,
        depth=1.1,
        location=(0.0, 0.0, 0.72)
    )
    body = bpy.context.active_object
    body.name = "ConeBody"
    body.parent = root
    body.data.materials.append(cone_body_mat)

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=0.23,
        depth=0.10,
        location=(0.0, 0.0, 0.82)
    )
    band = bpy.context.active_object
    band.name = "ConeBand"
    band.parent = root
    band.data.materials.append(cone_band_mat)

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, 0.08)
    )
    base = bpy.context.active_object
    base.name = "ConeBase"
    base.parent = root
    base.scale = (0.42, 0.42, 0.08)
    base.data.materials.append(cone_base_mat)

    return root


def setup_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)

    cam.location = (2.8, -2.8, 1.8)
    cam.rotation_euler = Euler(
        (
            math.radians(66),
            0.0,
            math.radians(45)
        ),
        "XYZ"
    )

    cam.data.lens = 50
    bpy.context.scene.camera = cam

    return cam


def setup_lights():
    light_data = bpy.data.lights.new(name="Light", type="AREA")
    light = bpy.data.objects.new(name="Light", object_data=light_data)
    bpy.context.collection.objects.link(light)

    light.location = (2.8, -2.2, 3.6)
    light.rotation_euler = Euler((math.radians(55), 0.0, math.radians(35)), "XYZ")
    light.data.energy = 1600
    light.data.shape = "RECTANGLE"
    light.data.size = 3.0
    light.data.size_y = 3.0

    fill_data = bpy.data.lights.new(name="FillLight", type="AREA")
    fill = bpy.data.objects.new(name="FillLight", object_data=fill_data)
    bpy.context.collection.objects.link(fill)

    fill.location = (-2.5, 2.0, 2.4)
    fill.rotation_euler = Euler((math.radians(70), 0.0, math.radians(-45)), "XYZ")
    fill.data.energy = 350
    fill.data.shape = "RECTANGLE"
    fill.data.size = 3.0
    fill.data.size_y = 3.0

    return light, fill


def setup_world():
    scene = bpy.context.scene

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")

    world = scene.world
    world.use_nodes = True

    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.80, 0.80, 0.80, 1.0)
    bg.inputs[1].default_value = 0.35


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.eevee.taa_render_samples = 96
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 3
    scene.eevee.gtao_factor = 1.25
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1


def apply_color_variation(class_name, root):
    if class_name == "Estrela":
        mat = root.data.materials[0]
        color = (
            random.uniform(0.95, 1.0),
            random.uniform(0.60, 0.78),
            random.uniform(0.02, 0.12),
            1.0
        )
        mat.diffuse_color = color
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color

    elif class_name == "Coracao":
        mat = root.data.materials[0]
        color = (
            random.uniform(0.78, 0.95),
            random.uniform(0.08, 0.20),
            random.uniform(0.14, 0.28),
            1.0
        )
        mat.diffuse_color = color
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color

    elif class_name == "ConeTransito":
        body = bpy.data.objects["ConeBody"]
        band = bpy.data.objects["ConeBand"]
        base = bpy.data.objects["ConeBase"]

        body_mat = body.data.materials[0]
        band_mat = band.data.materials[0]
        base_mat = base.data.materials[0]

        orange = (
            random.uniform(0.82, 0.96),
            random.uniform(0.22, 0.38),
            random.uniform(0.02, 0.08),
            1.0
        )

        white = (
            random.uniform(0.88, 0.96),
            random.uniform(0.88, 0.96),
            random.uniform(0.88, 0.96),
            1.0
        )

        dark = (
            random.uniform(0.04, 0.08),
            random.uniform(0.04, 0.08),
            random.uniform(0.04, 0.08),
            1.0
        )

        body_mat.diffuse_color = orange
        body_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = orange

        band_mat.diffuse_color = white
        band_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = white

        base_mat.diffuse_color = dark
        base_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = dark


def randomize_transform(class_name, root):
    if class_name == "ConeTransito":
        root.rotation_euler = Euler(
            (
                random.uniform(-0.10, 0.10),
                random.uniform(-0.10, 0.10),
                random.uniform(0.0, 2 * math.pi)
            ),
            "XYZ"
        )
        s = random.uniform(0.92, 1.05)
        root.scale = (s, s, s)

    else:
        root.rotation_euler = Euler(
            (
                math.radians(90) + random.uniform(-0.20, 0.20),
                random.uniform(-0.20, 0.20),
                random.uniform(0.0, 2 * math.pi)
            ),
            "XYZ"
        )
        s = random.uniform(0.88, 1.02)
        root.scale = (s, s, s)


def build_scene():
    cleanup_scene()
    setup_world()
    setup_render()
    create_backdrop()
    setup_camera()
    setup_lights()

    star_mat = make_material("StarMat", (1.0, 0.68, 0.05, 1.0))
    heart_mat = make_material("HeartMat", (0.88, 0.10, 0.18, 1.0))

    estrela = create_star()
    coracao = create_heart()
    cone = create_traffic_cone()

    estrela.data.materials.append(star_mat)
    coracao.data.materials.append(heart_mat)

    return {
        "Estrela": estrela,
        "Coracao": coracao,
        "ConeTransito": cone
    }


def generate_dataset(objects):
    scene = bpy.context.scene

    for name in obj_names:
        set_family_hide_render(objects[name], True)

    render_count = 0

    for split_name, renders_per_object in obj_renders_per_split:
        for obj_name in obj_names:
            root = objects[obj_name]
            set_family_hide_render(root, False)

            split_path = output_path / split_name / obj_name
            split_path.mkdir(parents=True, exist_ok=True)

            for render_num in range(renders_per_object):
                randomize_transform(obj_name, root)
                apply_color_variation(obj_name, root)

                scene.render.filepath = str(
                    split_path / f"{render_count:06d}.png"
                )

                bpy.ops.render.render(write_still=True)

                render_count += 1

            set_family_hide_render(root, True)

    for name in obj_names:
        set_family_hide_render(objects[name], False)


objects = build_scene()

output_path.mkdir(parents=True, exist_ok=True)
blend_path.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

generate_dataset(objects)

bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))