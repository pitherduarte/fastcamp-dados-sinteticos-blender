import bpy
import math
import random

from mathutils import Euler, Color
from pathlib import Path


def randomly_rotate_object(obj_2_change):
    random_rot = (
        random.random() * 2 * math.pi,
        random.random() * 2 * math.pi,
        random.random() * 2 * math.pi
    )

    obj_2_change.rotation_euler = Euler(random_rot, "XYZ")


def randomly_change_color(material_2_change):
    random_color = Color((1.0, 0.0, 0.0))
    random_color.hsv = (
        random.random(),
        1.0,
        1.0
    )

    color = (
        random_color.r,
        random_color.g,
        random_color.b,
        1.0
    )

    material_2_change.diffuse_color = color

    if material_2_change.use_nodes:
        material_2_change.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color


obj_names = ["A", "B", "C"]

obj_renders_per_split = [
    ("train", 300),
    ("val", 80),
    ("test", 10)
]

output_path = Path(
    r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-dados-sinteticos-blender\card-08-primeiro-dataset\datasets\video_completo"
)

blend_path = Path(
    r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-dados-sinteticos-blender\card-08-primeiro-dataset\blender\dataset_abc_video.blend"
)

scene = bpy.context.scene
scene.camera = bpy.data.objects["Camera"]

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 224
scene.render.resolution_y = 224
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"

blend_path.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

render_count = 0

for obj_name in obj_names:
    scene.objects[obj_name].hide_render = True

for split_name, renders_per_object in obj_renders_per_split:
    for obj_name in obj_names:
        obj_2_render = scene.objects[obj_name]
        obj_2_render.hide_render = False

        material_2_change = obj_2_render.data.materials[0]

        split_path = output_path / split_name / obj_name
        split_path.mkdir(parents=True, exist_ok=True)

        for render_num in range(renders_per_object):
            randomly_rotate_object(obj_2_render)
            randomly_change_color(material_2_change)

            scene.render.filepath = str(
                split_path / f"{render_count:06d}.png"
            )

            bpy.ops.render.render(write_still=True)

            render_count += 1

        obj_2_render.hide_render = True

for obj_name in obj_names:
    scene.objects[obj_name].hide_render = False