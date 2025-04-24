from models import User
from models import User, db

from werkzeug.security import generate_password_hash



def get_user_by_id(user_id):
    return User.query.get(user_id)


def add_user(username, password, email, name, avatar_url):
    # Mã hóa mật khẩu
    hashed_password = generate_password_hash(password)

    # Tạo đối tượng người dùng mới
    new_user = User(username=username, email=email, name=name, avatar_url=avatar_url)
    new_user.set_password(password)  # Lưu mật khẩu đã băm

    # Thêm người dùng vào cơ sở dữ liệu
    db.session.add(new_user)
    db.session.commit()  # Lưu thay đổi vào cơ sở dữ liệu

    return new_user  # Trả về người dùng đã được tạo