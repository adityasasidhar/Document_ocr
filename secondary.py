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
from typing import List, Optional, Dict,Any
import json


def get_api_key() -> str:
    """Get API key from environment variable or file.

    Priority:
    1. ANTHROPIC_API_KEY environment variable
    2. anthropic_api_key.txt file

    Returns:
        str: The API key

    Raises:
        ValueError: If API key is not found in either location
    """
    # Try environment variable first
    with open('anthropic_api_key.txt', 'r') as f:
        api_key = f.read().strip()
    print("api key used")
    return api_key


from typing import List, Optional, Dict, Any
from pathlib import Path
import base64
import anthropic
import json
import re


def generate_balance_sheet(filepaths: List[str], api_key: Optional[str] = None) -> str:
    """
    Multi-agent system for generating Italian balance sheets with minimal token usage.
    Uses Claude Sonnet for complex extraction and Haiku for everything else.
    """
    print("\n" + "=" * 70)
    print("MULTI-AGENT BALANCE SHEET GENERATOR".center(70))
    print("=" * 70 + "\n")

    if len(filepaths) > 5:
        raise ValueError(f"Maximum 5 files allowed, got {len(filepaths)}")

    # Get API key
    if api_key is None:
        api_key = get_api_key()

    client = anthropic.Anthropic(api_key=api_key)

    # Step 1: Load and prepare documents with caching
    pdf_documents = _load_documents(filepaths)

    # Step 2: Quick document analysis (Haiku)
    print("\n📋 PHASE 1: Document Analysis")
    doc_summary = _analyze_documents(client, pdf_documents)

    # Step 3: Data extraction (Sonnet - one-shot with detailed prompt)
    print("\n📊 PHASE 2: Data Extraction")
    extracted_data = _extract_financial_data(client, pdf_documents, doc_summary)

    # Step 4: Validation and calculations (Haiku)
    print("\n🔢 PHASE 3: Validation and Calculations")
    validated_data = _validate_and_calculate(client, extracted_data)

    # Step 5: Format generation (Haiku)
    print("\n📄 PHASE 4: Balance Sheet Formatting")
    balance_sheet = _format_balance_sheet(client, validated_data)

    # Step 6: Final cleanup
    balance_sheet = _cleanup_formatting(balance_sheet)

    print("\n✅ Balance sheet generation complete!")
    return balance_sheet


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

        # Add cache control to the last document for reuse across phases
        if idx == len(filepaths) - 1:
            doc_dict["cache_control"] = {"type": "ephemeral"}

        pdf_documents.append(doc_dict)
        print(f"  ✓ Loaded ({len(pdf_data) / 1024:.2f} KB)")

    return pdf_documents


def _analyze_documents(client: anthropic.Anthropic,
                       pdf_documents: List[Dict]) -> Dict[str, Any]:
    """
    Phase 1: Quick document analysis using Haiku.
    Identify what's in the documents without extracting all data.
    """
    print("  🤖 Using Claude Haiku...")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1500,
        temperature=0,
        messages=[{
            "role": "user",
            "content": pdf_documents + [{
                "type": "text",
                "text": """Quickly analyze these financial documents and provide a concise summary.

Return ONLY a JSON object (no markdown):
{
    "company_name": "exact company name",
    "balance_sheet_date": "DD/MM/YYYY",
    "fiscal_year": "YYYY",
    "document_pages": 10,
    "contains_stato_patrimoniale": true/false,
    "contains_conto_economico": true/false,
    "contains_nota_integrativa": true/false,
    "currency": "EUR",
    "document_quality": "clear|partial|poor"
}

Be concise and accurate.""",
                "cache_control": {"type": "ephemeral"}
            }]
        }]
    )

    summary_text = response.content[0].text.strip()
    print(f"  ✓ Analysis complete ({response.usage.input_tokens}→{response.usage.output_tokens} tokens)")

    # Extract JSON
    try:
        # Remove markdown if present
        summary_text = re.sub(r'```json\s*|\s*```', '', summary_text)
        doc_summary = json.loads(summary_text)
    except:
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', summary_text, re.DOTALL)
        doc_summary = json.loads(json_match.group(0)) if json_match else {}

    return doc_summary


