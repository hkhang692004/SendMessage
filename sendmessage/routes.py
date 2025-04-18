from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from sendmessage import db, app, dao, login_manager
from models import User, Message, Attachment
import cloudinary.uploader
import os
from utils import upload_file

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
            flash('Mật khẩu không khớp!', 'danger')
            return redirect(url_for('register'))

        # Kiểm tra nếu username đã tồn tại
        if User.query.filter_by(username=username).first():
            flash('Username đã tồn tại!', 'danger')
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

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session['user_id'] = user.id  # Lưu user_id vào session
            flash('Login successful', 'success')
            return redirect(url_for('messages'))
        else:
            flash('Invalid username or password', 'danger')

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

    return render_template('messages.html', conversations=conversations, search_results=search_results,
                           current_user=user)


from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from sendmessage import app, db
from models import User, Conversation, Message
from datetime import datetime
import cloudinary.uploader  # Nếu bạn dùng Cloudinary để lưu file
import os


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
        messages=messages
    )


@app.route('/logout')
def logout():
    logout_user()  # Xóa thông tin người dùng khỏi session
    flash('Bạn đã đăng xuất', 'info')
    return redirect(url_for('login'))


@login_manager.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


if __name__ == "__main__":
    app.run(debug=True)
