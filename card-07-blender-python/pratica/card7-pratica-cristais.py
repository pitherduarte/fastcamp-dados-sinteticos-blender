"""
Projeto: Campo de Cristais Neon
Autor: Pither Mikael Gonçalves Duarte
Atividade: Card 7 - Prática própria
Tecnologia: Python com Blender bpy

"""
import bpy
import math
import random
from mathutils import Vector
from bpy.props import FloatProperty, IntProperty


NOME_COLECAO = "Campo_Cristais_Neon"
PREFIXO = "CN_"


# -----------------------------------------------------------------------------
# Limpeza e organização
# -----------------------------------------------------------------------------

def limpar_campo_anterior():
    """Remove somente a coleção criada por este script em execuções anteriores."""
    colecao = bpy.data.collections.get(NOME_COLECAO)

    if colecao is not None:
        for objeto in list(colecao.objects):
            bpy.data.objects.remove(objeto, do_unlink=True)
        bpy.data.collections.remove(colecao)

    # Remove malhas sem uso que pertenciam ao campo anterior.
    for malha in list(bpy.data.meshes):
        if malha.name.startswith(PREFIXO) and malha.users == 0:
            bpy.data.meshes.remove(malha)


def criar_colecao():
    colecao = bpy.data.collections.new(NOME_COLECAO)
    bpy.context.scene.collection.children.link(colecao)
    return colecao


def mover_para_colecao(objeto, colecao):
    """Move um objeto criado por operador para a coleção do projeto."""
    for colecao_atual in list(objeto.users_collection):
        colecao_atual.objects.unlink(objeto)
    colecao.objects.link(objeto)


# -----------------------------------------------------------------------------
# Materiais
# -----------------------------------------------------------------------------

def obter_ou_criar_material(nome):
    material = bpy.data.materials.get(nome)
    if material is None:
        material = bpy.data.materials.new(nome)
    material.use_nodes = True
    material.node_tree.nodes.clear()
    return material


def criar_material_neon(nome, cor, forca_emissao):
    """Combina um shader físico com emissão para preservar volume e brilho."""
    material = obter_ou_criar_material(nome)
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    saida = nodes.new(type="ShaderNodeOutputMaterial")
    saida.location = (520, 0)

    adicionar = nodes.new(type="ShaderNodeAddShader")
    adicionar.location = (280, 0)

    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    principled.location = (-120, 90)
    principled.inputs["Base Color"].default_value = (
        cor[0] * 0.12,
        cor[1] * 0.12,
        cor[2] * 0.12,
        1.0,
    )
    principled.inputs["Metallic"].default_value = 0.35
    principled.inputs["Roughness"].default_value = 0.22

    emissao = nodes.new(type="ShaderNodeEmission")
    emissao.location = (-120, -120)
    emissao.inputs["Color"].default_value = (*cor, 1.0)
    emissao.inputs["Strength"].default_value = forca_emissao

    links.new(principled.outputs["BSDF"], adicionar.inputs[0])
    links.new(emissao.outputs["Emission"], adicionar.inputs[1])
    links.new(adicionar.outputs[0], saida.inputs["Surface"])

    return material


def criar_material_base():
    material = obter_ou_criar_material(PREFIXO + "Base_Escura")
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    saida = nodes.new(type="ShaderNodeOutputMaterial")
    shader = nodes.new(type="ShaderNodeBsdfPrincipled")

    shader.inputs["Base Color"].default_value = (0.008, 0.012, 0.025, 1.0)
    shader.inputs["Metallic"].default_value = 0.75
    shader.inputs["Roughness"].default_value = 0.23

    links.new(shader.outputs["BSDF"], saida.inputs["Surface"])
    return material


# -----------------------------------------------------------------------------
# Geometria procedural
# -----------------------------------------------------------------------------

