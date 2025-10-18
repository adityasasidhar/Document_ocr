import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import mm
from pathlib import Path
import anthropic
import base64
from typing import List, Optional, Dict, Any
import json
import re


def get_api_key() -> str:
    """Get API key from environment variable or file."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        print("API key from environment")
        return api_key

    try:
        with open('anthropic_api_key.txt', 'r') as f:
            api_key = f.read().strip()
        print("API key from file")
        return api_key
    except FileNotFoundError:
        raise ValueError("API key not found. Set ANTHROPIC_API_KEY or create anthropic_api_key.txt")


def _extract_json(text: str) -> Dict[str, Any]:
    """Robust JSON extraction with multiple fallback strategies."""
    text = re.sub(r'```json\s*|\s*```', '', text, flags=re.IGNORECASE)
    text = text.strip()

    # Attempt 1: Direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Find JSON object with balanced braces
    try:
        start = text.find('{')
        if start != -1:
            brace_count = 0
            in_string = False
            escape_next = False

            for i in range(start, len(text)):
                char = text[i]

                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = text[start:i + 1]
                            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    # Attempt 3: Fix common JSON issues
    try:
        cleaned = re.sub(r',(\s*[}\]])', r'\1', text)
        return json.loads(cleaned)
    except:
        pass

    raise ValueError(f"Failed to extract valid JSON. Preview: {text[:500]}...")


def _load_documents(filepaths: List[str]) -> List[Dict[str, Any]]:
    """Load and encode PDF documents with prompt caching."""
    pdf_documents = []

    for idx, filepath in enumerate(filepaths):
        pdf_path = Path(filepath)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {filepath}")
        if pdf_path.suffix.lower() != '.pdf':
            raise ValueError(f"File must be a PDF, got: {pdf_path.suffix}")

        print(f"📄 Loading: {pdf_path.name}")

        with open(pdf_path, 'rb') as f:
            pdf_data = base64.standard_b64encode(f.read()).decode('utf-8')

        doc_dict = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_data
            }
        }

        if idx == len(filepaths) - 1:
            doc_dict["cache_control"] = {"type": "ephemeral"}

        pdf_documents.append(doc_dict)
        print(f"  ✓ Loaded ({len(pdf_data) / 1024:.2f} KB)")

    return pdf_documents


def _analyze_documents(client: anthropic.Anthropic, pdf_documents: List[Dict]) -> Dict[str, Any]:
    """Phase 1: Quick document analysis using Haiku."""
    print("  🤖 Using Claude Haiku...")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1500,
        temperature=0,
        messages=[{
            "role": "user",
            "content": pdf_documents + [{
                "type": "text",
                "text": """Analyze these financial documents. Return ONLY valid JSON:

