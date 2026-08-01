import bpy
import json
import math
import random
import shutil
from pathlib import Path

from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

print("CARD 10 — PRÁTICA COMPLEXA V4 (AÇÚCAR SEMPRE VISÍVEL)")

PRACTICA_DIR = Path(
    r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-dados-sinteticos-blender"
    r"\card-10-anotacao-automatica\pratica"
)

BLENDER_DIR = PRACTICA_DIR / "blender"
DATASET_DIR = PRACTICA_DIR / "dataset"
IMAGES_DIR = DATASET_DIR / "images"
SEMANTIC_DIR = DATASET_DIR / "masks_semantic"
INSTANCE_DIR = DATASET_DIR / "masks_instance"
ANNOTATIONS_DIR = DATASET_DIR / "annotations"

BLEND_PATH = BLENDER_DIR / "segmentacao_cafe_pratica_v4.blend"

NUM_IMAGENS = 20
RESOLUCAO = 512
AMOSTRAS_CYCLES = 64
SEMENTE = 42
LIMPAR_RESULTADOS_ANTERIORES = True

CLASSES = {
    "caneca": 50,
    "liquido": 100,
    "pires": 150,
    "colher": 200,
    "acucar": 250,
}

CORES_CANECAS = [
    (0.68, 0.055, 0.045, 1.0),
    (0.035, 0.20, 0.62, 1.0),
    (0.025, 0.43, 0.18, 1.0),
    (0.78, 0.78, 0.80, 1.0),
    (0.88, 0.46, 0.035, 1.0),
    (0.30, 0.08, 0.52, 1.0),
]

CORES_PIRES = [
    (0.80, 0.80, 0.82, 1.0),
    (0.62, 0.66, 0.72, 1.0),
    (0.82, 0.72, 0.60, 1.0),
]

CORES_CAFE = [
    (0.08, 0.025, 0.008, 1.0),
    (0.16, 0.055, 0.012, 1.0),
    (0.24, 0.09, 0.018, 1.0),
]

CORES_CENARIO = [
    (0.14, 0.08, 0.045, 1.0),
    (0.18, 0.20, 0.23, 1.0),
    (0.31, 0.22, 0.13, 1.0),
    (0.10, 0.19, 0.16, 1.0),
]

CORES_ACUCAR = [
    (0.88, 0.86, 0.80, 1.0),
    (0.70, 0.62, 0.50, 1.0),
]


def criar_pastas():
    BLENDER_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    SEMANTIC_DIR.mkdir(parents=True, exist_ok=True)
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

    for classe in CLASSES:
        (INSTANCE_DIR / classe).mkdir(parents=True, exist_ok=True)


def limpar_resultados():
    if not LIMPAR_RESULTADOS_ANTERIORES:
        return

    diretorios = [
        IMAGES_DIR,
        SEMANTIC_DIR,
        ANNOTATIONS_DIR,
    ] + [INSTANCE_DIR / classe for classe in CLASSES]

    for diretorio in diretorios:
        diretorio.mkdir(parents=True, exist_ok=True)
        for arquivo in diretorio.iterdir():
            if arquivo.is_file() and arquivo.suffix.lower() in {".png", ".json"}:
                arquivo.unlink()


def limpar_cena():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for colecao in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for bloco in list(colecao):
            if bloco.users == 0:
                colecao.remove(bloco)


def apontar_para(objeto, alvo):
    direcao = Vector(alvo) - objeto.location
    objeto.rotation_euler = direcao.to_track_quat("-Z", "Y").to_euler()


def criar_material(nome, cor, metalico=0.0, rugosidade=0.45):
    material = bpy.data.materials.new(nome)
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = cor
    bsdf.inputs["Metallic"].default_value = metalico
    bsdf.inputs["Roughness"].default_value = rugosidade

    return material


def trocar_cor(material, cores):
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = random.choice(cores)


def aplicar_material(objeto, material):
    objeto.data.materials.clear()
    objeto.data.materials.append(material)


def adicionar_bevel(objeto, largura, segmentos=3):
    bevel = objeto.modifiers.new("Bevel", "BEVEL")
    bevel.width = largura
    bevel.segments = segmentos
    bevel.limit_method = "ANGLE"

    # O modificador Weighted Normal do Blender 2.83 exige Auto Smooth.
    if hasattr(objeto.data, "use_auto_smooth"):
        objeto.data.use_auto_smooth = True
        objeto.data.auto_smooth_angle = math.radians(60.0)

    normal = objeto.modifiers.new("Weighted Normal", "WEIGHTED_NORMAL")
    normal.keep_sharp = True


