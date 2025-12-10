# -*- coding: utf-8 -*-
"""
Script trích xuất TTP từ báo cáo (TXT hoặc PDF) bằng model TTPXHunter trên Hugging Face.

Yêu cầu:
- pip install torch transformers nltk pdfplumber
- Có các file:
    - label_dict.pkl
    - ttp_id_name.pkl
    - report .txt hoặc .pdf
"""

import torch
import pickle
import nltk
import pdfplumber
from transformers import RobertaForSequenceClassification, RobertaTokenizer

# Nếu lần đầu dùng nltk.sent_tokenize thì cần tải punkt
# Chỉ cần chạy 1 lần (có thể comment lại sau khi tải xong)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
    
nltk.download('punkt_tab')

# =========================
# 1. Load model & tokenizer
# =========================

MODEL_NAME = "nanda-rani/TTPXHunter"

print("[*] Đang load model và tokenizer từ Hugging Face...")

model = RobertaForSequenceClassification.from_pretrained(MODEL_NAME)
tokenizer = RobertaTokenizer.from_pretrained(MODEL_NAME)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()  # đặt ở chế độ evaluation

print(f"[*] Sử dụng device: {device}")


# =========================
# 2. Các hàm tiện ích xử lý text
# =========================

def remove_consecutive_newlines(text: str) -> str:
    """
    Xoá các newline liên tiếp, chỉ giữ tối đa 1.
    Ví dụ: '\n\n\n' -> '\n'
    """
    if not text:
        return text
    cleaned_text = text[0]
    for char in text[1:]:
        if not (char == cleaned_text[-1] and cleaned_text[-1] == '\n'):
            cleaned_text += char
    return cleaned_text


# =========================
# 3. Hàm core: dịch TTP ID -> tên
# =========================

def translate_ttp_ids_to_names(ttp_ids, ttpid2name_path):
    """
    Translate TTP (Tactics, Techniques, and Procedures) IDs to human-readable names.

    Args:
    - ttp_ids (list of str): List of TTP IDs (ví dụ ["T1059", "T1566", ...]).
    - ttpid2name_path (str): Đường dẫn file pickle chứa mapping id -> name.

    Returns:
    - list of str: Corresponding human-readable names for the TTP IDs.
    """
    with open(ttpid2name_path, 'rb') as file:
        id_to_name_map = pickle.load(file)

    ttp_names = [id_to_name_map[ttp_id] for ttp_id in ttp_ids if ttp_id in id_to_name_map]

    return ttp_names


# =========================
# 4. Hàm core: chạy model trên các câu
# =========================

def extract_ttp_from_sentences(sentences, threshold, label_dict_path, ttpid2name_path):
    """
    Extract TTP (Tactics, Techniques, and Procedures) based on a prediction threshold from the given sentences.

    Args:
    - sentences (list of str): List of sentences to extract TTP from.
    - threshold (float): Confidence threshold for accepting predictions.
    - label_dict_path (str): Đường dẫn file pickle mapping label -> integer id.
    - ttpid2name_path (str): Đường dẫn file pickle mapping TTP ID -> tên.

    Returns:
    - unique_ttp_ids (list of str): Unique TTP IDs extracted from the sentences (ví dụ ["T1059", ...]).
    - names_for_ttp_ids (list of str): Human-readable names corresponding to the TTP IDs.
    """
    predictions = []

    print(f"[*] Tổng số câu cần xử lý: {len(sentences)}")

    # Loop over sentences and perform inference
    for idx, text in enumerate(sentences):
        text = text.strip()
        if not text:
            continue

        # Tokenize the input text
        inputs = tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt"
        ).to(device)

        # Perform inference without gradient tracking
        with torch.no_grad():
            outputs = model(**inputs)

        # Extract logits and compute probabilities
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
        max_prob, predicted_class_indices = torch.max(probabilities, dim=1)

        # Filter predictions based on the confidence threshold
        predicted_labels = [
            model.config.id2label[class_idx.item()]
            for prob, class_idx in zip(max_prob, predicted_class_indices)
            if prob.item() > threshold
        ]

        predictions.extend(predicted_labels)

    print(f"[*] Số prediction vượt threshold: {len(predictions)}")

    if not predictions:
        return [], []

    # Map the predicted labels to integer labels
    # Giả sử label có dạng "TTP_37" hoặc "LABEL_12"
    mapped_labels = [int(label.split('_')[1]) for label in predictions]

    # Load the label-to-id dictionary
    with open(label_dict_path, 'rb') as file:
        label_dict = pickle.load(file)

    # Invert the dictionary to map integer labels to TTP IDs (ví dụ 37 -> "T1059")
    inverted_label_dict = {v: k for k, v in label_dict.items()}
    ttp_list = [inverted_label_dict[label] for label in mapped_labels if label in inverted_label_dict]

    # Extract unique TTP IDs
    unique_ttp_ids = list(set(ttp_list))

    # Translate TTP IDs to their names
    names_for_ttp_ids = translate_ttp_ids_to_names(unique_ttp_ids, ttpid2name_path)

    return unique_ttp_ids, names_for_ttp_ids


