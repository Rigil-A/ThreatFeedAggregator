# normalizers/ioc_normalizer.py

import re
from models.ioc import IOC, detect_ioc_type, is_private_ip, is_valid_domain

def clean_value(value: str) -> str:
    value = value.strip().strip(",").strip(";").strip("[](){}")
    value = value.replace("\\", "")
    return value.lower()


def normalize_ioc(value: str, feed) -> IOC | None:
    """
    Chuẩn hoá và validate IOC.
    Trả về IOC object hoặc None nếu IOC không hợp lệ.
    """

    raw = clean_value(value)
    if not raw:
        return None

    ioc_type = detect_ioc_type(raw)

    # ------------------------------------
    # 1) Loại bỏ invalid
    # ------------------------------------
    if ioc_type == "ip" and is_private_ip(raw):
        return None

    if ioc_type == "domain" and not is_valid_domain(raw):
        return None

    if ioc_type == "unknown":
        return None

    # ------------------------------------
    # 2) Build metadata
    # ------------------------------------
    metadata = {
        "length": len(raw),
        "has_dot": "." in raw,
        "starts_with_www": raw.startswith("www.")
    }

    return IOC(
        value=raw,
        ioc_type=ioc_type,
        source=feed.provider,
        feed_name=feed.name,
        metadata=metadata
    )


def normalize_bulk(iocs: list[str], feed) -> list[IOC]:
    """
    Nhận list string IOC -> trả về list IOC object đã chuẩn hoá.
    Loại trùng lặp + invalid IOC.
    """
    seen = set()
    result = []

    for raw in iocs:
        normalized = normalize_ioc(raw, feed)
        if not normalized:
            continue

        if normalized.value in seen:
            continue

        seen.add(normalized.value)
        result.append(normalized)

    return result