def criar_malha_cristal(nome, raio, altura, lados=6):
    """Cria um cristal facetado: base hexagonal, corpo e ponta."""
    altura_corpo = altura * 0.72
    raio_base = raio * 0.88

    vertices = []

    # Anel inferior.
    for indice in range(lados):
        angulo = 2.0 * math.pi * indice / lados
        vertices.append(
            (raio_base * math.cos(angulo), raio_base * math.sin(angulo), 0.0)
        )

    # Anel superior do corpo.
    for indice in range(lados):
        angulo = 2.0 * math.pi * indice / lados
        vertices.append(
            (raio * math.cos(angulo), raio * math.sin(angulo), altura_corpo)
        )

    # Ponta do cristal.
    indice_ponta = len(vertices)
    vertices.append((0.0, 0.0, altura))

    faces = []

    # Face inferior com ordem invertida para apontar para baixo.
    faces.append(tuple(reversed(range(lados))))

    # Faces laterais do corpo.
    for indice in range(lados):
        seguinte = (indice + 1) % lados
        faces.append((indice, seguinte, lados + seguinte, lados + indice))

    # Faces triangulares da ponta.
    for indice in range(lados):
        seguinte = (indice + 1) % lados
        faces.append((lados + indice, lados + seguinte, indice_ponta))

    malha = bpy.data.meshes.new(PREFIXO + nome + "_Malha")
    malha.from_pydata(vertices, [], faces)
    malha.update()

    objeto = bpy.data.objects.new(PREFIXO + nome, malha)
    return objeto


def adicionar_bevel(objeto, largura):
    modificador = objeto.modifiers.new(name="Bevel_Leve", type="BEVEL")
    modificador.width = largura
    modificador.segments = 2
    modificador.limit_method = "ANGLE"


def criar_base(colecao, material):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=5.3,
        depth=0.32,
        location=(0.0, 0.0, -0.18),
    )
    base = bpy.context.active_object
    base.name = PREFIXO + "Plataforma"
    mover_para_colecao(base, colecao)
    base.data.materials.append(material)

    bevel = base.modifiers.new(name="Bevel_Base", type="BEVEL")
    bevel.width = 0.12
    bevel.segments = 3

    return base


def criar_cristais(
    colecao,
    materiais,
    quantidade,
    raio_campo,
    altura_minima,
    altura_maxima,
    forca_bevel,
    semente,
):
    random.seed(semente)
    angulo_dourado = math.pi * (3.0 - math.sqrt(5.0))

    for indice in range(quantidade):
        if indice == 0:
            distancia = 0.0
            angulo = 0.0
            altura = altura_maxima
            raio = 0.58
        else:
            proporcao = indice / max(1, quantidade - 1)
            distancia = raio_campo * math.sqrt(proporcao)
            angulo = indice * angulo_dourado + random.uniform(-0.18, 0.18)

            # Cristais próximos do centro tendem a ser um pouco mais altos.
            fator_centro = 1.0 - (distancia / max(raio_campo, 0.001))
            altura_base = altura_minima + (altura_maxima - altura_minima) * (
                0.35 + 0.55 * fator_centro
            )
            altura = max(
                altura_minima,
                min(altura_maxima, altura_base + random.uniform(-0.45, 0.45)),
            )
            raio = random.uniform(0.25, 0.48)

        x = distancia * math.cos(angulo) + random.uniform(-0.10, 0.10)
        y = distancia * math.sin(angulo) + random.uniform(-0.10, 0.10)

        cristal = criar_malha_cristal(
            nome=f"Cristal_{indice + 1:02d}",
            raio=raio,
            altura=altura,
            lados=6,
        )
        colecao.objects.link(cristal)
        cristal.location = (x, y, 0.0)
        cristal.rotation_euler = (
            math.radians(random.uniform(-6.0, 6.0)),
            math.radians(random.uniform(-6.0, 6.0)),
            random.uniform(0.0, math.tau),
        )

        # Garante que todas as cores apareçam antes de repetir a paleta.
        material = materiais[(indice + semente) % len(materiais)]
        cristal.data.materials.append(material)
        adicionar_bevel(cristal, min(forca_bevel, raio * 0.22))


