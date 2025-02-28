from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64
import calendar
import logging
import pytz
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import zipfile

_logger = logging.getLogger(__name__)

class HrPayrollCertificateWizard(models.TransientModel):
    _name = 'hr.payroll.certificate.wizard'
    _description = 'Asistente de Certificados Laborales'

    # Campos Básicos
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Empleados',
        required=True
    )

    certificate_type = fields.Selection([
        ('income', 'Certificado de Ingresos y Retenciones'),
        ('labor', 'Certificado Laboral'),
        ('payroll', 'Certificado de Nómina'),
        ('provisions', 'Certificado de Provisiones'),
        ('vacation', 'Certificado de Vacaciones')
    ], string='Tipo de Certificado', required=True, default='labor')

    date_from = fields.Date(
        string='Fecha Inicial',
        required=True
    )

    date_to = fields.Date(
        string='Fecha Final',
        required=True
    )

    # Opciones de Formato
    include_header = fields.Boolean(
        string='Incluir Membrete',
        default=True
    )

    include_footer = fields.Boolean(
        string='Incluir Pie de Página',
        default=True
    )

    include_signature = fields.Boolean(
        string='Incluir Firma Digital',
        default=True
    )

    signature_employee_id = fields.Many2one(
        'hr.employee',
        string='Firmante',
        domain=[('certificate_authority', '=', True)]
    )

    # Opciones Adicionales
    include_salary = fields.Boolean(
        string='Incluir Salario',
        default=True
    )

    include_benefits = fields.Boolean(
        string='Incluir Beneficios',
        default=True
    )

    include_bank_info = fields.Boolean(
        string='Incluir Info. Bancaria',
        default=False
    )

    # Opciones de Generación
    format_type = fields.Selection([
        ('pdf', 'PDF'),
        ('docx', 'Word'),
        ('xlsx', 'Excel')
    ], string='Formato', required=True, default='pdf')

    generate_zip = fields.Boolean(
        string='Generar ZIP',
        default=True,
        help='Generar archivo ZIP cuando son múltiples certificados'
    )

    # Campos Técnicos
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )

    @api.onchange('certificate_type')
    def _onchange_certificate_type(self):
        """Actualiza fechas según tipo de certificado"""
        today = fields.Date.today()
        if self.certificate_type == 'income':
            # Para certificados de ingresos, usar año fiscal anterior
            prev_year = today.year - 1
            self.date_from = fields.Date.from_string(f'{prev_year}-01-01')
            self.date_to = fields.Date.from_string(f'{prev_year}-12-31')
        else:
            # Para otros certificados, usar mes actual
            self.date_from = today.replace(day=1)
            self.date_to = today.replace(
                day=calendar.monthrange(today.year, today.month)[1]
            )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validar fechas"""
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError(_('La fecha final debe ser mayor a la fecha inicial'))

    def action_generate_certificates(self):
        """Genera certificados según configuración"""
        self.ensure_one()

        try:
            # Validar configuración
            self._validate_configuration()

            # Generar certificados
            if len(self.employee_ids) > 1 and self.generate_zip:
                return self._generate_certificates_zip()
            else:
                return self._generate_single_certificate()

        except Exception as e:
            _logger.error("Error generando certificados: %s", str(e))
            raise ValidationError(_('Error generando certificados: %s') % str(e))

    def _validate_configuration(self):
        """Valida la configuración necesaria"""
        if self.include_signature and not self.signature_employee_id:
            raise ValidationError(_('Debe seleccionar un firmante para incluir firma'))

        if self.certificate_type == 'income':
            self._validate_income_certificate_config()

    def _validate_income_certificate_config(self):
        """Validación específica para certificados de ingresos"""
        # Verificar que existan nóminas en el período
        for employee in self.employee_ids:
            payslips = self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['done', 'paid']),
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to)
            ])
            if not payslips:
                raise ValidationError(_(
                    'No se encontraron nóminas procesadas para el empleado %s en el período seleccionado'
                ) % employee.name)

    def _generate_certificates_zip(self):
        """Genera archivo ZIP con múltiples certificados"""
        # Crear archivo ZIP en memoria
        zip_buffer = BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)

        # Generar certificados individuales
        for employee in self.employee_ids:
            certificate_content = self._generate_certificate_content(employee)
            filename = self._get_certificate_filename(employee)
            zip_file.writestr(filename, certificate_content)

        zip_file.close()

        # Crear adjunto
        zip_content = base64.b64encode(zip_buffer.getvalue())
        attachment = self.env['ir.attachment'].create({
            'name': f'Certificados_{self.certificate_type}_{fields.Date.today()}.zip',
            'type': 'binary',
            'datas': zip_content,
            'mimetype': 'application/zip',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _generate_single_certificate(self):
        """Genera certificado individual"""
        self.ensure_one()
        employee = self.employee_ids[0]

        certificate_content = self._generate_certificate_content(employee)
        filename = self._get_certificate_filename(employee)

        # Crear adjunto
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(certificate_content),
            'mimetype': self._get_mimetype(),
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _generate_certificate_content(self, employee):
        """Genera contenido del certificado según tipo"""
        method_name = f'_generate_{self.certificate_type}_certificate'
        if not hasattr(self, method_name):
            raise ValidationError(_('Tipo de certificado no implementado'))

        return getattr(self, method_name)(employee)

    def _generate_labor_certificate(self, employee):
        """Genera certificado laboral"""
        # Obtener datos del empleado
        contract = employee.contract_id
        if not contract:
            raise ValidationError(_('El empleado %s no tiene contrato activo') % employee.name)

        # Crear documento PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Agregar membrete si está configurado
        if self.include_header:
            elements.extend(self._add_header())

        # Contenido principal
        elements.append(Paragraph('CERTIFICA QUE:', styles['Heading1']))
        elements.append(Spacer(1, 12))

        # Información del empleado
        employee_info = [
            f"El/La señor(a) {employee.name}, identificado(a) con {employee.identification_type} "
            f"No. {employee.identification_id}, labora en nuestra compañía desde el "
            f"{contract.date_start.strftime('%d de %B de %Y')}",
            f"Cargo actual: {contract.job_id.name}",
            f"Tipo de contrato: {dict(contract._fields['contract_type'].selection).get(contract.contract_type)}"
        ]

        if self.include_salary:
            employee_info.append(
                f"Salario actual: {contract.wage:,.2f} pesos mensuales"
            )

        for info in employee_info:
            elements.append(Paragraph(info, styles['Normal']))
            elements.append(Spacer(1, 12))

        # Agregar firma si está configurado
        if self.include_signature:
            elements.extend(self._add_signature())

        # Agregar pie de página si está configurado
        if self.include_footer:
            elements.extend(self._add_footer())

        # Generar PDF
        doc.build(elements)
        return buffer.getvalue()

def _generate_income_certificate(self, employee):
    """Genera certificado de ingresos y retenciones"""
    # Crear documento PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Agregar membrete si está configurado
    if self.include_header:
        elements.extend(self._add_header())

    # Título del certificado
    elements.append(Paragraph(
        'CERTIFICADO DE INGRESOS Y RETENCIONES',
        styles['Heading1']
    ))
    elements.append(Spacer(1, 12))

    # Obtener nóminas del período
    payslips = self.env['hr.payslip'].search([
        ('employee_id', '=', employee.id),
        ('state', 'in', ['done', 'paid']),
        ('date_from', '>=', self.date_from),
        ('date_to', '<=', self.date_to)
    ])

    # Calcular totales
    totals = {
        'basic': 0,
        'extras': 0,
        'bonuses': 0,
        'commissions': 0,
        'other_income': 0,
        'health': 0,
        'pension': 0,
        'solidarity': 0,
        'retention': 0
    }

    for payslip in payslips:
        for line in payslip.line_ids:
            if line.category_id.code == 'BASIC':
                totals['basic'] += line.total
            elif line.category_id.code == 'EXTRA':
                totals['extras'] += line.total
            elif line.category_id.code == 'BON':
                totals['bonuses'] += line.total
            elif line.category_id.code == 'COM':
                totals['commissions'] += line.total
            elif line.category_id.code == 'ALW':
                totals['other_income'] += line.total
            elif line.code == 'HEALTH':
                totals['health'] += abs(line.total)
            elif line.code == 'PENSION':
                totals['pension'] += abs(line.total)
            elif line.code == 'SOLIDARITY':
                totals['solidarity'] += abs(line.total)
            elif line.code == 'RETENTION':
                totals['retention'] += abs(line.total)

    # Información del empleado
    employee_data = [
        ['Nombre completo:', employee.name],
        ['Tipo de documento:', employee.identification_type],
        ['Número de documento:', employee.identification_id],
        ['Período certificado:', f"{self.date_from.strftime('%d/%m/%Y')} - {self.date_to.strftime('%d/%m/%Y')}"]
    ]

    table = Table(employee_data, colWidths=[200, 300])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Tabla de ingresos
    income_data = [
        ['CONCEPTO', 'VALOR'],
        ['Salario básico', f"${totals['basic']:,.2f}"],
        ['Horas extra y recargos', f"${totals['extras']:,.2f}"],
        ['Bonificaciones', f"${totals['bonuses']:,.2f}"],
        ['Comisiones', f"${totals['commissions']:,.2f}"],
        ['Otros ingresos', f"${totals['other_income']:,.2f}"],
        ['TOTAL INGRESOS', f"${sum(totals.values()):,.2f}"]
    ]

    table = Table(income_data, colWidths=[300, 200])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Tabla de deducciones
    deduction_data = [
        ['DEDUCCIONES', 'VALOR'],
        ['Aportes salud', f"${totals['health']:,.2f}"],
        ['Aportes pensión', f"${totals['pension']:,.2f}"],
        ['Fondo solidaridad', f"${totals['solidarity']:,.2f}"],
        ['Retención en la fuente', f"${totals['retention']:,.2f}"],
        ['TOTAL DEDUCCIONES', f"${sum([totals['health'], totals['pension'], totals['solidarity'], totals['retention']]):,.2f}"]
    ]

    table = Table(deduction_data, colWidths=[300, 200])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(table)

    # Agregar firma si está configurado
    if self.include_signature:
        elements.extend(self._add_signature())

    # Agregar pie de página si está configurado
    if self.include_footer:
        elements.extend(self._add_footer())

    # Generar PDF
    doc.build(elements)
    return buffer.getvalue()

def _generate_payroll_certificate(self, employee):
    """Genera certificado de nómina"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Agregar membrete
    if self.include_header:
        elements.extend(self._add_header())

    # Título
    elements.append(Paragraph(
        'CERTIFICADO DE NÓMINA',
        styles['Heading1']
    ))
    elements.append(Spacer(1, 12))

    # Obtener nóminas del período
    payslips = self.env['hr.payslip'].search([
        ('employee_id', '=', employee.id),
        ('state', 'in', ['done', 'paid']),
        ('date_from', '>=', self.date_from),
        ('date_to', '<=', self.date_to)
    ])

    # Información del empleado
    contract = employee.contract_id
    employee_data = [
        ['Empleado:', employee.name],
        ['Identificación:', employee.identification_id],
        ['Cargo:', contract.job_id.name],
        ['Tipo de contrato:', dict(contract._fields['contract_type'].selection).get(contract.contract_type)],
        ['Salario base:', f"${contract.wage:,.2f}"]
    ]

    table = Table(employee_data, colWidths=[200, 300])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Detalle de nóminas
    for payslip in payslips:
        elements.append(Paragraph(
            f"Período: {payslip.date_from.strftime('%d/%m/%Y')} - {payslip.date_to.strftime('%d/%m/%Y')}",
            styles['Heading2']
        ))
        elements.append(Spacer(1, 12))

        # Tabla de conceptos
        payslip_data = [['Concepto', 'Cantidad', 'Valor']]
        for line in payslip.line_ids:
            if line.total != 0:
                payslip_data.append([
                    line.name,
                    f"{line.quantity:.2f}" if line.quantity != 1 else "",
                    f"${line.total:,.2f}"
                ])

        table = Table(payslip_data, colWidths=[250, 100, 150])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

    # Agregar firma y pie de página
    if self.include_signature:
        elements.extend(self._add_signature())
    if self.include_footer:
        elements.extend(self._add_footer())

    # Generar PDF
    doc.build(elements)
    return buffer.getvalue()

