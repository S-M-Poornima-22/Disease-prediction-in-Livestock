from flask import Flask, render_template, request, redirect, url_for
import joblib
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
# This creates a local file named 'livestock_history.db' in your project folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///livestock_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the History Table Structure
class DiagnosisHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    animal_type = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    disease = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.String(20), nullable=False)
    date_recorded = db.Column(db.DateTime, default=lambda: datetime.now())

# Create the database file and tables automatically
with app.app_context():
    db.create_all()


# Load trained model and encoders
model = joblib.load("disease_prediction_model.pkl")
label_encoders = joblib.load("label_encoders.pkl")

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Prediction Form Page
@app.route('/predict')
def predict():
    return render_template('predict.html')

# NEW ROUTE: View Historical Dashboard
@app.route('/history')
def show_history():
    # Fetch all records ordered by the newest entry first
    records = DiagnosisHistory.query.order_by(DiagnosisHistory.date_recorded.desc()).all()
    return render_template('history.html', records=records)

# Process Form and Show Result
@app.route('/result', methods=['POST'])
def result():
    animal_type = request.form['animal_type']
    age = int(request.form['age'])
    temperature = float(request.form['temperature'])
    sym1 = request.form.get('sym1', None)
    sym2 = request.form.get('sym2', None)
    sym3 = request.form.get('sym3', None)

    def encode_input(value, col):
        le = label_encoders[col]
        return le.transform([value])[0] if value in le.classes_ else 0

    encoded_input = [
        encode_input(animal_type, 'Animal_Type'),
        age,
        temperature,
        encode_input(sym1, 'symptom1') if sym1 else 0,
        encode_input(sym2, 'symptom2') if sym2 else 0,
        encode_input(sym3, 'symptom3') if sym3 else 0,
    ]

    disease_code = model.predict([encoded_input])[0]
    probabilities = model.predict_proba([encoded_input])[0]
    
    class_index = list(model.classes_).index(disease_code)
    confidence = probabilities[class_index] * 100
    confidence_formatted = f"{confidence:.1f}%"

    predicted_disease = label_encoders['Disease'].inverse_transform([disease_code])[0]

    treatment_protocols = {
        "foot and mouth": "Isolate the infected animal immediately to prevent herd contagion. Wash hooves and mouth with a mild antiseptic solution. Limit movement and contact a certified veterinarian immediately.",
        "anthrax": "CRITICAL RISK: Do not open the carcass under any circumstances. Isolate the entire area immediately and notify local veterinary health authorities instantly.",
        "blackleg": "Isolate the animal immediately. Administer high doses of antibiotics/penicillin if caught in early stages as directed by a vet. Promptly vaccinate the rest of the herd.",
        "pneumonia": "Move the animal to a dry, well-ventilated shelter away from cold drafts. Provide clean hydration and contact a vet for appropriate antibiotic or anti-inflammatory treatment.",
    }

    disease_key = predicted_disease.lower().strip()
    advice = treatment_protocols.get(
        disease_key, 
        "Isolate the animal from the rest of the herd, monitor its vitals closely, and consult a professional veterinarian for a targeted treatment plan."
    )

    # --- THE NEW UPGRADE: SAVE ENTRY TO DATABASE ---
    new_entry = DiagnosisHistory(
        animal_type=animal_type,
        age=age,
        temperature=temperature,
        disease=predicted_disease,
        confidence=confidence_formatted
    )
    db.session.add(new_entry)
    db.session.commit() # Saves it directly into the SQLite file!

    return render_template(
        'result.html', 
        disease=predicted_disease, 
        confidence=confidence_formatted, 
        treatment_advice=advice
    )

if __name__ == '__main__':
    app.run(debug=True)