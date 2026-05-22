import re
from pathlib import Path

TIMESTAMP_REGEX = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}(?::\d{2})?[^-]*- ")


def read_messages(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
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


def strip_timestamp(message: str) -> str:
    match = TIMESTAMP_REGEX.match(message)
    content = message[match.end():].strip() if match else message.strip()
    if ": " in content:
        _, message_body = content.split(": ", 1)
        return message_body.strip()
    return content


def dedupe_messages(messages):
    seen = set()
    deduped = []
    for message in messages:
        text = strip_timestamp(message)
        if text not in seen:
            seen.add(text)
            deduped.append(message)
    return deduped


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Deduplicate WhatsApp exported text by exact message content.")
    parser.add_argument("input", help="Path to exported WhatsApp .txt file")
    parser.add_argument("--output", help="Output path for deduplicated file")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    messages = read_messages(input_path)
    deduped = dedupe_messages(messages)

    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_deduped.txt")
    output_path.write_text("\n".join(deduped), encoding="utf-8")

    print(f"Input messages: {len(messages)}")
    print(f"Unique messages: {len(deduped)}")
    print(f"Saved deduplicated output to: {output_path}")


if __name__ == "__main__":
    main()