def parentear(objeto, pai):
    matriz = objeto.matrix_world.copy()
    objeto.parent = pai
    objeto.matrix_world = matriz


def criar_copo_mesh():
    segmentos = 64

    raio_externo_inferior = 0.61
    raio_externo_superior = 0.66
    raio_interno_inferior = 0.50
    raio_interno_superior = 0.54

    z_externo_inferior = 0.08
    z_interno_inferior = 0.22
    z_superior = 1.28

    vertices = []
    faces = []

    def criar_anel(raio, z):
        inicio = len(vertices)
        for i in range(segmentos):
            angulo = 2.0 * math.pi * i / segmentos
            vertices.append((raio * math.cos(angulo), raio * math.sin(angulo), z))
        return inicio

    externo_inferior = criar_anel(raio_externo_inferior, z_externo_inferior)
    externo_superior = criar_anel(raio_externo_superior, z_superior)
    interno_superior = criar_anel(raio_interno_superior, z_superior)
    interno_inferior = criar_anel(raio_interno_inferior, z_interno_inferior)

    centro_externo = len(vertices)
    vertices.append((0.0, 0.0, z_externo_inferior))

    centro_interno = len(vertices)
    vertices.append((0.0, 0.0, z_interno_inferior))

    for i in range(segmentos):
        proximo = (i + 1) % segmentos

        faces.append((
            externo_inferior + i,
            externo_inferior + proximo,
            externo_superior + proximo,
            externo_superior + i,
        ))

        faces.append((
            externo_superior + i,
            externo_superior + proximo,
            interno_superior + proximo,
            interno_superior + i,
        ))

        faces.append((
            interno_superior + i,
            interno_superior + proximo,
            interno_inferior + proximo,
            interno_inferior + i,
        ))

        faces.append((
            centro_externo,
            externo_inferior + proximo,
            externo_inferior + i,
        ))

        faces.append((
            centro_interno,
            interno_inferior + i,
            interno_inferior + proximo,
        ))

    malha = bpy.data.meshes.new("Malha_Caneca")
    malha.from_pydata(vertices, [], faces)
    malha.update()

    caneca = bpy.data.objects.new("Caneca_Corpo", malha)
    bpy.context.collection.objects.link(caneca)

    for poligono in malha.polygons:
        poligono.use_smooth = True

    caneca.pass_index = CLASSES["caneca"]
    adicionar_bevel(caneca, 0.025, 3)

    return caneca


def criar_caneca():
    raiz = bpy.data.objects.new("Caneca_Root", None)
    bpy.context.collection.objects.link(raiz)

    corpo = criar_copo_mesh()

    bpy.ops.mesh.primitive_torus_add(
        major_segments=64,
        minor_segments=20,
        location=(0.72, 0.0, 0.72),
        rotation=(math.radians(90.0), 0.0, 0.0),
        major_radius=0.34,
        minor_radius=0.075,
    )
    alca = bpy.context.object
    alca.name = "Caneca_Alca"
    alca.pass_index = CLASSES["caneca"]

    for poligono in alca.data.polygons:
        poligono.use_smooth = True

    material = criar_material(
        "Material_Caneca",
        random.choice(CORES_CANECAS),
        metalico=0.0,
        rugosidade=0.34,
    )

    aplicar_material(corpo, material)
    aplicar_material(alca, material)

    parentear(corpo, raiz)
    parentear(alca, raiz)

    return {
        "root": raiz,
        "corpo": corpo,
        "alca": alca,
        "material": material,
    }


def criar_liquido(raiz_caneca):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=0.515,
        depth=0.045,
        location=(0.0, 0.0, 1.205),
    )
    liquido = bpy.context.object
    liquido.name = "Liquido"
    liquido.pass_index = CLASSES["liquido"]

    for poligono in liquido.data.polygons:
        poligono.use_smooth = True

    adicionar_bevel(liquido, 0.018, 3)

    material = criar_material(
        "Material_Cafe",
        random.choice(CORES_CAFE),
        metalico=0.0,
        rugosidade=0.18,
    )
    aplicar_material(liquido, material)
    parentear(liquido, raiz_caneca)

    return {
        "objeto": liquido,
        "material": material,
    }