def _extract_financial_data(client: anthropic.Anthropic,
                            pdf_documents: List[Dict],
                            doc_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 2: Comprehensive data extraction using Sonnet.
    One-shot extraction with detailed prompt engineering instead of thinking.
    """
    print("  🤖 Using Claude Sonnet...")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=7000,
        temperature=0,
        messages=[{
            "role": "user",
            "content": pdf_documents + [{
                "type": "text",
                "text": f"""You are an expert Italian accountant. Extract ALL financial data from these documents.

Document info: {json.dumps(doc_summary, indent=2)}

CRITICAL INSTRUCTIONS:
1. Find EVERY line item with its exact value
2. Preserve all hierarchical relationships
3. Note which values are subtotals vs individual items
4. Mark negative values clearly
5. Extract exact wording for line items

Return ONLY a JSON object (no markdown, no explanations):

{{
    "metadata": {{
        "company_name": "",
        "balance_sheet_date": "",
        "fiscal_year": ""
    }},
    "stato_patrimoniale_attivo": {{
        "A_crediti_soci": {{
            "value": 0,
            "details": {{}}
        }},
        "B_immobilizzazioni": {{
            "I_immateriali": {{
                "items": {{}},
                "totale": 0
            }},
            "II_materiali": {{
                "costo_storico": 0,
                "fondo_ammortamento": 0,
                "valore_netto": 0,
                "items": {{}}
            }},
            "III_finanziarie": {{
                "items": {{}},
                "totale": 0
            }},
            "totale_immobilizzazioni": 0
        }},
        "C_attivo_circolante": {{
            "I_rimanenze": {{
                "items": {{}},
                "totale": 0
            }},
            "II_crediti": {{
                "entro_12_mesi": {{}},
                "oltre_12_mesi": {{}},
                "totale": 0
            }},
            "III_attivita_finanziarie": {{
                "items": {{}},
                "totale": 0
            }},
            "IV_disponibilita_liquide": {{
                "items": {{}},
                "totale": 0
            }},
            "totale_attivo_circolante": 0
        }},
        "D_ratei_risconti": {{
            "items": {{}},
            "totale": 0
        }},
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
        "B_fondi_rischi_oneri": {{
            "items": {{}},
            "totale": 0
        }},
        "C_trattamento_fine_rapporto": 0,
        "D_debiti": {{
            "entro_12_mesi": {{}},
            "oltre_12_mesi": {{}},
            "totale": 0
        }},
        "E_ratei_risconti": {{
            "items": {{}},
            "totale": 0
        }},
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
        "20_imposte_reddito": {{
            "correnti": 0,
            "differite": 0,
            "anticipate": 0,
            "totale": 0
        }},
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

EXTRACTION RULES:
- Use exact numbers from documents (don't calculate yet)
- Keep all decimal places
- Negative values as negative numbers (not in parentheses yet)
- Empty dict {{}} if no data available for a section
- Be thorough - extract EVERYTHING visible"""
            }]
        }]
    )

    data_text = response.content[0].text.strip()
    print(f"  ✓ Data extracted ({response.usage.input_tokens}→{response.usage.output_tokens} tokens)")

    # Parse JSON with error handling
    try:
        data_text = re.sub(r'```json\s*|\s*```', '', data_text)
        extracted_data = json.loads(data_text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON parsing error: {e}")
        # Try to find and extract the JSON object
        json_match = re.search(r'\{.*\}', data_text, re.DOTALL)
        if json_match:
            extracted_data = json.loads(json_match.group(0))
        else:
            raise ValueError("Failed to extract valid JSON from response")

    return extracted_data


def _validate_and_calculate(client: anthropic.Anthropic,
                            extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 3: Validation and calculations using Haiku.
    Simple arithmetic - verify totals and balance.
    """
    print("  🤖 Using Claude Haiku...")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4000,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""Validate and correct this financial data. Perform all necessary calculations.

{json.dumps(extracted_data, indent=2, ensure_ascii=False)}

VALIDATION CHECKLIST:
1. Calculate all missing subtotals
2. Verify: TOTALE_ATTIVO = TOTALE_PASSIVO (must balance!)
3. Verify: Differenza A-B = Totale A - Totale B
4. Verify: Risultato prima imposte = Differenza A-B + Totale C + Totale D
5. Verify: Utile/Perdita = Risultato prima imposte - Imposte totale
6. Check patrimonio netto: sum of all components
7. Ensure all numeric values are present (no nulls)

Return ONLY JSON (no markdown):
{{
    "validation_status": "balanced" or "unbalanced",
    "balance_difference": 0,
    "corrections_made": ["list of corrections"],
    "corrected_data": {{...same structure as input...}}
}}

If unbalanced, try to identify and fix the issue. If you can't fix it, return data as-is but note the issue."""
        }]
    )

    result_text = response.content[0].text.strip()
    print(f"  ✓ Validated ({response.usage.input_tokens}→{response.usage.output_tokens} tokens)")

    # Parse validation result
    try:
        result_text = re.sub(r'```json\s*|\s*```', '', result_text)
        validation_result = json.loads(result_text)
    except:
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        validation_result = json.loads(json_match.group(0)) if json_match else {"corrected_data": extracted_data}

    # Report validation status
    if validation_result.get("validation_status") == "unbalanced":
        diff = validation_result.get("balance_difference", 0)
        print(f"  ⚠️ Warning: Balance difference of €{diff:,.2f}")
    else:
        print(f"  ✓ Balance sheet is balanced")

    if validation_result.get("corrections_made"):
        print(f"  📝 Made {len(validation_result['corrections_made'])} corrections")

    return validation_result.get("corrected_data", extracted_data)


def _format_balance_sheet(client: anthropic.Anthropic,
                          validated_data: Dict[str, Any]) -> str:
    """
    Phase 4: Format as Italian balance sheet using Haiku.
    Template-based formatting with specific Italian accounting standards.
    """
    print("  🤖 Using Claude Haiku...")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=5000,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""Format this validated data as a complete Italian balance sheet in PLAIN TEXT.

{json.dumps(validated_data, indent=2, ensure_ascii=False)}

FORMATTING REQUIREMENTS:

BILANCIO D'ESERCIZIO AL [date]
[Company Name]

STATO PATRIMONIALE - ATTIVO

A) CREDITI VERSO SOCI
   [details if any]
   Totale: € X,XXX.XX

B) IMMOBILIZZAZIONI
  I - Immobilizzazioni immateriali
      [list each item]
      Totale: € X,XXX.XX

  II - Immobilizzazioni materiali
      Costo storico: € X,XXX.XX
      Fondo ammortamento: € (X,XXX.XX)
      Valore netto: € X,XXX.XX

  III - Immobilizzazioni finanziarie
      [list items]
      Totale: € X,XXX.XX

  TOTALE IMMOBILIZZAZIONI (B): € X,XXX.XX

C) ATTIVO CIRCOLANTE
  I - Rimanenze: € X,XXX.XX

  II - Crediti (entro 12 mesi)
      [list each type]
      Totale: € X,XXX.XX

  III - Attività finanziarie che non costituiscono immobilizzazioni: € X,XXX.XX

  IV - Disponibilità liquide
      [list items]
      Totale: € X,XXX.XX

  TOTALE ATTIVO CIRCOLANTE (C): € X,XXX.XX

