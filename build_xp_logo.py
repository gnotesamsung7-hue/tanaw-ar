#!/usr/bin/env python3
"""
Builds web/models/xp-logo.glb from the official horizontal XP Power logo (black on white).

Follows the XP Power Brand Guidelines (2024): logo not recoloured, skewed or re-proportioned.
Uses only brand colours: XP Black #000000, XP Bright White #FFFFFF, XP Light Grey #F3F2EF.

Layers (front view):
  white panel (clearspace around the logo)  ->  black logo shapes raised  ->  white "XP" raised in the square
"""
import sys
import numpy as np
import trimesh
from PIL import Image, ImageFilter
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from skimage import measure
from trimesh.visual.material import PBRMaterial

SRC = sys.argv[1]
OUT = sys.argv[2]
WIDTH = 0.60        # logo width in metres (life size in AR; people can pinch to resize)
PANEL_T = 0.012     # white panel thickness
LOGO_T = 0.012      # black logo relief
XP_T = 0.004        # white XP letters sit slightly proud of the black square
UPSCALE = 6

def mat(rgb, metal=0.0, rough=0.5):
    return PBRMaterial(baseColorFactor=[*[c / 255 for c in rgb], 1.0], metallicFactor=metal, roughnessFactor=rough)

BLACK, WHITE, LIGHT_GREY = (0, 0, 0), (255, 255, 255), (243, 242, 239)

# 1. clean, high-res mask of the black ink
img = Image.open(SRC).convert("L")
img = img.resize((img.width * UPSCALE, img.height * UPSCALE), Image.LANCZOS).filter(ImageFilter.GaussianBlur(UPSCALE * 0.6))
a = np.asarray(img).astype(float) / 255
ink = a < 0.5
ys, xs = np.nonzero(ink)
ink = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]      # trim to the logo itself
H, W = ink.shape

def polygons(mask):
    pad = np.pad(mask.astype(float), 2)
    rings = []
    for c in measure.find_contours(pad, 0.5):
        if len(c) < 10:
            continue
        p = Polygon([(x - 2, y - 2) for y, x in c]).buffer(0)
        if p.area > (UPSCALE * 3) ** 2:
            rings.append(p.simplify(UPSCALE * 0.35))
    rings.sort(key=lambda p: -p.area)
    g = Polygon()
    for r in rings:
        g = g.symmetric_difference(r)   # nested contours alternate solid / hole
    return g.buffer(0)

black = polygons(ink)
parts = list(black.geoms) if isinstance(black, MultiPolygon) else [black]
square = max(parts, key=lambda p: p.area)
xp_letters = unary_union([Polygon(i.coords) for i in square.interiors]).buffer(-UPSCALE * 0.05)

s = WIDTH / W                          # pixels -> metres
def to3d(mesh, z0):
    v = mesh.vertices.copy()
    x = (v[:, 0] - W / 2) * s
    y = (H - v[:, 1]) * s + LIFT       # image y down -> 3D y up; stands on the foot
    z = v[:, 2] * s + z0
    mesh.vertices = np.column_stack([x, y, z])
    mesh.invert()                      # mirror in y flips winding back
    return mesh

def extrude(geom, thickness, z0):
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    ms = [trimesh.creation.extrude_polygon(p, height=thickness / s) for p in polys if p.area > 1]
    return to3d(trimesh.util.concatenate(ms), z0)

scene = trimesh.Scene()

# white panel with clearspace = half the square's height all round (keeps the logo on white, as supplied)
cs = (square.bounds[3] - square.bounds[1]) * 0.5
FOOT_H = 0.02
LIFT = FOOT_H + cs * s               # panel bottom rests on top of the foot
panel = box(-cs, -cs, W + cs, H + cs)
pm = extrude(panel, PANEL_T, -PANEL_T)
pm.visual = trimesh.visual.TextureVisuals(material=mat(WHITE, rough=0.6))
scene.add_geometry(pm, node_name="panel_white")

# logo in XP Black
bm = extrude(black, LOGO_T, 0)
bm.visual = trimesh.visual.TextureVisuals(material=mat(BLACK, metal=0.1, rough=0.35))
scene.add_geometry(bm, node_name="logo_black")

# XP letters in XP Bright White, filling the knock-outs of the black square
xm = extrude(xp_letters, LOGO_T + XP_T, 0)
xm.visual = trimesh.visual.TextureVisuals(material=mat(WHITE, rough=0.45))
scene.add_geometry(xm, node_name="logo_xp_white")

# stand: panel sits on a light-grey foot so it stays upright on the floor
pw = (W + 2 * cs) * s
ph = (H + 2 * cs) * s
foot = trimesh.creation.box(extents=[pw * 1.02, FOOT_H, 0.14])
foot.apply_translation([0, FOOT_H / 2, 0])
foot.visual = trimesh.visual.TextureVisuals(material=mat(LIGHT_GREY, rough=0.7))
scene.add_geometry(foot, node_name="foot_light_grey")

scene.export(OUT)
b = scene.bounds
print(f"{OUT}: {b[1][0]-b[0][0]:.3f} x {b[1][1]-b[0][1]:.3f} x {b[1][2]-b[0][2]:.3f} m, "
      f"black parts={len(parts)}, xp holes={len(square.interiors)}")
