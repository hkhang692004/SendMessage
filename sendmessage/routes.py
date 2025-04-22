import eventlet

eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from sendmessage import db, app, dao, login_manager, socketio
from models import User, Message, Attachment, Conversation
import cloudinary.uploader
import os
from utils import upload_file
from flask_login import login_required, current_user
from datetime import datetime
from flask_socketio import emit, join_room

from sendmessage.dao import add_user


@app.route('/')
def home():
    return render_template('index.html')  # Trả về template index.html


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
            msg_text = content.strip()

            # Nếu có tệp đính kèm, upload lên Cloudinary (hoặc lưu local)
            if file and file.filename != '':
                upload_result = cloudinary.uploader.upload(file)
                file_url = upload_result.get("secure_url")
                msg_text += f" [Tệp đính kèm: {file_url}]"

            message = Message(
                conversation_id=conversation.id,
                sender_id=current_user.id,
                content=msg_text,
                is_read=False  # Mặc định tin nhắn là chưa đọc
            )
            db.session.add(message)
            db.session.commit()

        return redirect(url_for('chat_with_partner', partner_email=partner.email))

    # GET: hiển thị tin nhắn
    messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.timestamp.asc()).all()

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

import cloudinary.uploader
from flask import request, jsonify

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

    # Upload file lên Cloudinary
    upload_result = cloudinary.uploader.upload(file, resource_type="auto")

    return jsonify({
        "url": upload_result['secure_url'],  # URL của file
        "filename": original_filename  # Tên file gốc
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


@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)


@socketio.on('send_message')
def handle_send_message(data):
    content = data['content']
    sender_id = data['sender_id']
    conversation_id = data['conversation_id']

    # Lưu vào CSDL
    message = Message(content=content, sender_id=sender_id, conversation_id=conversation_id)
    db.session.add(message)
    db.session.commit()

    # Sau đó phát lại tới người nhận
    emit('receive_message', {
        'content': content,
        'sender_id': sender_id,
        'timestamp': message.timestamp.strftime('%H:%M %d/%m/%Y')
    }, room=str(conversation_id))


if __name__ == "__main__":
    socketio.run(app, debug=True)
