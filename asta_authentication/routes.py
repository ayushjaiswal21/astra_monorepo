# asta_authentication/routes.py

from flask import Blueprint, request, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity

from .models import db, User, Post, Article

api_bp = Blueprint('api', __name__, url_prefix='/api')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_unique_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4()}.{ext}"
    return secure_filename(unique_name)

@api_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    user_id = get_jwt_identity()
    content = request.form.get('content')
    if not content:
        return jsonify({'error': 'Post content is required.'}), 400

    media_url = None
    if 'media' in request.files:
        file = request.files['media']
        if file and allowed_file(file.filename):
            filename = get_unique_filename(file.filename)
            post_upload_folder = current_app.config['POST_UPLOAD_FOLDER']
            os.makedirs(post_upload_folder, exist_ok=True)
            file.save(os.path.join(post_upload_folder, filename))
            media_url = f"/api/uploads/posts/{filename}" # Use the API endpoint

    new_post = Post(user_id=user_id, content=content, media_url=media_url)
    db.session.add(new_post)
    db.session.commit()
    return jsonify(new_post.to_dict()), 201

@api_bp.route('/posts/feed', methods=['GET'])
@jwt_required()
def get_main_feed():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posts])

@api_bp.route('/posts/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_posts(user_id):
    user = User.query.get_or_404(user_id)
    posts = user.posts.order_by(Post.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posts])

@api_bp.route('/articles', methods=['POST'])
@jwt_required()
def create_article():
    user_id = get_jwt_identity()
    title = request.form.get('title')
    body = request.form.get('body')
    if not title or not body:
        return jsonify({'error': 'Title and body are required.'}), 400

    cover_image_url = None
    if 'cover_image' in request.files:
        file = request.files['cover_image']
        if file and allowed_file(file.filename):
            filename = get_unique_filename(file.filename)
            article_upload_folder = current_app.config['ARTICLE_UPLOAD_FOLDER']
            os.makedirs(article_upload_folder, exist_ok=True)
            file.save(os.path.join(article_upload_folder, filename))
            cover_image_url = f"/api/uploads/articles/{filename}"

    new_article = Article(user_id=user_id, title=title, body=body, cover_image_url=cover_image_url)
    db.session.add(new_article)
    db.session.commit()
    return jsonify(new_article.to_dict(with_body=True)), 201

@api_bp.route('/articles', methods=['GET'])
def get_all_articles():
    articles = Article.query.order_by(Article.created_at.desc()).all()
    return jsonify([a.to_dict() for a in articles])

@api_bp.route('/articles/<int:article_id>', methods=['GET'])
def get_single_article(article_id):
    article = Article.query.get_or_404(article_id)
    return jsonify(article.to_dict(with_body=True))

# Static file serving
@api_bp.route('/uploads/posts/<path:filename>')
def serve_post_media(filename):
    return send_from_directory(current_app.config['POST_UPLOAD_FOLDER'], filename)

@api_bp.route('/uploads/articles/<path:filename>')
def serve_article_media(filename):
    return send_from_directory(current_app.config['ARTICLE_UPLOAD_FOLDER'], filename)
