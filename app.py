import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.utils import secure_filename

# --- აპლიკაციის და ბაზის კონფიგურაცია ---
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- ფაილების ატვირთვის კონფიგურაცია ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- ბაზის კონფიგურაცია (არ იცვლება) ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- JSON ფაილების გზები ---
NEWS_FILE = os.path.join(basedir, 'news.json')
GALLERY_FILE = os.path.join(basedir, 'gallery.json')

# --- ადმინისტრატორის მონაცემები ---
ADMIN_USERNAME = 'imedisxidi2025'
ADMIN_PASSWORD = 'mutlaobamikvars'


# --- დამხმარე ფუნქციები ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- JSON დამხმარე ფუნქციები ---
def load_data(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_data(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- მონაცემთა ბაზის მოდელი (არ იცვლება) ---
class Beneficiary(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    story: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_needed: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_collected: Mapped[int] = mapped_column(Integer, default=0)


with app.app_context():
    db.create_all()


# --- მარშრუტები (Routes) ---

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
def index():
    beneficiaries = Beneficiary.query.all()
    news = load_data(NEWS_FILE)
    gallery = load_data(GALLERY_FILE)
    # ვაჩვენოთ მხოლოდ ბოლო 3 სიახლე მთავარ გვერდზე
    latest_news = sorted(news, key=lambda x: x['id'], reverse=True)[:3]
    return render_template('index.html', beneficiaries=beneficiaries, news=latest_news, gallery=gallery)


# --- ადმინის მარშრუტები ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('მომხმარებლის სახელი ან პაროლი არასწორია.', 'danger')
    return render_template('admin/adlogin.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    beneficiaries = Beneficiary.query.order_by(Beneficiary.id.desc()).all()
    return render_template('admin/dashboard.html', beneficiaries=beneficiaries)


@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))


# --- ბენეფიციარების მართვა (არ იცვლება) ---
@app.route('/admin/add', methods=['POST'])
def add_beneficiary():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    # ... იგივე კოდი რაც წინა ვერსიაში
    name = request.form['name']
    story = request.form['story']
    amount_needed = request.form['amount_needed']
    image_url_from_form = request.form.get('image_url')
    image_path = ''
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = url_for('uploaded_file', filename=filename)
    if not image_path and image_url_from_form: image_path = image_url_from_form
    if not image_path: image_path = f'https://placehold.co/600x400/FFC107/333333?text={name.split()[0]}'
    new_beneficiary = Beneficiary(name=name, story=story, image_url=image_path, amount_needed=int(amount_needed),
                                  amount_collected=0)
    db.session.add(new_beneficiary)
    db.session.commit()
    flash('ბენეფიციარი წარმატებით დაემატა!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit/<int:beneficiary_id>', methods=['GET', 'POST'])
def edit_beneficiary(beneficiary_id):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    beneficiary_to_edit = db.get_or_404(Beneficiary, beneficiary_id)
    if request.method == 'POST':
        # ... იგივე კოდი რაც წინა ვერსიაში
        beneficiary_to_edit.name = request.form['name']
        beneficiary_to_edit.story = request.form['story']
        beneficiary_to_edit.amount_needed = int(request.form['amount_needed'])
        beneficiary_to_edit.amount_collected = int(request.form['amount_collected'])
        image_url_from_form = request.form.get('image_url')
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                beneficiary_to_edit.image_url = url_for('uploaded_file', filename=filename)
            elif image_url_from_form and beneficiary_to_edit.image_url != image_url_from_form:
                beneficiary_to_edit.image_url = image_url_from_form
        db.session.commit()
        flash('ბენეფიციარის მონაცემები წარმატებით განახლდა!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/edit.html', beneficiary=beneficiary_to_edit)


@app.route('/admin/delete/<int:beneficiary_id>')
def delete_beneficiary(beneficiary_id):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    beneficiary_to_delete = db.get_or_404(Beneficiary, beneficiary_id)
    db.session.delete(beneficiary_to_delete)
    db.session.commit()
    flash('ბენეფიციარი წარმატებით წაიშალა!', 'success')
    return redirect(url_for('admin_dashboard'))


# --- სიახლეების მართვა ---
@app.route('/admin/news', methods=['GET', 'POST'])
def manage_news():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    news_list = load_data(NEWS_FILE)
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_id = int(uuid.uuid4().int & (1 << 64) - 1)  # დიდი უნიკალური ID
        new_article = {'id': new_id, 'title': title, 'content': content}
        news_list.append(new_article)
        save_data(NEWS_FILE, news_list)
        flash('სიახლე წარმატებით დაემატა!', 'success')
        return redirect(url_for('manage_news'))

    sorted_news = sorted(news_list, key=lambda x: x['id'], reverse=True)
    return render_template('admin/news.html', news=sorted_news)


@app.route('/admin/news/delete/<int:news_id>')
def delete_news(news_id):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    news_list = load_data(NEWS_FILE)
    news_list = [n for n in news_list if n['id'] != news_id]
    save_data(NEWS_FILE, news_list)
    flash('სიახლე წარმატებით წაიშალა!', 'warning')
    return redirect(url_for('manage_news'))


# --- გალერეის მართვა ---
@app.route('/admin/gallery', methods=['GET', 'POST'])
def manage_gallery():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    gallery_list = load_data(GALLERY_FILE)
    if request.method == 'POST':
        description = request.form['description']
        if 'photo' not in request.files or request.files['photo'].filename == '':
            flash('გთხოვთ ატვირთოთ ფოტო!', 'danger')
            return redirect(request.url)

        file = request.files['photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('uploaded_file', filename=filename)

            new_image = {'id': filename, 'url': image_url, 'description': description}
            gallery_list.append(new_image)
            save_data(GALLERY_FILE, gallery_list)
            flash('ფოტო გალერეაში წარმატებით დაემატა!', 'success')
            return redirect(url_for('manage_gallery'))

    return render_template('admin/gallery.html', gallery=gallery_list)


@app.route('/admin/gallery/delete/<image_id>')
def delete_gallery_image(image_id):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    gallery_list = load_data(GALLERY_FILE)

    # ფაილის წაშლა 'uploads' საქაღალდიდან
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_id))
    except OSError as e:
        print(f"Error deleting file {image_id}: {e}")

    gallery_list = [img for img in gallery_list if img['id'] != image_id]
    save_data(GALLERY_FILE, gallery_list)
    flash('ფოტო გალერეიდან წარმატებით წაიშალა!', 'warning')
    return redirect(url_for('manage_gallery'))


if __name__ == '__main__':
    app.run(debug=True)