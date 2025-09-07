from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Flask App Setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB file size limit

# Load Gemini API Key
load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Check File Type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Process Uploaded File
def process_file(filepath):
    df = pd.read_excel(filepath)
    df.columns = df.columns.str.lower().str.strip()

    required_cols = {'amount', 'category', 'date'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Excel must contain columns: {required_cols}")

    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime("%B %Y")

    summary = df.groupby(['month', 'category'])['amount'].sum().reset_index()
    return df, summary

# Get AI-Powered Insight
def get_ai_insight(summary):
    summary_str = summary.to_string(index=False)
    prompt = f"""
    Here is a summary of monthly expenses grouped by Category.
    Please analyze the trends and suggest 3 to 5 bullet-point actionable insights.

    {summary_str}
    """

    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text.strip()

# Home Page Route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            df, summary = process_file(filepath)
            insight = get_ai_insight(summary)

            # Chart Data Preparation
            category_group = df.groupby('category')['amount'].sum().sort_values(ascending=False)
            bar_labels = category_group.index.tolist()
            bar_values = category_group.values.tolist()

            pie_labels = bar_labels
            pie_values = bar_values

            return render_template(
                'index.html',
                summary=summary.values.tolist(),
                insight=insight,
                bar_labels=bar_labels,
                bar_values=bar_values,
                pie_labels=pie_labels,
                pie_values=pie_values
            )

        return "Invalid file format. Please upload a .csv, .xls, or .xlsx file."

    return render_template('index.html', summary=None, insight=None)

# Create Uploads Folder & Run Server
if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True)
