from sqlalchemy import Column, String, Integer, DateTime, func
from werkzeug.security import generate_password_hash, check_password_hash
from sendmessage import db, app
from flask_login import UserMixin

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Table, func
from werkzeug.security import generate_password_hash, check_password_hash
from sendmessage import db, app
from datetime import datetime
import pytz


vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

def get_vietnam_time():
    return datetime.now(vn_tz)

group_members = db.Table('group_members',
                         db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True),
                         db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                         )


class User(UserMixin, db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), nullable=False)
    avatar_url = db.Column(db.String(255),
                           default='https://res.cloudinary.com/dblzpkokm/image/upload/v1744450061/defaultuserimg_prr7d2.jpg')

    conversations1 = db.relationship('Conversation', foreign_keys='Conversation.user1_id', lazy='dynamic')
    conversations2 = db.relationship('Conversation', foreign_keys='Conversation.user2_id', lazy='dynamic')
    groups = db.relationship('Group', secondary=group_members, backref='members')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_conversation_with(self, partner):
        # Tìm cuộc trò chuyện giữa người dùng và đối tác
        conversation = Conversation.query.filter(
            ((Conversation.user1_id == self.id) & (Conversation.user2_id == partner.id)) |
            ((Conversation.user2_id == self.id) & (Conversation.user1_id == partner.id))
        ).first()

        if not conversation:
            # Nếu không có cuộc trò chuyện, tạo mới
            conversation = Conversation(user1_id=self.id, user2_id=partner.id)
            db.session.add(conversation)
            db.session.commit()

        return conversation


class Conversation(db.Model):
    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user2_id = Column(Integer, ForeignKey('user.id'), nullable=False)

    messages = db.relationship('Message', backref='conversation', lazy=True)

    def get_partner(self, user_id):
        if self.user1_id == user_id:
            return User.query.get(self.user2_id)  # Trả về đối tượng User đúng
        return User.query.get(self.user1_id)
    # Trả về ID của user1 (thay vì user1 trực tiếp)
    def get_last_message(self):
        """Lấy tin nhắn gần nhất trong cuộc trò chuyện"""
        return Message.query.filter_by(conversation_id=self.id).order_by(Message.timestamp.desc()).first()



class Message(db.Model):
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversation.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    content = Column(String(500), nullable=False)
    timestamp = Column(DateTime, default=get_vietnam_time, nullable=False)
    is_read = Column(Boolean, default=False)

    # Quan hệ với người gửi tin nhắn
    sender = db.relationship('User', foreign_keys=[sender_id], backref='messages')
    attachments = db.relationship('Attachment', backref='message', lazy=True)


class Attachment(db.Model):
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('message.id'), nullable=False)
    file_url = Column(String(255), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    original_filename = Column(String(255))  # Thêm trường lưu tên file gốc






class Group(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(Integer, ForeignKey('user.id'))


# Hàm tạo người dùng
def create_user(username, email, password, name):
    user = User(username=username, email=email, name=name)
    user.set_password(password)  # Mã hóa mật khẩu
    db.session.add(user)
    db.session.commit()
    return user


# Hàm tạo cuộc trò chuyện giữa 2 người dùng


if __name__ == '__main__':
    with app.app_context():
        # Xóa dữ liệu cũ và tạo lại bảng
        db.drop_all()
        db.create_all()


        user1 = create_user("john_doe", "john@example.com", "password123", "John Doe")
        user2 = create_user("jane_doe", "jane@example.com", "password123", "Jane Doe")






