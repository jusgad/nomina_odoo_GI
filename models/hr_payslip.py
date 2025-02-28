from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    # Campos específicos para Colombia
    liquidation_type = fields.Selection([
        ('normal', 'Nómina Regular'),
        ('vacation', 'Vacaciones'),
        ('prima', 'Prima de Servicios'),
        ('cesantias', 'Cesantías'),
        ('intereses_cesantias', 'Intereses de Cesantías'),
        ('final_liquidation', 'Liquidación Definitiva'),
    ], string='Tipo de Liquidación', default='normal', required=True, 
    readonly=True, states={'draft': [('readonly', False)]})

    # Campos para nómina electrónica
    electronic_payroll_id = fields.Many2one(
        'hr.electronic.payroll', string='Nómina Electrónica',
        readonly=True, copy=False)

    electronic_payroll_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('generated', 'Generada'),
        ('sent', 'Enviada'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
    ], string='Estado Nómina Electrónica', default='pending', copy=False, readonly=True)

    # Campos para PILA
    pila_id = fields.Many2one(
        'hr.pila', string='PILA',
        readonly=True, copy=False)

    pila_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('generated', 'Generada'),
        ('paid', 'Pagada'),
    ], string='Estado PILA', default='pending', copy=False, readonly=True)

    # Campos para cálculos específicos de Colombia
    worked_days = fields.Integer(
        string='Días Trabajados', compute='_compute_worked_days', store=True,
        help='Días efectivamente trabajados en el periodo')

    transport_allowance = fields.Monetary(
        string='Auxilio de Transporte', compute='_compute_transport_allowance', store=True,
        help='Valor del auxilio de transporte según la legislación colombiana')

    # Campos para incapacidades
    disability_days = fields.Integer(
        string='Días de Incapacidad', compute='_compute_disability_days', store=True,
        help='Días de incapacidad en el periodo')

    disability_value = fields.Monetary(
        string='Valor Incapacidades', compute='_compute_disability_value', store=True,
        help='Valor total de las incapacidades en el periodo')

    # Campos para licencias
    leave_days = fields.Integer(
        string='Días de Licencia', compute='_compute_leave_days', store=True,
        help='Días de licencia en el periodo')

    leave_value = fields.Monetary(
        string='Valor Licencias', compute='_compute_leave_value', store=True,
        help='Valor total de las licencias en el periodo')

    # Campos para horas extra
    overtime_hours = fields.Float(
        string='Horas Extra', compute='_compute_overtime', store=True,
        help='Total de horas extra en el periodo')

    overtime_value = fields.Monetary(
        string='Valor Horas Extra', compute='_compute_overtime', store=True,
        help='Valor total de las horas extra en el periodo')

    # Campos para vacaciones
    vacation_days = fields.Integer(
        string='Días de Vacaciones', compute='_compute_vacation_days', store=True,
        help='Días de vacaciones en el periodo')

    vacation_value = fields.Monetary(
        string='Valor Vacaciones', compute='_compute_vacation_value', store=True,
        help='Valor total de las vacaciones en el periodo')

    # Campos para prima de servicios
    prima_value = fields.Monetary(
        string='Valor Prima de Servicios', compute='_compute_prima_value', store=True,
        help='Valor de la prima de servicios')

    # Campos para cesantías
    cesantias_value = fields.Monetary(
        string='Valor Cesantías', compute='_compute_cesantias_value', store=True,
        help='Valor de las cesantías')

    intereses_cesantias_value = fields.Monetary(
        string='Valor Intereses Cesantías', compute='_compute_intereses_cesantias_value', store=True,
        help='Valor de los intereses sobre cesantías')

    # Campos para retención en la fuente
    withholding_tax = fields.Monetary(
        string='Retención en la Fuente', compute='_compute_withholding_tax', store=True,
        help='Valor de la retención en la fuente')

    # Campos para deducciones
    total_deductions = fields.Monetary(
        string='Total Deducciones', compute='_compute_total_deductions', store=True,
        help='Valor total de las deducciones')

    # Campos para aportes a seguridad social
    health_contribution_employee = fields.Monetary(
        string='Aporte Salud Empleado', compute='_compute_social_security', store=True,
        help='Aporte del empleado a salud (4%)')

    pension_contribution_employee = fields.Monetary(
        string='Aporte Pensión Empleado', compute='_compute_social_security', store=True,
        help='Aporte del empleado a pensión (4%)')

    health_contribution_company = fields.Monetary(
        string='Aporte Salud Empresa', compute='_compute_social_security', store=True,
        help='Aporte de la empresa a salud (8.5%)')

    pension_contribution_company = fields.Monetary(
        string='Aporte Pensión Empresa', compute='_compute_social_security', store=True,
        help='Aporte de la empresa a pensión (12%)')

    arl_contribution = fields.Monetary(
        string='Aporte ARL', compute='_compute_social_security', store=True,
        help='Aporte a riesgos laborales según nivel de riesgo')

    # Campos para parafiscales
    parafiscal_icbf = fields.Monetary(
        string='Aporte ICBF', compute='_compute_parafiscales', store=True,
        help='Aporte al ICBF (3%)')

    parafiscal_sena = fields.Monetary(
        string='Aporte SENA', compute='_compute_parafiscales', store=True,
        help='Aporte al SENA (2%)')

    parafiscal_caja = fields.Monetary(
        string='Aporte Caja Compensación', compute='_compute_parafiscales', store=True,
        help='Aporte a Caja de Compensación Familiar (4%)')

    # Campos para histórico de nómina
    payslip_history_ids = fields.One2many(
        'hr.payslip.history', 'payslip_id', string='Histórico de Nómina')

    # Campos para banco
    payment_method = fields.Selection([
        ('transfer', 'Transferencia Bancaria'),
        ('check', 'Cheque'),
        ('cash', 'Efectivo'),
    ], string='Método de Pago', default='transfer', required=True,
    readonly=True, states={'draft': [('readonly', False)]})

    bank_account_id = fields.Many2one(
        'res.partner.bank', string='Cuenta Bancaria',
        readonly=True, states={'draft': [('readonly', False)]},
        domain="[('partner_id', '=', employee_id.address_home_id)]")

    # Campos para dotación
    clothing_allowance_date = fields.Date(
        string='Fecha Entrega Dotación',
        help='Fecha de entrega de la dotación')

    # Campos para control de cambios
    has_modifications = fields.Boolean(
        string='Tiene Modificaciones', default=False, copy=False,
        help='Indica si la nómina ha sido modificada después de calculada')

    modification_reason = fields.Text(
        string='Motivo de Modificación', copy=False,
        help='Razón por la cual se modificó la nómina')

    # Campos para firma electrónica
    signed_by_employee = fields.Boolean(
        string='Firmado por Empleado', default=False, copy=False,
        help='Indica si el empleado ha firmado la nómina electrónicamente')

    signed_date = fields.Datetime(
        string='Fecha de Firma', copy=False,
        help='Fecha y hora en que el empleado firmó la nómina')

    # Campos para control de versiones
    version = fields.Integer(
        string='Versión', default=1, copy=False,
        help='Versión de la nómina, se incrementa con cada recálculo')

    previous_payslip_id = fields.Many2one(
        'hr.payslip', string='Nómina Anterior', copy=False,
        help='Referencia a la versión anterior de esta nómina')

    # Campos para integración con contabilidad
    move_id = fields.Many2one(
        'account.move', string='Asiento Contable', copy=False, readonly=True,
        help='Asiento contable generado por esta nómina')

    # Campos para integración con tesorería
    payment_id = fields.Many2one(
        'account.payment', string='Pago', copy=False, readonly=True,
        help='Pago generado por esta nómina')

    # Campos para control de procesos
    process_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'En Proceso'),
        ('completed', 'Completado'),
        ('error', 'Error'),
    ], string='Estado del Proceso', default='pending', copy=False, readonly=True)

    process_message = fields.Text(
        string='Mensaje del Proceso', copy=False, readonly=True,
        help='Mensaje informativo sobre el estado del proceso')

    # Campos para integración con el nuevo sistema de entradas de trabajo de v18
    work_entry_source = fields.Selection(
        selection_add=[('co_attendance', 'Asistencia Colombia')],
        readonly=True, states={'draft': [('readonly', False)]})

