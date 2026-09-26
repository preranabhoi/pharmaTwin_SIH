"""
Script to generate standard GLTF 2.0 Binary (.glb) anatomical model
containing modular named organ meshes:
- Body_Silhouette (translucent full human silhouette)
- Brain (CNS)
- Heart (Cardiovascular)
- Left_Lung & Right_Lung (Respiratory)
- Liver (Hepatic)
- Left_Kidney & Right_Kidney (Renal)
- Stomach & Intestine (Gastrointestinal)
"""

import io
import json
import math
import struct
from pathlib import Path


def create_cube_mesh(min_x, min_y, min_z, max_x, max_y, max_z):
    """Creates a basic box mesh with 8 vertices and 36 indices."""
    positions = [
        # Front
        min_x, min_y, max_z,
        max_x, min_y, max_z,
        max_x, max_y, max_z,
        min_x, max_y, max_z,
        # Back
        min_x, min_y, min_z,
        max_x, min_y, min_z,
        max_x, max_y, min_z,
        min_x, max_y, min_z,
    ]
    normals = [
        0, 0, 1,  0, 0, 1,  0, 0, 1,  0, 0, 1,
        0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1
    ]
    indices = [
        0, 1, 2,  0, 2, 3,    # front
        1, 5, 6,  1, 6, 2,    # right
        5, 4, 7,  5, 7, 6,    # back
        4, 0, 3,  4, 3, 7,    # left
        3, 2, 6,  3, 6, 7,    # top
        4, 5, 1,  4, 1, 0     # bottom
    ]
    return positions, normals, indices


def create_sphere_mesh(center_x, center_y, center_z, radius_x, radius_y, radius_z, lat_segments=12, lon_segments=16):
    """Creates a smooth ellipsoid mesh."""
    positions = []
    normals = []
    indices = []

    for lat in range(lat_segments + 1):
        theta = lat * math.pi / lat_segments
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)

        for lon in range(lon_segments + 1):
            phi = lon * 2 * math.pi / lon_segments
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)

            nx = sin_theta * cos_phi
            ny = cos_theta
            nz = sin_theta * sin_phi

            x = center_x + radius_x * nx
            y = center_y + radius_y * ny
            z = center_z + radius_z * nz

            positions.extend([round(x, 4), round(y, 4), round(z, 4)])
            normals.extend([round(nx, 4), round(ny, 4), round(nz, 4)])

    for lat in range(lat_segments):
        for lon in range(lon_segments):
            first = lat * (lon_segments + 1) + lon
            second = first + lon_segments + 1

            indices.extend([first, second, first + 1])
            indices.extend([second, second + 1, first + 1])

    return positions, normals, indices


