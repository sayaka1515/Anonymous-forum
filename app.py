from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import os
import time
import logging
from sqlalchemy.orm import sessionmaker
from functools import wraps
from uuid import uuid4

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['AVATAR_FOLDER'] = 'static/avatars'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('forum.log'),
        logging.StreamHandler()
    ]
)

# 檢查檔案副檔名
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 確保資料夾存在
def ensure_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
        app.logger.debug(f"Created folder: {folder}")

# 資料庫模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    avatar_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user = db.relationship('User', backref='posts')
    board = db.relationship('Board', backref='posts')
    replies = db.relationship('Reply', backref='post', cascade='all, delete-orphan')

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    media_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user = db.relationship('User', backref='replies')

@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        Session = sessionmaker(bind=db.engine)
        session = Session()
        try:
            user = session.get(User, int(user_id))
        finally:
            session.close()
        return user

# 管理員裝飾器
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('僅管理員可執行此操作！')
            app.logger.warning(f"User {current_user.id} attempted admin action without permission")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# 路由
@app.route('/')
def index():
    board_id = request.args.get('board')
    boards = Board.query.all()
    if board_id:
        posts = Post.query.filter_by(board_id=board_id).order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', boards=boards, posts=posts)

@app.route('/board/<int:board_id>')
def board(board_id):
    board = Board.query.get_or_404(board_id)
    posts = Post.query.filter_by(board_id=board_id).order_by(Post.created_at.desc()).all()
    boards = Board.query.all()
    return render_template('index.html', boards=boards, posts=posts, current_board=board)

@app.route('/board/new', methods=['GET', 'POST'])
@admin_required
def create_board():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        if Board.query.filter_by(name=name).first():
            flash('討論版名稱已存在！')
            return redirect(url_for('create_board'))
        board = Board(name=name, description=description)
        try:
            db.session.add(board)
            db.session.commit()
            flash('討論版創建成功！')
            app.logger.info(f"Board '{name}' created by admin {current_user.id}")
        except Exception as e:
            db.session.rollback()
            flash(f'創建討論版失敗：{str(e)}')
            app.logger.error(f"Error creating board: {str(e)}")
        return redirect(url_for('index'))
    return render_template('create_board.html')

