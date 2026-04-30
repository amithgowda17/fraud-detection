from flask import Flask, request, render_template, redirect, url_for, session, send_file
import numpy as np
import pickle
import pandas as pd
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

model = pickle.load(open('model.pkl', 'rb'))

LOG_FILE = "transactions_log.csv"

if not os.path.exists(LOG_FILE):
    df = pd.DataFrame(columns=["amount","time","location","device","history","result"])
    df.to_csv(LOG_FILE, index=False)

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form['username']=="admin" and request.form['password']=="admin":
            session['user']="admin"
            return redirect(url_for('home'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

# HOME
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = pd.read_csv(LOG_FILE)

    fraud = len(data[data['result']=="Fraud"])
    safe = len(data[data['result']=="Safe"])
    total = fraud + safe
    percent = (fraud/total*100) if total>0 else 0

    return render_template("index.html",
        fraud=fraud,
        safe=safe,
        total=total,
        percent=round(percent,2),
        result=None,
        explanation=None
    )

# PREDICT
@app.route('/predict_ui', methods=['POST'])
def predict_ui():
    amount=float(request.form['amount'])
    time=float(request.form['time'])
    location=float(request.form['location'])
    device=float(request.form['device'])
    history=float(request.form['history'])

    data=np.array([[amount,time,location,device,history]])
    pred=model.predict(data)[0]

    if pred==1:
        result="⚠️ Fraud Transaction"
        explanation="Abnormal behavior detected (amount/location/history)."
        label="Fraud"
    else:
        result="✅ Safe Transaction"
        explanation="Transaction matches normal behavior."
        label="Safe"

    new=pd.DataFrame([[amount,time,location,device,history,label]],
        columns=["amount","time","location","device","history","result"])
    new.to_csv(LOG_FILE,mode='a',header=False,index=False)

    df=pd.read_csv(LOG_FILE)
    fraud=len(df[df['result']=="Fraud"])
    safe=len(df[df['result']=="Safe"])
    total=fraud+safe
    percent=(fraud/total*100) if total>0 else 0

    return render_template("index.html",
        fraud=fraud,
        safe=safe,
        total=total,
        percent=round(percent,2),
        result=result,
        explanation=explanation
    )

# PDF REPORT
@app.route('/download_report')
def download_report():
    df=pd.read_csv(LOG_FILE)

    fraud=len(df[df['result']=="Fraud"])
    safe=len(df[df['result']=="Safe"])
    total=fraud+safe

    file="fraud_report.pdf"

    doc=SimpleDocTemplate(file)
    styles=getSampleStyleSheet()

    content=[]
    content.append(Paragraph("Fraud Detection Report", styles['Title']))
    content.append(Spacer(1,10))
    content.append(Paragraph(f"Total: {total}", styles['Normal']))
    content.append(Paragraph(f"Fraud: {fraud}", styles['Normal']))
    content.append(Paragraph(f"Safe: {safe}", styles['Normal']))

    doc.build(content)

    return send_file(file, as_attachment=True)

# LOGOUT
@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect(url_for('login'))

if __name__=="__main__":
    app.run(debug=True)