def build_human_twin_glb(output_path: Path):
    """Packages all organ meshes into a standard GLB binary file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    organs_config = [
        {"name": "Body_Silhouette", "type": "body", "pos": (0, 0.6, 0), "rad": (0.42, 1.2, 0.28), "color": [0.1, 0.6, 0.9, 0.15]},
        {"name": "Brain", "type": "brain", "pos": (0, 1.62, 0), "rad": (0.18, 0.16, 0.22), "color": [0.1, 0.7, 0.5, 0.9]},
        {"name": "Heart", "type": "heart", "pos": (-0.06, 0.95, 0.08), "rad": (0.12, 0.15, 0.11), "color": [0.1, 0.7, 0.5, 0.9]},
        {"name": "Left_Lung", "type": "left_lung", "pos": (-0.18, 0.95, 0.04), "rad": (0.10, 0.25, 0.12), "color": [0.1, 0.7, 0.5, 0.9]},
        {"name": "Right_Lung", "type": "right_lung", "pos": (0.18, 0.95, 0.04), "rad": (0.10, 0.25, 0.12), "color": [0.1, 0.7, 0.5, 0.9]},
        {"name": "Liver", "type": "liver", "pos": (0.12, 0.58, 0.06), "rad": (0.18, 0.12, 0.14), "color": [0.1, 0.7, 0.5, 0.9]},
        {"name": "Left_Kidney", "type": "left_kidney", "pos": (-0.15, 0.38, -0.05), "rad": (0.07, 0.10, 0.07), "color": [0.1, 0.7, 0.5, 0.9]},
        {"name": "Right_Kidney", "type": "right_kidney", "pos": (0.15, 0.36, -0.05), "rad": (0.07, 0.10, 0.07), "color": [0.1, 0.7, 0.5, 0.9]},
        {"name": "Stomach", "type": "stomach", "pos": (-0.08, 0.48, 0.06), "rad": (0.11, 0.09, 0.10), "color": [0.1, 0.7, 0.5, 0.9]},
        {"name": "Intestine", "type": "intestine", "pos": (0, 0.22, 0.05), "rad": (0.18, 0.14, 0.12), "color": [0.1, 0.7, 0.5, 0.9]},
    ]

    binary_buffer = bytearray()
    buffer_views = []
    accessors = []
    meshes = []
    nodes = []
    materials = []

    byte_offset = 0

    for idx, org in enumerate(organs_config):
        cx, cy, cz = org["pos"]
        rx, ry, rz = org["rad"]
        positions, normals, indices = create_sphere_mesh(cx, cy, cz, rx, ry, rz)

        # 1. Vertex Positions
        pos_bytes = struct.pack(f"<{len(positions)}f", *positions)
        pos_view_idx = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": byte_offset,
            "byteLength": len(pos_bytes),
            "target": 34962 # ARRAY_BUFFER
        })
        byte_offset += len(pos_bytes)
        binary_buffer.extend(pos_bytes)

        # Align to 4 bytes
        pad = (4 - (len(binary_buffer) % 4)) % 4
        binary_buffer.extend(b"\x00" * pad)
        byte_offset += pad

        pos_accessor_idx = len(accessors)
        min_x = min(positions[0::3])
        max_x = max(positions[0::3])
        min_y = min(positions[1::3])
        max_y = max(positions[1::3])
        min_z = min(positions[2::3])
        max_z = max(positions[2::3])

        accessors.append({
            "bufferView": pos_view_idx,
            "byteOffset": 0,
            "componentType": 5126, # FLOAT
            "count": len(positions) // 3,
            "type": "VEC3",
            "min": [min_x, min_y, min_z],
            "max": [max_x, max_y, max_z]
        })

        # 2. Vertex Normals
        norm_bytes = struct.pack(f"<{len(normals)}f", *normals)
        norm_view_idx = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": byte_offset,
            "byteLength": len(norm_bytes),
            "target": 34962
        })
        byte_offset += len(norm_bytes)
        binary_buffer.extend(norm_bytes)

        pad = (4 - (len(binary_buffer) % 4)) % 4
        binary_buffer.extend(b"\x00" * pad)
        byte_offset += pad

        norm_accessor_idx = len(accessors)
        accessors.append({
            "bufferView": norm_view_idx,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(normals) // 3,
            "type": "VEC3"
        })

        # 3. Indices
        ind_bytes = struct.pack(f"<{len(indices)}H", *indices)
        ind_view_idx = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": byte_offset,
            "byteLength": len(ind_bytes),
            "target": 34963 # ELEMENT_ARRAY_BUFFER
        })
        byte_offset += len(ind_bytes)
        binary_buffer.extend(ind_bytes)

        pad = (4 - (len(binary_buffer) % 4)) % 4
        binary_buffer.extend(b"\x00" * pad)
        byte_offset += pad

        ind_accessor_idx = len(accessors)
        accessors.append({
            "bufferView": ind_view_idx,
            "byteOffset": 0,
            "componentType": 5123, # UNSIGNED_SHORT
            "count": len(indices),
            "type": "SCALAR"
        })

        # Material
        mat_idx = len(materials)
        materials.append({
            "name": f"Mat_{org['name']}",
            "pbrMetallicRoughness": {
                "baseColorFactor": org["color"],
                "metallicFactor": 0.1,
                "roughnessFactor": 0.4
            },
            "alphaMode": "BLEND" if org["type"] == "body" else "OPAQUE",
            "doubleSided": True
        })

        # Mesh
        mesh_idx = len(meshes)
        meshes.append({
            "name": org["name"],
            "primitives": [{
                "attributes": {
                    "POSITION": pos_accessor_idx,
                    "NORMAL": norm_accessor_idx
                },
                "indices": ind_accessor_idx,
                "material": mat_idx
            }]
        })

        # Node
        nodes.append({
            "name": org["name"],
            "mesh": mesh_idx
        })

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "PharmaTwin AI GLB Builder v1.0"},
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "scene": 0,
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "buffers": [{"byteLength": len(binary_buffer)}],
        "bufferViews": buffer_views,
        "accessors": accessors
    }

    json_str = json.dumps(gltf_dict, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_pad

    bin_pad = (4 - (len(binary_buffer) % 4)) % 4
    binary_buffer.extend(b"\x00" * bin_pad)

    total_length = 12 + 8 + len(json_bytes) + 8 + len(binary_buffer)

    with open(output_path, "wb") as f:
        # GLB Header
        f.write(b"glTF") # magic
        f.write(struct.pack("<I", 2)) # version
        f.write(struct.pack("<I", total_length))

        # Chunk 0: JSON
        f.write(struct.pack("<I", len(json_bytes)))
        f.write(b"JSON")
        f.write(json_bytes)

        # Chunk 1: BIN
        f.write(struct.pack("<I", len(binary_buffer)))
        f.write(b"BIN\x00")
        f.write(binary_buffer)

    print(f"Successfully generated GLB model at {output_path} ({total_length} bytes)")


if __name__ == "__main__":
    workspace_root = Path(__file__).resolve().parent.parent.parent
    build_human_twin_glb(workspace_root / "frontend" / "public" / "models" / "human_twin.glb")
    build_human_twin_glb(workspace_root / "frontend" / "models" / "human_twin.glb")