def _generate_provisions_certificate(self, employee):
    """Genera certificado de provisiones"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Agregar membrete
    if self.include_header:
        elements.extend(self._add_header())

    # Título
    elements.append(Paragraph(
        'CERTIFICADO DE PROVISIONES SOCIALES',
        styles['Heading1']
    ))
    elements.append(Spacer(1, 12))

    # Información del empleado
    contract = employee.contract_id
    employee_data = [
        ['Empleado:', employee.name],
        ['Identificación:', employee.identification_id],
        ['Fecha ingreso:', contract.date_start.strftime('%d/%m/%Y')],
        ['Salario actual:', f"${contract.wage:,.2f}"]
    ]

    table = Table(employee_data, colWidths=[200, 300])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Calcular provisiones
    provisions = self.env['hr.provision'].search([
        ('employee_id', '=', employee.id),
        ('date', '>=', self.date_from),
        ('date', '<=', self.date_to)
    ])

    # Tabla de provisiones
    provision_data = [
        ['CONCEPTO', 'BASE', 'PROVISIÓN']
    ]

    totals = {
        'prima': 0,
        'cesantias': 0,
        'intereses': 0,
        'vacaciones': 0
    }

    for provision in provisions:
        for line in provision.line_ids:
            if line.type in totals:
                totals[line.type] += line.amount

    provision_data.extend([
        ['Prima de servicios', f"${totals['prima']:,.2f}", f"${totals['prima']/12:,.2f}"],
        ['Cesantías', f"${totals['cesantias']:,.2f}", f"${totals['cesantias']/12:,.2f}"],
        ['Intereses cesantías', f"${totals['cesantias']:,.2f}", f"${totals['cesantias']*0.12/12:,.2f}"],
        ['Vacaciones', f"${totals['vacaciones']:,.2f}", f"${totals['vacaciones']/12:,.2f}"]
    ])

    table = Table(provision_data, colWidths=[200, 150, 150])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(table)

    # Agregar firma y pie de página
    if self.include_signature:
        elements.extend(self._add_signature())
    if self.include_footer:
        elements.extend(self._add_footer())

    # Generar PDF
    doc.build(elements)
    return buffer.getvalue()

def _generate_vacation_certificate(self, employee):
    """Genera certificado de vacaciones"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Agregar membrete
    if self.include_header:
        elements.extend(self._add_header())

    # Título
    elements.append(Paragraph(
        'CERTIFICADO DE VACACIONES',
        styles['Heading1']
    ))
    elements.append(Spacer(1, 12))

    # Información del empleado
    contract = employee.contract_id
    employee_data = [
        ['Empleado:', employee.name],
        ['Identificación:', employee.identification_id],
        ['Fecha ingreso:', contract.date_start.strftime('%d/%m/%Y')],
        ['Días acumulados:', str(contract.vacation_days_accumulated)]
    ]

    table = Table(employee_data, colWidths=[200, 300])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Obtener registros de vacaciones
    vacations = self.env['hr.leave'].search([
        ('employee_id', '=', employee.id),
        ('holiday_status_id.code', '=', 'VAC'),
        ('state', '=', 'validate'),
        ('request_date_from', '>=', self.date_from),
        ('request_date_to', '<=', self.date_to)
    ])

    # Tabla de vacaciones tomadas
    if vacations:
        vacation_data = [
            ['PERÍODO', 'FECHA INICIO', 'FECHA FIN', 'DÍAS']
        ]

        for vacation in vacations:
            vacation_data.append([
                vacation.name,
                vacation.date_from.strftime('%d/%m/%Y'),
                vacation.date_to.strftime('%d/%m/%Y'),
                str(vacation.number_of_days)
            ])

        table = Table(vacation_data, colWidths=[200, 100, 100, 100])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

    # Resumen
    elements.append(Paragraph('RESUMEN DE VACACIONES:', styles['Heading2']))
    elements.append(Spacer(1, 12))

    summary_data = [
        ['Concepto', 'Días'],
        ['Días causados', str(contract.vacation_days_earned)],
        ['Días tomados', str(contract.vacation_days_taken)],
        ['Días pendientes', str(contract.vacation_days_remaining)]
    ]

    table = Table(summary_data, colWidths=[300, 200])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(table)

    # Agregar firma y pie de página
    if self.include_signature:
        elements.extend(self._add_signature())
    if self.include_footer:
        elements.extend(self._add_footer())

    # Generar PDF
    doc.build(elements)
    return buffer.getvalue()

    def _add_header(self):
        """Agrega membrete al documento"""
        elements = []
        styles = getSampleStyleSheet()

        # Logo de la compañía
        if self.company_id.logo:
            # Implementar agregado de logo
            pass

        # Información de la compañía
        company_info = [
            self.company_id.name,
            f"NIT: {self.company_id.vat}",
            self.company_id.street,
            f"{self.company_id.city}, {self.company_id.state_id.name}",
            self.company_id.phone
        ]

        for info in company_info:
            elements.append(Paragraph(info, styles['Normal']))

        elements.append(Spacer(1, 20))
        return elements

    def _add_signature(self):
        """Agrega firma al documento"""
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Spacer(1, 40))
        elements.append(Paragraph('_' * 30, styles['Normal']))
        elements.append(Paragraph(self.signature_employee_id.name, styles['Normal']))
        elements.append(Paragraph(self.signature_employee_id.job_id.name, styles['Normal']))

        return elements

    def _add_footer(self):
        """Agrega pie de página al documento"""
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"Generado el {fields.Datetime.now().strftime('%d de %B de %Y')}",
            styles['Normal']
        ))

        return elements

    def _get_certificate_filename(self, employee):
        """Genera nombre del archivo"""
        date_str = fields.Date.today().strftime('%Y%m%d')
        cert_type = dict(self._fields['certificate_type'].selection).get(self.certificate_type)
        extension = dict(self._fields['format_type'].selection).get(self.format_type)
        
        return f"{cert_type}_{employee.name}_{date_str}.{extension}".replace(' ', '_')

    def _get_mimetype(self):
        """Retorna el tipo MIME según formato"""
        mimetypes = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        return mimetypes.get(self.format_type, 'application/octet-stream')