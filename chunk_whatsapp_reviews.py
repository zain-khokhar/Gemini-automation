import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

TIMESTAMP_REGEX = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}(?::\d{2})?[^-]*- ")
SUBJECT_PATTERNS = [
    re.compile(r"subject(?: name)?\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9\s\-_/&]*)", re.IGNORECASE),
    re.compile(r"subject code\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9\s\-_/&]*)", re.IGNORECASE),
    re.compile(r"paper review\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9\s\-_/&]*)", re.IGNORECASE),
    re.compile(r"paper\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9\s\-_/&]*)", re.IGNORECASE),
    re.compile(r"^\*?([A-Za-z]{2,5}\s*\d{2,3}P?)\b", re.IGNORECASE),
    re.compile(r"\b([A-Za-z]{2,5}\d{2,3}P?)\b", re.IGNORECASE),
]


def read_messages(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    messages = []
    current = None
    for line in lines:
        if TIMESTAMP_REGEX.match(line):
            if current is not None:
                messages.append(current)
            current = line
        else:
            if current is None:
                current = line
            else:
                current += "\n" + line
    if current is not None:
        messages.append(current)
    return messages


def get_message_body(message: str) -> str:
    match = TIMESTAMP_REGEX.match(message)
    if match:
        body = message[match.end():].strip()
    else:
        body = message.strip()
    return body


def normalize_subject(subject: str) -> str:
    subject = subject.strip()
    subject = re.sub(r"\s+", " ", subject)
    subject = subject.upper()
    subject = subject.replace("SUBJECT", "").strip()
    subject = re.sub(r"[^A-Z0-9 P\-_/&]", "", subject)
    subject = re.sub(r"\s+", " ", subject)
    return subject


def extract_subjects(text: str):
    subjects = []
    for pattern in SUBJECT_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(1).strip()
            if raw:
                normalized = normalize_subject(raw)
                if normalized and normalized not in subjects:
                    subjects.append(normalized)
        if subjects:
            break
    if not subjects:
        return ["UNKNOWN"]
    return subjects


def count_words(text: str) -> int:
    return len(text.split())


def chunk_reviews(messages, max_words):
    chunks = []
    current = []
    current_words = 0
    for message in messages:
        body = get_message_body(message)
        review_words = count_words(body)
        if current and current_words + review_words > max_words:
            chunks.append(current)
            current = []
            current_words = 0
        current.append(message)
        current_words += review_words
    if current:
        chunks.append(current)
    return chunks


def write_chunks(chunks, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    filenames = []
    for idx, chunk in enumerate(chunks, start=1):
        filename = output_dir / f"reviews_chunk_{idx:03d}.txt"
        filename.write_text("\n".join(chunk), encoding="utf-8")
        filenames.append(filename)
    return filenames


def build_summary(messages, chunks, output_dir: Path):
    subject_counter = Counter()
    subject_reviews = defaultdict(list)
    for idx, message in enumerate(messages, start=1):
        body = get_message_body(message)
        subjects = extract_subjects(body)
        for subject in subjects:
            subject_counter[subject] += 1
            subject_reviews[subject].append(idx)

    summary_lines = [
        f"Total messages/reviews: {len(messages)}",
        f"Total chunk files: {len(chunks)}",
        "",
        "Subjects found and review counts:",
    ]
    for subject, count in subject_counter.most_common():
        summary_lines.append(f"{subject}: {count}")
    summary_lines.append("")
    summary_lines.append("Chunk files detail:")
    for idx, chunk in enumerate(chunks, start=1):
        chunk_words = sum(count_words(get_message_body(msg)) for msg in chunk)
        summary_lines.append(f"reviews_chunk_{idx:03d}.txt - {len(chunk)} reviews, {chunk_words} words")

    summary_file = output_dir / "subjects_summary.txt"
    summary_file.write_text("\n".join(summary_lines), encoding="utf-8")

    json_file = output_dir / "subjects_summary.json"
    data = {
        "total_reviews": len(messages),
        "total_chunks": len(chunks),
        "chunks": [
            {
                "filename": f"reviews_chunk_{idx:03d}.txt",
                "reviews": len(chunk),
                "words": sum(count_words(get_message_body(msg)) for msg in chunk),
            }
            for idx, chunk in enumerate(chunks, start=1)
        ],
        "subjects": [
            {"subject": subject, "count": count, "review_indices": subject_reviews[subject]}
            for subject, count in subject_counter.most_common()
        ],
    }
    json_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return summary_file, json_file


def main():
    parser = argparse.ArgumentParser(description="Chunk WhatsApp review file into review-wise files and build subject summary.")
    parser.add_argument("input", help="Deduplicated WhatsApp export text file")
    parser.add_argument("--output-dir", help="Output directory for chunk files", default=None)
    parser.add_argument("--max-words", type=int, help="Maximum words per chunk file", default=10000)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    messages = read_messages(input_path)
    chunks = chunk_reviews(messages, args.max_words)
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent / (input_path.stem + "_chunks")
    write_chunks(chunks, output_dir)
    summary_file, json_file = build_summary(messages, chunks, output_dir)

    print(f"Total reviews/messages: {len(messages)}")
    print(f"Generated {len(chunks)} chunk files in: {output_dir}")
    print(f"Summary text: {summary_file}")
    print(f"Summary JSON: {json_file}")


if __name__ == "__main__":
    main()
