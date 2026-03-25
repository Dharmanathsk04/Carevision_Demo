from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import numpy as np
import pandas as pd
import joblib
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'carevision_secret_key_2025'  # Required for session

# ================= LOAD HEART MODEL =================
try:
    heart_model = joblib.load("heart_model.pkl")
    heart_scaler = joblib.load("heart_scaler.pkl")
    print("✅ Heart model loaded successfully")
except Exception as e:
    print(f"❌ Error loading heart model: {e}")
    heart_model = None
    heart_scaler = None

heart_columns = [
    "age", "sex", "cp", "trestbps", "chol",
    "fbs", "restecg", "thalach", "exang",
    "oldpeak", "slope", "ca", "thal"
]

# ================= LOAD DIABETES MODEL =================
try:
    diabetes_model = joblib.load("diabetes_model.pkl")
    diabetes_scaler = joblib.load("diabetes_scaler.pkl")
    gender_encoder = joblib.load("gender_encoder.pkl")
    smoking_encoder = joblib.load("smoking_encoder.pkl")
    print("✅ Diabetes model loaded successfully")
except Exception as e:
    print(f"❌ Error loading diabetes model: {e}")
    diabetes_model = None
    diabetes_scaler = None
    gender_encoder = None
    smoking_encoder = None

diabetes_columns = [
    "gender", "age", "hypertension", "heart_disease",
    "smoking_history", "bmi", "hba1c_level", "blood_glucose_level"
]

# ================= PREDICTION HISTORY =================
PREDICTION_HISTORY = []

# ================= LOGIN ROUTES =================

@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    # Simple login (for demo, accept any credentials)
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    
    if username and password:
        session['logged_in'] = True
        session['username'] = username
        # Initialize empty prediction history for new user
        if not any(p.get('username') == username for p in PREDICTION_HISTORY):
            # Add some sample data for demo
            sample_predictions = [
                {
                    'username': username,
                    'date': '2024-12-15 14:30',
                    'disease': 'heart',
                    'risk_high': False,
                    'probability': 15.2,
                    'health_score': 85
                },
                {
                    'username': username,
                    'date': '2024-12-10 11:20',
                    'disease': 'diabetes',
                    'risk_high': True,
                    'probability': 68.5,
                    'health_score': 32
                },
                {
                    'username': username,
                    'date': '2024-12-05 09:45',
                    'disease': 'heart',
                    'risk_high': True,
                    'probability': 72.3,
                    'health_score': 28
                }
            ]
            PREDICTION_HISTORY.extend(sample_predictions)
        
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ================= DASHBOARD ROUTE =================

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    
    username = session.get('username', 'User')
    
    # Filter predictions for current user
    user_predictions = [p for p in PREDICTION_HISTORY if p.get('username') == username]
    
    # Calculate statistics
    heart_count = len([p for p in user_predictions if p.get('disease') == 'heart'])
    diabetes_count = len([p for p in user_predictions if p.get('disease') == 'diabetes'])
    
    # Calculate accuracy based on user predictions (sample data)
    if len(user_predictions) > 0:
        high_risk_count = len([p for p in user_predictions if p.get('risk_high')])
        # This is a simplified accuracy calculation for demo
        accuracy = min(95.7, 100 - (high_risk_count * 5))
    else:
        accuracy = 95.7
    
    # Get recent predictions (last 5, most recent first)
    recent_predictions = sorted(
        user_predictions,
        key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d %H:%M") if isinstance(x['date'], str) else x['date'],
        reverse=True
    )[:5]
    
    return render_template("dashboard.html",
                         username=username,
                         heart_count=heart_count,
                         diabetes_count=diabetes_count,
                         accuracy=round(accuracy, 1),
                         recent_predictions=recent_predictions)

# ================= CHAT ROUTE =================

@app.route("/chat")
def chat():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    return render_template("chat.html", username=session.get('username', 'User'))

# ================= MAP ROUTE =================

@app.route("/map")
def map_page():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    return render_template("map.html")

# ================= MEDICAL ROUTE =================

@app.route("/medical")
def medical_page():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    return render_template("medical.html")

# ================= PROTECTED ROUTES =================

