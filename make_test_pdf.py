"""Create a 3-page PDF with distinct, extractable text using fpdf2."""
from fpdf import FPDF

PAGES = [
    (
        "Introduction",
        "This document describes machine learning concepts. Neural networks are "
        "computational models inspired by the brain. Deep learning uses multiple "
        "layers to learn representations from data. The perceptron is the simplest "
        "neural network unit. Backpropagation trains deep networks efficiently."
    ),
    (
        "Revenue Analysis",
        "Total revenue for Q1 was five million dollars. Q2 revenue increased by "
        "fifteen percent. Annual growth rate is twelve percent. Sales team expanded "
        "to thirty members. Quarterly profit margin reached twenty two percent. "
        "Operating costs reduced by eight percent in the fiscal year."
    ),
    (
        "Conclusion",
        "The study concludes that neural networks outperform traditional regression "
        "methods on complex tasks. Future work includes expanding datasets and "
        "improving hyperparameter tuning strategies. Gradient descent optimisation "
        "remains a key research area in deep learning applications."
    ),
]

def make_pdf(path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for heading, body in PAGES:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, heading, ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 8, body)
    pdf.output(path)
    print(f"PDF written: {path}  ({len(PAGES)} pages)")

if __name__ == "__main__":
    make_pdf(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\test_sample.pdf")