D) RATEI E RISCONTI ATTIVI: € X,XXX.XX

TOTALE ATTIVO: € X,XXX.XX


STATO PATRIMONIALE - PASSIVO

A) PATRIMONIO NETTO
  I - Capitale sociale: € X,XXX.XX
  II - Riserva da sovrapprezzo azioni: € X,XXX.XX
  III - Riserve di rivalutazione: € X,XXX.XX
  IV - Riserva legale: € X,XXX.XX
  V - Riserve statutarie: € X,XXX.XX
  VII - Altre riserve: € X,XXX.XX
  VIII - Utili (perdite) portati a nuovo: € X,XXX.XX
  IX - Utile (perdita) dell'esercizio: € X,XXX.XX
  TOTALE PATRIMONIO NETTO (A): € X,XXX.XX

B) FONDI PER RISCHI E ONERI: € X,XXX.XX

C) TRATTAMENTO DI FINE RAPPORTO DI LAVORO SUBORDINATO: € X,XXX.XX

D) DEBITI (entro 12 mesi)
   [list each type]
   Totale: € X,XXX.XX

E) RATEI E RISCONTI PASSIVI: € X,XXX.XX

TOTALE PASSIVO: € X,XXX.XX


CONTO ECONOMICO

A) VALORE DELLA PRODUZIONE
   1) Ricavi delle vendite e delle prestazioni: € X,XXX.XX
   2) Variazione rimanenze prodotti: € X,XXX.XX
   5) Altri ricavi e proventi: € X,XXX.XX
   TOTALE VALORE DELLA PRODUZIONE (A): € X,XXX.XX