# Métodos computados
@api.depends('worked_days_line_ids', 'worked_days_line_ids.number_of_days')
def _compute_worked_days(self):
    for payslip in self:
        worked_days = 0
        for line in payslip.worked_days_line_ids:
            if line.work_entry_type_id.code in ['WORK100', 'CO_WORK']:
                worked_days += line.number_of_days
        payslip.worked_days = round(worked_days)

@api.depends('employee_id', 'contract_id', 'worked_days')
def _compute_transport_allowance(self):
    for payslip in self:
        if not payslip.contract_id or not payslip.worked_days:
            payslip.transport_allowance = 0.0
            continue
        
        if not payslip.contract_id.transport_allowance:
            payslip.transport_allowance = 0.0
            continue
        
        # Obtener el valor del auxilio de transporte
        transport_value = payslip.contract_id._get_transport_allowance()
        
        # Prorratear según días trabajados
        days_in_month = 30  # En Colombia se calcula sobre 30 días
        payslip.transport_allowance = transport_value * (payslip.worked_days / days_in_month)

@api.depends('worked_days_line_ids', 'worked_days_line_ids.number_of_days')
def _compute_disability_days(self):
    for payslip in self:
        disability_days = 0
        for line in payslip.worked_days_line_ids:
            if line.work_entry_type_id.code in ['LEAVE90', 'LEAVE100', 'CO_DISABILITY']:
                disability_days += line.number_of_days
        payslip.disability_days = round(disability_days)