{
    "company_name": "exact name",
    "balance_sheet_date": "DD/MM/YYYY",
    "fiscal_year": "YYYY",
    "document_pages": 10,
    "contains_stato_patrimoniale": true,
    "contains_conto_economico": true,
    "contains_nota_integrativa": true,
    "currency": "EUR",
    "document_quality": "clear"
}""",
                "cache_control": {"type": "ephemeral"}
            }]
        }]
    )

    summary_text = response.content[0].text.strip()
    print(f"  ✓ Analysis complete ({response.usage.input_tokens}→{response.usage.output_tokens} tokens)")

    try:
        doc_summary = _extract_json(summary_text)
    except ValueError as e:
        print(f"  ⚠️ Warning: {e}")
        doc_summary = {"document_quality": "unknown"}

    return doc_summary


def _extract_financial_data(client: anthropic.Anthropic, pdf_documents: List[Dict],
                            doc_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 2: Comprehensive data extraction using Sonnet."""
    print("  🤖 Using Claude Sonnet...")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=7000,
        temperature=0,
        messages=[{
            "role": "user",
            "content": pdf_documents + [{
                "type": "text",
                "text": f"""Extract ALL financial data from documents. Info: {json.dumps(doc_summary)}

Return ONLY valid JSON (no markdown):

{{
    "metadata": {{
        "company_name": "",
        "balance_sheet_date": "",
        "fiscal_year": ""
    }},
    "stato_patrimoniale_attivo": {{
        "A_crediti_soci": {{"value": 0, "details": {{}}}},
        "B_immobilizzazioni": {{
            "I_immateriali": {{"items": {{}}, "totale": 0}},
            "II_materiali": {{"costo_storico": 0, "fondo_ammortamento": 0, "valore_netto": 0, "items": {{}}}},
            "III_finanziarie": {{"items": {{}}, "totale": 0}},
            "totale_immobilizzazioni": 0
        }},
        "C_attivo_circolante": {{
            "I_rimanenze": {{"items": {{}}, "totale": 0}},
            "II_crediti": {{"entro_12_mesi": {{}}, "oltre_12_mesi": {{}}, "totale": 0}},
            "III_attivita_finanziarie": {{"items": {{}}, "totale": 0}},
            "IV_disponibilita_liquide": {{"items": {{}}, "totale": 0}},
            "totale_attivo_circolante": 0
        }},
        "D_ratei_risconti": {{"items": {{}}, "totale": 0}},
        "TOTALE_ATTIVO": 0
    }},
    "stato_patrimoniale_passivo": {{
        "A_patrimonio_netto": {{
            "I_capitale_sociale": 0,
            "II_riserva_sovrapprezzo": 0,
            "III_riserve_rivalutazione": 0,
            "IV_riserva_legale": 0,
            "V_riserve_statutarie": 0,
            "VI_riserva_azioni_proprie": 0,
            "VII_altre_riserve": {{}},
            "VIII_utili_perdite_portati_a_nuovo": 0,
            "IX_utile_perdita_esercizio": 0,
            "totale_patrimonio_netto": 0
        }},
        "B_fondi_rischi_oneri": {{"items": {{}}, "totale": 0}},
        "C_trattamento_fine_rapporto": 0,
        "D_debiti": {{"entro_12_mesi": {{}}, "oltre_12_mesi": {{}}, "totale": 0}},
        "E_ratei_risconti": {{"items": {{}}, "totale": 0}},
        "TOTALE_PASSIVO": 0
    }},
    "conto_economico": {{
        "A_valore_produzione": {{
            "1_ricavi_vendite": 0,
            "2_variazioni_rimanenze": 0,
            "3_variazioni_lavori_in_corso": 0,
            "4_incrementi_immobilizzazioni": 0,
            "5_altri_ricavi": {{}},
            "totale_A": 0
        }},
        "B_costi_produzione": {{
            "6_materie_prime": 0,
            "7_servizi": 0,
            "8_godimento_beni_terzi": 0,
            "9_personale": {{}},
            "10_ammortamenti_svalutazioni": {{}},
            "11_variazioni_rimanenze": 0,
            "12_accantonamenti": 0,
            "13_altri_accantonamenti": 0,
            "14_oneri_diversi_gestione": 0,
            "totale_B": 0
        }},
        "differenza_A_B": 0,
        "C_proventi_oneri_finanziari": {{
            "15_proventi_partecipazioni": 0,
            "16_altri_proventi_finanziari": {{}},
            "17_interessi_oneri_finanziari": {{}},
            "17bis_utili_perdite_cambio": 0,
            "totale_C": 0
        }},
        "D_rettifiche_valore": {{
            "18_rivalutazioni": 0,
            "19_svalutazioni": 0,
            "totale_D": 0
        }},
        "risultato_prima_imposte": 0,
        "20_imposte_reddito": {{"correnti": 0, "differite": 0, "anticipate": 0, "totale": 0}},
        "21_utile_perdita_esercizio": 0
    }},
    "nota_integrativa": {{
        "criteri_valutazione": "",
        "immobilizzazioni_immateriali": "",
        "immobilizzazioni_materiali": "",
        "immobilizzazioni_finanziarie": "",
        "rimanenze": "",
        "crediti": "",
        "debiti": "",
        "ratei_risconti": "",
        "patrimonio_netto": "",
        "fondi_rischi": "",
        "trattamento_fine_rapporto": "",
        "ricavi_costi": "",
        "imposte": "",
        "altre_informazioni": ""
    }}
}}

Extract exact numbers. Use 0 if not found. NO trailing commas."""
            }]
        }]
    )

    data_text = response.content[0].text.strip()
    print(f"  ✓ Data extracted ({response.usage.input_tokens}→{response.usage.output_tokens} tokens)")

    try:
        extracted_data = _extract_json(data_text)
    except ValueError as e:
        print(f"  ❌ Extraction failed: {e}")
        raise

    return extracted_data


