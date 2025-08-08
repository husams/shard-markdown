# Test encoding
data = b"\xff\xfe# Invalid encoding content"

encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
for enc in encodings:
    try:
        result = data.decode(enc)
        print(f"{enc}: SUCCESS - First 20 chars: {repr(result[:20])}")
    except UnicodeDecodeError as e:
        print(f"{enc}: FAILED - {e}")
