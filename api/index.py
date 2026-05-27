from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get('SECRET_KEY', 'trolley-bend-tracker-secret-key')

# Database configuration
# Use /tmp for Vercel (writable), fallback to local instance folder
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

DB_PATH = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(INSTANCE_DIR, 'bends.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model
class BendRecord(db.Model):
    __tablename__ = 'bend_records'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    job_number = db.Column(db.String(50), nullable=False)
    tube_material = db.Column(db.String(50), nullable=False)
    tube_diameter = db.Column(db.String(20), nullable=False)
    bend_angle = db.Column(db.String(20), nullable=False)
    bend_radius = db.Column(db.String(20), nullable=False)
    trolley_model = db.Column(db.String(50), nullable=False)
    operator = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    fail_reason = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'job_number': self.job_number,
            'tube_material': self.tube_material,
            'tube_diameter': self.tube_diameter,
            'bend_angle': self.bend_angle,
            'bend_radius': self.bend_radius,
            'trolley_model': self.trolley_model,
            'operator': self.operator,
            'status': self.status,
            'fail_reason': self.fail_reason or '',
            'notes': self.notes or '',
            'created_at': self.created_at
        }

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    bends = BendRecord.query.order_by(BendRecord.date.desc()).all()
    bend_list = [b.to_dict() for b in bends]

    # Calculate stats
    total = len(bends)
    passed = sum(1 for b in bends if b.status == 'Pass')
    failed = sum(1 for b in bends if b.status == 'Fail')
    pending = sum(1 for b in bends if b.status == 'Pending')

    stats = {
        'total': total,
        'passed': passed,
        'failed': failed,
        'pending': pending,
        'pass_rate': round((passed / total * 100), 1) if total > 0 else 0
    }

    return render_template('index.html', bends=bend_list, stats=stats)

@app.route('/add', methods=['POST'])
def add_bend():
    new_bend = BendRecord(
        date=request.form.get('date', datetime.now().strftime('%Y-%m-%d')),
        job_number=request.form.get('job_number', '').strip(),
        tube_material=request.form.get('tube_material', '').strip(),
        tube_diameter=request.form.get('tube_diameter', '').strip(),
        bend_angle=request.form.get('bend_angle', '').strip(),
        bend_radius=request.form.get('bend_radius', '').strip(),
        trolley_model=request.form.get('trolley_model', '').strip(),
        operator=request.form.get('operator', '').strip(),
        status=request.form.get('status', 'Pending'),
        fail_reason=request.form.get('fail_reason', '').strip() if request.form.get('status') == 'Fail' else None,
        notes=request.form.get('notes', '').strip()
    )

    db.session.add(new_bend)
    db.session.commit()

    flash('Bend record added successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/delete/<int:bend_id>')
def delete_bend(bend_id):
    bend = db.session.get(BendRecord, bend_id)
    if bend:
        db.session.delete(bend)
        db.session.commit()
        flash('Bend record deleted successfully!', 'success')
    else:
        flash('Record not found.', 'error')
    return redirect(url_for('index'))

@app.route('/api/bends')
def api_bends():
    bends = BendRecord.query.order_by(BendRecord.date.desc()).all()
    return jsonify([b.to_dict() for b in bends])

@app.route('/api/bends/<int:bend_id>')
def api_bend(bend_id):
    bend = db.session.get(BendRecord, bend_id)
    if bend:
        return jsonify(bend.to_dict())
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
