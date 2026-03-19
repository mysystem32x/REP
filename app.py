from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json

# ✅ ИСПРАВЛЕНИЕ 1: Инициализация приложения
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройки загрузок
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаем папку для загрузок, если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# ==========================================
# Database Models
# ==========================================

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    youtube_url = db.Column(db.String(500), nullable=True)  # ✅ YouTube поле
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='$')
    area = db.Column(db.Float, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    property_type = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    additional_images = db.Column(db.Text)
    description = db.Column(db.Text)
    features = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'youtube_url': self.youtube_url,  # ✅ Добавлено в экспорт
            'price': self.price,
            'currency': self.currency,
            'area': self.area,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'type': self.property_type,
            'category': self.category,
            'image': self.image,
            'additional_images': self.get_additional_images(),
            'description': self.description,
            'features': self.features.split(',') if self.features else [],
            'latitude': self.latitude,
            'longitude': self.longitude
        }

    def get_additional_images(self):
        if self.additional_images:
            try:
                return json.loads(self.additional_images)
            except:
                return []
        return []

    def set_additional_images(self, images_list):
        self.additional_images = json.dumps(images_list)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


# ==========================================
# Helper Functions
# ==========================================

def allowed_file(filename):
    """Проверка расширения файла"""
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_files(files, prefix=''):
    """Функция сохранения с обработкой ошибок"""
    saved_files = []
    for file in files:
        if not file or not file.filename or file.filename.strip() == '':
            continue

        if not allowed_file(file.filename):
            continue

        try:
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{prefix}_{timestamp}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(filepath)

            if os.path.exists(filepath):
                saved_files.append(f'/static/uploads/{filename}')
            else:
                print(f"❌ Ошибка: файл не был сохранён: {filepath}")

        except Exception as e:
            print(f"❌ Ошибка при сохранении файла {file.filename}: {str(e)}")

    return saved_files


def init_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin создан: admin / admin123")


# ==========================================
# Routes
# ==========================================

@app.route('/')
def index():
    categories = [
        {"name": "Новостройки", "slug": "новостройки", "image": "https://img.prian.ru/2024_04/2/202404020444311663427750o.jpg"},
        {"name": "Вторичка", "slug": "вторичка", "image": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?q=80&w=400&auto=format&fit=crop"},
        {"name": "Инвестиции", "slug": "инвестиции", "image": "https://img.freepik.com/premium-photo/growth-business-finance-success-graph-stock-profit-investment-3d-financial-chart-market-background-with-economy-money-currency-increase-banki ng-progress-strategy-rise-up-arrow-global-economic_79161-2822.jpg"},
    ]
    return render_template('index.html', categories=categories)


@app.route('/properties')
def properties():
    category = request.args.get('category', '')
    query = Property.query
    if category:
        query = query.filter_by(category=category)
    props = query.all()
    return render_template('properties.html', properties=props, selected_category=category)


# ✅ ИСПРАВЛЕНИЕ 2: Синтаксис маршрута
@app.route('/property/<int:property_id>')
def property_detail(property_id):
    prop = Property.query.get_or_404(property_id)
    return render_template('property_detail.html', property=prop)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


# ✅ ИСПРАВЛЕНИЕ 3: Маршрут для файлов с параметром filename
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ==========================================
# Admin Routes
# ==========================================

@app.route('/admin')
def admin_panel():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    properties = Property.query.all()
    return render_template('admin/dashboard.html', properties=properties)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            return redirect(url_for('admin_panel'))
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('index'))


