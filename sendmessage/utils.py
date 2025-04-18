# utils.py
import os
from werkzeug.utils import secure_filename
from datetime import datetime

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file(file, user_id=None):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        folder_name = f"user_{user_id}" if user_id else datetime.now().strftime('%Y-%m-%d')
        upload_folder = os.path.join(os.getcwd(), 'uploads', folder_name)

        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        return f'/uploads/{folder_name}/{filename}'
    return None
