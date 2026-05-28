from __future__ import annotations

import json
import math
import re
import struct
import unicodedata
import zipfile
import argparse
from io import BytesIO
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


DEFAULT_K = 12
DEFAULT_RADIUS_KM = 80.0


def normalize_name(value: str) -> str:
    """Return an accent-insensitive key for municipality joins."""
    text = str(value).upper()
    text = re.sub(r"\s*\(GO\)\s*$", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_pt_br_number(value: object) -> float:
    """Parse values such as 21.177,21 or 3.921 from Brazilian CSV files."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")

    text = str(value).strip().replace('"', "")
    if text in {"", "...", "-", "nan", "NaN"}:
        return float("nan")

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
        return float(text)

    if "." in text:
        parts = text.split(".")
        if len(parts[-1]) == 3 and all(part.isdigit() for part in parts):
            return float("".join(parts))
        return float(text)

    return float(text)


def parse_decimal(value: object) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    text = str(value).strip().replace(",", ".")
    if text in {"", "...", "-", "nan", "NaN"}:
        return float("nan")
    return float(text)


def _decode_dbf_value(raw: bytes, encoding: str) -> str:
    value = raw.decode(encoding, errors="replace").strip()
    return value.replace("ă", "ã").replace("Ă", "Ã")


def read_dbf(data: bytes, encoding: str) -> pd.DataFrame:
    """Read the small DBF tables bundled with the shapefiles."""
    num_records = struct.unpack("<I", data[4:8])[0]
    header_len = struct.unpack("<H", data[8:10])[0]
    record_len = struct.unpack("<H", data[10:12])[0]

    fields: list[tuple[str, str, int, int]] = []
    pos = 32
    while pos < header_len and data[pos] != 0x0D:
        name = data[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", "replace")
        field_type = chr(data[pos + 11])
        length = data[pos + 16]
        decimals = data[pos + 17]
        fields.append((name, field_type, length, decimals))
        pos += 32

    rows: list[dict[str, object]] = []
    for idx in range(num_records):
        record = data[header_len + idx * record_len : header_len + (idx + 1) * record_len]
        if not record or record[0:1] == b"*":
            continue

        cursor = 1
        row: dict[str, object] = {}
        for name, field_type, length, _ in fields:
            raw = record[cursor : cursor + length]
            cursor += length
            value = _decode_dbf_value(raw, encoding)
            if field_type in {"N", "F"}:
                row[name] = parse_decimal(value) if value else np.nan
            else:
                row[name] = value
        rows.append(row)

    return pd.DataFrame(rows)


def _ring_centroid(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    area2 = 0.0
    cx_sum = 0.0
    cy_sum = 0.0

    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        cross = x1 * y2 - x2 * y1
        area2 += cross
        cx_sum += (x1 + x2) * cross
        cy_sum += (y1 + y2) * cross

    if abs(area2) < 1e-12:
        avg_x = float(np.mean([x for x, _ in points]))
        avg_y = float(np.mean([y for _, y in points]))
        return 0.0, avg_x, avg_y

    return area2 / 2.0, cx_sum / (3.0 * area2), cy_sum / (3.0 * area2)


def read_shapefile_centroids(data: bytes) -> pd.DataFrame:
    """Parse polygon centroids from an ESRI Shapefile without external GIS deps."""
    records: list[dict[str, float | int]] = []
    pos = 100

    while pos + 8 <= len(data):
        record_number, content_words = struct.unpack(">ii", data[pos : pos + 8])
        pos += 8
        content_len = content_words * 2
        content = data[pos : pos + content_len]
        pos += content_len

        if len(content) < 4:
            continue

        shape_type = struct.unpack("<i", content[:4])[0]
        if shape_type == 0:
            records.append({"shape_record": record_number, "latitude": np.nan, "longitude": np.nan})
            continue
        if shape_type not in {5, 15, 25}:
            raise ValueError(f"Unsupported shape type {shape_type}")

        xmin, ymin, xmax, ymax = struct.unpack("<4d", content[4:36])
        num_parts, num_points = struct.unpack("<2i", content[36:44])
        part_offsets = list(struct.unpack("<" + "i" * num_parts, content[44 : 44 + 4 * num_parts]))

        points_start = 44 + 4 * num_parts
        flat_points = struct.unpack("<" + "d" * (2 * num_points), content[points_start : points_start + 16 * num_points])
        points = [(flat_points[i], flat_points[i + 1]) for i in range(0, len(flat_points), 2)]

        part_offsets.append(num_points)
        total_area = 0.0
        cx_weighted = 0.0
        cy_weighted = 0.0

        for start, end in zip(part_offsets, part_offsets[1:]):
            area, cx, cy = _ring_centroid(points[start:end])
            total_area += area
            cx_weighted += cx * area
            cy_weighted += cy * area

        if abs(total_area) > 1e-12:
            lon = cx_weighted / total_area
            lat = cy_weighted / total_area
        else:
            lon = (xmin + xmax) / 2.0
            lat = (ymin + ymax) / 2.0

        if not (xmin <= lon <= xmax and ymin <= lat <= ymax):
            lon = (xmin + xmax) / 2.0
            lat = (ymin + ymax) / 2.0

        records.append(
            {
                "shape_record": record_number,
                "latitude": lat,
                "longitude": lon,
                "bbox_xmin": xmin,
                "bbox_ymin": ymin,
                "bbox_xmax": xmax,
                "bbox_ymax": ymax,
                "shape_parts": num_parts,
                "shape_points": num_points,
            }
        )

    return pd.DataFrame(records)


def read_goias_shapes(raw_zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(raw_zip_path) as outer_zip:
        nested = outer_zip.read("GO_Municipios_2025.zip")

    with zipfile.ZipFile(BytesIO(nested)) as shape_zip:
        dbf = read_dbf(shape_zip.read("GO_Municipios_2025.dbf"), encoding="utf-8")
        centroids = read_shapefile_centroids(shape_zip.read("GO_Municipios_2025.shp"))

    shapes = pd.concat([dbf.reset_index(drop=True), centroids.reset_index(drop=True)], axis=1)
    shapes = shapes.rename(
        columns={
            "CD_MUN": "municipality_code",
            "NM_MUN": "municipality_shp",
            "CD_RGI": "immediate_region_code",
            "NM_RGI": "immediate_region",
            "CD_RGINT": "intermediate_region_code",
            "NM_RGINT": "intermediate_region",
            "AREA_KM2": "area_km2_shp",
        }
    )
    shapes["municipality_code"] = shapes["municipality_code"].astype(str)
    shapes["name_key"] = shapes["municipality_shp"].map(normalize_name)
    return shapes


def read_ibge_table(raw_zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(raw_zip_path) as raw_zip:
        with raw_zip.open("tabelaIBGE.csv") as table_file:
            table = pd.read_csv(
                table_file,
                sep=";",
                encoding="utf-8-sig",
                skiprows=4,
                header=None,
                names=[
                    "municipality_code",
                    "municipality_ibge",
                    "population_2022",
                    "area_km2_ibge",
                    "density_2022",
                ],
            )

    table["municipality_code"] = table["municipality_code"].astype(str)
    table["municipality"] = table["municipality_ibge"].str.replace(r"\s*\(GO\)\s*$", "", regex=True)
    table["population_2022"] = table["population_2022"].map(parse_pt_br_number)
    table["area_km2_ibge"] = table["area_km2_ibge"].map(parse_pt_br_number)
    table["density_2022"] = table["density_2022"].map(parse_pt_br_number)
    table["name_key"] = table["municipality"].map(normalize_name)
    return table


def read_consulta(raw_zip_path: Path) -> pd.DataFrame:
    variable_map = {
        "População Estimada - Total (habitantes)": "estimated_population_2022",
        "Matrículas - Total (alunos)": "enrollments_total",
        "Hospitais (número)": "hospitals",
        "Leitos (número)": "beds",
        "Estabelecimentos de Ensino - Total (número)": "schools_total",
        "Produto Interno Bruto per Capita (R$)": "gdp_per_capita_brl",
    }

    with zipfile.ZipFile(raw_zip_path) as raw_zip:
        with raw_zip.open("consulta.csv") as consulta_file:
            raw = pd.read_csv(consulta_file, sep=";", encoding="latin1")

    raw = raw.rename(columns={"Localidade": "municipality_consulta", "Variável": "variable", "2022": "value"})
    raw = raw[raw["variable"].isin(variable_map)].copy()
    raw["name_key"] = raw["municipality_consulta"].map(normalize_name)
    raw["value"] = raw["value"].map(parse_pt_br_number)

    wide = raw.pivot_table(index=["name_key", "municipality_consulta"], columns="variable", values="value", aggfunc="first")
    wide = wide.rename(columns=variable_map).reset_index()

    for col in variable_map.values():
        if col not in wide.columns:
            wide[col] = np.nan

    return wide[["name_key", "municipality_consulta", *variable_map.values()]]


def haversine_matrix(latitudes: Iterable[float], longitudes: Iterable[float]) -> np.ndarray:
    lat = np.radians(np.asarray(list(latitudes), dtype=float))
    lon = np.radians(np.asarray(list(longitudes), dtype=float))

    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2.0) ** 2
    return 6371.0088 * 2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _minmax(values: pd.Series) -> pd.Series:
    clean = values.astype(float)
    min_value = clean.min()
    max_value = clean.max()
    if not np.isfinite(min_value) or not np.isfinite(max_value) or max_value == min_value:
        return pd.Series(np.zeros(len(clean)), index=clean.index)
    return (clean - min_value) / (max_value - min_value)


def add_installation_cost(dataset: pd.DataFrame) -> pd.DataFrame:
    data = dataset.copy()
    population = data["population_2022"].fillna(data["estimated_population_2022"]).fillna(data["population_2022"].median())
    area = data["area_km2"].fillna(data["area_km2"].median())
    gdp = data["gdp_per_capita_brl"].fillna(data["gdp_per_capita_brl"].median())

    pop_score = _minmax(np.log1p(population))
    area_score = _minmax(np.log1p(area))
    gdp_score = _minmax(np.log1p(gdp))

    cost_million = 0.80 + 1.60 * pop_score + 0.50 * area_score + 0.30 * gdp_score
    data["install_cost_brl"] = np.round(cost_million * 1_000_000.0, 2)
    return data


def build_dataset(raw_zip_path: str | Path = "raw/basededados.zip", output_dir: str | Path = "processed") -> dict[str, Path]:
    raw_zip_path = Path(raw_zip_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    shapes = read_goias_shapes(raw_zip_path)
    ibge = read_ibge_table(raw_zip_path)
    consulta = read_consulta(raw_zip_path)

    dataset = shapes.merge(ibge, on="municipality_code", how="left", suffixes=("", "_ibge_join"))
    dataset["municipality"] = dataset["municipality"].fillna(dataset["municipality_shp"])
    dataset["name_key"] = dataset["municipality"].map(normalize_name)
    dataset = dataset.merge(consulta, on="name_key", how="left")

    dataset["area_km2"] = dataset["area_km2_ibge"].fillna(dataset["area_km2_shp"])
    dataset["population_2022"] = dataset["population_2022"].fillna(dataset["estimated_population_2022"])
    dataset["demand_weight"] = dataset["population_2022"] / dataset["population_2022"].sum()
    dataset = add_installation_cost(dataset)

    output_columns = [
        "municipality_code",
        "municipality",
        "latitude",
        "longitude",
        "area_km2",
        "population_2022",
        "density_2022",
        "estimated_population_2022",
        "enrollments_total",
        "hospitals",
        "beds",
        "schools_total",
        "gdp_per_capita_brl",
        "install_cost_brl",
        "demand_weight",
        "immediate_region_code",
        "immediate_region",
        "intermediate_region_code",
        "intermediate_region",
    ]
    dataset = dataset[output_columns].sort_values("municipality").reset_index(drop=True)

    missing_coordinates = dataset[["latitude", "longitude"]].isna().any(axis=1).sum()
    missing_population = dataset["population_2022"].isna().sum()
    if missing_coordinates or missing_population:
        raise ValueError(
            f"Dataset has {missing_coordinates} rows without coordinates and "
            f"{missing_population} rows without population."
        )

    distance_matrix = haversine_matrix(dataset["latitude"], dataset["longitude"])

    dataset_path = output_dir / "goias_facility_locations.csv"
    distance_path = output_dir / "distance_matrix_km.npy"
    config_path = output_dir / "problem_config.json"

    dataset.to_csv(dataset_path, index=False, encoding="utf-8")
    np.save(distance_path, distance_matrix)

    median_cost = float(dataset["install_cost_brl"].median())
    config = {
        "dataset": str(dataset_path.as_posix()),
        "distance_matrix": str(distance_path.as_posix()),
        "n_municipalities": int(len(dataset)),
        "total_population": int(dataset["population_2022"].sum()),
        "default_k": DEFAULT_K,
        "default_radius_km": DEFAULT_RADIUS_KM,
        "default_budget_brl": round(1.08 * DEFAULT_K * median_cost, 2),
        "cost_model": "0.80M + normalized log(population), log(area), log(gdp_per_capita)",
        "distance_model": "Haversine over SIRGAS 2000 municipality polygon centroids",
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    return {
        "dataset": dataset_path,
        "distance_matrix": distance_path,
        "config": config_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Goias facility-location dataset.")
    parser.add_argument("--raw-zip", default="raw/basededados.zip", help="Path to basededados.zip.")
    parser.add_argument("--output-dir", default="processed", help="Directory where processed files are written.")
    args = parser.parse_args()

    paths = build_dataset(raw_zip_path=args.raw_zip, output_dir=args.output_dir)
    print("Dataset generated:")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