# -----------------------------------------------------------------------------
# Câmera, iluminação e renderização
# -----------------------------------------------------------------------------

def apontar_para(objeto, alvo):
    direcao = Vector(alvo) - objeto.location
    objeto.rotation_euler = direcao.to_track_quat("-Z", "Y").to_euler()


def criar_camera(colecao):
    dados = bpy.data.cameras.new(PREFIXO + "Camera_Dados")
    camera = bpy.data.objects.new(PREFIXO + "Camera", dados)
    colecao.objects.link(camera)

    camera.location = (8.8, -10.8, 7.2)
    dados.lens = 52
    apontar_para(camera, (0.0, 0.0, 1.7))

    bpy.context.scene.camera = camera
    return camera


def criar_luz_area(colecao, nome, localizacao, energia, cor, tamanho):
    dados = bpy.data.lights.new(PREFIXO + nome + "_Dados", type="AREA")
    dados.energy = energia
    dados.color = cor
    dados.shape = "DISK"
    dados.size = tamanho

    luz = bpy.data.objects.new(PREFIXO + nome, dados)
    colecao.objects.link(luz)
    luz.location = localizacao
    apontar_para(luz, (0.0, 0.0, 1.3))
    return luz


def configurar_mundo():
    mundo = bpy.context.scene.world
    if mundo is None:
        mundo = bpy.data.worlds.new("Mundo_Cristais_Neon")
        bpy.context.scene.world = mundo

    mundo.use_nodes = True
    fundo = mundo.node_tree.nodes.get("Background")
    if fundo is not None:
        fundo.inputs["Color"].default_value = (0.0015, 0.002, 0.008, 1.0)
        fundo.inputs["Strength"].default_value = 0.025


def configurar_compositor():
    """Adiciona brilho real ao render, inclusive no Eevee Next."""
    cena = bpy.context.scene
    cena.use_nodes = True
    nodes = cena.node_tree.nodes
    links = cena.node_tree.links
    nodes.clear()

    render_layers = nodes.new(type="CompositorNodeRLayers")
    brilho = nodes.new(type="CompositorNodeGlare")
    composite = nodes.new(type="CompositorNodeComposite")

    brilho.glare_type = "FOG_GLOW"
    brilho.quality = "HIGH"
    brilho.threshold = 0.55
    brilho.size = 7

    render_layers.location = (-300, 0)
    brilho.location = (0, 0)
    composite.location = (300, 0)

    links.new(render_layers.outputs["Image"], brilho.inputs["Image"])
    links.new(brilho.outputs["Image"], composite.inputs["Image"])


def configurar_render():
    cena = bpy.context.scene

    try:
        cena.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        cena.render.engine = "BLENDER_EEVEE"

    cena.render.resolution_x = 900
    cena.render.resolution_y = 900
    cena.render.resolution_percentage = 100
    cena.render.image_settings.file_format = "PNG"
    cena.render.filepath = "//campo_cristais_neon_card7.png"

    # Qualidade suficiente para o trabalho sem deixar o render muito pesado.
    if hasattr(cena, "eevee"):
        if hasattr(cena.eevee, "taa_render_samples"):
            cena.eevee.taa_render_samples = 64

    try:
        cena.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass

    configurar_mundo()
    configurar_compositor()


# -----------------------------------------------------------------------------
# Operador do Blender
# -----------------------------------------------------------------------------

