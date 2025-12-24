# extract_ioc_from_pdf.py
# -*- coding: utf-8 -*-

import pdfplumber
from ioc_finder import find_iocs
import argparse
import os


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
    """
    iocs = find_iocs(text)
    return iocs


def pretty_print_iocs(iocs: dict):
    """
    In IOC ra màn hình theo từng loại.
    """
    if not iocs:
        print("[!] Không tìm thấy IOC nào.")
        return

    # Các key phổ biến trong ioc-finder: domains, urls, ipv4s, ipv6s, emails, md5s, sha1s, sha256s,...
    for key, values in iocs.items():
        if not values:
            continue
        print(f"\n=== {key.upper()} ({len(values)}) ===")
        for v in sorted(set(values)):
            print(v)


def main():
    parser = argparse.ArgumentParser(
        description="Extract IOCs from a PDF report using ioc-finder."
    )
    parser.add_argument(
        "pdf_path",
        help="Đường dẫn tới file PDF (VD: report.pdf)",
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path

    if not os.path.isfile(pdf_path):
        print(f"[!] File không tồn tại: {pdf_path}")
        return

    print(f"[*] Đang đọc PDF: {pdf_path}")
    text = read_pdf_to_text(pdf_path)

    if not text.strip():
        print("[!] Không trích xuất được text từ PDF (có thể là file scan/ảnh).")
        return

    print("[*] Đang trích xuất IOC bằng ioc-finder...")
    iocs = extract_iocs_from_text(text)

    print("\n================ KẾT QUẢ IOC ================")
    pretty_print_iocs(iocs)


if __name__ == "__main__":
    main()
