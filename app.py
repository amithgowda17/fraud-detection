from flask import Flask, request, render_template, redirect, url_for, session, send_file
import numpy as np
import pickle
import pandas as pd
import os
import matplotlib.pyplot as plt

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

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

# ---------------- INSIGHTS PAGE ----------------
@app.route('/insights')
def insights():
    if 'user' not in session:
        return redirect(url_for('login'))

    df = pd.read_csv(LOG_FILE)

    fraud = len(df[df['result']=="Fraud"])
    safe = len(df[df['result']=="Safe"])
    total = fraud + safe
    percent = (fraud/total*100) if total>0 else 0

    return render_template("insights.html",
        fraud=fraud,
        safe=safe,
        total=total,
        percent=round(percent,2)
    )


# ---------------- ABOUT PAGE ----------------
@app.route('/about')
def about():
    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template("about.html")


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

# ---------------- PDF REPORT (FINAL CORPORATE) ----------------
@app.route('/download_report')
def download_report():
    df = pd.read_csv(LOG_FILE)

    fraud = len(df[df['result']=="Fraud"])
    safe = len(df[df['result']=="Safe"])
    total = fraud + safe
    percent = (fraud/total*100) if total>0 else 0

    pie_path = "pie.png"
    bar_path = "bar.png"

    # PIE CHART
    plt.figure()
    plt.pie([fraud, safe], labels=["Fraud","Safe"], autopct='%1.1f%%',
            colors=["#ef4444","#22c55e"])
    plt.savefig(pie_path)
    plt.close()

    # BAR CHART
    plt.figure()
    plt.bar(["Fraud","Safe"], [fraud,safe], color=["#ef4444","#22c55e"])
    plt.savefig(bar_path)
    plt.close()

    file = "fraud_report.pdf"

    doc = SimpleDocTemplate(file)
    styles = getSampleStyleSheet()

    content = []

    from datetime import datetime

    # HEADER
    content.append(Paragraph("<b>Fraud Detection System - Corporate Report</b>", styles['Heading1']))
    content.append(Paragraph("Financial Transaction Analysis Dashboard", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d %B %Y, %H:%M')}",
        styles['Normal']))
    content.append(Spacer(1, 15))

    # WIDE TABLE
    table_data = [
        ["Metric", "Description", "Value"],
        ["Total Transactions", "All processed transactions in system", total],
        ["Fraud Transactions", "Transactions flagged as suspicious", fraud],
        ["Safe Transactions", "Transactions considered normal", safe],
        ["Fraud Percentage", "Fraud ratio in total transactions", f"{round(percent,2)}%"]
    ]

    table = Table(table_data, colWidths=[150, 250, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('BACKGROUND',(0,1),(-1,-1),colors.whitesmoke)
    ]))

    content.append(table)
    content.append(Spacer(1, 15))

    # CHARTS SIDE-BY-SIDE
    chart_table = Table([
        [
            Image(pie_path, width=230, height=150),
            Image(bar_path, width=230, height=150)
        ]
    ], colWidths=[260, 260])

    content.append(chart_table)
    content.append(Spacer(1, 15))

    # INSIGHT
    if percent > 50:
        msg = "High fraud activity detected. Immediate monitoring and investigation is strongly recommended."
        bg = colors.HexColor("#fee2e2")
    else:
        msg = "Fraud levels are within acceptable limits and system behavior appears stable."
        bg = colors.HexColor("#dcfce7")

    insight = Table([[msg]], colWidths=[500])
    insight.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),bg),
        ('BOX',(0,0),(-1,-1),1,colors.black),
        ('PADDING',(0,0),(-1,-1),10)
    ]))

    content.append(insight)
    content.append(Spacer(1, 15))

    # ABOUT PROJECT
    content.append(Paragraph("<b>About This Project</b>", styles['Heading2']))
    content.append(Spacer(1, 10))

    points = [
        "• This project implements a Machine Learning-based system to detect fraudulent transactions in real-time.",
        "• It analyzes multiple behavioral factors such as transaction amount, location, device type, and past history.",
        "• The system uses a trained classification model to distinguish between safe and fraudulent transactions.",
        "• A web-based dashboard is provided to interact with the system and perform live transaction analysis.",
        "• Visual analytics such as charts and summaries help in understanding fraud trends effectively.",
        "• Automated PDF reports are generated to support monitoring and decision-making processes.",
        "• The system design is inspired by real-world banking and financial fraud detection mechanisms.",
        "• Built using Python, Flask, Scikit-learn, and data visualization tools."
    ]

    for p in points:
        content.append(Paragraph(p, styles['Normal']))
        content.append(Spacer(1, 4))

    # FOOTER
    content.append(Spacer(1, 10))
    content.append(Paragraph(
        "Confidential Report | Fraud Detection System ",
        styles['Italic']))

    # BORDER
    def draw_border(canvas, doc):
        canvas.setStrokeColor(colors.grey)
        canvas.setLineWidth(2)
        canvas.rect(20, 20, 570, 800)

    doc.build(content, onFirstPage=draw_border)

    return send_file(file, as_attachment=True)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect(url_for('login'))

if __name__=="__main__":
    app.run(debug=True)