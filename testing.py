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

    # Create document with realistic margins
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

    # Custom styles for Italian balance sheet
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

with open('outputs/11edc51a71365c0662435ef07ab62f39_bilancio.txt', 'r', encoding='utf-8') as f:
    text = f.read()

create_pdf(text, output_filename="bilancio.pdf")