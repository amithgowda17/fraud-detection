from flask import Flask, request, render_template, redirect, url_for, session
import numpy as np
import pickle
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "secret123"

model = pickle.load(open('model.pkl', 'rb'))

LOG_FILE = "transactions_log.csv"

if not os.path.exists(LOG_FILE):
    df = pd.DataFrame(columns=["amount","time","location","device","history","result"])
    df.to_csv(LOG_FILE, index=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username']=="admin" and request.form['password']=="admin":
            session['user'] = "admin"
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = pd.read_csv(LOG_FILE)
    fraud_count = len(data[data['result']=='Fraud'])
    safe_count = len(data[data['result']=='Safe'])

    return render_template('index.html',
        history=data.tail(5).values.tolist(),
        fraud=fraud_count,
        safe=safe_count)

@app.route('/predict_ui', methods=['POST'])
def predict_ui():
    amount = float(request.form['amount'])
    time = float(request.form['time'])
    location = float(request.form['location'])
    device = float(request.form['device'])
    history_val = float(request.form['history'])

    input_data = np.array([[amount, time, location, device, history_val]])
    prediction = model.predict(input_data)[0]

    if prediction == 1:
        result = "Fraud"
        message = "⚠️ Fraud Transaction"
    else:
        result = "Safe"
        message = "✅ Safe Transaction"

    new_row = pd.DataFrame([[amount,time,location,device,history_val,result]],
        columns=["amount","time","location","device","history","result"])
    new_row.to_csv(LOG_FILE, mode='a', header=False, index=False)

    data = pd.read_csv(LOG_FILE)

    fraud_count = len(data[data['result']=='Fraud'])
    safe_count = len(data[data['result']=='Safe'])

    return render_template('index.html',
        result=message,
        history=data.tail(5).values.tolist(),
        fraud=fraud_count,
        safe=safe_count)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
