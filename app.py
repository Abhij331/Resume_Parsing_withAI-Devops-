from flask import Flask, render_template, request
from PyPDF2 import PdfReader
import pdfplumber
from PIL import Image
import google.generativeai as genai
import os
import json
import re

# Set your API key

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


# App creation
app = Flask(__name__)

# Initialize Generative AI model
model = genai.GenerativeModel("models/gemini-1.5-pro")


def extract_text_from_pdf(file):
    """
    Extracts text from a PDF file using PyPDF2 and PDFplumber.
    """
    text = ""

    try:
        # Attempt to extract text using PyPDF2
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print(f"PyPDF2 failed: {e}")

    # If PyPDF2 extraction fails or yields insufficient text, try PDFplumber
    if not text.strip():
        try:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            print(f"PDFplumber failed: {e}")

   
    return text


def resumes_details(resume):
    """
    Processes the extracted text with the Generative AI model to extract resume details.
    """
    prompt = f"""
    You are a resume parsing assistant. Given the following resume text, extract all the important details and return them in a well-structured JSON format.

    The resume text:
    {resume}

    Extract and include the following:
    - Full Name
    - Contact Number
    - Email Address
    - Location
    - Technical Skills
    - Non-Technical Skills
    - Education
    - Work Experience (including company name, role, and responsibilities)
    - Certifications
    - Languages spoken
    - Suggested Resume Category (based on the skills and experience)
    - Recommended Job Roles (based on the candidate's skills and experience)

    Return the response in JSON format.
    """

    # Generate response from the model
    response = model.generate_content(prompt).text
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return render_template('index.html', error="No file part")

    file = request.files['resume']

    if file.filename == '':
        return render_template('index.html', error="No selected file")

    if file and file.filename.endswith('.pdf'):
        try:
            # Extract text from the PDF
            text = extract_text_from_pdf(file)

            if not text.strip():
                return render_template('index.html', error="Failed to extract text from the PDF. Please check the file.")

            # Get resume details from the model
            response = resumes_details(text)
            print("Raw Model Response:", response)

            # Clean the response
            response_clean = re.search(r'{.*}', response, re.DOTALL)
            if response_clean:
                response_clean = response_clean.group()
            else:
                return render_template('index.html', error="Failed to extract valid JSON from the model response")

            # Parse JSON
            try:
                data = json.loads(response_clean)
            except json.JSONDecodeError as e:
                print("JSON Parsing Error:", e)
                return render_template('index.html', error="Failed to parse JSON from the model response")

            # Pass data to the template for rendering
            return render_template('index.html', 
                                   full_name=data.get('full_name'),
                                   contact_number=data.get('contact_number'),
                                   email_address=data.get('email_address'),
                                   location=data.get('location'),
                                   technical_skills=data.get('technical_skills'),
                                   non_technical_skills=data.get('non_technical_skills'),
                                   education=data.get('education'),
                                   work_experience=data.get('work_experience'),
                                   certifications=data.get('certifications'),
                                   languages=data.get('languages'),
                                   suggested_resume_category=data.get('suggested_resume_category'),
                                   recommended_job_roles=data.get('recommended_job_roles'))
        except Exception as e:
            print("Error occurred:", e)
            return render_template('index.html', error="An error occurred while processing the resume.")
    else:
        return render_template('index.html', error="Invalid file type. Please upload a PDF resume.")


# Start the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