def _validate_and_calculate(client: anthropic.Anthropic, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 3: Validation and calculations using Haiku."""
    print("  🤖 Using Claude Haiku...")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=6000,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""Validate and correct calculations:

{json.dumps(extracted_data, indent=2, ensure_ascii=False)}

TASKS:
1. Calculate missing subtotals
2. Verify TOTALE_ATTIVO = TOTALE_PASSIVO
3. Verify differenza_A_B = totale_A - totale_B
4. Verify risultato_prima_imposte
5. Verify utile_perdita_esercizio

Return ONLY valid JSON:

{{
    "is_balanced": true,
    "balance_difference": 0,
    "corrections_made": [],
    "corrected_data": {{
        ...same structure...
    }}
}}

NO trailing commas. NO markdown."""
        }]
    )

    result_text = response.content[0].text.strip()
    print(f"  ✓ Validated ({response.usage.input_tokens}→{response.usage.output_tokens} tokens)")

    try:
        validation_result = _extract_json(result_text)

        if not validation_result.get("is_balanced", False):
            diff = validation_result.get("balance_difference", 0)
            print(f"  ⚠️ Warning: Balance difference of €{diff:,.2f}")
        else:
            print(f"  ✓ Balance sheet is balanced")

        corrections = validation_result.get("corrections_made", [])
        if corrections:
            print(f"  📝 Made {len(corrections)} corrections")

        return validation_result.get("corrected_data", extracted_data)

    except ValueError as e:
        print(f"  ⚠️ Validation parsing failed: {e}")
        print(f"  ℹ️ Using original extracted data")
        return extracted_data


def _format_balance_sheet(client: anthropic.Anthropic, validated_data: Dict[str, Any]) -> str:
    """Phase 4: Format as Italian balance sheet using Haiku."""
    print("  🤖 Using Claude Haiku...")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=6000,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""Format as Italian balance sheet in PLAIN TEXT:

{json.dumps(validated_data, indent=2, ensure_ascii=False)}

Structure:

BILANCIO D'ESERCIZIO AL [date]
[Company Name]

STATO PATRIMONIALE - ATTIVO

A) CREDITI VERSO SOCI: € X,XXX
B) IMMOBILIZZAZIONI
  I - Immobilizzazioni immateriali: € X,XXX
  II - Immobilizzazioni materiali
      Costo storico: € X,XXX
      Fondo ammortamento: € (X,XXX)
      Valore netto: € X,XXX
  III - Immobilizzazioni finanziarie: € X,XXX
  TOTALE IMMOBILIZZAZIONI (B): € X,XXX

C) ATTIVO CIRCOLANTE
  I - Rimanenze: € X,XXX
  II - Crediti (entro 12 mesi): € X,XXX
  III - Attività finanziarie: € X,XXX
  IV - Disponibilità liquide: € X,XXX
  TOTALE ATTIVO CIRCOLANTE (C): € X,XXX

D) RATEI E RISCONTI: € X,XXX

TOTALE ATTIVO: € X,XXX


STATO PATRIMONIALE - PASSIVO

A) PATRIMONIO NETTO
  I - Capitale sociale: € X,XXX
  IV - Riserva legale: € X,XXX
  VII - Altre riserve: € X,XXX
  VIII - Utili (perdite) portati a nuovo: € X,XXX
  IX - Utile (perdita) dell'esercizio: € X,XXX
  TOTALE PATRIMONIO NETTO (A): € X,XXX

B) FONDI PER RISCHI E ONERI: € X,XXX
C) TRATTAMENTO FINE RAPPORTO: € X,XXX
D) DEBITI (entro 12 mesi): € X,XXX
E) RATEI E RISCONTI: € X,XXX

TOTALE PASSIVO: € X,XXX


CONTO ECONOMICO

A) VALORE DELLA PRODUZIONE
   1) Ricavi delle vendite: € X,XXX
   5) Altri ricavi: € X,XXX
   TOTALE (A): € X,XXX

B) COSTI DELLA PRODUZIONE
   6) Materie prime: € X,XXX
   7) Servizi: € X,XXX
   9) Personale: € X,XXX
   10) Ammortamenti: € X,XXX
   14) Oneri diversi: € X,XXX
   TOTALE (B): € X,XXX

DIFFERENZA (A-B): € X,XXX