def criar_pires():
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=1.22,
        depth=0.085,
        location=(0.0, 0.0, 0.055),
    )
    pires = bpy.context.object
    pires.name = "Pires"
    pires.pass_index = CLASSES["pires"]

    adicionar_bevel(pires, 0.085, 5)

    material = criar_material(
        "Material_Pires",
        random.choice(CORES_PIRES),
        metalico=0.0,
        rugosidade=0.38,
    )
    aplicar_material(pires, material)

    return {
        "objeto": pires,
        "material": material,
    }


def criar_colher():
    raiz = bpy.data.objects.new("Colher_Root", None)
    bpy.context.collection.objects.link(raiz)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.25, 0.0, 0.12))
    cabo = bpy.context.object
    cabo.name = "Colher_Cabo"
    cabo.dimensions = (1.45, 0.115, 0.055)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    adicionar_bevel(cabo, 0.04, 4)

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48,
        ring_count=24,
        radius=0.20,
        location=(2.02, 0.0, 0.12),
    )
    concha = bpy.context.object
    concha.name = "Colher_Concha"
    concha.scale = (1.45, 0.85, 0.20)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    for poligono in concha.data.polygons:
        poligono.use_smooth = True

    material = criar_material(
        "Material_Colher",
        (0.42, 0.45, 0.50, 1.0),
        metalico=0.92,
        rugosidade=0.16,
    )

    for objeto in (cabo, concha):
        objeto.pass_index = CLASSES["colher"]
        aplicar_material(objeto, material)
        parentear(objeto, raiz)

    return {
        "root": raiz,
        "objetos": [cabo, concha],
    }


def criar_acucar():
    raiz = bpy.data.objects.new("Acucar_Root", None)
    bpy.context.collection.objects.link(raiz)

    material = criar_material(
        "Material_Acucar",
        random.choice(CORES_ACUCAR),
        metalico=0.0,
        rugosidade=0.78,
    )

    cubos = []

    for indice, posicao_local in enumerate(((-0.16, 0.0, 0.0), (0.16, 0.06, 0.035)), start=1):
        bpy.ops.mesh.primitive_cube_add(size=0.40, location=(0.0, 0.0, 0.0))
        cubo = bpy.context.object
        cubo.name = f"Acucar_{indice}"
        cubo.pass_index = CLASSES["acucar"]

        adicionar_bevel(cubo, 0.045, 4)
        aplicar_material(cubo, material)

        cubo.parent = raiz
        cubo.location = posicao_local
        cubo.rotation_euler = (
            math.radians(random.uniform(-4.0, 4.0)),
            math.radians(random.uniform(-4.0, 4.0)),
            math.radians(random.uniform(-15.0, 15.0)),
        )

        cubos.append(cubo)

    return {
        "root": raiz,
        "objetos": cubos,
        "material": material,
    }


def criar_cenario():
    material = criar_material(
        "Material_Cenario",
        random.choice(CORES_CENARIO),
        metalico=0.0,
        rugosidade=0.72,
    )

    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0.0, 0.0, 0.0))
    piso = bpy.context.object
    piso.name = "Piso"
    aplicar_material(piso, material)

    bpy.ops.mesh.primitive_plane_add(
        size=12.0,
        location=(0.0, 3.15, 3.0),
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    fundo = bpy.context.object
    fundo.name = "Fundo"
    aplicar_material(fundo, material)

    return {
        "piso": piso,
        "fundo": fundo,
        "material": material,
    }


def criar_camera():
    bpy.ops.object.camera_add(location=(4.20, -6.50, 3.70))
    camera = bpy.context.object
    camera.name = "Camera"
    camera.data.lens = 52.0
    apontar_para(camera, (0.0, 0.0, 0.72))

    bpy.context.scene.camera = camera
    return camera


def criar_luzes():
    bpy.ops.object.light_add(type="AREA", location=(-3.6, -4.0, 5.4))
    principal = bpy.context.object
    principal.name = "Luz_Principal"
    principal.data.energy = 620.0
    principal.data.shape = "DISK"
    principal.data.size = 4.0
    apontar_para(principal, (0.0, 0.0, 0.65))

    bpy.ops.object.light_add(type="AREA", location=(4.0, -1.4, 3.4))
    preenchimento = bpy.context.object
    preenchimento.name = "Luz_Preenchimento"
    preenchimento.data.energy = 260.0
    preenchimento.data.shape = "RECTANGLE"
    preenchimento.data.size = 3.0
    apontar_para(preenchimento, (0.0, 0.0, 0.75))

    bpy.ops.object.light_add(type="AREA", location=(0.0, 2.2, 4.8))
    recorte = bpy.context.object
    recorte.name = "Luz_Recorte"
    recorte.data.energy = 340.0
    recorte.data.shape = "DISK"
    recorte.data.size = 2.4
    apontar_para(recorte, (0.0, 0.0, 0.9))

    return {
        "principal": principal,
        "preenchimento": preenchimento,
        "recorte": recorte,
    }


def configurar_mundo():
    mundo = bpy.context.scene.world
    mundo.use_nodes = True

    background = mundo.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.035, 0.040, 0.050, 1.0)
    background.inputs["Strength"].default_value = 0.22


