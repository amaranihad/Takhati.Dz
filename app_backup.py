from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from openai import OpenAI
from flask import request, jsonify
import PyPDF2
from flask import jsonify
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
import sqlite3
import json
from datetime import datetime
from werkzeug.security import generate_password_hash

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = "takhati-secret-key"
UPLOAD_FOLDER = "static/uploads/medical_records"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
UPLOAD_FOLDER = "static/uploads/teacher"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        status TEXT DEFAULT 'غير محدد',
        created_at TEXT,
        last_login TEXT
    )
    ''')
  # 🔵 جدول questionnaire الجديد
    cursor.execute("""
   CREATE TABLE IF NOT EXISTS parent_stage1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL,
    selected_causes TEXT,
    answers TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
    """)

    cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT NOT NULL,
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT NOT NULL,
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS medical_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    child_name TEXT NOT NULL,
    doctor_name TEXT,
    file_name TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS teacher_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER,
    title TEXT,
    type TEXT,
    file_name TEXT,
    created_at TEXT
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS student_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT,
    action TEXT,
    score TEXT,
    created_at TEXT
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS library (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    file_name TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER,
    title TEXT,
    question TEXT,
    correct_answer TEXT,
    created_at TEXT
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS student_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT,
    exercise_id INTEGER,
    answer TEXT,
    status TEXT DEFAULT 'pending',
    score INTEGER DEFAULT 0,
    created_at TEXT
)
""")
    # إضافة الأدمن
    admin_username = "admin"
    admin_password ="1234"

    cursor.execute("SELECT id FROM users WHERE username = ?", (admin_username,))
    existing_admin = cursor.fetchone()

    if not existing_admin:
        cursor.execute(
            "INSERT INTO users (username, password, role, status, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?)",
            (
                admin_username,
                admin_password,
                "admin",
                "موثوق",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                None
            )
        )

    conn.commit()
    conn.close()
init_db()



@app.route("/")
def index():
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, password, role FROM users WHERE username = ? AND password = ?",
            (username, password)
        )

        user = cursor.fetchone()

        if user:

            # تحديث آخر دخول
            last_login = datetime.now().strftime("%Y-%m-%d %H:%M")

            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (last_login, user[0])
            )

            conn.commit()
            conn.close()

            # ======================
            # SESSION
            # ======================
            session['user_id'] = user[0]
            session['username'] = user[1]

            role = user[3].strip().lower()
            session['role'] = role

            # ======================
            # REDIRECT LOGIC CLEAN
            # ======================
            if role == "admin" or role == "أدمن":
                return redirect(url_for("admin_dashboard"))

            elif role in ["specialist", "مختص"]:
                return redirect(url_for("specialist_dashboard"))

            elif role in ["teacher", "أستاذ", "prof"]:
                return redirect(url_for("teacher_dashboard"))

            elif role in ["parent", "ولي أمر"]:
                return redirect(url_for("stage1"))

            else:
                return redirect(url_for("index"))

        else:
            conn.close()
            flash('اسم المستخدم أو كلمة المرور غير صحيحة')
            return redirect(url_for('login'))

    return render_template('login.html')



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # التحقق من وجود الحساب مسبقا
        cursor.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )

        if cursor.fetchone():
            flash("اسم المستخدم موجود مسبقاً")
            conn.close()
            return redirect(url_for("register"))

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        # إنشاء الحساب
        cursor.execute(
            """
            INSERT INTO users
            (username, password, role, status, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                password,
                role,
                "غير محدد",
                created_at,
                created_at
            )
        )

        conn.commit()
        conn.close()

        flash("تم إنشاء الحساب بنجاح")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/question")
def question():
    return render_template("question.html")







def get_admin_data():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, role, created_at, last_login FROM users
    """)
    users = cur.fetchall()

    try:
        cur.execute("SELECT id, sender, message, date, read FROM messages")
        messages = cur.fetchall()
    except:
        messages = []

    conn.close()

    total_accounts = len(users)
    active_accounts = total_accounts 
    unread_messages = 0

    return (
        users,
        messages,
        total_accounts,
        active_accounts,
        unread_messages
    )
@app.route('/admin-dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    users, messages, total_accounts, active_accounts, unread_messages = get_admin_data()

    return render_template(
        'admin_dashboard.html',
        users=users,
        messages=messages,
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        unread_messages=unread_messages
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# STAGE 1
# =========================
@app.route("/parent/stage1", methods=["GET", "POST"])
def stage1():
    if request.method == "POST":
        causes = request.form.getlist("causes")

        if not causes:
            flash("الرجاء اختيار سبب واحد على الأقل")
            return redirect(url_for("stage1"))

        session["causes"] = causes
        return redirect(url_for("stage1_questions"))

    return render_template("stage1.html")


# =========================
# QUESTIONS
# =========================
@app.route("/parent/stage1/questions", methods=["GET", "POST"])
def stage1_questions():

    causes = session.get("causes", [])

    if not causes:
        return redirect(url_for("stage1"))

    questions = load_questions(causes)

    if request.method == "POST":
        answers = request.form.to_dict()
        session["answers"] = answers
        return redirect(url_for("analyze"))

    return render_template("stage1_questions.html", questions=questions)


# =========================
# ANALYSIS (REAL FORMULA)
# =========================
@app.route("/analyze")
def analyze():

    answers = session.get("answers", {})

    score_map = {
        "أبداً": 0,
        "نادراً": 1,
        "أحياناً": 2,
        "دائماً": 3
    }

    total = 0
    max_total = 0

    for q, a in answers.items():
        x_i = score_map.get(a, 0)
        w_i = 1

        total += x_i * w_i
        max_total += 3 * w_i

    percent = (total / max_total) * 100 if max_total > 0 else 0
    percent = round(percent, 2)

    causes = session.get("causes", [])
    top = causes[0] if causes else "development"

    labels = {
        "development": "صعوبات التعلم النمائية و الأكاديمية",
        "autism": "إضطراب طيف التوحد",
        "adhd": "تشتت الإنتباه و فرط الحركة",
        "sensory": "مشاكل الحواس (السمع و البصر)",
        "slow": "بطء في التعلم",
        "impulsive": "تشتت الانتباه مع الإندفاعية",
        "language": "صعوبة في إكتساب اللغة"
    }

    if percent < 30:
        level = "خفيف"
        advice = "المؤشرات ضعيفة ويمكن متابعتها فقط."
    elif percent < 60:
        level = "متوسط"
        advice = "توجد مؤشرات تحتاج متابعة تربوية."
    else:
        level = "مرتفع"
        advice = "يُنصح باستشارة مختص."

    return render_template("analysis.html",
                           problem=labels[top],
                           percent=percent,
                           level=level,
                           advice=advice)


# =========================
# IQ TEST
# =========================
@app.route("/iq_test")
def iq_test():
    return render_template("iq_test.html")





# =========================
# QUESTIONS DATA (7 FULL DOMAINS - EXACT)
# =========================


def load_questions(causes):
    data = {}

    # =========================
    # 1. صعوبة في اكتساب اللغة
    # =========================
    if "language" in causes:
        data["صعوبة في اكتساب اللغة"] = [
            "يجد ابني صعوبة في قراءة الكلمات الجديدة",
            "يجد ابني صعوبة في قراءة نصوص قصيرة جدا",
            "يواجه ابني صعوبة في تمييز الأصوات المتشابهة للحروف",
            "يواجه ابني صعوبة في قراءة الأعداد باللغة الانجليزية",
            "يخلط ابني بين الكلمات المتشابهة في النطق عند الكتابة",
            "يواجه ابني صعوبة في قراءة الجمل المركبة",
            "لا يربط ابني بين شكل الحرف المكتوب وصوته المنطوق",
            "يواجه ابني صعوبة في نطق الحروف بشكل صحيح عند تركيب الكلمات"
        ]

    # =========================
    # 2. صعوبات التعلم النمائية والأكاديمية
    # =========================
    if "development" in causes:
        data["صعوبات التعلم النمائية والأكاديمية"] = [
            "يجد صعوبة في تذكر ترتيب أيام الأسبوع أو الشهور",
            "يواجه مشكلة في ربط الحذاء أو إغلاق أزرار القميص",
            "يخلط بين الاتجاهات اليمين واليسار",
            "يجد صعوبة في نقل رسالة شفوية بسيطة من شخص لآخر",
            "يواجه صعوبة في أداء الأنشطة التي تتطلب قراءة أو كتابة في المنزل",
            "يجد صعوبة في فهم فكرة الماضي أو المستقبل",
            "يستغرق وقتاً طويلاً جداً في أداء الواجبات المنزلية البسيطة",
            "يحتاج أن يُشرح له الدرس أكثر من مرة وكأنه يتعلمه لأول مرة",
            "يجد صعوبة في التعبير عما مر به خلال يومه بشكل متسلسل",
            "يخلط في قراءة لافتات المحلات أو العناوين البسيطة"
        ]

    # =========================
    # 3. اضطراب طيف التوحد
    # =========================
    if "autism" in causes:
        data["اضطراب طيف التوحد"] = [
            "لا يستجيب لمناداة اسمه فوراً رغم سلامة سمعه",
            "يفضل اللعب بنفس الطريقة والألعاب يومياً دون ملل",
            "يتأثر بشدة من الأصوات المنزلية العادية كالخلاط والمكنسة الكهربائية",
            "يجد صعوبة في تكوين صداقات مع أطفال العائلة أو الجيران",
            "لديه اهتمامات ضيقة جداً (مثل التركيز على نوع واحد من القصص أو الألعاب)",
            "لا يستخدم الإشارة ليُري شيئاً يثير اهتمامه",
            "يظهر حركات متكررة بجسمه (مثل الدوران حول نفسه أو المشي على أطراف أصابعه)",
            "لا يشارك في ألعاب التخيل (مثل التظاهر بأنه طبيب أو طيار)",
            "يتجنب التلامس الجسدي أحياناً",
            "يجد صعوبة في فهم النكت أو الكلام الذي يحمل معنيين"
        ]

    # =========================
    # 4. تشتت الانتباه وفرط الحركة
    # =========================
    if "adhd" in causes:
        data["تشتت الانتباه وفرط الحركة"] = [
            "يبدو وكأنه مدفوع بمحرك ولا يهدأ أبداً حتى عند الأكل",
            "يترك مائدة الطعام قبل الانتهاء من وجباته",
            "يجد صعوبة في الجلوس بهدوء لمشاهدة برنامج أو اللعب بلعبة واحدة",
            "يتدخل في حديث الكبار بشكل مستمر ومقاطع",
            "يفقد أغراضه الشخصية (ألعاب، ملابس) بشكل متكرر",
            "يتكلم بسرعة وبكثرة دون توقف",
            "يقوم بتصرفات خطرة دون تفكير في العواقب (مثل القفز من أماكن عالية)",
            "يسهل تشتيته بأي صوت أو حركة بسيطة حوله",
            "يجد صعوبة في إنهاء ما بدأ من مهام مثل ترتيب غرفته",
            "يتكلم كثيراً ويحرك يديه أو قدميه باستمرار أثناء الجلوس"
        ]

    # =========================
    # 5. مشاكل في الحواس
    # =========================
    if "sensory" in causes:
        data["مشاكل في الحواس (السمع والبصر)"] = [
            "يقترب جداً من شاشة التلفاز أو الهاتف أثناء المشاهدة",
            "يطلب دائماً رفع صوت التلفاز رغم كونه مسموعاً للبقية",
            "يغمض عينا واحدة عند محاولة التركيز في شيء بعيد",
            "يميل برأسه جهة معينة ليسمع بوضوح",
            "يشكو من صداع أو زغللة في العين بعد الواجبات",
            "لا يلتفت للأصوات التي تأتي من خلفه أو من غرفة أخرى",
            "يفرك عينيه بكثرة حتى بدون وجود حساسية",
            "يخلط بين الكلمات المتشابهة في الصوت",
            "يجد صعوبة في التقاط الكرة المرمية إليه",
            "يطلب إعادة الكلام كثيراً بقوله ماذا أو أعد"
        ]

    # =========================
    # 6. بطء التعلم
    # =========================
    if "slow" in causes:
        data["بطء التعلم"] = [
            "مهاراته في العناية بنفسه (الأكل واللبس) متأخرة مقارنة بأقرانه",
            "يجد صعوبة في استيعاب قوانين الألعاب الجماعية البسيطة",
            "تفكيره يبدو أبسط من عمره الزمني",
            "يستغرق وقتاً طويلاً للإجابة على سؤال بسيط",
            "يجد صعوبة في التعامل مع النقود أو معرفة قيمتها",
            "يكرر نفس الأخطاء رغم تنبيهه عدة مرات",
            "يفضل اللعب مع أطفال أصغر منه سناً",
            "لديه حصيلة لغوية محدودة مقارنة بأبناء جيله",
            "يجد صعوبة في استنتاج النتائج البسيطة",
            "يبدو محبطاً وغير واثق من نفسه عند تجربة شيء جديد"
        ]

    # =========================
    # 7. تشتت الانتباه مع الاندفاعية
    # =========================
    if "impulsive" in causes:
        data["تشتت الانتباه المصاحب للاندفاعية"] = [
            "يفقد أعصابه بسرعة ويبدأ بالصراخ أو البكاء لأسباب بسيطة",
            "يقوم بتخريب ألعابه أو أغراض المنزل عند الغضب",
            "يجد صعوبة في انتظار دوره في اللعب أو الطعام",
            "يجاوب على الأسئلة قبل أن تُكمل",
            "يبدو وكأنه لا يسمع التوجيهات أو يتجاهلها",
            "يقع في حوادث منزلية كثيرة (كسر أشياء، اصطدام)",
            "يجد صعوبة في البقاء هادئاً في الأماكن العامة",
            "يفرط في الحركة في الأوقات غير المناسبة مثل وقت النوم",
            "ينتقل من نشاط إلى آخر دون إتمام أي واحد",
            "يجد صعوبة في الالتزام بجدول المنزل اليومي"
        ]

    return data

@app.route("/landing_page")
def landing_page():
    return render_template("landing_page.html")

@app.route("/account_choice")
def account_choice():
    return render_template("account_choice.html")

@app.route('/parent_form', methods=['GET', 'POST'])
def parent_form():

    if request.method == 'POST':
        return redirect(url_for('parent_dashboard'))

    return render_template('parent_form.html')


@app.route('/parent_dashboard')
def parent_dashboard():
    return render_template('parent_dashboard.html')


@app.route("/child_form")
def child_form():
    return render_template("child_form.html")


# =========================
# SPECIALIST DASHBOARD
# =========================

@app.route("/specialist")
def specialist_dashboard():
    return render_template("specialist_dashboard.html")


@app.route("/specialist/adaptation")
def adaptation_settings():
    return render_template("adaptation_settings.html")


@app.route("/specialist/analysis")
def specialist_analysis():
    return render_template("specialist_analysis.html")


@app.route("/specialist/children")
def children_accounts():
    return render_template("children_accounts.html")


@app.route("/specialist/notes")
def children_notes():
    return render_template("children_notes.html")


@app.route("/specialist/reports")
def weekly_reports():
    return render_template("weekly_reports.html")


@app.route("/specialist/parents")
def parents_accounts():
    return render_template("parents_accounts.html")


@app.route("/specialist/medical-records", methods=["GET", "POST"])
def medical_records():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        child_name = request.form.get("child_name")
        doctor_name = request.form.get("doctor_name")
        pdf_file = request.files.get("pdf_file")

        if pdf_file and pdf_file.filename.endswith(".pdf"):
            filename = secure_filename(pdf_file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            pdf_file.save(save_path)

            cursor.execute("""
                INSERT INTO medical_records (child_name, doctor_name, file_name, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, (
                child_name,
                doctor_name,
                filename,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

            conn.commit()

    cursor.execute("""
        SELECT *
        FROM medical_records
        ORDER BY id DESC
    """)

    records = cursor.fetchall()
    conn.close()

    return render_template("medical_records.html", records=records)


@app.route("/specialist/iq")
def iq_results():
    return render_template("iq_results.html")


@app.route("/specialist/profile")
def specialist_profile():
    return render_template("specialist_profile.html")

 
@app.route("/specialist/chat")
def specialist_chat():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, role, status
        FROM users
        WHERE role != 'specialist'
        ORDER BY role, username
    """)

    contacts = cursor.fetchall()
    conn.close()

    return render_template("specialist_chat.html", contacts=contacts)


@app.route("/specialist/chat/admin")
def chat_admin():
    return render_template("specialist_chat.html", chat_type="admin") 

@socketio.on("send_message")
def handle_send_message(data):
    print("وصلت رسالة:", data)

    room = data.get("room")
    sender = data.get("sender")
    message = data.get("message")

    if not room or not sender or not message:
        print("بيانات ناقصة")
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO messages (room, sender, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        room,
        sender,
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    conn.close()

    emit("receive_message", {
        "sender": sender,
        "message": message
    }, room=room)
@app.route("/get_messages/<room>")
def get_messages(room):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sender, message, created_at
        FROM messages
        WHERE room = ?
        ORDER BY id ASC
    """, (room,))

    messages = cursor.fetchall()
    conn.close()

    return {
        "messages": [
            {
                "sender": msg["sender"],
                "message": msg["message"],
                "created_at": msg["created_at"]
            }
            for msg in messages
        ]
    }

@socketio.on("join")
def handle_join(data):
    room = data.get("room")

    if not room:
        print("Room ناقصة")
        return

    join_room(room)
    print("تم الدخول إلى الغرفة:", room)

@socketio.on("call_offer")
def handle_call_offer(data):
    emit("call_offer", data, room=data["room"], include_self=False)


@socketio.on("call_answer")
def handle_call_answer(data):
    emit("call_answer", data, room=data["room"], include_self=False)


@socketio.on("ice_candidate")
def handle_ice_candidate(data):
    emit("ice_candidate", data, room=data["room"], include_self=False)


@socketio.on("end_call")
def handle_end_call(data):
    emit("end_call", data, room=data["room"], include_self=False)


@app.route("/teacher/dashboard")
def teacher_dashboard():
    return render_template("teacher_dashboard.html")


@app.route("/teacher/agenda")
def teacher_agenda():
    return render_template("teacher_agenda.html")

@app.route("/teacher/students")
def teacher_students():
    return render_template("teacher_students.html")

@app.route("/teacher/lessons", methods=["GET", "POST"])
def teacher_lessons():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title")
        pdf = request.files.get("pdf")

        if pdf:
            filename = secure_filename(pdf.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            pdf.save(path)

            cursor.execute("""
                INSERT INTO teacher_files (teacher_id, title, type, file_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                1,
                title,
                "lesson",
                filename,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

            conn.commit()

    cursor.execute("SELECT * FROM teacher_files WHERE type='lesson'")
    lessons = cursor.fetchall()
    conn.close()

    return render_template("teacher_lessons.html", lessons=lessons)

@app.route("/teacher/exercises", methods=["GET", "POST"])
def teacher_exercises():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title")
        pdf = request.files.get("pdf")

        if pdf:
            filename = secure_filename(pdf.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            pdf.save(path)

            cursor.execute("""
                INSERT INTO teacher_files (teacher_id, title, type, file_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                1,
                title,
                "exercise",
                filename,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

            conn.commit()

    cursor.execute("SELECT * FROM teacher_files WHERE type='exercise'")
    exercises = cursor.fetchall()
    conn.close()

    return render_template("teacher_exercises.html", exercises=exercises)


@app.route("/teacher/library", methods=["GET", "POST"])
def teacher_library():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # إذا رفع كتاب جديد
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        pdf = request.files.get("pdf")

        if pdf:
            filename = secure_filename(pdf.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            pdf.save(path)

            cursor.execute("""
                INSERT INTO library (title, description, file_name, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, (
                title,
                description,
                filename,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

            conn.commit()

    # جلب الكتب
    cursor.execute("SELECT * FROM library ORDER BY id DESC")
    books = cursor.fetchall()
    conn.close()

    return render_template("teacher_library.html", books=books)


@app.route("/teacher/chat")
def teacher_chat():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, role
        FROM users
        WHERE role IN ('admin', 'أدمن', 'مختص', 'أستاذ', 'prof', 'ولي أمر')
    """)

    contacts = cursor.fetchall()

    # 🔥 نضيف الإدارة حتى لو ما كانتش user عادي
    admin_contact = {
        "id": 0,
        "username": "الإدارة",
        "role": "admin"
    }

    contacts = [admin_contact] + contacts

    conn.close()

    return render_template("teacher_chat.html", contacts=contacts)


@app.route('/teacher/profile')
def teacher_profile():
    return render_template("teacher_profile.html")


    
@app.route("/child_home")
def child_home():
    return render_template("child_home.html")



@app.route("/child_dashboard")
def child_dashboard():
    return render_template("child_dashboard.html")

@app.route("/go-child-home", methods=["POST"])
def go_child_home():
    return redirect(url_for("child_home"))

@app.route('/api/progress')
def progress_data():
    return {
        "labels": ["اليوم 1", "اليوم 3", "اليوم 5"],
        "values": [40, 60, 80]
    }


@app.route('/api/appointments')
def appointments():
    return {
        "data": [
            {
                "title": "جلسة أونلاين مع الأخصائي",
                "time": "18:30",
                "day": "اليوم"
            },
            {
                "title": "دورة حضورية",
                "time": "10:00",
                "day": "الخميس"
            }
        ]
    }


@app.route('/api/subscription')
def subscription():
    return {
        "status": "active",
        "features": ["تقارير", "مواعيد", "متابعة الطفل"]
    }




messages = {
    "admin": [],
    "teacher": [],
    "specialist": []
}

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json

    room = data["room"]
    text = data["text"]
    sender = data["sender"]

    messages[room].append({
        "text": text,
        "sender": sender
    })

    return jsonify({"status": "ok"})

@app.route("/get_messages/<room>", endpoint="get_messages_v1")
def get_messages(room):
    return jsonify(messages.get(room, []))


# رفع PDF واستخراج النص
@app.route("/upload_file", methods=["POST"])
def upload_file():

    file = request.files["file"]

    reader = PyPDF2.PdfReader(file)
    text = ""

    for page in reader.pages:
        text += page.extract_text()

    return jsonify({"text": text})


# تكييف النص بالذكاء الاصطناعي
@app.route("/adapt_text", methods=["POST"])
def adapt_text():

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return jsonify({
            "error": "ميزة الذكاء الاصطناعي غير مفعلة حالياً."
        }), 503

    client = OpenAI(api_key=api_key)

    text = request.json.get("text")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "أعد كتابة النص بطريقة تعليمية مبسطة للأطفال: "
                           "تكبير الكلمات، تحسين الوضوح، إضافة فراغات، "
                           "وتشكيل بسيط وتحسين الأسلوب."
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )

    result = response.choices[0].message.content

    return jsonify({"result": result})






@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/ai_panel")
def ai_panel():
    return render_template("ai_panel.html")



@app.route("/ai_reader")
def reader_ai():
    return render_template("ai_reader.html")

@app.route("/get_child_text")
def get_child_text():

    text = """
    في يوم جميل كانت القطة تجلس في الحديقة.
    وكان الكلب يلعب تحت الشجرة الكبيرة.
    وشرب الأطفال الحليب ثم لعبوا باللعبة الملونة.
    """

    return jsonify({"text": text})



@app.route("/therapy_program")
def therapy_program():
    return render_template("therapy_game.html")


@app.route("/therapy_game")
def therapy_game():
    return render_template("therapy_program.html")

@app.route("/speech_to_text", methods=["POST"])
def speech_to_text():

    audio = request.files["audio"]

    # لاحقاً يمكن نضيف Whisper API
    return jsonify({"text": "مؤقتاً تم الاستقبال"})


@app.route("/maze")
def maze():
    return render_template("maze.html")

@app.route("/specialist_camera")
def specialist_camera():
    return render_template("specialist_camera.html")





if __name__ == "__main__":
    socketio.run(app, debug=True, port=5005, use_reloader=False)