class OBJECT_OT_gerar_campo_cristais_neon(bpy.types.Operator):
    """Gera um campo procedural de cristais low-poly com várias cores neon"""

    bl_idname = "object.gerar_campo_cristais_neon"
    bl_label = "Gerar Campo de Cristais Neon"
    bl_options = {"REGISTER", "UNDO"}

    quantidade: IntProperty(
        name="Quantidade de cristais",
        description="Número de cristais gerados na plataforma",
        default=16,
        min=5,
        max=40,
    )

    raio_campo: FloatProperty(
        name="Área de distribuição",
        description="Controla o espaço ocupado pelo conjunto",
        default=4.2,
        min=2.0,
        max=7.0,
    )

    altura_minima: FloatProperty(
        name="Altura mínima",
        default=1.1,
        min=0.5,
        max=4.0,
    )

    altura_maxima: FloatProperty(
        name="Altura máxima",
        default=4.2,
        min=1.5,
        max=7.0,
    )

    intensidade_neon: FloatProperty(
        name="Intensidade neon",
        description="Força de emissão das cores dos cristais",
        default=7.0,
        min=0.5,
        max=30.0,
    )

    arredondamento: FloatProperty(
        name="Arredondamento",
        description="Largura do Bevel aplicado nas bordas",
        default=0.045,
        min=0.0,
        max=0.15,
    )

    semente: IntProperty(
        name="Semente aleatória",
        description="Mude o número para gerar outra distribuição",
        default=7,
        min=0,
        max=9999,
    )

    def execute(self, context):
        limpar_campo_anterior()
        colecao = criar_colecao()

        altura_minima = min(self.altura_minima, self.altura_maxima)
        altura_maxima = max(self.altura_minima, self.altura_maxima)

        # Paleta com cores neon bem diferentes entre si.
        paleta = [
            ("Ciano", (0.00, 0.85, 1.00)),
            ("Magenta", (1.00, 0.02, 0.55)),
            ("Violeta", (0.58, 0.10, 1.00)),
            ("Verde", (0.20, 1.00, 0.18)),
            ("Laranja", (1.00, 0.22, 0.02)),
        ]

        materiais_neon = [
            criar_material_neon(
                PREFIXO + "Neon_" + nome,
                cor,
                self.intensidade_neon,
            )
            for nome, cor in paleta
        ]

        material_base = criar_material_base()
        criar_base(colecao, material_base)

        criar_cristais(
            colecao=colecao,
            materiais=materiais_neon,
            quantidade=self.quantidade,
            raio_campo=self.raio_campo,
            altura_minima=altura_minima,
            altura_maxima=altura_maxima,
            forca_bevel=self.arredondamento,
            semente=self.semente,
        )

        criar_camera(colecao)

        # Três luzes com cores diferentes para reforçar o clima neon.
        criar_luz_area(
            colecao,
            "Luz_Ciano",
            (5.5, -4.0, 7.0),
            900.0,
            (0.05, 0.75, 1.0),
            4.0,
        )
        criar_luz_area(
            colecao,
            "Luz_Magenta",
            (-5.0, -1.0, 5.0),
            750.0,
            (1.0, 0.03, 0.35),
            3.5,
        )
        criar_luz_area(
            colecao,
            "Luz_Violeta",
            (0.5, 5.0, 6.5),
            650.0,
            (0.45, 0.08, 1.0),
            3.0,
        )

        configurar_render()

        self.report(
            {"INFO"},
            "Campo de cristais neon criado. Pressione F12 para renderizar.",
        )
        return {"FINISHED"}


CLASSES = (OBJECT_OT_gerar_campo_cristais_neon,)


def register():
    for classe in CLASSES:
        classe_anterior = getattr(bpy.types, classe.__name__, None)
        if classe_anterior is not None:
            try:
                bpy.utils.unregister_class(classe_anterior)
            except RuntimeError:
                pass
        bpy.utils.register_class(classe)


def unregister():
    for classe in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(classe)
        except RuntimeError:
            pass


if __name__ == "__main__":
    register()

    # Executa automaticamente ao pressionar Alt + P.
    bpy.ops.object.gerar_campo_cristais_neon()