B) COSTI DELLA PRODUZIONE
   6) Materie prime, sussidiarie e merci: € X,XXX.XX
   7) Servizi: € X,XXX.XX
   8) Godimento beni di terzi: € X,XXX.XX
   9) Personale: € X,XXX.XX
   10) Ammortamenti e svalutazioni: € X,XXX.XX
   14) Oneri diversi di gestione: € X,XXX.XX
   TOTALE COSTI DELLA PRODUZIONE (B): € X,XXX.XX

DIFFERENZA TRA VALORE E COSTI DELLA PRODUZIONE (A-B): € X,XXX.XX

C) PROVENTI E ONERI FINANZIARI
   16) Altri proventi finanziari: € X,XXX.XX
   17) Interessi e altri oneri finanziari: € (X,XXX.XX)
   TOTALE PROVENTI E ONERI FINANZIARI (C): € X,XXX.XX

D) RETTIFICHE DI VALORE DI ATTIVITÀ FINANZIARIE
   19) Svalutazioni: € (X,XXX.XX)
   TOTALE RETTIFICHE (D): € X,XXX.XX

RISULTATO PRIMA DELLE IMPOSTE: € X,XXX.XX

20) Imposte sul reddito dell'esercizio: € X,XXX.XX

UTILE (PERDITA) DELL'ESERCIZIO: € X,XXX.XX


NOTA INTEGRATIVA

[Format as flowing paragraphs with proper Italian accounting terminology]