@app.route("/heart", methods=["GET", "POST"])
def heart_page():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    
    if request.method == "POST":
        return heart_predict()
    return render_template("index.html")

@app.route("/diabetes", methods=["GET", "POST"])
def diabetes_page():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    
    if request.method == "POST":
        return diabetes_predict()
    return render_template("index2.html")

# ================= HEART PREDICTION =================
def heart_predict():
    try:
        if heart_model is None or heart_scaler is None:
            return "Heart model not loaded. Please check server logs.", 500
        
        values = []
        for col in heart_columns:
            value = request.form.get(col)
            if not value:
                return f"Missing value for {col}. Please fill all fields.", 400
            try:
                values.append(float(value))
            except ValueError:
                return f"Invalid value for {col}. Must be a number.", 400
        
        df = pd.DataFrame([values], columns=heart_columns)
        scaled = heart_scaler.transform(df)

        pred = heart_model.predict(scaled)[0]
        prob = heart_model.predict_proba(scaled)[0][1] * 100
        health = round(100 - prob)
        
        username = session.get('username', 'User')
        
        # Save to history
        PREDICTION_HISTORY.append({
            'username': username,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'disease': 'heart',
            'risk_high': bool(pred == 1),
            'probability': round(prob, 2),
            'health_score': health
        })

        return render_template("result.html",
                               pred=pred,
                               prob=round(prob, 2),
                               health=health)
    except Exception as e:
        return f"Error processing prediction: {str(e)}", 400

# ================= DIABETES PREDICTION =================
def diabetes_predict():
    try:
        if diabetes_model is None or diabetes_scaler is None:
            return "Diabetes model not loaded. Please check server logs.", 500
        
        # Get form data
        gender = request.form.get("gender", "").lower().strip()
        smoking = request.form.get("smoking_history", "").lower().strip()
        
        if not gender or not smoking:
            return "Gender and smoking history are required.", 400
        
        # Encode categorical values
        try:
            gender_encoded = gender_encoder.transform([gender])[0]
            smoking_encoded = smoking_encoder.transform([smoking])[0]
        except Exception as e:
            return f"Invalid value. Valid genders: {list(gender_encoder.classes_)}", 400
        
        # Get numerical values
        try:
            values = [
                gender_encoded,
                float(request.form.get("age", 0)),
                int(request.form.get("hypertension", 0)),
                int(request.form.get("heart_disease", 0)),
                smoking_encoded,
                float(request.form.get("bmi", 0)),
                float(request.form.get("hba1c_level", 0)),
                float(request.form.get("blood_glucose_level", 0))
            ]
        except ValueError:
            return "All fields must be valid numbers.", 400
        
        # Make prediction
        df = pd.DataFrame([values], columns=diabetes_columns)
        scaled = diabetes_scaler.transform(df)

        pred = diabetes_model.predict(scaled)[0]
        prob = diabetes_model.predict_proba(scaled)[0][1] * 100
        health = round(100 - prob)
        
        username = session.get('username', 'User')
        
        # Save to history
        PREDICTION_HISTORY.append({
            'username': username,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'disease': 'diabetes',
            'risk_high': bool(pred == 1),
            'probability': round(prob, 2),
            'health_score': health
        })

        return render_template("result2.html",
                               pred=pred,
                               prob=round(prob, 2),
                               health=health)
    except Exception as e:
        return f"Error processing diabetes prediction: {str(e)}", 400

