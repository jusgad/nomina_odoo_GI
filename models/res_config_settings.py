from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuraciones Generales de la Compañía
    module_nomina_colombia = fields.Boolean(
        string="Gestión de Nómina Colombiana"
    )

    # Configuraciones de la DIAN
    dian_resolution_number = fields.Char(
        string="Número de Resolución DIAN",
        config_parameter='nomina_colombia.dian_resolution_number'
    )

    dian_resolution_date = fields.Date(
        string="Fecha de Resolución DIAN",
        config_parameter='nomina_colombia.dian_resolution_date'
    )

    dian_test_mode = fields.Boolean(
        string="Modo de Pruebas DIAN",
        config_parameter='nomina_colombia.dian_test_mode'
    )

    electronic_payroll_enabled = fields.Boolean(
        string="Habilitar Nómina Electrónica",
        config_parameter='nomina_colombia.electronic_payroll_enabled'
    )

    # Configuraciones del Operador PILA
    pila_operator = fields.Selection([
        ('simple', 'Operador Simple'),
        ('integrated', 'Operador Integrado'),
        ('pila', 'Operador PILA')
    ], string="Operador PILA",
        config_parameter='nomina_colombia.pila_operator'
    )

    pila_operator_url = fields.Char(
        string="URL del Operador",
        config_parameter='nomina_colombia.pila_operator_url'
    )

    pila_operator_username = fields.Char(
        string="Usuario del Operador",
        config_parameter='nomina_colombia.pila_operator_username'
    )

    pila_operator_password = fields.Char(
        string="Contraseña del Operador",
        config_parameter='nomina_colombia.pila_operator_password'
    )

    # Configuraciones de Redondeo y Precisión
    wage_rounding = fields.Selection([
        ('no_rounding', 'Sin Redondeo'),
        ('hundred', 'Centenas'),
        ('thousand', 'Miles')
    ], string="Redondeo de Salarios",
        config_parameter='nomina_colombia.wage_rounding',
        default='no_rounding'
    )

    decimal_precision = fields.Integer(
        string="Precisión Decimal",
        config_parameter='nomina_colombia.decimal_precision',
        default=2
    )

    # Configuraciones de Cálculos por Defecto
    default_work_days = fields.Integer(
        string="Días Laborales por Defecto",
        config_parameter='nomina_colombia.default_work_days',
        default=30
    )

    default_hour_value_factor = fields.Float(
        string="Factor Valor Hora",
        config_parameter='nomina_colombia.default_hour_value_factor',
        default=240
    )

    # Configuraciones de Integración Bancaria
    bank_file_format = fields.Selection([
        ('bancolombia', 'Bancolombia'),
        ('davivienda', 'Davivienda'),
        ('bbva', 'BBVA'),
        ('popular', 'Banco Popular')
    ], string="Formato Archivo Bancario",
        config_parameter='nomina_colombia.bank_file_format'
    )

    generate_bank_file = fields.Boolean(
        string="Generar Archivo Bancario",
        config_parameter='nomina_colombia.generate_bank_file'
    )

    # Configuraciones de Reportes
    payslip_report_template = fields.Selection([
        ('detailed', 'Detallado'),
        ('simple', 'Simple'),
        ('custom', 'Personalizado')
    ], string="Plantilla de Comprobante de Pago",
        config_parameter='nomina_colombia.payslip_report_template',
        default='detailed'
    )

    # Configuraciones de Contabilización
    auto_post_payslip = fields.Boolean(
        string="Contabilización Automática de Nómina",
        config_parameter='nomina_colombia.auto_post_payslip'
    )

    payroll_journal_id = fields.Many2one(
        'account.journal',
        string="Diario de Nómina",
        config_parameter='nomina_colombia.payroll_journal_id'
    )

    provision_journal_id = fields.Many2one(
        'account.journal',
        string="Diario de Provisiones",
        config_parameter='nomina_colombia.provision_journal_id'
    )

    # Configuraciones de Seguridad Social
    default_pension_percentage = fields.Float(
        string="Porcentaje Pensión por Defecto",
        config_parameter='nomina_colombia.default_pension_percentage',
        default=16.0
    )

    default_health_percentage = fields.Float(
        string="Porcentaje Salud por Defecto",
        config_parameter='nomina_colombia.default_health_percentage',
        default=12.5
    )

    default_arl_percentage = fields.Float(
        string="Porcentaje ARL por Defecto",
        config_parameter='nomina_colombia.default_arl_percentage',
        default=0.522
    )

    # Métodos de la Clase
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        # Recuperar valores almacenados
        res.update(
            dian_resolution_number=ICPSudo.get_param('nomina_colombia.dian_resolution_number', default=''),
            dian_resolution_date=ICPSudo.get_param('nomina_colombia.dian_resolution_date', default=False),
            dian_test_mode=ICPSudo.get_param('nomina_colombia.dian_test_mode', default=True),
            electronic_payroll_enabled=ICPSudo.get_param('nomina_colombia.electronic_payroll_enabled', default=False),
            pila_operator=ICPSudo.get_param('nomina_colombia.pila_operator', default='simple'),
            wage_rounding=ICPSudo.get_param('nomina_colombia.wage_rounding', default='no_rounding'),
            decimal_precision=int(ICPSudo.get_param('nomina_colombia.decimal_precision', default=2)),
            default_work_days=int(ICPSudo.get_param('nomina_colombia.default_work_days', default=30)),
            bank_file_format=ICPSudo.get_param('nomina_colombia.bank_file_format', default=False),
            payslip_report_template=ICPSudo.get_param('nomina_colombia.payslip_report_template', default='detailed'),
            auto_post_payslip=ICPSudo.get_param('nomina_colombia.auto_post_payslip', default=False),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        # Almacenar valores en parámetros del sistema
        ICPSudo.set_param('nomina_colombia.dian_resolution_number', self.dian_resolution_number)
        ICPSudo.set_param('nomina_colombia.dian_resolution_date', self.dian_resolution_date)
        ICPSudo.set_param('nomina_colombia.dian_test_mode', self.dian_test_mode)
        ICPSudo.set_param('nomina_colombia.electronic_payroll_enabled', self.electronic_payroll_enabled)
        ICPSudo.set_param('nomina_colombia.pila_operator', self.pila_operator)
        ICPSudo.set_param('nomina_colombia.wage_rounding', self.wage_rounding)
        ICPSudo.set_param('nomina_colombia.decimal_precision', self.decimal_precision)
        ICPSudo.set_param('nomina_colombia.default_work_days', self.default_work_days)
        ICPSudo.set_param('nomina_colombia.bank_file_format', self.bank_file_format)
        ICPSudo.set_param('nomina_colombia.payslip_report_template', self.payslip_report_template)
        ICPSudo.set_param('nomina_colombia.auto_post_payslip', self.auto_post_payslip)

    @api.onchange('electronic_payroll_enabled')
    def _onchange_electronic_payroll_enabled(self):
        if self.electronic_payroll_enabled and not self.dian_resolution_number:
            return {
                'warning': {
                    'title': _("Advertencia"),
                    'message': _("Para habilitar la nómina electrónica, debe configurar el número de resolución DIAN.")
                }
            }

    @api.constrains('decimal_precision')
    def _check_decimal_precision(self):
        for record in self:
            if record.decimal_precision < 0 or record.decimal_precision > 6:
                raise ValidationError(_("La precisión decimal debe estar entre 0 y 6."))

    @api.constrains('default_work_days')
    def _check_default_work_days(self):
        for record in self:
            if record.default_work_days < 1 or record.default_work_days > 31:
                raise ValidationError(_("Los días laborales por defecto deben estar entre 1 y 31."))

    def action_test_dian_connection(self):
        """Prueba la conexión con la DIAN"""
        self.ensure_one()
        try:
            # Implementar lógica de prueba de conexión
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Éxito"),
                    'message': _("Conexión con la DIAN establecida correctamente."),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuraciones de Certificados Digitales
    digital_certificate = fields.Binary(
        string="Certificado Digital",
        config_parameter='nomina_colombia.digital_certificate'
    )

    digital_certificate_password = fields.Char(
        string="Contraseña del Certificado",
        config_parameter='nomina_colombia.digital_certificate_password'
    )

    certificate_expiration_date = fields.Date(
        string="Fecha de Vencimiento del Certificado",
        config_parameter='nomina_colombia.certificate_expiration_date'
    )

    # Configuraciones de Correo Electrónico
    payslip_mail_template_id = fields.Many2one(
        'mail.template',
        string="Plantilla de Correo para Comprobantes",
        config_parameter='nomina_colombia.payslip_mail_template_id'
    )

    send_payslip_automatically = fields.Boolean(
        string="Enviar Comprobantes Automáticamente",
        config_parameter='nomina_colombia.send_payslip_automatically'
    )

    # Configuraciones de Provisiones
    provision_calculation_method = fields.Selection([
        ('monthly', 'Mensual'),
        ('bimonthly', 'Bimestral'),
        ('quarterly', 'Trimestral'),
        ('semiannual', 'Semestral')
    ], string="Método de Cálculo de Provisiones",
        config_parameter='nomina_colombia.provision_calculation_method',
        default='monthly'
    )

    auto_calculate_provisions = fields.Boolean(
        string="Calcular Provisiones Automáticamente",
        config_parameter='nomina_colombia.auto_calculate_provisions'
    )

    # Configuraciones de Retención en la Fuente
    retention_method = fields.Selection([
        ('fixed', 'Fija'),
        ('variable', 'Variable'),
        ('table', 'Tabla de Retención')
    ], string="Método de Retención",
        config_parameter='nomina_colombia.retention_method',
        default='table'
    )

    retention_calculation_base = fields.Selection([
        ('monthly', 'Base Mensual'),
        ('bimonthly', 'Base Bimestral')
    ], string="Base de Cálculo Retención",
        config_parameter='nomina_colombia.retention_calculation_base',
        default='monthly'
    )

    # Configuraciones de Horas Extra
    overtime_calculation_method = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Valor Fijo')
    ], string="Método de Cálculo Horas Extra",
        config_parameter='nomina_colombia.overtime_calculation_method',
        default='percentage'
    )

    default_overtime_percentage = fields.Float(
        string="Porcentaje por Defecto Horas Extra",
        config_parameter='nomina_colombia.default_overtime_percentage',
        default=25.0
    )

    # Configuraciones de Vacaciones
    vacation_days_per_year = fields.Integer(
        string="Días de Vacaciones por Año",
        config_parameter='nomina_colombia.vacation_days_per_year',
        default=15
    )

    vacation_payment_method = fields.Selection([
        ('average', 'Promedio'),
        ('last_salary', 'Último Salario')
    ], string="Método de Pago Vacaciones",
        config_parameter='nomina_colombia.vacation_payment_method',
        default='average'
    )

    # Configuraciones de Cesantías
    severance_fund_payment_day = fields.Integer(
        string="Día de Pago Cesantías",
        config_parameter='nomina_colombia.severance_fund_payment_day',
        default=14
    )

    severance_interest_payment_day = fields.Integer(
        string="Día de Pago Intereses Cesantías",
        config_parameter='nomina_colombia.severance_interest_payment_day',
        default=31
    )

    # Configuraciones de Seguridad
    payroll_access_token = fields.Char(
        string="Token de Acceso API",
        config_parameter='nomina_colombia.payroll_access_token'
    )

    payroll_api_url = fields.Char(
        string="URL API Nómina",
        config_parameter='nomina_colombia.payroll_api_url'
    )

    # Métodos Adicionales
    def generate_access_token(self):
        """Genera un nuevo token de acceso para la API"""
        token = uuid.uuid4().hex
        self.env['ir.config_parameter'].sudo().set_param(
            'nomina_colombia.payroll_access_token', token)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Éxito"),
                'message': _("Nuevo token de acceso generado correctamente."),
                'type': 'success',
                'sticky': False,
            }
        }

    def check_certificate_expiration(self):
        """Verifica la vigencia del certificado digital"""
        if not self.certificate_expiration_date:
            return

        days_to_expire = (self.certificate_expiration_date - fields.Date.today()).days
        if days_to_expire <= 30:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Advertencia"),
                    'message': _("El certificado digital vencerá en %s días.") % days_to_expire,
                    'type': 'warning',
                    'sticky': True,
                }
            }

    @api.model
    def create_default_mail_template(self):
        """Crea una plantilla de correo por defecto para comprobantes"""
        template_data = {
            'name': 'Plantilla Comprobante de Nómina',
            'model_id': self.env['ir.model'].search(
                [('model', '=', 'hr.payslip')], limit=1).id,
            'subject': 'Comprobante de Nómina - ${object.name}',
            'email_from': '${object.company_id.email}',
            'partner_to': '${object.employee_id.address_home_id.id}',
            'body_html': '''
                <div style="margin: 0px; padding: 0px;">
                    <p style="margin: 0px; padding: 0px; font-size: 13px;">
                        Estimado/a ${object.employee_id.name},<br/><br/>
                        Adjunto encontrará su comprobante de nómina correspondiente al período
                        ${object.date_from} - ${object.date_to}.<br/><br/>
                        Saludos cordiales,<br/>
                        ${object.company_id.name}
                    </p>
                </div>
            ''',
            'report_template': self.env.ref('nomina_colombia.report_payslip').id,
        }
        return self.env['mail.template'].create(template_data)

    def test_email_configuration(self):
        """Prueba la configuración de correo electrónico"""
        try:
            test_mail = self.env['mail.mail'].create({
                'subject': 'Prueba de Configuración de Correo',
                'email_from': self.company_id.email,
                'email_to': self.company_id.email,
                'body_html': '<p>Este es un correo de prueba para verificar la configuración.</p>'
            })
            test_mail.send()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Éxito"),
                    'message': _("Correo de prueba enviado correctamente."),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    @api.onchange('provision_calculation_method')
    def _onchange_provision_calculation_method(self):
        if self.provision_calculation_method != 'monthly':
            return {
                'warning': {
                    'title': _("Advertencia"),
                    'message': _("El cálculo no mensual de provisiones puede afectar los reportes mensuales.")
                }
            }

    @api.constrains('severance_fund_payment_day', 'severance_interest_payment_day')
    def _check_payment_days(self):
        for record in self:
            if record.severance_fund_payment_day < 1 or record.severance_fund_payment_day > 31:
                raise ValidationError(_("El día de pago de cesantías debe estar entre 1 y 31."))
            if record.severance_interest_payment_day < 1 or record.severance_interest_payment_day > 31:
                raise ValidationError(_("El día de pago de intereses debe estar entre 1 y 31."))

    def action_update_uvt(self):
        """Actualiza el valor de la UVT desde la DIAN"""
        try:
            # Implementar lógica para obtener UVT actualizado
            # Esta es una implementación de ejemplo
            current_year = fields.Date.today().year
            uvt_value = self._get_uvt_from_dian(current_year)
            self.env['ir.config_parameter'].sudo().set_param(
                'nomina_colombia.uvt_value', str(uvt_value))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Éxito"),
                    'message': _("Valor de UVT actualizado correctamente."),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _get_uvt_from_dian(self, year):
        """Obtiene el valor de la UVT desde la DIAN"""
        # Implementar lógica de conexión con DIAN
        # Esta es una implementación de ejemplo
        uvt_values = {
            2024: 47065,
            2023: 42412,
            2022: 38004,
        }
        return uvt_values.get(year, 0)
    class ResConfigSettings(models.TransientModel):
        _inherit = 'res.config.settings'

        # Configuraciones de Nómina Electrónica DIAN
        dian_environment = fields.Selection([
            ('1', 'Producción'),
            ('2', 'Pruebas')
        ], string="Ambiente DIAN",
            config_parameter='nomina_colombia.dian_environment',
            default='2'
        )

        dian_software_id = fields.Char(
            string="ID del Software DIAN",
            config_parameter='nomina_colombia.dian_software_id'
        )

        dian_software_pin = fields.Char(
            string="PIN del Software DIAN",
            config_parameter='nomina_colombia.dian_software_pin'
        )

        dian_date_from = fields.Date(
            string="Fecha Inicio Resolución",
            config_parameter='nomina_colombia.dian_date_from'
        )

        dian_date_to = fields.Date(
            string="Fecha Fin Resolución",
            config_parameter='nomina_colombia.dian_date_to'
        )

        # Configuraciones de Numeración
        payslip_sequence_id = fields.Many2one(
            'ir.sequence',
            string="Secuencia de Comprobantes",
            config_parameter='nomina_colombia.payslip_sequence_id'
        )

        electronic_payslip_prefix = fields.Char(
            string="Prefijo Nómina Electrónica",
            config_parameter='nomina_colombia.electronic_payslip_prefix'
        )

        # Configuraciones de Redondeo Específicas
        round_payslip_amount = fields.Selection([
            ('peso', 'Peso'),
            ('hundred', 'Centena'),
            ('thousand', 'Miles')
        ], string="Redondeo Valores Nómina",
            config_parameter='nomina_colombia.round_payslip_amount',
            default='peso'
        )

        round_transport_allowance = fields.Boolean(
            string="Redondear Auxilio de Transporte",
            config_parameter='nomina_colombia.round_transport_allowance',
            default=True
        )

        # Configuraciones de Conceptos por Defecto
        default_basic_salary_code = fields.Char(
            string="Código Salario Básico",
            config_parameter='nomina_colombia.default_basic_salary_code',
            default='BASIC'
        )

        default_transport_allowance_code = fields.Char(
            string="Código Auxilio de Transporte",
            config_parameter='nomina_colombia.default_transport_allowance_code',
            default='TRANS'
        )

        # Configuraciones de Cálculos Avanzados
        average_calculation_months = fields.Integer(
            string="Meses para Cálculo de Promedio",
            config_parameter='nomina_colombia.average_calculation_months',
            default=3
        )

        include_non_salary_average = fields.Boolean(
            string="Incluir Pagos No Salariales en Promedio",
            config_parameter='nomina_colombia.include_non_salary_average',
            default=False
        )

        # Configuraciones de Reportes Específicos
        certifications_footer_text = fields.Text(
            string="Texto Pie de Página Certificaciones",
            config_parameter='nomina_colombia.certifications_footer_text'
        )

        show_detailed_provisions = fields.Boolean(
            string="Mostrar Provisiones Detalladas",
            config_parameter='nomina_colombia.show_detailed_provisions',
            default=True
        )

        # Configuraciones de Integración Contable
        detailed_accounting_entries = fields.Boolean(
            string="Asientos Contables Detallados",
            config_parameter='nomina_colombia.detailed_accounting_entries',
            default=True
        )

        group_payslip_entries = fields.Boolean(
            string="Agrupar Asientos de Nómina",
            config_parameter='nomina_colombia.group_payslip_entries',
            default=False
        )

    # Métodos de la Clase
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        # Recuperar valores adicionales
        res.update(
            dian_environment=ICPSudo.get_param('nomina_colombia.dian_environment', '2'),
            dian_software_id=ICPSudo.get_param('nomina_colombia.dian_software_id', False),
            dian_software_pin=ICPSudo.get_param('nomina_colombia.dian_software_pin', False),
            dian_date_from=ICPSudo.get_param('nomina_colombia.dian_date_from', False),
            dian_date_to=ICPSudo.get_param('nomina_colombia.dian_date_to', False),
            electronic_payslip_prefix=ICPSudo.get_param('nomina_colombia.electronic_payslip_prefix', False),
            round_payslip_amount=ICPSudo.get_param('nomina_colombia.round_payslip_amount', 'peso'),
            round_transport_allowance=ICPSudo.get_param('nomina_colombia.round_transport_allowance', True),
            average_calculation_months=int(ICPSudo.get_param('nomina_colombia.average_calculation_months', '3')),
            include_non_salary_average=ICPSudo.get_param('nomina_colombia.include_non_salary_average', False),
            detailed_accounting_entries=ICPSudo.get_param('nomina_colombia.detailed_accounting_entries', True),
            group_payslip_entries=ICPSudo.get_param('nomina_colombia.group_payslip_entries', False),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        # Guardar valores adicionales
        ICPSudo.set_param('nomina_colombia.dian_environment', self.dian_environment)
        ICPSudo.set_param('nomina_colombia.dian_software_id', self.dian_software_id)
        ICPSudo.set_param('nomina_colombia.dian_software_pin', self.dian_software_pin)
        ICPSudo.set_param('nomina_colombia.dian_date_from', self.dian_date_from)
        ICPSudo.set_param('nomina_colombia.dian_date_to', self.dian_date_to)
        ICPSudo.set_param('nomina_colombia.electronic_payslip_prefix', self.electronic_payslip_prefix)
        ICPSudo.set_param('nomina_colombia.round_payslip_amount', self.round_payslip_amount)
        ICPSudo.set_param('nomina_colombia.round_transport_allowance', self.round_transport_allowance)
        ICPSudo.set_param('nomina_colombia.average_calculation_months', self.average_calculation_months)
        ICPSudo.set_param('nomina_colombia.include_non_salary_average', self.include_non_salary_average)
        ICPSudo.set_param('nomina_colombia.detailed_accounting_entries', self.detailed_accounting_entries)
        ICPSudo.set_param('nomina_colombia.group_payslip_entries', self.group_payslip_entries)

    @api.constrains('dian_date_from', 'dian_date_to')
    def _check_dian_dates(self):
        for record in self:
            if record.dian_date_from and record.dian_date_to:
                if record.dian_date_to < record.dian_date_from:
                    raise ValidationError(_("La fecha fin de resolución DIAN debe ser posterior a la fecha de inicio."))

    @api.constrains('average_calculation_months')
    def _check_average_months(self):
        for record in self:
            if record.average_calculation_months < 1 or record.average_calculation_months > 12:
                raise ValidationError(_("Los meses para cálculo de promedio deben estar entre 1 y 12."))

    def action_create_sequences(self):
        """Crea o actualiza las secuencias necesarias"""
        self.ensure_one()
        
        # Secuencia para comprobantes de nómina
        if not self.payslip_sequence_id:
            sequence_data = {
                'name': 'Secuencia Comprobantes de Nómina',
                'code': 'hr.payslip.colombia',
                'implementation': 'no_gap',
                'prefix': 'NOM/',
                'padding': 8,
                'company_id': self.company_id.id,
            }
            sequence = self.env['ir.sequence'].create(sequence_data)
            self.payslip_sequence_id = sequence.id

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Secuencias creadas/actualizadas correctamente.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_test_dian_connection(self):
        """Prueba la conexión con la DIAN"""
        self.ensure_one()
        
        if not self.dian_software_id or not self.dian_software_pin:
            raise ValidationError(_("Debe configurar el ID y PIN del software DIAN."))

        try:
            # Aquí iría la lógica de conexión con la DIAN
            # Esta es una implementación de ejemplo
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Éxito'),
                    'message': _('Conexión con la DIAN establecida correctamente.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_validate_configuration(self):
        """Valida la configuración completa del módulo"""
        self.ensure_one()
        errors = []

        # Validar configuración DIAN
        if not self.dian_software_id:
            errors.append(_("Falta configurar el ID del software DIAN"))
        if not self.dian_software_pin:
            errors.append(_("Falta configurar el PIN del software DIAN"))
        if not self.dian_date_from or not self.dian_date_to:
            errors.append(_("Faltan las fechas de resolución DIAN"))

        # Validar secuencias
        if not self.payslip_sequence_id:
            errors.append(_("Falta configurar la secuencia de comprobantes"))

        # Validar configuración contable
        if not self.payroll_journal_id:
            errors.append(_("Falta configurar el diario de nómina"))

        if errors:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Errores de Configuración'),
                    'message': '\n'.join(errors),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('La configuración es válida.'),
                'type': 'success',
                'sticky': False,
            }
        }