RULES:
- Plain text only, NO markdown, NO asterisks, NO pipes
- € symbol before all amounts
- Thousand separator: comma (€ 10,000.00)
- Decimal separator: period
- Negative amounts: € (X,XXX.XX) in parentheses
- Proper indentation: 2 spaces per level
- "entro 12 mesi" for short-term items where applicable
- Skip zero-value sections unless structurally important
- Nota integrativa in paragraph format, not lists"""
        }]
    )

    balance_sheet = response.content[0].text.strip()
    print(f"  ✓ Formatted ({response.usage.input_tokens}→{response.usage.output_tokens} tokens)")

    return balance_sheet


def _cleanup_formatting(text: str) -> str:
    """Remove any remaining markdown or formatting artifacts."""
    # Remove markdown code blocks
    text = re.sub(r'```[a-z]*\n?', '', text)

    # Remove markdown formatting
    for char in ['**', '*', '|', '###', '##', '#']:
        text = text.replace(char, '')

    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# Optional: Add comprehensive token tracking
class TokenTracker:
    """Track token usage across all API calls."""

    def __init__(self):
        self.calls = []
        self.total_input = 0
        self.total_output = 0
        self.total_cost = 0

    def add_call(self, phase: str, model: str, input_tokens: int, output_tokens: int):
        # Approximate costs (as of 2025)
        costs = {
            "claude-haiku-4-5": {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
            "claude-sonnet-4-5": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000}
        }

        cost = (input_tokens * costs[model]["input"] +
                output_tokens * costs[model]["output"])

        self.calls.append({
            "phase": phase,
            "model": model,
            "input": input_tokens,
            "output": output_tokens,
            "cost": cost
        })

        self.total_input += input_tokens
        self.total_output += output_tokens
        self.total_cost += cost

    def print_summary(self):
        print("\n" + "=" * 70)
        print("TOKEN USAGE SUMMARY".center(70))
        print("=" * 70)
        for call in self.calls:
            print(f"{call['phase']:20} | {call['model']:20} | "
                  f"{call['input']:>7} → {call['output']:>7} | ${call['cost']:.4f}")
        print("-" * 70)
        print(f"{'TOTAL':20} | {''  :20} | "
              f"{self.total_input:>7} → {self.total_output:>7} | ${self.total_cost:.4f}")
        print("=" * 70 + "\n")

def create_pdf(text_content: str, output_filename: str = "bilancio.pdf"):
    """Create professional PDF from balance sheet text"""

    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm
    )

    story = []
    styles = getSampleStyleSheet()

    style_defs = {
        'BilanciTitle': {'fontName': 'Helvetica-Bold', 'fontSize': 13, 'alignment': TA_CENTER,
                         'spaceAfter': 3, 'leading': 16},
        'BilanciCompany': {'fontName': 'Helvetica-Bold', 'fontSize': 11, 'alignment': TA_CENTER,
                           'spaceAfter': 20, 'leading': 14},
        'BilanciMainSection': {'fontName': 'Helvetica-Bold', 'fontSize': 11, 'spaceAfter': 8,
                               'spaceBefore': 15, 'leading': 14},
        'BilanciSection': {'fontName': 'Helvetica-Bold', 'fontSize': 10, 'spaceAfter': 5,
                           'spaceBefore': 8, 'leading': 12},
        'BilanciSubSection': {'fontName': 'Helvetica-Bold', 'fontSize': 9, 'leftIndent': 5,
                              'spaceAfter': 3, 'leading': 11},
        'BilanciItem': {'fontSize': 9, 'leftIndent': 10, 'spaceAfter': 2, 'leading': 11},
        'BilanciSubItem': {'fontSize': 8, 'leftIndent': 20, 'spaceAfter': 1, 'leading': 10},
        'BilanciDetailItem': {'fontSize': 8, 'leftIndent': 30, 'spaceAfter': 1, 'leading': 10,
                              'textColor': colors.HexColor('#333333')},
        'BilanciTotal': {'fontName': 'Helvetica-Bold', 'fontSize': 9, 'leftIndent': 5,
                         'spaceAfter': 6, 'spaceBefore': 3, 'leading': 11},
        'BilanciGrandTotal': {'fontName': 'Helvetica-Bold', 'fontSize': 10, 'spaceAfter': 8,
                              'spaceBefore': 6, 'leading': 13},
        'BilanciNota': {'fontSize': 9, 'spaceAfter': 8, 'spaceBefore': 3, 'leading': 12,
                        'alignment': TA_LEFT}
    }

    for name, props in style_defs.items():
        styles.add(ParagraphStyle(name=name, parent=styles['Normal'], **props))

    lines = text_content.split('\n')

    for i, original_line in enumerate(lines):
        line = original_line.strip()
        if not line:
            story.append(Spacer(1, 3))
            continue

        leading_spaces = len(original_line) - len(original_line.lstrip())

        if 'BILANCIO' in line and 'ESERCIZIO' in line:
            style = 'BilanciTitle'
        elif i < 5 and line.isupper() and len(line) < 50 and not any(
                x in line for x in ['STATO', 'ATTIVO', 'PASSIVO', 'CONTO', 'NOTA']):
            style = 'BilanciCompany'
        elif any(line.startswith(x) for x in ['STATO PATRIMONIALE', 'CONTO ECONOMICO', 'NOTA INTEGRATIVA']):
            story.append(Spacer(1, 8))
            style = 'BilanciMainSection'
        elif line.strip() in ['A)', 'B)', 'C)', 'D)', 'E)'] or any(
                line.startswith(x) for x in ['A) ', 'B) ', 'C) ', 'D) ', 'E) ']):
            style = 'BilanciSection'
        elif any(line.strip().startswith(x) for x in
                 ['I -', 'II -', 'III -', 'IV -', 'V -', 'VI -', 'VII -', 'VIII -', 'IX -', 'X -', 'I.', 'II.', 'III.',
                  'IV.', 'V.', 'VI.', 'VII.', 'VIII.', 'IX.', 'X.']):
            style = 'BilanciSubSection'
        elif any(line.startswith(f'{n}.') for n in range(1, 25)):
            style = 'BilanciTotal' if 'TOTALE' in line.upper() or 'Totale' in line else 'BilanciSubSection'
        elif 'TOTALE' in line.upper() and ':' in line:
            style = 'BilanciGrandTotal' if any(x in line.upper() for x in
                                               ['ATTIVO', 'PASSIVO', 'PATRIMONIO', 'IMMOBILIZZAZIONI', 'CIRCOLANTE',
                                                'DEBITI', 'PRODUZIONE']) else 'BilanciTotal'
        elif 'Totale' in line and ':' in line:
            style = 'BilanciTotal'
        elif 'DIFFERENZA' in line or 'RISULTATO' in line:
            style = 'BilanciGrandTotal'
        elif line.startswith('-'):
            style = 'BilanciDetailItem' if leading_spaces >= 15 else (
                'BilanciSubItem' if leading_spaces >= 8 else 'BilanciItem')
        elif i > 100 and not line[0].isupper() and not line[0].isdigit():
            style = 'BilanciNota'
        else:
            style = 'BilanciDetailItem' if leading_spaces >= 20 else (
                'BilanciSubItem' if leading_spaces >= 10 else ('BilanciItem' if leading_spaces >= 5 else 'BilanciNota'))

        story.append(Paragraph(line, styles[style]))

    doc.build(story)
    print(f"✓ PDF created: {output_filename}")


def main():
    """Main execution"""

    INPUT_FILES = [
        'client_input/BILANCIO 31.12.2024.pdf',
        # 'client_input/file2.pdf',
        # 'client_input/file3.pdf',
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
