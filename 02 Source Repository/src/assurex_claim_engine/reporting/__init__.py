"""
AssureX Claim Engine - Reporting Package
Generates downloadable adjudication reports, printable dossiers, and PDF documents.
"""
from .pdf_generator import generate_claim_pdf_report

__all__ = ["generate_claim_pdf_report"]
