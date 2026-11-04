"""Prepared Moveo link. The mesh is official. The envelope is measured from it."""

from __future__ import annotations

import struct
from functools import lru_cache
from pathlib import Path

import numpy as np

from mantle.bounds import KEEP_OUT_PAST_MM, KEEP_OUT_SIZE_MM

ROOT = Path(__file__).resolve().parents[2]
STL_PATH = ROOT / "hardware" / "moveo" / "source" / "3M1.STL"
SOURCE_COMMIT = "0866a92501277636f76000a195d8a16d44b5b476"
HARDWARE_VERSION = "moveo-3m1-stl-0866a92"


def _vertices(path: Path) -> np.ndarray:
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * 50
    if len(data) != expected:
        raise RuntimeError(f"{path.name} is not a binary STL of {count} triangles")
    verts = np.empty((count * 3, 3), dtype=np.float64)
    offset = 84
    for index in range(count):
        nums = struct.unpack_from("<12fH", data, offset)
        for vertex in range(3):
            verts[index * 3 + vertex] = nums[3 + vertex * 3 : 6 + vertex * 3]
        offset += 50
    return verts


def _rolling_max(values: np.ndarray) -> np.ndarray:
    rolled = values.copy()
    for index in range(len(values)):
        rolled[index] = values[max(0, index - 1) : index + 2].max()
    return rolled


@lru_cache(maxsize=1)
def load_hardware() -> dict:
    verts = _vertices(STL_PATH)
    minimum = verts.min(axis=0)
    maximum = verts.max(axis=0)
    center_x = float((minimum[0] + maximum[0]) / 2)
    center_z = float((minimum[2] + maximum[2]) / 2)
    y0 = float(minimum[1])
    y1 = float(maximum[1])
    bins = 10
    edges = np.linspace(y0, y1, bins + 1)
    stations = []
    for index in range(bins):
        start, end = edges[index], edges[index + 1]
        if index == bins - 1:
            mask = (verts[:, 1] >= start) & (verts[:, 1] <= end)
        else:
            mask = (verts[:, 1] >= start) & (verts[:, 1] < end)
        chunk = verts[mask]
        if len(chunk) == 0:
            continue
        rx = float(np.max(np.abs(chunk[:, 0] - center_x)))
        rz = float(np.max(np.abs(chunk[:, 2] - center_z)))
        stations.append(
            {
                "y": float((start + end) / 2),
                "rx": rx,
                "rz": rz,
            }
        )
    radii_x = _rolling_max(np.array([item["rx"] for item in stations]))
    radii_z = _rolling_max(np.array([item["rz"] for item in stations]))
    for item, rx, rz in zip(stations, radii_x, radii_z):
        item["rx"] = float(rx)
        item["rz"] = float(rz)

    distal = stations[-1]
    keep_y = y1 + KEEP_OUT_PAST_MM + KEEP_OUT_SIZE_MM[1] / 2
    keep_z = center_z + max(distal["rx"], distal["rz"]) + 2.0
    return {
        "id": "moveo-forearm",
        "version": HARDWARE_VERSION,
        "name": "Moveo forearm",
        "part": "3M1",
        "units": "mm",
        "sourceCommit": SOURCE_COMMIT,
        "mesh": "/api/hardware/mesh.stl",
        "quality": "Official STL as a visual reference. Cover clearance uses a sliced envelope, not the raw triangles.",
        "assumptions": [
            "Units are millimeters, inferred from a 190.1 mm span, not from a drawing.",
            "Extended is the STL pose. Folded is an assumed 50° rotation about the near end.",
            "The neighboring-joint keep-out is a prepared box, not scanned hardware.",
        ],
        "attribution": "Mechanical reference: BCN3D Moveo, MIT, © 2016 BCN3D Technologies.",
        "axis": "y",
        "bounds": {
            "min": [float(v) for v in minimum],
            "max": [float(v) for v in maximum],
            "size": [float(v) for v in (maximum - minimum)],
        },
        "center": [center_x, float((y0 + y1) / 2), center_z],
        "pivot": [center_x, y0, center_z],
        "span": [y0, y1],
        "stations": stations,
        "keepOut": {
            "id": "distal-joint",
            "label": "Neighboring joint",
            "center": [center_x, keep_y, keep_z],
            "size": list(KEEP_OUT_SIZE_MM),
            "frame": "parent",
        },
        "canDesign": "A cover on this link only. It does not cross the joint.",
    }


def radius_at(hardware: dict, y: float) -> tuple[float, float]:
    stations = hardware["stations"]
    if y <= stations[0]["y"]:
        return stations[0]["rx"], stations[0]["rz"]
    if y >= stations[-1]["y"]:
        return stations[-1]["rx"], stations[-1]["rz"]
    for left, right in zip(stations, stations[1:]):
        if left["y"] <= y <= right["y"]:
            span = right["y"] - left["y"]
            mix = 0 if span == 0 else (y - left["y"]) / span
            rx = left["rx"] + (right["rx"] - left["rx"]) * mix
            rz = left["rz"] + (right["rz"] - left["rz"]) * mix
            return float(rx), float(rz)
    return stations[-1]["rx"], stations[-1]["rz"]