def configurar_render():
    cena = bpy.context.scene

    cena.render.engine = "CYCLES"
    cena.cycles.device = "CPU"
    cena.cycles.samples = AMOSTRAS_CYCLES
    cena.cycles.preview_samples = 16
    cena.cycles.use_denoising = True

    cena.render.resolution_x = RESOLUCAO
    cena.render.resolution_y = RESOLUCAO
    cena.render.resolution_percentage = 100

    cena.render.image_settings.file_format = "PNG"
    cena.render.image_settings.color_mode = "RGB"
    cena.render.image_settings.color_depth = "8"
    cena.render.image_settings.compression = 15

    cena.render.use_file_extension = True
    cena.render.use_compositing = True
    cena.render.use_sequencer = False
    cena.render.film_transparent = False

    cena.view_settings.view_transform = "Filmic"
    cena.view_settings.look = "Filmic - Medium High Contrast"
    cena.view_settings.exposure = 0.0
    cena.view_settings.gamma = 1.0

    bpy.context.view_layer.use_pass_object_index = True


def criar_saida(nos, nome, diretorio, prefixo, modo_cor, posicao):
    saida = nos.new("CompositorNodeOutputFile")
    saida.name = nome
    saida.label = nome
    saida.location = posicao
    saida.base_path = str(diretorio)

    saida.format.file_format = "PNG"
    saida.format.color_mode = modo_cor
    saida.format.color_depth = "8"
    saida.format.compression = 15
    saida.file_slots[0].path = prefixo

    return saida


def configurar_compositor():
    cena = bpy.context.scene
    cena.use_nodes = True

    arvore = cena.node_tree
    nos = arvore.nodes
    links = arvore.links
    nos.clear()

    render_layers = nos.new("CompositorNodeRLayers")
    render_layers.name = "Render Layers"
    render_layers.location = (-900, 170)

    composite = nos.new("CompositorNodeComposite")
    composite.name = "Composite"
    composite.location = (650, 440)

    links.new(render_layers.outputs["Image"], composite.inputs["Image"])

    dividir = nos.new("CompositorNodeMath")
    dividir.name = "Semantic_Index"
    dividir.label = "IndexOB / 255"
    dividir.operation = "DIVIDE"
    dividir.inputs[1].default_value = 255.0
    dividir.location = (-520, -400)

    saida_semantica = criar_saida(
        nos,
        "Saida_Semantica",
        SEMANTIC_DIR,
        "semantic_",
        "BW",
        (290, -400),
    )

    links.new(render_layers.outputs["IndexOB"], dividir.inputs[0])
    links.new(dividir.outputs[0], saida_semantica.inputs[0])

    y = 230

    for nome, indice in CLASSES.items():
        mascara = nos.new("CompositorNodeIDMask")
        mascara.name = "Mask_" + nome
        mascara.label = f"{nome}: {indice}"
        mascara.index = indice
        mascara.location = (-520, y)

        if hasattr(mascara, "use_antialiasing"):
            mascara.use_antialiasing = False

        saida = criar_saida(
            nos,
            "Saida_" + nome,
            INSTANCE_DIR / nome,
            nome + "_",
            "BW",
            (290, y),
        )

        links.new(render_layers.outputs["IndexOB"], mascara.inputs[0])
        links.new(mascara.outputs[0], saida.inputs[0])

        y -= 150


