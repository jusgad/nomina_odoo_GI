from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Campos específicos para Colombia
    identification_type = fields.Selection([
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PP', 'Pasaporte'),
        ('NIT', 'NIT'),
    ], string='Tipo de Identificación', default='CC', required=True, tracking=True)
    
    identification_id = fields.Char(string='Número de Identificación', copy=False, tracking=True)
    expedition_date = fields.Date(string='Fecha de Expedición', tracking=True)
    expedition_place_id = fields.Many2one('res.city', string='Lugar de Expedición', tracking=True)
    
    # Campos para seguridad social
    eps_id = fields.Many2one('res.partner', string='EPS', domain=[('eps', '=', True)], tracking=True)
    pension_fund_id = fields.Many2one('res.partner', string='Fondo de Pensiones', domain=[('pension_fund', '=', True)], tracking=True)
    severance_fund_id = fields.Many2one('res.partner', string='Fondo de Cesantías', domain=[('severance_fund', '=', True)], tracking=True)
    arl_id = fields.Many2one('res.partner', string='ARL', domain=[('arl', '=', True)], tracking=True)
    arl_risk = fields.Selection([
        ('1', 'I - Riesgo Mínimo (0.522%)'),
        ('2', 'II - Riesgo Bajo (1.044%)'),
        ('3', 'III - Riesgo Medio (2.436%)'),
        ('4', 'IV - Riesgo Alto (4.350%)'),
        ('5', 'V - Riesgo Máximo (6.960%)'),
    ], string='Nivel de Riesgo ARL', default='1', tracking=True)
    
    # Información bancaria
    bank_account_id = fields.Many2one('res.partner.bank', string='Cuenta Bancaria', tracking=True)
    account_type = fields.Selection([
        ('savings', 'Ahorros'),
        ('current', 'Corriente'),
    ], string='Tipo de Cuenta', default='savings', tracking=True)
    
    # Información familiar
    family_ids = fields.One2many('hr.employee.family', 'employee_id', string='Familiares')
    
    # Campos adicionales
    first_name = fields.Char(string='Primer Nombre', tracking=True)
    second_name = fields.Char(string='Segundo Nombre', tracking=True)
    first_surname = fields.Char(string='Primer Apellido', tracking=True)
    second_surname = fields.Char(string='Segundo Apellido', tracking=True)
    
    # Campos para nómina electrónica
    electronic_payroll_code = fields.Char(string='Código para Nómina Electrónica', copy=False)
    
    # Campos para PILA
    pila_code = fields.Char(string='Código PILA', copy=False)
    pila_sub_type = fields.Selection([
        ('00', 'No Aplica'),
        ('01', 'Dependiente'),
        ('02', 'Servicio Doméstico'),
        ('03', 'Independiente'),
        ('04', 'Madre Comunitaria'),
        ('12', 'Aprendices en etapa lectiva'),
        ('19', 'Aprendices en etapa productiva'),
        ('22', 'Profesor de establecimiento particular'),
    ], string='Subtipo Cotizante PILA', default='01', tracking=True)
    
    # Campos adicionales para Colombia
    work_permit = fields.Boolean(string='Requiere Permiso de Trabajo', default=False, tracking=True)
    work_permit_number = fields.Char(string='Número de Permiso de Trabajo', tracking=True)
    work_permit_expiry = fields.Date(string='Fecha de Vencimiento del Permiso', tracking=True)
    
    # Campos para subsidio de transporte
    transport_subsidy = fields.Boolean(string='Aplica Subsidio de Transporte', default=True, tracking=True)
    
    # Campos para dotación
    clothing_allowance = fields.Boolean(string='Aplica Dotación', default=True, tracking=True)
    
    @api.constrains('identification_id', 'identification_type')
    def _check_identification_id(self):
        for employee in self:
            if employee.identification_id:
                # Validación para Cédula de Ciudadanía (CC)
                if employee.identification_type == 'CC':
                    if not re.match(r'^\d{5,10}$', employee.identification_id):
                        raise ValidationError(_('La Cédula de Ciudadanía debe tener entre 5 y 10 dígitos.'))
                
                # Validación para Cédula de Extranjería (CE)
                elif employee.identification_type == 'CE':
                    if not re.match(r'^[a-zA-Z0-9]{4,12}$', employee.identification_id):
                        raise ValidationError(_('La Cédula de Extranjería debe tener entre 4 y 12 caracteres alfanuméricos.'))
                
                # Validación para Tarjeta de Identidad (TI)
                elif employee.identification_type == 'TI':
                    if not re.match(r'^\d{10,11}$', employee.identification_id):
                        raise ValidationError(_('La Tarjeta de Identidad debe tener 10 u 11 dígitos.'))
                
                # Validación para Pasaporte (PP)
                elif employee.identification_type == 'PP':
                    if not re.match(r'^[a-zA-Z0-9]{6,15}$', employee.identification_id):
                        raise ValidationError(_('El Pasaporte debe tener entre 6 y 15 caracteres alfanuméricos.'))
                
                # Validación para NIT
                elif employee.identification_type == 'NIT':
                    # Eliminar guiones y espacios para la validación
                    nit_clean = re.sub(r'[-\s]', '', employee.identification_id)
                    
                    # Verificar formato básico: 9 dígitos + dígito de verificación
                    if not re.match(r'^\d{9,10}$', nit_clean):
                        raise ValidationError(_('El NIT debe tener 9 dígitos más un dígito de verificación (formato: XXXXXXXXX-Y).'))
                    
                    # Si tiene 10 dígitos, verificar que el último sea el dígito de verificación correcto
                    if len(nit_clean) == 10:
                        nit_digits = nit_clean[:9]
                        check_digit = int(nit_clean[9])
                        
                        # Algoritmo para calcular el dígito de verificación del NIT colombiano
                        factors = [3, 7, 13, 17, 19, 23, 29, 37, 41]
                        sum_product = sum(int(digit) * factor for digit, factor in zip(nit_digits, factors))
                        calculated_check = (sum_product % 11)
                        
                        if calculated_check >= 2:
                            calculated_check = 11 - calculated_check
                            
                        if check_digit != calculated_check:
                            raise ValidationError(_('El dígito de verificación del NIT es incorrecto.'))
    
    @api.constrains('work_permit', 'work_permit_number', 'work_permit_expiry')
    def _check_work_permit(self):
        for employee in self:
            if employee.work_permit and not employee.work_permit_number:
                raise ValidationError(_('Debe ingresar el número de permiso de trabajo.'))
            if employee.work_permit and not employee.work_permit_expiry:
                raise ValidationError(_('Debe ingresar la fecha de vencimiento del permiso de trabajo.'))
    
    @api.onchange('first_name', 'second_name', 'first_surname', 'second_surname')
    def _onchange_names(self):
        """Actualiza el nombre completo cuando cambian los componentes del nombre"""
        names = [name for name in [self.first_name, self.second_name] if name]
        surnames = [name for name in [self.first_surname, self.second_surname] if name]
        
        full_name = ' '.join(names + surnames)
        if full_name:
            self.name = full_name
    
    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribe el método create para formatear el nombre completo"""
        for vals in vals_list:
            if not vals.get('name') and any(key in vals for key in ['first_name', 'second_name', 'first_surname', 'second_surname']):
                names = [vals.get(key, '') for key in ['first_name', 'second_name']]
                surnames = [vals.get(key, '') for key in ['first_surname', 'second_surname']]
                
                names = [name for name in names if name]
                surnames = [name for name in surnames if name]
                
                vals['name'] = ' '.join(names + surnames)
        
        return super(HrEmployee, self).create(vals_list)
    
    def write(self, vals):
        """Sobrescribe el método write para formatear el nombre completo"""
        result = super(HrEmployee, self).write(vals)
        
        # Si se modificaron los componentes del nombre pero no el nombre completo
        if any(key in vals for key in ['first_name', 'second_name', 'first_surname', 'second_surname']) and 'name' not in vals:
            for employee in self:
                names = [getattr(employee, key, '') for key in ['first_name', 'second_name']]
                surnames = [getattr(employee, key, '') for key in ['first_surname', 'second_surname']]
                
                names = [name for name in names if name]
                surnames = [name for name in surnames if name]
                
                full_name = ' '.join(names + surnames)
                if full_name:
                    employee.name = full_name
        
        return result
    
    def _get_employee_work_entries_values(self, date_start, date_stop):
        """Sobrescribe el método para incluir lógica específica de Colombia en las entradas de trabajo"""
        # Este método es nuevo en Odoo v18 y se utiliza para el cálculo de nómina basado en entradas de trabajo
        vals_list = super(HrEmployee, self)._get_employee_work_entries_values(date_start, date_stop)
        
        # Aquí se puede añadir lógica específica para Colombia
        # Por ejemplo, manejo de incapacidades, licencias, etc.
        
        return vals_list
    
    def generate_electronic_payroll_code(self):
        """Genera un código único para la nómina electrónica"""
        for employee in self:
            if not employee.electronic_payroll_code:
                # Generar un código basado en el tipo y número de identificación
                id_type = employee.identification_type
                id_number = employee.identification_id
                if id_type and id_number:
                    employee.electronic_payroll_code = f"{id_type}-{id_number}"
    
    def generate_pila_code(self):
        """Genera un código único para PILA"""
        for employee in self:
            if not employee.pila_code:
                # Generar un código basado en el tipo y número de identificación
                id_type = employee.identification_type
                id_number = employee.identification_id
                if id_type and id_number:
                    employee.pila_code = f"{id_type}{id_number}"