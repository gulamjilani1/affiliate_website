import os
from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXT = {"png","jpg","jpeg","gif","webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXT

def save_image(file_storage):
    """Save uploaded image into static/images and return filename (or None)."""
    if not file_storage:
        return None
    filename = secure_filename(file_storage.filename)
    folder = os.path.join(current_app.root_path, "static", "images")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    file_storage.save(path)
    return filename
