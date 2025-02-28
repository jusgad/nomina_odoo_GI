from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Campos específicos para contratos colombianos
contract_type_id = fields.Many2one(
    'hr.contract.type', string='Tipo de Contrato',
    tracking=True, help='Tipo de contrato según la legislación colombiana')

# Término del contrato
contract_term = fields.Selection([
    ('fijo', 'Término Fijo'),
    ('indefinido', 'Término Indefinido'),
    ('obra_labor', 'Obra o Labor'),
    ('aprendizaje', 'Aprendizaje'),
    ('practicas', 'Prácticas'),
], string='Término del Contrato', default='indefinido', required=True, tracking=True)

# Duración en meses (para contratos a término fijo)
duration_months = fields.Integer(
    string='Duración (Meses)', 
    tracking=True,
    help='Duración del contrato en meses (solo para contratos a término fijo)')

# Campos para prórrogas
has_extension = fields.Boolean(string='Tiene Prórroga', tracking=True)
extension_count = fields.Integer(string='Número de Prórrogas', default=0, tracking=True)
extension_date = fields.Date(string='Fecha de Prórroga', tracking=True)

# Periodo de prueba
trial_period_months = fields.Integer(
    string='Periodo de Prueba (Meses)', 
    default=2,
    tracking=True,
    help='Duración del periodo de prueba en meses')
trial_date_end = fields.Date(
    string='Fin del Periodo de Prueba', 
    compute='_compute_trial_date_end', 
    store=True,
    tracking=True)

# Campos para salario
wage_type = fields.Selection([
    ('integral', 'Salario Integral'),
    ('ordinary', 'Salario Ordinario'),
], string='Tipo de Salario', default='ordinary', required=True, tracking=True)

integral_factor = fields.Float(
    string='Factor Salarial Integral', 
    default=70.0,
    help='Porcentaje del salario que corresponde a la parte fija (mínimo 70%)',
    tracking=True)

# Campos para subsidios y beneficios
transport_allowance = fields.Boolean(
    string='Auxilio de Transporte', 
    default=True,
    tracking=True,
    help='Indica si el empleado tiene derecho al auxilio de transporte')

food_allowance = fields.Monetary(
    string='Auxilio de Alimentación', 
    default=0.0,
    tracking=True,
    help='Valor mensual del auxilio de alimentación')

# Campos para deducciones voluntarias
voluntary_pension = fields.Monetary(
    string='Pensión Voluntaria', 
    default=0.0,
    tracking=True,
    help='Aporte mensual a pensión voluntaria')

voluntary_afc = fields.Monetary(
    string='Ahorro AFC', 
    default=0.0,
    tracking=True,
    help='Aporte mensual a cuenta AFC')

# Campos para retención en la fuente
withholding_method = fields.Selection([
    ('fixed', 'Fijo'),
    ('table', 'Tabla'),
    ('percentage', 'Porcentaje'),
    ('none', 'No Aplica'),
], string='Método de Retención', default='table', required=True, tracking=True)

withholding_percentage = fields.Float(
    string='Porcentaje de Retención', 
    default=0.0,
    tracking=True,
    help='Porcentaje de retención en la fuente (si el método es porcentaje)')

withholding_fixed = fields.Monetary(
    string='Valor Fijo de Retención', 
    default=0.0,
    tracking=True,
    help='Valor fijo de retención en la fuente (si el método es fijo)')

# Campos para procedimiento 1 o 2 de retención
withholding_procedure = fields.Selection([
    ('1', 'Procedimiento 1'),
    ('2', 'Procedimiento 2'),
], string='Procedimiento de Retención', default='2', tracking=True)

# Campos para exenciones de retención
exempt_income_percentage = fields.Float(
    string='Porcentaje de Renta Exenta', 
    default=25.0,
    tracking=True,
    help='Porcentaje de salario considerado como renta exenta (máximo 25%)')

dependents = fields.Boolean(
    string='Tiene Dependientes', 
    default=False,
    tracking=True,
    help='Indica si el empleado tiene dependientes para efectos de retención')

# Campos para horas extra y recargos
has_overtime = fields.Boolean(
    string='Maneja Horas Extra', 
    default=True,
    tracking=True,
    help='Indica si el contrato permite el pago de horas extra')