C) PROVENTI E ONERI FINANZIARI: € X,XXX
D) RETTIFICHE DI VALORE: € X,XXX

RISULTATO PRIMA DELLE IMPOSTE: € X,XXX
20) Imposte: € X,XXX

UTILE (PERDITA) DELL'ESERCIZIO: € X,XXX


NOTA INTEGRATIVA

[Paragraphs from nota_integrativa]

RULES:
- Plain text, NO markdown
- € before amounts
- Comma separator (€ 10,000)
- Negatives: € (X,XXX)
- 2-space indent
- Skip zeros
- "entro 12 mesi" for short-term"""
        }]
    )

    balance_sheet = response.content[0].text.strip()
    print(f"  ✓ Formatted ({response.usage.input_tokens}→{response.usage.output_tokens} tokens)")

    return balance_sheet


def _cleanup_formatting(text: str) -> str:
    """Remove markdown artifacts."""
    text = re.sub(r'```[a-z]*\n?', '', text, flags=re.IGNORECASE)

    for char in ['**', '*', '|', '###', '##', '#']:
        text = text.replace(char, '')

    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def generate_balance_sheet(filepaths: List[str], api_key: Optional[str] = None) -> str:
    """Multi-agent system for generating Italian balance sheets."""
    print("\n" + "=" * 70)
    print("MULTI-AGENT BALANCE SHEET GENERATOR".center(70))
    print("=" * 70 + "\n")

    if len(filepaths) > 5:
        raise ValueError(f"Maximum 5 files allowed, got {len(filepaths)}")

    if api_key is None:
        api_key = get_api_key()

    client = anthropic.Anthropic(api_key=api_key)

    pdf_documents = _load_documents(filepaths)

    print("\n📋 PHASE 1: Document Analysis")
    doc_summary = _analyze_documents(client, pdf_documents)

    print("\n📊 PHASE 2: Data Extraction")
    extracted_data = _extract_financial_data(client, pdf_documents, doc_summary)

    print("\n🔢 PHASE 3: Validation and Calculations")
    validated_data = _validate_and_calculate(client, extracted_data)

    print("\n📄 PHASE 4: Balance Sheet Formatting")
    balance_sheet = _format_balance_sheet(client, validated_data)

    balance_sheet = _cleanup_formatting(balance_sheet)

    print("\n✅ Balance sheet generation complete!")
    return balance_sheet


def create_pdf(text_content: str, output_filename: str = "bilancio.pdf"):
    """Create professional, realistic Italian balance sheet PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import datetime

    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm
    )

    story = []
    styles = getSampleStyleSheet()

    style_defs = {
        # Header styles
        'HeaderTitle': {
            'fontName': 'Helvetica-Bold',
            'fontSize': 16,
            'alignment': TA_CENTER,
            'spaceAfter': 6,
            'textColor': colors.HexColor('#1a237e'),
            'leading': 18
        },
        'HeaderSubtitle': {
            'fontName': 'Helvetica-Bold',
            'fontSize': 12,
            'alignment': TA_CENTER,
            'spaceAfter': 20,
            'textColor': colors.HexColor('#283593'),
            'leading': 14
        },
        'CompanyInfo': {
            'fontName': 'Helvetica',
            'fontSize': 10,
            'alignment': TA_CENTER,
            'spaceAfter': 15,
            'leading': 12
        },

        # Section headers
        'SectionMain': {
            'fontName': 'Helvetica-Bold',
            'fontSize': 12,
            'alignment': TA_LEFT,
            'spaceBefore': 20,
            'spaceAfter': 10,
            'textColor': colors.HexColor('#0d47a1'),
            'leftIndent': 0,
            'leading': 14
        },
        'SectionSub': {
            'fontName': 'Helvetica-Bold',
            'fontSize': 10,
            'alignment': TA_LEFT,
            'spaceBefore': 12,
            'spaceAfter': 6,
            'textColor': colors.black,
            'leftIndent': 5 * mm,
            'leading': 12
        },

        # Table styles
        'TableHeader': {
            'fontName': 'Helvetica-Bold',
            'fontSize': 9,
            'alignment': TA_LEFT,
            'textColor': colors.white,
            'leading': 10
        },
        'TableItem': {
            'fontName': 'Helvetica',
            'fontSize': 8,
            'alignment': TA_LEFT,
            'textColor': colors.black,
            'leftIndent': 2 * mm,
            'leading': 9
        },
        'TableAmount': {
            'fontName': 'Helvetica',
            'fontSize': 8,
            'alignment': TA_RIGHT,
            'textColor': colors.black,
            'leading': 9
        },
        'TableTotal': {
            'fontName': 'Helvetica-Bold',
            'fontSize': 9,
            'alignment': TA_RIGHT,
            'textColor': colors.black,
            'leading': 10
        },

        # Note styles
        'NoteSection': {
            'fontName': 'Helvetica-Bold',
            'fontSize': 10,
            'alignment': TA_LEFT,
            'spaceBefore': 15,
            'spaceAfter': 8,
            'textColor': colors.HexColor('#1565c0'),
            'leading': 12
        },
        'NoteText': {
            'fontName': 'Helvetica',
            'fontSize': 8,
            'alignment': TA_JUSTIFY,
            'spaceAfter': 4,
            'leftIndent': 5 * mm,
            'rightIndent': 5 * mm,
            'leading': 10
        },

        # Footer styles
        'Footer': {
            'fontName': 'Helvetica-Oblique',
            'fontSize': 7,
            'alignment': TA_CENTER,
            'textColor': colors.gray,
            'spaceBefore': 20,
            'leading': 9
        }
    }

    # Add styles to stylesheet
    for name, props in style_defs.items():
        styles.add(ParagraphStyle(name=name, parent=styles['Normal'], **props))

    def add_header_section():
        """Add professional header with company info and dates."""
        today = datetime.datetime.now().strftime("%d/%m/%Y")

        # Main title
        story.append(Paragraph("BILANCIO D'ESERCIZIO", styles['HeaderTitle']))
        story.append(Paragraph("STATO PATRIMONIALE E CONTO ECONOMICO", styles['HeaderSubtitle']))

        # Company info block
        company_info = []
        lines = text_content.split('\n')
        for line in lines[:10]:  # Look for company name in first 10 lines
            if any(keyword in line.upper() for keyword in ['S.R.L.', 'S.P.A.', 'S.R.L', 'S.P.A', 'SRL', 'SPA']):
                company_info.append(line.strip())
                break
            if line.strip() and len(line.strip()) < 100 and not any(x in line for x in ['STATO', 'ATTIVO', 'AL']):
                company_info.append(line.strip())

        if company_info:
            story.append(Paragraph("<br/>".join(company_info[:2]), styles['CompanyInfo']))

        # Date info
        for line in lines[:15]:
            if 'AL' in line.upper() and any(x in line for x in ['31/12', '31/03', '30/06', '30/09']):
                story.append(Paragraph(line.strip(), styles['CompanyInfo']))
                break

        story.append(Spacer(1, 15 * mm))

    def parse_financial_data():
        """Parse the text content into structured data for tables."""
        sections = {
            'attivo': [],
            'passivo': [],
            'conto_economico': [],
            'note': []
        }

        current_section = None
        lines = text_content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section changes
            if 'STATO PATRIMONIALE - ATTIVO' in line.upper():
                current_section = 'attivo'
                continue
            elif 'STATO PATRIMONIALE - PASSIVO' in line.upper():
                current_section = 'passivo'
                continue
            elif 'CONTO ECONOMICO' in line.upper():
                current_section = 'conto_economico'
                continue
            elif 'NOTA INTEGRATIVA' in line.upper():
                current_section = 'note'
                continue

            if current_section and current_section != 'note':
                # Parse financial items (looking for € symbol or numbers)
                if '€' in line or any(x in line for x in [')', '-', 'I)', 'II)', 'III)']):
                    sections[current_section].append(line)
            elif current_section == 'note':
                sections['note'].append(line)

        return sections

    def create_financial_table(data, section_title):
        """Create a professional financial table."""
        if not data:
            return

        story.append(Paragraph(section_title, styles['SectionMain']))

        table_data = []
        header_row = ['Voce', 'Importo (€)']
        table_data.append(header_row)

        for line in data[:30]:  # Limit to first 30 items per section
            if '€' in line:
                # Split description and amount
                parts = line.split('€')
                if len(parts) >= 2:
                    description = parts[0].strip()
                    amount = '€ ' + parts[1].strip()

                    # Clean up description
                    description = description.replace('**', '').replace('*', '').strip()

                    table_data.append([description, amount])

        if len(table_data) > 1:
            table = Table(table_data, colWidths=[120 * mm, 40 * mm])
            table.setStyle(TableStyle([
                # Header style
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),

                # Table borders
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),

                # Total row highlighting
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e3f2fd')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),

                # Regular rows
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))

            story.append(table)
            story.append(Spacer(1, 10 * mm))

    def add_notes_section(notes_data):
        """Add the notes section with proper formatting."""
        if not notes_data:
            return

        story.append(PageBreak())
        story.append(Paragraph("NOTA INTEGRATIVA", styles['SectionMain']))

        current_subsection = None
        subsection_content = []

        for line in notes_data:
            line = line.strip()
            if not line:
                continue

            # Detect subsection headers (typically short, descriptive lines)
            if (len(line) < 100 and not line.startswith('-') and
                not any(x in line for x in ['€', ':', '•']) and
                line[0].isupper() if line else False):

                # Save previous subsection
                if current_subsection and subsection_content:
                    story.append(Paragraph(current_subsection, styles['NoteSection']))
                    for content_line in subsection_content:
                        if len(content_line.strip()) > 10:  # Meaningful content
                            story.append(Paragraph(content_line.strip(), styles['NoteText']))
                    subsection_content = []
                    story.append(Spacer(1, 5 * mm))

                current_subsection = line
            else:
                subsection_content.append(line)

        # Add final subsection
        if current_subsection and subsection_content:
            story.append(Paragraph(current_subsection, styles['NoteSection']))
            for content_line in subsection_content:
                if len(content_line.strip()) > 10:
                    story.append(Paragraph(content_line.strip(), styles['NoteText']))

    def add_footer():
        """Add professional footer."""
        story.append(Spacer(1, 15 * mm))
        footer_text = [
            "Il presente bilancio è stato redatto in conformità con i principi contabili nazionali (OIC).",
            "Documento generato automaticamente il " + datetime.datetime.now().strftime(
                "%d/%m/%Y") + " - Per approvazione."
        ]

        for text in footer_text:
            story.append(Paragraph(text, styles['Footer']))

    # Build the PDF
    try:
        # Add header
        add_header_section()

        # Parse and structure the data
        financial_data = parse_financial_data()

        # Add financial tables
        if financial_data['attivo']:
            create_financial_table(financial_data['attivo'], "STATO PATRIMONIALE - ATTIVO")

        if financial_data['passivo']:
            create_financial_table(financial_data['passivo'], "STATO PATRIMONIALE - PASSIVO")

        # Page break before conto economico
        story.append(PageBreak())

        if financial_data['conto_economico']:
            create_financial_table(financial_data['conto_economico'], "CONTO ECONOMICO")

        # Add notes section
        if financial_data['note']:
            add_notes_section(financial_data['note'])

        # Add footer
        add_footer()

        # Build the document
        doc.build(story)
        print(f"✓ Professional PDF created: {output_filename}")

    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        # Fallback: create simple PDF
        simple_story = [Paragraph(text_content.replace('\n', '<br/>'), styles['Normal'])]
        doc.build(simple_story)
        print("✓ Created simple PDF fallback")


def main():
    """Main execution."""
    INPUT_FILES = [
        'client_input/BILANCIO 31.12.2024.pdf',
    ]

    OUTPUT_PDF = 'bilancio_completo.pdf'

    try:
        print("\n🚀 Starting balance sheet generation...\n")

        balance_sheet_text = generate_balance_sheet(INPUT_FILES)

        with open('bilancio_output.txt', 'w', encoding='utf-8') as f:
            f.write(balance_sheet_text)
        print(f"\n💾 Text saved: bilancio_output.txt")

        print("\n" + "=" * 70)
        print("PREVIEW - FIRST 30 LINES".center(70))
        print("=" * 70)
        for line in balance_sheet_text.split('\n')[:30]:
            print(line)
        print("=" * 70 + "\n")

        print("📝 Generating PDF...\n")
        create_pdf(balance_sheet_text, OUTPUT_PDF)

        print("\n" + "=" * 70)
        print("✓ SUCCESS!".center(70))
        print("=" * 70)
        print(f"\n📄 Generated: {OUTPUT_PDF}")
        print(f"📄 Text backup: bilancio_output.txt\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()