@api.depends('line_ids', 'line_ids.total')
def _compute_disability_value(self):
    for payslip in self:
        disability_value = 0.0
        for line in payslip.line_ids:
            if line.code in ['DISABILITY', 'CO_DISABILITY']:
                disability_value += line.total
        payslip.disability_value = disability_value

@api.depends('worked_days_line_ids', 'worked_days_line_ids.number_of_days')
def _compute_leave_days(self):
    for payslip in self:
        leave_days = 0
        for line in payslip.worked_days_line_ids:
            if line.work_entry_type_id.code in ['LEAVE', 'CO_LEAVE']:
                leave_days += line.number_of_days
        payslip.leave_days = round(leave_days)

@api.depends('line_ids', 'line_ids.total')
def _compute_leave_value(self):
    for payslip in self:
        leave_value = 0.0
        for line in payslip.line_ids:
            if line.code in ['LEAVE', 'CO_LEAVE']:
                leave_value += line.total
        payslip.leave_value = leave_value

@api.depends('worked_days_line_ids', 'worked_days_line_ids.number_of_hours')
def _compute_overtime(self):
    for payslip in self:
        overtime_hours = 0.0
        overtime_value = 0.0
        
        # Horas extra
        for line in payslip.worked_days_line_ids:
            if line.work_entry_type_id.code in ['CO_OVERTIME', 'CO_OVERTIME_NIGHT', 'CO_OVERTIME_HOLIDAY']:
                overtime_hours += line.number_of_hours
        
        # Valor de horas extra
        for line in payslip.line_ids:
            if line.code in ['HEO', 'HEN', 'HEDO', 'HEDN', 'HENO', 'HENN', 'CO_OVERTIME']:
                overtime_value += line.total
                
                payslip.overtime_hours = overtime_hours
                payslip.overtime_value = overtime_value
    
    @api.depends('worked_days_line_ids', 'worked_days_line_ids.number_of_days')
    def _compute_vacation_days(self):
        for payslip in self:
            vacation_days = 0
            for line in payslip.worked_days_line_ids:
                if line.work_entry_type_id.code in ['LEAVE120', 'CO_VACATION']:
                    vacation_days += line.number_of_days
            payslip.vacation_days = round(vacation_days)
    
    @api.depends('line_ids', 'line_ids.total')
    def _compute_vacation_value(self):
        for payslip in self:
            vacation_value = 0.0
            for line in payslip.line_ids:
                if line.code in ['VACATION', 'CO_VACATION']:
                    vacation_value += line.total
            payslip.vacation_value = vacation_value
    
    @api.depends('line_ids', 'line_ids.total', 'liquidation_type')
    def _compute_prima_value(self):
        for payslip in self:
            prima_value = 0.0
            if payslip.liquidation_type == 'prima':
                for line in payslip.line_ids:
                    if line.code in ['PRIMA', 'CO_PRIMA']:
                        prima_value += line.total
            payslip.prima_value = prima_value
    
    @api.depends('line_ids', 'line_ids.total', 'liquidation_type')
    def _compute_cesantias_value(self):
        for payslip in self:
            cesantias_value = 0.0
            if payslip.liquidation_type == 'cesantias':
                for line in payslip.line_ids:
                    if line.code in ['CESANTIAS', 'CO_CESANTIAS']:
                        cesantias_value += line.total
            payslip.cesantias_value = cesantias_value
    
    @api.depends('line_ids', 'line_ids.total', 'liquidation_type')
    def _compute_intereses_cesantias_value(self):
        for payslip in self:
            intereses_value = 0.0
            if payslip.liquidation_type == 'intereses_cesantias':
                for line in payslip.line_ids:
                    if line.code in ['INT_CESANTIAS', 'CO_INT_CESANTIAS']:
                        intereses_value += line.total
            payslip.intereses_cesantias_value = intereses_value
    
    @api.depends('line_ids', 'line_ids.total')
    def _compute_withholding_tax(self):
        for payslip in self:
            withholding_tax = 0.0
            for line in payslip.line_ids:
                if line.code in ['RETENCION', 'CO_RETENCION']:
                    withholding_tax += line.total
            payslip.withholding_tax = withholding_tax
    
    @api.depends('line_ids', 'line_ids.total')
    def _compute_total_deductions(self):
        for payslip in self:
            total_deductions = 0.0
            for line in payslip.line_ids:
                if line.category_id.code == 'DED':
                    total_deductions += line.total
            payslip.total_deductions = total_deductions
    
    @api.depends('line_ids', 'line_ids.total', 'contract_id')
    def _compute_social_security(self):
        for payslip in self:
            health_employee = 0.0
            pension_employee = 0.0
            health_company = 0.0
            pension_company = 0.0
            arl = 0.0
            
            for line in payslip.line_ids:
                if line.code == 'SALUD_EMP':
                    health_employee += line.total
                elif line.code == 'PENSION_EMP':
                    pension_employee += line.total
                elif line.code == 'SALUD_EMP_EMPRESA':
                    health_company += line.total
                elif line.code == 'PENSION_EMP_EMPRESA':
                    pension_company += line.total
                elif line.code == 'ARL':
                    arl += line.total
            
            payslip.health_contribution_employee = health_employee
            payslip.pension_contribution_employee = pension_employee
            payslip.health_contribution_company = health_company
            payslip.pension_contribution_company = pension_company
            payslip.arl_contribution = arl
    
    @api.depends('line_ids', 'line_ids.total')
    def _compute_parafiscales(self):
        for payslip in self:
            icbf = 0.0
            sena = 0.0
            caja = 0.0
            
            for line in payslip.line_ids:
                if line.code == 'ICBF':
                    icbf += line.total
                elif line.code == 'SENA':
                    sena += line.total
                elif line.code == 'CCF':
                    caja += line.total
            
            payslip.parafiscal_icbf = icbf
            payslip.parafiscal_sena = sena
            payslip.parafiscal_caja = caja
    
    # Sobrescritura de métodos estándar
    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        Sobrescribe el método estándar para incluir cálculos específicos de Colombia
        """
        result = super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
        
        # Aquí podemos añadir lógica específica para Colombia
        # Por ejemplo, manejo de horas extra, incapacidades, etc.
        
        return result
    
    def _get_base_local_dict(self):
        """
        Extiende el diccionario local para las reglas salariales con funciones específicas de Colombia
        """
        res = super(HrPayslip, self)._get_base_local_dict()
        
        # Añadir funciones específicas para Colombia
        res.update({
            'calculate_overtime': self._calculate_overtime,
            'calculate_prima': self._calculate_prima,
            'calculate_cesantias': self._calculate_cesantias,
            'calculate_intereses_cesantias': self._calculate_intereses_cesantias,
            'calculate_withholding_tax': self._calculate_withholding_tax,
            'get_base_salary': self._get_base_salary,
            'get_integral_salary_base': self._get_integral_salary_base,
            'get_transport_allowance': self._get_transport_allowance,
        })
        
        return res
    
    def action_payslip_done(self):
        """
        Sobrescribe el método estándar para incluir validaciones y procesos específicos de Colombia
        """
        # Validaciones específicas para Colombia
        for payslip in self:
            if not payslip.worked_days and payslip.liquidation_type == 'normal':
                raise UserError(_("No puede confirmar una nómina sin días trabajados."))
        
        # Llamar al método original
        result = super(HrPayslip, self).action_payslip_done()
        
        # Procesos adicionales para Colombia
        for payslip in self:
            # Crear histórico
            self.env['hr.payslip.history'].create({
                'payslip_id': payslip.id,
                'employee_id': payslip.employee_id.id,
                'date': fields.Date.today(),
                'user_id': self.env.user.id,
                'action': 'confirm',
                'notes': _('Nómina confirmada'),
            })
            
            # Generar nómina electrónica si corresponde
            if payslip.company_id.electronic_payroll_enabled:
                payslip.generate_electronic_payroll()
        
        return result
    
    def action_payslip_cancel(self):
        """
        Sobrescribe el método estándar para incluir validaciones y procesos específicos de Colombia
        """
        # Validaciones específicas para Colombia
        for payslip in self:
            if payslip.electronic_payroll_status in ['sent', 'accepted']:
                raise UserError(_("No puede cancelar una nómina que ya ha sido enviada o aceptada en la DIAN."))
        
        # Llamar al método original
        result = super(HrPayslip, self).action_payslip_cancel()
        
        # Procesos adicionales para Colombia
        for payslip in self:
            # Crear histórico
            self.env['hr.payslip.history'].create({
                'payslip_id': payslip.id,
                'employee_id': payslip.employee_id.id,
                'date': fields.Date.today(),
                'user_id': self.env.user.id,
                'action': 'cancel',
                'notes': _('Nómina cancelada'),
            })
            
            # Cancelar nómina electrónica si existe
            if payslip.electronic_payroll_id:
                payslip.electronic_payroll_id.action_cancel()
                payslip.electronic_payroll_status = 'pending'
        
        return result
    
    def compute_sheet(self):
        """
        Sobrescribe el método estándar para incluir lógica específica de Colombia
        """
        # Incrementar versión si ya fue calculada antes
        for payslip in self.filtered(lambda p: p.state != 'draft'):
            payslip.version += 1
            payslip.has_modifications = True
        
        # Llamar al método original
        result = super(HrPayslip, self).compute_sheet()
        
        # Procesos adicionales para Colombia
        for payslip in self:
            # Crear histórico
            self.env['hr.payslip.history'].create({
                'payslip_id': payslip.id,
                'employee_id': payslip.employee_id.id,
                'date': fields.Date.today(),
                'user_id': self.env.user.id,
                'action': 'compute',
                'notes': _('Nómina calculada (versión %s)') % payslip.version,
            })
        
        return result
    
    # Métodos específicos para Colombia
    def _calculate_overtime(self, overtime_type, hours):
        """
        Calcula el valor de las horas extra según su tipo
        
        :param overtime_type: Tipo de hora extra (HEO, HEN, HEDO, HEDN, etc.)
        :param hours: Número de horas
        :return: Valor de las horas extra
        """
        self.ensure_one()
        
        if not self.contract_id or not hours:
            return 0.0
        
        # Valor hora ordinaria
        hourly_wage = self.contract_id.wage / 240  # 30 días * 8 horas
        
        # Factores según tipo de hora extra
        factors = {
            'HEO': 1.25,    # Hora Extra Ordinaria (25%)
            'HEN': 1.75,    # Hora Extra Nocturna (75%)
            'HEDO': 2.0,    # Hora Extra Dominical/Festivo Diurna (100%)
            'HEDN': 2.5,    # Hora Extra Dominical/Festivo Nocturna (150%)
            'HENO': 1.35,   # Hora Extra Nocturna Ordinaria (35%)
            'HENN': 2.1,    # Hora Extra Nocturna Dominical/Festivo (110%)
        }
        
        factor = factors.get(overtime_type, 1.0)
        
        return hourly_wage * hours * factor
    
    def _calculate_prima(self):
        """
        Calcula la prima de servicios
        
        :return: Valor de la prima de servicios
        """
        self.ensure_one()
        
        if not self.contract_id:
            return 0.0
        
        # Base para prima: salario + auxilio de transporte
        base = self.contract_id.wage + self._get_transport_allowance()
        
        # Días trabajados en el semestre
        # Esto es simplificado, en un caso real habría que calcular los días exactos
        days_in_semester = 180
        worked_days_in_semester = days_in_semester  # Simplificado
        
        # Cálculo de prima
        prima = (base * worked_days_in_semester) / days_in_semester / 2
        
        return prima
    
    def _calculate_cesantias(self):
        """
        Calcula las cesantías
        
        :return: Valor de las cesantías
        """
        self.ensure_one()
        
        if not self.contract_id:
            return 0.0
        
        # Base para cesantías según configuración del contrato
        if self.contract_id.severance_base == 'all':
            # Salario + todo lo constitutivo de salario
            base = self.contract_id.wage + self._get_transport_allowance()
            # Aquí se deberían sumar otros conceptos constitutivos
        elif self.contract_id.severance_base == 'wage':
            # Solo salario básico
            base = self.contract_id.wage
        else:
            # Según definición legal (salario + auxilio de transporte)
            base = self.contract_id.wage + self._get_transport_allowance()
        
        # Días trabajados en el año
        # Esto es simplificado, en un caso real habría que calcular los días exactos
        days_in_year = 360
        worked_days_in_year = days_in_year  # Simplificado
        
        # Cálculo de cesantías
        cesantias = (base * worked_days_in_year) / days_in_year
        
        return cesantias
    
    def _calculate_intereses_cesantias(self):
        """
        Calcula los intereses sobre cesantías
        
        :return: Valor de los intereses sobre cesantías
        """
        self.ensure_one()
        
        cesantias = self._calculate_cesantias()
        
        # Tasa de interés: 12% anual
        interest_rate = 0.12
        
        # Días trabajados en el año
        # Esto es simplificado, en un caso real habría que calcular los días exactos
        days_in_year = 360
        worked_days_in_year = days_in_year  # Simplificado
        
        # Cálculo de intereses
        intereses = cesantias * interest_rate * (worked_days_in_year / days_in_year)
        
        return intereses
    
    def _calculate_withholding_tax(self):
        """
        Calcula la retención en la fuente según el método configurado en el contrato
        
        :return: Valor de la retención en la fuente
        """
        self.ensure_one()
        
        if not self.contract_id:
            return 0.0
        
        # Delegar el cálculo al contrato
        return self.contract_id._compute_withholding_tax(self)
    
    def _get_base_salary(self):
        """
        Obtiene el salario base para cálculos
        
        :return: Salario base
        """
        self.ensure_one()
        
        if not self.contract_id:
            return 0.0
        
        return self.contract_id.wage
    
    def _get_integral_salary_base(self):
        """
        Obtiene la base del salario integral
        
        :return: Base del salario integral
        """
        self.ensure_one()
        
        if not self.contract_id or self.contract_id.wage_type != 'integral':
            return 0.0
        
        return self.contract_id._get_integral_base()
    
    def _get_transport_allowance(self):
        """
        Obtiene el auxilio de transporte
        
        :return: Valor del auxilio de transporte
        """
        self.ensure_one()
        
        if not self.contract_id:
            return 0.0
        
        return self.contract_id._get_transport_allowance()
    
    # Métodos para nómina electrónica
    def generate_electronic_payroll(self):
        """
        Genera el documento de nómina electrónica para la DIAN
        """
        self.ensure_one()
        
        if self.electronic_payroll_id:
            raise UserError(_("Ya existe un documento de nómina electrónica para esta nómina."))
        
        if self.state != 'done':
            raise UserError(_("Solo se puede generar nómina electrónica para nóminas confirmadas."))
        
        # Crear documento de nómina electrónica
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'payslip_id': self.id,
            'employee_id': self.employee_id.id,
            'date': self.date_to,
            'company_id': self.company_id.id,
            'state': 'draft',
        })
        
        # Asociar a la nómina
        self.electronic_payroll_id = electronic_payroll.id
        self.electronic_payroll_status = 'generated'
        
        return electronic_payroll
    
    def action_send_electronic_payroll(self):
        """
        Envía el documento de nómina electrónica a la DIAN
        """
        self.ensure_one()
        
        if not self.electronic_payroll_id:
            raise UserError(_("No existe un documento de nómina electrónica para esta nómina."))
        
        if self.electronic_payroll_status not in ['generated', 'rejected']:
            raise UserError(_("Solo se pueden enviar documentos generados o rechazados."))
        
        # Enviar a la DIAN
        result = self.electronic_payroll_id.action_send()
        
        if result:
            self.electronic_payroll_status = 'sent'
        
        return result
    
    # Métodos para PILA
    def generate_pila(self):
        """
        Genera el documento PILA
        """
        self.ensure_one()
        
        if self.pila_id:
            raise UserError(_("Ya existe un documento PILA para esta nómina."))
        
        if self.state != 'done':
            raise UserError(_("Solo se puede generar PILA para nóminas confirmadas."))
        
        # Crear documento PILA
        pila = self.env['hr.pila'].create({
            'payslip_id': self.id,
            'employee_id': self.employee_id.id,
            'date': self.date_to,
            'company_id': self.company_id.id,
            'state': 'draft',
        })
        
        # Asociar a la nómina
        self.pila_id = pila.id
        self.pila_status = 'generated'
        
        return pila
    
    # Métodos para reportes
    def action_print_payslip(self):
        """
        Imprime el comprobante de nómina
        """
        self.ensure_one()
        return self.env.ref('nomina_colombia_v18.action_report_payslip').report_action(self)
    
    def action_send_payslip_email(self):
        """
        Envía el comprobante de nómina por correo electrónico
        """
        self.ensure_one()
        
        if not self.employee_id.work_email:
            raise UserError(_("El empleado no tiene configurado un correo electrónico de trabajo."))
        
        template = self.env.ref('nomina_colombia_v18.email_template_payslip')
        
        # Enviar correo
        template.send_mail(self.id, force_send=True)
        
        # Crear histórico
        self.env['hr.payslip.history'].create({
            'payslip_id': self.id,
            'employee_id': self.employee_id.id,
            'date': fields.Date.today(),
            'user_id': self.env.user.id,
            'action': 'email',
            'notes': _('Comprobante enviado por correo electrónico'),
        })
        
        return True
    
    # Métodos para firma electrónica
    def action_sign_payslip(self):
        """
        Firma electrónicamente el comprobante de nómina
        """
        self.ensure_one()
        
        if self.signed_by_employee:
            raise UserError(_("El comprobante ya ha sido firmado."))
        
        # Aquí iría la lógica de firma electrónica
        # Por ahora simplemente marcamos como firmado
        
        self.write({
            'signed_by_employee': True,
            'signed_date': fields.Datetime.now(),
        })
        
        # Crear histórico
        self.env['hr.payslip.history'].create({
            'payslip_id': self.id,
            'employee_id': self.employee_id.id,
            'date': fields.Date.today(),
            'user_id': self.env.user.id,
            'action': 'sign',
            'notes': _('Comprobante firmado electrónicamente'),
        })
        
        return True
    
    # Métodos para integración con contabilidad
    def action_create_accounting_entry(self):
        """
        Crea el asiento contable de la nómina
        """
        self.ensure_one()
        
        if self.move_id:
            raise UserError(_("Ya existe un asiento contable para esta nómina."))
        
        if self.state != 'done':
            raise UserError(_("Solo se puede contabilizar nóminas confirmadas."))
        
        # Aquí iría la lógica para crear el asiento contable
        # Este es un ejemplo simplificado
        
        move_vals = {
            'ref': _('Nómina: %s') % self.number,
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'line_ids': [],
        }
        
        # Líneas del asiento (simplificado)
        # En un caso real, habría que detallar todas las cuentas
        
        # Crear el asiento
        move = self.env['account.move'].create(move_vals)
        
        # Asociar a la nómina
        self.move_id = move.id
        
        # Crear histórico
        self.env['hr.payslip.history'].create({
            'payslip_id': self.id,
            'employee_id': self.employee_id.id,
            'date': fields.Date.today(),
            'user_id': self.env.user.id,
            'action': 'accounting',
            'notes': _('Asiento contable creado'),
        })
        
        return move
    
    # Métodos para integración con tesorería
    def action_create_payment(self):
        """
        Crea el pago de la nómina
        """
        self.ensure_one()
        
        if self.payment_id:
            raise UserError(_("Ya existe un pago para esta nómina."))
        
        if self.state != 'done':
            raise UserError(_("Solo se puede pagar nóminas confirmadas."))
        
        if not self.bank_account_id and self.payment_method == 'transfer':
            raise UserError(_("Debe configurar una cuenta bancaria para el pago por transferencia."))
        
        # Aquí iría la lógica para crear el pago
        # Este es un ejemplo simplificado
        
        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.employee_id.address_home_id.id,
            'amount': self.net,
            'journal_id': self.journal_id.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            'ref': _('Nómina: %s') % self.number,
        }
        
        # Crear el pago
        payment = self.env['account.payment'].create(payment_vals)
        
        # Asociar a la nómina
        self.payment_id = payment.id
        
        # Crear histórico
        self.env['hr.payslip.history'].create({
            'payslip_id': self.id,
            'employee_id': self.employee_id.id,
            'date': fields.Date.today(),
            'user_id': self.env.user.id,
            'action': 'payment',
            'notes': _('Pago creado'),
        })
        
        return payment
    
    # Métodos para liquidación definitiva
    def action_final_liquidation(self):
        """
        Realiza la liquidación definitiva del empleado
        """
        self.ensure_one()
        
        if self.liquidation_type != 'final_liquidation':
            raise UserError(_("Esta nómina no es de tipo liquidación definitiva."))
        
        if self.state != 'draft':
            raise UserError(_("Solo se puede realizar la liquidación definitiva en estado borrador."))
        
        # Aquí iría la lógica para calcular la liquidación definitiva
        # Incluiría cesantías, intereses, prima, vacaciones, indemnización, etc.
        
        # Calcular la nómina
        self.compute_sheet()
        
        return True
    
    # Métodos para dotación
    def action_register_clothing_allowance(self):
        """
        Registra la entrega de dotación
        """
        self.ensure_one()
        
        if not self.contract_id.clothing_allowance:
            raise UserError(_("Este empleado no tiene derecho a dotación según su contrato."))
        
        # Formulario para registrar la dotación
        return {
            'name': _('Registrar Dotación'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.clothing.allowance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_date': fields.Date.today(),
            }
        }


class HrPayslipHistory(models.Model):
    _name = 'hr.payslip.history'
    _description = 'Histórico de Nómina'
    _order = 'date desc, id desc'
    
    payslip_id = fields.Many2one('hr.payslip', string='Nómina', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    date = fields.Date(string='Fecha', required=True, default=fields.Date.today)
    user_id = fields.Many2one('res.users', string='Usuario', required=True, default=lambda self: self.env.user.id)
    action = fields.Selection([
        ('create', 'Creación'),
        ('compute', 'Cálculo'),
        ('confirm', 'Confirmación'),
        ('cancel', 'Cancelación'),
        ('email', 'Envío por Email'),
        ('sign', 'Firma'),
        ('accounting', 'Contabilización'),
        ('payment', 'Pago'),
        ('other', 'Otro'),
    ], string='Acción', required=True)
    notes = fields.Text(string='Observaciones')
    
    # Campos relacionados
    company_id = fields.Many2one(related='payslip_id.company_id')
    payslip_number = fields.Char(related='payslip_id.number', string='Número de Nómina')
    payslip_state = fields.Selection(related='payslip_id.state', string='Estado de Nómina')