# Campos para liquidación
severance_base = fields.Selection([
    ('all', 'Salario + Todo lo Constitutivo'),
    ('wage', 'Solo Salario Básico'),
    ('legal', 'Según Definición Legal'),
], string='Base para Cesantías', default='legal', required=True, tracking=True)

# Campos para vacaciones
vacation_days = fields.Integer(
    string='Días de Vacaciones por Año', 
    default=15,
    tracking=True,
    help='Días de vacaciones a los que tiene derecho por año')

# Campos para nómina electrónica
electronic_payroll_code = fields.Char(
    string='Código para Nómina Electrónica', 
    copy=False,
    tracking=True)

# Campos para dotación
clothing_allowance = fields.Boolean(
    string='Derecho a Dotación', 
    default=True,
    tracking=True,
    help='Indica si el empleado tiene derecho a dotación')

# Campos para jornada laboral
schedule_pay = fields.Selection(
    selection_add=[('biweekly', 'Quincenal')],
    default='monthly',
    tracking=True)

work_hours_per_day = fields.Float(
    string='Horas de Trabajo por Día', 
    default=8.0,
    tracking=True,
    help='Número de horas de trabajo por día')

# Campos para estructura salarial
struct_id = fields.Many2one(
    'hr.payroll.structure', 
    string='Estructura Salarial',
    tracking=True,
    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

# Campos para riesgos laborales
risk_level = fields.Selection([
    ('1', 'I - Riesgo Mínimo (0.522%)'),
    ('2', 'II - Riesgo Bajo (1.044%)'),
    ('3', 'III - Riesgo Medio (2.436%)'),
    ('4', 'IV - Riesgo Alto (4.350%)'),
    ('5', 'V - Riesgo Máximo (6.960%)'),
], string='Nivel de Riesgo ARL', default='1', tracking=True)

# Campos para firma del contrato
signed_contract = fields.Boolean(string='Contrato Firmado', default=False, tracking=True)
signed_date = fields.Date(string='Fecha de Firma', tracking=True)

# Campos para documentos relacionados
document_ids = fields.One2many(
    'ir.attachment', 
    'res_id', 
    domain=[('res_model', '=', 'hr.contract')],
    string='Documentos', 
    help='Documentos relacionados con el contrato')

document_count = fields.Integer(
    compute='_compute_document_count', 
    string='Número de Documentos')

# Campos para historial de cambios salariales
wage_history_ids = fields.One2many(
    'hr.contract.wage.history', 
    'contract_id', 
    string='Historial de Salarios')

# Campos para integración con work entries (nuevo en v18)
work_entry_source = fields.Selection(
    selection_add=[('co_attendance', 'Asistencia Colombia')],
    tracking=True)

# Campos para manejo de incapacidades
disability_deduction = fields.Selection([
    ('company', 'Asume la Empresa'),
    ('eps', 'Asume la EPS'),
    ('mixed', 'Mixto según normativa'),
], string='Deducción por Incapacidad', default='mixed', tracking=True)

# Campos para manejo de licencias
maternity_leave_days = fields.Integer(
    string='Días de Licencia de Maternidad', 
    default=126,
    tracking=True,
    help='Días de licencia de maternidad según la ley colombiana')

paternity_leave_days = fields.Integer(
    string='Días de Licencia de Paternidad', 
    default=8,
    tracking=True,
    help='Días de licencia de paternidad según la ley colombiana')

# Métodos computados
@api.depends('date_start', 'trial_period_months')
def _compute_trial_date_end(self):
    for contract in self:
        if contract.date_start and contract.trial_period_months:
            contract.trial_date_end = contract.date_start + relativedelta(months=contract.trial_period_months)
        else:
            contract.trial_date_end = False

def _compute_document_count(self):
    for contract in self:
        contract.document_count = self.env['ir.attachment'].search_count([
            ('res_model', '=', 'hr.contract'),
            ('res_id', '=', contract.id)
        ])

# Restricciones y validaciones
@api.constrains('wage', 'wage_type', 'integral_factor')
def _check_wage(self):
    for contract in self:
        if contract.wage_type == 'integral':
            # Verificar que el salario integral sea al menos 10 SMMLV
            min_wage = self.env['ir.config_parameter'].sudo().get_param('hr_payroll.minimum_wage', 1000000)
            min_wage_float = float(min_wage)
            if contract.wage < (min_wage_float * 10):
                raise ValidationError(_('El salario integral debe ser al menos 10 veces el salario mínimo.'))
            
            # Verificar que el factor integral sea al menos 70%
            if contract.integral_factor < 70.0:
                raise ValidationError(_('El factor salarial integral no puede ser menor al 70%.'))

@api.constrains('contract_term', 'duration_months')
def _check_contract_term(self):
    for contract in self:
        if contract.contract_term == 'fijo' and not contract.duration_months:
            raise ValidationError(_('Para contratos a término fijo, debe especificar la duración en meses.'))
        
        if contract.contract_term == 'fijo' and contract.duration_months > 36:
            raise ValidationError(_('Los contratos a término fijo no pueden exceder 3 años (36 meses).'))

@api.constrains('trial_period_months')
def _check_trial_period(self):
    for contract in self:
        if contract.trial_period_months > 2 and contract.contract_term != 'indefinido':
            raise ValidationError(_('El periodo de prueba no puede exceder 2 meses para contratos diferentes a término indefinido.'))
        
        if contract.trial_period_months > 5:
            raise ValidationError(_('El periodo de prueba no puede exceder 5 meses.'))

@api.constrains('exempt_income_percentage')
def _check_exempt_income(self):
    for contract in self:
        if contract.exempt_income_percentage > 25.0:
            raise ValidationError(_('El porcentaje de renta exenta no puede exceder el 25%.'))

# Métodos onchange
@api.onchange('contract_term')
def _onchange_contract_term(self):
    if self.contract_term == 'indefinido':
        self.duration_months = 0
    elif self.contract_term == 'fijo' and not self.duration_months:
        self.duration_months = 12
    
    if self.contract_term == 'aprendizaje':
        self.trial_period_months = 0
        # Buscar estructura salarial para aprendices
        apprentice_structure = self.env['hr.payroll.structure'].search([
            ('code', '=', 'APRENDIZ'),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
        ], limit=1)
        if apprentice_structure:
            self.struct_id = apprentice_structure.id

@api.onchange('wage_type')
def _onchange_wage_type(self):
    if self.wage_type == 'integral':
        # Buscar estructura salarial para salario integral
        integral_structure = self.env['hr.payroll.structure'].search([
            ('code', '=', 'INTEGRAL'),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
        ], limit=1)
        if integral_structure:
            self.struct_id = integral_structure.id
    else:
        # Buscar estructura salarial para salario ordinario
        ordinary_structure = self.env['hr.payroll.structure'].search([
            ('code', '=', 'ORDINARIO'),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
        ], limit=1)
        if ordinary_structure:
            self.struct_id = ordinary_structure.id

@api.onchange('employee_id')
def _onchange_employee_id(self):
    super(HrContract, self)._onchange_employee_id()
    if self.employee_id and self.employee_id.arl_risk:
        self.risk_level = self.employee_id.arl_risk
        self.risk_level = self.employee_id.arl_risk
    
    # Métodos para prórrogas de contrato
    def action_extend_contract(self):
        """Extiende un contrato a término fijo"""
        self.ensure_one()
        if self.contract_term != 'fijo':
            raise UserError(_('Solo se pueden prorrogar contratos a término fijo.'))
        
        if not self.date_end:
            raise UserError(_('El contrato debe tener una fecha de finalización para poder prorrogarlo.'))
        
        # Formulario para prórroga
        return {
            'name': _('Prorrogar Contrato'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract.extend.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_id': self.id,
                'default_current_end_date': self.date_end,
            }
        }
    
    def extend_contract(self, extension_months, extension_date=None):
        """Extiende el contrato por un número específico de meses"""
        self.ensure_one()
        if not extension_date:
            extension_date = self.date_end
        
        if extension_date < date.today():
            raise UserError(_('La fecha de prórroga no puede ser anterior a la fecha actual.'))
        
        # Calcular nueva fecha de finalización
        new_end_date = extension_date + relativedelta(months=extension_months)
        
        # Actualizar contrato
        self.write({
            'date_end': new_end_date,
            'has_extension': True,
            'extension_count': self.extension_count + 1,
            'extension_date': extension_date,
        })
        
        # Crear entrada en el historial de prórrogas
        self.env['hr.contract.extension.history'].create({
            'contract_id': self.id,
            'extension_date': extension_date,
            'previous_end_date': self.date_end,
            'new_end_date': new_end_date,
            'extension_months': extension_months,
        })
        
        # Mensaje de éxito
        message = _(
            'Contrato prorrogado por %s meses. '
            'Nueva fecha de finalización: %s. '
            'Esta es la prórroga número %s.'
        ) % (extension_months, new_end_date, self.extension_count)
        
        self.message_post(body=message)
        
        return True
    
    # Métodos para historial de salarios
    def _track_wage_changes(self, vals):
        """Registra cambios en el salario"""
        if 'wage' in vals and self.wage != vals['wage']:
            self.env['hr.contract.wage.history'].create({
                'contract_id': self.id,
                'employee_id': self.employee_id.id,
                'previous_wage': self.wage,
                'new_wage': vals['wage'],
                'change_date': fields.Date.today(),
                'change_reason': 'manual',  # Por defecto, cambio manual
            })
    
    def write(self, vals):
        """Sobrescribe el método write para registrar cambios en el salario"""
        if 'wage' in vals:
            for contract in self:
                if contract.wage != vals['wage']:
                    contract._track_wage_changes(vals)
        
        return super(HrContract, self).write(vals)
    
    # Métodos para documentos
    def action_view_documents(self):
        """Acción para ver los documentos relacionados con el contrato"""
        self.ensure_one()
        return {
            'name': _('Documentos del Contrato'),
            'domain': [('res_model', '=', 'hr.contract'), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'context': {
                'default_res_model': 'hr.contract',
                'default_res_id': self.id,
            },
        }
    
    # Métodos para generación de documentos
    def action_print_contract(self):
        """Imprime el contrato en formato PDF"""
        self.ensure_one()
        return self.env.ref('nomina_colombia_v18.action_report_hr_contract').report_action(self)
    
    # Métodos para cálculos específicos de nómina colombiana
    def _get_transport_allowance(self):
        """Calcula el auxilio de transporte según la normativa colombiana"""
        self.ensure_one()
        if not self.transport_allowance:
            return 0.0
        
        # Obtener el valor del auxilio de transporte de los parámetros del sistema
        transport_value = float(self.env['ir.config_parameter'].sudo().get_param(
            'hr_payroll.transport_allowance', 0.0))
        
        # Verificar si aplica según el salario (2 SMMLV)
        min_wage = float(self.env['ir.config_parameter'].sudo().get_param(
            'hr_payroll.minimum_wage', 0.0))
        
        if self.wage > (min_wage * 2):
            return 0.0
        
        return transport_value
    
    def _get_integral_base(self):
        """Calcula la base del salario integral"""
        self.ensure_one()
        if self.wage_type != 'integral':
            return 0.0
        
        return self.wage * (self.integral_factor / 100.0)
    
    def _get_integral_factor_value(self):
        """Calcula el valor del factor prestacional del salario integral"""
        self.ensure_one()
        if self.wage_type != 'integral':
            return 0.0
        
        return self.wage * ((100.0 - self.integral_factor) / 100.0)
    
    # Métodos para integración con el nuevo sistema de entradas de trabajo de v18
    def _get_work_hours_per_day(self):
        """Retorna las horas de trabajo por día según el contrato"""
        self.ensure_one()
        return self.work_hours_per_day or 8.0
    
    def _get_work_days_per_week(self):
        """Retorna los días de trabajo por semana según el contrato"""
        self.ensure_one()
        # Por defecto en Colombia son 48 horas semanales (6 días)
        return 6.0
    
    # Métodos para cálculo de retención en la fuente
    def _compute_withholding_tax(self, payslip):
        """Calcula la retención en la fuente según el método configurado"""
        self.ensure_one()
        
        if self.withholding_method == 'none':
            return 0.0
        
        if self.withholding_method == 'fixed':
            return self.withholding_fixed
        
        if self.withholding_method == 'percentage':
            # Base: Total de ingresos gravables
            taxable_income = sum(line.total for line in payslip.line_ids if line.category_id.code == 'GROSS')
            return taxable_income * (self.withholding_percentage / 100.0)
        
        if self.withholding_method == 'table':
            # Implementar cálculo según tabla de retención
            # Este es un cálculo complejo que depende de varios factores
            # Se implementará en un método separado
            return self._compute_withholding_tax_table(payslip)
        
        return 0.0
    
    def _compute_withholding_tax_table(self, payslip):
        """Calcula la retención en la fuente según la tabla de retención"""
        # Este método implementará el cálculo completo según la normativa colombiana
        # Incluirá el procedimiento 1 o 2 según la configuración
        # Por ahora retornamos 0 como placeholder
        return 0.0
    
    # Métodos para nómina electrónica
    def generate_electronic_payroll_code(self):
        """Genera un código único para la nómina electrónica"""
        for contract in self:
            if not contract.electronic_payroll_code:
                # Generar un código basado en el empleado y la fecha
                employee = contract.employee_id
                if employee and employee.identification_id:
                    contract.electronic_payroll_code = f"CONT-{employee.identification_type}-{employee.identification_id}-{contract.date_start.strftime('%Y%m%d')}"
    
    # Métodos para manejo de estados del contrato (adaptados a v18)
    def _track_subtype(self, init_values):
        """Sobrescribe el método para trackear cambios en el estado del contrato"""
        self.ensure_one()
        if 'state' in init_values and self.state == 'open' and init_values['state'] == 'draft':
            return self.env.ref('hr_contract.mt_contract_pending')
        elif 'state' in init_values and self.state == 'close' and init_values['state'] in ['draft', 'open']:
            return self.env.ref('hr_contract.mt_contract_close')
        return super(HrContract, self)._track_subtype(init_values)


class HrContractWageHistory(models.Model):
    _name = 'hr.contract.wage.history'
    _description = 'Historial de Cambios Salariales'
    _order = 'change_date desc, id desc'
    
    contract_id = fields.Many2one('hr.contract', string='Contrato', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    previous_wage = fields.Monetary(string='Salario Anterior', required=True)
    new_wage = fields.Monetary(string='Nuevo Salario', required=True)
    change_date = fields.Date(string='Fecha de Cambio', required=True, default=fields.Date.today)
    change_reason = fields.Selection([
        ('manual', 'Cambio Manual'),
        ('promotion', 'Promoción'),
        ('adjustment', 'Ajuste Salarial'),
        ('legal', 'Incremento Legal'),
        ('other', 'Otro'),
    ], string='Motivo del Cambio', default='manual', required=True)
    notes = fields.Text(string='Observaciones')
    
    # Campos relacionados
    company_id = fields.Many2one(related='contract_id.company_id')
    currency_id = fields.Many2one(related='contract_id.currency_id')
    
    # Campos computados
    percentage_change = fields.Float(string='Porcentaje de Cambio (%)', compute='_compute_percentage_change', store=True)
    
    @api.depends('previous_wage', 'new_wage')
    def _compute_percentage_change(self):
        for record in self:
            if record.previous_wage:
                record.percentage_change = ((record.new_wage - record.previous_wage) / record.previous_wage) * 100
            else:
                record.percentage_change = 0.0


class HrContractExtensionHistory(models.Model):
    _name = 'hr.contract.extension.history'
    _description = 'Historial de Prórrogas de Contrato'
    _order = 'extension_date desc, id desc'
    
    contract_id = fields.Many2one('hr.contract', string='Contrato', required=True, ondelete='cascade')
    extension_date = fields.Date(string='Fecha de Prórroga', required=True)
    previous_end_date = fields.Date(string='Fecha de Finalización Anterior', required=True)
    new_end_date = fields.Date(string='Nueva Fecha de Finalización', required=True)
    extension_months = fields.Integer(string='Duración de Prórroga (Meses)', required=True)
    notes = fields.Text(string='Observaciones')
    
    # Campos relacionados
    employee_id = fields.Many2one(related='contract_id.employee_id', string='Empleado')
    company_id = fields.Many2one(related='contract_id.company_id')
