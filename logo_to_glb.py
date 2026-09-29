#!/usr/bin/env python3
"""
Turn a flat logo (SVG or PNG) into a 3D extruded .glb model for Tanaw AR.

  python logo_to_glb.py logo.svg ../web/models/xp-logo.glb --width 0.6 --depth 0.05

The logo stands upright on a thin base, facing the viewer, with each colour of the
logo kept as its own material. Width is in metres (real size when placed in AR).

Needs: pip install trimesh shapely mapbox-earcut svgelements pillow scikit-image numpy
"""
import argparse
from collections import defaultdict

import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from trimesh.visual.material import PBRMaterial


def polys_from_svg(path):
    import svgelements as se
    svg = se.SVG.parse(path, reify=True)
    by_color = defaultdict(list)
    for el in svg.elements():
        if not isinstance(el, se.Shape) or isinstance(el, se.SVGText):
            continue
        fill = el.fill
        if fill is None or fill.value is None or fill.alpha == 0:
            continue
        shape = se.Path(el)
        if len(shape) == 0:
            continue
        rings = []
        for sub in shape.as_subpaths():
            sub = se.Path(sub)
            length = sub.length(error=1e-3) or 0
            n = max(24, int(length / 0.5))
            pts = [(p.x, p.y) for p in (sub.point(t) for t in np.linspace(0, 1, n)) if p is not None]
            if len(pts) >= 3:
                ring = Polygon(pts).buffer(0)
                if not ring.is_empty:
                    rings.append(ring)
        if not rings:
            continue
        geom = rings[0]
        for r in rings[1:]:  # even-odd: inner rings become holes
            geom = geom.symmetric_difference(r)
        key = (fill.red / 255, fill.green / 255, fill.blue / 255)
        # a later shape paints over earlier ones of other colours
        for other in list(by_color):
            if other != key:
                by_color[other] = [g.difference(geom) for g in by_color[other]]
        by_color[key].append(geom)
    return {k: unary_union(v) for k, v in by_color.items()}, True  # SVG y points down


def polys_from_png(path, max_colors=4):
    from PIL import Image
    from skimage import measure
    img = Image.open(path).convert("RGBA")
    scale = 1024 / max(img.size)
    if scale < 1:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    a = np.asarray(img).astype(float) / 255
    rgb, alpha = a[..., :3], a[..., 3]
    # ink = visible and not near-white background
    ink = (alpha > 0.5) & (rgb.min(axis=2) < 0.92)
    q = img.convert("RGB").quantize(colors=max_colors + 1, method=Image.MEDIANCUT)
    labels = np.asarray(q)
    palette = np.array(q.getpalette()[: (max_colors + 1) * 3]).reshape(-1, 3) / 255
    out = {}
    for idx, col in enumerate(palette):
        mask = ink & (labels == idx)
        if mask.sum() < 50:
            continue
        padded = np.pad(mask.astype(float), 1)
        polys = []
        for c in measure.find_contours(padded, 0.5):
            if len(c) < 8:
                continue
            p = Polygon([(x - 1, y - 1) for y, x in c]).buffer(0)
            if p.area > 20:
                polys.append(p.simplify(0.6))
        if not polys:
            continue
        geom = polys[0]
        for p in polys[1:]:
            geom = geom.symmetric_difference(p)
        out[tuple(col)] = geom
    return out, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--width", type=float, default=0.6, help="logo width in metres")
    ap.add_argument("--depth", type=float, default=0.05, help="extrusion depth in metres")
    ap.add_argument("--no-base", action="store_true")
    ap.add_argument("--metal", type=float, default=0.35)
    args = ap.parse_args()

    shapes, flip_y = (polys_from_svg if args.src.lower().endswith(".svg") else polys_from_png)(args.src)
    shapes = {k: v for k, v in shapes.items() if not v.is_empty}
    if not shapes:
        raise SystemExit("No filled shapes found in the logo.")

    allg = unary_union(list(shapes.values()))
    minx, miny, maxx, maxy = allg.bounds
    s = args.width / (maxx - minx)
    ymid_flip = maxy if flip_y else miny

    scene = trimesh.Scene()
    for i, (col, geom) in enumerate(shapes.items()):
        parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
        meshes = []
        for p in parts:
            if not isinstance(p, Polygon) or p.area * s * s < 1e-7:
                continue
            m = trimesh.creation.extrude_polygon(p, height=args.depth / s)
            meshes.append(m)
        if not meshes:
            continue
        m = trimesh.util.concatenate(meshes)
        v = m.vertices.copy()
        x = (v[:, 0] - (minx + maxx) / 2) * s
        y = ((ymid_flip - v[:, 1]) if flip_y else (v[:, 1] - miny)) * s
        z = v[:, 2] * s - args.depth / 2
        m.vertices = np.column_stack([x, y, z])
        if flip_y:
            m.invert()  # mirroring flips winding; restore outward normals
        base_h = 0 if args.no_base else 0.02
        m.apply_translation([0, base_h, 0])
        m.visual = trimesh.visual.TextureVisuals(material=PBRMaterial(
            baseColorFactor=[*col, 1.0], metallicFactor=args.metal, roughnessFactor=0.35))
        scene.add_geometry(m, node_name=f"logo_color_{i}")

    if not args.no_base:
        w = args.width * 1.08
        base = trimesh.creation.box(extents=[w, 0.02, max(args.depth * 3, 0.12)])
        base.apply_translation([0, 0.01, 0])
        base.visual = trimesh.visual.TextureVisuals(material=PBRMaterial(
            baseColorFactor=[0.12, 0.13, 0.15, 1], metallicFactor=0.6, roughnessFactor=0.3))
        scene.add_geometry(base, node_name="base")

    scene.export(args.out)
    b = scene.bounds
    print(f"Wrote {args.out}: {len(shapes)} colour(s), size {b[1][0]-b[0][0]:.2f} x {b[1][1]-b[0][1]:.2f} x {b[1][2]-b[0][2]:.2f} m")


if __name__ == "__main__":
    main()