# =========================
# 5. Hàm xử lý TEXT (string) chung
# =========================

def process_text_for_attack_patterns(text, threshold, label_dict_path, ttpid2name_path):
    """
    Nhận trực tiếp text (string), xử lý & trích xuất TTP.

    Args:
    - text (str): Nội dung báo cáo dưới dạng string.
    - threshold (float): Confidence threshold.
    - label_dict_path (str): Đường dẫn label_dict.pkl.
    - ttpid2name_path (str): Đường dẫn ttp_id_name.pkl.

    Returns:
    - tuple: (unique TTP IDs, names corresponding to TTP IDs).
    """
    # Clean the text by removing consecutive newlines and tabs
    text = remove_consecutive_newlines(text)
    text = text.replace('\t', ' ').replace("\\'", "'")

    # Tokenize sentences
    tokenized_sentences = nltk.sent_tokenize(text)

    # Split tokenized sentences by newlines and filter empty lines
    sentences = []
    for sentence in tokenized_sentences:
        sentences += [line for line in sentence.split('\n') if len(line.strip()) > 0]

    # Extract TTP from the processed sentences
    return extract_ttp_from_sentences(sentences, threshold, label_dict_path, ttpid2name_path)


# =========================
# 6. Hàm đọc TXT file
# =========================

def process_txt_file_for_attack_patterns(file_name, threshold, label_dict_path, ttpid2name_path):
    """
    Read and process a text file to extract attack patterns using TTP extraction.

    Args:
    - file_name (str): Path to the input text file.
    - threshold (float): Confidence threshold for TTP extraction.

    Returns:
    - tuple: (unique TTP IDs, names corresponding to TTP IDs).
    """
    with open(file_name, 'r', encoding='utf-8') as file:
        text = file.read()

    return process_text_for_attack_patterns(text, threshold, label_dict_path, ttpid2name_path)


# =========================
# 7. Hàm đọc PDF file
# =========================

def read_pdf_to_text(pdf_path):
    """
    Đọc toàn bộ text từ file PDF bằng pdfplumber.
    """
    all_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text.append(page_text)
    return "\n".join(all_text)


def process_pdf_for_attack_patterns(pdf_path, threshold, label_dict_path, ttpid2name_path):
    """
    Đọc và xử lý file PDF để trích xuất TTP.
    """
    text = read_pdf_to_text(pdf_path)
    return process_text_for_attack_patterns(text, threshold, label_dict_path, ttpid2name_path)


# =========================
# 8. Ví dụ sử dụng
# =========================

if __name__ == "__main__":
    # Đường dẫn các file mapping
    label_dict_path = "label_dict.pkl"
    ttpid2name_path = "ttp_id_name.pkl"

    # Ngưỡng confidence
    threshold = 0.644

    # ====== Ví dụ 1: xử lý file TXT ======
    # txt_report = "SharpPanda_APT_Campaign_Expands_its_Arsenal_Targeting_G20_Nations.txt"
    # ttps, ttp_names = process_txt_file_for_attack_patterns(
    #     txt_report,
    #     threshold,
    #     label_dict_path,
    #     ttpid2name_path
    # )

    # ====== Ví dụ 2: xử lý file PDF ======
    pdf_report = "Symantec_Seedworm-Iranian-Hackers-Target-Telecoms-Orgs-North-East-Africa(12-19-2023).pdf"
    ttps, ttp_names = process_pdf_for_attack_patterns(
        pdf_report,
        threshold,
        label_dict_path,
        ttpid2name_path
    )

    print("\n=== Kết quả TTP trích xuất được ===")
    print(f"Tổng số TTP (unique): {len(ttps)}\n")

    for ttp_id, ttp_name in zip(ttps, ttp_names):
        print(f"{ttp_id} - {ttp_name}")
