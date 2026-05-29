from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import csv
import io

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get('SECRET_KEY', 'trolley-bend-tracker-secret-key')

# Database configuration
# On Vercel, the filesystem is read-only except for /tmp.
# Use DATABASE_URL env var for persistent PostgreSQL (e.g. Supabase).
# Falls back to /tmp/bends.db (SQLite) which is writable on Vercel but ephemeral.
_database_url = os.environ.get('DATABASE_URL')

if _database_url:
    # Supabase/Heroku sometimes returns 'postgres://' which SQLAlchemy requires as 'postgresql://'
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    DB_PATH = _database_url
else:
    DB_PATH = 'sqlite:////tmp/bends.db'

app.config['SQLALCHEMY_DATABASE_URI'] = DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model
class BendRecord(db.Model):
    __tablename__ = 'bend_records'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    job_number = db.Column(db.String(50), nullable=True)
    tube_material = db.Column(db.String(50), nullable=False, default='Stainless Steel')
    tube_diameter = db.Column(db.String(20), nullable=False)
    bend_angle = db.Column(db.String(20), nullable=True)
    bend_radius = db.Column(db.String(20), nullable=False)
    trolley_model = db.Column(db.String(50), nullable=True)
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

# Context processor for template globals
@app.context_processor
def inject_globals():
    return {
        'now': datetime.now().strftime('%Y-%m-%d'),
        'materials': ['Steel', 'Stainless Steel', 'Aluminum', 'Copper', 'Brass', 'Titanium'],
        'fail_reasons': ['Wrinkling', 'Flattening', 'Springback', 'Cracking', 'Ovality', 
                        'Galling', 'Incorrect Angle', 'Incorrect Radius', 'Material Defect', 
                        'Tooling Issue', 'Other'],
        'statuses': ['Pending', 'Pass', 'Fail']
    }

def get_filtered_bends(search='', status_filter='', material_filter='', date_from='', date_to=''):
    query = BendRecord.query
    
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                BendRecord.job_number.ilike(search_term),
                BendRecord.operator.ilike(search_term),
                BendRecord.trolley_model.ilike(search_term),
                BendRecord.notes.ilike(search_term)
            )
        )
    
    if status_filter:
        query = query.filter(BendRecord.status == status_filter)
    
    if material_filter:
        query = query.filter(BendRecord.tube_material == material_filter)
    
    if date_from:
        query = query.filter(BendRecord.date >= date_from)
    
    if date_to:
        query = query.filter(BendRecord.date <= date_to)
    
    return query.order_by(BendRecord.date.desc()).all()

def calculate_stats(bends):
    total = len(bends)
    passed = sum(1 for b in bends if b.status == 'Pass')
    failed = sum(1 for b in bends if b.status == 'Fail')
    pending = sum(1 for b in bends if b.status == 'Pending')
    
    # Calculate fail reasons breakdown
    fail_reasons = {}
    for b in bends:
        if b.status == 'Fail' and b.fail_reason:
            fail_reasons[b.fail_reason] = fail_reasons.get(b.fail_reason, 0) + 1
    
    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'pending': pending,
        'pass_rate': round((passed / total * 100), 1) if total > 0 else 0,
        'fail_reasons': fail_reasons
    }

@app.route('/')
def index():
    # Get filter params
    search = request.args.get('search', '')
    status_filter = request.args.get('status_filter', '')
    material_filter = request.args.get('material_filter', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    bends = get_filtered_bends(search, status_filter, material_filter, date_from, date_to)
    bend_list = [b.to_dict() for b in bends]
    stats = calculate_stats(bends)
    
    # Get unique materials for filter dropdown
    all_materials = [m[0] for m in db.session.query(BendRecord.tube_material).distinct().all()]
    
    return render_template('index.html', 
                         bends=bend_list, 
                         stats=stats,
                         search=search,
                         status_filter=status_filter,
                         material_filter=material_filter,
                         date_from=date_from,
                         date_to=date_to,
                         all_materials=all_materials)

def resolve_operator(form):
    """Resolve operator value, supporting custom 'Other' entries."""
    op = form.get('operator', '').strip()
    custom = form.get('operator_custom', '').strip()
    if op == '__custom__' or not op:
        return custom or op
    return op

@app.route('/add', methods=['POST'])
def add_bend():
    new_bend = BendRecord(
        date=request.form.get('date', datetime.now().strftime('%Y-%m-%d')),
        job_number=request.form.get('job_number', '').strip() or None,
        tube_material=request.form.get('tube_material', 'Stainless Steel').strip(),
        tube_diameter=request.form.get('tube_diameter', '').strip(),
        bend_angle=request.form.get('bend_angle', '').strip() or None,
        bend_radius=request.form.get('bend_radius', '').strip(),
        trolley_model=request.form.get('trolley_model', '').strip() or None,
        operator=resolve_operator(request.form),
        status=request.form.get('status', 'Pending'),
        fail_reason=request.form.get('fail_reason', '').strip() if request.form.get('status') == 'Fail' else None,
        notes=request.form.get('notes', '').strip()
    )

    db.session.add(new_bend)
    db.session.commit()

    flash('Bend record added successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/edit/<int:bend_id>', methods=['GET', 'POST'])
def edit_bend(bend_id):
    bend = db.session.get(BendRecord, bend_id)
    if not bend:
        flash('Record not found.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        bend.date = request.form.get('date', bend.date)
        bend.job_number = request.form.get('job_number', '').strip() or None
        bend.tube_material = request.form.get('tube_material', 'Stainless Steel').strip()
        bend.tube_diameter = request.form.get('tube_diameter', '').strip()
        bend.bend_angle = request.form.get('bend_angle', '').strip() or None
        bend.bend_radius = request.form.get('bend_radius', '').strip()
        bend.trolley_model = request.form.get('trolley_model', '').strip() or None
        bend.operator = resolve_operator(request.form)
        bend.status = request.form.get('status', 'Pending')
        bend.fail_reason = request.form.get('fail_reason', '').strip() if request.form.get('status') == 'Fail' else None
        bend.notes = request.form.get('notes', '').strip()

        
        db.session.commit()
        flash('Bend record updated successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('edit.html', bend=bend.to_dict())

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

@app.route('/export')
def export_csv():
    bends = BendRecord.query.order_by(BendRecord.date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Job Number', 'Material', 'Diameter (mm)', 
                     'Angle (°)', 'Radius (mm)', 'Trolley Model', 'Operator', 
                     'Status', 'Fail Reason', 'Notes', 'Created At'])
    
    for b in bends:
        writer.writerow([b.id, b.date, b.job_number, b.tube_material, 
                        b.tube_diameter, b.bend_angle, b.bend_radius, 
                        b.trolley_model, b.operator, b.status, 
                        b.fail_reason or '', b.notes or '', b.created_at])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=bend_records_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

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
