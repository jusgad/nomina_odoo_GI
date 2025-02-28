from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import base64
import hashlib
import json
import logging
import requests
import uuid
import xml.etree.ElementTree as ET
from lxml import etree

_logger = logging.getLogger(__name__)


class HrElectronicPayroll(models.Model):
    _name = 'hr.electronic.payroll'
    _description = 'Nómina Electrónica DIAN'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    
    name = fields.Char(string='Número', readonly=True, copy=False)
    
    # Campos de relación
    payslip_id = fields.Many2one(
        'hr.payslip', string='Nómina',
        required=True, ondelete='restrict',
        readonly=True, states={'draft': [('readonly', False)]})
    
    employee_id = fields.Many2one(
        'hr.employee', string='Empleado',
        required=True, ondelete='restrict',
        readonly=True, states={'draft': [('readonly', False)]})
    
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        required=True, default=lambda self: self.env.company,
        readonly=True, states={'draft': [('readonly', False)]})
    
    # Campos de fechas
    date = fields.Date(
        string='Fecha', required=True,
        default=fields.Date.context_today,
        readonly=True, states={'draft': [('readonly', False)]})
    
    period_start = fields.Date(
        string='Inicio del Periodo',
        readonly=True, states={'draft': [('readonly', False)]})
    
    period_end = fields.Date(
        string='Fin del Periodo',
        readonly=True, states={'draft': [('readonly', False)]})
    
    # Campos de estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('sent', 'Enviado'),
        ('accepted', 'Aceptado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True, copy=False)
    
    # Campos para DIAN
    dian_resolution_number = fields.Char(
        string='Número de Resolución DIAN',
        readonly=True, states={'draft': [('readonly', False)]})
    
    dian_resolution_date = fields.Date(
        string='Fecha de Resolución DIAN',
        readonly=True, states={'draft': [('readonly', False)]})
    
    dian_prefix = fields.Char(
        string='Prefijo DIAN',
        readonly=True, states={'draft': [('readonly', False)]})
    
    dian_number = fields.Char(
        string='Número DIAN', copy=False,
        readonly=True)
    
    dian_operation_type = fields.Selection([
        ('10', 'Estándar'),
        ('20', 'Nota de Ajuste'),
        ('30', 'Eliminación'),
    ], string='Tipo de Operación', default='10',
       readonly=True, states={'draft': [('readonly', False)]})
    
    dian_environment = fields.Selection([
        ('1', 'Producción'),
        ('2', 'Pruebas'),
    ], string='Ambiente DIAN', default='2',
       readonly=True, states={'draft': [('readonly', False)]})
    
    # Campos para XML
    xml_filename = fields.Char(
        string='Nombre del Archivo XML', copy=False,
        readonly=True)
    
    xml_file = fields.Binary(
        string='Archivo XML', copy=False,
        readonly=True)
    
    xml_signed_filename = fields.Char(
        string='Nombre del Archivo XML Firmado', copy=False,
        readonly=True)
    
    xml_signed_file = fields.Binary(
        string='Archivo XML Firmado', copy=False,
        readonly=True)
    
    # Campos para respuesta DIAN
    dian_response_filename = fields.Char(
        string='Nombre del Archivo de Respuesta', copy=False,
        readonly=True)
    
    dian_response_file = fields.Binary(
        string='Archivo de Respuesta', copy=False,
        readonly=True)
    
    dian_response_code = fields.Char(
        string='Código de Respuesta DIAN', copy=False,
        readonly=True)
    
    dian_response_description = fields.Text(
        string='Descripción de Respuesta DIAN', copy=False,
        readonly=True)
    
    dian_transaction_id = fields.Char(
        string='ID de Transacción DIAN', copy=False,
        readonly=True)
    
    dian_cude = fields.Char(
        string='CUDE', copy=False,
        help='Código Único de Documento Electrónico',
        readonly=True)
    
    # Campos para PDF
    pdf_filename = fields.Char(
        string='Nombre del Archivo PDF', copy=False,
        readonly=True)
    
    pdf_file = fields.Binary(
        string='Archivo PDF', copy=False,
        readonly=True)
    
    # Campos para registro de eventos
    log_ids = fields.One2many(
        'hr.electronic.payroll.log', 'electronic_payroll_id',
        string='Registro de Eventos')
    
    # Campos para notas de ajuste
    is_adjustment_note = fields.Boolean(
        string='Es Nota de Ajuste', default=False,
        readonly=True, states={'draft': [('readonly', False)]})
    
    original_electronic_payroll_id = fields.Many2one(
        'hr.electronic.payroll', string='Documento Original',
        domain="[('state', '=', 'accepted'), ('id', '!=', id)]",
        readonly=True, states={'draft': [('readonly', False)]})
    
    adjustment_reason = fields.Text(
        string='Motivo del Ajuste',
        readonly=True, states={'draft': [('readonly', False)]})
    
    # Campos para información técnica
    uuid = fields.Char(
        string='UUID', copy=False,
        default=lambda self: str(uuid.uuid4()),
        readonly=True)
    
    software_id = fields.Char(
        string='ID del Software', copy=False,
        readonly=True, states={'draft': [('readonly', False)]})
    
    software_security_code = fields.Char(
        string='Código de Seguridad del Software', copy=False,
        readonly=True, states={'draft': [('readonly', False)]})
    
    technical_key = fields.Char(
        string='Clave Técnica', copy=False,
        readonly=True, states={'draft': [('readonly', False)]})
    
    # Campos para certificado digital
    certificate_id = fields.Many2one(
        'hr.electronic.certificate', string='Certificado Digital',
        domain="[('state', '=', 'valid'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        readonly=True, states={'draft': [('readonly', False)]})
    
    # Campos para información del empleado
    employee_identification_type = fields.Selection(
        related='employee_id.identification_type',
        string='Tipo de Identificación')
    
    employee_identification = fields.Char(
        related='employee_id.identification_id',
        string='Número de Identificación')
    
    employee_first_name = fields.Char(
        related='employee_id.first_name',
        string='Primer Nombre')
    
    employee_second_name = fields.Char(
        related='employee_id.second_name',
        string='Segundo Nombre')
    
    employee_first_surname = fields.Char(
        related='employee_id.first_surname',
        string='Primer Apellido')
    
    employee_second_surname = fields.Char(
        related='employee_id.second_surname',
        string='Segundo Apellido')
    
    # Campos para información de la nómina
    payslip_number = fields.Char(
        related='payslip_id.number',
        string='Número de Nómina')
    
    payslip_date = fields.Date(
        related='payslip_id.date_to',
        string='Fecha de Nómina')
    
    payslip_contract_id = fields.Many2one(
        related='payslip_id.contract_id',
        string='Contrato')
    
    payslip_wage = fields.Monetary(
        related='payslip_id.contract_id.wage',
        string='Salario')
    
    payslip_worked_days = fields.Integer(
        related='payslip_id.worked_days',
        string='Días Trabajados')
    
    payslip_net = fields.Monetary(
        related='payslip_id.net',
        string='Neto a Pagar')
    
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Moneda')
    
    # Campos para información adicional
    notes = fields.Text(
        string='Notas',
        readonly=True, states={'draft': [('readonly', False)]})
    
    # Campos computados
    dian_status = fields.Char(
        string='Estado DIAN', compute='_compute_dian_status',
        store=True)
    
    can_be_sent = fields.Boolean(
        string='Puede Enviarse', compute='_compute_can_be_sent',
        store=True)
    
    # Secuencia
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = vals.get('date', fields.Date.context_today(self))
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'hr.electronic.payroll', sequence_date=seq_date) or _('New')
        return super(HrElectronicPayroll, self).create(vals)
    
    # Métodos computados
    @api.depends('state', 'dian_response_code')
    def _compute_dian_status(self):
        for record in self:
            if record.state == 'draft':
                record.dian_status = _('Borrador')
            elif record.state == 'generated':
                record.dian_status = _('Generado')
            elif record.state == 'sent':
                record.dian_status = _('Enviado a DIAN')
            elif record.state == 'accepted':
                record.dian_status = _('Aceptado por DIAN')
            elif record.state == 'rejected':
                if record.dian_response_code:
                    record.dian_status = _('Rechazado: %s') % record.dian_response_code
                else:
                    record.dian_status = _('Rechazado por DIAN')
            elif record.state == 'cancelled':
                record.dian_status = _('Cancelado')
            else:
                record.dian_status = _('Desconocido')
    
    @api.depends('state', 'xml_signed_file')
    def _compute_can_be_sent(self):
        for record in self:
            record.can_be_sent = record.state in ['generated'] and bool(record.xml_signed_file)
    
    # Restricciones
    @api.constrains('is_adjustment_note', 'original_electronic_payroll_id', 'adjustment_reason')
    def _check_adjustment_note(self):
        for record in self:
            if record.is_adjustment_note:
                if not record.original_electronic_payroll_id:
                    raise ValidationError(_('Para una nota de ajuste, debe seleccionar el documento original.'))
                if not record.adjustment_reason:
                    raise ValidationError(_('Para una nota de ajuste, debe especificar el motivo del ajuste.'))
    
    # Métodos onchange
    @api.onchange('payslip_id')
    def _onchange_payslip(self):
        if self.payslip_id:
            self.employee_id = self.payslip_id.employee_id
            self.period_start = self.payslip_id.date_from
            self.period_end = self.payslip_id.date_to
    
    @api.onchange('is_adjustment_note')
    def _onchange_is_adjustment_note(self):
        if self.is_adjustment_note:
            self.dian_operation_type = '20'
        else:
            self.dian_operation_type = '10'
            self.original_electronic_payroll_id = False
            self.adjustment_reason = False
    
    # Métodos de acción
    def action_generate(self):
        """
        Genera el XML de nómina electrónica
        """
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_("Solo se puede generar documentos en estado borrador."))
        
        # Validar datos requeridos
        self._validate_required_data()
        
        # Generar número DIAN
        if not self.dian_number:
            self.dian_number = self._get_next_dian_number()
        
        # Generar XML
        xml_content = self._generate_xml()
        
        # Guardar XML
        filename = f"NE_{self.company_id.vat}_{self.dian_number}.xml"
        self.write({
            'xml_filename': filename,
            'xml_file': base64.b64encode(xml_content.encode()),
            'state': 'generated',
        })
        
        # Firmar XML
        self.action_sign()
        
        # Registrar evento
        self._create_log('generate', _('Documento generado'))
        
        return True
    
    def action_sign(self):
        """
        Firma el XML con el certificado digital
        """
        self.ensure_one()
        
        if not self.xml_file:
            raise UserError(_("No hay XML para firmar."))
        
        if not self.certificate_id:
            raise UserError(_("Debe seleccionar un certificado digital."))
        
        # Decodificar XML
        xml_content = base64.b64decode(self.xml_file).decode()
        
        # Firmar XML
        signed_xml = self._sign_xml(xml_content)
        
        # Guardar XML firmado
        filename = f"NE_{self.company_id.vat}_{self.dian_number}_signed.xml"
        self.write({
            'xml_signed_filename': filename,
            'xml_signed_file': base64.b64encode(signed_xml.encode()),
        })
        
        # Registrar evento
        self._create_log('sign', _('Documento firmado'))
        
        return True
    
    def action_send(self):
        """
        Envía el XML firmado a la DIAN
        """
        self.ensure_one()
        
        if not self.xml_signed_file:
            raise UserError(_("No hay XML firmado para enviar."))
        
        if self.state not in ['generated', 'rejected']:
            raise UserError(_("Solo se pueden enviar documentos generados o rechazados."))
        
        # Decodificar XML firmado
        xml_content = base64.b64decode(self.xml_signed_file).decode()
        
        # Enviar a DIAN
        response = self._send_to_dian(xml_content)
        
        # Procesar respuesta
        if response.get('is_valid'):
            state = 'accepted'
            message = _('Documento aceptado por DIAN')
        else:
            state = 'rejected'
            message = _('Documento rechazado por DIAN: %s') % response.get('error_message', '')
        
        # Guardar respuesta
        self.write({
            'state': state,
            'dian_response_code': response.get('status_code'),
            'dian_response_description': response.get('status_description'),
            'dian_transaction_id': response.get('transaction_id'),
            'dian_response_filename': f"NE_{self.company_id.vat}_{self.dian_number}_response.xml",
            'dian_response_file': base64.b64encode(response.get('response_xml', '').encode()),
        })
        
        # Si fue aceptado, generar PDF
        if state == 'accepted':
            self.action_generate_pdf()
        
        # Registrar evento
        self._create_log('send', message)
        
        return True
    
    def action_cancel(self):
        """
        Cancela el documento de nómina electrónica
        """
        self.ensure_one()
        
        if self.state == 'accepted':
            # Para documentos aceptados, se debe enviar una nota de eliminación a la DIAN
            return self._create_cancellation_note()
        
        if self.state in ['draft', 'generated', 'rejected']:
            # Para documentos no enviados o rechazados, se puede cancelar directamente
            self.write({
                'state': 'cancelled',
            })
            
            # Registrar evento
            self._create_log('cancel', _('Documento cancelado'))
            
            return True
        
        raise UserError(_("No se puede cancelar un documento en estado %s.") % self.state)
    
    def action_generate_pdf(self):
        """
        Genera el PDF de la nómina electrónica
        """
        self.ensure_one()
        
        if self.state not in ['accepted']:
            raise UserError(_("Solo se puede generar PDF para documentos aceptados."))
        
        # Generar PDF
        report = self.env.ref('nomina_colombia_v18.action_report_electronic_payroll')
        pdf_content, _ = report._render_qweb_pdf(self.id)
        
        # Guardar PDF
        filename = f"NE_{self.company_id.vat}_{self.dian_number}.pdf"
        self.write({
            'pdf_filename': filename,
            'pdf_file': base64.b64encode(pdf_content),
        })
        
        # Registrar evento
        self._create_log('pdf', _('PDF generado'))
        
        return True
    
    def action_send_email(self):
        """
        Envía el documento por correo electrónico al empleado
        """
        self.ensure_one()
        
        if not self.pdf_file:
            raise UserError(_("Debe generar primero el PDF."))
        
        if not self.employee_id.work_email:
            raise UserError(_("El empleado no tiene configurado un correo electrónico de trabajo."))
        
        # Enviar correo
        template = self.env.ref('nomina_colombia_v18.email_template_electronic_payroll')
        template.send_mail(self.id, force_send=True)
        
        # Registrar evento
        self._create_log('email', _('Documento enviado por correo electrónico'))
        
        return True
    
    def action_view_payslip(self):
        """
        Muestra la nómina relacionada
        """
        self.ensure_one()
        
        return {
            'name': _('Nómina'),
            'view_mode': 'form',
            'res_model': 'hr.payslip',
            'res_id': self.payslip_id.id,
            'type': 'ir.actions.act_window',
        }
    
    def action_download_xml(self):
        """
        Descarga el XML firmado
        """
        self.ensure_one()
        
        if not self.xml_signed_file:
            raise UserError(_("No hay XML firmado para descargar."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/hr.electronic.payroll/{self.id}/xml_signed_file/{self.xml_signed_filename}?download=true",
            'target': 'self',
        }
    
    def action_download_pdf(self):
        """
        Descarga el PDF
        """
        self.ensure_one()
        
        if not self.pdf_file:
            raise UserError(_("No hay PDF para descargar."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/hr.electronic.payroll/{self.id}/pdf_file/{self.pdf_filename}?download=true",
            'target': 'self',
        }
    
    def action_reset_to_draft(self):
        """
        Restablece el documento a estado borrador
        """
        self.ensure_one()
        
        if self.state in ['accepted']:
            raise UserError(_("No se puede restablecer un documento aceptado por la DIAN."))
        
        self.write({
            'state': 'draft',
            'xml_file': False,
            'xml_filename': False,
            'xml_signed_file': False,
            'xml_signed_filename': False,
            'dian_response_file': False,
            'dian_response_filename': False,
            'dian_response_code': False,
            'dian_response_description': False,
            'dian_transaction_id': False,
            'pdf_file': False,
            'pdf_filename': False,
        })
        
        # Registrar evento
        self._create_log('reset', _('Documento restablecido a borrador'))
        
        return True
    
    # Métodos auxiliares
    def _validate_required_data(self):
        """
        Valida que todos los datos requeridos estén presentes
        """
        self.ensure_one()
        
        # Validar datos de la compañía
        if not self.company_id.vat:
            raise UserError(_("La compañía no tiene configurado el NIT."))
        
        if not self.company_id.partner_id.dian_fiscal_responsibility_ids:
            raise UserError(_("La compañía no tiene configuradas las responsabilidades fiscales."))
        
        # Validar datos del empleado
        if not self.employee_id.identification_id:
            raise UserError(_("El empleado no tiene configurado el número de identificación."))
        
        if not self.employee_id.address_home_id:
            raise UserError(_("El empleado no tiene configurada la dirección particular."))
        
        # Validar datos técnicos
        if not self.software_id or not self.software_security_code:
            raise UserError(_("Debe configurar el ID del software y el código de seguridad."))
        
        # Validar datos de la nómina
        if not self.payslip_id.number:
            raise UserError(_("La nómina no tiene número asignado."))
        
        return True
    
    def _get_next_dian_number(self):
        """
        Obtiene el siguiente número para DIAN
        """
        self.ensure_one()
        
        # Obtener la secuencia para nómina electrónica
        sequence = self.env['ir.sequence'].search([
            ('code', '=', 'dian.electronic.payroll'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not sequence:
            raise UserError(_("No se encontró la secuencia para nómina electrónica."))
        
        # Obtener el siguiente número
        next_number = sequence.next_by_id()
        
        # Si hay prefijo, agregarlo
        if self.dian_prefix:
            next_number = f"{self.dian_prefix}{next_number}"
        
        return next_number
    
    def _generate_xml(self):
        """
        Genera el XML según el formato UBL 2.1 para nómina electrónica
        """
        self.ensure_one()
        
        # Crear el elemento raíz
        root = ET.Element("NominaIndividual", {
            "xmlns": "dian:gov:co:facturaelectronica:NominaIndividual",
            "xmlns:xs": "http://www.w3.org/2001/XMLSchema-instance",
            "xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
            "xmlns:ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "xmlns:xades": "http://uri.etsi.org/01903/v1.3.2#",
            "xmlns:xades141": "http://uri.etsi.org/01903/v1.4.1#",
            "SchemaLocation": "dian:gov:co:facturaelectronica:NominaIndividual NominaIndividualElectronicaXSD.xsd"
        })
        
        # Información general
        general_info = ET.SubElement(root, "InformacionGeneral")
        ET.SubElement(general_info, "Version").text = "V1.0"
        ET.SubElement(general_info, "Ambiente").text = self.dian_environment
        ET.SubElement(general_info, "TipoOperacion").text = self.dian_operation_type
        ET.SubElement(general_info, "FechaGeneracion").text = self.date.strftime("%Y-%m-%d")
        ET.SubElement(general_info, "PeriodoNomina", {"FechaIngreso": self.period_start.strftime("%Y-%m-%d"), "FechaRetiro": self.period_end.strftime("%Y-%m-%d") if self.period_end else ""})
        ET.SubElement(general_info, "TipoMoneda").text = self.currency_id.name
        
        # Información del empleador
        employer = ET.SubElement(root, "Empleador")
        ET.SubElement(employer, "NIT").text = self.company_id.vat.replace("-", "").replace(".", "")
        ET.SubElement(employer, "RazonSocial").text = self.company_id.name
        
        # Información del trabajador
        employee = ET.SubElement(root, "Trabajador")
        ET.SubElement(employee, "TipoDocumento").text = self.employee_identification_type
        ET.SubElement(employee, "NumeroDocumento").text = self.employee_identification
        ET.SubElement(employee, "PrimerApellido").text = self.employee_first_surname or ""
        ET.SubElement(employee, "SegundoApellido").text = self.employee_second_surname or ""
        ET.SubElement(employee, "PrimerNombre").text = self.employee_first_name or ""
        ET.SubElement(employee, "SegundoNombre").text = self.employee_second_name or ""
        
        # Información de la nómina
        payroll = ET.SubElement(root, "Pago")
        ET.SubElement(payroll, "Forma").text = "1"  # 1 = Transferencia
        ET.SubElement(payroll, "Metodo").text = "1"  # 1 = Contado
        
        # Devengados
        earnings = ET.SubElement(root, "Devengados")
        
        # Básico
        basic = ET.SubElement(earnings, "Basico")
        ET.SubElement(basic, "DiasTrabajados").text = str(self.payslip_worked_days)
        ET.SubElement(basic, "SueldoTrabajado").text = str(self.payslip_wage)
        
        # Deducciones
        deductions = ET.SubElement(root, "Deducciones")
        
        # Salud
        health = ET.SubElement(deductions, "Salud")
        ET.SubElement(health, "Porcentaje").text = "4.00"
        ET.SubElement(health, "Deduccion").text = str(self.payslip_id.health_contribution_employee)
        
        # Pensión
        pension = ET.SubElement(deductions, "Pension")
        ET.SubElement(pension, "Porcentaje").text = "4.00"
        ET.SubElement(pension, "Deduccion").text = str(self.payslip_id.pension_contribution_employee)
        
        # Convertir a string XML
        xml_string = ET.tostring(root, encoding='utf-8', method='xml')
        
        # Formatear XML para mejor legibilidad
        parsed_xml = etree.fromstring(xml_string)
        pretty_xml = etree.tostring(parsed_xml, pretty_print=True, encoding='utf-8').decode()
        
        return pretty_xml
    
    def _sign_xml(self, xml_content):
        """
        Firma el XML con el certificado digital
        """
        self.ensure_one()
        
        if not self.certificate_id:
            raise UserError(_("Debe seleccionar un certificado digital."))
        
        # Aquí iría la lógica para firmar el XML
        # Este es un proceso complejo que requiere una biblioteca específica
        # Por ahora, simplemente devolvemos el XML original como ejemplo
        
        # En un caso real, se utilizaría una biblioteca como signxml o pyXMLSecurity
        # para firmar el XML según los requisitos de la DIAN
        
        # Calcular CUDE (Código Único de Documento Electrónico)
        cude = self._calculate_cude()
        self.dian_cude = cude
        
        # Agregar CUDE al XML
        # Esto es simplificado, en un caso real se modificaría el XML correctamente
        signed_xml = xml_content.replace("</NominaIndividual>", f"<CUDE>{cude}</CUDE></NominaIndividual>")
        
        return signed_xml
    
    def _calculate_cude(self):
        """
        Calcula el CUDE (Código Único de Documento Electrónico)
        """
        self.ensure_one()
        
        # Construir la cadena para el CUDE según especificaciones de la DIAN
        cude_string = (
            f"{self.company_id.vat}"
            f"{self.dian_number}"
            f"{self.date.strftime('%Y-%m-%d')}"
            f"{self.payslip_id.net}"
            f"{self.employee_id.identification_id}"
            f"{self.software_id}"
            f"{self.technical_key}"
        )
        
        # Calcular el hash SHA-384
        cude = hashlib.sha384(cude_string.encode()).hexdigest()
        
        return cude
    
    def _send_to_dian(self, xml_content):
        """
        Envía el XML a la DIAN
        """
        self.ensure_one()
        
        # Configuración del servicio web de la DIAN
        if self.dian_environment == '1':
            # URL de producción
            url = self.company_id.dian_payroll_url_production
        else:
            # URL de pruebas
            url = self.company_id.dian_payroll_url_test
        
        # Preparar la solicitud
        headers = {
            'Content-Type': 'application/xml',
            'Accept': 'application/xml'
        }
        
        # Enviar la solicitud
        try:
            response = requests.post(url, data=xml_content, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # Registrar error
            self._create_log('error', _('Error al enviar a DIAN: %s') % str(e))
            return {
                'is_valid': False,
                'status_code': 'ERROR',
                'status_description': str(e),
                'error_message': str(e),
                'response_xml': '',
                'transaction_id': '',
            }
        
        # Procesar la respuesta
        try:
            response_xml = response.text
            root = ET.fromstring(response_xml)
            
            # Extraer información de la respuesta
            status_code = root.find('.//b:StatusCode', namespaces={'b': 'http://schemas.datacontract.org/2004/07/DianResponse'})
            status_description = root.find('.//b:StatusDescription', namespaces={'b': 'http://schemas.datacontract.org/2004/07/DianResponse'})
            transaction_id = root.find('.//b:XmlDocumentKey', namespaces={'b': 'http://schemas.datacontract.org/2004/07/DianResponse'})
            
            status_code_text = status_code.text if status_code is not None else 'UNKNOWN'
            status_description_text = status_description.text if status_description is not None else 'Desconocido'
            transaction_id_text = transaction_id.text if transaction_id is not None else ''
            
            # Determinar si es válido
            is_valid = status_code_text == '00'
            
            return {
                'is_valid': is_valid,
                'status_code': status_code_text,
                'status_description': status_description_text,
                'error_message': '' if is_valid else status_description_text,
                'response_xml': response_xml,
                'transaction_id': transaction_id_text,
            }
        except Exception as e:
            # Registrar error
            self._create_log('error', _('Error al procesar respuesta de DIAN: %s') % str(e))
            return {
                'is_valid': False,
                'status_code': 'ERROR',
                'status_description': 'Error al procesar respuesta',
                'error_message': str(e),
                'response_xml': response.text,
                'transaction_id': '',
            }
    
    def _create_cancellation_note(self):
        """
        Crea una nota de eliminación para cancelar un documento aceptado
        """
        self.ensure_one()
        
        # Crear una nueva nómina electrónica como nota de eliminación
        cancellation_note = self.copy({
            'name': _('New'),
            'dian_operation_type': '30',  # Eliminación
            'is_adjustment_note': True,
            'original_electronic_payroll_id': self.id,
            'adjustment_reason': _('Cancelación del documento %s') % self.name,
            'state': 'draft',
            'xml_file': False,
            'xml_filename': False,
            'xml_signed_file': False,
            'xml_signed_filename': False,
            'dian_response_file': False,
            'dian_response_filename': False,
            'dian_response_code': False,
            'dian_response_description': False,
            'dian_transaction_id': False,
            'dian_cude': False,
            'pdf_file': False,
            'pdf_filename': False,
        })
        
        # Abrir formulario para la nota de eliminación
        return {
            'name': _('Nota de Eliminación'),
            'view_mode': 'form',
            'res_model': 'hr.electronic.payroll',
            'res_id': cancellation_note.id,
            'type': 'ir.actions.act_window',
        }
    
    def _create_log(self, action_type, description):
        """
        Crea un registro en el log de eventos
        """
        self.ensure_one()
        
        self.env['hr.electronic.payroll.log'].create({
            'electronic_payroll_id': self.id,
            'date': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'action_type': action_type,
            'description': description,
        })
        
        # Agregar mensaje al chatter
        self.message_post(body=description)
        
        return True


class HrElectronicPayrollLog(models.Model):
    _name = 'hr.electronic.payroll.log'
    _description = 'Registro de Eventos de Nómina Electrónica'
    _order = 'date desc, id desc'
    
    electronic_payroll_id = fields.Many2one(
        'hr.electronic.payroll', string='Nómina Electrónica',
        required=True, ondelete='cascade')
    
    date = fields.Datetime(
        string='Fecha y Hora', required=True,
        default=fields.Datetime.now)
    
    user_id = fields.Many2one(
        'res.users', string='Usuario',
        required=True, default=lambda self: self.env.user.id)
    
    action_type = fields.Selection([
        ('create', 'Creación'),
        ('generate', 'Generación'),
        ('sign', 'Firma'),
        ('send', 'Envío'),
        ('accept', 'Aceptación'),
        ('reject', 'Rechazo'),
        ('cancel', 'Cancelación'),
        ('pdf', 'Generación PDF'),
        ('email', 'Envío Email'),
        ('reset', 'Restablecer'),
        ('error', 'Error'),
        ('other', 'Otro'),
    ], string='Tipo de Acción', required=True)
    
    description = fields.Text(
        string='Descripción', required=True)
    
    # Campos relacionados
    company_id = fields.Many2one(
        related='electronic_payroll_id.company_id',
        string='Compañía', store=True)
    
    employee_id = fields.Many2one(
        related='electronic_payroll_id.employee_id',
        string='Empleado', store=True)


class HrElectronicCertificate(models.Model):
    _name = 'hr.electronic.certificate'
    _description = 'Certificado Digital'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Nombre', required=True,
        tracking=True)
    
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        default=lambda self: self.env.company,
        tracking=True)
    
    certificate_file = fields.Binary(
        string='Archivo del Certificado', required=True,
        attachment=True, tracking=True)
    
    certificate_filename = fields.Char(
        string='Nombre del Archivo')
    
    password = fields.Char(
        string='Contraseña', required=True,
        help='Contraseña del certificado digital')
    
    issuer = fields.Char(
        string='Emisor', tracking=True)
    
    subject = fields.Char(
        string='Sujeto', tracking=True)
    
    valid_from = fields.Date(
        string='Válido Desde', tracking=True)
    
    valid_to = fields.Date(
        string='Válido Hasta', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('valid', 'Válido'),
        ('expired', 'Expirado'),
        ('revoked', 'Revocado'),
    ], string='Estado', default='draft',
       compute='_compute_state', store=True, tracking=True)
    
    notes = fields.Text(
        string='Notas', tracking=True)
    
    @api.depends('valid_from', 'valid_to')
    def _compute_state(self):
        today = fields.Date.today()
        for record in self:
            if not record.valid_from or not record.valid_to:
                record.state = 'draft'
            elif record.valid_to < today:
                record.state = 'expired'
            elif record.valid_from <= today <= record.valid_to:
                record.state = 'valid'
            else:
                record.state = 'draft'
    
    @api.model
    def create(self, vals):
        record = super(HrElectronicCertificate, self).create(vals)
        record._extract_certificate_info()
        return record
    
    def write(self, vals):
        result = super(HrElectronicCertificate, self).write(vals)
        if 'certificate_file' in vals or 'password' in vals:
            self._extract_certificate_info()
        return result
    
    def _extract_certificate_info(self):
        """
        Extrae información del certificado digital
        """
        for record in self:
            if not record.certificate_file or not record.password:
                continue
            
            try:
                # Aquí iría la lógica para extraer información del certificado
                # Usando bibliotecas como cryptography o PyOpenSSL
                # Por ahora, establecemos valores de ejemplo
                
                record.issuer = "Autoridad Certificadora"
                record.subject = f"CN={record.company_id.name}"
                record.valid_from = fields.Date.today()
                record.valid_to = fields.Date.today() + timedelta(days=365)
                
            except Exception as e:
                record.message_post(body=_("Error al extraer información del certificado: %s") % str(e))
    
    def action_check_validity(self):
        """
        Verifica la validez del certificado
        """
        self.ensure_one()
        
        self._extract_certificate_info()
        
        if self.state == 'valid':
            message = _("El certificado es válido hasta %s.") % self.valid_to
        elif self.state == 'expired':
            message = _("El certificado ha expirado el %s.") % self.valid_to
        else:
            message = _("No se pudo determinar la validez del certificado.")
        
        self.message_post(body=message)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Verificación de Certificado'),
                'message': message,
                'sticky': False,
                'type': 'info' if self.state == 'valid' else 'warning',
            }
        }