@app.route('/admin/property/new', methods=['GET', 'POST'])
def admin_add_property():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        try:
            images = request.files.getlist('images')
            saved_images = save_uploaded_files(images, prefix=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

            main_image = saved_images[0] if saved_images else 'https://images.unsplash.com/photo-1560448204-603b3fc33ddc?q=80&w=800&auto=format&fit=crop'
            additional_images = saved_images[1:] if len(saved_images) > 1 else []

            prop = Property(
                name=request.form.get('name'),
                location=request.form.get('location'),
                youtube_url=request.form.get('youtube_url'),  # ✅ Сохраняем YouTube
                price=float(request.form.get('price')),
                area=float(request.form.get('area')),
                bedrooms=int(request.form.get('bedrooms')),
                bathrooms=int(request.form.get('bathrooms')),
                property_type=request.form.get('type'),
                category=request.form.get('category'),
                image=main_image,
                description=request.form.get('description'),
                features=request.form.get('features'),
                latitude=float(request.form.get('latitude')) if request.form.get('latitude') else None,
                longitude=float(request.form.get('longitude')) if request.form.get('longitude') else None,
            )

            if additional_images:
                prop.set_additional_images(additional_images)

            db.session.add(prop)
            db.session.commit()
            return redirect(url_for('admin_panel'))

        except Exception as e:
            print(f"❌ Ошибка при создании объекта: {str(e)}")
            db.session.rollback()
            return render_template('admin/property_form.html', error=str(e))

    return render_template('admin/property_form.html')


# ✅ ИСПРАВЛЕНИЕ 4: Синтаксис маршрута редактирования
@app.route('/admin/property/<int:property_id>/edit', methods=['GET', 'POST'])
def admin_edit_property(property_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    prop = Property.query.get_or_404(property_id)

    if request.method == 'POST':
        try:
            existing_images = request.form.getlist('existing_images')
            new_images = request.files.getlist('images')
            new_saved_images = save_uploaded_files(new_images, prefix=f"prop_{property_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

            all_images = existing_images + new_saved_images
            main_image = all_images[0] if all_images else prop.image
            additional_images = all_images[1:] if len(all_images) > 1 else []

            prop.name = request.form.get('name')
            prop.location = request.form.get('location')
            prop.youtube_url = request.form.get('youtube_url')  # ✅ Обновляем YouTube
            prop.price = float(request.form.get('price'))
            prop.area = float(request.form.get('area'))
            prop.bedrooms = int(request.form.get('bedrooms'))
            prop.bathrooms = int(request.form.get('bathrooms'))
            prop.property_type = request.form.get('type')
            prop.category = request.form.get('category')
            prop.image = main_image
            prop.description = request.form.get('description')
            prop.features = request.form.get('features')
            prop.latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
            prop.longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None

            if additional_images:
                prop.set_additional_images(additional_images)
            else:
                prop.additional_images = None

            db.session.commit()
            return redirect(url_for('admin_panel'))

        except Exception as e:
            print(f"❌ Ошибка при обновлении объекта: {str(e)}")
            db.session.rollback()
            return render_template('admin/property_form.html', property=prop, error=str(e))

    return render_template('admin/property_form.html', property=prop)


# ✅ ИСПРАВЛЕНИЕ 5: Синтаксис маршрута удаления
@app.route('/admin/property/<int:property_id>/delete', methods=['POST'])
def admin_delete_property(property_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    prop = Property.query.get_or_404(property_id)

    try:
        if prop.image and prop.image.startswith('/static/uploads/'):
            filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(prop.image))
            if os.path.exists(filepath):
                os.remove(filepath)

        for img in prop.get_additional_images():
            if img and img.startswith('/static/uploads/'):
                filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(img))
                if os.path.exists(filepath):
                    os.remove(filepath)
    except Exception as e:
        print(f"⚠️ Ошибка при удалении файлов: {e}")

    db.session.delete(prop)
    db.session.commit()
    return redirect(url_for('admin_panel'))


@app.route('/api/properties')
def api_properties():
    properties = Property.query.all()
    return jsonify([p.to_dict() for p in properties])


# ==========================================
# Error Handlers
# ==========================================



# ✅ ИСПРАВЛЕНИЕ 6: Запуск приложения
if __name__ == '__main__':
    init_db()
    print(f"📁 Папка загрузок: {UPLOAD_FOLDER}")
    print(f"🌐 Запуск сервера на порту 8080...")
    app.run(debug=True, host='0.0.0.0', port=8080)