@app.route('/board/<int:board_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_board(board_id):
    board = Board.query.get_or_404(board_id)
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        if name != board.name and Board.query.filter_by(name=name).first():
            flash('討論版名稱已存在！')
            return redirect(url_for('edit_board', board_id=board_id))
        board.name = name
        board.description = description
        try:
            db.session.commit()
            flash('討論版更新成功！')
            app.logger.info(f"Board {board_id} updated by admin {current_user.id}")
        except Exception as e:
            db.session.rollback()
            flash(f'更新討論版失敗：{str(e)}')
            app.logger.error(f"Error updating board {board_id}: {str(e)}")
        return redirect(url_for('index'))
    return render_template('edit_board.html', board=board)

@app.route('/board/<int:board_id>/delete', methods=['POST'])
@admin_required
def delete_board(board_id):
    board = Board.query.get_or_404(board_id)
    try:
        for post in board.posts:
            if post.media_path:
                media_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(post.media_path)).replace('\\', '/')
                if os.path.exists(media_path):
                    os.remove(media_path)
                    app.logger.debug(f"Deleted media: {media_path}")
            for reply in post.replies:
                if reply.media_path:
                    reply_media_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(reply.media_path)).replace('\\', '/')
                    if os.path.exists(reply_media_path):
                        os.remove(reply_media_path)
                        app.logger.debug(f"Deleted reply media: {reply_media_path}")
        db.session.delete(board)
        db.session.commit()
        flash('討論版已成功刪除！')
        app.logger.info(f"Board {board_id} deleted by admin {current_user.id}")
    except Exception as e:
        db.session.rollback()
        flash(f'刪除討論版失敗：{str(e)}')
        app.logger.error(f"Error deleting board {board_id}: {str(e)}")
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('用戶名已存在！')
            return redirect(url_for('register'))
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('註冊成功，請登入！')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('用戶名或密碼錯誤！')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        board_id = request.form['board_id']
        media_path = None
        if 'media' in request.files:
            file = request.files['media']
            app.logger.debug(f"Received file: {file.filename if file else 'None'}")
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid4().hex}_{int(time.time())}_{filename}"
                ensure_folder(app.config['UPLOAD_FOLDER'])
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename).replace('\\', '/')
                media_path = f"uploads/{unique_filename}"
                try:
                    file.save(full_path)
                    app.logger.debug(f"Saved media to: {full_path}")
                    if not os.path.exists(full_path):
                        flash('媒體檔案儲存失敗！')
                        app.logger.error(f"Media not found after save: {full_path}")
                        return redirect(url_for('create_post'))
                except Exception as e:
                    flash(f'媒體檔案儲存失敗：{str(e)}')
                    app.logger.error(f"Error saving media: {str(e)}")
                    return redirect(url_for('create_post'))
            else:
                app.logger.warning(f"Invalid or unsupported file: {file.filename if file else 'None'}")
        try:
            post = Post(title=title, content=content, board_id=board_id, user_id=current_user.id, media_path=media_path)
            db.session.add(post)
            db.session.commit()
            flash('貼文發布成功！')
            app.logger.debug(f"Post created with media_path: {media_path}")
        except Exception as e:
            flash(f'貼文發布失敗：{str(e)}')
            app.logger.error(f"Error creating post: {str(e)}")
            return redirect(url_for('create_post'))
        return redirect(url_for('index'))
    boards = Board.query.all()
    if not boards:
        flash('目前無討論版，請聯繫管理員！')
        return redirect(url_for('index'))
    return render_template('create_post.html', boards=boards)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)

@app.route('/post/<int:post_id>/reply', methods=['POST'])
@login_required
def add_reply(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form['content']
    media_path = None
    if 'media' in request.files:
        file = request.files['media']
        app.logger.debug(f"Received file: {file.filename if file else 'None'}")
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{int(time.time())}_{filename}"
            ensure_folder(app.config['UPLOAD_FOLDER'])
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename).replace('\\', '/')
            media_path = f"uploads/{unique_filename}"
            try:
                file.save(full_path)
                app.logger.debug(f"Saved media to: {full_path}")
                if not os.path.exists(full_path):
                    flash('媒體檔案儲存失敗！')
                    app.logger.error(f"Media not found after save: {full_path}")
                    return redirect(url_for('post', post_id=post_id))
            except Exception as e:
                flash(f'媒體檔案儲存失敗：{str(e)}')
                app.logger.error(f"Error saving media: {str(e)}")
                return redirect(url_for('post', post_id=post_id))
        else:
            app.logger.warning(f"Invalid or unsupported file: {file.filename if file else 'None'}")
    try:
        reply = Reply(content=content, post_id=post_id, user_id=current_user.id, media_path=media_path)
        db.session.add(reply)
        db.session.commit()
        flash('回覆發布成功！')
        app.logger.debug(f"Reply created with media_path: {media_path}")
    except Exception as e:
        flash(f'回覆發布失敗：{str(e)}')
        app.logger.error(f"Error creating reply: {str(e)}")
        return redirect(url_for('post', post_id=post_id))
    return redirect(url_for('post', post_id=post_id))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id and not current_user.is_admin:
        flash('您無權刪除此貼文！')
        app.logger.warning(f"User {current_user.id} attempted to delete post {post_id} without permission")
        return redirect(url_for('post', post_id=post_id))
    
    try:
        if post.media_path:
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(post.media_path)).replace('\\', '/')
            if os.path.exists(media_path):
                os.remove(media_path)
                app.logger.debug(f"Deleted media: {media_path}")
        for reply in post.replies:
            if reply.media_path:
                reply_media_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(reply.media_path)).replace('\\', '/')
                if os.path.exists(reply_media_path):
                    os.remove(reply_media_path)
                    app.logger.debug(f"Deleted reply media: {reply_media_path}")
        db.session.delete(post)
        db.session.commit()
        flash('貼文已成功刪除！')
        app.logger.info(f"Post {post_id} deleted by user {current_user.id}")
    except Exception as e:
        db.session.rollback()
        flash(f'刪除貼文失敗：{str(e)}')
        app.logger.error(f"Error deleting post {post_id}: {str(e)}")
        return redirect(url_for('post', post_id=post_id))
    
    return redirect(url_for('index'))

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    role = '全論壇總管理' if user.is_admin else '一般用戶'
    app.logger.debug(f"User {user_id} profile loaded, avatar_path: {user.avatar_path}")
    return render_template('user_profile.html', user=user, posts=posts, role=role)