def randomizar_cena(elementos):
    caneca = elementos["caneca"]
    liquido = elementos["liquido"]
    pires = elementos["pires"]
    colher = elementos["colher"]
    acucar = elementos["acucar"]
    cenario = elementos["cenario"]
    camera = elementos["camera"]
    luzes = elementos["luzes"]

    centro_x = random.uniform(-0.16, 0.16)
    centro_y = random.uniform(-0.12, 0.12)

    pires["objeto"].location = (centro_x, centro_y, 0.055)
    pires["objeto"].rotation_euler.z = random.uniform(-0.12, 0.12)

    caneca["root"].location = (
        centro_x + random.uniform(-0.035, 0.035),
        centro_y + random.uniform(-0.035, 0.035),
        0.08,
    )
    caneca["root"].rotation_euler.z = random.uniform(-math.pi, math.pi)

    nivel_z = random.uniform(1.15, 1.22)
    liquido["objeto"].location.z = nivel_z
    liquido["objeto"].scale.z = random.uniform(0.80, 1.18)

    lado = random.choice([-1.0, 1.0])
    colher["root"].location = (
        centro_x + lado * random.uniform(0.75, 1.05),
        centro_y + random.uniform(-0.60, 0.52),
        0.04,
    )
    colher["root"].rotation_euler.z = random.uniform(-0.65, 0.65)
    if lado < 0:
        colher["root"].rotation_euler.z += math.pi

    # O açúcar fica sempre visível e no lado oposto à colher.
    lado_acucar = -lado
    acucar["root"].hide_render = False
    acucar["root"].hide_viewport = False
    acucar["root"].location = (
        centro_x + lado_acucar * random.uniform(0.68, 0.88),
        centro_y - random.uniform(0.42, 0.62),
        0.22,
    )
    acucar["root"].rotation_euler.z = random.uniform(-0.45, 0.45)

    for cubo in acucar["objetos"]:
        cubo.hide_render = False
        cubo.hide_viewport = False

    trocar_cor(caneca["material"], CORES_CANECAS)
    trocar_cor(liquido["material"], CORES_CAFE)
    trocar_cor(pires["material"], CORES_PIRES)
    trocar_cor(acucar["material"], CORES_ACUCAR)
    trocar_cor(cenario["material"], CORES_CENARIO)

    camera.location = (
        random.uniform(3.80, 4.55),
        random.uniform(-6.85, -6.10),
        random.uniform(3.35, 4.05),
    )
    camera.data.lens = random.uniform(48.0, 56.0)
    apontar_para(camera, (centro_x, centro_y, 0.68))

    luzes["principal"].data.energy = random.uniform(520.0, 760.0)
    luzes["preenchimento"].data.energy = random.uniform(190.0, 330.0)
    luzes["recorte"].data.energy = random.uniform(260.0, 420.0)

    bpy.context.view_layer.update()


def bbox_grupo(objetos, cena, camera):
    pontos_tela = []

    for objeto in objetos:
        if objeto.hide_render:
            continue

        for canto in objeto.bound_box:
            ponto_mundo = objeto.matrix_world @ Vector(canto)
            ponto_tela = world_to_camera_view(cena, camera, ponto_mundo)

            if ponto_tela.z > 0:
                pontos_tela.append(ponto_tela)

    if not pontos_tela:
        return None

    min_x = max(0.0, min(p.x for p in pontos_tela))
    max_x = min(1.0, max(p.x for p in pontos_tela))
    min_y = max(0.0, min(p.y for p in pontos_tela))
    max_y = min(1.0, max(p.y for p in pontos_tela))

    if min_x >= max_x or min_y >= max_y:
        return None

    x1 = int(min_x * RESOLUCAO)
    x2 = int(max_x * RESOLUCAO)
    y1 = int((1.0 - max_y) * RESOLUCAO)
    y2 = int((1.0 - min_y) * RESOLUCAO)

    return {
        "x": x1,
        "y": y1,
        "width": max(0, x2 - x1),
        "height": max(0, y2 - y1),
    }


