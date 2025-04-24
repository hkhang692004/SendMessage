import uuid

import eventlet
from werkzeug.utils import secure_filename

eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from sendmessage import db, app, dao, login_manager, socketio
from models import User, Message, Attachment, Conversation
import cloudinary.uploader
import os
from utils import upload_file
from flask_login import login_required, current_user
from datetime import datetime, timezone
from flask_socketio import emit, join_room

from sendmessage.dao import add_user


@app.route('/')
def home():
    return render_template('index.html')


# Route đăng ký người dùng
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']
        name = request.form['name']

        # Kiểm tra nếu mật khẩu trùng khớp
        if password != confirm_password:
            flash('Mật khẩu không khớp!', 'error')
            return redirect(url_for('register'))

        # Kiểm tra nếu username đã tồn tại
        if User.query.filter_by(username=username).first():
            flash('Username đã tồn tại!', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email đã tồn tại!', 'error')
            return redirect(url_for('register'))


        # Xử lý avatar
        avatar_file = request.files.get('avatar')
        if avatar_file:
            upload_result = cloudinary.uploader.upload(avatar_file)
            avatar_url = upload_result['secure_url']
        else:
            avatar_url = 'https://res.cloudinary.com/dblzpkokm/image/upload/v1744450061/defaultuserimg_prr7d2.jpg'

        # Tạo người dùng mới
        new_user = add_user(username, password, email, name, avatar_url)
        flash('Đăng ký thành công!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Route đăng nhập người dùng
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Vui lòng nhập đầy đủ tên người dùng và mật khẩu.", 'info')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('messages'))
        else:
            flash('Tên người dùng hoặc mật khẩu không đúng!', 'error')
    return render_template('login.html')


@app.route('/messages', methods=['GET', 'POST'])
@login_required
def messages():
    user = current_user  # từ Flask-Login
    conversations = user.conversations1.union(user.conversations2).all()

    # Xử lý tìm kiếm người dùng qua email
    email_search = request.args.get('email_search')
    if email_search:
        search_results = User.query.filter(User.email.like(f'%{email_search}%')).all()
    else:
        search_results = []

    return render_template(
        'messages.html',
        conversations=conversations,
        search_results=search_results,
        email_search=email_search,
        current_user=user
    )


@app.route('/chat/<partner_email>', methods=['GET', 'POST'])
@login_required
def chat_with_partner(partner_email):
    partner = User.query.filter_by(email=partner_email).first_or_404()

    # Tìm hoặc tạo cuộc trò chuyện giữa 2 người
    conversation = Conversation.query.filter(
        ((Conversation.user1_id == current_user.id) & (Conversation.user2_id == partner.id)) |
        ((Conversation.user1_id == partner.id) & (Conversation.user2_id == current_user.id))
    ).first()

    if not conversation:
        conversation = Conversation(user1_id=current_user.id, user2_id=partner.id)
        db.session.add(conversation)
        db.session.commit()

    # POST: Gửi tin nhắn
    if request.method == 'POST':
        content = request.form.get('content', '')
        file = request.files.get('file')

        if content.strip() or file:
            # Tạo tin nhắn mới
            message = Message(
                conversation_id=conversation.id,
                sender_id=current_user.id,
                content=content.strip(),
                is_read=False
            )
            db.session.add(message)
            db.session.flush()  # Flush để lấy ID của tin nhắn mới

            # Nếu có tệp đính kèm, upload lên Cloudinary và lưu vào Attachment
            if file and file.filename != '':
                try:
                    # Lấy kích thước file
                    file_size = len(file.read())
                    file.seek(0)  # Reset lại vị trí đọc file

                    # Lấy loại file từ phần mở rộng
                    file_type = os.path.splitext(file.filename)[1][1:].lower()

                    # Upload lên Cloudinary
                    upload_result = cloudinary.uploader.upload(file, resource_type="auto")
                    file_url = upload_result.get("secure_url")

                    # Tạo bản ghi Attachment
                    attachment = Attachment(
                        message_id=message.id,
                        file_url=file_url,
                        file_type=file_type,
                        file_size=file_size,
                        original_filename=file.filename
                    )
                    db.session.add(attachment)
                except Exception as e:
                    # Xử lý lỗi nếu có
                    current_app.logger.error(f"Lỗi khi upload file: {str(e)}")

            db.session.commit()

        return redirect(url_for('chat_with_partner', partner_email=partner.email))

    # GET: hiển thị tin nhắn
    messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.timestamp.asc()).all()

    # Đánh dấu các tin nhắn của đối phương là đã đọc
    unread_messages = Message.query.filter_by(
        conversation_id=conversation.id,
        sender_id=partner.id,
        is_read=False
    ).all()

    for msg in unread_messages:
        msg.is_read = True

    if unread_messages:
        db.session.commit()

    return render_template(
        'chatbox.html',
        partner=partner,
        messages=messages,
        conversation=conversation
    )


@app.route('/logout')
def logout():
    logout_user()  # Xóa thông tin người dùng khỏi session
    flash('Bạn đã đăng xuất', 'info')
    return redirect(url_for('login'))


@app.route("/send-message-with-file", methods=["POST"])
@login_required
def send_message_with_file():
    # Lấy thông tin từ form
    sender_id = request.form.get("sender_id")
    conversation_id = request.form.get("conversation_id")
    content = request.form.get("content", "")
    partner_id=request.form.get("partner_id")


    # Tạo message và giữ nguyên nội dung ban đầu
    message = Message(
        content=content,
        sender_id=sender_id,
        conversation_id=conversation_id,
    )
    db.session.add(message)
    db.session.commit()

    file_url = None
    file_type = None
    original_filename = None
    file_size = None

    # Xử lý file nếu có
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '':
            # Lưu lại tên file gốc
            original_filename = file.filename

            # Lấy phần mở rộng của file
            file_extension = ''
            if '.' in original_filename:
                file_extension = original_filename.rsplit('.', 1)[1].lower()
                file_type = file_extension

            # Xác định loại tài nguyên dựa trên phần mở rộng
            resource_type = "auto"
            document_extensions = ['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'pdf', 'txt', 'rtf']
            if file_extension.lower() in document_extensions:
                resource_type = "raw"

            # Tạo public_id với UUID để tránh trùng lặp
            file_uuid = uuid.uuid4()
            public_id = f"attachments/{file_uuid}"

            # Upload file lên Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                resource_type=resource_type,
                public_id=public_id,
                use_filename=True,
                unique_filename=True,
                overwrite=False,
            )

            # Tạo URL phù hợp cho việc tải xuống
            file_url = upload_result['secure_url']
            file_size = upload_result.get('bytes', 0)

            # Đối với tệp raw (tài liệu), thêm thông số fl_attachment để đảm bảo tải xuống đúng
            if resource_type == "raw":
                from urllib.parse import quote
                if "fl_attachment" not in file_url:
                    file_url = f"{file_url}?fl_attachment={quote(original_filename)}"

            try:
                # Lưu attachment với message_id đã tạo
                new_attachment = Attachment(
                    message_id=message.id,
                    file_url=file_url,
                    file_type=file_extension,
                    file_size=file_size,
                    original_filename=original_filename
                )
                db.session.add(new_attachment)
                db.session.commit()

            except Exception as e:
                db.session.rollback()
                print(f"Error saving attachment: {str(e)}")
                return jsonify({"error": str(e)}), 500

    # Phát tin nhắn cho mọi người trong phòng
    emit_data = {
        "id": message.id,
        "content": message.content,
        "sender_id": sender_id,
        "conversation_id": conversation_id,
        "timestamp": message.timestamp.isoformat()
    }

    # Thêm thông tin về attachment
    if file_url:
        emit_data["has_attachment"] = True
        emit_data["file_url"] = file_url
        emit_data["file_type"] = file_type
        emit_data["original_filename"] = original_filename
        emit_data["file_size"] = file_size

    socketio.emit("receive_message", emit_data, room=conversation_id)
    socketio.emit("new_conv", {'msg': 'new conversation'}, room=str(partner_id), namespace='/', to=str(partner_id))
    # Trả về kết quả
    return jsonify({
        "status": "success",
        "message_id": message.id
    })


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Lưu lại tên file gốc
    original_filename = file.filename

    # Lấy phần mở rộng của file
    file_extension = ''
    if '.' in original_filename:
        file_extension = original_filename.rsplit('.', 1)[1].lower()

    # Xác định loại tài nguyên dựa trên phần mở rộng
    resource_type = "auto"

    # Kiểm tra nếu là file văn bản (như Word, Excel, PDF...)
    document_extensions = ['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'pdf', 'txt', 'rtf']
    if file_extension.lower() in document_extensions:
        resource_type = "raw"

    # Tạo public_id với UUID để tránh trùng lặp
    import uuid
    file_uuid = uuid.uuid4()
    public_id = f"attachments/{file_uuid}"

    # Upload file lên Cloudinary
    upload_result = cloudinary.uploader.upload(
        file,
        resource_type=resource_type,
        public_id=public_id,
        use_filename=True,  # Sử dụng tên file gốc
        unique_filename=True,  # Đảm bảo tên file là duy nhất
        overwrite=False,  # Không ghi đè nếu file đã tồn tại
    )

    # Tạo URL phù hợp cho việc tải xuống
    file_url = upload_result['secure_url']

    # Đối với tệp raw (tài liệu), thêm thông số fl_attachment để đảm bảo tải xuống đúng
    display_filename = original_filename  # Tên hiển thị mặc định

    if resource_type == "raw":
        from urllib.parse import quote
        # Đảm bảo URL không chứa tham số fl_attachment nếu đã có
        if "fl_attachment" not in file_url:
            # Thêm tham số fl_attachment vào URL, nhưng lưu tên file riêng để hiển thị
            file_url = f"{file_url}?fl_attachment={quote(original_filename)}"

    message_id = request.form.get('message_id', None)
    print(f"Message ID received: {message_id}")

    # Nếu đang truyền vào
    try:
        if message_id:
            new_attachment = Attachment(
                message_id=message_id,
                file_url=file_url,
                file_type=file_extension,
                file_size=upload_result.get('bytes', 0),
                original_filename=original_filename
            )
            db.session.add(new_attachment)
            db.session.commit()
            print(f"Attachment created with ID: {new_attachment.id}")  # Log ID mới tạo
    except Exception as e:
        db.session.rollback()
        print(f"Error saving attachment: {str(e)}")

    return jsonify({
        "url": file_url,  # URL của file đã được điều chỉnh
        "filename": original_filename,  # Tên file gốc để hiển thị
        "display_filename": display_filename,  # Tên hiển thị (có thể sử dụng riêng cho UI)
        "file_type": file_extension,  # Phần mở rộng của file
        "public_id": upload_result.get('public_id', ''),  # ID công khai của file
        "bytes": upload_result.get('bytes', 0),  # Kích thước file
        "uuid": str(file_uuid)  # UUID của file để có thể tìm kiếm dễ dàng trong DB
    })


@app.route('/get_conversations', methods=['GET'])
def get_conversations():
    # Lấy danh sách cuộc trò chuyện từ cơ sở dữ liệu
    conversations = Conversation.query.filter_by(user_id=current_user.id).all()
    conversation_data = []

    for conv in conversations:
        partner = conv.get_partner(current_user.id)
        conversation_data.append({
            'id': conv.id,
            'partner_name': partner.name,
            'partner_email': partner.email,
            'partner_avatar': partner.avatar_url or url_for('static', filename='default-avatar.png'),
            'chat_url': url_for('chat_with_partner', partner_email=partner.email),
        })

    return jsonify(conversation_data)


@login_manager.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)

@socketio.on('connect')
def handle_join():
    room = str(current_user.id)
    join_room(room)

@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)


@socketio.on("send_message")
def handle_send_message(data):
    content = data.get("content", "")
    sender_id = data.get("sender_id")
    conversation_id = data.get("conversation_id")
    partner_id=data.get("partner_id")

    # Tạo tin nhắn mới trong DB
    message = Message(
        content=content,
        sender_id=sender_id,
        conversation_id=conversation_id,
    )
    db.session.add(message)
    db.session.commit()

    # Phát ra tin nhắn cho mọi người trong phòng
    emit("receive_message", {
        "id": message.id,
        "content": content,
        "sender_id": sender_id,
        "conversation_id": conversation_id,
        "timestamp": message.timestamp.isoformat()
    }, room=conversation_id)

    # Trả về message_id
    emit("message_sent", {
        "message_id": message.id
    }, room=request.sid)
    emit("new_conv", {'msg': 'new conversation'}, room=str(partner_id), namespace='/', to=str(partner_id))

if __name__ == "__main__":
    socketio.run(app, debug=True)
