# File: agents/pdf_agent.py

import logging
import os
from datetime import datetime
import re
import PyPDF2
from agents.base_agent import Agent

logger = logging.getLogger(__name__)

class PdfAgent(Agent):
    """
    Agent specialized in processing PDF files.
    Extracts structured data, identifies document type,
    and flags specific conditions like high-value invoices.
    """
    
    def __init__(self, memory_store):
        super().__init__(memory_store)
        
    def process(self, file_path, metadata):
        """Process a PDF file and extract relevant information."""
        logger.info(f"Processing PDF file: {file_path}")
        
        try:
            # Open the PDF file
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Get basic PDF info
                num_pages = len(pdf_reader.pages)
                
                # Extract text from all pages
                full_text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n\n"
                
                # Determine document type
                document_type = self._determine_document_type(full_text)
                
                # Process based on document type
                if document_type == "Invoice":
                    invoice_data = self._extract_invoice_data(full_text)
                    result = {
                        "document_type": document_type,
                        "page_count": num_pages,
                        "invoice_data": invoice_data,
                        "summary": self._generate_summary(full_text, document_type, invoice_data)
                    }
                elif document_type == "Policy Document":
                    policy_data = self._extract_policy_data(full_text)
                    result = {
                        "document_type": document_type,
                        "page_count": num_pages,
                        "policy_data": policy_data,
                        "summary": self._generate_summary(full_text, document_type, policy_data)
                    }
                elif document_type == "Resume":
                    resume_data = self._extract_resume_data(full_text)
                    result = {
                        "document_type": document_type,
                        "page_count": num_pages,
                        "resume_data": resume_data,
                        "summary": self._generate_summary(full_text, document_type, resume_data)
                    }
                else:
                    result = {
                        "document_type": document_type,
                        "page_count": num_pages,
                        "summary": self._generate_summary(full_text, document_type)
                    }
                
                # Store the results in memory
                document_id = metadata["document_id"]
                self.memory_store.store(document_id, "pdf_analysis", result)
                
                return result
                
        except Exception as e:
            logger.error(f"Error processing PDF: {e}", exc_info=True)
            raise
    
    def _determine_document_type(self, text):
        """Determine the type of PDF document based on content analysis."""
        text_lower = text.lower()
        
        # Count occurrences of key terms for each document type
        invoice_terms = ["invoice", "bill", "payment", "amount due", "total due", "subtotal"]
        policy_terms = ["policy", "regulation", "compliance", "guidelines", "terms and conditions", 
                       "gdpr", "hipaa", "ccpa", "pci", "sox"]
        report_terms = ["report", "analysis", "study", "findings", "results", "quarterly", "annual", "executive summary"]
        resume_terms = ["resume", "cv", "experience", "education", "skills", "employment", "work history", 
                       "qualifications", "profile", "references", "certifications"]
        
        invoice_count = sum(text_lower.count(term) for term in invoice_terms)
        policy_count = sum(text_lower.count(term) for term in policy_terms)
        report_count = sum(text_lower.count(term) for term in report_terms)
        resume_count = sum(text_lower.count(term) for term in resume_terms)
        
        # Resume-specific patterns
        if any(pattern in text_lower for pattern in ["work experience", "professional experience", "education", "skills"]):
            resume_count += 3
        
        # Report-specific patterns
        if any(pattern in text_lower for pattern in ["executive summary", "key findings", "market analysis"]):
            report_count += 3
        
        # Determine document type based on highest count with minimum threshold
        max_count = max(invoice_count, policy_count, report_count, resume_count)
        
        if max_count == 0:
            return "General Document"
        elif max_count == invoice_count and invoice_count >= 2:
            return "Invoice"
        elif max_count == policy_count and policy_count >= 2:
            return "Policy Document"
        elif max_count == report_count and report_count >= 2:
            return "Report"
        elif max_count == resume_count and resume_count >= 2:
            return "Resume"
        else:
            return "General Document"
    
    def _extract_invoice_data(self, text):
        """Extract structured data from an invoice PDF."""
        # Find invoice number
        invoice_number_patterns = [
            r'invoice\s*(?:no|num|number|#)?\s*[:#]?\s*([\w\d-]+)',
            r'inv\s*[:#]?\s*([\w\d-]+)',
            r'invoice\s*[:#]?\s*([\w\d-]+)'
        ]
        
        invoice_number = "Unknown"
        for pattern in invoice_number_patterns:
            invoice_match = re.search(pattern, text.lower())
            if invoice_match:
                invoice_number = invoice_match.group(1)
                break
        
        # Find invoice date
        date_patterns = [
            r'date\s*[:#]?\s*([\d/.-]+)',
            r'invoice\s*date\s*[:#]?\s*([\d/.-]+)'
        ]
        
        invoice_date = "Unknown"
        for pattern in date_patterns:
            date_match = re.search(pattern, text.lower())
            if date_match:
                invoice_date = date_match.group(1)
                break
        
        # Find total amount
        total_patterns = [
            r'total\s*due\s*[:#]?\s*[$€£]?\s*([\d,]+\.?\d*)',
            r'total\s*amount\s*[:#]?\s*[$€£]?\s*([\d,]+\.?\d*)',
            r'amount\s*due\s*[:#]?\s*[$€£]?\s*([\d,]+\.?\d*)',
            r'grand\s*total\s*[:#]?\s*[$€£]?\s*([\d,]+\.?\d*)',
            r'total\s*[:#]?\s*[$€£]?\s*([\d,]+\.?\d*)'
        ]
        
        total = 0.0
        for pattern in total_patterns:
            total_match = re.search(pattern, text.lower())
            if total_match:
                # Remove commas and convert to float
                total_str = total_match.group(1).replace(',', '')
                try:
                    total = float(total_str)
                    break
                except ValueError:
                    logger.warning(f"Could not convert total amount to float: {total_str}")
        
        # Find currency
        currency = "USD"  # Default
        currency_symbols = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "¥": "JPY"
        }
        
        for symbol, curr in currency_symbols.items():
            if symbol in text:
                currency = curr
                break
        
        # Extract line items (simplified)
        line_items = []
        # In a real implementation, this would use more sophisticated parsing
        # to extract line items based on layout analysis
        
        return {
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "total": total,
            "currency": currency,
            "line_items": line_items
        }
    
    def _extract_policy_data(self, text):
        """Extract structured data from a policy document PDF."""
        text_lower = text.lower()
        
        # Extract policy number
        policy_number_patterns = [
            r'policy\s*(?:no|num|number|#)?\s*[:#]?\s*([\w\d-]+)',
            r'policy\s*[:#]?\s*([\w\d-]+)'
        ]
        
        policy_number = "Unknown"
        for pattern in policy_number_patterns:
            policy_match = re.search(pattern, text_lower)
            if policy_match:
                policy_number = policy_match.group(1)
                break
        
        # Extract effective date
        date_patterns = [
            r'effective\s*date\s*[:#]?\s*([\d/.-]+)',
            r'date\s*effective\s*[:#]?\s*([\d/.-]+)',
            r'effective\s*[:#]?\s*([\d/.-]+)'
        ]
        
        effective_date = "Unknown"
        for pattern in date_patterns:
            date_match = re.search(pattern, text_lower)
            if date_match:
                effective_date = date_match.group(1)
                break
        
        # Check for regulatory mentions
        regulations = []
        reg_keywords = {
            "gdpr": "GDPR (General Data Protection Regulation)",
            "hipaa": "HIPAA (Health Insurance Portability and Accountability Act)",
            "pci dss": "PCI DSS (Payment Card Industry Data Security Standard)",
            "pci": "PCI (Payment Card Industry)",
            "sox": "SOX (Sarbanes-Oxley Act)",
            "fda": "FDA (Food and Drug Administration)",
            "iso": "ISO (International Organization for Standardization)",
            "ccpa": "CCPA (California Consumer Privacy Act)"
        }
        
        for reg, full_name in reg_keywords.items():
            if reg in text_lower:
                regulations.append(full_name)
        
        # Extract policy scope and coverage
        scope = "Unknown"
        scope_match = re.search(r'scope\s*:?(.*?)(?:\n\n|\n\d|$)', text_lower, re.DOTALL)
        if scope_match:
            scope = scope_match.group(1).strip()
        
        return {
            "policy_number": policy_number,
            "effective_date": effective_date,
            "regulations": regulations,
            "has_regulatory_mentions": len(regulations) > 0,
            "scope": scope
        }
    
    def _extract_resume_data(self, text):
        """Extract structured data from a resume PDF."""
        text_lower = text.lower()
        
        # Extract name (typically at the top)
        lines = text.split('\n')
        name = lines[0] if lines else "Unknown"
        
        # Try to extract contact information
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        email = email_match.group(0) if email_match else "Unknown"
        
        # Try to extract phone
        phone_match = re.search(r'[\+\(]?[1-9][0-9 \-\(\)]{8,}[0-9]', text)
        phone = phone_match.group(0) if phone_match else "Unknown"
        
        # Extract skills section
        skills = []
        skills_section = re.search(r'(?:skills|technical skills|core competencies)(?::|.{0,10})\s*(.*?)(?:\n\n|\n\w+:|\Z)', 
                             text_lower, re.IGNORECASE | re.DOTALL)
        if skills_section:
            skills_text = skills_section.group(1).strip()
            skills = [skill.strip() for skill in re.split(r'[,•\n]', skills_text) if skill.strip()]
        
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "skills": skills[:5]  # Limit to top 5 skills
        }
    
    def _generate_summary(self, text, document_type, data=None):
        """Generate a summary of the PDF content."""
        # Word count
        word_count = len(text.split())
        
        if document_type == "Invoice":
            if data and isinstance(data, dict):
                inv_num = data.get("invoice_number", "Unknown")
                total = data.get("total", 0.0)
                currency = data.get("currency", "USD")
                
                if inv_num != "Unknown" and total > 0:
                    return f"This is an invoice ({inv_num}) with a total amount of {currency} {total:.2f}, containing {word_count} words."
            
            return f"This is an invoice document with {word_count} words."
            
        elif document_type == "Policy Document":
            if data and isinstance(data, dict):
                policy_num = data.get("policy_number", "Unknown")
                regulations = data.get("regulations", [])
                
                if policy_num != "Unknown" and regulations:
                    reg_str = ", ".join([r.split(" (")[0] for r in regulations])
                    return f"This is a policy document ({policy_num}) referencing {reg_str}, containing {word_count} words."
                
            return f"This is a policy document with {word_count} words."
            
        elif document_type == "Resume":
            if data and isinstance(data, dict):
                name = data.get("name", "Unknown")
                skills = data.get("skills", [])
                
                if name != "Unknown" and skills:
                    skills_str = ", ".join(skills[:3])  # Show top 3 skills
                    return f"This is a resume for {name} with skills including {skills_str}, containing {word_count} words."
                
            return f"This is a resume document with {word_count} words."
            
        elif document_type == "Report":
            # Try to extract the report title
            title_match = re.search(r'^([^\n.]+)', text.strip())
            title = title_match.group(1) if title_match else "report"
            
            # Truncate long title
            if len(title) > 50:
                title = title[:47] + "..."
                
            return f"This is a {document_type.lower()} about {title.lower()}, containing {word_count} words."
            
        else:
            return f"This is a {document_type.lower()} with {word_count} words."