# ================= CHAT API ENDPOINT =================
@app.route("/api/chat", methods=["POST"])
def chat_api():
    try:
        if not session.get('logged_in'):
            return jsonify({"error": "Not authenticated"}), 401
            
        data = request.json
        message = data.get("message", "").strip()
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # Here you would integrate with your actual AI service
        # For now, returning a simple response
        response = f"I understand you're asking about: '{message}'. As Carevision AI, I'm here to help with health-related questions. However, please note that I'm a demo version and should not replace professional medical advice."
        
        return jsonify({
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ================= API ENDPOINT FOR JS =================
@app.route("/predict", methods=["POST"])
def api_predict():
    try:
        if not session.get('logged_in'):
            return jsonify({"error": "Not authenticated"}), 401
            
        data = request.json
        
        if data["disease"] != "diabetes":
            return jsonify({"error": "Only diabetes prediction available via API"}), 400
        
        if diabetes_model is None:
            return jsonify({"error": "Diabetes model not loaded"}), 500
        
        # Extract and process data
        inputs = data["inputs"]
        
        if len(inputs) != 8:
            return jsonify({"error": "Expected 8 input values"}), 400
        
        # Note: For API, we need to encode gender and smoking
        gender_str = str(inputs[0]).lower()
        smoking_str = str(inputs[4]).lower()
        
        try:
            gender_encoded = gender_encoder.transform([gender_str])[0]
            smoking_encoded = smoking_encoder.transform([smoking_str])[0]
        except Exception as e:
            return jsonify({"error": f"Encoding error: {str(e)}"}), 400
        
        # Replace with encoded values
        processed_inputs = [
            gender_encoded,
            float(inputs[1]),
            int(inputs[2]),
            int(inputs[3]),
            smoking_encoded,
            float(inputs[5]),
            float(inputs[6]),
            float(inputs[7])
        ]
        
        df = pd.DataFrame([processed_inputs], columns=diabetes_columns)
        scaled = diabetes_scaler.transform(df)
        
        pred = diabetes_model.predict(scaled)[0]
        prob = diabetes_model.predict_proba(scaled)[0][1] * 100
        health = round(100 - prob)
        
        # Save API prediction to history
        username = session.get('username', 'User')
        PREDICTION_HISTORY.append({
            'username': username,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'disease': 'diabetes',
            'risk_high': bool(pred == 1),
            'probability': round(prob, 2),
            'health_score': health,
            'via_api': True
        })
        
        return jsonify({
            "prediction": int(pred),
            "probability": round(prob, 2),
            "health_score": health
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ================= PROFILE PAGE =================
@app.route("/profile")
def profile():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    
    username = session.get('username', 'User')
    
    # Calculate user stats
    user_predictions = [p for p in PREDICTION_HISTORY if p.get('username') == username]
    heart_count = len([p for p in user_predictions if p.get('disease') == 'heart'])
    diabetes_count = len([p for p in user_predictions if p.get('disease') == 'diabetes'])
    
    return render_template("profile.html",
                         username=username,
                         heart_count=heart_count,
                         diabetes_count=diabetes_count)

# ================= HISTORY PAGE =================
@app.route("/history")
def history():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    
    username = session.get('username', 'User')
    
    # Get user's predictions sorted by date (newest first)
    user_predictions = [p for p in PREDICTION_HISTORY if p.get('username') == username]
    sorted_predictions = sorted(
        user_predictions,
        key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d %H:%M") if isinstance(x['date'], str) else x['date'],
        reverse=True
    )
    
    return render_template("history.html",
                         predictions=sorted_predictions,
                         username=username)

# ================= EXPORT DATA =================
@app.route("/export")
def export_data():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    
    username = session.get('username', 'User')
    
    # Filter user's predictions
    user_predictions = [p for p in PREDICTION_HISTORY if p.get('username') == username]
    
    # Convert to JSON for download
    data = json.dumps(user_predictions, indent=2, default=str)
    
    return Response(
        data,
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename={username}_predictions.json"}
    )

# ================= HEALTH TIPS API =================
@app.route("/api/health-tips")
def health_tips():
    tips = [
        "Monitor your blood pressure regularly",
        "Maintain healthy cholesterol levels",
        "Check blood sugar if diabetic",
        "Regular exercise reduces heart risk by 30%",
        "Adequate sleep improves metabolic health",
        "Stay hydrated - drink at least 2 liters of water daily",
        "Include fruits and vegetables in every meal",
        "Limit processed foods and sugar intake",
        "Manage stress through meditation or yoga",
        "Get regular health check-ups"
    ]
    return jsonify({"tips": tips})

# ================= ERROR HANDLERS =================
@app.errorhandler(404)
def page_not_found(e):
    return "Page not found. <a href='/'>Go to Login</a>", 404

@app.errorhandler(500)
def internal_server_error(e):
    return "Server error. <a href='/'>Go to Login</a>", 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)