import bpy
from math import radians
from bpy.props import FloatProperty


class OBJECT_OT_gerar_objeto_emissivo(bpy.types.Operator):
    bl_idname = "object.gerar_objeto_emissivo"
    bl_label = "Gerar Objeto Emissivo"
    bl_options = {"REGISTER", "UNDO"}

    noise_scale: FloatProperty(
        name="Escala do ruído",
        description="Controla o tamanho do padrão usado pelo modificador Displace",
        default=1.0,
        min=0.05,
        max=3.0
    )

    displacement_strength: FloatProperty(
        name="Força do deslocamento",
        description="Controla o quanto a textura deforma o objeto",
        default=0.5,
        min=0.0,
        max=3.0
    )

    emission_strength: FloatProperty(
        name="Força da emissão",
        description="Controla a intensidade do material emissivo",
        default=50.0,
        min=0.0,
        max=500.0
    )

    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add(
            size=2.0,
            location=(0.0, 0.0, 0.0)
        )

        obj = bpy.context.active_object
        obj.name = "Objeto_Emissivo"
        obj.rotation_euler[0] += radians(45)

        mod_subsurf = obj.modifiers.new(
            name="Subdivision Surface",
            type="SUBSURF"
        )
        mod_subsurf.subdivision_type = "CATMULL_CLARK"
        mod_subsurf.levels = 3
        mod_subsurf.render_levels = 3

        bpy.ops.object.shade_smooth()

        mod_displace = obj.modifiers.new(
            name="Deslocamento",
            type="DISPLACE"
        )
        mod_displace.strength = self.displacement_strength

        textura = bpy.data.textures.new(
            name="Textura_Distorcida",
            type="DISTORTED_NOISE"
        )
        textura.noise_scale = self.noise_scale

        mod_displace.texture = textura

        material = bpy.data.materials.new(name="Material_Emissivo")
        material.use_nodes = True
        obj.data.materials.append(material)

        nodes = material.node_tree.nodes
        links = material.node_tree.links

        nodes.clear()

        node_output = nodes.new(type="ShaderNodeOutputMaterial")
        node_output.name = "Material Output"
        node_output.location = (300, 0)

        node_emission = nodes.new(type="ShaderNodeEmission")
        node_emission.name = "Emission"
        node_emission.location = (0, 0)

        node_emission.inputs["Color"].default_value = (
            0.0,
            0.3,
            1.0,
            1.0
        )

        node_emission.inputs["Strength"].default_value = (
            self.emission_strength
        )

        links.new(
            node_emission.outputs["Emission"],
            node_output.inputs["Surface"]
        )

        scene = context.scene

        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except TypeError:
            scene.render.engine = "BLENDER_EEVEE"

        if scene.world is not None:
            scene.world.use_nodes = True
            world_nodes = scene.world.node_tree.nodes
            background = world_nodes.get("Background")

            if background is not None:
                background.inputs["Color"].default_value = (
                    0.005,
                    0.005,
                    0.005,
                    1.0
                )
                background.inputs["Strength"].default_value = 0.05

        eevee_settings = getattr(scene, "eevee", None)

        if (
            eevee_settings is not None
            and hasattr(eevee_settings, "use_bloom")
        ):
            eevee_settings.use_bloom = True

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        context.view_layer.objects.active = obj

        self.report(
            {"INFO"},
            "Objeto emissivo criado com sucesso."
        )

        return {"FINISHED"}


def register():
    nome_classe = OBJECT_OT_gerar_objeto_emissivo.__name__
    classe_antiga = getattr(bpy.types, nome_classe, None)

    if classe_antiga is not None:
        try:
            bpy.utils.unregister_class(classe_antiga)
        except RuntimeError:
            pass

    bpy.utils.register_class(OBJECT_OT_gerar_objeto_emissivo)


def unregister():
    try:
        bpy.utils.unregister_class(OBJECT_OT_gerar_objeto_emissivo)
    except RuntimeError:
        pass


if __name__ == "__main__":
    register()
    bpy.ops.object.gerar_objeto_emissivo()