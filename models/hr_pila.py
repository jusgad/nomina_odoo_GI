# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import base64
import logging

_logger = logging.getLogger(__name__)

class HrPila(models.Model):
    _name = 'hr.pila'
    _description = 'PILA Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    date_from = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
        states={'done': [('readonly', True)]}
    )
    
    date_to = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
        states={'done': [('readonly', True)]}
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    payment_date = fields.Date(
        string='Payment Date',
        tracking=True,
        states={'done': [('readonly', True)]}
    )
    
    file_data = fields.Binary(
        string='PILA File',
        readonly=True,
        copy=False
    )
    
    file_name = fields.Char(
        string='File Name',
        readonly=True,
        copy=False
    )
    
    payslip_ids = fields.Many2many(
        'hr.payslip',
        'hr_pila_payslip_rel',
        'pila_id',
        'payslip_id',
        string='Payslips',
        states={'done': [('readonly', True)]}
    )
    
    total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_totals',
        store=True
    )
    
    total_health = fields.Float(
        string='Total Health',
        compute='_compute_totals',
        store=True,
        digits=(16, 2)
    )
    
    total_pension = fields.Float(
        string='Total Pension',
        compute='_compute_totals',
        store=True,
        digits=(16, 2)
    )
    
    total_arl = fields.Float(
        string='Total ARL',
        compute='_compute_totals',
        store=True,
        digits=(16, 2)
    )
    
    total_parafiscal = fields.Float(
        string='Total Parafiscal',
        compute='_compute_totals',
        store=True,
        digits=(16, 2)
    )
    
    note = fields.Text(
        string='Notes'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.pila') or _('New')
        return super(HrPila, self).create(vals_list)

    @api.depends('payslip_ids', 'payslip_ids.line_ids')
    def _compute_totals(self):
        for pila in self:
            payslips = pila.payslip_ids.filtered(lambda p: p.state in ['done', 'paid'])
            
            pila.total_employees = len(payslips.mapped('employee_id'))
            
            # Calcular totales de aportes
            total_health = 0.0
            total_pension = 0.0
            total_arl = 0.0
            total_parafiscal = 0.0
            
            for payslip in payslips:
                for line in payslip.line_ids:
                    if line.code == 'HEALTH':
                        total_health += line.total
                    elif line.code == 'PENSION':
                        total_pension += line.total
                    elif line.code == 'ARL':
                        total_arl += line.total
                    elif line.code in ['SENA', 'ICBF', 'CCF']:
                        total_parafiscal += line.total
            
            pila.total_health = total_health
            pila.total_pension = total_pension
            pila.total_arl = total_arl
            pila.total_parafiscal = total_parafiscal

    def action_generate_file(self):
        """Genera el archivo plano de PILA"""
        self.ensure_one()
        if not self.payslip_ids:
            raise UserError(_('No payslips found for this period.'))
            
        try:
            # Aquí va la lógica de generación del archivo plano
            file_content = self._generate_pila_content()
            
            # Codificar el contenido en base64
            file_data = base64.b64encode(file_content.encode('utf-8'))
            
            # Generar nombre del archivo
            file_name = f"PILA_{self.company_id.vat}_{self.date_from.strftime('%Y%m')}_{self.date_to.strftime('%Y%m')}.txt"
            
            # Actualizar registro
            self.write({
                'file_data': file_data,
                'file_name': file_name,
                'state': 'generated'
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/?model=hr.pila&id={self.id}&field=file_data&filename={file_name}&download=true',
                'target': 'self',
            }
            
        except Exception as e:
            raise UserError(_('Error generating PILA file: %s') % str(e))

    def _generate_pila_content(self):
        """Genera el contenido del archivo PILA"""
        content = []
        
        # 1. Registro tipo 1 - Encabezado
        header = self._generate_header()
        content.append(header)
        
        # 2. Registro tipo 2 - Liquidación
        for payslip in self.payslip_ids:
            employee_record = self._generate_employee_record(payslip)
            content.append(employee_record)
        
        # 3. Registro tipo 3 - Totales
        footer = self._generate_footer()
        content.append(footer)
        
        return '\n'.join(content)

    def _generate_header(self):
        """Genera el registro tipo 1 - Encabezado"""
        company = self.company_id
        return (
            f"01"  # Tipo registro
            f"{company.vat:>16}"  # NIT
            f"{company.name:<200}"  # Razón social
            f"{self.date_from.strftime('%Y%m'):>6}"  # Período
            # ... más campos según especificación
        )

    def _generate_employee_record(self, payslip):
        """Genera el registro tipo 2 - Liquidación por empleado"""
        employee = payslip.employee_id
        contract = payslip.contract_id
        
        return (
            f"02"  # Tipo registro
            f"{employee.identification_id:>16}"  # Documento
            f"{employee.name:<100}"  # Nombre
            f"{contract.wage:015.2f}"  # IBC
            # ... más campos según especificación
        )

    def _generate_footer(self):
        """Genera el registro tipo 3 - Totales"""
        return (
            f"03"  # Tipo registro
            f"{self.total_employees:06d}"  # Total empleados
            f"{self.total_health:015.2f}"  # Total salud
            f"{self.total_pension:015.2f}"  # Total pensión
            f"{self.total_arl:015.2f}"  # Total ARL
            f"{self.total_parafiscal:015.2f}"  # Total parafiscales
            # ... más campos según especificación
        )

    def action_confirm(self):
        """Confirma la PILA"""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('Please generate the PILA file first.'))
        self.write({'state': 'done'})

    def action_draft(self):
        """Regresa a borrador"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'file_data': False,
            'file_name': False
        })

    def action_cancel(self):
        """Cancela la PILA"""
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def unlink(self):
        """Previene eliminar registros confirmados"""
        for record in self:
            if record.state in ['done']:
                raise UserError(_('You cannot delete a confirmed PILA record.'))
        return super(HrPila, self).unlink()

class HrPilaLine(models.Model):
    _name = 'hr.pila.line'
    _description = 'PILA Line'
    
    pila_id = fields.Many2one(
        'hr.pila',
        string='PILA',
        required=True,
        ondelete='cascade'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )
    
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        required=True
    )
    
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        required=True
    )
    
    wage = fields.Float(
        string='Wage',
        digits=(16, 2)
    )
    
    health_base = fields.Float(
        string='Health Base',
        digits=(16, 2)
    )
    
    health_employee = fields.Float(
        string='Health Employee',
        digits=(16, 2)
    )
    
    health_employer = fields.Float(
        string='Health Employer',
        digits=(16, 2)
    )
    
    pension_base = fields.Float(
        string='Pension Base',
        digits=(16, 2)
    )
    
    pension_employee = fields.Float(
        string='Pension Employee',
        digits=(16, 2)
    )
    
    pension_employer = fields.Float(
        string='Pension Employer',
        digits=(16, 2)
    )
    
    arl_base = fields.Float(
        string='ARL Base',
        digits=(16, 2)
    )
    
    arl_value = fields.Float(
        string='ARL Value',
        digits=(16, 2)
    )
    
    ccf_base = fields.Float(
        string='CCF Base',
        digits=(16, 2)
    )
    
    ccf_value = fields.Float(
        string='CCF Value',
        digits=(16, 2)
    )
    
    sena_base = fields.Float(
        string='SENA Base',
        digits=(16, 2)
    )
    
    sena_value = fields.Float(
        string='SENA Value',
        digits=(16, 2)
    )
    
    icbf_base = fields.Float(
        string='ICBF Base',
        digits=(16, 2)
    )
    
    icbf_value = fields.Float(
        string='ICBF Value',
        digits=(16, 2)
    )
class HrPilaEmployee(models.Model):
    _name = 'hr.pila.employee'
    _description = 'PILA Employee Configuration'
    _inherit = ['mail.thread']

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True
    )

    pension_fund_id = fields.Many2one(
        'hr.pension.fund',
        string='Pension Fund',
        required=True,
        tracking=True
    )

    health_fund_id = fields.Many2one(
        'hr.health.fund',
        string='Health Fund',
        required=True,
        tracking=True
    )

    severance_fund_id = fields.Many2one(
        'hr.severance.fund',
        string='Severance Fund',
        required=True,
        tracking=True
    )

    arl_id = fields.Many2one(
        'hr.arl',
        string='ARL',
        required=True,
        tracking=True
    )

    risk_class = fields.Selection([
        ('1', 'Class I - 0.522%'),
        ('2', 'Class II - 1.044%'),
        ('3', 'Class III - 2.436%'),
        ('4', 'Class IV - 4.350%'),
        ('5', 'Class V - 6.960%'),
    ], string='Risk Class', required=True, tracking=True)

    ccf_id = fields.Many2one(
        'hr.ccf',
        string='Caja de Compensación',
        required=True,
        tracking=True
    )

    foreign_employee = fields.Boolean(
        string='Foreign Employee',
        tracking=True
    )

    pension_subcategory = fields.Selection([
        ('normal', 'Normal'),
        ('high_risk', 'High Risk'),
        ('foreign_pension', 'Foreign Pension'),
        ('pension_agreement', 'International Agreement'),
    ], string='Pension Subcategory', default='normal', tracking=True)

    health_subcategory = fields.Selection([
        ('normal', 'Normal'),
        ('foreign_health', 'Foreign Health'),
        ('health_agreement', 'International Agreement'),
    ], string='Health Subcategory', default='normal', tracking=True)

class HrPilaProcessing(models.Model):
    _name = 'hr.pila.processing'
    _description = 'PILA Processing Details'
    _inherit = ['mail.thread']
    _order = 'date desc'

    pila_id = fields.Many2one(
        'hr.pila',
        string='PILA Reference',
        required=True,
        ondelete='cascade'
    )

    date = fields.Date(
        string='Processing Date',
        required=True,
        tracking=True
    )

    operator_type = fields.Selection([
        ('simple', 'Simple'),
        ('integrated', 'Integrated'),
        ('pila', 'PILA'),
    ], string='Operator Type', required=True, tracking=True)

    payment_method = fields.Selection([
        ('pse', 'PSE'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
    ], string='Payment Method', required=True, tracking=True)

    bank_id = fields.Many2one(
        'res.bank',
        string='Bank'
    )

    payment_reference = fields.Char(
        string='Payment Reference',
        tracking=True
    )

    total_amount = fields.Float(
        string='Total Amount',
        digits=(16, 2),
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True)

    error_message = fields.Text(
        string='Error Message',
        tracking=True
    )

    @api.model
    def validate_pila_structure(self, file_content):
        """Valida la estructura del archivo PILA"""
        errors = []
        lines = file_content.split('\n')
        
        # Validar encabezado
        if not self._validate_header(lines[0]):
            errors.append(_('Invalid header structure'))
            
        # Validar registros de detalle
        for line in lines[1:-1]:
            if not self._validate_detail(line):
                errors.append(_('Invalid detail record: %s') % line)
                
        # Validar totales
        if not self._validate_footer(lines[-1]):
            errors.append(_('Invalid footer structure'))
            
        return errors

    def _validate_header(self, header_line):
        """Valida la estructura del encabezado"""
        try:
            # Implementar validaciones específicas del encabezado
            required_length = 500 
            if len(header_line) != required_length:
                return False
            
            # Validar tipo de registro
            if header_line[:2] != '01':
                return False
                
            # Más validaciones específicas...
            return True
        except Exception:
            return False

    def _validate_detail(self, detail_line):
        """Valida la estructura de una línea de detalle"""
        try:
            # Implementar validaciones específicas de las líneas de detalle
            required_length = 800  
            if len(detail_line) != required_length:
                return False
                
            # Validar tipo de registro
            if detail_line[:2] != '02':
                return False
                
            # Más validaciones específicas...
            return True
        except Exception:
            return False

    def _validate_footer(self, footer_line):
        """Valida la estructura del pie"""
        try:
            # Implementar validaciones específicas del pie
            required_length = 300 
            if len(footer_line) != required_length:
                return False
                
            # Validar tipo de registro
            if footer_line[:2] != '03':
                return False
                
            # Más validaciones específicas...
            return True
        except Exception:
            return False

    def action_validate(self):
        """Valida el proceso de PILA"""
        self.ensure_one()
        try:
            # Realizar validaciones
            if not self.pila_id.file_data:
                raise ValidationError(_('No PILA file generated yet.'))
                
            # Decodificar archivo
            file_content = base64.b64decode(self.pila_id.file_data).decode('utf-8')
            
            # Validar estructura
            errors = self.validate_pila_structure(file_content)
            if errors:
                self.write({
                    'state': 'error',
                    'error_message': '\n'.join(errors)
                })
                return False
                
            self.write({'state': 'validated'})
            return True
            
        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            return False

    def action_send(self):
        """Envía el archivo PILA al operador"""
        self.ensure_one()
        if self.state != 'validated':
            raise UserError(_('PILA must be validated first.'))
            
        try:
            # Implementar lógica de envío al operador
            self._send_to_operator()
            self.write({'state': 'sent'})
            
        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise UserError(_('Error sending PILA: %s') % str(e))

    def _send_to_operator(self):
        """Implementación del envío al operador"""
        if self.operator_type == 'simple':
            return self._send_to_simple_operator()
        elif self.operator_type == 'integrated':
            return self._send_to_integrated_operator()
        elif self.operator_type == 'pila':
            return self._send_to_pila_operator()
        else:
            raise ValidationError(_('Invalid operator type'))

    def _send_to_simple_operator(self):
        """Envía al operador simple (ej: SOI, ARUS)"""
        self.ensure_one()
        try:
        # Configuración del operador
            operator_config = self.env['hr.pila.operator.config'].search([
                ('operator_type', '=', 'simple'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if not operator_config:
                raise ValidationError(_('Simple operator configuration not found'))

            # Preparar el archivo
            file_content = base64.b64decode(self.pila_id.file_data)
            
            # Preparar los headers para la petición
            headers = {
                'Authorization': f'Bearer {operator_config.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # Preparar el payload
            payload = {
                'nit': self.company_id.vat,
                'period': self.pila_id.date_from.strftime('%Y%m'),
                'file_content': base64.b64encode(file_content).decode('utf-8'),
                'payment_type': self.payment_method,
                'total_amount': self.total_amount,
                'reference': self.pila_id.name
            }

            # Realizar la petición al API del operador
            response = requests.post(
                operator_config.api_url + '/upload',
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                raise ValidationError(
                _('Error from operator: %s') % response.json().get('message', '')
                )

            # Procesar respuesta
            response_data = response.json()
            
            # Guardar referencia de pago
            self.write({
                'payment_reference': response_data.get('payment_reference'),
                'state': 'sent'
            })

            # Registrar en el log
            self.env['hr.pila.log'].create({
                'pila_id': self.pila_id.id,
                'action': 'send',
                'description': f'Sent to {operator_config.name} - Ref: {response_data.get("payment_reference")}'
            })

            return True

        except requests.exceptions.RequestException as e:
            error_msg = f'Connection error with operator: {str(e)}'
            self._handle_sending_error(error_msg)
            
        except Exception as e:
            error_msg = f'Error sending to simple operator: {str(e)}'
            self._handle_sending_error(error_msg)

    def _send_to_integrated_operator(self):
        """Envía al operador integrado (ej: ASOPAGOS, MI PLANILLA)"""
        self.ensure_one()
        try:
            # Configuración del operador
            operator_config = self.env['hr.pila.operator.config'].search([
                ('operator_type', '=', 'integrated'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if not operator_config:
                raise ValidationError(_('Integrated operator configuration not found'))

            # Preparar datos de autenticación SOAP
            client = Client(
                operator_config.wsdl_url,
                transport=Transport(timeout=30)
            )

            # Preparar el archivo y encriptarlo si es necesario
            file_content = base64.b64decode(self.pila_id.file_data)
            if operator_config.requires_encryption:
                file_content = self._encrypt_file(file_content, operator_config.encryption_key)

            # Preparar el payload SOAP
            soap_payload = {
                'credentials': {
                    'username': operator_config.username,
                    'password': operator_config.password,
                    'nit': self.company_id.vat
                },
                'data': {
                    'period': self.pila_id.date_from.strftime('%Y%m'),
                    'file_content': base64.b64encode(file_content).decode('utf-8'),
                    'payment_method': self.payment_method,
                    'total_amount': self.total_amount,
                    'reference': self.pila_id.name
                }
            }

            # Llamar al servicio SOAP
            response = client.service.uploadPILA(**soap_payload)

            if not response.success:
                raise ValidationError(
                    _('Error from integrated operator: %s') % response.error_message
                )

            # Guardar referencia de pago
            self.write({
                'payment_reference': response.payment_reference,
                'state': 'sent'
            })

            # Registrar en el log
            self.env['hr.pila.log'].create({
                'pila_id': self.pila_id.id,
                'action': 'send',
                'description': f'Sent to {operator_config.name} - Ref: {response.payment_reference}'
            })

            return True

        except Exception as e:
            error_msg = f'Error sending to integrated operator: {str(e)}'
            self._handle_sending_error(error_msg)

    def _send_to_pila_operator(self):
        """Envía al operador PILA (ej: SIMPLE, FTP)"""
        self.ensure_one()
        try:
            # Configuración del operador
            operator_config = self.env['hr.pila.operator.config'].search([
                ('operator_type', '=', 'pila'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if not operator_config:
                raise ValidationError(_('PILA operator configuration not found'))

            # Crear nombre del archivo
            filename = f"PILA_{self.company_id.vat}_{self.pila_id.date_from.strftime('%Y%m')}.txt"

            # Conectar al FTP
            with FTP(operator_config.ftp_host) as ftp:
                ftp.login(
                    user=operator_config.ftp_user,
                    passwd=operator_config.ftp_password
                )
                
                # Cambiar al directorio correcto
                ftp.cwd(operator_config.ftp_path)

                # Subir el archivo
                file_content = base64.b64decode(self.pila_id.file_data)
                with BytesIO(file_content) as file:
                    ftp.storbinary(f'STOR {filename}', file)

                # Verificar que el archivo se subió correctamente
                if filename not in ftp.nlst():
                    raise ValidationError(_('File upload to FTP failed'))

            # Guardar referencia
            self.write({
                'payment_reference': filename,
                'state': 'sent'
            })

            # Registrar en el log
            self.env['hr.pila.log'].create({
                'pila_id': self.pila_id.id,
                'action': 'send',
                'description': f'Sent to FTP - File: {filename}'
            })

            return True

        except Exception as e:
            error_msg = f'Error sending to PILA operator: {str(e)}'
            self._handle_sending_error(error_msg)

    def _handle_sending_error(self, error_message):
        """Maneja los errores de envío de manera centralizada"""
        self.write({
            'state': 'error',
            'error_message': error_message
        })

        # Registrar en el log
        self.env['hr.pila.log'].create({
            'pila_id': self.pila_id.id,
            'action': 'error',
            'description': error_message
        })

        # Notificar al usuario
        self.env.user.notify_warning(
            title=_('PILA Sending Error'),
            message=error_message
        )

        raise ValidationError(error_message)

    def _encrypt_file(self, file_content, encryption_key):
        """Encripta el contenido del archivo si es requerido"""
        try:
            # Implementar el método de encriptación requerido por el operador
            fernet = Fernet(encryption_key)
            return fernet.encrypt(file_content)
        except Exception as e:
            raise ValidationError(_('Error encrypting file: %s') % str(e))
class HrPilaReport(models.Model):
    _name = 'hr.pila.report'
    _description = 'PILA Reports'
    _inherit = ['mail.thread']
    _order = 'date desc'

    pila_id = fields.Many2one(
        'hr.pila',
        string='PILA Reference',
        required=True,
        ondelete='cascade'
    )

    date = fields.Date(
        string='Report Date',
        required=True,
        tracking=True
    )

    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('errors', 'Errors Report'),
        ('payment', 'Payment Report'),
        ('audit', 'Audit Report')
    ], string='Report Type', required=True)

    def generate_report(self):
        """Genera el reporte según el tipo seleccionado"""
        self.ensure_one()
        if self.report_type == 'summary':
            return self._generate_summary_report()
        elif self.report_type == 'detailed':
            return self._generate_detailed_report()
        elif self.report_type == 'errors':
            return self._generate_errors_report()
        elif self.report_type == 'payment':
            return self._generate_payment_report()
        elif self.report_type == 'audit':
            return self._generate_audit_report()

    def _generate_summary_report(self):
        """Genera reporte resumen de PILA"""
        self.ensure_one()
        data = {
            'pila_ref': self.pila_id.name,
            'date_from': self.pila_id.date_from,
            'date_to': self.pila_id.date_to,
            'total_employees': self.pila_id.total_employees,
            'total_health': self.pila_id.total_health,
            'total_pension': self.pila_id.total_pension,
            'total_arl': self.pila_id.total_arl,
            'total_parafiscal': self.pila_id.total_parafiscal,
        }
        return self.env.ref('nomina_colombia_v18.action_report_pila_summary').report_action(self, data=data)

class HrPilaValidation(models.Model):
    _name = 'hr.pila.validation'
    _description = 'PILA Validation Rules'

    name = fields.Char(
        string='Rule Name',
        required=True
    )

    code = fields.Char(
        string='Rule Code',
        required=True
    )

    description = fields.Text(
        string='Description'
    )

    validation_type = fields.Selection([
        ('required', 'Required Field'),
        ('format', 'Format Validation'),
        ('range', 'Range Validation'),
        ('dependency', 'Dependency Validation'),
        ('custom', 'Custom Validation')
    ], string='Validation Type', required=True)

    python_code = fields.Text(
        string='Python Code',
        help="Python code for custom validations"
    )

    active = fields.Boolean(
        default=True
    )

    def validate(self, record):
        """Ejecuta la validación según el tipo"""
        self.ensure_one()
        if self.validation_type == 'required':
            return self._validate_required(record)
        elif self.validation_type == 'format':
            return self._validate_format(record)
        elif self.validation_type == 'range':
            return self._validate_range(record)
        elif self.validation_type == 'dependency':
            return self._validate_dependency(record)
        elif self.validation_type == 'custom':
            return self._validate_custom(record)
        return True

class HrPilaLog(models.Model):
    _name = 'hr.pila.log'
    _description = 'PILA Process Log'
    _order = 'create_date desc'

    pila_id = fields.Many2one(
        'hr.pila',
        string='PILA Reference'
    )

    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user
    )

    action = fields.Selection([
        ('create', 'Created'),
        ('generate', 'Generated'),
        ('validate', 'Validated'),
        ('send', 'Sent'),
        ('error', 'Error'),
        ('cancel', 'Cancelled')
    ], string='Action')

    description = fields.Text(
        string='Description'
    )

    error_message = fields.Text(
        string='Error Message'
    )

class HrPilaSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pila_operator = fields.Selection([
        ('simple', 'Simple'),
        ('integrated', 'Integrated'),
        ('pila', 'PILA')
    ], string='Default PILA Operator', config_parameter='nomina_colombia.pila_operator')

    pila_payment_method = fields.Selection([
        ('pse', 'PSE'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash')
    ], string='Default Payment Method', config_parameter='nomina_colombia.pila_payment_method')

    pila_validation_mode = fields.Selection([
        ('strict', 'Strict'),
        ('warning', 'Warning Only'),
        ('flexible', 'Flexible')
    ], string='Validation Mode', config_parameter='nomina_colombia.pila_validation_mode')

    auto_send_pila = fields.Boolean(
        string='Auto-send PILA',
        config_parameter='nomina_colombia.auto_send_pila'
    )

    def set_values(self):
        super(HrPilaSettings, self).set_values()
        self.env['ir.config_parameter'].set_param(
            'nomina_colombia.pila_operator',
            self.pila_operator
        )
        self.env['ir.config_parameter'].set_param(
            'nomina_colombia.pila_payment_method',
            self.pila_payment_method
        )
        self.env['ir.config_parameter'].set_param(
            'nomina_colombia.pila_validation_mode',
            self.pila_validation_mode
        )
        self.env['ir.config_parameter'].set_param(
            'nomina_colombia.auto_send_pila',
            str(self.auto_send_pila)
        )

class HrPilaWizard(models.TransientModel):
    _name = 'hr.pila.wizard'
    _description = 'PILA Generation Wizard'

    date_from = fields.Date(
        string='Start Date',
        required=True
    )

    date_to = fields.Date(
        string='End Date',
        required=True
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees'
    )

    include_all_employees = fields.Boolean(
        string='Include All Employees',
        default=True
    )

    def action_generate_pila(self):
        """Genera PILA desde el wizard"""
        self.ensure_one()
        
        # Validar fechas
        if self.date_to < self.date_from:
            raise ValidationError(_('End date must be greater than start date'))

        # Crear registro PILA
        vals = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'state': 'draft'
        }

        if not self.include_all_employees:
            if not self.employee_ids:
                raise ValidationError(_('Please select at least one employee'))
            vals['employee_ids'] = [(6, 0, self.employee_ids.ids)]

        pila_id = self.env['hr.pila'].create(vals)

        # Registrar en el log
        self.env['hr.pila.log'].create({
            'pila_id': pila_id.id,
            'action': 'create',
            'description': _('PILA created from wizard')
        })

        # Retornar acción para ver el registro creado
        return {
            'name': _('PILA'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.pila',
            'res_id': pila_id.id,
            'view_mode': 'form',
            'target': 'current',
        }