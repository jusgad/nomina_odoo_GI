# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import csv
import io

class ImportEmployeeWizard(models.TransientModel):
    _name = 'hr.employee.import.wizard'
    _description = 'Asistente de Importación de Empleados'

    file = fields.Binary(
        string='Archivo CSV',
        required=True
    )
    filename = fields.Char(
        string='Nombre del archivo'
    )
    
    delimiter = fields.Selection([
        (',', 'Coma (,)'),
        (';', 'Punto y coma (;)'),
        ('|', 'Pleca (|)')
    ], string='Delimitador', default=',', required=True)

    encoding = fields.Selection([
        ('utf-8', 'UTF-8'),
        ('iso-8859-1', 'ISO-8859-1'),
        ('ascii', 'ASCII')
    ], string='Codificación', default='utf-8', required=True)

    def action_import(self):
        """Importa empleados desde archivo CSV"""
        if not self.file:
            raise ValidationError(_('Por favor seleccione un archivo'))

        try:
            # Decodificar archivo
            csv_data = base64.b64decode(self.file)
            file_input = io.StringIO(csv_data.decode(self.encoding))
            file_reader = csv.DictReader(file_input, delimiter=self.delimiter)
            
            # Validar cabeceras
            required_headers = [
                'identification_type', 'identification_id', 'name',
                'work_email', 'mobile_phone', 'department'
            ]
            headers = file_reader.fieldnames
            
            if not all(header in headers for header in required_headers):
                raise ValidationError(_('Faltan columnas requeridas en el archivo'))

            # Procesar registros
            employees_created = 0
            employees_updated = 0
            errors = []

            for row in file_reader:
                try:
                    # Buscar departamento
                    department = self.env['hr.department'].search([
                        ('name', '=', row['department'])
                    ], limit=1)
                    
                    if not department:
                        department = self.env['hr.department'].create({
                            'name': row['department']
                        })

                    # Buscar o crear empleado
                    employee = self.env['hr.employee'].search([
                        ('identification_id', '=', row['identification_id'])
                    ], limit=1)

                    employee_vals = {
                        'identification_type': row['identification_type'],
                        'identification_id': row['identification_id'],
                        'name': row['name'],
                        'work_email': row['work_email'],
                        'mobile_phone': row['mobile_phone'],
                        'department_id': department.id,
                        'country_id': self.env.ref('base.co').id,
                    }

                    if employee:
                        employee.write(employee_vals)
                        employees_updated += 1
                    else:
                        self.env['hr.employee'].create(employee_vals)
                        employees_created += 1

                except Exception as e:
                    errors.append(f"Error en línea {file_reader.line_num}: {str(e)}")

            # Crear registro de log
            self.env['hr.employee.import.log'].create({
                'date': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'filename': self.filename,
                'employees_created': employees_created,
                'employees_updated': employees_updated,
                'errors': '\n'.join(errors) if errors else False
            })

            # Mostrar resultado
            message = _(
                'Importación completada:\n'
                '- Empleados creados: %s\n'
                '- Empleados actualizados: %s\n'
                '- Errores encontrados: %s'
            ) % (employees_created, employees_updated, len(errors))

            if errors:
                message += _('\n\nErrores:\n') + '\n'.join(errors)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Resultado de la importación'),
                    'message': message,
                    'type': 'info' if not errors else 'warning',
                    'sticky': True,
                }
            }

        except Exception as e:
            raise ValidationError(_('Error al procesar el archivo: %s') % str(e))

    def action_download_template(self):
        """Descarga plantilla CSV"""
        template_content = "identification_type,identification_id,name,work_email,mobile_phone,department\n"
        template_content += "CC,1234567890,Juan Pérez,juan.perez@example.com,3001234567,Ventas\n"
        
        # Crear adjunto temporal
        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_empleados.csv',
            'type': 'binary',
            'datas': base64.b64encode(template_content.encode('utf-8')),
            'mimetype': 'text/csv'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }