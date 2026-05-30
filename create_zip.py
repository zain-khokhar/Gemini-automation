import os
import zipfile

source_dir = r"e:\desktop\gemini-json"
zip_path = r"e:\desktop\Gemini-MCQ-Sync.zip"

exclude_dirs = {'.git', 'node_modules', '__pycache__', 'session', 'build', 'dist', 'installer'}
exclude_files = {'MCQ-Extractor.exe', 'test_sync.py'}

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file in exclude_files or file.endswith('.zip') or file.endswith('.db'):
                continue
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, source_dir)
            zipf.write(file_path, arcname)

print("Done creating zip!")