def escrever_json(indice, elementos):
    cena = bpy.context.scene
    camera = cena.camera

    grupos = {
        "caneca": [
            elementos["caneca"]["corpo"],
            elementos["caneca"]["alca"],
        ],
        "liquido": [elementos["liquido"]["objeto"]],
        "pires": [elementos["pires"]["objeto"]],
        "colher": elementos["colher"]["objetos"],
        "acucar": elementos["acucar"]["objetos"],
    }

    dados = {
        "image": f"imagem_{indice:04d}.png",
        "semantic_mask": f"semantic_{indice:04d}.png",
        "resolution": [RESOLUCAO, RESOLUCAO],
        "objects": [],
    }

    for classe, objetos in grupos.items():
        bbox = bbox_grupo(objetos, cena, camera)
        visivel = any(not objeto.hide_render for objeto in objetos) and bbox is not None

        dados["objects"].append({
            "class": classe,
            "pass_index": CLASSES[classe],
            "visible": visivel,
            "instance_mask": f"{classe}_{indice:04d}.png",
            "bounding_box": bbox,
        })

    caminho = ANNOTATIONS_DIR / f"imagem_{indice:04d}.json"

    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def verificar_arquivos(indice):
    esperados = [
        IMAGES_DIR / f"imagem_{indice:04d}.png",
        SEMANTIC_DIR / f"semantic_{indice:04d}.png",
        ANNOTATIONS_DIR / f"imagem_{indice:04d}.json",
    ]

    for classe in CLASSES:
        esperados.append(
            INSTANCE_DIR / classe / f"{classe}_{indice:04d}.png"
        )

    faltando = [str(caminho) for caminho in esperados if not caminho.exists()]

    if faltando:
        print("AVISO — arquivos não encontrados após o render:")
        for caminho in faltando:
            print("  ", caminho)
    else:
        print(f"Arquivos do frame {indice:04d} confirmados.")


def salvar_blend():
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))


def gerar_dataset(elementos):
    cena = bpy.context.scene
    cena.frame_start = 1
    cena.frame_end = NUM_IMAGENS

    for indice in range(1, NUM_IMAGENS + 1):
        cena.frame_set(indice)
        randomizar_cena(elementos)

        caminho_imagem = IMAGES_DIR / f"imagem_{indice:04d}.png"
        cena.render.filepath = str(caminho_imagem)

        bpy.ops.render.render(write_still=True)

        # Garante a gravação da imagem RGB mesmo se o caminho de saída
        # principal não for respeitado por alguma configuração do arquivo.
        render_result = bpy.data.images.get("Render Result")
        if render_result is not None and not caminho_imagem.exists():
            render_result.save_render(filepath=str(caminho_imagem), scene=cena)

        escrever_json(indice, elementos)
        verificar_arquivos(indice)

        print(f"Render {indice}/{NUM_IMAGENS} concluído.")

    salvar_blend()



def validar_dataset_final():
    contagens = {
        "images": len(list(IMAGES_DIR.glob("imagem_*.png"))),
        "semantic": len(list(SEMANTIC_DIR.glob("semantic_*.png"))),
        "annotations": len(list(ANNOTATIONS_DIR.glob("imagem_*.json"))),
    }

    for classe in CLASSES:
        contagens[f"mask_{classe}"] = len(
            list((INSTANCE_DIR / classe).glob(f"{classe}_*.png"))
        )

    resumo = {
        "expected_per_category": NUM_IMAGENS,
        "counts": contagens,
        "complete": all(valor == NUM_IMAGENS for valor in contagens.values()),
    }

    caminho_resumo = DATASET_DIR / "resumo_dataset.json"
    with caminho_resumo.open("w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=2)

    print("RESUMO FINAL DO DATASET")
    for nome, quantidade in contagens.items():
        print(f"  {nome}: {quantidade}/{NUM_IMAGENS}")

    if resumo["complete"]:
        print("Dataset completo e validado.")
    else:
        print("ATENÇÃO: há arquivos faltando. Consulte resumo_dataset.json.")


def main():
    random.seed(SEMENTE)

    criar_pastas()
    limpar_resultados()
    limpar_cena()

    cenario = criar_cenario()
    pires = criar_pires()
    caneca = criar_caneca()
    liquido = criar_liquido(caneca["root"])
    colher = criar_colher()
    acucar = criar_acucar()
    camera = criar_camera()
    luzes = criar_luzes()

    configurar_mundo()
    configurar_render()
    configurar_compositor()

    elementos = {
        "cenario": cenario,
        "pires": pires,
        "caneca": caneca,
        "liquido": liquido,
        "colher": colher,
        "acucar": acucar,
        "camera": camera,
        "luzes": luzes,
    }

    salvar_blend()
    gerar_dataset(elementos)
    validar_dataset_final()

    print("PRÁTICA CONCLUÍDA")
    print("Arquivo Blender:", BLEND_PATH)
    print("Dataset:", DATASET_DIR)


if __name__ == "__main__":
    main()
