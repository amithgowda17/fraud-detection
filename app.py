from flask import Flask, request, render_template, redirect, url_for, session, send_file
import numpy as np
import pickle
import pandas as pd
import os
import matplotlib.pyplot as plt

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

model = pickle.load(open('model.pkl', 'rb'))

LOG_FILE = "transactions_log.csv"

if not os.path.exists(LOG_FILE):
    df = pd.DataFrame(columns=["amount","time","location","device","history","result"])
    df.to_csv(LOG_FILE, index=False)

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form['username']=="admin" and request.form['password']=="admin":
            session['user']="admin"
            return redirect(url_for('home'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

# ---------------- HOME ----------------
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    df = pd.read_csv(LOG_FILE)

    fraud = len(df[df['result']=="Fraud"])
    safe = len(df[df['result']=="Safe"])
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

# ---------------- PREDICT ----------------
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
        explanation="Abnormal behavior detected based on transaction pattern."
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

# ---------------- PDF REPORT ----------------
@app.route('/download_report')
def download_report():
    df = pd.read_csv(LOG_FILE)

    fraud = len(df[df['result']=="Fraud"])
    safe = len(df[df['result']=="Safe"])
    total = fraud + safe
    percent = (fraud/total*100) if total>0 else 0

    pie_path = "pie.png"
    bar_path = "bar.png"

    # Pie chart
    plt.figure()
    plt.pie([fraud, safe], labels=["Fraud","Safe"], autopct='%1.1f%%')
    plt.title("Fraud Distribution")
    plt.savefig(pie_path)
    plt.close()

    # Bar chart
    plt.figure()
    plt.bar(["Fraud","Safe"], [fraud, safe])
    plt.title("Transaction Comparison")
    plt.savefig(bar_path)
    plt.close()

    file = "fraud_report.pdf"

    doc = SimpleDocTemplate(file)
    styles = getSampleStyleSheet()

    content = []

    # TITLE
    content.append(Paragraph("<b>Fraud Detection Report</b>", styles['Title']))
    content.append(Spacer(1, 15))

    # INTRO
    content.append(Paragraph(
        "This report provides an overview of transaction analysis performed by the Fraud Detection System.",
        styles['Normal']))
    content.append(Spacer(1, 20))

    # SUMMARY
    content.append(Paragraph("<b>Summary</b>", styles['Heading2']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Total Transactions: {total}", styles['Normal']))
    content.append(Paragraph(f"Fraud Transactions: {fraud}", styles['Normal']))
    content.append(Paragraph(f"Safe Transactions: {safe}", styles['Normal']))
    content.append(Paragraph(f"Fraud Percentage: {round(percent,2)}%", styles['Normal']))

    content.append(Spacer(1, 20))

    # CHARTS
    content.append(Paragraph("<b>Visual Analytics</b>", styles['Heading2']))
    content.append(Spacer(1, 10))

    content.append(Image(pie_path, width=300, height=200))
    content.append(Spacer(1, 10))
    content.append(Image(bar_path, width=300, height=200))

    content.append(Spacer(1, 20))

    # ANALYSIS
    content.append(Paragraph("<b>Analysis</b>", styles['Heading2']))
    content.append(Spacer(1, 10))

    if percent > 50:
        msg = "High fraud activity detected. Immediate monitoring recommended."
    else:
        msg = "Fraud levels are within acceptable limits."

    content.append(Paragraph(msg, styles['Normal']))

    content.append(Spacer(1, 20))

    # CONCLUSION
    content.append(Paragraph("<b>Conclusion</b>", styles['Heading2']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(
        "The system uses machine learning techniques to identify suspicious transactions "
        "based on behavioral patterns such as amount, location, and past history.",
        styles['Normal']))

    content.append(Spacer(1, 30))

    content.append(Paragraph(
        "Generated by Fraud Detection System",
        styles['Italic']))

    doc.build(content)

    return send_file(file, as_attachment=True)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect(url_for('login'))

if __name__=="__main__":
    app.run(debug=True)