"""Geometría de la mira, independiente del motor de dibujo.

El overlay dibuja con Cairo y la ventana de ajustes con QPainter. Los dos piden
las formas a este módulo, así que la mira no puede quedar distinta en un sitio
y en otro: antes había que cambiar la misma fórmula en dos archivos.

Todas las coordenadas salen en píxeles y relativas al centro de la mira, con la
Y creciendo hacia abajo (como en pantalla). Cada motor solo tiene que trasladar
las formas a donde corresponda y rellenarlas con la regla WINDING.
"""
import math
from dataclasses import dataclass

# Ángulo de cada brazo por estilo, en grados: 0 = derecha, 90 = arriba.
ARM_ANGLES = {
    "cross": (0, 90, 180, 270),    # cruz de cuatro brazos
    "tcross": (0, 180, 270),       # cruz en T: sin el brazo de arriba
    "x": (45, 135, 225, 315),      # aspa
}

# Estilos que pueden llevar punto central
DOT_STYLES = ("cross", "tcross", "x", "circle")

# Estilos con brazos horizontales y verticales: con grosor impar se desplaza
# medio píxel para que las líneas caigan justo sobre la rejilla de píxeles.
SNAP_STYLES = ("cross", "tcross")


@dataclass(frozen=True)
class Polygon:
    """Brazo de la mira: un rectángulo ya girado, con sus cuatro vértices.
    Los vértices van siempre en el mismo sentido, así que al rellenar varios
    brazos superpuestos no se mezcla la transparencia dos veces."""

    points: tuple


@dataclass(frozen=True)
class Disc:
    """Círculo relleno (punto central o estilo punto)."""

    cx: float
    cy: float
    r: float


@dataclass(frozen=True)
class Ring:
    """Anillo. Con inner <= 0 es un círculo relleno."""

    cx: float
    cy: float
    outer: float
    inner: float


def _bar(angle_deg, distance, length, thickness, dx, dy):
    """Rectángulo girado 'angle_deg' cuyo centro está a 'distance' del centro
    de la mira en esa dirección."""
    rad = math.radians(angle_deg)
    # Dirección del brazo y su perpendicular (la Y se invierte: en pantalla crece hacia abajo)
    ux, uy = math.cos(rad), -math.sin(rad)
    px, py = math.sin(rad), math.cos(rad)
    cx, cy = dx + ux * distance, dy + uy * distance
    half_l, half_t = length / 2, thickness / 2
    return Polygon(tuple(
        (cx + ux * sl * half_l + px * st * half_t, cy + uy * sl * half_l + py * st * half_t)
        for sl, st in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    ))


def pixel_nudge(cfg):
    """Medio píxel de desplazamiento cuando hace falta para que las líneas
    queden nítidas, o 0. Ya viene aplicado en las formas de shapes()."""
    return 0.5 if cfg["style"] in SNAP_STYLES and int(cfg["thickness"]) % 2 == 1 else 0.0


def shapes(cfg, grow=0.0):
    """Formas de la mira expandidas 'grow' píxeles por cada lado.

    Con grow = 0 es la mira; con grow > 0 es la silueta que se usa de contorno.
    Para el estilo imagen devuelve una lista vacía: esa se dibuja aparte.
    """
    style = cfg["style"]
    if style == "image":
        return []

    thickness = float(cfg["thickness"])
    nudge = pixel_nudge(cfg)
    items = []

    angles = ARM_ANGLES.get(style)
    if angles:
        arm, gap = float(cfg["arm"]), float(cfg["gap"])
        # El centro del brazo no se mueve al expandirlo: crece hacia dentro y hacia fuera
        distance = gap + arm / 2
        items += [_bar(a, distance, arm + 2 * grow, thickness + 2 * grow, nudge, nudge) for a in angles]
    elif style == "circle":
        radius = float(cfg["circle_radius"])
        items.append(Ring(nudge, nudge, radius + thickness / 2 + grow, radius - thickness / 2 - grow))

    if style == "dot" or (cfg["center_dot"] and style in DOT_STYLES):
        items.append(Disc(nudge, nudge, float(cfg["dot_radius"]) + grow))
    return items


def radius(cfg, grow=0.0):
    """Distancia del centro al punto más lejano de la mira, en píxeles.
    Sirve para calcular cuánto espacio necesita y el aumento de la vista previa."""
    if cfg["style"] == "image":
        return float(cfg["image_size"]) / 2
    far = 0.0
    for item in shapes(cfg, grow):
        if isinstance(item, Polygon):
            far = max(far, max(math.hypot(x, y) for x, y in item.points))
        elif isinstance(item, Disc):
            far = max(far, item.r + math.hypot(item.cx, item.cy))
        elif isinstance(item, Ring):
            far = max(far, item.outer + math.hypot(item.cx, item.cy))
    return far
