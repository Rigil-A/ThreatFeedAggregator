# extract_ioc_to_json.py
# -*- coding: utf-8 -*-

import pdfplumber
from ioc_finder import find_iocs
import argparse
import os
import json


def read_pdf_to_text(pdf_path: str) -> str:
    """
    Đọc toàn bộ text từ file PDF.
    """
    all_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                all_text.append(page_text)
            else:
                print(f"[!] Trang {page_num} không trích xuất được text (có thể là scan/ảnh).")
    return "\n".join(all_text)


def extract_iocs_from_text(text: str) -> dict:
    """
    Dùng ioc-finder để trích xuất IOC từ text.
    Có thể truyền thêm options nếu muốn.
    """
    iocs = find_iocs(
        text,
        parse_domain_from_url=True,
        parse_from_url_path=True,
        parse_domain_from_email_address=True,
        parse_address_from_cidr=True,
        parse_urls_without_scheme=True,
        parse_imphashes=True,
        parse_authentihashes=True,
    )
    return iocs


def main():
    parser = argparse.ArgumentParser(
        description="Extract IOCs from a PDF report using ioc-finder and save to JSON."
    )
    parser.add_argument(
        "pdf_path",
        help="Đường dẫn tới file PDF (VD: report.pdf)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Đường dẫn file JSON output (mặc định: cùng tên PDF nhưng .json)",
        default=None,
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path

    if not os.path.isfile(pdf_path):
        print(f"[!] File không tồn tại: {pdf_path}")
        return

    # Nếu không truyền -o/--output thì tự sinh tên file JSON
    if args.output is None:
        base, _ = os.path.splitext(pdf_path)
        output_path = base + "_iocs.json"
    else:
        output_path = args.output

    print(f"[*] Đang đọc PDF: {pdf_path}")
    text = read_pdf_to_text(pdf_path)

    if not text.strip():
        print("[!] Không trích xuất được text từ PDF (có thể là file scan/ảnh).")
        return

    print("[*] Đang trích xuất IOC bằng ioc-finder...")
    iocs = extract_iocs_from_text(text)

    print(f"[*] Đang lưu IOC ra file JSON: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(iocs, f, indent=2, ensure_ascii=False)

    print("[+] Hoàn thành. Bạn có thể mở file JSON để xem chi tiết các IOC.")


if __name__ == "__main__":
    main()
