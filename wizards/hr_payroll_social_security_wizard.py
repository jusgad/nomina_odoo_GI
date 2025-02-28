from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import base64

class HrPayrollSocialSecurityWizard(models.TransientModel):
    _name = 'hr.payroll.social.security.wizard'
    _description = 'Asistente de Seguridad Social'

    date_from = fields.Date(
        string='Fecha Inicial',
        required=True
    )
    
    date_to = fields.Date(
        string='Fecha Final',
        required=True
    )

    payment_date = fields.Date(
        string='Fecha de Pago',
        required=True,
        default=fields.Date.today
    )

    report_type = fields.Selection([
        ('pila', 'Planilla PILA'),
        ('summary', 'Resumen Aportes'),
        ('detailed', 'Detalle por Empleado')
    ], string='Tipo de Reporte', required=True, default='pila')

    include_provisions = fields.Boolean(
        string='Incluir Provisiones',
        default=True
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError(_('La fecha final debe ser mayor a la fecha inicial'))

    def action_generate_report(self):
        """Genera reporte según el tipo seleccionado"""
        self.ensure_one()

        try:
            # Obtener método según tipo de reporte
            method_name = f'_generate_{self.report_type}_report'
            if not hasattr(self, method_name):
                raise ValidationError(_('Tipo de reporte no implementado'))

            # Generar reporte
            result = getattr(self, method_name)()
            
            return result

        except Exception as e:
            raise ValidationError(_('Error generando reporte: %s') % str(e))

    def _generate_pila_report(self):
        """Genera planilla PILA"""
        # Crear registro PILA
        pila = self.env['hr.pila'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'payment_date': self.payment_date,
            'state': 'draft'
        })

        # Generar archivo
        pila.action_generate_file()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.pila',
            'res_id': pila.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _generate_summary_report(self):
        """Genera resumen de aportes"""
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'include_provisions': self.include_provisions
        }
        
        return self.env.ref('nomina_colombia.action_report_social_security_summary').report_action(self, data=data)

    def _generate_detailed_report(self):
        """Genera reporte detallado por empleado"""
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'include_provisions': self.include_provisions
        }
        
        return self.env.ref('nomina_colombia.action_report_social_security_detailed').report_action(self, data=data)