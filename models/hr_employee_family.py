from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re
from datetime import date


class HrEmployeeFamily(models.Model):
    _name = 'hr.employee.family'
    _description = 'Información de Familiares del Empleado'
    _order = 'relation_type, birth_date'
    _rec_name = 'complete_name'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    relation_type = fields.Selection([
        ('spouse', 'Cónyuge/Compañero(a)'),
        ('child', 'Hijo(a)'),
        ('parent', 'Padre/Madre'),
        ('sibling', 'Hermano(a)'),
        ('other', 'Otro'),
    ], string='Parentesco', required=True, tracking=True)
    
    # Información personal
    first_name = fields.Char(string='Primer Nombre', required=True, tracking=True)
    second_name = fields.Char(string='Segundo Nombre', tracking=True)
    first_surname = fields.Char(string='Primer Apellido', required=True, tracking=True)
    second_surname = fields.Char(string='Segundo Apellido', tracking=True)
    complete_name = fields.Char(string='Nombre Completo', compute='_compute_complete_name', store=True)
    
    # Identificación
    identification_type = fields.Selection([
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('RC', 'Registro Civil'),
        ('PP', 'Pasaporte'),
    ], string='Tipo de Identificación', default='CC', required=True, tracking=True)
    identification_id = fields.Char(string='Número de Identificación', required=True, tracking=True)
    
    # Información adicional
    birth_date = fields.Date(string='Fecha de Nacimiento', required=True, tracking=True)
    age = fields.Integer(string='Edad', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Masculino'),
        ('female', 'Femenino'),
        ('other', 'Otro'),
    ], string='Género', required=True, tracking=True)
    
    # Información de contacto
    phone = fields.Char(string='Teléfono', tracking=True)
    email = fields.Char(string='Correo Electrónico', tracking=True)
    
    # Información para beneficios
    is_beneficiary = fields.Boolean(string='Es Beneficiario', default=True, 
                                   help='Indica si este familiar es beneficiario de la seguridad social', tracking=True)
    is_dependent = fields.Boolean(string='Es Dependiente', default=False,
                                 help='Indica si este familiar es dependiente económico del empleado', tracking=True)
    
    # Campos específicos para hijos
    education_level = fields.Selection([
        ('none', 'Ninguno'),
        ('preschool', 'Preescolar'),
        ('primary', 'Primaria'),
        ('secondary', 'Secundaria'),
        ('technical', 'Técnico'),
        ('university', 'Universidad'),
        ('postgraduate', 'Postgrado'),
    ], string='Nivel Educativo', tracking=True)
    
    is_student = fields.Boolean(string='Es Estudiante', tracking=True)
    has_disability = fields.Boolean(string='Tiene Discapacidad', tracking=True)
    disability_certificate = fields.Char(string='Certificado de Discapacidad', tracking=True)
    
    # Campos específicos para cónyuge
    works = fields.Boolean(string='Trabaja', tracking=True)
    company_name = fields.Char(string='Empresa donde Trabaja', tracking=True)
    
    # Documentos relacionados
    document_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'hr.employee.family')],
                                  string='Documentos', help='Documentos relacionados con el familiar')
    
    # Campos para subsidio familiar
    subsidy_eligible = fields.Boolean(string='Elegible para Subsidio Familiar', compute='_compute_subsidy_eligible', store=True)
    
    @api.depends('first_name', 'second_name', 'first_surname', 'second_surname')
    def _compute_complete_name(self):
        for record in self:
            names = [name for name in [record.first_name, record.second_name] if name]
            surnames = [name for name in [record.first_surname, record.second_surname] if name]
            
            record.complete_name = ' '.join(names + surnames)
    
    @api.depends('birth_date')
    def _compute_age(self):
        today = date.today()
        for record in self:
            if record.birth_date:
                record.age = today.year - record.birth_date.year - (
                    (today.month, today.day) < (record.birth_date.month, record.birth_date.day)
                )
            else:
                record.age = 0
    
    @api.depends('relation_type', 'age', 'is_student', 'has_disability')
    def _compute_subsidy_eligible(self):
        for record in self:
            eligible = False
            
            if record.relation_type == 'spouse' and not record.works:
                eligible = True
            elif record.relation_type == 'child':
                # Menores de 18 años
                if record.age and record.age < 18:
                    eligible = True
                # Entre 18 y 23 años si estudia
                elif record.age and 18 <= record.age <= 23 and record.is_student:
                    eligible = True
                # Sin límite de edad si tiene discapacidad
                elif record.has_disability:
                    eligible = True
            
            record.subsidy_eligible = eligible
    
    @api.constrains('identification_id', 'identification_type')
    def _check_identification_id(self):
        for record in self:
            if record.identification_id:
                # Validación para Cédula de Ciudadanía (CC)
                if record.identification_type == 'CC':
                    if not re.match(r'^\d{5,10}$', record.identification_id):
                        raise ValidationError(_('La Cédula de Ciudadanía debe tener entre 5 y 10 dígitos.'))
                
                # Validación para Cédula de Extranjería (CE)
                elif record.identification_type == 'CE':
                    if not re.match(r'^[a-zA-Z0-9]{4,12}$', record.identification_id):
                        raise ValidationError(_('La Cédula de Extranjería debe tener entre 4 y 12 caracteres alfanuméricos.'))
                
                # Validación para Tarjeta de Identidad (TI)
                elif record.identification_type == 'TI':
                    if not re.match(r'^\d{10,11}$', record.identification_id):
                        raise ValidationError(_('La Tarjeta de Identidad debe tener 10 u 11 dígitos.'))
                
                # Validación para Registro Civil (RC)
                elif record.identification_type == 'RC':
                    if not re.match(r'^\d{10,11}$', record.identification_id):
                        raise ValidationError(_('El Registro Civil debe tener 10 u 11 dígitos.'))
                
                # Validación para Pasaporte (PP)
                elif record.identification_type == 'PP':
                    if not re.match(r'^[a-zA-Z0-9]{6,15}$', record.identification_id):
                        raise ValidationError(_('El Pasaporte debe tener entre 6 y 15 caracteres alfanuméricos.'))
    
    @api.constrains('relation_type', 'employee_id')
    def _check_spouse_uniqueness(self):
        for record in self:
            if record.relation_type == 'spouse':
                spouse_count = self.search_count([
                    ('employee_id', '=', record.employee_id.id),
                    ('relation_type', '=', 'spouse'),
                    ('id', '!=', record.id)
                ])
                if spouse_count > 0:
                    raise ValidationError(_('El empleado ya tiene registrado un cónyuge o compañero(a) permanente.'))
    
    @api.constrains('birth_date')
    def _check_birth_date(self):
        today = date.today()
        for record in self:
            if record.birth_date and record.birth_date > today:
                raise ValidationError(_('La fecha de nacimiento no puede ser posterior a la fecha actual.'))
    
    @api.onchange('relation_type')
    def _onchange_relation_type(self):
        if self.relation_type == 'child':
            self.is_beneficiary = True
            # Para niños, el tipo de documento más común es RC o TI dependiendo de la edad
            if self.birth_date:
                age = (date.today().year - self.birth_date.year - (
                    (date.today().month, date.today().day) < (self.birth_date.month, self.birth_date.day)
                ))
                if age < 7:
                    self.identification_type = 'RC'
                elif age < 18:
                    self.identification_type = 'TI'
        elif self.relation_type == 'spouse':
            self.is_beneficiary = True
    
    def name_get(self):
        result = []
        for record in self:
            name = record.complete_name
            if record.relation_type:
                relation_labels = dict(self._fields['relation_type'].selection)
                relation = relation_labels.get(record.relation_type)
                name = f"{name} ({relation})"
            result.append((record.id, name))
        return result
    
    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('Documentos'),
            'domain': [('res_model', '=', 'hr.employee.family'), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'context': {
                'default_res_model': 'hr.employee.family',
                'default_res_id': self.id,
            },
        }
    
    def get_document_count(self):
        for record in self:
            record.document_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'hr.employee.family'),
                ('res_id', '=', record.id)
            ])
    
    document_count = fields.Integer(compute='get_document_count', string='Número de Documentos')