@app.route('/user/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid4().hex}_{int(time.time())}_{filename}"
                ensure_folder(app.config['AVATAR_FOLDER'])
                temp_path = os.path.join(app.config['AVATAR_FOLDER'], f"temp_{unique_filename}").replace('\\', '/')
                full_path = os.path.join(app.config['AVATAR_FOLDER'], unique_filename).replace('\\', '/')
                avatar_path = f"avatars/{unique_filename}"
                try:
                    # 儲存原始圖片
                    file.save(temp_path)
                    img = Image.open(temp_path)
                    # 獲取裁切座標
                    x = int(float(request.form.get('x', 0)))
                    y = int(float(request.form.get('y', 0)))
                    width = int(float(request.form.get('width', 100)))
                    height = int(float(request.form.get('height', 100)))
                    # 裁切圖片
                    img = img.crop((x, y, x + width, y + height))
                    # 縮放至 100x100
                    img.thumbnail((100, 100))
                    img.save(full_path)
                    app.logger.debug(f"Saved cropped avatar to: {full_path}")
                    # 驗證檔案可讀
                    if not os.path.exists(full_path):
                        raise Exception("頭像檔案儲存後未找到")
                    # 刪除舊頭像
                    if current_user.avatar_path:
                        old_path = os.path.join(app.config['AVATAR_FOLDER'], os.path.basename(current_user.avatar_path)).replace('\\', '/')
                        if os.path.exists(old_path):
                            os.remove(old_path)
                            app.logger.debug(f"Deleted old avatar: {old_path}")
                    # 刪除臨時檔案
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        app.logger.debug(f"Deleted temp file: {temp_path}")
                    current_user.avatar_path = avatar_path
                    db.session.commit()
                    flash('頭像更新成功！')
                except Exception as e:
                    flash(f'頭像上傳或裁切失敗：{str(e)}')
                    app.logger.error(f"Error processing avatar: {str(e)}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return redirect(url_for('edit_profile'))
            else:
                flash('無效的圖片檔案或格式不支援！')
        return redirect(url_for('user_profile', user_id=current_user.id))
    return render_template('edit_profile.html')

# 初始化資料庫
with app.app_context():
    db.drop_all()
    db.create_all()
    if not Board.query.first():
        boards = [
            Board(name='綜合討論', description='各種話題的綜合討論區'),
            Board(name='科技交流', description='討論科技新知與技術分享'),
            Board(name='生活分享', description='分享生活點滴與經驗'),
            Board(name='遊戲天地', description='電玩遊戲與攻略討論'),
            Board(name='美食天地', description='美食推薦與烹飪心得')
        ]
        db.session.bulk_save_objects(boards)
        db.session.commit()
    # 初始創建管理員用戶（僅限開發環境）
    if not User.query.filter_by(username='yukari17').first():
        admin_user = User(username='yukari17', password_hash=generate_password_hash('admin123'), is_admin=True)
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info("Initial admin user 'yukari17' created.")

if __name__ == '__main__':
    app.run(debug=True)